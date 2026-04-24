"""Segmentation endpoint and filter param tests."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.auth import get_merchant_id
from api.db import clickhouse as ch_db

MERCHANT = "11111111-1111-1111-1111-111111111111"
AUTH = {"X-Api-Key": "test-key"}

SEGMENT_DATA = {
    "plans": ["plan_monthly", "plan_annual"],
    "countries": ["IN", "US", "GB"],
    "sources": ["organic", "google_ads", "referral"],
    "payment_methods": ["upi_autopay", "card", "nach"],
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


# ── /api/v1/segments ─────────────────────────────────────────────────────────

class TestSegmentsEndpoint:
    def test_returns_all_dimensions(self, client):
        with patch.object(ch_db, "list_segment_values", return_value=SEGMENT_DATA):
            r = client.get("/api/v1/segments", headers=AUTH)
        assert r.status_code == 200
        data = r.json()
        assert "plans" in data
        assert "countries" in data
        assert "sources" in data
        assert "payment_methods" in data

    def test_countries_list(self, client):
        with patch.object(ch_db, "list_segment_values", return_value=SEGMENT_DATA):
            r = client.get("/api/v1/segments", headers=AUTH)
        assert r.json()["countries"] == ["IN", "US", "GB"]

    def test_requires_auth(self, client):
        app.dependency_overrides.clear()
        with patch("api.db.postgres.merchant_id_for_api_key", return_value=None):
            r = client.get("/api/v1/segments", headers={"X-Api-Key": "bad"})
        assert r.status_code == 401


# ── MRR summary with segment filters ─────────────────────────────────────────

class TestMrrSegmentFilters:
    def test_country_filter_forwarded(self, client):
        with patch.object(ch_db, "mrr_opening", return_value=100_000) as mock_open, \
             patch.object(ch_db, "mrr_movements_by_type", return_value={"new": 50_000}):
            r = client.get("/api/v1/mrr/summary?month=2024-01&country=IN", headers=AUTH)
        assert r.status_code == 200
        _, kwargs = mock_open.call_args
        assert kwargs.get("country") == "IN"

    def test_source_filter_forwarded(self, client):
        with patch.object(ch_db, "mrr_opening", return_value=0) as mock_open, \
             patch.object(ch_db, "mrr_movements_by_type", return_value={}):
            r = client.get("/api/v1/mrr/summary?month=2024-01&source=organic", headers=AUTH)
        assert r.status_code == 200
        _, kwargs = mock_open.call_args
        assert kwargs.get("source") == "organic"

    def test_payment_method_filter_forwarded(self, client):
        with patch.object(ch_db, "mrr_opening", return_value=0) as mock_open, \
             patch.object(ch_db, "mrr_movements_by_type", return_value={}):
            r = client.get("/api/v1/mrr/summary?month=2024-01&payment_method=card", headers=AUTH)
        assert r.status_code == 200
        _, kwargs = mock_open.call_args
        assert kwargs.get("payment_method") == "card"

    def test_multiple_filters_combined(self, client):
        with patch.object(ch_db, "mrr_opening", return_value=0) as mock_open, \
             patch.object(ch_db, "mrr_movements_by_type", return_value={}):
            r = client.get(
                "/api/v1/mrr/summary?month=2024-01&country=IN&source=google_ads&plan_id=plan_pro",
                headers=AUTH,
            )
        assert r.status_code == 200
        _, kwargs = mock_open.call_args
        assert kwargs["country"] == "IN"
        assert kwargs["source"] == "google_ads"
        assert kwargs["plan_id"] == "plan_pro"

    def test_no_filters_still_works(self, client):
        with patch.object(ch_db, "mrr_opening", return_value=0), \
             patch.object(ch_db, "mrr_movements_by_type", return_value={}):
            r = client.get("/api/v1/mrr/summary?month=2024-01", headers=AUTH)
        assert r.status_code == 200


# ── Metrics overview with segment filters ─────────────────────────────────────

class TestMetricsSegmentFilters:
    def _churn_stub(self):
        return {
            "new_subscribers": 5, "churned_subscribers": 1,
            "reactivated_subscribers": 0, "active_at_period_start": 20,
            "churn_mrr_paise": 5000,
        }

    def test_country_filter_forwarded_to_metrics(self, client):
        with patch("api.db.postgres.active_subscriber_count", return_value=10), \
             patch.object(ch_db, "mrr_opening", return_value=0) as mock_open, \
             patch.object(ch_db, "mrr_movements_by_type", return_value={}), \
             patch.object(ch_db, "churn_stats", return_value=self._churn_stub()):
            r = client.get("/api/v1/metrics/overview?month=2024-01&country=US", headers=AUTH)
        assert r.status_code == 200
        _, kwargs = mock_open.call_args
        assert kwargs.get("country") == "US"

    def test_payment_method_filter_forwarded_to_metrics(self, client):
        with patch("api.db.postgres.active_subscriber_count", return_value=10), \
             patch.object(ch_db, "mrr_opening", return_value=0) as mock_open, \
             patch.object(ch_db, "mrr_movements_by_type", return_value={}), \
             patch.object(ch_db, "churn_stats", return_value=self._churn_stub()):
            r = client.get("/api/v1/metrics/overview?month=2024-01&payment_method=nach", headers=AUTH)
        assert r.status_code == 200
        _, kwargs = mock_open.call_args
        assert kwargs.get("payment_method") == "nach"


# ── Movements with segment filters ───────────────────────────────────────────

class TestMovementsSegmentFilters:
    def test_movements_country_filter(self, client):
        with patch.object(ch_db, "mrr_movement_rows", return_value=[]) as mock_rows:
            r = client.get("/api/v1/mrr/movements?month=2024-01&country=GB", headers=AUTH)
        assert r.status_code == 200
        _, kwargs = mock_rows.call_args
        assert kwargs.get("country") == "GB"

    def test_movements_source_filter(self, client):
        with patch.object(ch_db, "mrr_movement_rows", return_value=[]) as mock_rows:
            r = client.get("/api/v1/mrr/movements?month=2024-01&source=referral", headers=AUTH)
        assert r.status_code == 200
        _, kwargs = mock_rows.call_args
        assert kwargs.get("source") == "referral"
