"""
MRR Dashboard endpoints.

All endpoints require X-Api-Key header → resolves to merchant_id.
Amounts are always returned in paise (Int64). Callers divide by 100 for rupees.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from api.auth import get_merchant_id
from api.db import clickhouse
from api.limiter import limiter

router = APIRouter(prefix="/api/v1")

_MOVEMENT_TYPES = ["new", "expansion", "contraction", "churn", "reactivation"]


def _parse_month(month_str: str) -> date:
    """Parse 'YYYY-MM' string → first day of that month as date."""
    if not re.fullmatch(r"\d{4}-\d{2}", month_str):
        raise HTTPException(status_code=422, detail="month must be YYYY-MM")
    year, mon = int(month_str[:4]), int(month_str[5:])
    if not (1 <= mon <= 12):
        raise HTTPException(status_code=422, detail="month out of range")
    return date(year, mon, 1)


def _current_month_str() -> str:
    today = date.today()
    return f"{today.year}-{today.month:02d}"


@router.get("/mrr/summary")
@limiter.limit("60/minute")
def mrr_summary(
    request: Request,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
    month: str = Query(default=None, description="YYYY-MM, defaults to current month"),
    plan_id: str = Query(default=None),
    country: str = Query(default=None, description="ISO 3166-1 alpha-2 country code"),
    source: str = Query(default=None, description="Acquisition channel"),
    payment_method: str = Query(default=None, description="Payment method"),
):
    mo = _parse_month(month or _current_month_str())

    opening = clickhouse.mrr_opening(merchant_id, mo, plan_id=plan_id, country=country, source=source, payment_method=payment_method)
    by_type = clickhouse.mrr_movements_by_type(merchant_id, mo, plan_id=plan_id, country=country, source=source, payment_method=payment_method)

    movements = {t: by_type.get(t, 0) for t in _MOVEMENT_TYPES}
    net = sum(movements.values())

    return {
        "month": mo.strftime("%Y-%m"),
        "opening_mrr_paise": opening,
        "closing_mrr_paise": opening + net,
        "net_new_mrr_paise": net,
        "movements": movements,
    }


@router.get("/mrr/trend")
@limiter.limit("60/minute")
def mrr_trend(
    request: Request,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
    months: int = Query(default=12, ge=1, le=36),
    plan_id: str = Query(default=None),
    country: str = Query(default=None),
    source: str = Query(default=None),
    payment_method: str = Query(default=None),
):
    today = date.today()
    first_day_this_month = today.replace(day=1)
    start = (first_day_this_month - timedelta(days=1)).replace(day=1)
    for _ in range(months - 2):
        start = (start - timedelta(days=1)).replace(day=1)

    seg = dict(plan_id=plan_id, country=country, source=source, payment_method=payment_method)
    rows = clickhouse.mrr_trend(merchant_id, start, **seg)

    by_month: dict[str, dict[str, int]] = {}
    for r in rows:
        key = r["period_month"].strftime("%Y-%m") if hasattr(r["period_month"], "strftime") else str(r["period_month"])[:7]
        by_month.setdefault(key, {t: 0 for t in _MOVEMENT_TYPES})
        by_month[key][r["movement_type"]] = r["delta"]

    opening = clickhouse.mrr_opening(merchant_id, start, **seg)
    series = []
    cur = start
    for _ in range(months):
        key = cur.strftime("%Y-%m")
        mv = by_month.get(key, {t: 0 for t in _MOVEMENT_TYPES})
        net = sum(mv.values())
        series.append({
            "month": key,
            "opening_mrr_paise": opening,
            "closing_mrr_paise": opening + net,
            "net_new_mrr_paise": net,
            "movements": mv,
        })
        opening += net
        if cur.month == 12:
            cur = cur.replace(year=cur.year + 1, month=1)
        else:
            cur = cur.replace(month=cur.month + 1)

    return {"months": series}


@router.get("/mrr/movements")
@limiter.limit("60/minute")
def mrr_movements(
    request: Request,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
    month: str = Query(default=None, description="YYYY-MM, defaults to current month"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    plan_id: str = Query(default=None),
    country: str = Query(default=None),
    source: str = Query(default=None),
    payment_method: str = Query(default=None),
):
    """Individual MRR movement records for a month, sorted by |delta| descending."""
    mo = _parse_month(month or _current_month_str())
    offset = (page - 1) * page_size
    rows = clickhouse.mrr_movement_rows(
        merchant_id, mo, limit=page_size, offset=offset,
        plan_id=plan_id, country=country, source=source, payment_method=payment_method,
    )

    for r in rows:
        if hasattr(r.get("period_month"), "strftime"):
            r["period_month"] = r["period_month"].strftime("%Y-%m")
        r["voluntary"] = bool(r["voluntary"])

    return {"month": mo.strftime("%Y-%m"), "page": page, "page_size": page_size, "movements": rows}
