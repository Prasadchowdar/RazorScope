"""
Benchmarks endpoint.

Computes merchant metrics for the given month, then scores each metric
against industry percentile tables and returns the comparison.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from api.auth import get_merchant_id
from api.benchmarks import score
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


@router.get("/benchmarks")
@limiter.limit("30/minute")
def benchmarks(
    request: Request,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
    month: str = Query(default=None, description="YYYY-MM, defaults to current month"),
):
    """
    Score merchant metrics against industry SaaS benchmarks.

    Returns a list of scored metrics, each with:
    - merchant_value: the computed metric for the requested month
    - percentile: estimated industry percentile (0–100)
    - label: "top quartile" | "above median" | "below median" | "bottom quartile"
    - industry_p10/p25/p50/p75/p90: benchmark breakpoints for reference

    Benchmark data: ChartMogul 2024, SaaS Capital Index, OpenView (Indian B2B SaaS).
    """
    mo = _parse_month(month or _current_month())

    # Gather merchant metrics
    opening_mrr = clickhouse.mrr_opening(merchant_id, mo)
    by_type = clickhouse.mrr_movements_by_type(merchant_id, mo)
    churn_data = clickhouse.churn_stats(merchant_id, mo)
    active_subs = postgres.active_subscriber_count(merchant_id)

    net_movement = sum(by_type.values())
    closing_mrr = opening_mrr + net_movement

    # Derived rates
    mrr_growth = (
        round((closing_mrr - opening_mrr) / opening_mrr * 100, 2)
        if opening_mrr else 0.0
    )
    nrr = round(closing_mrr / opening_mrr * 100, 1) if opening_mrr else 0.0
    arpu = closing_mrr / active_subs if active_subs else 0.0

    churned = churn_data["churned_subscribers"]
    at_start = churn_data["active_at_period_start"]
    customer_churn = round(churned / at_start * 100, 2) if at_start else 0.0

    rev_churn = (
        round(churn_data["churn_mrr_paise"] / opening_mrr * 100, 2)
        if opening_mrr else 0.0
    )

    scored = [
        score("mrr_growth_rate", mrr_growth),
        score("customer_churn_rate", customer_churn),
        score("revenue_churn_rate", rev_churn),
        score("nrr_pct", nrr),
        score("arpu_paise", arpu),
    ]

    return {
        "month": mo.strftime("%Y-%m"),
        "benchmarks": scored,
        "data_source": "ChartMogul 2024 SaaS Benchmarks + SaaS Capital Index (Indian B2B SaaS)",
    }
