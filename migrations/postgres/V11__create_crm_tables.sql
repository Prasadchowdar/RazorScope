-- CRM: pipeline stages per merchant
CREATE TABLE pipeline_stages (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID        NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    name        TEXT        NOT NULL,
    position    INT         NOT NULL DEFAULT 0,
    color       TEXT        NOT NULL DEFAULT '#6B7280',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_stages_merchant ON pipeline_stages(merchant_id, position);

-- CRM: leads (prospects in the pipeline)
CREATE TABLE crm_leads (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id          UUID        NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    stage_id             UUID        REFERENCES pipeline_stages(id) ON DELETE SET NULL,
    customer_id          UUID        REFERENCES customers(id) ON DELETE SET NULL,
    name                 TEXT        NOT NULL,
    email                TEXT,
    company              TEXT,
    phone                TEXT,
    plan_interest        TEXT,
    mrr_estimate_paise   BIGINT      NOT NULL DEFAULT 0,
    source               TEXT,
    owner                TEXT,
    notes                TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_leads_merchant ON crm_leads(merchant_id);
CREATE INDEX idx_leads_stage    ON crm_leads(stage_id);

-- CRM: activity log per lead (notes, calls, emails, stage changes)
CREATE TABLE crm_activities (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id     UUID        NOT NULL REFERENCES crm_leads(id) ON DELETE CASCADE,
    merchant_id UUID        NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    type        TEXT        NOT NULL DEFAULT 'note',
    body        TEXT        NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_activities_lead ON crm_activities(lead_id, created_at DESC);

-- Enable RLS on all CRM tables
ALTER TABLE pipeline_stages ENABLE ROW LEVEL SECURITY;
ALTER TABLE crm_leads       ENABLE ROW LEVEL SECURITY;
ALTER TABLE crm_activities  ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON pipeline_stages
    FOR ALL TO razorscope_app
    USING (merchant_id = current_setting('app.current_merchant_id', true)::uuid);

CREATE POLICY tenant_isolation ON crm_leads
    FOR ALL TO razorscope_app
    USING (merchant_id = current_setting('app.current_merchant_id', true)::uuid);

CREATE POLICY tenant_isolation ON crm_activities
    FOR ALL TO razorscope_app
    USING (merchant_id = current_setting('app.current_merchant_id', true)::uuid);

-- Grant access to existing roles
GRANT SELECT, INSERT, UPDATE, DELETE ON pipeline_stages, crm_leads, crm_activities TO razorscope_app;
GRANT ALL ON pipeline_stages, crm_leads, crm_activities TO razorscope_service;
