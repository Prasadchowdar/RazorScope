"""Tests for benchmarks module and /api/v1/benchmarks endpoint."""
from contextlib import ExitStack
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.auth import get_merchant_id
from api.db import clickhouse as ch_db, postgres as pg_db
from api.benchmarks import BENCHMARKS, score

MERCHANT = "11111111-1111-1111-1111-111111111111"
CHURN_ZERO = {
    "new_subscribers": 3, "churned_subscribers": 0, "reactivated_subscribers": 0,
    "active_at_period_start": 10, "churn_mrr_paise": 0,
}


# ── BenchmarkSeries unit tests ────────────────────────────────────────────────

class TestPercentileComputation:
    def test_higher_is_better_at_p50_returns_50(self):
        b = BENCHMARKS["nrr_pct"]
        pct = b.merchant_percentile(b.percentiles[2])  # P50 value
        assert pct == pytest.approx(50.0, abs=1)

    def test_higher_is_better_above_p90_returns_90(self):
        b = BENCHMARKS["mrr_growth_rate"]
        pct = b.merchant_percentile(999)
        assert pct == 90.0

    def test_higher_is_better_below_p10_returns_p10(self):
        b = BENCHMARKS["nrr_pct"]
        pct = b.merchant_percentile(-999)
        assert pct == 10.0

    def test_lower_is_better_at_median_returns_50(self):
        b = BENCHMARKS["customer_churn_rate"]
        pct = b.merchant_percentile(b.percentiles[2])  # P50 churn value
        assert pct == pytest.approx(50.0, abs=1)

    def test_lower_is_better_zero_churn_returns_high_percentile(self):
        b = BENCHMARKS["customer_churn_rate"]
        pct = b.merchant_percentile(0)
        assert pct >= 75  # zero churn = top performer

    def test_lower_is_better_very_high_churn_returns_low_percentile(self):
        b = BENCHMARKS["customer_churn_rate"]
        pct = b.merchant_percentile(99)  # catastrophic churn
        assert pct < 25

    def test_interpolation_between_quartiles(self):
        b = BENCHMARKS["nrr_pct"]
        # Between P25=95 and P50=102 → should be between 25 and 50
        pct = b.merchant_percentile(98.5)
        assert 25 < pct < 50


class TestScoreFunction:
    def test_score_returns_required_keys(self):
        result = score("nrr_pct", 110.0)
        required = {"metric_key", "name", "description", "unit", "direction",
                    "merchant_value", "percentile", "label",
                    "industry_p10", "industry_p25", "industry_p50", "industry_p75", "industry_p90"}
        assert required.issubset(result.keys())

    def test_score_label_top_quartile(self):
        result = score("nrr_pct", 125.0)  # at P90 → top quartile
        assert result["label"] == "top quartile"

    def test_score_label_bottom_quartile(self):
        result = score("nrr_pct", 80.0)  # well below P10
        assert result["label"] == "bottom quartile"


# ── /api/v1/benchmarks endpoint ───────────────────────────────────────────────

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


class TestBenchmarksEndpoint:
    def _mock(self, stack, *, opening=1_000_000, movements=None, churn=None, active=10):
        if movements is None:
            movements = {}
        if churn is None:
            churn = CHURN_ZERO
        stack.enter_context(patch.object(ch_db, "mrr_opening", return_value=opening))
        stack.enter_context(patch.object(ch_db, "mrr_movements_by_type", return_value=movements))
        stack.enter_context(patch.object(ch_db, "churn_stats", return_value=churn))
        stack.enter_context(patch.object(pg_db, "active_subscriber_count", return_value=active))

    def test_response_shape(self, client):
        with ExitStack() as s:
            self._mock(s)
            resp = client.get("/api/v1/benchmarks?month=2024-03",
                              headers={"X-Api-Key": "any"})
        assert resp.status_code == 200
        data = resp.json()
        assert "benchmarks" in data
        assert "data_source" in data
        assert len(data["benchmarks"]) == 5

    def test_all_required_metric_keys_present(self, client):
        with ExitStack() as s:
            self._mock(s)
            resp = client.get("/api/v1/benchmarks?month=2024-03",
                              headers={"X-Api-Key": "any"})
        keys = {b["metric_key"] for b in resp.json()["benchmarks"]}
        assert keys == {"mrr_growth_rate", "customer_churn_rate",
                        "revenue_churn_rate", "nrr_pct", "arpu_paise"}

    def test_nrr_above_100_for_growing_merchant(self, client):
        with ExitStack() as s:
            self._mock(s, opening=1_000_000, movements={"expansion": 200_000})
            resp = client.get("/api/v1/benchmarks?month=2024-03",
                              headers={"X-Api-Key": "any"})
        nrr = next(b for b in resp.json()["benchmarks"] if b["metric_key"] == "nrr_pct")
        assert nrr["merchant_value"] == pytest.approx(120.0, abs=0.1)
        assert nrr["percentile"] > 50

    def test_zero_churn_scores_high_percentile(self, client):
        with ExitStack() as s:
            self._mock(s, churn={**CHURN_ZERO, "churned_subscribers": 0,
                                  "active_at_period_start": 20})
            resp = client.get("/api/v1/benchmarks?month=2024-03",
                              headers={"X-Api-Key": "any"})
        churn_b = next(b for b in resp.json()["benchmarks"]
                       if b["metric_key"] == "customer_churn_rate")
        assert churn_b["percentile"] >= 75

    def test_invalid_month_returns_422(self, client):
        resp = client.get("/api/v1/benchmarks?month=2024-13",
                          headers={"X-Api-Key": "any"})
        assert resp.status_code == 422
