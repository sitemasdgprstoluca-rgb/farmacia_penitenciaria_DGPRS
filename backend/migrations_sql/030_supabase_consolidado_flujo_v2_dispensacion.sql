-- ============================================================================
-- 030_supabase_consolidado_flujo_v2_dispensacion.sql
-- Migración consolidada para Supabase
-- Incluye: FLUJO V2 requisiciones + Tracking dual dispensación
-- Fecha: 2026-03-14
-- ============================================================================
-- INSTRUCCIONES: Ejecutar en Supabase Dashboard > SQL Editor
-- Cada bloque usa IF NOT EXISTS / DO $$ para ser idempotente (seguro re-ejecutar)
-- ============================================================================

-- ============================================================================
-- SECCIÓN 1: PRODUCTOS - Campos de dispensación por unidad mínima
-- ============================================================================

-- Presentación comercial (ya debe existir, pero aseguramos NOT NULL)
ALTER TABLE productos
  ADD COLUMN IF NOT EXISTS presentacion varchar(200);

-- Unidad mínima real de dispensación al paciente
-- Ej: 'tableta', 'cápsula', 'mililitro', 'ampolleta', 'dosis', 'sobre', 'pieza'
ALTER TABLE productos
  ADD COLUMN IF NOT EXISTS unidad_minima varchar(50) DEFAULT 'pieza';

-- Factor de conversión: cuántas unidades mínimas tiene 1 presentación comercial
-- Ej: 1 caja de 22 tabletas → factor_conversion = 22
-- Ej: 1 frasco de 120 ml → factor_conversion = 120
-- Si la presentación ya ES la unidad mínima → factor_conversion = 1
ALTER TABLE productos
  ADD COLUMN IF NOT EXISTS factor_conversion integer DEFAULT 1;

-- Constraint factor_conversion: >= 1 (evita división por cero) y <= 9999
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'chk_productos_factor_conversion_rango'
  ) THEN
    ALTER TABLE productos
      ADD CONSTRAINT chk_productos_factor_conversion_rango
      CHECK (factor_conversion >= 1 AND factor_conversion <= 9999);
  END IF;
  -- Eliminar constraint antiguo si existe
  IF EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'chk_productos_factor_conversion_positivo'
  ) THEN
    ALTER TABLE productos DROP CONSTRAINT chk_productos_factor_conversion_positivo;
  END IF;
END $$;

-- Constraint unidad_minima: solo valores autorizados
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'chk_productos_unidad_minima_valida'
  ) THEN
    ALTER TABLE productos
      ADD CONSTRAINT chk_productos_unidad_minima_valida
      CHECK (unidad_minima IN (
        'pieza', 'tableta', 'cápsula', 'mililitro', 'sobre',
        'ampolleta', 'gramo', 'dosis', 'parche', 'supositorio', 'óvulo', 'gota'
      ));
  END IF;
END $$;

-- Constraint presentacion: no puede ser solo números/símbolos (debe tener texto)
-- Nota: PostgreSQL no tiene regexp CHECK nativo antes de pg12, pero sí en pg12+
-- Supabase usa PostgreSQL 15+ así que esto es seguro
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'chk_productos_presentacion_tiene_texto'
  ) THEN
    ALTER TABLE productos
      ADD CONSTRAINT chk_productos_presentacion_tiene_texto
      CHECK (presentacion IS NULL OR presentacion ~ '[A-Za-záéíóúüñÁÉÍÓÚÜÑ]');
  END IF;
END $$;

COMMENT ON COLUMN productos.unidad_minima IS 'Unidad real de dispensación: pieza, tableta, cápsula, mililitro, sobre, ampolleta, gramo, dosis, parche, supositorio, óvulo, gota';
COMMENT ON COLUMN productos.factor_conversion IS 'Cantidad de unidades mínimas por presentación comercial (1-9999). Ej: caja de 22 tabletas = 22. NUNCA 0 (causaría división por cero)';

-- ============================================================================
-- SECCIÓN 2: LOTES - Tracking dual de stock
-- ============================================================================

-- Cantidad en presentaciones originales compradas
ALTER TABLE lotes
  ADD COLUMN IF NOT EXISTS cantidad_presentaciones_inicial integer;

COMMENT ON COLUMN lotes.cantidad_presentaciones_inicial IS
  'Unidades en presentación comercial compradas. Ej: 3 cajas. NULL = dato anterior al cambio';

-- Stock en unidades mínimas dispensables (NUEVO - tracking granular)
ALTER TABLE lotes
  ADD COLUMN IF NOT EXISTS cantidad_actual_unidades integer;

-- Backfill: convertir cantidad_actual × factor_conversion para lotes existentes
UPDATE lotes l
SET cantidad_actual_unidades = l.cantidad_actual * COALESCE(p.factor_conversion, 1)
FROM productos p
WHERE l.producto_id = p.id
  AND l.cantidad_actual_unidades IS NULL;

-- Para lotes sin producto (no debería ocurrir, pero seguridad)
UPDATE lotes
SET cantidad_actual_unidades = cantidad_actual
WHERE cantidad_actual_unidades IS NULL;

-- Aplicar NOT NULL y default
ALTER TABLE lotes
  ALTER COLUMN cantidad_actual_unidades SET NOT NULL,
  ALTER COLUMN cantidad_actual_unidades SET DEFAULT 0;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'chk_lotes_cantidad_unidades_no_negativa'
  ) THEN
    ALTER TABLE lotes
      ADD CONSTRAINT chk_lotes_cantidad_unidades_no_negativa
      CHECK (cantidad_actual_unidades >= 0);
  END IF;
END $$;

COMMENT ON COLUMN lotes.cantidad_actual_unidades IS
  'Stock en unidades mínimas dispensables (tabletas, cápsulas, ml, etc.). '
  'Ej: 21 cajas × 20 tabs/caja = 420. Al dispensar 1 tab → 419. '
  'Presentaciones completas = cantidad_actual_unidades / factor_conversion. '
  'Unidades sueltas = cantidad_actual_unidades % factor_conversion.';

-- Campo activo (necesario para filtros de lotes vigentes)
ALTER TABLE lotes
  ADD COLUMN IF NOT EXISTS activo boolean DEFAULT true;

-- ============================================================================
-- SECCIÓN 3: DETALLES REQUISICIÓN - Campos FLUJO V2
-- ============================================================================

ALTER TABLE detalles_requisicion
  ADD COLUMN IF NOT EXISTS cantidad_autorizada integer;

ALTER TABLE detalles_requisicion
  ADD COLUMN IF NOT EXISTS motivo_ajuste varchar(255);

COMMENT ON COLUMN detalles_requisicion.cantidad_autorizada IS
  'Cantidad aprobada por Farmacia. NULL = aún no autorizado. Puede ser menor a cantidad_solicitada (autorización parcial)';
COMMENT ON COLUMN detalles_requisicion.motivo_ajuste IS
  'Obligatorio cuando cantidad_autorizada < cantidad_solicitada. Explica al Centro por qué se redujo';

-- ============================================================================
-- SECCIÓN 4: DISPENSACIONES - Unidad dispensada
-- ============================================================================

ALTER TABLE detalle_dispensaciones
  ADD COLUMN IF NOT EXISTS unidad_dispensada varchar(50);

COMMENT ON COLUMN detalle_dispensaciones.unidad_dispensada IS
  'Unidad real en que se entregó al paciente: tableta, capsula, ml, etc.';

-- ============================================================================
-- SECCIÓN 5: REQUISICIONES - Campos FLUJO V2 (jerarquía y trazabilidad)
-- ============================================================================

-- Urgencia
ALTER TABLE requisiciones
  ADD COLUMN IF NOT EXISTS es_urgente boolean DEFAULT false;

ALTER TABLE requisiciones
  ADD COLUMN IF NOT EXISTS motivo_urgencia text;

ALTER TABLE requisiciones
  ADD COLUMN IF NOT EXISTS fecha_entrega_solicitada date;

-- Firmas del formulario del centro
ALTER TABLE requisiciones
  ADD COLUMN IF NOT EXISTS firma_solicitante varchar(255);

ALTER TABLE requisiciones
  ADD COLUMN IF NOT EXISTS nombre_solicitante varchar(255);

ALTER TABLE requisiciones
  ADD COLUMN IF NOT EXISTS cargo_solicitante varchar(100);

ALTER TABLE requisiciones
  ADD COLUMN IF NOT EXISTS firma_jefe_area varchar(255);

ALTER TABLE requisiciones
  ADD COLUMN IF NOT EXISTS nombre_jefe_area varchar(255);

ALTER TABLE requisiciones
  ADD COLUMN IF NOT EXISTS cargo_jefe_area varchar(100);

ALTER TABLE requisiciones
  ADD COLUMN IF NOT EXISTS firma_director varchar(255);

ALTER TABLE requisiciones
  ADD COLUMN IF NOT EXISTS nombre_director varchar(255);

ALTER TABLE requisiciones
  ADD COLUMN IF NOT EXISTS cargo_director varchar(100);

-- Fechas del flujo jerárquico
ALTER TABLE requisiciones
  ADD COLUMN IF NOT EXISTS fecha_envio_admin timestamptz;

ALTER TABLE requisiciones
  ADD COLUMN IF NOT EXISTS fecha_autorizacion_admin timestamptz;

ALTER TABLE requisiciones
  ADD COLUMN IF NOT EXISTS fecha_envio_director timestamptz;

ALTER TABLE requisiciones
  ADD COLUMN IF NOT EXISTS fecha_autorizacion_director timestamptz;

ALTER TABLE requisiciones
  ADD COLUMN IF NOT EXISTS fecha_envio_farmacia timestamptz;

ALTER TABLE requisiciones
  ADD COLUMN IF NOT EXISTS fecha_recepcion_farmacia timestamptz;

ALTER TABLE requisiciones
  ADD COLUMN IF NOT EXISTS fecha_autorizacion_farmacia timestamptz;

ALTER TABLE requisiciones
  ADD COLUMN IF NOT EXISTS fecha_recoleccion_limite timestamptz;

ALTER TABLE requisiciones
  ADD COLUMN IF NOT EXISTS fecha_vencimiento timestamptz;

-- Actores del flujo (trazabilidad anti-fraude)
-- administrador_centro: quién autorizó a nivel admin del centro
ALTER TABLE requisiciones
  ADD COLUMN IF NOT EXISTS administrador_centro_id integer
  REFERENCES usuarios(id) ON DELETE SET NULL;

-- director_centro: quién autorizó a nivel director
ALTER TABLE requisiciones
  ADD COLUMN IF NOT EXISTS director_centro_id integer
  REFERENCES usuarios(id) ON DELETE SET NULL;

-- receptor_farmacia: quién recibió físicamente en farmacia
ALTER TABLE requisiciones
  ADD COLUMN IF NOT EXISTS receptor_farmacia_id integer
  REFERENCES usuarios(id) ON DELETE SET NULL;

-- autorizador_farmacia: quién autorizó la cantidad final en farmacia
ALTER TABLE requisiciones
  ADD COLUMN IF NOT EXISTS autorizador_farmacia_id integer
  REFERENCES usuarios(id) ON DELETE SET NULL;

-- surtidor: quién físicamente surtió y entregó
ALTER TABLE requisiciones
  ADD COLUMN IF NOT EXISTS surtidor_id integer
  REFERENCES usuarios(id) ON DELETE SET NULL;

-- Motivos de rechazo/devolución
ALTER TABLE requisiciones
  ADD COLUMN IF NOT EXISTS motivo_rechazo text;

ALTER TABLE requisiciones
  ADD COLUMN IF NOT EXISTS motivo_devolucion text;

ALTER TABLE requisiciones
  ADD COLUMN IF NOT EXISTS motivo_vencimiento text;

ALTER TABLE requisiciones
  ADD COLUMN IF NOT EXISTS observaciones_farmacia text;

-- Índices para consultas frecuentes del flujo
CREATE INDEX IF NOT EXISTS idx_requisiciones_receptor_farmacia
  ON requisiciones(receptor_farmacia_id) WHERE receptor_farmacia_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_requisiciones_administrador_centro
  ON requisiciones(administrador_centro_id) WHERE administrador_centro_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_requisiciones_director_centro
  ON requisiciones(director_centro_id) WHERE director_centro_id IS NOT NULL;

-- ============================================================================
-- SECCIÓN 6: TABLA requisicion_historial_estados (nueva)
-- Historial inmutable de cambios de estado para auditoría completa
-- ============================================================================

CREATE TABLE IF NOT EXISTS requisicion_historial_estados (
  id              serial PRIMARY KEY,
  requisicion_id  integer NOT NULL REFERENCES requisiciones(id) ON DELETE CASCADE,
  estado_anterior varchar(50),
  estado_nuevo    varchar(50) NOT NULL,
  usuario_id      integer REFERENCES usuarios(id) ON DELETE SET NULL,
  fecha_cambio    timestamptz NOT NULL DEFAULT now(),
  accion          varchar(100) DEFAULT 'cambio_estado',
  motivo          text,
  observaciones   text,
  ip_address      varchar(45),
  user_agent      text,
  datos_adicionales jsonb,
  hash_verificacion varchar(64)
);

CREATE INDEX IF NOT EXISTS idx_historial_req_requisicion
  ON requisicion_historial_estados(requisicion_id);

CREATE INDEX IF NOT EXISTS idx_historial_req_fecha
  ON requisicion_historial_estados(fecha_cambio DESC);

CREATE INDEX IF NOT EXISTS idx_historial_req_usuario
  ON requisicion_historial_estados(usuario_id) WHERE usuario_id IS NOT NULL;

COMMENT ON TABLE requisicion_historial_estados IS
  'FLUJO V2: Historial inmutable de cambios de estado de requisiciones. '
  'Cada transición se registra con fecha, usuario, motivo y hash de integridad.';

-- ============================================================================
-- SECCIÓN 7: TABLA requisicion_ajustes_cantidad (nueva)
-- Registro de ajustes de cantidad por Farmacia al autorizar
-- ============================================================================

CREATE TABLE IF NOT EXISTS requisicion_ajustes_cantidad (
  id                      serial PRIMARY KEY,
  detalle_requisicion_id  integer NOT NULL REFERENCES detalles_requisicion(id) ON DELETE CASCADE,
  cantidad_original       integer NOT NULL,
  cantidad_ajustada       integer NOT NULL,
  usuario_id              integer NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
  fecha_ajuste            timestamptz NOT NULL DEFAULT now(),
  motivo_ajuste           text NOT NULL,
  tipo_ajuste             varchar(50) NOT NULL,
  producto_sustituto_id   integer REFERENCES productos(id) ON DELETE SET NULL,
  ip_address              varchar(45),
  created_at              timestamptz NOT NULL DEFAULT now()
);

-- Constraint: tipo_ajuste debe ser uno de los valores válidos
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'chk_ajuste_tipo_valido'
  ) THEN
    ALTER TABLE requisicion_ajustes_cantidad
      ADD CONSTRAINT chk_ajuste_tipo_valido
      CHECK (tipo_ajuste IN (
        'sin_stock', 'producto_agotado', 'sustitucion',
        'correccion_cantidad', 'lote_proximo_caducar'
      ));
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_ajustes_detalle_requisicion
  ON requisicion_ajustes_cantidad(detalle_requisicion_id);

COMMENT ON TABLE requisicion_ajustes_cantidad IS
  'FLUJO V2: Registro de ajustes de cantidad cuando Farmacia autoriza menos de lo solicitado. '
  'Obligatorio para trazabilidad de decisiones de farmacia.';

-- ============================================================================
-- VERIFICACIÓN FINAL
-- ============================================================================
SELECT
  table_name,
  column_name,
  data_type,
  column_default,
  is_nullable
FROM information_schema.columns
WHERE table_name IN (
  'productos', 'lotes', 'detalles_requisicion', 'detalle_dispensaciones',
  'requisiciones', 'requisicion_historial_estados', 'requisicion_ajustes_cantidad'
)
AND column_name IN (
  'presentacion', 'unidad_minima', 'factor_conversion',
  'cantidad_actual_unidades', 'cantidad_presentaciones_inicial', 'activo',
  'cantidad_autorizada', 'motivo_ajuste', 'unidad_dispensada',
  'es_urgente', 'fecha_recoleccion_limite', 'receptor_farmacia_id',
  'administrador_centro_id', 'director_centro_id', 'autorizador_farmacia_id',
  'surtidor_id', 'motivo_rechazo', 'motivo_devolucion', 'observaciones_farmacia',
  'fecha_envio_admin', 'fecha_autorizacion_farmacia'
)
ORDER BY table_name, column_name;
