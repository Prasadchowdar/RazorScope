from datetime import date

import pytest

from worker.cohort import compute_cohort_grid


def _movement(sub_id, period_month, movement_type, amount_paise, merchant_id="m1"):
    return {
        "merchant_id": merchant_id,
        "razorpay_sub_id": sub_id,
        "period_month": period_month,
        "movement_type": movement_type,
        "amount_paise": amount_paise,
    }


# ── empty / degenerate ────────────────────────────────────────────────────────

def test_empty_returns_empty():
    assert compute_cohort_grid([]) == []


def test_no_new_movements_returns_empty():
    rows = [_movement("s1", date(2024, 1, 1), "churn", 0)]
    assert compute_cohort_grid(rows) == []


# ── single cohort, single sub ─────────────────────────────────────────────────

def test_single_sub_period_zero_always_100_pct():
    rows = [_movement("s1", date(2024, 1, 1), "new", 99900)]
    result = compute_cohort_grid(rows, max_periods=3)
    p0 = next(r for r in result if r["period_number"] == 0)
    assert p0["retained_count"] == 1
    assert p0["cohort_size"] == 1
    assert p0["revenue_paise"] == 99900


def test_single_sub_retained_when_no_churn():
    rows = [
        _movement("s1", date(2024, 1, 1), "new", 99900),
        _movement("s1", date(2024, 2, 1), "expansion", 149900),
    ]
    result = compute_cohort_grid(rows, max_periods=3)
    p1 = next(r for r in result if r["period_number"] == 1)
    assert p1["retained_count"] == 1
    assert p1["revenue_paise"] == 149900


def test_churned_sub_not_retained():
    rows = [
        _movement("s1", date(2024, 1, 1), "new", 99900),
        _movement("s1", date(2024, 2, 1), "churn", 0),
    ]
    result = compute_cohort_grid(rows, max_periods=3)
    p1 = next(r for r in result if r["period_number"] == 1)
    assert p1["retained_count"] == 0
    assert p1["revenue_paise"] == 0


# ── forward-fill (no movement in period = carry previous state) ───────────────

def test_forward_fill_active_sub():
    # Sub pays in Jan, no event in Feb → still active in Feb (forward-fill)
    rows = [_movement("s1", date(2024, 1, 1), "new", 99900)]
    result = compute_cohort_grid(rows, max_periods=2)
    p1 = next((r for r in result if r["period_number"] == 1), None)
    if p1:  # only present if Feb is <= today
        assert p1["retained_count"] == 1


def test_forward_fill_churned_stays_churned():
    rows = [
        _movement("s1", date(2024, 1, 1), "new", 99900),
        _movement("s1", date(2024, 2, 1), "churn", 0),
    ]
    result = compute_cohort_grid(rows, max_periods=3)
    p2 = next((r for r in result if r["period_number"] == 2), None)
    if p2:
        assert p2["retained_count"] == 0


# ── multiple subs in same cohort ──────────────────────────────────────────────

def test_two_subs_one_churns():
    rows = [
        _movement("s1", date(2024, 1, 1), "new", 99900),
        _movement("s2", date(2024, 1, 1), "new", 49900),
        _movement("s2", date(2024, 2, 1), "churn", 0),
    ]
    result = compute_cohort_grid(rows, max_periods=3)
    p0 = next(r for r in result if r["period_number"] == 0)
    p1 = next(r for r in result if r["period_number"] == 1)
    assert p0["cohort_size"] == 2
    assert p0["retained_count"] == 2
    assert p1["retained_count"] == 1
    assert p1["revenue_paise"] == 99900


# ── multiple cohorts ──────────────────────────────────────────────────────────

def test_two_cohort_months_separate():
    rows = [
        _movement("s1", date(2024, 1, 1), "new", 99900),
        _movement("s2", date(2024, 2, 1), "new", 49900),
    ]
    result = compute_cohort_grid(rows, max_periods=3)
    cohort_months = {r["cohort_month"] for r in result}
    assert date(2024, 1, 1) in cohort_months
    assert date(2024, 2, 1) in cohort_months

    jan_subs_p0 = next(r for r in result if r["cohort_month"] == date(2024, 1, 1) and r["period_number"] == 0)
    assert jan_subs_p0["cohort_size"] == 1


# ── reactivation ──────────────────────────────────────────────────────────────

def test_reactivated_sub_counted_as_retained():
    rows = [
        _movement("s1", date(2024, 1, 1), "new", 99900),
        _movement("s1", date(2024, 2, 1), "churn", 0),
        _movement("s1", date(2024, 3, 1), "reactivation", 99900),
    ]
    result = compute_cohort_grid(rows, max_periods=3)
    p2 = next((r for r in result if r["period_number"] == 2), None)
    if p2:
        assert p2["retained_count"] == 1
