-- Add segmentation dimensions to mrr_movements.
-- ReplacingMergeTree supports ADD COLUMN — existing rows get the default value.
-- New inserts from the metric worker will include the actual values.
ALTER TABLE razorscope.mrr_movements
    ADD COLUMN IF NOT EXISTS country        LowCardinality(String) DEFAULT '',
    ADD COLUMN IF NOT EXISTS source         LowCardinality(String) DEFAULT '',
    ADD COLUMN IF NOT EXISTS payment_method LowCardinality(String) DEFAULT '';
