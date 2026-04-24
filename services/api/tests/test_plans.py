"""Tests for /api/v1/plans endpoint and plan_id filter on MRR endpoints."""
from contextlib import ExitStack
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.auth import get_merchant_id
from api.db import clickhouse as ch_db, postgres as pg_db

MERCHANT = "11111111-1111-1111-1111-111111111111"


def _auth_override():
    return MERCHANT


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_merchant_id] = _auth_override
    yield
    app.dependency_overrides.clear()


@pytest.fixture()
def client():
    with patch("api.db.postgres.init_pool"), \
         patch("api.db.postgres.close_pool"), \
         patch("api.db.clickhouse.init_client"):
        with TestClient(app) as c:
            yield c


class TestPlansEndpoint:
    def test_returns_plan_list(self, client):
        with patch.object(ch_db, "list_plans", return_value=["plan_A", "plan_B"]):
            resp = client.get("/api/v1/plans", headers={"X-Api-Key": "any"})
        assert resp.status_code == 200
        assert resp.json() == {"plans": ["plan_A", "plan_B"]}

    def test_empty_plan_list(self, client):
        with patch.object(ch_db, "list_plans", return_value=[]):
            resp = client.get("/api/v1/plans", headers={"X-Api-Key": "any"})
        assert resp.status_code == 200
        assert resp.json()["plans"] == []

    def test_requires_auth(self, client):
        app.dependency_overrides.clear()
        # No header → 422 (missing required header) before auth resolves
        resp = client.get("/api/v1/plans")
        assert resp.status_code in (401, 422)
        # restore
        app.dependency_overrides[get_merchant_id] = _auth_override


class TestMrrSummaryPlanFilter:
    def _mock(self, stack, opening=500_000, movements=None):
        movements = movements or {}
        stack.enter_context(patch.object(ch_db, "mrr_opening", return_value=opening))
        stack.enter_context(patch.object(ch_db, "mrr_movements_by_type", return_value=movements))

    def test_plan_id_forwarded_to_clickhouse(self, client):
        with ExitStack() as s:
            mock_opening = s.enter_context(patch.object(ch_db, "mrr_opening", return_value=300_000))
            mock_by_type = s.enter_context(patch.object(ch_db, "mrr_movements_by_type", return_value={}))
            resp = client.get(
                "/api/v1/mrr/summary?month=2024-03&plan_id=plan_premium",
                headers={"X-Api-Key": "any"},
            )
        assert resp.status_code == 200
        # both DB calls received plan_id=plan_premium
        assert mock_opening.call_args.kwargs.get("plan_id") == "plan_premium"
        assert mock_by_type.call_args.kwargs.get("plan_id") == "plan_premium"

    def test_no_plan_id_passes_none(self, client):
        with ExitStack() as s:
            mock_opening = s.enter_context(patch.object(ch_db, "mrr_opening", return_value=0))
            s.enter_context(patch.object(ch_db, "mrr_movements_by_type", return_value={}))
            client.get("/api/v1/mrr/summary?month=2024-03", headers={"X-Api-Key": "any"})
        assert mock_opening.call_args.kwargs.get("plan_id") is None

    def test_response_shape_unchanged_with_plan_filter(self, client):
        with ExitStack() as s:
            self._mock(s, opening=1_000_000, movements={"new": 200_000})
            resp = client.get(
                "/api/v1/mrr/summary?month=2024-03&plan_id=plan_basic",
                headers={"X-Api-Key": "any"},
            )
        data = resp.json()
        assert {"month", "opening_mrr_paise", "closing_mrr_paise",
                "net_new_mrr_paise", "movements"}.issubset(data.keys())


class TestMetricsOverviewPlanFilter:
    def test_plan_id_forwarded_to_churn_stats(self, client):
        churn_zero = {
            "new_subscribers": 0, "churned_subscribers": 0,
            "reactivated_subscribers": 0, "active_at_period_start": 10,
            "churn_mrr_paise": 0,
        }
        with ExitStack() as s:
            s.enter_context(patch.object(pg_db, "active_subscriber_count", return_value=10))
            s.enter_context(patch.object(ch_db, "mrr_opening", return_value=1_000_000))
            s.enter_context(patch.object(ch_db, "mrr_movements_by_type", return_value={}))
            mock_churn = s.enter_context(patch.object(ch_db, "churn_stats", return_value=churn_zero))
            resp = client.get(
                "/api/v1/metrics/overview?month=2024-03&plan_id=plan_pro",
                headers={"X-Api-Key": "any"},
            )
        assert resp.status_code == 200
        assert mock_churn.call_args.kwargs.get("plan_id") == "plan_pro"
