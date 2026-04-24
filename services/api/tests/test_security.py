"""Security endpoint tests — no real database."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.auth import get_merchant_id, require_admin
from api.jwt_utils import create_access_token

MERCHANT = "11111111-1111-1111-1111-111111111111"
KEY_ID   = "dddddddd-dddd-dddd-dddd-dddddddddddd"
AUTH     = {"X-Api-Key": "test-key"}

SAMPLE_KEY = {
    "id": KEY_ID,
    "name": "Production Key",
    "key_prefix": "rzs_abc12345****",
    "role": "admin",
    "last_used_at": None,
    "expires_at": None,
    "created_at": "2024-01-15T10:00:00",
    "revoked_at": None,
}

SAMPLE_AUDIT = {
    "id": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
    "actor_key": "rzs_test****",
    "action": "api_key.created",
    "resource": f"key:{KEY_ID}",
    "detail": {"name": "Production Key", "role": "admin"},
    "ip_addr": "127.0.0.1",
    "created_at": "2024-01-15T10:00:00",
}


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


# ── API Keys ──────────────────────────────────────────────────────────────────

class TestApiKeys:
    def test_list_keys_empty(self, client):
        with patch("api.db.postgres.list_api_keys", return_value=[]):
            r = client.get("/api/v1/security/keys", headers=AUTH)
        assert r.status_code == 200
        assert r.json()["keys"] == []

    def test_list_keys_returns_data(self, client):
        with patch("api.db.postgres.list_api_keys", return_value=[SAMPLE_KEY]):
            r = client.get("/api/v1/security/keys", headers=AUTH)
        assert r.status_code == 200
        assert r.json()["keys"][0]["name"] == "Production Key"
        assert "key_hash" not in r.json()["keys"][0]

    def test_create_key_success(self, client):
        created = {**SAMPLE_KEY, "raw_key": "rzs_abc123456789abcdefghij"}
        with patch("api.db.postgres.create_api_key", return_value=created), \
             patch("api.db.postgres.write_audit_log"):
            r = client.post("/api/v1/security/keys", headers=AUTH,
                            json={"name": "Production Key", "role": "admin"})
        assert r.status_code == 201
        data = r.json()
        assert data["raw_key"].startswith("rzs_")
        assert data["name"] == "Production Key"

    def test_create_key_invalid_role(self, client):
        r = client.post("/api/v1/security/keys", headers=AUTH,
                        json={"name": "Bad Key", "role": "superuser"})
        assert r.status_code == 422

    def test_create_viewer_key(self, client):
        created = {**SAMPLE_KEY, "role": "viewer", "raw_key": "rzs_viewerkey123456789"}
        with patch("api.db.postgres.create_api_key", return_value=created), \
             patch("api.db.postgres.write_audit_log"):
            r = client.post("/api/v1/security/keys", headers=AUTH,
                            json={"name": "Read Only", "role": "viewer"})
        assert r.status_code == 201
        assert r.json()["role"] == "viewer"

    def test_revoke_key_success(self, client):
        with patch("api.db.postgres.revoke_api_key", return_value=True), \
             patch("api.db.postgres.write_audit_log"):
            r = client.delete(f"/api/v1/security/keys/{KEY_ID}", headers=AUTH)
        assert r.status_code == 204

    def test_revoke_key_not_found(self, client):
        with patch("api.db.postgres.revoke_api_key", return_value=False):
            r = client.delete(f"/api/v1/security/keys/{KEY_ID}", headers=AUTH)
        assert r.status_code == 404

    def test_key_has_no_hash_in_response(self, client):
        with patch("api.db.postgres.list_api_keys", return_value=[SAMPLE_KEY]):
            r = client.get("/api/v1/security/keys", headers=AUTH)
        assert r.status_code == 200
        for key in r.json()["keys"]:
            assert "key_hash" not in key

    def test_viewer_role_cannot_list_keys(self, client):
        app.dependency_overrides.clear()
        token = create_access_token(merchant_id=MERCHANT, user_id=KEY_ID, role="viewer")
        r = client.get("/api/v1/security/keys", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403


# ── Audit Log ─────────────────────────────────────────────────────────────────

class TestAuditLog:
    def test_list_empty(self, client):
        with patch("api.db.postgres.list_audit_log", return_value=[]):
            r = client.get("/api/v1/security/audit", headers=AUTH)
        assert r.status_code == 200
        assert r.json()["entries"] == []
        assert r.json()["count"] == 0

    def test_list_returns_entries(self, client):
        with patch("api.db.postgres.list_audit_log", return_value=[SAMPLE_AUDIT]):
            r = client.get("/api/v1/security/audit", headers=AUTH)
        assert r.status_code == 200
        assert r.json()["count"] == 1
        assert r.json()["entries"][0]["action"] == "api_key.created"

    def test_limit_capped_at_500(self, client):
        with patch("api.db.postgres.list_audit_log", return_value=[]) as mock_list:
            r = client.get("/api/v1/security/audit?limit=9999", headers=AUTH)
        assert r.status_code == 200
        mock_list.assert_called_once_with(MERCHANT, 500)

    def test_default_limit_100(self, client):
        with patch("api.db.postgres.list_audit_log", return_value=[]) as mock_list:
            r = client.get("/api/v1/security/audit", headers=AUTH)
        assert r.status_code == 200
        mock_list.assert_called_once_with(MERCHANT, 100)

    def test_audit_entry_has_actor_and_action(self, client):
        with patch("api.db.postgres.list_audit_log", return_value=[SAMPLE_AUDIT]):
            r = client.get("/api/v1/security/audit", headers=AUTH)
        entry = r.json()["entries"][0]
        assert "actor_key" in entry
        assert "action" in entry
        assert "created_at" in entry

    def test_create_key_writes_audit(self, client):
        created = {**SAMPLE_KEY, "raw_key": "rzs_abc123456789abcdefghij"}
        with patch("api.db.postgres.create_api_key", return_value=created) as mock_create, \
             patch("api.db.postgres.write_audit_log") as mock_audit:
            r = client.post("/api/v1/security/keys", headers=AUTH,
                            json={"name": "Audited Key", "role": "admin"})
        assert r.status_code == 201
        mock_audit.assert_called_once()
        call_kwargs = mock_audit.call_args.kwargs
        assert call_kwargs["action"] == "api_key.created"

    def test_revoke_key_writes_audit(self, client):
        with patch("api.db.postgres.revoke_api_key", return_value=True), \
             patch("api.db.postgres.write_audit_log") as mock_audit:
            r = client.delete(f"/api/v1/security/keys/{KEY_ID}", headers=AUTH)
        assert r.status_code == 204
        mock_audit.assert_called_once()
        assert mock_audit.call_args.kwargs["action"] == "api_key.revoked"
