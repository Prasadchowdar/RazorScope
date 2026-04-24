CREATE TABLE metric_configs (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id          UUID        NOT NULL REFERENCES merchants(id) ON DELETE CASCADE UNIQUE,
    include_discounts    BOOLEAN     NOT NULL DEFAULT FALSE,
    include_trials       BOOLEAN     NOT NULL DEFAULT FALSE,
    churn_window_days    INT         NOT NULL DEFAULT 30,   -- 7–90
    fiscal_year_start    INT         NOT NULL DEFAULT 4,    -- April (Indian financial year)
    timezone             TEXT        NOT NULL DEFAULT 'Asia/Kolkata',
    trial_plan_ids       TEXT[]      NOT NULL DEFAULT '{}', -- plan IDs treated as trials
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_metric_configs_merchant ON metric_configs(merchant_id);
