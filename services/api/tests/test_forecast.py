"""
Unit tests for /mrr/forecast endpoint and OLS helper.
"""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.auth import get_merchant_id
from api.db import clickhouse as ch_db
from api.routers.forecast import _ols, _add_months

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
    with patch("api.db.postgres.init_pool"), \
         patch("api.db.postgres.close_pool"), \
         patch("api.db.clickhouse.init_client"):
        with TestClient(app) as c:
            yield c


def _history(n: int = 6):
    return [
        {"month": f"2024-{i + 1:02d}", "closing_mrr_paise": 100_000 + i * 10_000}
        for i in range(n)
    ]


# ─── Unit test: OLS helper ────────────────────────────────────────────────────

class TestOlsFormula:
    def test_perfect_linear_fit(self):
        xs = [0.0, 1.0, 2.0, 3.0]
        ys = [0.0, 10.0, 20.0, 30.0]
        slope, intercept, residual_std = _ols(xs, ys)
        assert abs(slope - 10.0) < 1e-9
        assert abs(intercept) < 1e-9
        assert residual_std < 1e-6

    def test_add_months_wraps_year(self):
        assert _add_months("2024-11", 3) == "2025-02"

    def test_add_months_no_wrap(self):
        assert _add_months("2024-01", 2) == "2024-03"


# ─── Endpoint tests ───────────────────────────────────────────────────────────

class TestForecast:
    def test_returns_three_forecast_months_by_default(self, client):
        with patch.object(ch_db, "mrr_trend_for_forecast", return_value=_history(6)):
            resp = client.get("/api/v1/mrr/forecast", headers={"X-Api-Key": "any"})
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["forecasted_months"]) == 3

    def test_all_months_have_required_fields(self, client):
        with patch.object(ch_db, "mrr_trend_for_forecast", return_value=_history(6)):
            resp = client.get("/api/v1/mrr/forecast", headers={"X-Api-Key": "any"})
        for m in resp.json()["forecasted_months"]:
            assert "month" in m
            assert "closing_mrr_paise" in m
            assert "net_new_mrr_paise" in m
            assert "confidence_low" in m
            assert "confidence_high" in m
            assert m["is_forecast"] is True

    def test_insufficient_history_returns_warning(self, client):
        with patch.object(ch_db, "mrr_trend_for_forecast", return_value=_history(2)):
            resp = client.get("/api/v1/mrr/forecast", headers={"X-Api-Key": "any"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["forecasted_months"] == []
        assert "insufficient" in body["warning"]

    def test_confidence_low_is_non_negative(self, client):
        with patch.object(ch_db, "mrr_trend_for_forecast", return_value=_history(6)):
            resp = client.get("/api/v1/mrr/forecast", headers={"X-Api-Key": "any"})
        for m in resp.json()["forecasted_months"]:
            assert m["confidence_low"] >= 0

    def test_months_ahead_param_controls_count(self, client):
        with patch.object(ch_db, "mrr_trend_for_forecast", return_value=_history(6)):
            resp = client.get("/api/v1/mrr/forecast?months_ahead=1", headers={"X-Api-Key": "any"})
        assert len(resp.json()["forecasted_months"]) == 1
