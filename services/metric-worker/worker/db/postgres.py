"""
PostgreSQL access for the metric worker.

Uses psycopg2 with a connection pool (ThreadedConnectionPool).
The worker runs as a consumer loop — synchronous DB calls are fine.
Uses razorscope_service role which bypasses RLS (worker needs cross-merchant access).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

import psycopg2
import psycopg2.extras
from psycopg2 import pool

from worker.models import MerchantConfig, SubscriptionSnapshot
from worker.retry import with_retry

log = logging.getLogger(__name__)

_pool: Optional[pool.ThreadedConnectionPool] = None


def init_pool(database_url: str, min_conn: int = 2, max_conn: int = 10) -> None:
    global _pool
    # Swap in service role credentials — worker bypasses RLS
    parsed = urlparse(database_url)
    service_url = database_url.replace(
        f"{parsed.username}:{parsed.password}",
        "razorscope_service:svc_dev_password",
    )
    _pool = pool.ThreadedConnectionPool(min_conn, max_conn, service_url)
    log.info("postgres pool ready")


def _get_conn():
    if _pool is None:
        raise RuntimeError("postgres pool not initialized — call init_pool() first")
    return _pool.getconn()


def _put_conn(conn):
    _pool.putconn(conn)


@with_retry(max_attempts=3, backoff_base=1.0, exceptions=(psycopg2.OperationalError, psycopg2.InterfaceError))
def load_snapshot(merchant_id: str, sub_id: str) -> SubscriptionSnapshot:
    """Load subscription state from PostgreSQL. Returns a zero-state snapshot if not found."""
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                """
                SELECT
                    razorpay_sub_id, merchant_id, customer_id,
                    COALESCE((SELECT razorpay_customer_id FROM customers WHERE id = s.customer_id), '') AS cust_rzp_id,
                    razorpay_plan_id, status,
                    mrr_paise, amount_paise, interval_type,
                    ever_paid, churned_at, current_period_end
                FROM subscriptions s
                WHERE merchant_id = %s AND razorpay_sub_id = %s
                """,
                (merchant_id, sub_id),
            )
            row = cur.fetchone()
    finally:
        _put_conn(conn)

    if row is None:
        return SubscriptionSnapshot(
            sub_id=sub_id,
            merchant_id=merchant_id,
            customer_id="",
            plan_id="",
            status="unknown",
            mrr_paise=0,
            amount_paise=0,
            interval_type="monthly",
            ever_paid=False,
            churned_at=None,
            current_period_end=None,
            exists=False,
        )

    return SubscriptionSnapshot(
        sub_id=row["razorpay_sub_id"],
        merchant_id=row["merchant_id"],
        customer_id=row.get("cust_rzp_id", ""),
        plan_id=row["razorpay_plan_id"],
        status=row["status"],
        mrr_paise=row["mrr_paise"],
        amount_paise=row["amount_paise"],
        interval_type=row["interval_type"],
        ever_paid=row["ever_paid"],
        churned_at=row["churned_at"],
        current_period_end=row["current_period_end"],
        exists=True,
    )


@with_retry(max_attempts=3, backoff_base=1.0, exceptions=(psycopg2.OperationalError, psycopg2.InterfaceError))
def upsert_snapshot(snapshot: SubscriptionSnapshot, event_sub_id: str, event_plan_id: str, event_customer_id: str) -> None:
    """Insert or update the subscription snapshot in PostgreSQL."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO subscriptions (
                    merchant_id, razorpay_sub_id, razorpay_plan_id,
                    status, mrr_paise, amount_paise, interval_type, ever_paid,
                    churned_at, current_period_end, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (merchant_id, razorpay_sub_id) DO UPDATE SET
                    status           = EXCLUDED.status,
                    mrr_paise        = EXCLUDED.mrr_paise,
                    amount_paise     = EXCLUDED.amount_paise,
                    interval_type    = EXCLUDED.interval_type,
                    ever_paid        = EXCLUDED.ever_paid,
                    churned_at       = COALESCE(EXCLUDED.churned_at, subscriptions.churned_at),
                    current_period_end = COALESCE(EXCLUDED.current_period_end, subscriptions.current_period_end),
                    updated_at       = NOW()
                """,
                (
                    snapshot.merchant_id,
                    snapshot.sub_id,
                    snapshot.plan_id or event_plan_id,
                    snapshot.status,
                    snapshot.mrr_paise,
                    snapshot.amount_paise,
                    snapshot.interval_type,
                    snapshot.ever_paid,
                    snapshot.churned_at,
                    snapshot.current_period_end,
                ),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)


@with_retry(max_attempts=3, backoff_base=1.0, exceptions=(psycopg2.OperationalError, psycopg2.InterfaceError))
def load_merchant_config(merchant_id: str) -> MerchantConfig:
    """Load per-merchant metric settings. Returns defaults if not configured."""
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                "SELECT churn_window_days, include_discounts, include_trials, timezone FROM metric_configs WHERE merchant_id = %s",
                (merchant_id,),
            )
            row = cur.fetchone()
    finally:
        _put_conn(conn)

    if row is None:
        return MerchantConfig(merchant_id=merchant_id)

    return MerchantConfig(
        merchant_id=merchant_id,
        churn_window_days=row["churn_window_days"],
        include_discounts=row["include_discounts"],
        include_trials=row["include_trials"],
        timezone=row["timezone"],
    )


def load_merchant_razorpay_credentials(
    merchant_id: str,
    encryption_key: str,
) -> Optional[dict]:
    """Return decrypted per-merchant Razorpay API credentials when configured."""
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    razorpay_key_id,
                    pgp_sym_decrypt(razorpay_key_secret_enc, %s)::text AS razorpay_key_secret
                FROM merchants
                WHERE id = %s::uuid
                  AND deleted_at IS NULL
                  AND razorpay_key_id IS NOT NULL
                  AND octet_length(COALESCE(razorpay_key_secret_enc, ''::bytea)) > 0
                """,
                (encryption_key, merchant_id),
            )
            row = cur.fetchone()
    finally:
        _put_conn(conn)

    if not row:
        return None
    return {
        "razorpay_key_id": row["razorpay_key_id"],
        "razorpay_key_secret": row["razorpay_key_secret"],
    }


def load_all_merchant_ids() -> list[str]:
    """Return all merchant UUIDs that have at least one subscription with ever_paid=TRUE."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT DISTINCT merchant_id::text FROM subscriptions WHERE ever_paid = TRUE"
            )
            rows = cur.fetchall()
    finally:
        _put_conn(conn)
    return [r[0] for r in rows]


def poll_pending_backfill_jobs() -> list[dict]:
    """Return up to 5 backfill jobs with status='pending', oldest first."""
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id::text AS job_id, merchant_id::text,
                       from_date, to_date, pages_fetched, cursor
                FROM backfill_jobs
                WHERE status = 'pending'
                ORDER BY created_at ASC
                LIMIT 5
                """
            )
            rows = cur.fetchall()
    finally:
        _put_conn(conn)
    return [dict(r) for r in rows]


def claim_backfill_job(job_id: str) -> bool:
    """Atomically transition a job from pending → running. Returns True if claimed."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE backfill_jobs
                SET status = 'running', updated_at = NOW()
                WHERE id = %s::uuid AND status = 'pending'
                """,
                (job_id,),
            )
            claimed = cur.rowcount == 1
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    return claimed


def update_backfill_progress(job_id: str, pages_fetched: int, cursor: Optional[str]) -> None:
    """Update in-flight progress: pages fetched and pagination cursor."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE backfill_jobs
                SET pages_fetched = %s, cursor = %s, updated_at = NOW()
                WHERE id = %s::uuid
                """,
                (pages_fetched, cursor, job_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)


def complete_backfill_job(job_id: str) -> None:
    """Mark a job as done."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE backfill_jobs
                SET status = 'done', completed_at = NOW(), updated_at = NOW()
                WHERE id = %s::uuid
                """,
                (job_id,),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)


def fail_backfill_job(job_id: str, error_detail: str) -> None:
    """Mark a job as failed with an error message."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE backfill_jobs
                SET status = 'failed', error_detail = %s, updated_at = NOW()
                WHERE id = %s::uuid
                """,
                (error_detail, job_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)


def close_pool() -> None:
    if _pool:
        _pool.closeall()
