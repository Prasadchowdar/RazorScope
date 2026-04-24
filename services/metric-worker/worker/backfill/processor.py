"""
Backfill job processor.

Picks up a pending backfill job, pages through historical Razorpay events,
runs each event through the same state machine used for live webhooks,
and writes MRR movements to ClickHouse.
"""
from __future__ import annotations

import logging

from worker.backfill.razorpay_client import get_client
from worker.config import Config
from worker.models import KafkaMessage
from worker.state_machine import process_event, updated_snapshot
from worker import db
from worker.db import postgres as pg

log = logging.getLogger(__name__)


def run_backfill_job(job: dict) -> None:
    """
    Process one backfill job end-to-end.

    job dict keys: job_id, merchant_id, from_date, to_date, pages_fetched, cursor
    """
    job_id = job["job_id"]
    merchant_id = job["merchant_id"]
    from_date = job["from_date"]  # date object from psycopg2
    to_date = job["to_date"]

    if not pg.claim_backfill_job(job_id):
        log.info("backfill job %s already claimed by another worker", job_id)
        return

    log.info("backfill job %s started merchant=%s range=%s→%s", job_id, merchant_id, from_date, to_date)

    creds = pg.load_merchant_razorpay_credentials(
        merchant_id,
        Config.RAZORPAY_SECRET_ENCRYPTION_KEY,
    )
    client = get_client(
        creds["razorpay_key_id"],
        creds["razorpay_key_secret"],
    ) if creds else get_client()
    cursor = job.get("cursor")
    pages_fetched = int(job.get("pages_fetched") or 0)

    try:
        config = pg.load_merchant_config(merchant_id)

        while True:
            events, next_cursor = client.fetch_page(merchant_id, from_date, to_date, cursor)

            for raw in events:
                try:
                    msg = KafkaMessage.from_dict(raw)
                    snapshot = pg.load_snapshot(merchant_id, msg.sub_id)
                    movement = process_event(msg, snapshot, config)
                    new_snap = updated_snapshot(snapshot, msg, movement)
                    pg.upsert_snapshot(new_snap, msg.sub_id, msg.plan_id, msg.customer_id)
                    if movement:
                        db.clickhouse.write_mrr_movement(movement)
                        log.debug(
                            "backfill mrr movement sub=%s type=%s delta=%d",
                            msg.sub_id, movement.movement_type, movement.delta_paise,
                        )
                except Exception as exc:
                    log.warning("backfill: skipping event %s due to error: %s", raw.get("event_id"), exc)

            pages_fetched += 1
            cursor = next_cursor
            pg.update_backfill_progress(job_id, pages_fetched, cursor)
            log.info("backfill job %s page %d done, next_cursor=%s", job_id, pages_fetched, cursor)

            if next_cursor is None:
                break

        pg.complete_backfill_job(job_id)
        log.info("backfill job %s completed after %d pages", job_id, pages_fetched)

    except Exception as exc:
        error_detail = str(exc)[:500]
        log.error("backfill job %s failed: %s", job_id, error_detail)
        pg.fail_backfill_job(job_id, error_detail)


def poll_and_run_backfill() -> None:
    """Scheduler callback: pick up all pending jobs and run them sequentially."""
    try:
        jobs = pg.poll_pending_backfill_jobs()
        if not jobs:
            return
        log.info("backfill poll: found %d pending job(s)", len(jobs))
        for job in jobs:
            run_backfill_job(job)
    except Exception as exc:
        log.error("backfill poll error: %s", exc)
