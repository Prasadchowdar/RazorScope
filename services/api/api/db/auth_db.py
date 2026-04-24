"""
PostgreSQL auth operations: merchant+user creation, refresh token store.

Uses the shared _pool from postgres.py — no separate connection pool needed.
Auth queries bypass RLS (no SET LOCAL needed) because they run before
merchant context is established.
"""
from __future__ import annotations

import hashlib
import logging
import secrets
from typing import Optional

import psycopg2.extras

from api.db.postgres import _get_conn, _put_conn

log = logging.getLogger(__name__)


def create_merchant_and_user(
    company_name: str,
    user_name: str,
    email: str,
    password_hash: str,
    razorpay_key_id: Optional[str] = None,
) -> dict:
    """Atomic: INSERT merchant + user + first named API key. Returns raw key once."""
    raw_key = "rzs_" + secrets.token_hex(20)
    raw_webhook_secret = "whsec_" + secrets.token_hex(24)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_prefix = raw_key[:12] + "****"

    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO merchants (name, razorpay_key_id, webhook_secret, api_key_hash)
                VALUES (%s, %s, %s, %s)
                RETURNING id::text
                """,
                # Keep the legacy merchants.api_key_hash populated for older
                # schema/query paths while also issuing the new named API key.
                (company_name, razorpay_key_id, raw_webhook_secret, key_hash),
            )
            merchant_id = cur.fetchone()["id"]

            cur.execute(
                """
                INSERT INTO users (merchant_id, email, name, password_hash, role, clerk_user_id)
                VALUES (%s::uuid, %s, %s, %s, 'owner', NULL)
                RETURNING id::text
                """,
                (merchant_id, email, user_name, password_hash),
            )
            user_id = cur.fetchone()["id"]

            cur.execute(
                """
                INSERT INTO merchant_api_keys
                    (merchant_id, name, key_hash, key_prefix, role)
                VALUES (%s::uuid, %s, %s, %s, 'admin')
                """,
                (merchant_id, "Default Key", key_hash, key_prefix),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)

    return {
        "merchant_id": merchant_id,
        "user_id": user_id,
        "raw_api_key": raw_key,
        "raw_webhook_secret": raw_webhook_secret,
    }


def find_user_by_email(email: str) -> Optional[dict]:
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id::text, merchant_id::text, password_hash, name,
                       email, role, is_active
                FROM users
                WHERE email = %s AND deleted_at IS NULL
                LIMIT 1
                """,
                (email,),
            )
            row = cur.fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    return dict(row) if row else None


def store_refresh_token(
    user_id: str,
    merchant_id: str,
    token_hash: str,
    user_agent: Optional[str],
    ip_addr: Optional[str],
) -> None:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO refresh_tokens
                    (user_id, merchant_id, token_hash, user_agent, ip_addr)
                VALUES (%s::uuid, %s::uuid, %s, %s, %s)
                """,
                (user_id, merchant_id, token_hash, user_agent, ip_addr),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)


def lookup_refresh_token(token_hash: str) -> Optional[dict]:
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    rt.id::text,
                    rt.user_id::text,
                    rt.merchant_id::text,
                    rt.expires_at,
                    u.role,
                    u.is_active
                FROM refresh_tokens rt
                JOIN users u ON u.id = rt.user_id
                WHERE rt.token_hash = %s
                  AND rt.revoked_at IS NULL
                  AND rt.expires_at > NOW()
                  AND u.deleted_at IS NULL
                """,
                (token_hash,),
            )
            row = cur.fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
    return dict(row) if row else None


def revoke_refresh_token(token_hash: str) -> None:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE refresh_tokens SET revoked_at = NOW() WHERE token_hash = %s",
                (token_hash,),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)


def rotate_refresh_token(
    old_hash: str,
    new_hash: str,
    user_id: str,
    merchant_id: str,
    user_agent: Optional[str],
    ip_addr: Optional[str],
) -> None:
    """Revoke old token and insert new one atomically."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE refresh_tokens SET revoked_at = NOW() WHERE token_hash = %s",
                (old_hash,),
            )
            cur.execute(
                """
                INSERT INTO refresh_tokens
                    (user_id, merchant_id, token_hash, user_agent, ip_addr)
                VALUES (%s::uuid, %s::uuid, %s, %s, %s)
                """,
                (user_id, merchant_id, new_hash, user_agent, ip_addr),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)
