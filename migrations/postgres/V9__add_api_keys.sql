-- Add API key to merchants for Dashboard API authentication.
-- Each merchant gets a unique key; existing rows get a deterministic default.
ALTER TABLE merchants ADD COLUMN IF NOT EXISTS api_key TEXT;

UPDATE merchants SET api_key = 'rzs_' || replace(id::text, '-', '') WHERE api_key IS NULL;

ALTER TABLE merchants ALTER COLUMN api_key SET NOT NULL;
ALTER TABLE merchants ADD CONSTRAINT merchants_api_key_unique UNIQUE (api_key);

CREATE INDEX idx_merchants_api_key ON merchants(api_key) WHERE deleted_at IS NULL;
