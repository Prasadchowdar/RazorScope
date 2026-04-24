"""Plans list endpoint — returns distinct plan IDs seen for a merchant."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from api.auth import get_merchant_id
from api.db import clickhouse
from api.limiter import limiter

router = APIRouter(prefix="/api/v1")


@router.get("/plans")
@limiter.limit("60/minute")
def list_plans(
    request: Request,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
):
    """Return distinct Razorpay plan IDs seen in MRR data for this merchant."""
    return {"plans": clickhouse.list_plans(merchant_id)}
