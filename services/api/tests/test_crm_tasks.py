"""CRM Tasks, Sequences, Rep Stats, and Enrichment tests — no real database."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.auth import get_merchant_id

MERCHANT  = "11111111-1111-1111-1111-111111111111"
LEAD_ID   = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
TASK_ID   = "ffffffff-ffff-ffff-ffff-ffffffffffff"
SEQ_ID    = "11111111-aaaa-bbbb-cccc-dddddddddddd"
STEP_ID   = "22222222-aaaa-bbbb-cccc-dddddddddddd"

AUTH = {"X-Api-Key": "test-key"}

SAMPLE_TASK = {
    "id": TASK_ID,
    "lead_id": LEAD_ID,
    "title": "Follow up call",
    "description": None,
    "assignee": "alice",
    "due_date": "2024-02-01",
    "status": "open",
    "created_at": "2024-01-15T10:00:00",
    "updated_at": "2024-01-15T10:00:00",
}

SAMPLE_SEQ = {
    "id": SEQ_ID,
    "name": "Onboarding Flow",
    "created_at": "2024-01-15T10:00:00",
    "step_count": 3,
    "active_enrollments": 2,
}

SAMPLE_STEP = {
    "id": STEP_ID,
    "step_num": 1,
    "delay_days": 0,
    "subject": "Welcome!",
    "body": "Hi {{name}}, welcome to our platform.",
}

SAMPLE_LEAD = {
    "id": LEAD_ID, "stage_id": None, "customer_id": None,
    "name": "Acme Corp", "email": "cto@acme.io", "company": "Acme",
    "phone": None, "plan_interest": "Pro", "mrr_estimate_paise": 50000,
    "source": "referral", "owner": "alice", "notes": "",
    "created_at": "2024-01-15T10:00:00", "updated_at": "2024-01-15T10:00:00",
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


# ── Tasks ──────────────────────────────────────────────────────────────────────

class TestTasks:
    def test_list_tasks_empty(self, client):
        with patch("api.db.postgres.list_tasks", return_value=[]):
            r = client.get("/api/v1/crm/tasks", headers=AUTH)
        assert r.status_code == 200
        assert r.json()["tasks"] == []

    def test_list_tasks_by_lead(self, client):
        with patch("api.db.postgres.list_tasks", return_value=[SAMPLE_TASK]) as mock:
            r = client.get(f"/api/v1/crm/tasks?lead_id={LEAD_ID}", headers=AUTH)
        assert r.status_code == 200
        assert len(r.json()["tasks"]) == 1
        mock.assert_called_once_with(MERCHANT, LEAD_ID, None)

    def test_list_tasks_by_status(self, client):
        with patch("api.db.postgres.list_tasks", return_value=[SAMPLE_TASK]) as mock:
            r = client.get("/api/v1/crm/tasks?status=open", headers=AUTH)
        assert r.status_code == 200
        mock.assert_called_once_with(MERCHANT, None, "open")

    def test_create_task(self, client):
        with patch("api.db.postgres.create_task", return_value=SAMPLE_TASK):
            r = client.post("/api/v1/crm/tasks", headers=AUTH,
                            json={"title": "Follow up call", "lead_id": LEAD_ID, "assignee": "alice"})
        assert r.status_code == 201
        assert r.json()["title"] == "Follow up call"

    def test_create_task_no_lead(self, client):
        task_no_lead = {**SAMPLE_TASK, "lead_id": None}
        with patch("api.db.postgres.create_task", return_value=task_no_lead):
            r = client.post("/api/v1/crm/tasks", headers=AUTH, json={"title": "Global task"})
        assert r.status_code == 201

    def test_update_task_status(self, client):
        done_task = {**SAMPLE_TASK, "status": "done"}
        with patch("api.db.postgres.update_task", return_value=done_task):
            r = client.put(f"/api/v1/crm/tasks/{TASK_ID}", headers=AUTH, json={"status": "done"})
        assert r.status_code == 200
        assert r.json()["status"] == "done"

    def test_update_task_not_found(self, client):
        with patch("api.db.postgres.update_task", return_value=None):
            r = client.put(f"/api/v1/crm/tasks/{TASK_ID}", headers=AUTH, json={"status": "done"})
        assert r.status_code == 404

    def test_delete_task(self, client):
        with patch("api.db.postgres.delete_task", return_value=True):
            r = client.delete(f"/api/v1/crm/tasks/{TASK_ID}", headers=AUTH)
        assert r.status_code == 204

    def test_delete_task_not_found(self, client):
        with patch("api.db.postgres.delete_task", return_value=False):
            r = client.delete(f"/api/v1/crm/tasks/{TASK_ID}", headers=AUTH)
        assert r.status_code == 404


# ── Sequences ─────────────────────────────────────────────────────────────────

class TestSequences:
    def test_list_sequences_empty(self, client):
        with patch("api.db.postgres.list_sequences", return_value=[]):
            r = client.get("/api/v1/crm/sequences", headers=AUTH)
        assert r.status_code == 200
        assert r.json()["sequences"] == []

    def test_list_sequences(self, client):
        with patch("api.db.postgres.list_sequences", return_value=[SAMPLE_SEQ]):
            r = client.get("/api/v1/crm/sequences", headers=AUTH)
        assert r.status_code == 200
        assert r.json()["sequences"][0]["name"] == "Onboarding Flow"

    def test_create_sequence(self, client):
        created = {**SAMPLE_SEQ, "step_count": 0, "active_enrollments": 0}
        with patch("api.db.postgres.create_sequence", return_value=created):
            r = client.post("/api/v1/crm/sequences", headers=AUTH, json={"name": "Onboarding Flow"})
        assert r.status_code == 201
        assert r.json()["name"] == "Onboarding Flow"

    def test_get_sequence_with_steps(self, client):
        seq_detail = {**SAMPLE_SEQ, "steps": [SAMPLE_STEP]}
        with patch("api.db.postgres.get_sequence", return_value=seq_detail):
            r = client.get(f"/api/v1/crm/sequences/{SEQ_ID}", headers=AUTH)
        assert r.status_code == 200
        assert len(r.json()["steps"]) == 1

    def test_get_sequence_not_found(self, client):
        with patch("api.db.postgres.get_sequence", return_value=None):
            r = client.get(f"/api/v1/crm/sequences/{SEQ_ID}", headers=AUTH)
        assert r.status_code == 404

    def test_delete_sequence(self, client):
        with patch("api.db.postgres.delete_sequence", return_value=True):
            r = client.delete(f"/api/v1/crm/sequences/{SEQ_ID}", headers=AUTH)
        assert r.status_code == 204

    def test_add_step(self, client):
        with patch("api.db.postgres.add_sequence_step", return_value=SAMPLE_STEP):
            r = client.post(f"/api/v1/crm/sequences/{SEQ_ID}/steps", headers=AUTH,
                            json={"step_num": 1, "delay_days": 0, "subject": "Welcome!", "body": "Hi!"})
        assert r.status_code == 201
        assert r.json()["subject"] == "Welcome!"

    def test_delete_step(self, client):
        with patch("api.db.postgres.delete_sequence_step", return_value=True):
            r = client.delete(f"/api/v1/crm/sequences/{SEQ_ID}/steps/{STEP_ID}", headers=AUTH)
        assert r.status_code == 204

    def test_enroll_lead(self, client):
        enrollment = {
            "id": "aaa", "sequence_id": SEQ_ID, "lead_id": LEAD_ID,
            "current_step": 0, "status": "active", "enrolled_at": "2024-01-15T10:00:00",
        }
        with patch("api.db.postgres.get_crm_lead", return_value=SAMPLE_LEAD), \
             patch("api.db.postgres.enroll_lead", return_value=enrollment):
            r = client.post(f"/api/v1/crm/sequences/{SEQ_ID}/enroll", headers=AUTH,
                            json={"lead_id": LEAD_ID})
        assert r.status_code == 201
        assert r.json()["status"] == "active"

    def test_enroll_lead_not_found(self, client):
        with patch("api.db.postgres.get_crm_lead", return_value=None):
            r = client.post(f"/api/v1/crm/sequences/{SEQ_ID}/enroll", headers=AUTH,
                            json={"lead_id": LEAD_ID})
        assert r.status_code == 404

    def test_unenroll_lead(self, client):
        with patch("api.db.postgres.unenroll_lead", return_value=True):
            r = client.delete(f"/api/v1/crm/sequences/{SEQ_ID}/enroll/{LEAD_ID}", headers=AUTH)
        assert r.status_code == 204

    def test_lead_enrollments(self, client):
        enrollment = {
            "id": "aaa", "sequence_id": SEQ_ID, "sequence_name": "Onboarding Flow",
            "lead_id": LEAD_ID, "current_step": 1, "status": "active",
            "enrolled_at": "2024-01-15T10:00:00",
        }
        with patch("api.db.postgres.list_lead_enrollments", return_value=[enrollment]):
            r = client.get(f"/api/v1/crm/leads/{LEAD_ID}/enrollments", headers=AUTH)
        assert r.status_code == 200
        assert len(r.json()["enrollments"]) == 1


# ── Rep Stats ─────────────────────────────────────────────────────────────────

class TestRepStats:
    def test_rep_stats_empty(self, client):
        with patch("api.db.postgres.get_rep_stats", return_value=[]):
            r = client.get("/api/v1/crm/reps", headers=AUTH)
        assert r.status_code == 200
        assert r.json()["reps"] == []

    def test_rep_stats_returns_data(self, client):
        stats = [{"rep": "alice", "total_leads": 5, "won_leads": 2, "lost_leads": 1,
                  "pipeline_mrr_paise": 250000, "new_leads_30d": 3}]
        with patch("api.db.postgres.get_rep_stats", return_value=stats):
            r = client.get("/api/v1/crm/reps", headers=AUTH)
        assert r.status_code == 200
        assert r.json()["reps"][0]["rep"] == "alice"
        assert r.json()["reps"][0]["pipeline_mrr_paise"] == 250000


# ── Enrichment ────────────────────────────────────────────────────────────────

class TestEnrichment:
    def test_enrich_returns_updated_lead(self, client):
        enriched = {**SAMPLE_LEAD, "notes": "[Enriched] Industry: SaaS | Size: 1-10 employees"}
        with patch("api.db.postgres.enrich_lead", return_value=enriched):
            r = client.post(f"/api/v1/crm/leads/{LEAD_ID}/enrich", headers=AUTH)
        assert r.status_code == 200
        assert "Enriched" in r.json()["notes"]

    def test_enrich_not_found(self, client):
        with patch("api.db.postgres.enrich_lead", return_value=None):
            r = client.post(f"/api/v1/crm/leads/{LEAD_ID}/enrich", headers=AUTH)
        assert r.status_code == 404
