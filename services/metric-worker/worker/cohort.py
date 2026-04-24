"""
Cohort retention computation.

Loads all mrr_movements from ClickHouse for a merchant and computes the
cohort × period retention grid entirely in Python.

Design decisions:
- Cohort month = month of the first 'new' movement for each subscription.
- Retained in period P = last known amount_paise at or before period P > 0.
  (Forward-fill: if no movement in a month, carry the previous state.)
- Written to ClickHouse cohort_retention (ReplacingMergeTree), safe to re-run.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import DefaultDict

log = logging.getLogger(__name__)


def _add_months(d: date, n: int) -> date:
    month = d.month - 1 + n
    return d.replace(year=d.year + month // 12, month=month % 12 + 1, day=1)


def compute_cohort_grid(
    movements: list[dict],
    max_periods: int = 12,
) -> list[dict]:
    """
    Build the cohort retention matrix from raw mrr_movement rows.

    movements: list of dicts with keys:
        merchant_id, razorpay_sub_id, period_month (date),
        movement_type (str), amount_paise (int)

    Returns list of cohort_retention rows ready for ClickHouse.
    """
    if not movements:
        return []

    merchant_id = movements[0]["merchant_id"]

    # ── Step 1: cohort month per sub (month of first 'new' movement) ──────────
    cohort_month_by_sub: dict[str, date] = {}
    for m in movements:
        if m["movement_type"] == "new":
            sub = m["razorpay_sub_id"]
            pm = m["period_month"]
            if sub not in cohort_month_by_sub or pm < cohort_month_by_sub[sub]:
                cohort_month_by_sub[sub] = pm

    if not cohort_month_by_sub:
        log.debug("cohort: no 'new' movements for merchant %s", merchant_id)
        return []

    # ── Step 2: latest amount_paise per (sub, period_month) ───────────────────
    # Sort by period_month so later entries overwrite earlier ones in same month
    sub_timeline: DefaultDict[str, dict[date, int]] = defaultdict(dict)
    for m in sorted(movements, key=lambda x: x["period_month"]):
        sub_timeline[m["razorpay_sub_id"]][m["period_month"]] = m["amount_paise"]

    # ── Step 3: group subs by cohort month ────────────────────────────────────
    cohort_to_subs: DefaultDict[date, list[str]] = defaultdict(list)
    for sub, cm in cohort_month_by_sub.items():
        cohort_to_subs[cm].append(sub)

    now_month = datetime.now(timezone.utc).date().replace(day=1)
    rows: list[dict] = []

    for cohort_month in sorted(cohort_to_subs):
        subs = cohort_to_subs[cohort_month]
        cohort_size = len(subs)

        for period_number in range(max_periods + 1):
            period_month = _add_months(cohort_month, period_number)
            if period_month > now_month:
                break

            retained_count = 0
            revenue_paise = 0

            for sub in subs:
                history = sub_timeline.get(sub, {})
                past = [pm for pm in history if pm <= period_month]
                if not past:
                    continue
                last_mrr = history[max(past)]
                if last_mrr > 0:
                    retained_count += 1
                    revenue_paise += last_mrr

            rows.append({
                "merchant_id": merchant_id,
                "cohort_month": cohort_month,
                "period_month": period_month,
                "period_number": period_number,
                "cohort_size": cohort_size,
                "retained_count": retained_count,
                "revenue_paise": revenue_paise,
            })

    log.info(
        "cohort: computed %d rows for merchant=%s across %d cohort months",
        len(rows), merchant_id, len(cohort_to_subs),
    )
    return rows
