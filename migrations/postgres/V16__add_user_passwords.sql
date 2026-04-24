ALTER TABLE users
    ALTER COLUMN clerk_user_id DROP NOT NULL;

ALTER TABLE users DROP CONSTRAINT IF EXISTS users_clerk_user_id_key;
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_clerk_unique
    ON users(clerk_user_id) WHERE clerk_user_id IS NOT NULL;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS password_hash TEXT,
    ADD COLUMN IF NOT EXISTS name         TEXT,
    ADD COLUMN IF NOT EXISTS is_active    BOOLEAN NOT NULL DEFAULT TRUE;
