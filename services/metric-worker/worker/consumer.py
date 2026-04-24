"""
Kafka consumer loop for the metric worker.

One consumer group ('razorscope-metric-workers') across all worker instances.
Kafka guarantees ordering within a partition, and we partition by merchant_id,
so all events for one merchant are processed by one worker at a time.

Poison message handling:
  - Transient errors (DB down): retried by the @with_retry decorator on DB functions.
  - Persistent errors (bad data / bug): message is pushed to a Redis DLQ list
    (kafka:dlq:razorpay.events) and offset is committed so the worker moves on.
    A separate process can replay or inspect DLQ messages.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Callable, Optional

import redis
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable

from worker.models import KafkaMessage

log = logging.getLogger(__name__)

_redis: Optional[redis.Redis] = None
DLQ_KEY = "kafka:dlq:razorpay.events"


def init_redis(redis_url: str) -> None:
    global _redis
    _redis = redis.from_url(redis_url, decode_responses=True)
    log.info("redis client ready for DLQ")


def _push_to_dlq(raw_value: dict, error: str) -> None:
    if _redis is None:
        log.error("DLQ redis not initialised — message lost: %s", raw_value.get("event_id"))
        return
    try:
        _redis.rpush(DLQ_KEY, json.dumps({"payload": raw_value, "error": error}))
        log.warning("pushed event_id=%s to DLQ (%s)", raw_value.get("event_id"), DLQ_KEY)
    except Exception as exc:
        log.error("failed to push to DLQ: %s", exc)


def build_consumer(brokers: list[str], topic: str, group_id: str) -> KafkaConsumer:
    """Create and return a KafkaConsumer. Retries until brokers are reachable."""
    for attempt in range(30):
        try:
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=brokers,
                group_id=group_id,
                auto_offset_reset="earliest",
                enable_auto_commit=False,
                value_deserializer=lambda b: json.loads(b.decode("utf-8")),
                session_timeout_ms=30_000,
                heartbeat_interval_ms=10_000,
                max_poll_records=100,
                consumer_timeout_ms=-1,
            )
            log.info("kafka consumer connected brokers=%s topic=%s group=%s", brokers, topic, group_id)
            return consumer
        except NoBrokersAvailable:
            log.warning("kafka not reachable (attempt %d/30), retrying in 5s", attempt + 1)
            time.sleep(5)
    raise RuntimeError(f"could not connect to Kafka brokers: {brokers}")


def run_consumer_loop(
    consumer: KafkaConsumer,
    process_fn: Callable[[KafkaMessage], None],
) -> None:
    """
    Main consumer loop. Commits after every message — success or DLQ.
    Transient failures are retried by the @with_retry decorators on DB calls.
    Persistent failures go to the Redis DLQ so the worker never gets stuck.
    """
    log.info("consumer loop started")
    try:
        for msg in consumer:
            event_id = msg.value.get("event_id", "?")
            try:
                event = KafkaMessage.from_dict(msg.value)
                process_fn(event)
            except Exception as exc:
                log.error("event_id=%s permanently failed, sending to DLQ: %s", event_id, exc, exc_info=True)
                _push_to_dlq(msg.value, str(exc))
            finally:
                consumer.commit()
    except KeyboardInterrupt:
        log.info("consumer loop stopped by signal")
    finally:
        consumer.close()
        log.info("consumer closed")
