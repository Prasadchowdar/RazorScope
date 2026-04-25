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

from pydantic import BaseModel

from api.auth import get_merchant_id
from api.db import clickhouse, postgres
from api.limiter import limiter

router = APIRouter(prefix="/api/v1")


class RiskScore(BaseModel):
    razorpay_sub_id: str
    customer_id: str
    plan_id: str
    risk_score: int
    risk_label: str
    factors: list[str]


def _compute_risk(row: dict, failure_count: int) -> tuple[int, str, list[str]]:
    score = 0
    factors: list[str] = []
    if row["has_contraction_90d"]:
        score += 40
        factors.append("contraction_in_90d")
    if failure_count > 1:
        score += 25
        factors.append("payment_failures_gt1")
    if row["tenure_months"] > 12:
        score += 20
        factors.append("tenure_over_12m")
    peak = row["peak_mrr_paise"]
    current = row["current_mrr_paise"]
    if peak > 0 and current < peak * 0.5:
        score += 15
        factors.append("mrr_below_50pct_peak")
    score = min(score, 100)
    label = "high" if score >= 65 else ("medium" if score >= 35 else "low")
    return score, label, factors


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


@router.get("/subscribers/risk-scores")
@limiter.limit("30/minute")
def subscriber_risk_scores(
    request: Request,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
    limit: int = Query(default=50, ge=1, le=200),
):
    """
    Compute a churn risk score (0-100) for the top N active subscribers.
    Deterministic formula: contraction_90d (+40), payment_failures>1 (+25),
    tenure>12m (+20), MRR<50% of peak (+15). No LLM involved.
    """
    rows = clickhouse.subscriber_risk_factors(merchant_id, limit)
    scores: list[RiskScore] = []
    for row in rows:
        failures = clickhouse.subscriber_payment_failures(merchant_id, row["razorpay_sub_id"])
        score, label, factors = _compute_risk(row, failures)
        scores.append(RiskScore(
            razorpay_sub_id=row["razorpay_sub_id"],
            customer_id=str(row["customer_id"]),
            plan_id=str(row["plan_id"]),
            risk_score=score,
            risk_label=label,
            factors=factors,
        ))
    scores.sort(key=lambda s: s.risk_score, reverse=True)
    return {"scores": [s.model_dump() for s in scores], "total": len(scores)}


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
