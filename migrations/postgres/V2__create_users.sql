CREATE TABLE users (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id   UUID        NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    clerk_user_id TEXT        NOT NULL UNIQUE,
    email         TEXT        NOT NULL,
    role          TEXT        NOT NULL DEFAULT 'member',  -- 'owner' | 'member' | 'viewer'
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at    TIMESTAMPTZ,
    UNIQUE(merchant_id, email)
);

CREATE INDEX idx_users_merchant ON users(merchant_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_clerk ON users(clerk_user_id);
