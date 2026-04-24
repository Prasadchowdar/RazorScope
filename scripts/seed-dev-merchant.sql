-- Seed a test merchant for local development and e2e testing.
-- Safe to run multiple times (ON CONFLICT: upsert api_key_hash).
INSERT INTO merchants (id, name, razorpay_key_id, webhook_secret, plan_tier, api_key_hash)
VALUES (
    '11111111-1111-1111-1111-111111111111',
    'Dev Test Merchant',
    'rzp_test_devmerchant123',
    'whsec_dev_test_secret',
    'growth',
    encode(digest('rzs_dev_11111111', 'sha256'), 'hex')
)
ON CONFLICT (id) DO UPDATE SET
    api_key_hash = encode(digest('rzs_dev_11111111', 'sha256'), 'hex');

-- Default metric config for the test merchant
INSERT INTO metric_configs (merchant_id)
VALUES ('11111111-1111-1111-1111-111111111111')
ON CONFLICT (merchant_id) DO NOTHING;

DO $$ BEGIN RAISE NOTICE 'Dev merchant seeded (id: 11111111-1111-1111-1111-111111111111)'; END $$;
