"""
Subscriber detail endpoint.

Returns the full MRR movement timeline for one subscription, plus
a CSV export endpoint for bulk movements data.
"""
from __future__ import annotations

import csv
import io
import re
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from api.auth import get_merchant_id
from api.db import clickhouse
from api.limiter import limiter

router = APIRouter(prefix="/api/v1")


def _parse_month(s: str) -> date:
    if not re.fullmatch(r"\d{4}-\d{2}", s):
        raise HTTPException(status_code=422, detail="month must be YYYY-MM")
    year, mon = int(s[:4]), int(s[5:])
    if not (1 <= mon <= 12):
        raise HTTPException(status_code=422, detail="month out of range")
    return date(year, mon, 1)


def _current_month_str() -> str:
    today = date.today()
    return f"{today.year}-{today.month:02d}"


@router.get("/subscribers/{sub_id}")
@limiter.limit("60/minute")
def subscriber_detail(
    request: Request,
    sub_id: str,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
):
    """
    Full MRR movement timeline for a single subscription.

    Returns all historical movements oldest-first so the caller can
    reconstruct an MRR contribution curve.
    """
    rows = clickhouse.subscriber_timeline(merchant_id, sub_id)
    if not rows:
        raise HTTPException(status_code=404, detail="subscriber not found")

    # Serialize date fields
    serialized = []
    for r in rows:
        row = dict(r)
        if hasattr(row.get("period_month"), "strftime"):
            row["period_month"] = row["period_month"].strftime("%Y-%m")
        row["voluntary"] = bool(row["voluntary"])
        serialized.append(row)

    first = serialized[0]
    return {
        "razorpay_sub_id": sub_id,
        "customer_id": first["customer_id"],
        "plan_id": first["plan_id"],
        "current_amount_paise": serialized[-1]["amount_paise"],
        "timeline": serialized,
    }


@router.get("/mrr/movements/export")
@limiter.limit("10/minute")
def export_movements_csv(
    request: Request,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
    month: str = Query(default=None, description="YYYY-MM, defaults to current month"),
    plan_id: str = Query(default=None, description="Filter to a specific plan"),
):
    """
    Download all MRR movements for a month as a CSV file.

    Rate-limited to 10/minute (file downloads are expensive).
    """
    mo = _parse_month(month or _current_month_str())
    rows = clickhouse.mrr_movement_rows_all(merchant_id, mo, plan_id=plan_id)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "razorpay_sub_id", "customer_id", "plan_id", "movement_type",
        "amount_paise", "prev_amount_paise", "delta_paise", "voluntary", "period_month",
    ])
    for r in rows:
        pm = r["period_month"]
        period = pm.strftime("%Y-%m") if hasattr(pm, "strftime") else str(pm)[:7]
        writer.writerow([
            r["razorpay_sub_id"], r["customer_id"], r["plan_id"], r["movement_type"],
            r["amount_paise"], r["prev_amount_paise"], r["delta_paise"],
            int(bool(r["voluntary"])), period,
        ])

    output.seek(0)
    filename = f"mrr_movements_{mo.strftime('%Y-%m')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
