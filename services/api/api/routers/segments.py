"""Segmentation dimension values — distinct countries, sources, payment methods, plans."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from api.auth import get_merchant_id
from api.db import clickhouse as ch_db
from api.limiter import limiter

router = APIRouter(prefix="/api/v1")


@router.get("/segments")
@limiter.limit("60/minute")
def list_segments(
    request: Request,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
):
    """Return distinct non-empty values for each segmentation dimension."""
    return ch_db.list_segment_values(merchant_id)
