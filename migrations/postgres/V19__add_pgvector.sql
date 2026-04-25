-- Feature: RAG context embeddings using pgvector
-- Stores OpenAI text-embedding-3-small (1536-dim) vectors for CRM activity notes.
-- Used by Churn Defender to RAG-fetch relevant past interactions before drafting emails.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE subscriber_embeddings (
    id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id  UUID         NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    customer_id  UUID         NOT NULL,
    source_type  TEXT         NOT NULL CHECK (source_type IN ('activity', 'note')),
    source_id    UUID         NOT NULL,
    content_text TEXT         NOT NULL,
    embedding    vector(1536) NOT NULL,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_source UNIQUE (source_type, source_id)
);

-- HNSW index for fast cosine similarity search, scoped per merchant+customer
CREATE INDEX idx_embeddings_hnsw
    ON subscriber_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX idx_embeddings_merchant_customer
    ON subscriber_embeddings(merchant_id, customer_id);

-- RLS: tenant isolation via app.current_merchant_id session variable
ALTER TABLE subscriber_embeddings ENABLE ROW LEVEL SECURITY;

CREATE POLICY subscriber_embeddings_tenant
    ON subscriber_embeddings
    FOR ALL
    TO razorscope_app
    USING (merchant_id::text = current_setting('app.current_merchant_id', TRUE));

GRANT ALL ON subscriber_embeddings TO razorscope_app;
GRANT ALL ON subscriber_embeddings TO razorscope_service;
