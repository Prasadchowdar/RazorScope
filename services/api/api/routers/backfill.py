"""
Backfill job endpoints.

Allow a merchant to trigger a historical data import from Razorpay.
The actual processing is done by the metric-worker's backfill scheduler.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from api.auth import require_admin
from api.db import postgres
from api.limiter import limiter

router = APIRouter(prefix="/api/v1")


def _parse_month_to_date(s: str) -> date:
    if not re.fullmatch(r"\d{4}-\d{2}", s):
        raise HTTPException(status_code=422, detail="date must be YYYY-MM")
    year, mon = int(s[:4]), int(s[5:])
    if not (1 <= mon <= 12):
        raise HTTPException(status_code=422, detail="month out of range")
    return date(year, mon, 1)


def _serialize_job(row: dict) -> dict:
    """Convert DB row to API response dict (date → string, None preserved)."""
    result = dict(row)
    for field in ("from_date", "to_date", "created_at", "completed_at"):
        v = result.get(field)
        if v is not None and hasattr(v, "isoformat"):
            result[field] = v.isoformat()
    return result


class BackfillRequest(BaseModel):
    from_date: str  # YYYY-MM
    to_date: str    # YYYY-MM


@router.post("/backfill", status_code=201)
@limiter.limit("20/minute")
def create_backfill_job(
    request: Request,
    body: BackfillRequest,
    merchant_id: Annotated[str, Depends(require_admin)],
):
    """
    Create a new backfill job to import historical Razorpay subscription data.

    The metric-worker will pick up the job within 60 seconds and begin processing.
    Poll GET /api/v1/backfill/{job_id} to track progress.
    """
    from_date = _parse_month_to_date(body.from_date)
    to_date = _parse_month_to_date(body.to_date)

    if to_date < from_date:
        raise HTTPException(status_code=422, detail="to_date must be >= from_date")

    integration = postgres.get_merchant_razorpay_integration(merchant_id)
    if not integration or not integration.get("has_api_credentials"):
        raise HTTPException(
            status_code=409,
            detail="connect Razorpay API credentials before running backfill",
        )

    job_id = postgres.create_backfill_job(
        merchant_id,
        from_date.isoformat(),
        to_date.isoformat(),
    )
    return {"job_id": job_id, "status": "pending"}


@router.get("/backfill")
@limiter.limit("30/minute")
def list_backfill_jobs(
    request: Request,
    merchant_id: Annotated[str, Depends(require_admin)],
):
    """List all backfill jobs for the authenticated merchant, newest first."""
    rows = postgres.list_backfill_jobs(merchant_id)
    return {"jobs": [_serialize_job(r) for r in rows]}


@router.get("/backfill/{job_id}")
@limiter.limit("60/minute")
def get_backfill_job(
    request: Request,
    job_id: str,
    merchant_id: Annotated[str, Depends(require_admin)],
):
    """Get status and progress of a specific backfill job."""
    row = postgres.get_backfill_job(merchant_id, job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="job not found")
    return _serialize_job(row)
