-- CRM Tasks (per-lead to-do items)
CREATE TABLE crm_tasks (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID        NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    lead_id     UUID        REFERENCES crm_leads(id) ON DELETE CASCADE,
    title       TEXT        NOT NULL,
    description TEXT,
    assignee    TEXT,
    due_date    DATE,
    status      TEXT        NOT NULL DEFAULT 'open',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_crm_tasks_merchant ON crm_tasks(merchant_id, status);
CREATE INDEX idx_crm_tasks_lead     ON crm_tasks(lead_id);

-- Email sequences (outreach templates)
CREATE TABLE crm_sequences (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID        NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    name        TEXT        NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_crm_sequences_merchant ON crm_sequences(merchant_id);

CREATE TABLE crm_sequence_steps (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    sequence_id UUID        NOT NULL REFERENCES crm_sequences(id) ON DELETE CASCADE,
    merchant_id UUID        NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    step_num    INT         NOT NULL,
    delay_days  INT         NOT NULL DEFAULT 0,
    subject     TEXT        NOT NULL,
    body        TEXT        NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_crm_seq_steps ON crm_sequence_steps(sequence_id, step_num);

-- Track which leads are enrolled in which sequences
CREATE TABLE crm_sequence_enrollments (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    sequence_id  UUID        NOT NULL REFERENCES crm_sequences(id) ON DELETE CASCADE,
    lead_id      UUID        NOT NULL REFERENCES crm_leads(id)      ON DELETE CASCADE,
    merchant_id  UUID        NOT NULL REFERENCES merchants(id)       ON DELETE CASCADE,
    current_step INT         NOT NULL DEFAULT 0,
    status       TEXT        NOT NULL DEFAULT 'active',
    enrolled_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(sequence_id, lead_id)
);

CREATE INDEX idx_crm_enrollments_lead ON crm_sequence_enrollments(lead_id);

-- RLS
ALTER TABLE crm_tasks                ENABLE ROW LEVEL SECURITY;
ALTER TABLE crm_sequences            ENABLE ROW LEVEL SECURITY;
ALTER TABLE crm_sequence_steps       ENABLE ROW LEVEL SECURITY;
ALTER TABLE crm_sequence_enrollments ENABLE ROW LEVEL SECURITY;

CREATE POLICY crm_tasks_isolation ON crm_tasks
    USING (merchant_id = current_setting('app.current_merchant_id')::uuid);

CREATE POLICY crm_sequences_isolation ON crm_sequences
    USING (merchant_id = current_setting('app.current_merchant_id')::uuid);

CREATE POLICY crm_sequence_steps_isolation ON crm_sequence_steps
    USING (merchant_id = current_setting('app.current_merchant_id')::uuid);

CREATE POLICY crm_sequence_enrollments_isolation ON crm_sequence_enrollments
    USING (merchant_id = current_setting('app.current_merchant_id')::uuid);

GRANT SELECT, INSERT, UPDATE, DELETE ON crm_tasks, crm_sequences, crm_sequence_steps, crm_sequence_enrollments TO razorscope_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON crm_tasks, crm_sequences, crm_sequence_steps, crm_sequence_enrollments TO razorscope_service;
