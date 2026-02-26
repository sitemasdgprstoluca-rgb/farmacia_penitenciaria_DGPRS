# DDL applied manually in Supabase SQL Editor (not via Django migration
# because the DB is hosted in Supabase and schema DDL is managed there).
# This migration is a no-op so Django's migration history stays consistent.
#
# Run the following SQL directly in the Supabase > SQL Editor (IN ORDER):
#
# ── STEP 1: Add missing column (lotes.created_by_id does NOT exist yet) ──────
#
#   ALTER TABLE lotes
#       ADD COLUMN IF NOT EXISTS created_by_id integer
#       REFERENCES usuarios(id) ON DELETE SET NULL;
#
# ── STEP 2: Create performance indexes ───────────────────────────────────────
#
#   CREATE INDEX IF NOT EXISTS idx_auditoria_logs_modelo_accion_obj_ts
#       ON auditoria_logs (modelo, accion, objeto_id, timestamp DESC)
#       WHERE usuario_id IS NOT NULL;
#
#   CREATE INDEX IF NOT EXISTS idx_lote_parcialidades_lote_created
#       ON lote_parcialidades (lote_id, created_at ASC);
#
#   CREATE INDEX IF NOT EXISTS idx_lotes_created_by_id
#       ON lotes (created_by_id)
#       WHERE created_by_id IS NOT NULL;

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0026_sync_producto_fields'),
    ]

    operations = []
