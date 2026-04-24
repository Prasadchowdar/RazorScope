-- Named API keys (multiple per merchant, with RBAC roles)
CREATE TABLE merchant_api_keys (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id  UUID        NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    name         TEXT        NOT NULL,
    key_hash     TEXT        NOT NULL UNIQUE,
    key_prefix   TEXT        NOT NULL,
    role         TEXT        NOT NULL DEFAULT 'admin',
    last_used_at TIMESTAMPTZ,
    expires_at   TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at   TIMESTAMPTZ
);

CREATE INDEX idx_merchant_api_keys_merchant ON merchant_api_keys(merchant_id) WHERE revoked_at IS NULL;
CREATE INDEX idx_merchant_api_keys_hash     ON merchant_api_keys(key_hash)    WHERE revoked_at IS NULL;

-- Audit log
CREATE TABLE audit_log (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID        NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    actor_key   TEXT,
    action      TEXT        NOT NULL,
    resource    TEXT,
    detail      JSONB,
    ip_addr     TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_log_merchant_time ON audit_log(merchant_id, created_at DESC);

-- RLS
ALTER TABLE merchant_api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log          ENABLE ROW LEVEL SECURITY;

CREATE POLICY merchant_api_keys_isolation ON merchant_api_keys
    USING (merchant_id = current_setting('app.current_merchant_id')::uuid);

CREATE POLICY audit_log_isolation ON audit_log
    USING (merchant_id = current_setting('app.current_merchant_id')::uuid);

GRANT SELECT, INSERT, UPDATE, DELETE ON merchant_api_keys TO razorscope_app;
GRANT SELECT, INSERT                  ON audit_log          TO razorscope_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON merchant_api_keys TO razorscope_service;
GRANT SELECT, INSERT                  ON audit_log          TO razorscope_service;
