-- Cohort retention matrix. Recomputed daily by Metric Workers.
-- Each row = retention of one signup cohort at one time period.
-- Heatmap: rows = cohort_month, columns = period_number (0..24).
CREATE TABLE IF NOT EXISTS razorscope.cohort_retention (
    merchant_id     LowCardinality(String),
    cohort_month    Date,      -- month customers signed up (e.g. 2024-01-01)
    period_month    Date,      -- month being measured
    period_number   UInt16,    -- months since cohort signup (0 = signup month)
    cohort_size     UInt32,    -- total customers in this cohort
    retained_count  UInt32,    -- customers still active in period_month
    revenue_paise   Int64,     -- MRR retained from this cohort in period_month
    updated_at      DateTime
)
ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY (merchant_id, toYYYYMM(cohort_month))
ORDER BY (merchant_id, cohort_month, period_number)
SETTINGS index_granularity = 8192;
