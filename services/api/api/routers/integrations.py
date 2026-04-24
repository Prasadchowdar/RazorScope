from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator

from api.auth import require_admin
from api.config import Config
from api.db import postgres
from api.limiter import limiter

router = APIRouter(prefix="/api/v1/integrations", tags=["integrations"])


def _build_webhook_url(merchant_id: str) -> str:
    base = Config.WEBHOOK_BASE_URL.rstrip("/")
    return f"{base}/v1/webhooks/razorpay/{merchant_id}"


def _serialize_integration(merchant_id: str, integration: dict) -> dict:
    has_api_credentials = bool(integration["has_api_credentials"])
    return {
        "merchant_id": merchant_id,
        "mode_basic": {
            "webhook_url": _build_webhook_url(merchant_id),
            "webhook_secret": integration["webhook_secret"],
        },
        "mode_advanced": {
            "razorpay_key_id": integration.get("razorpay_key_id") or "",
            "has_api_credentials": has_api_credentials,
            "backfill_ready": has_api_credentials,
        },
    }


class RazorpayCredentialsRequest(BaseModel):
    razorpay_key_id: str
    razorpay_key_secret: str

    @field_validator("razorpay_key_id", "razorpay_key_secret")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


@router.get("/razorpay")
@limiter.limit("60/minute")
def get_razorpay_integration(
    request: Request,
    merchant_id: Annotated[str, Depends(require_admin)],
):
    integration = postgres.get_merchant_razorpay_integration(merchant_id)
    if not integration:
        raise HTTPException(status_code=404, detail="merchant not found")
    return _serialize_integration(merchant_id, integration)


@router.put("/razorpay")
@limiter.limit("20/minute")
def save_razorpay_credentials(
    request: Request,
    body: RazorpayCredentialsRequest,
    merchant_id: Annotated[str, Depends(require_admin)],
):
    postgres.upsert_merchant_razorpay_credentials(
        merchant_id=merchant_id,
        key_id=body.razorpay_key_id,
        key_secret=body.razorpay_key_secret,
        encryption_key=Config.RAZORPAY_SECRET_ENCRYPTION_KEY,
    )
    integration = postgres.get_merchant_razorpay_integration(merchant_id)
    if not integration:
        raise HTTPException(status_code=404, detail="merchant not found")
    return _serialize_integration(merchant_id, integration)
