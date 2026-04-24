"""Unit tests for Razorpay integration endpoints."""
from unittest.mock import patch

from api.db import postgres as pg_db
from api.jwt_utils import create_access_token

MERCHANT = "11111111-1111-1111-1111-111111111111"


def _integration(
    webhook_secret: str = "whsec_test_secret",
    razorpay_key_id: str | None = None,
    has_api_credentials: bool = False,
):
    return {
        "merchant_id": MERCHANT,
        "webhook_secret": webhook_secret,
        "razorpay_key_id": razorpay_key_id,
        "has_api_credentials": has_api_credentials,
    }


class TestGetRazorpayIntegration:
    def test_returns_basic_and_advanced_modes(self, auth_client):
        with patch.object(
            pg_db,
            "get_merchant_razorpay_integration",
            return_value=_integration(),
        ):
            resp = auth_client.get("/api/v1/integrations/razorpay", headers={"X-Api-Key": "any"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["merchant_id"] == MERCHANT
        assert data["mode_basic"]["webhook_url"].endswith(f"/v1/webhooks/razorpay/{MERCHANT}")
        assert data["mode_basic"]["webhook_secret"] == "whsec_test_secret"
        assert data["mode_advanced"]["razorpay_key_id"] == ""
        assert data["mode_advanced"]["has_api_credentials"] is False
        assert data["mode_advanced"]["backfill_ready"] is False

    def test_returns_404_when_merchant_missing(self, auth_client):
        with patch.object(pg_db, "get_merchant_razorpay_integration", return_value=None):
            resp = auth_client.get("/api/v1/integrations/razorpay", headers={"X-Api-Key": "any"})

        assert resp.status_code == 404

    def test_viewer_role_cannot_read_integration(self, public_client):
        token = create_access_token(merchant_id=MERCHANT, user_id=MERCHANT, role="viewer")
        resp = public_client.get(
            "/api/v1/integrations/razorpay",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


class TestSaveRazorpayCredentials:
    def test_saves_credentials_and_unlocks_backfill(self, auth_client):
        with patch.object(pg_db, "upsert_merchant_razorpay_credentials") as save_mock, patch.object(
            pg_db,
            "get_merchant_razorpay_integration",
            return_value=_integration(
                webhook_secret="whsec_saved_secret",
                razorpay_key_id="rzp_live_test",
                has_api_credentials=True,
            ),
        ):
            resp = auth_client.put(
                "/api/v1/integrations/razorpay",
                json={
                    "razorpay_key_id": "rzp_live_test",
                    "razorpay_key_secret": "secret_test_value",
                },
                headers={"X-Api-Key": "any"},
            )

        assert resp.status_code == 200
        save_mock.assert_called_once()
        data = resp.json()
        assert data["mode_advanced"]["razorpay_key_id"] == "rzp_live_test"
        assert data["mode_advanced"]["has_api_credentials"] is True
        assert data["mode_advanced"]["backfill_ready"] is True

    def test_rejects_blank_credentials(self, auth_client):
        resp = auth_client.put(
            "/api/v1/integrations/razorpay",
            json={
                "razorpay_key_id": "   ",
                "razorpay_key_secret": "   ",
            },
            headers={"X-Api-Key": "any"},
        )

        assert resp.status_code == 422
