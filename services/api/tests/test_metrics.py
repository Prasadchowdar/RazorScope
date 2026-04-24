"""Unit tests for /api/v1/metrics/* endpoints."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.auth import get_merchant_id
from api.db import clickhouse as ch_db, postgres as pg_db

MERCHANT = "11111111-1111-1111-1111-111111111111"

CHURN_STATS_DEFAULT = {
    "new_subscribers": 5,
    "churned_subscribers": 1,
    "reactivated_subscribers": 0,
    "active_at_period_start": 20,
    "churn_mrr_paise": 99900,
}


def _override_auth():
    return MERCHANT


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_merchant_id] = _override_auth
    yield
    app.dependency_overrides.clear()


@pytest.fixture()
def client():
    with patch("api.db.postgres.init_pool"), \
         patch("api.db.postgres.close_pool"), \
         patch("api.db.clickhouse.init_client"):
        with TestClient(app) as c:
            yield c


# ─── /api/v1/metrics/overview ─────────────────────────────────────────────────

class TestMetricsOverview:
    def test_basic_response_shape(self, client):
        with patch.object(pg_db, "active_subscriber_count", return_value=10), \
             patch.object(ch_db, "mrr_opening", return_value=1_000_000), \
             patch.object(ch_db, "mrr_movements_by_type", return_value={"new": 200_000}), \
             patch.object(ch_db, "churn_stats", return_value=CHURN_STATS_DEFAULT):
            resp = client.get("/api/v1/metrics/overview?month=2024-03",
                              headers={"X-Api-Key": "any"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["month"] == "2024-03"
        assert set(data.keys()) >= {
            "active_subscribers", "arpu_paise", "customer_churn_rate",
            "revenue_churn_rate", "nrr_pct", "ltv_months",
        }

    def test_arpu_is_closing_mrr_divided_by_active_subs(self, client):
        # closing = 1_000_000 + 0 = 1_000_000; active = 10 → arpu = 100_000
        with patch.object(pg_db, "active_subscriber_count", return_value=10), \
             patch.object(ch_db, "mrr_opening", return_value=1_000_000), \
             patch.object(ch_db, "mrr_movements_by_type", return_value={}), \
             patch.object(ch_db, "churn_stats", return_value={**CHURN_STATS_DEFAULT, "churned_subscribers": 0}):
            resp = client.get("/api/v1/metrics/overview?month=2024-03",
                              headers={"X-Api-Key": "any"})
        assert resp.json()["arpu_paise"] == 100_000

    def test_arpu_zero_when_no_active_subs(self, client):
        with patch.object(pg_db, "active_subscriber_count", return_value=0), \
             patch.object(ch_db, "mrr_opening", return_value=500_000), \
             patch.object(ch_db, "mrr_movements_by_type", return_value={}), \
             patch.object(ch_db, "churn_stats", return_value={**CHURN_STATS_DEFAULT, "active_at_period_start": 0}):
            resp = client.get("/api/v1/metrics/overview?month=2024-03",
                              headers={"X-Api-Key": "any"})
        assert resp.json()["arpu_paise"] == 0

    def test_customer_churn_rate(self, client):
        # 2 churned / 20 at start = 10%
        with patch.object(pg_db, "active_subscriber_count", return_value=18), \
             patch.object(ch_db, "mrr_opening", return_value=1_000_000), \
             patch.object(ch_db, "mrr_movements_by_type", return_value={"churn": -200_000}), \
             patch.object(ch_db, "churn_stats", return_value={**CHURN_STATS_DEFAULT,
                          "churned_subscribers": 2, "active_at_period_start": 20,
                          "churn_mrr_paise": 200_000}):
            resp = client.get("/api/v1/metrics/overview?month=2024-03",
                              headers={"X-Api-Key": "any"})
        data = resp.json()
        assert data["customer_churn_rate"] == 10.0

    def test_revenue_churn_rate(self, client):
        # churn_mrr=200_000 / opening=1_000_000 = 20%
        with patch.object(pg_db, "active_subscriber_count", return_value=18), \
             patch.object(ch_db, "mrr_opening", return_value=1_000_000), \
             patch.object(ch_db, "mrr_movements_by_type", return_value={"churn": -200_000}), \
             patch.object(ch_db, "churn_stats", return_value={**CHURN_STATS_DEFAULT,
                          "churn_mrr_paise": 200_000}):
            resp = client.get("/api/v1/metrics/overview?month=2024-03",
                              headers={"X-Api-Key": "any"})
        assert resp.json()["revenue_churn_rate"] == 20.0

    def test_nrr_pct(self, client):
        # closing = 1_200_000, opening = 1_000_000 → nrr = 120.0
        with patch.object(pg_db, "active_subscriber_count", return_value=12), \
             patch.object(ch_db, "mrr_opening", return_value=1_000_000), \
             patch.object(ch_db, "mrr_movements_by_type", return_value={"expansion": 200_000}), \
             patch.object(ch_db, "churn_stats", return_value={**CHURN_STATS_DEFAULT,
                          "churned_subscribers": 0, "churn_mrr_paise": 0}):
            resp = client.get("/api/v1/metrics/overview?month=2024-03",
                              headers={"X-Api-Key": "any"})
        assert resp.json()["nrr_pct"] == 120.0

    def test_nrr_zero_when_no_opening_mrr(self, client):
        with patch.object(pg_db, "active_subscriber_count", return_value=5), \
             patch.object(ch_db, "mrr_opening", return_value=0), \
             patch.object(ch_db, "mrr_movements_by_type", return_value={"new": 500_000}), \
             patch.object(ch_db, "churn_stats", return_value={**CHURN_STATS_DEFAULT,
                          "active_at_period_start": 0}):
            resp = client.get("/api/v1/metrics/overview?month=2024-03",
                              headers={"X-Api-Key": "any"})
        assert resp.json()["nrr_pct"] == 0.0

    def test_ltv_computed_from_churn_rate(self, client):
        # 10% monthly churn → LTV = 10 months
        with patch.object(pg_db, "active_subscriber_count", return_value=10), \
             patch.object(ch_db, "mrr_opening", return_value=1_000_000), \
             patch.object(ch_db, "mrr_movements_by_type", return_value={}), \
             patch.object(ch_db, "churn_stats", return_value={**CHURN_STATS_DEFAULT,
                          "churned_subscribers": 2, "active_at_period_start": 20}):
            resp = client.get("/api/v1/metrics/overview?month=2024-03",
                              headers={"X-Api-Key": "any"})
        assert resp.json()["ltv_months"] == 10.0

    def test_ltv_none_when_no_churn(self, client):
        with patch.object(pg_db, "active_subscriber_count", return_value=10), \
             patch.object(ch_db, "mrr_opening", return_value=1_000_000), \
             patch.object(ch_db, "mrr_movements_by_type", return_value={}), \
             patch.object(ch_db, "churn_stats", return_value={**CHURN_STATS_DEFAULT,
                          "churned_subscribers": 0, "active_at_period_start": 20}):
            resp = client.get("/api/v1/metrics/overview?month=2024-03",
                              headers={"X-Api-Key": "any"})
        assert resp.json()["ltv_months"] is None

    def test_invalid_month_422(self, client):
        resp = client.get("/api/v1/metrics/overview?month=bad",
                          headers={"X-Api-Key": "any"})
        assert resp.status_code == 422


# ─── /api/v1/metrics/plans ────────────────────────────────────────────────────

class TestMetricsPlans:
    def test_basic_shape(self, client):
        plans = [
            {"plan_id": "plan_A", "subscriber_count": 8, "net_mrr_delta_paise": 800_000},
            {"plan_id": "plan_B", "subscriber_count": 2, "net_mrr_delta_paise": 200_000},
        ]
        with patch.object(ch_db, "plan_mrr_breakdown", return_value=plans):
            resp = client.get("/api/v1/metrics/plans?month=2024-03",
                              headers={"X-Api-Key": "any"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_mrr_paise"] == 1_000_000
        assert len(data["plans"]) == 2

    def test_pct_of_total_sums_to_100(self, client):
        plans = [
            {"plan_id": "plan_A", "subscriber_count": 8, "net_mrr_delta_paise": 750_000},
            {"plan_id": "plan_B", "subscriber_count": 2, "net_mrr_delta_paise": 250_000},
        ]
        with patch.object(ch_db, "plan_mrr_breakdown", return_value=plans):
            resp = client.get("/api/v1/metrics/plans?month=2024-03",
                              headers={"X-Api-Key": "any"})
        pcts = [p["pct_of_total"] for p in resp.json()["plans"]]
        assert sum(pcts) == pytest.approx(100.0, abs=0.2)

    def test_empty_plans(self, client):
        with patch.object(ch_db, "plan_mrr_breakdown", return_value=[]):
            resp = client.get("/api/v1/metrics/plans?month=2024-03",
                              headers={"X-Api-Key": "any"})
        data = resp.json()
        assert data["plans"] == []
        assert data["total_mrr_paise"] == 0
