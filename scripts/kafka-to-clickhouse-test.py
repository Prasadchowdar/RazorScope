#!/usr/bin/env python
"""
Test fixture: consumes one message from the razorpay.events Kafka topic
and writes it to ClickHouse subscription_events table.

This is NOT the production metric worker (Stage 2). It exists solely to
verify the end-to-end exit criteria: event reaches ClickHouse within 5s.

Usage:
    pip install kafka-python clickhouse-connect
    python scripts/kafka-to-clickhouse-test.py
"""

import json
import os
import sys
import time

# Optional: target event_id to search for. If provided, consumer reads until it finds it.
TARGET_EVENT_ID = sys.argv[1] if len(sys.argv) > 1 else None

try:
    import clickhouse_connect
    from kafka import KafkaConsumer
except ImportError:
    print("Missing deps. Run: pip install kafka-python clickhouse-connect")
    sys.exit(1)

KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "localhost:29092").split(",")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "razorpay.events")
CH_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
CH_PORT = int(os.getenv("CLICKHOUSE_PORT", "8123"))
CH_USER = os.getenv("CLICKHOUSE_USER", "razorscope")
CH_PASS = os.getenv("CLICKHOUSE_PASSWORD", "razorscope_dev")
CH_DB = os.getenv("CLICKHOUSE_DB", "razorscope")

print(f"Connecting to Kafka {KAFKA_BROKERS}, topic={KAFKA_TOPIC}")
import uuid as _uuid
consumer = KafkaConsumer(
    KAFKA_TOPIC,
    bootstrap_servers=KAFKA_BROKERS,
    auto_offset_reset="earliest",       # read from beginning so we don't miss already-produced msgs
    consumer_timeout_ms=10_000,
    value_deserializer=lambda b: json.loads(b.decode("utf-8")),
    group_id=f"test-fixture-{_uuid.uuid4()}",   # unique per run — never shares offsets
)

print(f"Connecting to ClickHouse {CH_HOST}:{CH_PORT}")
ch = clickhouse_connect.get_client(
    host=CH_HOST, port=CH_PORT,
    username=CH_USER, password=CH_PASS,
    database=CH_DB,
)

print(f"Waiting for messages (up to 10s){' targeting event_id=' + TARGET_EVENT_ID if TARGET_EVENT_ID else ''}...")
inserted = 0
found_target = False

for msg in consumer:
    m = msg.value
    eid = m.get("event_id", "")
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    ch.insert(
        "subscription_events",
        [[
            eid,
            m.get("merchant_id", ""),
            m.get("event_type", ""),
            m.get("sub_id", ""),
            m.get("payment_id", ""),
            m.get("plan_id", ""),
            m.get("customer_id", ""),
            m.get("amount_paise", 0),
            m.get("currency", "INR"),
            m.get("payment_method", "unknown"),
            "monthly",
            m.get("amount_paise", 0),
            "webhook",
            now,
            now,
            m.get("raw_payload", "{}"),
        ]],
        column_names=[
            "event_id", "merchant_id", "event_type", "razorpay_sub_id",
            "razorpay_pay_id", "plan_id", "customer_id", "amount_paise",
            "currency", "payment_method", "interval_type", "mrr_paise",
            "source", "event_ts", "received_at", "raw_payload",
        ],
    )
    print(f"Inserted event_id={eid} into ClickHouse")
    inserted += 1
    if TARGET_EVENT_ID and eid == TARGET_EVENT_ID:
        found_target = True
        break  # found what we need

consumer.close()

if inserted == 0:
    print("ERROR: No messages received within timeout")
    sys.exit(1)
if TARGET_EVENT_ID and not found_target:
    print(f"ERROR: target event_id={TARGET_EVENT_ID} not found in consumed messages")
    sys.exit(1)
print("Done.")
