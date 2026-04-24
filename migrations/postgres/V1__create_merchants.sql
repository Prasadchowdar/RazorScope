CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE merchants (
    id                        UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name                      TEXT        NOT NULL,
    razorpay_key_id           TEXT        NOT NULL UNIQUE,
    razorpay_key_secret_enc   BYTEA       NOT NULL DEFAULT ''::BYTEA,  -- AES-256-GCM ciphertext (prod)
    webhook_secret            TEXT        NOT NULL,                     -- plaintext in dev
    plan_tier                 TEXT        NOT NULL DEFAULT 'free',
    trial_ends_at             TIMESTAMPTZ,
    created_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at                TIMESTAMPTZ
);

CREATE INDEX idx_merchants_razorpay_key ON merchants(razorpay_key_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_merchants_plan ON merchants(plan_tier) WHERE deleted_at IS NULL;
