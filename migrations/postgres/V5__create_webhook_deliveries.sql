CREATE TABLE webhook_deliveries (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id      UUID        NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    event_id         TEXT        NOT NULL,   -- Razorpay entity ID (payment/subscription)
    event_type       TEXT        NOT NULL,
    received_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    kafka_offset     BIGINT,                 -- NULL if written to Redis fallback queue
    status           TEXT        NOT NULL DEFAULT 'received',
        -- received | processed | failed | duplicate
    error_detail     TEXT,
    UNIQUE(merchant_id, event_id)
);

CREATE INDEX idx_wd_merchant_received ON webhook_deliveries(merchant_id, received_at DESC);
CREATE INDEX idx_wd_status ON webhook_deliveries(merchant_id, status);

-- Auto-delete rows beyond 500 per merchant to keep the table bounded
CREATE OR REPLACE FUNCTION trim_webhook_deliveries()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM webhook_deliveries
    WHERE merchant_id = NEW.merchant_id
      AND id NOT IN (
        SELECT id FROM webhook_deliveries
        WHERE merchant_id = NEW.merchant_id
        ORDER BY received_at DESC
        LIMIT 500
    );
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_trim_webhook_deliveries
AFTER INSERT ON webhook_deliveries
FOR EACH ROW EXECUTE FUNCTION trim_webhook_deliveries();
