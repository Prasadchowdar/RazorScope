"""CRM endpoint tests — no real database."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.auth import get_merchant_id

MERCHANT = "11111111-1111-1111-1111-111111111111"
STAGE_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
LEAD_ID  = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

AUTH = {"X-Api-Key": "test-key"}

SAMPLE_STAGE = {"id": STAGE_ID, "name": "Prospect", "position": 1, "color": "#6B7280"}
SAMPLE_LEAD  = {
    "id": LEAD_ID, "stage_id": STAGE_ID, "customer_id": None,
    "name": "Acme Corp", "email": "cto@acme.io", "company": "Acme",
    "phone": None, "plan_interest": "Pro", "mrr_estimate_paise": 50000,
    "source": "referral", "owner": "alice", "notes": "",
    "created_at": "2024-01-15T10:00:00", "updated_at": "2024-01-15T10:00:00",
}
SAMPLE_ACTIVITY = {
    "id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
    "type": "note", "body": "Initial call done.", "created_at": "2024-01-15T10:05:00",
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


# ── Stages ────────────────────────────────────────────────────────────────────

class TestStages:
    def test_list_returns_stages(self, client):
        with patch("api.db.postgres.list_pipeline_stages", return_value=[SAMPLE_STAGE]):
            r = client.get("/api/v1/crm/stages", headers=AUTH)
        assert r.status_code == 200
        assert r.json()["stages"] == [SAMPLE_STAGE]

    def test_list_empty(self, client):
        with patch("api.db.postgres.list_pipeline_stages", return_value=[]):
            r = client.get("/api/v1/crm/stages", headers=AUTH)
        assert r.status_code == 200
        assert r.json()["stages"] == []

    def test_create_stage(self, client):
        with patch("api.db.postgres.create_pipeline_stage", return_value=SAMPLE_STAGE):
            r = client.post("/api/v1/crm/stages", json={"name": "Prospect"}, headers=AUTH)
        assert r.status_code == 201
        assert r.json()["name"] == "Prospect"

    def test_create_stage_with_color(self, client):
        stage = {**SAMPLE_STAGE, "color": "#FF5733"}
        with patch("api.db.postgres.create_pipeline_stage", return_value=stage):
            r = client.post("/api/v1/crm/stages", json={"name": "Prospect", "color": "#FF5733"}, headers=AUTH)
        assert r.status_code == 201
        assert r.json()["color"] == "#FF5733"

    def test_update_stage(self, client):
        updated = {**SAMPLE_STAGE, "name": "Qualified"}
        with patch("api.db.postgres.update_pipeline_stage", return_value=updated):
            r = client.put(f"/api/v1/crm/stages/{STAGE_ID}", json={"name": "Qualified"}, headers=AUTH)
        assert r.status_code == 200
        assert r.json()["name"] == "Qualified"

    def test_update_stage_not_found(self, client):
        with patch("api.db.postgres.update_pipeline_stage", return_value=None):
            r = client.put(f"/api/v1/crm/stages/{STAGE_ID}", json={"name": "X"}, headers=AUTH)
        assert r.status_code == 404

    def test_delete_stage(self, client):
        with patch("api.db.postgres.delete_pipeline_stage", return_value=True):
            r = client.delete(f"/api/v1/crm/stages/{STAGE_ID}", headers=AUTH)
        assert r.status_code == 204

    def test_delete_stage_has_leads(self, client):
        with patch("api.db.postgres.delete_pipeline_stage", return_value=False):
            r = client.delete(f"/api/v1/crm/stages/{STAGE_ID}", headers=AUTH)
        assert r.status_code == 409


# ── Leads ─────────────────────────────────────────────────────────────────────

class TestLeads:
    def test_list_leads(self, client):
        with patch("api.db.postgres.list_crm_leads", return_value=[SAMPLE_LEAD]):
            r = client.get("/api/v1/crm/leads", headers=AUTH)
        assert r.status_code == 200
        assert len(r.json()["leads"]) == 1

    def test_list_leads_filter_by_stage(self, client):
        with patch("api.db.postgres.list_crm_leads", return_value=[SAMPLE_LEAD]) as m:
            r = client.get(f"/api/v1/crm/leads?stage_id={STAGE_ID}", headers=AUTH)
        assert r.status_code == 200
        m.assert_called_once_with(MERCHANT, STAGE_ID)

    def test_create_lead(self, client):
        with patch("api.db.postgres.create_crm_lead", return_value=SAMPLE_LEAD):
            r = client.post("/api/v1/crm/leads", json={"name": "Acme Corp"}, headers=AUTH)
        assert r.status_code == 201
        assert r.json()["name"] == "Acme Corp"

    def test_create_lead_missing_name(self, client):
        r = client.post("/api/v1/crm/leads", json={"email": "x@y.com"}, headers=AUTH)
        assert r.status_code == 422

    def test_get_lead(self, client):
        with patch("api.db.postgres.get_crm_lead", return_value=SAMPLE_LEAD), \
             patch("api.db.postgres.list_lead_activities", return_value=[SAMPLE_ACTIVITY]):
            r = client.get(f"/api/v1/crm/leads/{LEAD_ID}", headers=AUTH)
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == LEAD_ID
        assert len(data["activities"]) == 1

    def test_get_lead_not_found(self, client):
        with patch("api.db.postgres.get_crm_lead", return_value=None):
            r = client.get(f"/api/v1/crm/leads/{LEAD_ID}", headers=AUTH)
        assert r.status_code == 404

    def test_update_lead(self, client):
        updated = {**SAMPLE_LEAD, "email": "new@acme.io"}
        with patch("api.db.postgres.update_crm_lead", return_value=updated):
            r = client.put(f"/api/v1/crm/leads/{LEAD_ID}", json={"email": "new@acme.io"}, headers=AUTH)
        assert r.status_code == 200
        assert r.json()["email"] == "new@acme.io"

    def test_update_lead_not_found(self, client):
        with patch("api.db.postgres.update_crm_lead", return_value=None):
            r = client.put(f"/api/v1/crm/leads/{LEAD_ID}", json={"email": "x@y.com"}, headers=AUTH)
        assert r.status_code == 404

    def test_delete_lead(self, client):
        with patch("api.db.postgres.delete_crm_lead", return_value=True):
            r = client.delete(f"/api/v1/crm/leads/{LEAD_ID}", headers=AUTH)
        assert r.status_code == 204

    def test_delete_lead_not_found(self, client):
        with patch("api.db.postgres.delete_crm_lead", return_value=False):
            r = client.delete(f"/api/v1/crm/leads/{LEAD_ID}", headers=AUTH)
        assert r.status_code == 404

    def test_move_stage_via_update(self, client):
        new_stage = "dddddddd-dddd-dddd-dddd-dddddddddddd"
        updated = {**SAMPLE_LEAD, "stage_id": new_stage}
        with patch("api.db.postgres.update_crm_lead", return_value=updated):
            r = client.put(f"/api/v1/crm/leads/{LEAD_ID}", json={"stage_id": new_stage}, headers=AUTH)
        assert r.status_code == 200
        assert r.json()["stage_id"] == new_stage


# ── Activities ────────────────────────────────────────────────────────────────

class TestActivities:
    def test_add_note(self, client):
        with patch("api.db.postgres.get_crm_lead", return_value=SAMPLE_LEAD), \
             patch("api.db.postgres.add_lead_activity", return_value=SAMPLE_ACTIVITY):
            r = client.post(
                f"/api/v1/crm/leads/{LEAD_ID}/activities",
                json={"type": "note", "body": "Initial call done."},
                headers=AUTH,
            )
        assert r.status_code == 201
        assert r.json()["type"] == "note"

    def test_add_call(self, client):
        activity = {**SAMPLE_ACTIVITY, "type": "call"}
        with patch("api.db.postgres.get_crm_lead", return_value=SAMPLE_LEAD), \
             patch("api.db.postgres.add_lead_activity", return_value=activity):
            r = client.post(
                f"/api/v1/crm/leads/{LEAD_ID}/activities",
                json={"type": "call", "body": "30 min demo call"},
                headers=AUTH,
            )
        assert r.status_code == 201

    def test_invalid_activity_type(self, client):
        r = client.post(
            f"/api/v1/crm/leads/{LEAD_ID}/activities",
            json={"type": "fax", "body": "Sent a fax"},
            headers=AUTH,
        )
        assert r.status_code == 422

    def test_activity_lead_not_found(self, client):
        with patch("api.db.postgres.get_crm_lead", return_value=None):
            r = client.post(
                f"/api/v1/crm/leads/{LEAD_ID}/activities",
                json={"type": "note", "body": "test"},
                headers=AUTH,
            )
        assert r.status_code == 404


# ── Pipeline snapshot ─────────────────────────────────────────────────────────

class TestPipeline:
    def test_pipeline_groups_leads_by_stage(self, client):
        leads = [SAMPLE_LEAD, {**SAMPLE_LEAD, "id": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"}]
        with patch("api.db.postgres.list_pipeline_stages", return_value=[SAMPLE_STAGE]), \
             patch("api.db.postgres.list_crm_leads", return_value=leads):
            r = client.get("/api/v1/crm/pipeline", headers=AUTH)
        assert r.status_code == 200
        data = r.json()
        assert len(data["pipeline"]) == 1
        assert len(data["pipeline"][0]["leads"]) == 2
        assert data["unassigned"] == []

    def test_pipeline_unassigned_leads(self, client):
        unassigned_lead = {**SAMPLE_LEAD, "stage_id": None}
        with patch("api.db.postgres.list_pipeline_stages", return_value=[SAMPLE_STAGE]), \
             patch("api.db.postgres.list_crm_leads", return_value=[unassigned_lead]):
            r = client.get("/api/v1/crm/pipeline", headers=AUTH)
        assert r.status_code == 200
        data = r.json()
        assert data["pipeline"][0]["leads"] == []
        assert len(data["unassigned"]) == 1

    def test_pipeline_requires_auth(self, client):
        app.dependency_overrides.clear()
        with patch("api.db.postgres.merchant_id_for_api_key", return_value=None):
            r = client.get("/api/v1/crm/pipeline", headers={"X-Api-Key": "bad"})
        assert r.status_code == 401
