"""
Unit tests for subscriber detail and CSV export endpoints.
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
    with patch("api.db.postgres.init_pool"), \
         patch("api.db.postgres.close_pool"), \
         patch("api.db.clickhouse.init_client"):
        with TestClient(app) as c:
            yield c


def _timeline_rows():
    return [
        {
            "razorpay_sub_id": "sub_001",
            "customer_id": "cust_001",
            "plan_id": "plan_growth_monthly",
            "movement_type": "new",
            "amount_paise": 299900,
            "prev_amount_paise": 0,
            "delta_paise": 299900,
            "voluntary": 0,
            "period_month": date(2024, 1, 1),
        },
        {
            "razorpay_sub_id": "sub_001",
            "customer_id": "cust_001",
            "plan_id": "plan_growth_monthly",
            "movement_type": "expansion",
            "amount_paise": 499900,
            "prev_amount_paise": 299900,
            "delta_paise": 200000,
            "voluntary": 0,
            "period_month": date(2024, 3, 1),
        },
    ]


# ─── GET /api/v1/subscribers/{sub_id} ────────────────────────────────────────

class TestSubscriberDetail:
    def test_returns_timeline(self, client):
        with patch.object(ch_db, "subscriber_timeline", return_value=_timeline_rows()):
            resp = client.get("/api/v1/subscribers/sub_001",
                              headers={"X-Api-Key": "any"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["razorpay_sub_id"] == "sub_001"
        assert body["customer_id"] == "cust_001"
        assert body["plan_id"] == "plan_growth_monthly"
        assert body["current_amount_paise"] == 499900
        assert len(body["timeline"]) == 2

    def test_timeline_serialises_dates(self, client):
        with patch.object(ch_db, "subscriber_timeline", return_value=_timeline_rows()):
            resp = client.get("/api/v1/subscribers/sub_001",
                              headers={"X-Api-Key": "any"})
        periods = [e["period_month"] for e in resp.json()["timeline"]]
        assert periods == ["2024-01", "2024-03"]

    def test_timeline_serialises_voluntary_as_bool(self, client):
        with patch.object(ch_db, "subscriber_timeline", return_value=_timeline_rows()):
            resp = client.get("/api/v1/subscribers/sub_001",
                              headers={"X-Api-Key": "any"})
        for entry in resp.json()["timeline"]:
            assert isinstance(entry["voluntary"], bool)

    def test_unknown_subscriber_returns_404(self, client):
        with patch.object(ch_db, "subscriber_timeline", return_value=[]):
            resp = client.get("/api/v1/subscribers/sub_unknown",
                              headers={"X-Api-Key": "any"})
        assert resp.status_code == 404

    def test_first_movement_is_new(self, client):
        with patch.object(ch_db, "subscriber_timeline", return_value=_timeline_rows()):
            resp = client.get("/api/v1/subscribers/sub_001",
                              headers={"X-Api-Key": "any"})
        assert resp.json()["timeline"][0]["movement_type"] == "new"


# ─── GET /api/v1/mrr/movements/export ────────────────────────────────────────

class TestMovementsExport:
    def _sample_rows(self):
        return [
            {
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
        ]

    def test_returns_csv_content_type(self, client):
        with patch.object(ch_db, "mrr_movement_rows_all", return_value=self._sample_rows()):
            resp = client.get("/api/v1/mrr/movements/export?month=2024-03",
                              headers={"X-Api-Key": "any"})
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]

    def test_csv_has_header_row(self, client):
        with patch.object(ch_db, "mrr_movement_rows_all", return_value=self._sample_rows()):
            resp = client.get("/api/v1/mrr/movements/export?month=2024-03",
                              headers={"X-Api-Key": "any"})
        lines = resp.text.strip().splitlines()
        assert lines[0].startswith("razorpay_sub_id")

    def test_csv_data_row_count(self, client):
        with patch.object(ch_db, "mrr_movement_rows_all", return_value=self._sample_rows()):
            resp = client.get("/api/v1/mrr/movements/export?month=2024-03",
                              headers={"X-Api-Key": "any"})
        lines = resp.text.strip().splitlines()
        assert len(lines) == 2  # header + 1 data row

    def test_csv_attachment_filename(self, client):
        with patch.object(ch_db, "mrr_movement_rows_all", return_value=[]):
            resp = client.get("/api/v1/mrr/movements/export?month=2024-03",
                              headers={"X-Api-Key": "any"})
        cd = resp.headers.get("content-disposition", "")
        assert "mrr_movements_2024-03.csv" in cd

    def test_empty_month_returns_header_only(self, client):
        with patch.object(ch_db, "mrr_movement_rows_all", return_value=[]):
            resp = client.get("/api/v1/mrr/movements/export?month=2024-01",
                              headers={"X-Api-Key": "any"})
        lines = resp.text.strip().splitlines()
        assert len(lines) == 1  # header only

    def test_invalid_month_returns_422(self, client):
        resp = client.get("/api/v1/mrr/movements/export?month=2024-3",
                          headers={"X-Api-Key": "any"})
        assert resp.status_code == 422

    def test_plan_filter_passed_through(self, client):
        with patch.object(ch_db, "mrr_movement_rows_all", return_value=[]) as mock:
            client.get("/api/v1/mrr/movements/export?month=2024-03&plan_id=plan_x",
                       headers={"X-Api-Key": "any"})
        mock.assert_called_once_with(MERCHANT, date(2024, 3, 1), plan_id="plan_x")
