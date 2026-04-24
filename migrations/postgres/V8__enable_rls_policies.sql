-- Create application roles
-- razorscope_app: used by API server (RLS enforced, cannot see other merchants' rows)
-- razorscope_service: used by metric workers / backfill (BYPASSRLS for cross-merchant aggregation)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'razorscope_app') THEN
        CREATE ROLE razorscope_app LOGIN PASSWORD 'app_dev_password';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'razorscope_service') THEN
        CREATE ROLE razorscope_service BYPASSRLS LOGIN PASSWORD 'svc_dev_password';
    END IF;
END $$;

GRANT USAGE ON SCHEMA public TO razorscope_app, razorscope_service;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO razorscope_app;
GRANT ALL ON ALL TABLES IN SCHEMA public TO razorscope_service;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO razorscope_app, razorscope_service;

-- Enable RLS on all tenant-scoped tables
ALTER TABLE customers          ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions      ENABLE ROW LEVEL SECURITY;
ALTER TABLE webhook_deliveries ENABLE ROW LEVEL SECURITY;
ALTER TABLE backfill_jobs      ENABLE ROW LEVEL SECURITY;
ALTER TABLE metric_configs     ENABLE ROW LEVEL SECURITY;

-- Policy: app role can only see rows matching the current merchant context
-- Set with: SET LOCAL app.current_merchant_id = '<uuid>' at the start of each request
CREATE POLICY tenant_isolation ON customers
    FOR ALL TO razorscope_app
    USING (merchant_id = current_setting('app.current_merchant_id', true)::uuid);

CREATE POLICY tenant_isolation ON subscriptions
    FOR ALL TO razorscope_app
    USING (merchant_id = current_setting('app.current_merchant_id', true)::uuid);

CREATE POLICY tenant_isolation ON webhook_deliveries
    FOR ALL TO razorscope_app
    USING (merchant_id = current_setting('app.current_merchant_id', true)::uuid);

CREATE POLICY tenant_isolation ON backfill_jobs
    FOR ALL TO razorscope_app
    USING (merchant_id = current_setting('app.current_merchant_id', true)::uuid);

CREATE POLICY tenant_isolation ON metric_configs
    FOR ALL TO razorscope_app
    USING (merchant_id = current_setting('app.current_merchant_id', true)::uuid);
