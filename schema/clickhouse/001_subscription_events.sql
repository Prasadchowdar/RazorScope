-- Append-only event log. NEVER UPDATE rows — replay events to recompute metrics.
-- Each row is one Razorpay webhook event that affected a subscription.
CREATE TABLE IF NOT EXISTS razorscope.subscription_events (
    event_id         String,
    merchant_id      LowCardinality(String),
    event_type       LowCardinality(String),   -- subscription.charged | subscription.cancelled | etc.
    razorpay_sub_id  String,
    razorpay_pay_id  String,                   -- empty string when no payment entity
    plan_id          String,
    customer_id      String,
    amount_paise     Int64,                    -- ALWAYS integers, never floats
    currency         FixedString(3),
    payment_method   LowCardinality(String),   -- upi_autopay | card | nach | upi_collect | unknown
    interval_type    LowCardinality(String),   -- monthly | quarterly | yearly | weekly | daily
    mrr_paise        Int64,                    -- normalized monthly equivalent at time of event
    source           LowCardinality(String),   -- webhook | backfill
    event_ts         DateTime64(3, 'Asia/Kolkata'),
    received_at      DateTime64(3),
    raw_payload      String                    -- full JSON — enables Kafka event replay
)
ENGINE = MergeTree()
PARTITION BY (merchant_id, toYYYYMM(event_ts))
ORDER BY (merchant_id, event_ts, event_id)
SETTINGS index_granularity = 8192;
