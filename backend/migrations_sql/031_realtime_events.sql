-- ============================================================================
-- 031_realtime_events.sql
-- Tabla de eventos en tiempo real para Supabase Realtime
-- Fecha: 2026-03-14
-- ============================================================================
-- INSTRUCCIONES: Ejecutar en Supabase Dashboard > SQL Editor
-- Habilita el hook useRealtimeSync del frontend para sincronizacion en
-- tiempo real entre usuarios sin exponer datos sensibles.
-- ============================================================================

-- ============================================================================
-- SECCION 1: TABLA realtime_events
-- ============================================================================

CREATE TABLE IF NOT EXISTS realtime_events (
  id          bigserial    PRIMARY KEY,
  event_type  varchar(50)  NOT NULL,
  entity      varchar(50)  NOT NULL,
  entity_id   integer,
  scope_id    integer,
  actor_id    integer,
  created_at  timestamptz  NOT NULL DEFAULT now()
);

COMMENT ON TABLE realtime_events IS
  'Tabla de notificaciones para Supabase Realtime. Solo contiene metadatos '
  '(event_type, entity, entity_id, scope_id) — ningun dato sensible. '
  'El frontend suscribe a INSERTs y recarga via API DRF que aplica permisos.';

COMMENT ON COLUMN realtime_events.event_type  IS 'Tipo de accion: created, updated, deleted, estado_changed';
COMMENT ON COLUMN realtime_events.entity      IS 'Tipo de entidad: requisicion, movimiento, lote, producto, dispensacion';
COMMENT ON COLUMN realtime_events.entity_id   IS 'ID del registro afectado';
COMMENT ON COLUMN realtime_events.scope_id    IS 'ID de scope para filtrado (centro_id, farmacia_id, etc.)';
COMMENT ON COLUMN realtime_events.actor_id    IS 'ID del usuario que origino el evento (usuario_id)';

-- ============================================================================
-- SECCION 2: INDICES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_realtime_events_entity
  ON realtime_events(entity, entity_id);

CREATE INDEX IF NOT EXISTS idx_realtime_events_created_at
  ON realtime_events(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_realtime_events_scope
  ON realtime_events(scope_id) WHERE scope_id IS NOT NULL;

-- ============================================================================
-- SECCION 3: PUBLICACION SUPABASE REALTIME
-- Agrega la tabla a la publicacion supabase_realtime para que el hook
-- useRealtimeSync del frontend reciba los INSERTs en tiempo real.
-- ============================================================================

DO $$
BEGIN
  -- Verificar si la publicacion supabase_realtime existe
  IF EXISTS (
    SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime'
  ) THEN
    -- Agregar la tabla solo si no esta ya publicada
    IF NOT EXISTS (
      SELECT 1
      FROM pg_publication_tables
      WHERE pubname = 'supabase_realtime'
        AND tablename = 'realtime_events'
    ) THEN
      ALTER PUBLICATION supabase_realtime ADD TABLE realtime_events;
    END IF;
  END IF;
END $$;

-- ============================================================================
-- SECCION 4: LIMPIEZA AUTOMATICA
-- Funcion y trigger para eliminar eventos con mas de 5 minutos.
-- Previene crecimiento indefinido de la tabla.
-- ============================================================================

CREATE OR REPLACE FUNCTION cleanup_old_realtime_events()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  -- Borrar eventos con mas de 5 minutos cada vez que se inserta uno nuevo
  -- LIMIT evita que la operacion sea costosa si hay un backlog grande
  DELETE FROM realtime_events
  WHERE id IN (
    SELECT id FROM realtime_events
    WHERE created_at < now() - INTERVAL '5 minutes'
    ORDER BY created_at ASC
    LIMIT 500
  );
  RETURN NEW;
END;
$$;

-- Crear trigger solo si no existe
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_trigger
    WHERE tgname = 'trg_cleanup_realtime_events'
      AND tgrelid = 'realtime_events'::regclass
  ) THEN
    CREATE TRIGGER trg_cleanup_realtime_events
      AFTER INSERT ON realtime_events
      FOR EACH ROW EXECUTE FUNCTION cleanup_old_realtime_events();
  END IF;
END $$;

-- ============================================================================
-- SECCION 5: POLITICAS RLS
-- La tabla no necesita RLS porque no contiene datos sensibles.
-- Solo metadatos de navegacion (entity + id).
-- El frontend siempre consulta la API DRF para datos reales.
-- ============================================================================

-- Habilitar RLS pero con politica permisiva de lectura (cualquier usuario autenticado)
ALTER TABLE realtime_events ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE tablename = 'realtime_events' AND policyname = 'realtime_events_select_authenticated'
  ) THEN
    CREATE POLICY realtime_events_select_authenticated
      ON realtime_events FOR SELECT
      TO authenticated
      USING (true);
  END IF;
END $$;

-- Solo el rol service_role (backend Django) puede insertar
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE tablename = 'realtime_events' AND policyname = 'realtime_events_insert_service_role'
  ) THEN
    CREATE POLICY realtime_events_insert_service_role
      ON realtime_events FOR INSERT
      TO service_role
      WITH CHECK (true);
  END IF;
END $$;

-- ============================================================================
-- VERIFICACION FINAL
-- ============================================================================
SELECT
  t.table_name,
  t.table_type,
  p.pubname IS NOT NULL AS en_publicacion_realtime
FROM information_schema.tables t
LEFT JOIN pg_publication_tables p
  ON p.tablename = t.table_name AND p.pubname = 'supabase_realtime'
WHERE t.table_name = 'realtime_events'
  AND t.table_schema = 'public';
