from typing import Optional

from fastapi import Depends, Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.db import postgres
from api.jwt_utils import decode_access_token

_bearer = HTTPBearer(auto_error=False)


def get_merchant_id(
    request: Request,
    x_api_key: Optional[str] = Header(default=None, alias="X-Api-Key"),
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> str:
    """FastAPI dependency: accepts X-Api-Key header OR Bearer JWT. Returns merchant_id."""
    if x_api_key:
        auth = postgres.lookup_api_key(x_api_key)
        if not auth:
            raise HTTPException(status_code=401, detail="invalid api key")
        request.state.merchant_id = auth["merchant_id"]
        request.state.role = auth["role"]
        request.state.actor = auth["key_prefix"]
        request.state.auth_method = "api_key"
        return auth["merchant_id"]

    if creds and creds.scheme == "Bearer":
        payload = decode_access_token(creds.credentials)
        merchant_id = payload["mid"]
        request.state.merchant_id = merchant_id
        request.state.role = payload.get("role", "member")
        request.state.user_id = payload["sub"]
        request.state.actor = f"user:{payload['sub']}"
        request.state.auth_method = "bearer"
        return merchant_id

    raise HTTPException(status_code=401, detail="authentication required")


def require_admin(
    request: Request,
    merchant_id: str = Depends(get_merchant_id),
) -> str:
    role = getattr(request.state, "role", None)
    if role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="admin access required")
    return merchant_id
