"""
Unit tests for backfill job endpoints.
"""
from datetime import date
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.auth import get_merchant_id, require_admin
from api.jwt_utils import create_access_token
from api.db import postgres as pg_db

MERCHANT = "11111111-1111-1111-1111-111111111111"
JOB_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def _override_auth():
    return MERCHANT


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_merchant_id] = _override_auth
    app.dependency_overrides[require_admin] = _override_auth
    yield
    app.dependency_overrides.clear()


@pytest.fixture()
def client():
    with patch("api.db.postgres.init_pool"), \
         patch("api.db.postgres.close_pool"), \
         patch("api.db.clickhouse.init_client"):
        with TestClient(app) as c:
            yield c


def _sample_job(status="pending"):
    return {
        "job_id": JOB_ID,
        "status": status,
        "from_date": date(2024, 1, 1),
        "to_date": date(2024, 6, 1),
        "pages_fetched": 0,
        "total_pages": None,
        "error_detail": None,
        "created_at": None,
        "completed_at": None,
    }


# ─── POST /api/v1/backfill ────────────────────────────────────────────────────

class TestCreateBackfillJob:
    def test_create_job_returns_201_with_job_id(self, client):
        with patch.object(pg_db, "get_merchant_razorpay_integration", return_value={"has_api_credentials": True}), \
             patch.object(pg_db, "create_backfill_job", return_value=JOB_ID):
            resp = client.post("/api/v1/backfill",
                               json={"from_date": "2024-01", "to_date": "2024-06"},
                               headers={"X-Api-Key": "any"})
        assert resp.status_code == 201
        assert resp.json()["job_id"] == JOB_ID
        assert resp.json()["status"] == "pending"

    def test_job_status_pending_on_creation(self, client):
        with patch.object(pg_db, "get_merchant_razorpay_integration", return_value={"has_api_credentials": True}), \
             patch.object(pg_db, "create_backfill_job", return_value=JOB_ID):
            resp = client.post("/api/v1/backfill",
                               json={"from_date": "2023-01", "to_date": "2023-12"},
                               headers={"X-Api-Key": "any"})
        assert resp.json()["status"] == "pending"

    def test_invalid_from_date_format_returns_422(self, client):
        resp = client.post("/api/v1/backfill",
                           json={"from_date": "2024-1", "to_date": "2024-06"},
                           headers={"X-Api-Key": "any"})
        assert resp.status_code == 422

    def test_invalid_to_date_format_returns_422(self, client):
        resp = client.post("/api/v1/backfill",
                           json={"from_date": "2024-01", "to_date": "24-06"},
                           headers={"X-Api-Key": "any"})
        assert resp.status_code == 422

    def test_to_date_before_from_date_returns_422(self, client):
        resp = client.post("/api/v1/backfill",
                           json={"from_date": "2024-06", "to_date": "2024-01"},
                           headers={"X-Api-Key": "any"})
        assert resp.status_code == 422

    def test_same_month_is_valid(self, client):
        with patch.object(pg_db, "get_merchant_razorpay_integration", return_value={"has_api_credentials": True}), \
             patch.object(pg_db, "create_backfill_job", return_value=JOB_ID):
            resp = client.post("/api/v1/backfill",
                               json={"from_date": "2024-03", "to_date": "2024-03"},
                               headers={"X-Api-Key": "any"})
        assert resp.status_code == 201

    def test_requires_connected_razorpay_credentials(self, client):
        with patch.object(pg_db, "get_merchant_razorpay_integration", return_value={"has_api_credentials": False}):
            resp = client.post("/api/v1/backfill",
                               json={"from_date": "2024-01", "to_date": "2024-06"},
                               headers={"X-Api-Key": "any"})
        assert resp.status_code == 409

    def test_invalid_month_number_returns_422(self, client):
        resp = client.post("/api/v1/backfill",
                           json={"from_date": "2024-13", "to_date": "2024-13"},
                           headers={"X-Api-Key": "any"})
        assert resp.status_code == 422

    def test_no_credentials_returns_401(self, client):
        app.dependency_overrides.clear()
        resp = client.post("/api/v1/backfill",
                           json={"from_date": "2024-01", "to_date": "2024-06"})
        assert resp.status_code == 401

    def test_viewer_role_forbidden(self, client):
        app.dependency_overrides.clear()
        token = create_access_token(merchant_id=MERCHANT, user_id=JOB_ID, role="viewer")
        resp = client.post(
            "/api/v1/backfill",
            json={"from_date": "2024-01", "to_date": "2024-06"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


# ─── GET /api/v1/backfill ─────────────────────────────────────────────────────

class TestListBackfillJobs:
    def test_list_jobs_returns_empty_list(self, client):
        with patch.object(pg_db, "list_backfill_jobs", return_value=[]):
            resp = client.get("/api/v1/backfill", headers={"X-Api-Key": "any"})
        assert resp.status_code == 200
        assert resp.json()["jobs"] == []

    def test_list_jobs_returns_created_jobs(self, client):
        with patch.object(pg_db, "list_backfill_jobs", return_value=[_sample_job()]):
            resp = client.get("/api/v1/backfill", headers={"X-Api-Key": "any"})
        jobs = resp.json()["jobs"]
        assert len(jobs) == 1
        assert jobs[0]["job_id"] == JOB_ID
        assert jobs[0]["status"] == "pending"


# ─── GET /api/v1/backfill/{job_id} ───────────────────────────────────────────

class TestGetBackfillJob:
    def test_get_job_returns_job(self, client):
        with patch.object(pg_db, "get_backfill_job", return_value=_sample_job("running")):
            resp = client.get(f"/api/v1/backfill/{JOB_ID}",
                              headers={"X-Api-Key": "any"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"

    def test_get_job_returns_404_for_unknown(self, client):
        with patch.object(pg_db, "get_backfill_job", return_value=None):
            resp = client.get("/api/v1/backfill/no-such-id",
                              headers={"X-Api-Key": "any"})
        assert resp.status_code == 404
