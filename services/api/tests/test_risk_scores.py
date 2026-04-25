"""
Unit tests for the /subscribers/risk-scores endpoint.
"""
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
    with patch("api.db.postgres.init_pool"), \
         patch("api.db.postgres.close_pool"), \
         patch("api.db.clickhouse.init_client"):
        with TestClient(app) as c:
            yield c


def _risk_row(
    sub_id="sub_001",
    customer_id="cust_001",
    plan_id="plan_pro",
    has_contraction_90d=True,
    tenure_months=15,
    current_mrr_paise=200000,
    peak_mrr_paise=500000,
):
    return {
        "razorpay_sub_id": sub_id,
        "customer_id": customer_id,
        "plan_id": plan_id,
        "has_contraction_90d": has_contraction_90d,
        "tenure_months": tenure_months,
        "current_mrr_paise": current_mrr_paise,
        "peak_mrr_paise": peak_mrr_paise,
    }


class TestRiskScores:
    def test_returns_200_with_scores_list(self, client):
        rows = [_risk_row()]
        with patch.object(ch_db, "subscriber_risk_factors", return_value=rows), \
             patch.object(ch_db, "subscriber_payment_failures", return_value=0):
            resp = client.get("/api/v1/subscribers/risk-scores", headers={"X-Api-Key": "any"})
        assert resp.status_code == 200
        body = resp.json()
        assert "scores" in body
        assert "total" in body
        assert body["total"] == 1

    def test_high_risk_all_factors(self, client):
        row = _risk_row(has_contraction_90d=True, tenure_months=15,
                        current_mrr_paise=200000, peak_mrr_paise=500000)
        with patch.object(ch_db, "subscriber_risk_factors", return_value=[row]), \
             patch.object(ch_db, "subscriber_payment_failures", return_value=3):
            resp = client.get("/api/v1/subscribers/risk-scores", headers={"X-Api-Key": "any"})
        score = resp.json()["scores"][0]
        assert score["risk_label"] == "high"
        assert score["risk_score"] >= 65
        assert len(score["factors"]) >= 3

    def test_low_risk_no_factors(self, client):
        row = _risk_row(has_contraction_90d=False, tenure_months=6,
                        current_mrr_paise=300000, peak_mrr_paise=310000)
        with patch.object(ch_db, "subscriber_risk_factors", return_value=[row]), \
             patch.object(ch_db, "subscriber_payment_failures", return_value=0):
            resp = client.get("/api/v1/subscribers/risk-scores", headers={"X-Api-Key": "any"})
        score = resp.json()["scores"][0]
        assert score["risk_label"] == "low"
        assert score["risk_score"] < 35

    def test_empty_returns_zero_total(self, client):
        with patch.object(ch_db, "subscriber_risk_factors", return_value=[]), \
             patch.object(ch_db, "subscriber_payment_failures", return_value=0):
            resp = client.get("/api/v1/subscribers/risk-scores", headers={"X-Api-Key": "any"})
        body = resp.json()
        assert body["scores"] == []
        assert body["total"] == 0

    def test_limit_param_accepted(self, client):
        with patch.object(ch_db, "subscriber_risk_factors", return_value=[]) as mock, \
             patch.object(ch_db, "subscriber_payment_failures", return_value=0):
            client.get("/api/v1/subscribers/risk-scores?limit=100", headers={"X-Api-Key": "any"})
        mock.assert_called_once_with(MERCHANT, limit=100)
