CREATE TABLE subscriptions (
    id                    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id           UUID        NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    razorpay_sub_id       TEXT        NOT NULL,
    razorpay_plan_id      TEXT        NOT NULL,
    customer_id           UUID        REFERENCES customers(id),
    status                TEXT        NOT NULL DEFAULT 'created',
        -- created | authenticated | active | paused | cancelled | completed | expired
    amount_paise          BIGINT      NOT NULL,  -- plan amount in paise, never float
    currency              CHAR(3)     NOT NULL DEFAULT 'INR',
    interval_type         TEXT        NOT NULL DEFAULT 'monthly',
        -- daily | weekly | monthly | quarterly | yearly
    mrr_paise             BIGINT      NOT NULL DEFAULT 0,  -- normalized monthly equivalent
    ever_paid             BOOLEAN     NOT NULL DEFAULT FALSE,
    current_period_start  TIMESTAMPTZ,
    current_period_end    TIMESTAMPTZ,
    trial_start           TIMESTAMPTZ,
    trial_end             TIMESTAMPTZ,
    cancelled_at          TIMESTAMPTZ,
    churned_at            TIMESTAMPTZ,
    started_at            TIMESTAMPTZ,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(merchant_id, razorpay_sub_id)
);

CREATE INDEX idx_subs_merchant_status ON subscriptions(merchant_id, status);
CREATE INDEX idx_subs_active ON subscriptions(merchant_id) WHERE status = 'active';
CREATE INDEX idx_subs_customer ON subscriptions(customer_id);
