CREATE TABLE customers (
    id                    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id           UUID        NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    razorpay_customer_id  TEXT        NOT NULL,
    email                 TEXT,
    name                  TEXT,
    first_paid_at         TIMESTAMPTZ,
    total_paid_paise      BIGINT      NOT NULL DEFAULT 0,  -- cumulative, updated by metric workers
    ltv_paise             BIGINT      NOT NULL DEFAULT 0,  -- updated monthly by metric workers
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(merchant_id, razorpay_customer_id)
);

CREATE INDEX idx_customers_merchant ON customers(merchant_id);
