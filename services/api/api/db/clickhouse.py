"""
ClickHouse read queries for the Dashboard API.

All queries scope to merchant_id explicitly (ClickHouse has no RLS).
mrr_movements uses ReplacingMergeTree — always query with FINAL.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Optional

import clickhouse_connect

log = logging.getLogger(__name__)

_client: Optional[clickhouse_connect.driver.Client] = None


def init_client(host: str, port: int, user: str, password: str, database: str) -> None:
    global _client
    _client = clickhouse_connect.get_client(
        host=host, port=port,
        username=user, password=password,
        database=database,
    )
    log.info("clickhouse client ready")


def _ch():
    if _client is None:
        raise RuntimeError("clickhouse client not initialized")
    return _client


def _segment_clause(
    plan_id: str | None = None,
    country: str | None = None,
    source: str | None = None,
    payment_method: str | None = None,
) -> tuple[str, dict]:
    """Build an extra WHERE fragment + params for optional segmentation filters."""
    parts, params = [], {}
    if plan_id:
        parts.append(" AND plan_id = {seg_plan:String}")
        params["seg_plan"] = plan_id
    if country:
        parts.append(" AND country = {seg_country:String}")
        params["seg_country"] = country
    if source:
        parts.append(" AND source = {seg_source:String}")
        params["seg_source"] = source
    if payment_method:
        parts.append(" AND payment_method = {seg_pm:String}")
        params["seg_pm"] = payment_method
    return "".join(parts), params


def list_segment_values(merchant_id: str) -> dict:
    """Return distinct non-empty values for each segmentation dimension."""
    ch = _ch()

    def _distinct(col: str) -> list[str]:
        result = ch.query(
            f"SELECT DISTINCT {col} FROM mrr_movements FINAL "
            f"WHERE merchant_id = {{mid:String}} AND {col} != '' ORDER BY {col}",
            parameters={"mid": merchant_id},
        )
        return [row[0] for row in result.result_rows]

    return {
        "plans":           list_plans(merchant_id),
        "countries":       _distinct("country"),
        "sources":         _distinct("source"),
        "payment_methods": _distinct("payment_method"),
    }


def list_plans(merchant_id: str) -> list[str]:
    """Distinct non-empty plan_ids seen for this merchant, sorted."""
    result = _ch().query(
        "SELECT DISTINCT plan_id FROM mrr_movements FINAL "
        "WHERE merchant_id = {mid:String} AND plan_id != '' "
        "ORDER BY plan_id ASC",
        parameters={"mid": merchant_id},
    )
    return [row[0] for row in result.result_rows]


def mrr_opening(
    merchant_id: str, month_start: date,
    plan_id: str | None = None, country: str | None = None,
    source: str | None = None, payment_method: str | None = None,
) -> int:
    """Sum of all delta_paise before the given month — this is opening MRR."""
    extra, ep = _segment_clause(plan_id, country, source, payment_method)
    result = _ch().query(
        f"SELECT sum(delta_paise) FROM mrr_movements FINAL "
        f"WHERE merchant_id = {{mid:String}} AND period_month < {{mo:Date}}{extra}",
        parameters={"mid": merchant_id, "mo": month_start, **ep},
    )
    val = result.first_row[0]
    return int(val) if val else 0


def mrr_movements_by_type(
    merchant_id: str, month_start: date,
    plan_id: str | None = None, country: str | None = None,
    source: str | None = None, payment_method: str | None = None,
) -> dict[str, int]:
    """Sum of delta_paise grouped by movement_type for the given month."""
    extra, ep = _segment_clause(plan_id, country, source, payment_method)
    result = _ch().query(
        f"SELECT movement_type, sum(delta_paise) FROM mrr_movements FINAL "
        f"WHERE merchant_id = {{mid:String}} AND period_month = {{mo:Date}}{extra} "
        f"GROUP BY movement_type",
        parameters={"mid": merchant_id, "mo": month_start, **ep},
    )
    return {row[0]: int(row[1]) for row in result.result_rows}


def mrr_trend(
    merchant_id: str, start_month: date,
    plan_id: str | None = None, country: str | None = None,
    source: str | None = None, payment_method: str | None = None,
) -> list[dict]:
    """Per-month, per-movement-type delta from start_month to present."""
    extra, ep = _segment_clause(plan_id, country, source, payment_method)
    result = _ch().query(
        f"SELECT period_month, movement_type, sum(delta_paise) as delta "
        f"FROM mrr_movements FINAL "
        f"WHERE merchant_id = {{mid:String}} AND period_month >= {{sm:Date}}{extra} "
        f"GROUP BY period_month, movement_type "
        f"ORDER BY period_month ASC",
        parameters={"mid": merchant_id, "sm": start_month, **ep},
    )
    return [
        {"period_month": row[0], "movement_type": row[1], "delta": int(row[2])}
        for row in result.result_rows
    ]


def churn_stats(
    merchant_id: str, month_start: date,
    plan_id: str | None = None, country: str | None = None,
    source: str | None = None, payment_method: str | None = None,
) -> dict:
    """
    Returns for a given month:
      - new_subscribers: count of distinct subs with a 'new' movement
      - churned_subscribers: count of distinct subs with a 'churn' movement
      - active_at_period_start: count of subs active at end of prev month (for churn rate denominator)
      - churn_mrr_paise: absolute MRR lost to churn (positive number)
    """
    ch = _ch()
    extra, ep = _segment_clause(plan_id, country, source, payment_method)

    # new + churned in this month
    counts = ch.query(
        f"SELECT movement_type, count(DISTINCT razorpay_sub_id) "
        f"FROM mrr_movements FINAL "
        f"WHERE merchant_id = {{mid:String}} AND period_month = {{mo:Date}}{extra} "
        f"  AND movement_type IN ('new', 'churn', 'reactivation') "
        f"GROUP BY movement_type",
        parameters={"mid": merchant_id, "mo": month_start, **ep},
    )
    by_type = {row[0]: int(row[1]) for row in counts.result_rows}

    # MRR lost to churn this month (sum of |delta| for churn rows)
    churn_mrr_result = ch.query(
        f"SELECT abs(sum(delta_paise)) FROM mrr_movements FINAL "
        f"WHERE merchant_id = {{mid:String}} AND period_month = {{mo:Date}}{extra} "
        f"  AND movement_type = 'churn'",
        parameters={"mid": merchant_id, "mo": month_start, **ep},
    )
    churn_mrr = int(churn_mrr_result.first_row[0] or 0)

    # Active at start of month = subs whose last known state before this month had amount > 0
    prev_month = (month_start.replace(day=1) - __import__("datetime").timedelta(days=1)).replace(day=1)
    active_start_result = ch.query(
        f"SELECT countIf(last_amount > 0) FROM ("
        f"  SELECT razorpay_sub_id, argMax(amount_paise, period_month) AS last_amount "
        f"  FROM mrr_movements FINAL "
        f"  WHERE merchant_id = {{mid:String}} AND period_month <= {{pm:Date}}{extra} "
        f"  GROUP BY razorpay_sub_id"
        f")",
        parameters={"mid": merchant_id, "pm": prev_month, **ep},
    )
    active_at_start = int(active_start_result.first_row[0] or 0)

    return {
        "new_subscribers": by_type.get("new", 0),
        "churned_subscribers": by_type.get("churn", 0),
        "reactivated_subscribers": by_type.get("reactivation", 0),
        "active_at_period_start": active_at_start,
        "churn_mrr_paise": churn_mrr,
    }


def plan_mrr_breakdown(merchant_id: str, month_start: date) -> list[dict]:
    """MRR and subscriber count grouped by plan_id for the given month."""
    result = _ch().query(
        "SELECT plan_id, "
        "       count(DISTINCT razorpay_sub_id) AS subscriber_count, "
        "       sum(delta_paise) AS net_mrr_delta "
        "FROM mrr_movements FINAL "
        "WHERE merchant_id = {mid:String} AND period_month = {mo:Date} "
        "GROUP BY plan_id "
        "ORDER BY abs(net_mrr_delta) DESC",
        parameters={"mid": merchant_id, "mo": month_start},
    )
    return [
        {
            "plan_id": row[0],
            "subscriber_count": int(row[1]),
            "net_mrr_delta_paise": int(row[2]),
        }
        for row in result.result_rows
    ]


def cohort_grid(merchant_id: str, max_cohort_months: int = 12) -> list[dict]:
    """
    Return the cohort retention matrix from cohort_retention FINAL.
    Scoped to the most recent max_cohort_months cohort months.
    """
    result = _ch().query(
        "SELECT cohort_month, period_number, period_month, "
        "       cohort_size, retained_count, revenue_paise "
        "FROM cohort_retention FINAL "
        "WHERE merchant_id = {mid:String} "
        "  AND cohort_month >= toDate(now() - INTERVAL {months:UInt16} MONTH) "
        "ORDER BY cohort_month ASC, period_number ASC",
        parameters={"mid": merchant_id, "months": max_cohort_months},
    )
    cols = ["cohort_month", "period_number", "period_month",
            "cohort_size", "retained_count", "revenue_paise"]
    return [dict(zip(cols, row)) for row in result.result_rows]


def mrr_movement_rows(
    merchant_id: str,
    month_start: date,
    limit: int = 100,
    offset: int = 0,
    plan_id: str | None = None,
    country: str | None = None,
    source: str | None = None,
    payment_method: str | None = None,
) -> list[dict]:
    """Individual MRR movement rows for a given month, sorted by |delta| desc."""
    extra, ep = _segment_clause(plan_id, country, source, payment_method)
    result = _ch().query(
        f"SELECT razorpay_sub_id, customer_id, plan_id, movement_type, "
        f"       amount_paise, prev_amount_paise, delta_paise, voluntary, period_month "
        f"FROM mrr_movements FINAL "
        f"WHERE merchant_id = {{mid:String}} AND period_month = {{mo:Date}}{extra} "
        f"ORDER BY abs(delta_paise) DESC "
        f"LIMIT {{lim:UInt32}} OFFSET {{off:UInt32}}",
        parameters={"mid": merchant_id, "mo": month_start, "lim": limit, "off": offset, **ep},
    )
    cols = ["razorpay_sub_id", "customer_id", "plan_id", "movement_type",
            "amount_paise", "prev_amount_paise", "delta_paise", "voluntary", "period_month"]
    return [dict(zip(cols, row)) for row in result.result_rows]


def subscriber_timeline(merchant_id: str, sub_id: str) -> list[dict]:
    """All MRR movements for a single subscription, ordered chronologically."""
    result = _ch().query(
        "SELECT razorpay_sub_id, customer_id, plan_id, movement_type, "
        "       amount_paise, prev_amount_paise, delta_paise, voluntary, period_month "
        "FROM mrr_movements FINAL "
        "WHERE merchant_id = {mid:String} AND razorpay_sub_id = {sid:String} "
        "ORDER BY period_month ASC",
        parameters={"mid": merchant_id, "sid": sub_id},
    )
    cols = ["razorpay_sub_id", "customer_id", "plan_id", "movement_type",
            "amount_paise", "prev_amount_paise", "delta_paise", "voluntary", "period_month"]
    return [dict(zip(cols, row)) for row in result.result_rows]


def mrr_movement_rows_all(
    merchant_id: str,
    month_start: date,
    plan_id: str | None = None,
    country: str | None = None,
    source: str | None = None,
    payment_method: str | None = None,
) -> list[dict]:
    """All movement rows for a month (no pagination) — used for CSV export."""
    extra, ep = _segment_clause(plan_id, country, source, payment_method)
    result = _ch().query(
        f"SELECT razorpay_sub_id, customer_id, plan_id, movement_type, "
        f"       amount_paise, prev_amount_paise, delta_paise, voluntary, period_month "
        f"FROM mrr_movements FINAL "
        f"WHERE merchant_id = {{mid:String}} AND period_month = {{mo:Date}}{extra} "
        f"ORDER BY abs(delta_paise) DESC",
        parameters={"mid": merchant_id, "mo": month_start, **ep},
    )
    cols = ["razorpay_sub_id", "customer_id", "plan_id", "movement_type",
            "amount_paise", "prev_amount_paise", "delta_paise", "voluntary", "period_month"]
    return [dict(zip(cols, row)) for row in result.result_rows]
