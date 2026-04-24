"""Auth endpoint tests: register, login, refresh, logout, me, dual-auth."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.auth import get_merchant_id
from api.jwt_utils import create_access_token, decode_access_token
from api.main import app

MERCHANT = "11111111-1111-1111-1111-111111111111"
USER_ID  = "22222222-2222-2222-2222-222222222222"
AUTH     = {"X-Api-Key": "test-key"}

SAMPLE_USER = {
    "id": USER_ID,
    "merchant_id": MERCHANT,
    "password_hash": None,  # overridden per test
    "name": "Test User",
    "email": "test@example.com",
    "role": "owner",
    "is_active": True,
}

SAMPLE_REGISTER_RESULT = {
    "merchant_id": MERCHANT,
    "user_id": USER_ID,
    "raw_api_key": "rzs_abcdef1234567890abcdef1234",
    "raw_webhook_secret": "whsec_abcdef1234567890abcdef1234567890",
}

SAMPLE_REFRESH_RECORD = {
    "id": "33333333-3333-3333-3333-333333333333",
    "user_id": USER_ID,
    "merchant_id": MERCHANT,
    "expires_at": "2099-01-01T00:00:00+00:00",
    "role": "owner",
    "is_active": True,
}

# ── Shared fixtures ───────────────────────────────────────────────────────────

@pytest.fixture()
def public_client():
    with patch("api.db.postgres.init_pool"), \
         patch("api.db.postgres.close_pool"), \
         patch("api.db.clickhouse.init_client"):
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


@pytest.fixture()
def auth_client():
    app.dependency_overrides[get_merchant_id] = lambda: MERCHANT
    with patch("api.db.postgres.init_pool"), \
         patch("api.db.postgres.close_pool"), \
         patch("api.db.clickhouse.init_client"):
        with TestClient(app) as c:
            yield c
    app.dependency_overrides.clear()


# ── Register ─────────────────────────────────────────────────────────────────

class TestRegister:
    def test_register_success_returns_201(self, public_client):
        with patch("api.db.auth_db.find_user_by_email", return_value=None), \
             patch("api.db.auth_db.create_merchant_and_user", return_value=SAMPLE_REGISTER_RESULT), \
             patch("api.db.auth_db.store_refresh_token"):
            r = public_client.post("/api/v1/auth/register", json={
                "company_name": "Acme Corp",
                "name": "Alice",
                "email": "alice@example.com",
                "password": "secret123",
            })
        assert r.status_code == 201

    def test_register_returns_access_token_and_api_key(self, public_client):
        with patch("api.db.auth_db.find_user_by_email", return_value=None), \
             patch("api.db.auth_db.create_merchant_and_user", return_value=SAMPLE_REGISTER_RESULT), \
             patch("api.db.auth_db.store_refresh_token"):
            r = public_client.post("/api/v1/auth/register", json={
                "company_name": "Acme Corp",
                "name": "Alice",
                "email": "alice@example.com",
                "password": "secret123",
            })
        data = r.json()
        assert "access_token" in data
        assert "api_key" in data
        assert data["api_key"].startswith("rzs_")
        assert "webhook_secret" in data
        assert data["webhook_secret"].startswith("whsec_")
        assert "webhook_url" in data
        assert data["webhook_url"].endswith(f"/v1/webhooks/razorpay/{MERCHANT}")

    def test_register_duplicate_email_returns_409(self, public_client):
        with patch("api.db.auth_db.find_user_by_email", return_value=SAMPLE_USER):
            r = public_client.post("/api/v1/auth/register", json={
                "company_name": "Acme Corp",
                "name": "Alice",
                "email": "alice@example.com",
                "password": "secret123",
            })
        assert r.status_code == 409

    def test_register_weak_password_returns_422(self, public_client):
        r = public_client.post("/api/v1/auth/register", json={
            "company_name": "Acme Corp",
            "name": "Alice",
            "email": "alice@example.com",
            "password": "short",
        })
        assert r.status_code == 422

    def test_register_invalid_email_returns_422(self, public_client):
        r = public_client.post("/api/v1/auth/register", json={
            "company_name": "Acme Corp",
            "name": "Alice",
            "email": "not-an-email",
            "password": "secret123",
        })
        assert r.status_code == 422

    def test_register_blank_company_name_returns_422(self, public_client):
        r = public_client.post("/api/v1/auth/register", json={
            "company_name": "   ",
            "name": "Alice",
            "email": "alice@example.com",
            "password": "secret123",
        })
        assert r.status_code == 422

    def test_register_sets_refresh_cookie(self, public_client):
        with patch("api.db.auth_db.find_user_by_email", return_value=None), \
             patch("api.db.auth_db.create_merchant_and_user", return_value=SAMPLE_REGISTER_RESULT), \
             patch("api.db.auth_db.store_refresh_token"):
            r = public_client.post("/api/v1/auth/register", json={
                "company_name": "Acme Corp",
                "name": "Alice",
                "email": "alice@example.com",
                "password": "secret123",
            })
        assert "rzs_refresh" in r.cookies


# ── Login ─────────────────────────────────────────────────────────────────────

class TestLogin:
    def _bcrypt_hash(self, password: str) -> str:
        import bcrypt
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def test_login_success_returns_200(self, public_client):
        user = {**SAMPLE_USER, "password_hash": self._bcrypt_hash("secret123")}
        with patch("api.db.auth_db.find_user_by_email", return_value=user), \
             patch("api.db.auth_db.store_refresh_token"):
            r = public_client.post("/api/v1/auth/login", json={
                "email": "test@example.com",
                "password": "secret123",
            })
        assert r.status_code == 200

    def test_login_returns_access_token(self, public_client):
        user = {**SAMPLE_USER, "password_hash": self._bcrypt_hash("secret123")}
        with patch("api.db.auth_db.find_user_by_email", return_value=user), \
             patch("api.db.auth_db.store_refresh_token"):
            r = public_client.post("/api/v1/auth/login", json={
                "email": "test@example.com",
                "password": "secret123",
            })
        data = r.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["merchant_id"] == MERCHANT

    def test_login_wrong_password_returns_401(self, public_client):
        user = {**SAMPLE_USER, "password_hash": self._bcrypt_hash("correct")}
        with patch("api.db.auth_db.find_user_by_email", return_value=user):
            r = public_client.post("/api/v1/auth/login", json={
                "email": "test@example.com",
                "password": "wrong",
            })
        assert r.status_code == 401

    def test_login_unknown_email_returns_401(self, public_client):
        with patch("api.db.auth_db.find_user_by_email", return_value=None):
            r = public_client.post("/api/v1/auth/login", json={
                "email": "nobody@example.com",
                "password": "secret123",
            })
        assert r.status_code == 401

    def test_login_inactive_user_returns_401(self, public_client):
        user = {**SAMPLE_USER, "password_hash": self._bcrypt_hash("secret123"), "is_active": False}
        with patch("api.db.auth_db.find_user_by_email", return_value=user):
            r = public_client.post("/api/v1/auth/login", json={
                "email": "test@example.com",
                "password": "secret123",
            })
        assert r.status_code == 401

    def test_login_sets_refresh_cookie(self, public_client):
        user = {**SAMPLE_USER, "password_hash": self._bcrypt_hash("secret123")}
        with patch("api.db.auth_db.find_user_by_email", return_value=user), \
             patch("api.db.auth_db.store_refresh_token"):
            r = public_client.post("/api/v1/auth/login", json={
                "email": "test@example.com",
                "password": "secret123",
            })
        assert "rzs_refresh" in r.cookies

    def test_login_response_has_no_password_hash(self, public_client):
        user = {**SAMPLE_USER, "password_hash": self._bcrypt_hash("secret123")}
        with patch("api.db.auth_db.find_user_by_email", return_value=user), \
             patch("api.db.auth_db.store_refresh_token"):
            r = public_client.post("/api/v1/auth/login", json={
                "email": "test@example.com",
                "password": "secret123",
            })
        assert "password_hash" not in r.json()


# ── Refresh ───────────────────────────────────────────────────────────────────

class TestRefresh:
    def test_refresh_with_valid_cookie_returns_new_token(self, public_client):
        with patch("api.db.auth_db.lookup_refresh_token", return_value=SAMPLE_REFRESH_RECORD), \
             patch("api.db.auth_db.rotate_refresh_token"):
            public_client.cookies.set("rzs_refresh", "valid_raw_token")
            r = public_client.post("/api/v1/auth/refresh")
        assert r.status_code == 200
        assert "access_token" in r.json()
        payload = decode_access_token(r.json()["access_token"])
        assert payload["role"] == "owner"

    def test_refresh_with_no_cookie_returns_401(self, public_client):
        r = public_client.post("/api/v1/auth/refresh")
        assert r.status_code == 401

    def test_refresh_with_invalid_token_returns_401(self, public_client):
        with patch("api.db.auth_db.lookup_refresh_token", return_value=None):
            public_client.cookies.set("rzs_refresh", "bad_token")
            r = public_client.post("/api/v1/auth/refresh")
        assert r.status_code == 401

    def test_refresh_rotates_token(self, public_client):
        with patch("api.db.auth_db.lookup_refresh_token", return_value=SAMPLE_REFRESH_RECORD), \
             patch("api.db.auth_db.rotate_refresh_token") as mock_rotate:
            public_client.cookies.set("rzs_refresh", "valid_raw_token")
            r = public_client.post("/api/v1/auth/refresh")
        assert r.status_code == 200
        mock_rotate.assert_called_once()

    def test_refresh_inactive_user_returns_401(self, public_client):
        inactive = {**SAMPLE_REFRESH_RECORD, "is_active": False}
        with patch("api.db.auth_db.lookup_refresh_token", return_value=inactive):
            public_client.cookies.set("rzs_refresh", "valid_raw_token")
            r = public_client.post("/api/v1/auth/refresh")
        assert r.status_code == 401


# ── Logout ────────────────────────────────────────────────────────────────────

class TestLogout:
    def test_logout_returns_204(self, public_client):
        with patch("api.db.auth_db.revoke_refresh_token"):
            public_client.cookies.set("rzs_refresh", "some_token")
            r = public_client.post("/api/v1/auth/logout")
        assert r.status_code == 204

    def test_logout_without_cookie_returns_204(self, public_client):
        r = public_client.post("/api/v1/auth/logout")
        assert r.status_code == 204

    def test_logout_revokes_token(self, public_client):
        with patch("api.db.auth_db.revoke_refresh_token") as mock_revoke:
            public_client.cookies.set("rzs_refresh", "some_raw_token")
            r = public_client.post("/api/v1/auth/logout")
        assert r.status_code == 204
        mock_revoke.assert_called_once()


# ── Dual-auth: X-Api-Key AND Bearer JWT both work ────────────────────────────

class TestDualAuth:
    def test_api_key_accepted_on_protected_endpoint(self, public_client):
        with patch("api.db.postgres.lookup_api_key", return_value={"merchant_id": MERCHANT, "role": "admin", "key_prefix": "rzs_testkey****"}), \
             patch("api.db.postgres.list_api_keys", return_value=[]):
            r = public_client.get("/api/v1/security/keys", headers={"X-Api-Key": "rzs_testkey"})
        assert r.status_code == 200

    def test_bearer_jwt_accepted_on_protected_endpoint(self, public_client):
        token = create_access_token(merchant_id=MERCHANT, user_id=USER_ID, role="admin")
        with patch("api.db.postgres.list_api_keys", return_value=[]):
            r = public_client.get(
                "/api/v1/security/keys",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert r.status_code == 200

    def test_no_auth_returns_401(self, public_client):
        r = public_client.get("/api/v1/security/keys")
        assert r.status_code == 401

    def test_invalid_api_key_returns_401(self, public_client):
        with patch("api.db.postgres.lookup_api_key", return_value=None):
            r = public_client.get("/api/v1/security/keys", headers={"X-Api-Key": "bad_key"})
        assert r.status_code == 401

    def test_invalid_jwt_returns_401(self, public_client):
        r = public_client.get(
            "/api/v1/security/keys",
            headers={"Authorization": "Bearer this.is.not.valid"},
        )
        assert r.status_code == 401

    def test_me_endpoint_returns_merchant_id(self, public_client):
        token = create_access_token(merchant_id=MERCHANT, user_id=USER_ID, role="admin")
        r = public_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["merchant_id"] == MERCHANT
        assert r.json()["role"] == "admin"
        assert r.json()["user_id"] == USER_ID
