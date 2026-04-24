from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.auth import require_admin
from api.limiter import limiter
from api.db import postgres

router = APIRouter(prefix="/api/v1/security", tags=["security"])


class KeyCreate(BaseModel):
    name: str
    role: str = "admin"
    expires_at: Optional[str] = None


class KeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    role: str
    last_used_at: Optional[str]
    expires_at: Optional[str]
    created_at: str
    revoked_at: Optional[str]


# ── API Keys ──────────────────────────────────────────────────────────────────

@router.get("/keys")
@limiter.limit("60/minute")
def list_keys(request: Request, merchant_id: str = Depends(require_admin)):
    keys = postgres.list_api_keys(merchant_id)
    return {"keys": keys}


@router.post("/keys", status_code=201)
@limiter.limit("20/minute")
def create_key(body: KeyCreate, request: Request, merchant_id: str = Depends(require_admin)):
    if body.role not in ("admin", "viewer"):
        raise HTTPException(status_code=422, detail="role must be 'admin' or 'viewer'")
    result = postgres.create_api_key(merchant_id, body.name, body.role, body.expires_at)
    postgres.write_audit_log(
        merchant_id=merchant_id,
        actor_key=_actor(request),
        action="api_key.created",
        resource=f"key:{result['id']}",
        detail={"name": body.name, "role": body.role},
        ip_addr=get_remote_address(request),
    )
    return result


@router.delete("/keys/{key_id}", status_code=204)
@limiter.limit("20/minute")
def revoke_key(key_id: str, request: Request, merchant_id: str = Depends(require_admin)):
    revoked = postgres.revoke_api_key(merchant_id, key_id)
    if not revoked:
        raise HTTPException(status_code=404, detail="key not found or already revoked")
    postgres.write_audit_log(
        merchant_id=merchant_id,
        actor_key=_actor(request),
        action="api_key.revoked",
        resource=f"key:{key_id}",
        ip_addr=get_remote_address(request),
    )


# ── Audit Log ─────────────────────────────────────────────────────────────────

@router.get("/audit")
@limiter.limit("30/minute")
def get_audit_log(request: Request, limit: int = 100, merchant_id: str = Depends(require_admin)):
    if limit > 500:
        limit = 500
    entries = postgres.list_audit_log(merchant_id, limit)
    return {"entries": entries, "count": len(entries)}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _actor(request: Request) -> str:
    return getattr(request.state, "actor", "unknown")
