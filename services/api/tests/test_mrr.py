"""
Unit tests for Dashboard API endpoints.

Pure — no real database or ClickHouse connections.
Dependencies are overridden via FastAPI's dependency_overrides.
"""
from datetime import date
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.auth import get_merchant_id
from api.db import clickhouse as ch_db

MERCHANT = "11111111-1111-1111-1111-111111111111"


def _override_auth():
    return MERCHANT


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_merchant_id] = _override_auth
    yield
    app.dependency_overrides.clear()


@pytest.fixture()
def client():
    # Patch DB init calls so lifespan doesn't need real connections
    with patch("api.db.postgres.init_pool"), \
         patch("api.db.postgres.close_pool"), \
         patch("api.db.clickhouse.init_client"):
        with TestClient(app) as c:
            yield c


# ─── /health ──────────────────────────────────────────────────────────────────

class TestHealth:
    def test_ok(self, client):
        with patch("api.db.postgres.merchant_id_for_api_key", return_value=None), \
             patch("api.db.clickhouse._ch") as mock_ch:
            mock_ch.return_value.query.return_value = None
            resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] in ("ok", "degraded")


# ─── /api/v1/mrr/summary ──────────────────────────────────────────────────────

class TestMrrSummary:
    def test_month_with_no_data_returns_zeros(self, client):
        with patch.object(ch_db, "mrr_opening", return_value=0), \
             patch.object(ch_db, "mrr_movements_by_type", return_value={}):
            resp = client.get("/api/v1/mrr/summary?month=2024-01",
                              headers={"X-Api-Key": "any"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["month"] == "2024-01"
        assert body["opening_mrr_paise"] == 0
        assert body["closing_mrr_paise"] == 0
        assert body["net_new_mrr_paise"] == 0
        assert body["movements"]["new"] == 0

    def test_new_subscription_reflected_in_closing(self, client):
        with patch.object(ch_db, "mrr_opening", return_value=0), \
             patch.object(ch_db, "mrr_movements_by_type", return_value={"new": 299900}):
            resp = client.get("/api/v1/mrr/summary?month=2024-03",
                              headers={"X-Api-Key": "any"})
        body = resp.json()
        assert body["opening_mrr_paise"] == 0
        assert body["closing_mrr_paise"] == 299900
        assert body["net_new_mrr_paise"] == 299900
        assert body["movements"]["new"] == 299900
        assert body["movements"]["churn"] == 0

    def test_churn_reduces_closing_mrr(self, client):
        with patch.object(ch_db, "mrr_opening", return_value=600000), \
             patch.object(ch_db, "mrr_movements_by_type", return_value={"churn": -299900}):
            resp = client.get("/api/v1/mrr/summary?month=2024-04",
                              headers={"X-Api-Key": "any"})
        body = resp.json()
        assert body["opening_mrr_paise"] == 600000
        assert body["closing_mrr_paise"] == 300100
        assert body["net_new_mrr_paise"] == -299900

    def test_defaults_to_current_month(self, client):
        today = date.today()
        expected = f"{today.year}-{today.month:02d}"
        with patch.object(ch_db, "mrr_opening", return_value=0), \
             patch.object(ch_db, "mrr_movements_by_type", return_value={}):
            resp = client.get("/api/v1/mrr/summary", headers={"X-Api-Key": "any"})
        assert resp.json()["month"] == expected

    def test_invalid_month_format_returns_422(self, client):
        resp = client.get("/api/v1/mrr/summary?month=2024-3",
                          headers={"X-Api-Key": "any"})
        assert resp.status_code == 422

    def test_invalid_month_value_returns_422(self, client):
        resp = client.get("/api/v1/mrr/summary?month=2024-13",
                          headers={"X-Api-Key": "any"})
        assert resp.status_code == 422


# ─── /api/v1/mrr/trend ────────────────────────────────────────────────────────

class TestMrrTrend:
    def _make_trend_rows(self):
        return [
            {"period_month": date(2024, 1, 1), "movement_type": "new", "delta": 299900},
            {"period_month": date(2024, 2, 1), "movement_type": "new", "delta": 299900},
        ]

    def test_returns_correct_number_of_months(self, client):
        with patch.object(ch_db, "mrr_opening", return_value=0), \
             patch.object(ch_db, "mrr_trend", return_value=[]):
            resp = client.get("/api/v1/mrr/trend?months=6", headers={"X-Api-Key": "any"})
        assert resp.status_code == 200
        assert len(resp.json()["months"]) == 6

    def test_running_opening_mrr_accumulates(self, client):
        today = date.today()
        # Build two rows for the oldest two months in a 3-month window
        m1 = date(today.year if today.month > 2 else today.year - 1,
                  (today.month - 2) % 12 or 12, 1)
        m2 = date(today.year if today.month > 1 else today.year - 1,
                  (today.month - 1) % 12 or 12, 1)
        rows = [
            {"period_month": m1, "movement_type": "new", "delta": 100_000},
            {"period_month": m2, "movement_type": "new", "delta": 50_000},
        ]
        with patch.object(ch_db, "mrr_opening", return_value=0), \
             patch.object(ch_db, "mrr_trend", return_value=rows):
            resp = client.get("/api/v1/mrr/trend?months=3", headers={"X-Api-Key": "any"})
        series = resp.json()["months"]
        assert len(series) == 3
        # First entry: opening=0, net=100_000
        assert series[0]["opening_mrr_paise"] == 0
        assert series[0]["closing_mrr_paise"] == 100_000
        # Second entry: opening carries forward
        assert series[1]["opening_mrr_paise"] == 100_000
        assert series[1]["closing_mrr_paise"] == 150_000

    def test_months_capped_at_36(self, client):
        resp = client.get("/api/v1/mrr/trend?months=37", headers={"X-Api-Key": "any"})
        assert resp.status_code == 422

    def test_months_minimum_1(self, client):
        resp = client.get("/api/v1/mrr/trend?months=0", headers={"X-Api-Key": "any"})
        assert resp.status_code == 422


# ─── /api/v1/mrr/movements ────────────────────────────────────────────────────

class TestMrrMovements:
    def _sample_row(self):
        return {
            "razorpay_sub_id": "sub_001",
            "customer_id": "cust_001",
            "plan_id": "plan_growth_monthly",
            "movement_type": "new",
            "amount_paise": 299900,
            "prev_amount_paise": 0,
            "delta_paise": 299900,
            "voluntary": 0,
            "period_month": date(2024, 3, 1),
        }

    def test_returns_movements_list(self, client):
        with patch.object(ch_db, "mrr_movement_rows", return_value=[self._sample_row()]):
            resp = client.get("/api/v1/mrr/movements?month=2024-03",
                              headers={"X-Api-Key": "any"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["month"] == "2024-03"
        assert len(body["movements"]) == 1
        mv = body["movements"][0]
        assert mv["movement_type"] == "new"
        assert mv["delta_paise"] == 299900
        assert mv["voluntary"] is False

    def test_empty_month_returns_empty_list(self, client):
        with patch.object(ch_db, "mrr_movement_rows", return_value=[]):
            resp = client.get("/api/v1/mrr/movements?month=2020-01",
                              headers={"X-Api-Key": "any"})
        assert resp.json()["movements"] == []

    def test_pagination_params_passed_through(self, client):
        with patch.object(ch_db, "mrr_movement_rows", return_value=[]) as mock:
            client.get("/api/v1/mrr/movements?month=2024-03&page=2&page_size=25",
                       headers={"X-Api-Key": "any"})
        mock.assert_called_once_with(MERCHANT, date(2024, 3, 1), limit=25, offset=25, plan_id=None, country=None, source=None, payment_method=None)


# ─── Auth ─────────────────────────────────────────────────────────────────────

class TestAuth:
    def test_no_credentials_returns_401(self, client):
        app.dependency_overrides.clear()
        resp = client.get("/api/v1/mrr/summary?month=2024-01")
        assert resp.status_code == 401

    def test_invalid_api_key_returns_401(self, client):
        app.dependency_overrides.clear()
        with patch("api.db.postgres.merchant_id_for_api_key", return_value=None):
            resp = client.get("/api/v1/mrr/summary?month=2024-01",
                              headers={"X-Api-Key": "bad_key"})
        assert resp.status_code == 401
