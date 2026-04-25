"""
MRR Forecast endpoint.

Uses simple OLS linear regression on historical closing MRR to project
3 months forward. No external ML libraries — pure stdlib math.
"""
from __future__ import annotations

import math
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from api.auth import get_merchant_id
from api.db import clickhouse
from api.limiter import limiter

router = APIRouter(prefix="/api/v1")


class ForecastMonth(BaseModel):
    month: str
    closing_mrr_paise: int
    net_new_mrr_paise: int
    is_forecast: bool = True
    confidence_low: int
    confidence_high: int


class ForecastResponse(BaseModel):
    forecasted_months: list[ForecastMonth]
    warning: str = ""


def _ols(xs: list[float], ys: list[float]) -> tuple[float, float, float]:
    """Return (slope, intercept, residual_std) from OLS fit."""
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    ss_xy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    ss_xx = sum((x - mean_x) ** 2 for x in xs)
    slope = ss_xy / ss_xx if ss_xx else 0.0
    intercept = mean_y - slope * mean_x
    residuals = [(y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys)]
    residual_std = math.sqrt(sum(residuals) / max(n - 2, 1))
    return slope, intercept, residual_std


def _add_months(month_str: str, delta: int) -> str:
    """Add delta months to a YYYY-MM string."""
    year, mon = int(month_str[:4]), int(month_str[5:7])
    mon += delta
    while mon > 12:
        mon -= 12
        year += 1
    return f"{year}-{mon:02d}"


@router.get("/mrr/forecast", response_model=ForecastResponse)
@limiter.limit("30/minute")
def mrr_forecast(
    request: Request,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
    months_history: int = Query(default=6, ge=3, le=24),
    months_ahead: int = Query(default=3, ge=1, le=12),
):
    history = clickhouse.mrr_trend_for_forecast(merchant_id, months_history)

    if len(history) < 3:
        return ForecastResponse(
            forecasted_months=[],
            warning="insufficient history — need at least 3 months of data",
        )

    xs = list(range(len(history)))
    ys = [float(m["closing_mrr_paise"]) for m in history]
    slope, intercept, residual_std = _ols(xs, ys)

    ci_half = int(1.96 * residual_std)
    last_closing = int(ys[-1])
    last_month = history[-1]["month"]

    forecasted: list[ForecastMonth] = []
    prev_closing = last_closing
    for i in range(months_ahead):
        x = len(history) + i
        predicted = max(0, int(slope * x + intercept))
        net_new = predicted - prev_closing
        low = max(0, predicted - ci_half)
        high = predicted + ci_half
        forecasted.append(ForecastMonth(
            month=_add_months(last_month, i + 1),
            closing_mrr_paise=predicted,
            net_new_mrr_paise=net_new,
            confidence_low=low,
            confidence_high=high,
        ))
        prev_closing = predicted

    return ForecastResponse(forecasted_months=forecasted)
