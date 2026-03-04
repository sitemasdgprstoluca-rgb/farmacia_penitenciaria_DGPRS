# DDL applied manually in Supabase SQL Editor (not via Django migration
# because the DB is hosted in Supabase and schema DDL is managed there).
# This migration is a no-op so Django's migration history stays consistent.
#
# Run the following SQL directly in the Supabase > SQL Editor:
#
# ── Create idempotency_keys table ────────────────────────────────────────────
#
#   CREATE TABLE IF NOT EXISTS idempotency_keys (
#       id              SERIAL PRIMARY KEY,
#       key             VARCHAR(100) NOT NULL UNIQUE,
#       endpoint        VARCHAR(100) NOT NULL,
#       user_id         INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
#       response_data   JSONB NOT NULL DEFAULT '{}',
#       response_status INTEGER NOT NULL DEFAULT 201,
#       created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
#   );
#
#   CREATE INDEX IF NOT EXISTS idx_idempotency_keys_key
#       ON idempotency_keys (key);
#
#   CREATE INDEX IF NOT EXISTS idx_idempotency_keys_user_created
#       ON idempotency_keys (user_id, created_at DESC);
#
# ── Optional: auto-clean keys older than 24 hours (via pg_cron) ──────────────
#
#   SELECT cron.schedule(
#       'clean-idempotency-keys',
#       '0 * * * *',   -- every hour
#       $$DELETE FROM idempotency_keys WHERE created_at < NOW() - INTERVAL '24 hours'$$
#   );
#
# ─────────────────────────────────────────────────────────────────────────────

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0027_add_perf_indexes'),
    ]

    operations = [
        # No-op: table is created manually in Supabase (see SQL above).
        # Django only tracks this migration to keep history consistent.
    ]
