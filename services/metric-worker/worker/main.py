"""
Metric Worker entry point.

Wires up: Kafka consumer → state machine → PostgreSQL snapshot → ClickHouse MRR write.
Runs a daily APScheduler job to recompute cohort retention for all merchants.
"""
import logging
import sys

from apscheduler.schedulers.background import BackgroundScheduler

from worker.config import Config
from worker.consumer import build_consumer, init_redis, run_consumer_loop
from worker.models import KafkaMessage
from worker.state_machine import process_event, updated_snapshot
from worker.cohort import compute_cohort_grid
from worker.backfill.processor import poll_and_run_backfill
from worker import db

logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)


def handle_event(event: KafkaMessage) -> None:
    """
    Process one Kafka event through the full pipeline:
    1. Load subscription snapshot from PostgreSQL
    2. Load merchant config (churn window, etc.)
    3. Run state machine → MRR movement
    4. Update snapshot in PostgreSQL
    5. Write MRR movement to ClickHouse
    """
    if not event.sub_id:
        log.debug("skipping event with no sub_id event_id=%s type=%s", event.event_id, event.event_type)
        return

    snapshot = db.postgres.load_snapshot(event.merchant_id, event.sub_id)
    config = db.postgres.load_merchant_config(event.merchant_id)

    movement = process_event(event, snapshot, config)

    # Always update snapshot, even when there's no MRR movement
    new_snapshot = updated_snapshot(snapshot, event, movement)
    db.postgres.upsert_snapshot(new_snapshot, event.sub_id, event.plan_id, event.customer_id)

    if movement:
        db.clickhouse.write_mrr_movement(movement)
        log.info(
            "mrr movement merchant=%s sub=%s type=%s delta=%d",
            event.merchant_id, event.sub_id, movement.movement_type, movement.delta_paise,
        )
    else:
        log.debug("no mrr movement event_id=%s type=%s", event.event_id, event.event_type)


def recompute_all_cohorts() -> None:
    """Daily job: recompute cohort retention for every merchant that has paid subs."""
    log.info("cohort job starting")
    try:
        merchant_ids = db.postgres.load_all_merchant_ids()
        log.info("cohort job: %d merchants", len(merchant_ids))
        for mid in merchant_ids:
            try:
                movements = db.clickhouse.load_all_movements(mid)
                rows = compute_cohort_grid(movements, max_periods=24)
                db.clickhouse.write_cohort_retention(rows)
            except Exception as exc:
                log.error("cohort job failed for merchant %s: %s", mid, exc)
    except Exception as exc:
        log.error("cohort job failed: %s", exc)
    log.info("cohort job done")


def main() -> None:
    log.info("metric worker starting")

    db.postgres.init_pool(Config.DATABASE_URL)
    init_redis(Config.REDIS_URL)
    db.clickhouse.init_client(
        host=Config.CLICKHOUSE_HOST,
        port=Config.CLICKHOUSE_PORT,
        user=Config.CLICKHOUSE_USER,
        password=Config.CLICKHOUSE_PASSWORD,
        database=Config.CLICKHOUSE_DB,
    )

    consumer = build_consumer(
        brokers=Config.KAFKA_BROKERS,
        topic=Config.KAFKA_TOPIC,
        group_id=Config.KAFKA_GROUP_ID,
    )

    # Run cohort recompute on startup, then daily at 02:00 UTC
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(recompute_all_cohorts, "cron", hour=2, minute=0)
    scheduler.add_job(poll_and_run_backfill, "interval", seconds=60, id="backfill_poll")
    scheduler.start()
    recompute_all_cohorts()  # initial run so data is available immediately

    try:
        run_consumer_loop(consumer, handle_event)
    finally:
        scheduler.shutdown(wait=False)
        db.postgres.close_pool()


if __name__ == "__main__":
    main()
