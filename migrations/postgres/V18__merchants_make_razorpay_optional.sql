ALTER TABLE merchants
    ALTER COLUMN razorpay_key_id DROP NOT NULL,
    ALTER COLUMN webhook_secret  DROP NOT NULL;

DROP INDEX IF EXISTS idx_merchants_razorpay_key;
CREATE UNIQUE INDEX idx_merchants_razorpay_key
    ON merchants(razorpay_key_id)
    WHERE razorpay_key_id IS NOT NULL AND deleted_at IS NULL;
