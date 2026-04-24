from __future__ import annotations

from typing import Optional

import bcrypt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, field_validator
from slowapi.util import get_remote_address

from api.auth import get_merchant_id
from api.config import Config
from api.db import auth_db
from api.jwt_utils import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_token,
)
from api.limiter import limiter

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _build_webhook_url(merchant_id: str) -> str:
    base = Config.WEBHOOK_BASE_URL.rstrip("/")
    return f"{base}/v1/webhooks/razorpay/{merchant_id}"


# ── Pydantic models ───────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    company_name: str
    name: str
    email: EmailStr
    password: str
    razorpay_key_id: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v

    @field_validator("company_name", "name")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v.strip()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key=Config.REFRESH_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        secure=Config.REFRESH_COOKIE_SECURE,
        samesite="lax",
        max_age=Config.JWT_REFRESH_EXPIRE_DAYS * 24 * 3600,
        path="/api/v1/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=Config.REFRESH_COOKIE_NAME,
        path="/api/v1/auth",
    )


def _issue_tokens(
    response: Response,
    user: dict,
    request: Request,
) -> dict:
    access_token = create_access_token(
        merchant_id=user["merchant_id"],
        user_id=user["id"],
        role=user["role"],
    )
    raw_refresh = generate_refresh_token()
    auth_db.store_refresh_token(
        user_id=user["id"],
        merchant_id=user["merchant_id"],
        token_hash=hash_token(raw_refresh),
        user_agent=request.headers.get("user-agent"),
        ip_addr=get_remote_address(request),
    )
    _set_refresh_cookie(response, raw_refresh)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "merchant_id": user["merchant_id"],
        "user_id": user["id"],
        "name": user.get("name") or "",
        "email": user["email"],
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register", status_code=201)
@limiter.limit("5/minute")
def register(body: RegisterRequest, request: Request, response: Response):
    existing = auth_db.find_user_by_email(body.email)
    if existing:
        raise HTTPException(status_code=409, detail="email already registered")

    pw_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()

    result = auth_db.create_merchant_and_user(
        company_name=body.company_name,
        user_name=body.name,
        email=body.email,
        password_hash=pw_hash,
        razorpay_key_id=body.razorpay_key_id or None,
    )

    user = {
        "id": result["user_id"],
        "merchant_id": result["merchant_id"],
        "role": "owner",
        "name": body.name,
        "email": body.email,
    }
    tokens = _issue_tokens(response, user, request)

    return {
        **tokens,
        "api_key": result["raw_api_key"],
        "webhook_secret": result["raw_webhook_secret"],
        "webhook_url": _build_webhook_url(result["merchant_id"]),
    }


@router.post("/login")
@limiter.limit("10/minute")
def login(body: LoginRequest, request: Request, response: Response):
    user = auth_db.find_user_by_email(body.email)
    invalid = HTTPException(status_code=401, detail="invalid credentials")

    if not user or not user.get("password_hash"):
        raise invalid
    if not user.get("is_active"):
        raise invalid
    if not bcrypt.checkpw(body.password.encode(), user["password_hash"].encode()):
        raise invalid

    return _issue_tokens(response, user, request)


@router.post("/refresh")
@limiter.limit("30/minute")
def refresh(
    request: Request,
    response: Response,
    rzs_refresh: Optional[str] = Cookie(default=None),
):
    if not rzs_refresh:
        raise HTTPException(status_code=401, detail="no refresh token")

    record = auth_db.lookup_refresh_token(hash_token(rzs_refresh))
    if not record:
        raise HTTPException(status_code=401, detail="invalid or expired refresh token")
    if not record.get("is_active"):
        raise HTTPException(status_code=401, detail="invalid or expired refresh token")

    new_raw = generate_refresh_token()
    auth_db.rotate_refresh_token(
        old_hash=hash_token(rzs_refresh),
        new_hash=hash_token(new_raw),
        user_id=record["user_id"],
        merchant_id=record["merchant_id"],
        user_agent=request.headers.get("user-agent"),
        ip_addr=get_remote_address(request),
    )
    _set_refresh_cookie(response, new_raw)

    # We don't have full user data here — build minimal payload for token
    access_token = create_access_token(
        merchant_id=record["merchant_id"],
        user_id=record["user_id"],
        role=record["role"],
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    rzs_refresh: Optional[str] = Cookie(default=None),
):
    if rzs_refresh:
        auth_db.revoke_refresh_token(hash_token(rzs_refresh))
    _clear_refresh_cookie(response)


@router.get("/me")
def me(request: Request, merchant_id: str = Depends(get_merchant_id)):
    return {
        "merchant_id": merchant_id,
        "actor": getattr(request.state, "actor", None),
        "role": getattr(request.state, "role", None),
        "user_id": getattr(request.state, "user_id", None),
    }
