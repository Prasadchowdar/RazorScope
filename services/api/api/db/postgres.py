"""
PostgreSQL access for the Dashboard API.

Uses razorscope_app role — RLS is enforced.
Set app.current_merchant_id per-transaction before querying tenant-scoped tables.
"""
from __future__ import annotations

import logging
from typing import Optional

import psycopg2
import psycopg2.extras
from psycopg2 import pool

log = logging.getLogger(__name__)

_pool: Optional[pool.ThreadedConnectionPool] = None


def init_pool(database_url: str, min_conn: int = 2, max_conn: int = 10) -> None:
    global _pool
    _pool = pool.ThreadedConnectionPool(min_conn, max_conn, database_url)
    log.info("postgres pool ready")


def close_pool() -> None:
    if _pool:
        _pool.closeall()


def _get_conn():
    if _pool is None:
        raise RuntimeError("postgres pool not initialized")
    return _pool.getconn()


def _put_conn(conn):
    _pool.putconn(conn)


def get_customer_by_razorpay_id(merchant_id: str, razorpay_customer_id: str) -> Optional[dict]:
    """Return name and email for a customer by their Razorpay customer ID."""
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            cur.execute(
                "SELECT name, email FROM customers "
                "WHERE merchant_id = %s::uuid AND razorpay_customer_id = %s",
                (merchant_id, razorpay_customer_id),
            )
            row = cur.fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    return dict(row) if row else None


def active_subscriber_count(merchant_id: str) -> int:
    """Count of subscriptions currently active (status=active, mrr_paise > 0).

    RLS is enforced via SET LOCAL on the razorscope_app role.
    """
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            cur.execute(
                "SELECT COUNT(*) FROM subscriptions WHERE status = 'active' AND mrr_paise > 0"
            )
            row = cur.fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    return int(row[0]) if row else 0


def create_backfill_job(merchant_id: str, from_date: str, to_date: str) -> str:
    """Insert a new backfill job and return its UUID."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            cur.execute(
                """
                INSERT INTO backfill_jobs (merchant_id, from_date, to_date, status)
                VALUES (%s::uuid, %s::date, %s::date, 'pending')
                RETURNING id::text
                """,
                (merchant_id, from_date, to_date),
            )
            row = cur.fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    return row[0]


def list_backfill_jobs(merchant_id: str) -> list[dict]:
    """All backfill jobs for a merchant, newest first."""
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            cur.execute(
                """
                SELECT id::text AS job_id, status, from_date, to_date,
                       pages_fetched, total_pages, error_detail,
                       created_at, completed_at
                FROM backfill_jobs
                WHERE merchant_id = %s::uuid
                ORDER BY created_at DESC
                """,
                (merchant_id,),
            )
            rows = cur.fetchall()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    return [dict(r) for r in rows]


def get_backfill_job(merchant_id: str, job_id: str) -> Optional[dict]:
    """Single backfill job scoped to merchant, or None if not found."""
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            cur.execute(
                """
                SELECT id::text AS job_id, status, from_date, to_date,
                       pages_fetched, total_pages, error_detail,
                       created_at, completed_at
                FROM backfill_jobs
                WHERE merchant_id = %s::uuid AND id = %s::uuid
                """,
                (merchant_id, job_id),
            )
            row = cur.fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    return dict(row) if row else None


def get_merchant_razorpay_integration(merchant_id: str) -> Optional[dict]:
    """Merchant-scoped Razorpay integration settings for onboarding/settings UI."""
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            cur.execute(
                """
                SELECT
                    id::text AS merchant_id,
                    webhook_secret,
                    razorpay_key_id,
                    CASE
                        WHEN razorpay_key_id IS NOT NULL
                         AND octet_length(COALESCE(razorpay_key_secret_enc, ''::bytea)) > 0
                        THEN TRUE
                        ELSE FALSE
                    END AS has_api_credentials
                FROM merchants
                WHERE id = %s::uuid AND deleted_at IS NULL
                """,
                (merchant_id,),
            )
            row = cur.fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    return dict(row) if row else None


def upsert_merchant_razorpay_credentials(
    merchant_id: str,
    key_id: str,
    key_secret: str,
    encryption_key: str,
) -> None:
    """Store per-merchant Razorpay API credentials for historical backfill."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            cur.execute(
                """
                UPDATE merchants
                SET razorpay_key_id = %s,
                    razorpay_key_secret_enc = pgp_sym_encrypt(%s, %s),
                    updated_at = NOW()
                WHERE id = %s::uuid AND deleted_at IS NULL
                """,
                (key_id, key_secret, encryption_key, merchant_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)


# ── CRM ──────────────────────────────────────────────────────────────────────

_DEFAULT_STAGES = [
    ("Prospect",    1, "#6B7280"),
    ("Qualified",   2, "#3B82F6"),
    ("Demo",        3, "#8B5CF6"),
    ("Proposal",    4, "#F59E0B"),
    ("Closed Won",  5, "#10B981"),
    ("Closed Lost", 6, "#EF4444"),
]


def _seed_default_stages(conn, merchant_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
        for name, pos, color in _DEFAULT_STAGES:
            cur.execute(
                "INSERT INTO pipeline_stages (merchant_id, name, position, color) VALUES (%s::uuid, %s, %s, %s)",
                (merchant_id, name, pos, color),
            )


def list_pipeline_stages(merchant_id: str) -> list[dict]:
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            cur.execute(
                "SELECT id::text, name, position, color FROM pipeline_stages WHERE merchant_id = %s::uuid ORDER BY position",
                (merchant_id,),
            )
            rows = cur.fetchall()
        if not rows:
            _seed_default_stages(conn, merchant_id)
            conn.commit()
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
                cur.execute(
                    "SELECT id::text, name, position, color FROM pipeline_stages WHERE merchant_id = %s::uuid ORDER BY position",
                    (merchant_id,),
                )
                rows = cur.fetchall()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    return [dict(r) for r in rows]


def create_pipeline_stage(merchant_id: str, name: str, color: str) -> dict:
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            cur.execute(
                """
                INSERT INTO pipeline_stages (merchant_id, name, position, color)
                VALUES (%s::uuid, %s,
                    COALESCE((SELECT MAX(position) + 1 FROM pipeline_stages WHERE merchant_id = %s::uuid), 1),
                    %s)
                RETURNING id::text, name, position, color
                """,
                (merchant_id, name, merchant_id, color),
            )
            row = cur.fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    return dict(row)


def update_pipeline_stage(merchant_id: str, stage_id: str, fields: dict) -> Optional[dict]:
    if not fields:
        return None
    allowed = {"name", "color", "position"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return None
    set_clause = ", ".join(f"{k} = %s" for k in updates)
    values = list(updates.values()) + [merchant_id, stage_id]
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            cur.execute(
                f"UPDATE pipeline_stages SET {set_clause} WHERE merchant_id = %s::uuid AND id = %s::uuid RETURNING id::text, name, position, color",
                values,
            )
            row = cur.fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    return dict(row) if row else None


def delete_pipeline_stage(merchant_id: str, stage_id: str) -> bool:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            cur.execute(
                "SELECT COUNT(*) FROM crm_leads WHERE stage_id = %s::uuid AND merchant_id = %s::uuid",
                (stage_id, merchant_id),
            )
            count = cur.fetchone()[0]
            if count > 0:
                conn.rollback()
                return False
            cur.execute(
                "DELETE FROM pipeline_stages WHERE merchant_id = %s::uuid AND id = %s::uuid RETURNING id",
                (merchant_id, stage_id),
            )
            deleted = cur.fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    return deleted is not None


def _serialize_lead(row: dict) -> dict:
    result = dict(row)
    for field in ("created_at", "updated_at"):
        v = result.get(field)
        if v is not None and hasattr(v, "isoformat"):
            result[field] = v.isoformat()
    return result


def list_crm_leads(merchant_id: str, stage_id: Optional[str] = None) -> list[dict]:
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            if stage_id:
                cur.execute(
                    "SELECT id::text, stage_id::text, customer_id::text, name, email, company, phone, plan_interest, mrr_estimate_paise, source, owner, notes, created_at, updated_at FROM crm_leads WHERE merchant_id = %s::uuid AND stage_id = %s::uuid ORDER BY created_at DESC",
                    (merchant_id, stage_id),
                )
            else:
                cur.execute(
                    "SELECT id::text, stage_id::text, customer_id::text, name, email, company, phone, plan_interest, mrr_estimate_paise, source, owner, notes, created_at, updated_at FROM crm_leads WHERE merchant_id = %s::uuid ORDER BY created_at DESC",
                    (merchant_id,),
                )
            rows = cur.fetchall()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    return [_serialize_lead(r) for r in rows]


def create_crm_lead(merchant_id: str, data: dict) -> dict:
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            stage_id = data.get("stage_id") or None
            cur.execute(
                """
                INSERT INTO crm_leads (merchant_id, stage_id, name, email, company, phone,
                    plan_interest, mrr_estimate_paise, source, owner, notes)
                VALUES (%s::uuid, %s::uuid, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id::text, stage_id::text, customer_id::text, name, email, company,
                    phone, plan_interest, mrr_estimate_paise, source, owner, notes, created_at, updated_at
                """,
                (
                    merchant_id, stage_id,
                    data.get("name"), data.get("email"), data.get("company"),
                    data.get("phone"), data.get("plan_interest"),
                    data.get("mrr_estimate_paise", 0), data.get("source"),
                    data.get("owner"), data.get("notes"),
                ),
            )
            row = cur.fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    return _serialize_lead(row)


def get_crm_lead(merchant_id: str, lead_id: str) -> Optional[dict]:
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            cur.execute(
                "SELECT id::text, stage_id::text, customer_id::text, name, email, company, phone, plan_interest, mrr_estimate_paise, source, owner, notes, created_at, updated_at FROM crm_leads WHERE merchant_id = %s::uuid AND id = %s::uuid",
                (merchant_id, lead_id),
            )
            row = cur.fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    return _serialize_lead(row) if row else None


def update_crm_lead(merchant_id: str, lead_id: str, fields: dict) -> Optional[dict]:
    if not fields:
        return None
    allowed = {"name", "email", "company", "phone", "stage_id", "plan_interest",
               "mrr_estimate_paise", "source", "owner", "notes"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return None
    set_parts = []
    values = []
    for k, v in updates.items():
        if k == "stage_id":
            set_parts.append("stage_id = %s::uuid")
            values.append(v)
        else:
            set_parts.append(f"{k} = %s")
            values.append(v)
    set_parts.append("updated_at = NOW()")
    set_clause = ", ".join(set_parts)
    values += [merchant_id, lead_id]
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            cur.execute(
                f"UPDATE crm_leads SET {set_clause} WHERE merchant_id = %s::uuid AND id = %s::uuid RETURNING id::text, stage_id::text, customer_id::text, name, email, company, phone, plan_interest, mrr_estimate_paise, source, owner, notes, created_at, updated_at",
                values,
            )
            row = cur.fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    return _serialize_lead(row) if row else None


def delete_crm_lead(merchant_id: str, lead_id: str) -> bool:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            cur.execute(
                "DELETE FROM crm_leads WHERE merchant_id = %s::uuid AND id = %s::uuid RETURNING id",
                (merchant_id, lead_id),
            )
            deleted = cur.fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    return deleted is not None


def add_lead_activity(merchant_id: str, lead_id: str, activity_type: str, body: str) -> dict:
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            cur.execute(
                "INSERT INTO crm_activities (lead_id, merchant_id, type, body) VALUES (%s::uuid, %s::uuid, %s, %s) RETURNING id::text, type, body, created_at",
                (lead_id, merchant_id, activity_type, body),
            )
            row = cur.fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    result = dict(row)
    if result.get("created_at") and hasattr(result["created_at"], "isoformat"):
        result["created_at"] = result["created_at"].isoformat()
    return result


def list_lead_activities(merchant_id: str, lead_id: str) -> list[dict]:
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            cur.execute(
                "SELECT id::text, type, body, created_at FROM crm_activities WHERE merchant_id = %s::uuid AND lead_id = %s::uuid ORDER BY created_at DESC",
                (merchant_id, lead_id),
            )
            rows = cur.fetchall()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    result = []
    for r in rows:
        d = dict(r)
        if d.get("created_at") and hasattr(d["created_at"], "isoformat"):
            d["created_at"] = d["created_at"].isoformat()
        result.append(d)
    return result


# ── Auth ──────────────────────────────────────────────────────────────────────

def lookup_api_key(api_key: str) -> Optional[dict]:
    """Return {merchant_id, role, key_prefix} for the given key, or None.

    Checks named merchant_api_keys first, then falls back to legacy merchants.api_key_hash.
    Updates last_used_at on named keys.
    """
    import hashlib
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT merchant_id::text, role, key_prefix
                FROM merchant_api_keys
                WHERE key_hash = %s AND revoked_at IS NULL
                  AND (expires_at IS NULL OR expires_at > NOW())
                """,
                (key_hash,),
            )
            row = cur.fetchone()
            if row:
                cur.execute(
                    "UPDATE merchant_api_keys SET last_used_at = NOW() WHERE key_hash = %s",
                    (key_hash,),
                )
                conn.commit()
                return {"merchant_id": row["merchant_id"], "role": row["role"], "key_prefix": row["key_prefix"]}
            cur.execute(
                "SELECT id::text FROM merchants WHERE api_key_hash = %s AND deleted_at IS NULL",
                (key_hash,),
            )
            row = cur.fetchone()
            conn.commit()
            if row:
                return {"merchant_id": row["id"], "role": "admin", "key_prefix": api_key[:12]}
            return None
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)


def merchant_id_for_api_key(api_key: str) -> Optional[str]:
    """Return merchant UUID for the given API key, or None if not found."""
    result = lookup_api_key(api_key)
    return result["merchant_id"] if result else None


# ── Named API Keys ─────────────────────────────────────────────────────────────

def list_api_keys(merchant_id: str) -> list[dict]:
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            cur.execute(
                """
                SELECT id::text, name, key_prefix, role,
                       last_used_at, expires_at, created_at, revoked_at
                FROM merchant_api_keys
                WHERE merchant_id = %s::uuid
                ORDER BY created_at DESC
                """,
                (merchant_id,),
            )
            rows = cur.fetchall()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    result = []
    for r in rows:
        d = dict(r)
        for f in ("last_used_at", "expires_at", "created_at", "revoked_at"):
            if d.get(f) and hasattr(d[f], "isoformat"):
                d[f] = d[f].isoformat()
        result.append(d)
    return result


def create_api_key(merchant_id: str, name: str, role: str = "admin", expires_at: Optional[str] = None) -> dict:
    """Generate a new named API key. Returns the full raw key ONCE plus the record."""
    import hashlib
    import secrets
    raw_key = "rzs_" + secrets.token_hex(20)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_prefix = raw_key[:12] + "****"
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            cur.execute(
                """
                INSERT INTO merchant_api_keys (merchant_id, name, key_hash, key_prefix, role, expires_at)
                VALUES (%s::uuid, %s, %s, %s, %s, %s)
                RETURNING id::text, name, key_prefix, role, expires_at, created_at
                """,
                (merchant_id, name, key_hash, key_prefix, role, expires_at),
            )
            row = cur.fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    d = dict(row)
    for f in ("expires_at", "created_at"):
        if d.get(f) and hasattr(d[f], "isoformat"):
            d[f] = d[f].isoformat()
    d["raw_key"] = raw_key
    return d


def revoke_api_key(merchant_id: str, key_id: str) -> bool:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            cur.execute(
                """
                UPDATE merchant_api_keys SET revoked_at = NOW()
                WHERE merchant_id = %s::uuid AND id = %s::uuid AND revoked_at IS NULL
                RETURNING id
                """,
                (merchant_id, key_id),
            )
            updated = cur.fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    return updated is not None


# ── Audit Log ──────────────────────────────────────────────────────────────────

def write_audit_log(merchant_id: str, actor_key: str, action: str,
                    resource: Optional[str] = None, detail: Optional[dict] = None,
                    ip_addr: Optional[str] = None) -> None:
    import json
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            cur.execute(
                """
                INSERT INTO audit_log (merchant_id, actor_key, action, resource, detail, ip_addr)
                VALUES (%s::uuid, %s, %s, %s, %s, %s)
                """,
                (merchant_id, actor_key, action, resource,
                 json.dumps(detail) if detail else None, ip_addr),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)


def list_audit_log(merchant_id: str, limit: int = 100) -> list[dict]:
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            cur.execute(
                """
                SELECT id::text, actor_key, action, resource, detail, ip_addr, created_at
                FROM audit_log
                WHERE merchant_id = %s::uuid
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (merchant_id, limit),
            )
            rows = cur.fetchall()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    result = []
    for r in rows:
        d = dict(r)
        if d.get("created_at") and hasattr(d["created_at"], "isoformat"):
            d["created_at"] = d["created_at"].isoformat()
        result.append(d)
    return result


# ── CRM Tasks ─────────────────────────────────────────────────────────────────

def _serialize_task(row: dict) -> dict:
    d = dict(row)
    for f in ("created_at", "updated_at"):
        if d.get(f) and hasattr(d[f], "isoformat"):
            d[f] = d[f].isoformat()
    if d.get("due_date") and hasattr(d["due_date"], "isoformat"):
        d["due_date"] = d["due_date"].isoformat()
    return d


def list_tasks(merchant_id: str, lead_id: Optional[str] = None, status: Optional[str] = None) -> list[dict]:
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            clauses = ["merchant_id = %s::uuid"]
            params: list = [merchant_id]
            if lead_id:
                clauses.append("lead_id = %s::uuid")
                params.append(lead_id)
            if status:
                clauses.append("status = %s")
                params.append(status)
            where = " AND ".join(clauses)
            cur.execute(
                f"SELECT id::text, lead_id::text, title, description, assignee, due_date, status, created_at, updated_at FROM crm_tasks WHERE {where} ORDER BY due_date ASC NULLS LAST, created_at ASC",
                params,
            )
            rows = cur.fetchall()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    return [_serialize_task(r) for r in rows]


def create_task(merchant_id: str, data: dict) -> dict:
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            lead_id = data.get("lead_id") or None
            cur.execute(
                """
                INSERT INTO crm_tasks (merchant_id, lead_id, title, description, assignee, due_date)
                VALUES (%s::uuid, %s::uuid, %s, %s, %s, %s)
                RETURNING id::text, lead_id::text, title, description, assignee, due_date, status, created_at, updated_at
                """,
                (merchant_id, lead_id, data["title"], data.get("description"),
                 data.get("assignee"), data.get("due_date")),
            )
            row = cur.fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    return _serialize_task(row)


def update_task(merchant_id: str, task_id: str, fields: dict) -> Optional[dict]:
    allowed = {"title", "description", "assignee", "due_date", "status"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return None
    set_clause = ", ".join(f"{k} = %s" for k in updates) + ", updated_at = NOW()"
    values = list(updates.values()) + [merchant_id, task_id]
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            cur.execute(
                f"UPDATE crm_tasks SET {set_clause} WHERE merchant_id = %s::uuid AND id = %s::uuid RETURNING id::text, lead_id::text, title, description, assignee, due_date, status, created_at, updated_at",
                values,
            )
            row = cur.fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    return _serialize_task(row) if row else None


def delete_task(merchant_id: str, task_id: str) -> bool:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            cur.execute(
                "DELETE FROM crm_tasks WHERE merchant_id = %s::uuid AND id = %s::uuid RETURNING id",
                (merchant_id, task_id),
            )
            deleted = cur.fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    return deleted is not None


# ── CRM Sequences ──────────────────────────────────────────────────────────────

def list_sequences(merchant_id: str) -> list[dict]:
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            cur.execute(
                """
                SELECT s.id::text, s.name, s.created_at,
                       COUNT(st.id) AS step_count,
                       COUNT(e.id) FILTER (WHERE e.status = 'active') AS active_enrollments
                FROM crm_sequences s
                LEFT JOIN crm_sequence_steps st ON st.sequence_id = s.id
                LEFT JOIN crm_sequence_enrollments e ON e.sequence_id = s.id
                WHERE s.merchant_id = %s::uuid
                GROUP BY s.id, s.name, s.created_at
                ORDER BY s.created_at DESC
                """,
                (merchant_id,),
            )
            rows = cur.fetchall()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    result = []
    for r in rows:
        d = dict(r)
        if d.get("created_at") and hasattr(d["created_at"], "isoformat"):
            d["created_at"] = d["created_at"].isoformat()
        d["step_count"] = int(d["step_count"])
        d["active_enrollments"] = int(d["active_enrollments"])
        result.append(d)
    return result


def create_sequence(merchant_id: str, name: str) -> dict:
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            cur.execute(
                "INSERT INTO crm_sequences (merchant_id, name) VALUES (%s::uuid, %s) RETURNING id::text, name, created_at",
                (merchant_id, name),
            )
            row = cur.fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    d = dict(row)
    if d.get("created_at") and hasattr(d["created_at"], "isoformat"):
        d["created_at"] = d["created_at"].isoformat()
    return d


def get_sequence(merchant_id: str, seq_id: str) -> Optional[dict]:
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            cur.execute(
                "SELECT id::text, name, created_at FROM crm_sequences WHERE merchant_id = %s::uuid AND id = %s::uuid",
                (merchant_id, seq_id),
            )
            seq = cur.fetchone()
            if not seq:
                return None
            cur.execute(
                "SELECT id::text, step_num, delay_days, subject, body FROM crm_sequence_steps WHERE sequence_id = %s::uuid ORDER BY step_num",
                (seq_id,),
            )
            steps = cur.fetchall()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    d = dict(seq)
    if d.get("created_at") and hasattr(d["created_at"], "isoformat"):
        d["created_at"] = d["created_at"].isoformat()
    d["steps"] = [dict(s) for s in steps]
    return d


def delete_sequence(merchant_id: str, seq_id: str) -> bool:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            cur.execute(
                "DELETE FROM crm_sequences WHERE merchant_id = %s::uuid AND id = %s::uuid RETURNING id",
                (merchant_id, seq_id),
            )
            deleted = cur.fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    return deleted is not None


def add_sequence_step(merchant_id: str, seq_id: str, step_num: int,
                      delay_days: int, subject: str, body: str) -> dict:
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            cur.execute(
                """
                INSERT INTO crm_sequence_steps (sequence_id, merchant_id, step_num, delay_days, subject, body)
                VALUES (%s::uuid, %s::uuid, %s, %s, %s, %s)
                RETURNING id::text, step_num, delay_days, subject, body
                """,
                (seq_id, merchant_id, step_num, delay_days, subject, body),
            )
            row = cur.fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    return dict(row)


def delete_sequence_step(merchant_id: str, seq_id: str, step_id: str) -> bool:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            cur.execute(
                "DELETE FROM crm_sequence_steps WHERE merchant_id = %s::uuid AND sequence_id = %s::uuid AND id = %s::uuid RETURNING id",
                (merchant_id, seq_id, step_id),
            )
            deleted = cur.fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    return deleted is not None


def enroll_lead(merchant_id: str, seq_id: str, lead_id: str) -> dict:
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            cur.execute(
                """
                INSERT INTO crm_sequence_enrollments (sequence_id, lead_id, merchant_id)
                VALUES (%s::uuid, %s::uuid, %s::uuid)
                ON CONFLICT (sequence_id, lead_id) DO UPDATE SET status = 'active', current_step = 0
                RETURNING id::text, sequence_id::text, lead_id::text, current_step, status, enrolled_at
                """,
                (seq_id, lead_id, merchant_id),
            )
            row = cur.fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    d = dict(row)
    if d.get("enrolled_at") and hasattr(d["enrolled_at"], "isoformat"):
        d["enrolled_at"] = d["enrolled_at"].isoformat()
    return d


def unenroll_lead(merchant_id: str, seq_id: str, lead_id: str) -> bool:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            cur.execute(
                "UPDATE crm_sequence_enrollments SET status = 'stopped' WHERE merchant_id = %s::uuid AND sequence_id = %s::uuid AND lead_id = %s::uuid RETURNING id",
                (merchant_id, seq_id, lead_id),
            )
            updated = cur.fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    return updated is not None


def list_lead_enrollments(merchant_id: str, lead_id: str) -> list[dict]:
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            cur.execute(
                """
                SELECT e.id::text, e.sequence_id::text, s.name AS sequence_name,
                       e.current_step, e.status, e.enrolled_at
                FROM crm_sequence_enrollments e
                JOIN crm_sequences s ON s.id = e.sequence_id
                WHERE e.merchant_id = %s::uuid AND e.lead_id = %s::uuid
                ORDER BY e.enrolled_at DESC
                """,
                (merchant_id, lead_id),
            )
            rows = cur.fetchall()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    result = []
    for r in rows:
        d = dict(r)
        if d.get("enrolled_at") and hasattr(d["enrolled_at"], "isoformat"):
            d["enrolled_at"] = d["enrolled_at"].isoformat()
        result.append(d)
    return result


# ── Rep Performance ────────────────────────────────────────────────────────────

def get_rep_stats(merchant_id: str) -> list[dict]:
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            cur.execute(
                """
                SELECT
                    COALESCE(l.owner, 'Unassigned') AS rep,
                    COUNT(*)                         AS total_leads,
                    COUNT(*) FILTER (WHERE ps.name = 'Closed Won')  AS won_leads,
                    COUNT(*) FILTER (WHERE ps.name = 'Closed Lost') AS lost_leads,
                    COALESCE(SUM(l.mrr_estimate_paise), 0)          AS pipeline_mrr_paise,
                    COUNT(*) FILTER (WHERE l.created_at > NOW() - INTERVAL '30 days') AS new_leads_30d
                FROM crm_leads l
                LEFT JOIN pipeline_stages ps ON ps.id = l.stage_id AND ps.merchant_id = l.merchant_id
                WHERE l.merchant_id = %s::uuid
                GROUP BY l.owner
                ORDER BY total_leads DESC
                """,
                (merchant_id,),
            )
            rows = cur.fetchall()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    return [
        {
            "rep": r["rep"],
            "total_leads": int(r["total_leads"]),
            "won_leads": int(r["won_leads"]),
            "lost_leads": int(r["lost_leads"]),
            "pipeline_mrr_paise": int(r["pipeline_mrr_paise"]),
            "new_leads_30d": int(r["new_leads_30d"]),
        }
        for r in rows
    ]


# ── Lead Enrichment (mock) ─────────────────────────────────────────────────────

_INDUSTRIES = ["SaaS", "FinTech", "HealthTech", "EdTech", "E-Commerce", "Logistics", "HR Tech", "Dev Tools"]
_SIZES = ["1-10", "11-50", "51-200", "201-500", "500+"]

def enrich_lead(merchant_id: str, lead_id: str) -> Optional[dict]:
    """Mock enrichment: derives company metadata from the lead's existing data."""
    lead = get_crm_lead(merchant_id, lead_id)
    if not lead:
        return None
    company = lead.get("company") or lead.get("name") or ""
    seed = sum(ord(c) for c in company)
    industry = _INDUSTRIES[seed % len(_INDUSTRIES)]
    size = _SIZES[(seed // 7) % len(_SIZES)]
    website = f"https://www.{company.lower().replace(' ', '')}.com" if company else None
    patch = {
        "notes": (lead.get("notes") or "") + f"\n[Enriched] Industry: {industry} | Size: {size} employees",
    }
    return update_crm_lead(merchant_id, lead_id, patch)
