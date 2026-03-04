# DDL aplicado manualmente en Supabase SQL Editor (no vía Django migration).
# Esta migración es un no-op para que el historial de Django quede consistente.
#
# Ejecutar el siguiente SQL en Supabase > SQL Editor (en orden):
#
# ── STEP 1: Crear tabla realtime_events ─────────────────────────────────────
#
#   CREATE TABLE IF NOT EXISTS realtime_events (
#       id         BIGSERIAL    PRIMARY KEY,
#       event_type VARCHAR(20)  NOT NULL,
#       entity     VARCHAR(50)  NOT NULL,
#       entity_id  INTEGER      NOT NULL,
#       scope_id   INTEGER,
#       created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
#   );
#
# ── STEP 2: Índice para consultas frecuentes ─────────────────────────────────
#
#   CREATE INDEX IF NOT EXISTS idx_re_entity_created
#       ON realtime_events (entity, created_at DESC);
#
# ── STEP 3: Habilitar Supabase Realtime en esta tabla ───────────────────────
#
#   ALTER PUBLICATION supabase_realtime ADD TABLE realtime_events;
#
# ── STEP 4: RLS — permitir lectura anónima (solo metadatos, sin datos sensibles)
#
#   ALTER TABLE realtime_events ENABLE ROW LEVEL SECURITY;
#
#   CREATE POLICY "anon_select" ON realtime_events
#       FOR SELECT USING (true);
#
# ── STEP 5 (opcional): Auto-limpieza vía pg_cron ─────────────────────────────
#
#   SELECT cron.schedule(
#       'clean-realtime-events',
#       '*/10 * * * *',   -- cada 10 minutos
#       $$DELETE FROM realtime_events WHERE created_at < NOW() - INTERVAL '15 minutes'$$
#   );
#
# ─────────────────────────────────────────────────────────────────────────────
# NOTAS DE SEGURIDAD:
#   - La tabla SOLO almacena: event_type, entity, entity_id, scope_id
#   - NO almacena nombres de medicamentos, cantidades, precios ni datos PII
#   - RLS anon=true es seguro porque solo es metadata de "algo cambió"
#   - El cliente siempre refetch a la API DRF (que aplica permisos completos)
# ─────────────────────────────────────────────────────────────────────────────

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0028_idempotency_key'),
    ]

    operations = [
        # No-op: tabla creada manualmente en Supabase (ver SQL arriba).
    ]
