CREATE TABLE backfill_jobs (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id    UUID        NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    status         TEXT        NOT NULL DEFAULT 'pending',
        -- pending | running | done | failed
    from_date      DATE        NOT NULL,
    to_date        DATE        NOT NULL,
    pages_fetched  INT         NOT NULL DEFAULT 0,
    total_pages    INT,
    cursor         TEXT,       -- pagination cursor for resumable backfill
    error_detail   TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at   TIMESTAMPTZ
);

CREATE INDEX idx_backfill_merchant ON backfill_jobs(merchant_id, status);
