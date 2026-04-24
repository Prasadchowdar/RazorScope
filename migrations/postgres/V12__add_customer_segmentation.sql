-- Segmentation dimensions on the customer record.
-- country: ISO 3166-1 alpha-2 (e.g. 'IN', 'US'), from subscription notes or address.
-- source:  acquisition channel (e.g. 'organic', 'google_ads', 'referral').
ALTER TABLE customers
    ADD COLUMN IF NOT EXISTS country TEXT,
    ADD COLUMN IF NOT EXISTS source  TEXT;

CREATE INDEX idx_customers_country ON customers(merchant_id, country) WHERE country IS NOT NULL;
CREATE INDEX idx_customers_source  ON customers(merchant_id, source)  WHERE source  IS NOT NULL;
