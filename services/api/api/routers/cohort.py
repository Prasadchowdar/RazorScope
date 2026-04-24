"""
Cohort retention endpoint.

Returns a grid: rows = cohort months, columns = period numbers (0..N).
Each cell has cohort_size, retained_count, and retention_pct.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from api.auth import get_merchant_id
from api.db import clickhouse
from api.limiter import limiter

router = APIRouter(prefix="/api/v1")


@router.get("/cohort")
@limiter.limit("30/minute")
def cohort_retention(
    request: Request,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
    months: int = Query(default=12, ge=1, le=24, description="Number of cohort months to return"),
):
    """
    Cohort retention grid for the last N cohort months.

    Response shape:
    {
      "cohorts": [
        {
          "cohort_month": "2024-01",
          "cohort_size": 42,
          "periods": [
            {"period_number": 0, "period_month": "2024-01", "retained_count": 42,
             "retention_pct": 100.0, "revenue_paise": 1234567},
            {"period_number": 1, "period_month": "2024-02", ...},
            ...
          ]
        },
        ...
      ]
    }
    """
    rows = clickhouse.cohort_grid(merchant_id, max_cohort_months=months)

    # Group by cohort_month
    by_cohort: dict[str, dict] = {}
    periods_by_cohort: dict[str, list] = defaultdict(list)

    for r in rows:
        cm = r["cohort_month"]
        cm_str = cm.strftime("%Y-%m") if hasattr(cm, "strftime") else str(cm)[:7]
        pm_str = r["period_month"].strftime("%Y-%m") if hasattr(r["period_month"], "strftime") else str(r["period_month"])[:7]

        if cm_str not in by_cohort:
            by_cohort[cm_str] = {
                "cohort_month": cm_str,
                "cohort_size": int(r["cohort_size"]),
            }
        else:
            # cohort_size is the same for all periods in a cohort — use max for safety
            by_cohort[cm_str]["cohort_size"] = max(by_cohort[cm_str]["cohort_size"], int(r["cohort_size"]))

        cohort_size = by_cohort[cm_str]["cohort_size"]
        retained = int(r["retained_count"])
        periods_by_cohort[cm_str].append({
            "period_number": int(r["period_number"]),
            "period_month": pm_str,
            "retained_count": retained,
            "retention_pct": round(retained / cohort_size * 100, 1) if cohort_size else 0.0,
            "revenue_paise": int(r["revenue_paise"]),
        })

    cohorts = []
    for cm_str in sorted(by_cohort.keys()):
        cohorts.append({
            **by_cohort[cm_str],
            "periods": sorted(periods_by_cohort[cm_str], key=lambda x: x["period_number"]),
        })

    return {"cohorts": cohorts}
