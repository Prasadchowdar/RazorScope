"""
Background embedding generation for CRM activity notes.

Runs fire-and-forget in a thread pool so the CRM activity creation endpoint
is never blocked by an OpenAI call. Uses text-embedding-3-small (1536 dims).
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from api.db import postgres
from api.llm import get_client

log = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="embedder")


def schedule_embed_activity(
    merchant_id: str,
    lead_id: str,
    activity_id: str,
    body_text: str,
) -> None:
    """Submit an embedding job to the background thread pool. Non-blocking."""
    _executor.submit(_embed_and_store, merchant_id, lead_id, activity_id, body_text)


def _embed_and_store(
    merchant_id: str,
    lead_id: str,
    activity_id: str,
    body_text: str,
) -> None:
    if not body_text or not body_text.strip():
        return
    try:
        embedding = _generate_embedding(body_text)
        lead = postgres.get_crm_lead(merchant_id, lead_id)
        if not lead or not lead.get("customer_id"):
            log.debug("embed_activity: no customer_id for lead %s, skipping", lead_id)
            return
        postgres.upsert_embedding(
            merchant_id=merchant_id,
            customer_id=lead["customer_id"],
            source_type="activity",
            source_id=activity_id,
            content_text=body_text,
            embedding=embedding,
        )
    except Exception as exc:
        log.warning("embed_activity failed for %s: %s", activity_id, exc)


def _generate_embedding(text: str) -> list[float]:
    client = get_client()
    resp = client.embeddings.create(
        model="text-embedding-3-small",
        input=text[:8000],  # safety cap
        encoding_format="float",
    )
    return resp.data[0].embedding


def generate_query_embedding(text: str) -> list[float]:
    """Synchronous embedding for a query string. Called from agents_router."""
    return _generate_embedding(text)
