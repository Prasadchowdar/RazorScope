-- merchant_api_keys cannot use RLS for the auth lookup:
-- we need to find the merchant FROM the key hash, so no context is available yet.
-- Tenant isolation for list/create/revoke is enforced at the application layer
-- (WHERE merchant_id = %s::uuid in every query).
ALTER TABLE merchant_api_keys DISABLE ROW LEVEL SECURITY;
DROP POLICY merchant_api_keys_isolation ON merchant_api_keys;

-- audit_log keeps RLS; it is always accessed after merchant_id is known.
-- Also fix its policy to use missing_ok so session startup doesn't error.
DROP POLICY audit_log_isolation ON audit_log;
CREATE POLICY audit_log_isolation ON audit_log
    USING (
        current_setting('app.current_merchant_id', true) <> ''
        AND merchant_id = current_setting('app.current_merchant_id', true)::uuid
    );
