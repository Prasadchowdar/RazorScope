-- Replace plaintext api_key with a SHA-256 hex digest.
-- In production: generate keys on the application side, store only the hash.
-- The raw key is shown to the merchant once at creation time and never stored.
ALTER TABLE merchants ADD COLUMN IF NOT EXISTS api_key_hash TEXT;

-- Migrate existing keys: hash the current plaintext value
UPDATE merchants SET api_key_hash = encode(digest(api_key, 'sha256'), 'hex') WHERE api_key_hash IS NULL;

ALTER TABLE merchants ALTER COLUMN api_key_hash SET NOT NULL;
ALTER TABLE merchants ADD CONSTRAINT merchants_api_key_hash_unique UNIQUE (api_key_hash);
CREATE INDEX idx_merchants_api_key_hash ON merchants(api_key_hash) WHERE deleted_at IS NULL;

-- Drop the old plaintext column
ALTER TABLE merchants DROP COLUMN api_key;
