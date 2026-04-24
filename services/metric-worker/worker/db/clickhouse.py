"""
ClickHouse writes for the metric worker.

mrr_movements uses ReplacingMergeTree — we always INSERT new rows.
ClickHouse deduplicates on background merge (keep latest by updated_at).
Queries must use FINAL or argMax to get consistent reads.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import clickhouse_connect

from worker.models import MRRMovement
from worker.retry import with_retry

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


@with_retry(max_attempts=3, backoff_base=1.0, exceptions=(Exception,))
def write_mrr_movement(m: MRRMovement) -> None:
    """Insert one MRR movement row into ClickHouse mrr_movements table."""
    if _client is None:
        raise RuntimeError("clickhouse client not initialized — call init_client() first")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    period = m.period_month.date().replace(day=1)

    _client.insert(
        "mrr_movements",
        [[
            m.merchant_id,
            period,
            m.movement_type,
            m.razorpay_sub_id,
            m.customer_id,
            m.plan_id,
            m.amount_paise,
            m.prev_amount_paise,
            m.delta_paise,
            1 if m.voluntary else 0,
            now,
            now,
            m.country,
            m.source,
            m.payment_method,
        ]],
        column_names=[
            "merchant_id", "period_month", "movement_type",
            "razorpay_sub_id", "customer_id", "plan_id",
            "amount_paise", "prev_amount_paise", "delta_paise",
            "voluntary", "computed_at", "updated_at",
            "country", "source", "payment_method",
        ],
    )
    log.debug("wrote mrr movement merchant=%s type=%s delta=%d",
              m.merchant_id, m.movement_type, m.delta_paise)


def write_subscription_event(event_row: list, column_names: list) -> None:
    """Insert a row into subscription_events (used by backfill worker)."""
    if _client is None:
        raise RuntimeError("clickhouse client not initialized")
    _client.insert("subscription_events", [event_row], column_names=column_names)


def load_all_movements(merchant_id: str) -> list[dict]:
    """Load every mrr_movement row for a merchant — used by the cohort recomputer."""
    if _client is None:
        raise RuntimeError("clickhouse client not initialized")
    result = _client.query(
        "SELECT merchant_id, razorpay_sub_id, period_month, movement_type, amount_paise "
        "FROM mrr_movements FINAL "
        "WHERE merchant_id = {mid:String} "
        "ORDER BY razorpay_sub_id, period_month",
        parameters={"mid": merchant_id},
    )
    return [
        {
            "merchant_id": row[0],
            "razorpay_sub_id": row[1],
            "period_month": row[2],  # ClickHouse returns Date as date
            "movement_type": row[3],
            "amount_paise": int(row[4]),
        }
        for row in result.result_rows
    ]


@with_retry(max_attempts=3, backoff_base=1.0, exceptions=(Exception,))
def write_cohort_retention(rows: list[dict]) -> None:
    """Upsert cohort_retention rows into ClickHouse (ReplacingMergeTree — safe to re-insert)."""
    if _client is None:
        raise RuntimeError("clickhouse client not initialized")
    if not rows:
        return

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    data = [
        [
            r["merchant_id"],
            r["cohort_month"],
            r["period_month"],
            r["period_number"],
            r["cohort_size"],
            r["retained_count"],
            r["revenue_paise"],
            now,
        ]
        for r in rows
    ]
    _client.insert(
        "cohort_retention",
        data,
        column_names=[
            "merchant_id", "cohort_month", "period_month", "period_number",
            "cohort_size", "retained_count", "revenue_paise", "updated_at",
        ],
    )
    log.debug("wrote %d cohort_retention rows", len(rows))
