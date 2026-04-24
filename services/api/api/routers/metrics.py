"""
Subscription metrics endpoints — ARPU, churn rate, NRR, plan breakdown.

All amounts in paise. Rates as floats 0–100.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from api.auth import get_merchant_id
from api.db import clickhouse, postgres
from api.limiter import limiter

router = APIRouter(prefix="/api/v1")


def _parse_month(s: str) -> date:
    if not re.fullmatch(r"\d{4}-\d{2}", s):
        raise HTTPException(status_code=422, detail="month must be YYYY-MM")
    year, mon = int(s[:4]), int(s[5:])
    if not (1 <= mon <= 12):
        raise HTTPException(status_code=422, detail="month out of range")
    return date(year, mon, 1)


def _current_month() -> str:
    d = date.today()
    return f"{d.year}-{d.month:02d}"


def _safe_div(num: float, den: float) -> float:
    return round(num / den, 4) if den else 0.0


@router.get("/metrics/overview")
@limiter.limit("60/minute")
def metrics_overview(
    request: Request,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
    month: str = Query(default=None, description="YYYY-MM, defaults to current month"),
    plan_id: str = Query(default=None),
    country: str = Query(default=None),
    source: str = Query(default=None),
    payment_method: str = Query(default=None),
):
    mo = _parse_month(month or _current_month())
    seg = dict(plan_id=plan_id, country=country, source=source, payment_method=payment_method)

    active_subs = postgres.active_subscriber_count(merchant_id)
    opening_mrr = clickhouse.mrr_opening(merchant_id, mo, **seg)
    by_type = clickhouse.mrr_movements_by_type(merchant_id, mo, **seg)
    churn = clickhouse.churn_stats(merchant_id, mo, **seg)

    net_movement = sum(by_type.values())
    closing_mrr = opening_mrr + net_movement

    arpu_paise = int(closing_mrr / active_subs) if active_subs else 0

    customer_churn_rate = round(
        _safe_div(churn["churned_subscribers"], churn["active_at_period_start"]) * 100, 2
    )
    revenue_churn_rate = round(
        _safe_div(churn["churn_mrr_paise"], opening_mrr) * 100, 2
    ) if opening_mrr else 0.0

    nrr_pct = round(_safe_div(closing_mrr, opening_mrr) * 100, 1) if opening_mrr else 0.0

    monthly_churn = customer_churn_rate / 100
    ltv_months = round(min(1 / monthly_churn, 120), 1) if monthly_churn > 0 else None

    return {
        "month": mo.strftime("%Y-%m"),
        "active_subscribers": active_subs,
        "new_subscribers": churn["new_subscribers"],
        "churned_subscribers": churn["churned_subscribers"],
        "reactivated_subscribers": churn["reactivated_subscribers"],
        "arpu_paise": arpu_paise,
        "customer_churn_rate": customer_churn_rate,
        "revenue_churn_rate": revenue_churn_rate,
        "nrr_pct": nrr_pct,
        "ltv_months": ltv_months,
        "opening_mrr_paise": opening_mrr,
        "closing_mrr_paise": closing_mrr,
    }


@router.get("/metrics/plans")
@limiter.limit("60/minute")
def metrics_plans(
    request: Request,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
    month: str = Query(default=None, description="YYYY-MM, defaults to current month"),
):
    mo = _parse_month(month or _current_month())
    plans = clickhouse.plan_mrr_breakdown(merchant_id, mo)

    total_mrr = sum(abs(p["net_mrr_delta_paise"]) for p in plans)
    for p in plans:
        p["pct_of_total"] = round(
            abs(p["net_mrr_delta_paise"]) / total_mrr * 100, 1
        ) if total_mrr else 0.0

    return {
        "month": mo.strftime("%Y-%m"),
        "total_mrr_paise": total_mrr,
        "plans": plans,
    }
