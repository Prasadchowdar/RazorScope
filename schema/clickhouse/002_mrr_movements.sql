-- Pre-aggregated MRR movements. Updated by Metric Workers after each event.
-- ReplacingMergeTree: reinsert with same ORDER BY key + newer updated_at to update a row.
-- Queries must use FINAL modifier or argMax to get the latest version.
CREATE TABLE IF NOT EXISTS razorscope.mrr_movements (
    merchant_id       LowCardinality(String),
    period_month      Date,                    -- first day of the month (e.g. 2024-03-01)
    movement_type     LowCardinality(String),  -- new | expansion | contraction | churn | reactivation
    razorpay_sub_id   String,
    customer_id       String,
    plan_id           String,
    amount_paise      Int64,                   -- MRR after movement (paise)
    prev_amount_paise Int64,                   -- MRR before movement (paise)
    delta_paise       Int64,                   -- signed delta (positive = growth, negative = loss)
    voluntary         UInt8,                   -- 1 = voluntary churn, 0 = involuntary
    computed_at       DateTime,
    updated_at        DateTime
)
ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY (merchant_id, toYYYYMM(period_month))
ORDER BY (merchant_id, period_month, movement_type, razorpay_sub_id)
SETTINGS index_granularity = 8192;
