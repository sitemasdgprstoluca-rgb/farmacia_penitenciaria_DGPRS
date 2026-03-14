-- ============================================================================
-- 030_supabase_consolidado_flujo_v2_dispensacion.sql
-- Migracion consolidada para Supabase
-- Incluye: FLUJO V2 requisiciones + Tracking dual dispensacion
-- Fecha: 2026-03-14
-- ============================================================================
-- INSTRUCCIONES: Ejecutar en Supabase Dashboard > SQL Editor
-- Cada bloque usa IF NOT EXISTS / DO $$ para ser idempotente (seguro re-ejecutar)
-- ============================================================================

-- ============================================================================
-- SECCION 1: PRODUCTOS - Campos de dispensacion por unidad minima
-- ============================================================================

ALTER TABLE productos
  ADD COLUMN IF NOT EXISTS presentacion varchar(200);

ALTER TABLE productos
  ADD COLUMN IF NOT EXISTS unidad_minima varchar(50) DEFAULT 'pieza';

ALTER TABLE productos
  ADD COLUMN IF NOT EXISTS factor_conversion integer DEFAULT 1;

-- CHECK: factor_conversion en rango 1-9999 (busca ANY check sobre esa columna)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint c
    JOIN pg_namespace n ON n.oid = c.connamespace
    WHERE c.conrelid = 'productos'::regclass
      AND c.contype = 'c'
      AND pg_get_constraintdef(c.oid) LIKE '%factor_conversion%'
  ) THEN
    ALTER TABLE productos
      ADD CONSTRAINT chk_productos_factor_conversion_rango
      CHECK (factor_conversion >= 1 AND factor_conversion <= 9999);
  END IF;
END $$;

-- CHECK: unidad_minima debe ser un valor de la lista permitida
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint c
    WHERE c.conrelid = 'productos'::regclass
      AND c.contype = 'c'
      AND pg_get_constraintdef(c.oid) LIKE '%unidad_minima%'
  ) THEN
    ALTER TABLE productos
      ADD CONSTRAINT chk_productos_unidad_minima_valida
      CHECK (unidad_minima IN (
        'pieza','tableta','cápsula','mililitro','sobre',
        'ampolleta','gramo','dosis','parche','supositorio','óvulo','gota'
      ));
  END IF;
END $$;

-- CHECK: presentacion debe contener al menos una letra (evita "123", "---", "")
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint c
    WHERE c.conrelid = 'productos'::regclass
      AND c.contype = 'c'
      AND pg_get_constraintdef(c.oid) LIKE '%presentacion%'
  ) THEN
    ALTER TABLE productos
      ADD CONSTRAINT chk_productos_presentacion_tiene_texto
      CHECK (presentacion IS NULL OR presentacion ~ '[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]');
  END IF;
END $$;

COMMENT ON COLUMN productos.presentacion IS 'Descripcion comercial de la presentacion. Ej: CAJA CON 22 TABLETAS, FRASCO 500ML';
COMMENT ON COLUMN productos.unidad_minima IS 'Unidad real de dispensacion: tableta, capsula, ml, ampolleta, dosis, sobre, pieza';
COMMENT ON COLUMN productos.factor_conversion IS 'Cantidad de unidades minimas por presentacion comercial. Ej: caja de 22 tabletas = 22';

-- ============================================================================
-- SECCION 2: LOTES - Tracking dual de stock
-- ============================================================================

ALTER TABLE lotes
  ADD COLUMN IF NOT EXISTS cantidad_presentaciones_inicial integer;

COMMENT ON COLUMN lotes.cantidad_presentaciones_inicial IS
  'Unidades en presentacion comercial compradas. Ej: 3 cajas. NULL = dato anterior al cambio';

ALTER TABLE lotes
  ADD COLUMN IF NOT EXISTS cantidad_actual_unidades integer;

-- Backfill: convertir cantidad_actual x factor_conversion para lotes existentes
-- COALESCE garantiza NULL-safety en ambos lados
UPDATE lotes l
SET cantidad_actual_unidades = COALESCE(l.cantidad_actual, 0) * COALESCE(p.factor_conversion, 1)
FROM productos p
WHERE l.producto_id = p.id
  AND l.cantidad_actual_unidades IS NULL;

-- Seguridad: cubrir lotes huerfanos o con producto sin factor_conversion
UPDATE lotes
SET cantidad_actual_unidades = COALESCE(cantidad_actual, 0)
WHERE cantidad_actual_unidades IS NULL;

-- Aplicar DEFAULT primero, luego NOT NULL (orden seguro en Postgres)
ALTER TABLE lotes
  ALTER COLUMN cantidad_actual_unidades SET DEFAULT 0;

ALTER TABLE lotes
  ALTER COLUMN cantidad_actual_unidades SET NOT NULL;

-- CHECK constraint: busca ANY check sobre cantidad_actual_unidades (evita duplicado)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint c
    WHERE c.conrelid = 'lotes'::regclass
      AND c.contype = 'c'
      AND pg_get_constraintdef(c.oid) LIKE '%cantidad_actual_unidades%'
  ) THEN
    ALTER TABLE lotes
      ADD CONSTRAINT chk_lotes_cantidad_unidades_no_negativa
      CHECK (cantidad_actual_unidades >= 0);
  END IF;
END $$;

COMMENT ON COLUMN lotes.cantidad_actual_unidades IS
  'Stock en unidades minimas dispensables (tabletas, capsulas, ml, etc.)';

ALTER TABLE lotes
  ADD COLUMN IF NOT EXISTS activo boolean DEFAULT true;

-- ============================================================================
-- SECCION 3: DETALLES REQUISICION - Campos FLUJO V2
-- ============================================================================

ALTER TABLE detalles_requisicion
  ADD COLUMN IF NOT EXISTS cantidad_autorizada integer;

ALTER TABLE detalles_requisicion
  ADD COLUMN IF NOT EXISTS motivo_ajuste varchar(255);

COMMENT ON COLUMN detalles_requisicion.cantidad_autorizada IS
  'Cantidad aprobada por Farmacia. NULL = aun no autorizado';
COMMENT ON COLUMN detalles_requisicion.motivo_ajuste IS
  'Obligatorio cuando cantidad_autorizada < cantidad_solicitada';

-- ============================================================================
-- SECCION 4: DISPENSACIONES - Unidad dispensada
-- ============================================================================

ALTER TABLE detalle_dispensaciones
  ADD COLUMN IF NOT EXISTS unidad_dispensada varchar(50);

COMMENT ON COLUMN detalle_dispensaciones.unidad_dispensada IS
  'Unidad real en que se entrego al paciente: tableta, capsula, ml, etc.';

-- ============================================================================
-- SECCION 5: REQUISICIONES - Campos FLUJO V2 (jerarquia y trazabilidad)
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

-- Fechas del flujo jerarquico
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

-- Actores del flujo (trazabilidad) - DO blocks para FK columns (idempotente y seguro)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'requisiciones' AND column_name = 'administrador_centro_id'
  ) THEN
    ALTER TABLE requisiciones
      ADD COLUMN administrador_centro_id integer REFERENCES usuarios(id) ON DELETE SET NULL;
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'requisiciones' AND column_name = 'director_centro_id'
  ) THEN
    ALTER TABLE requisiciones
      ADD COLUMN director_centro_id integer REFERENCES usuarios(id) ON DELETE SET NULL;
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'requisiciones' AND column_name = 'receptor_farmacia_id'
  ) THEN
    ALTER TABLE requisiciones
      ADD COLUMN receptor_farmacia_id integer REFERENCES usuarios(id) ON DELETE SET NULL;
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'requisiciones' AND column_name = 'autorizador_farmacia_id'
  ) THEN
    ALTER TABLE requisiciones
      ADD COLUMN autorizador_farmacia_id integer REFERENCES usuarios(id) ON DELETE SET NULL;
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'requisiciones' AND column_name = 'surtidor_id'
  ) THEN
    ALTER TABLE requisiciones
      ADD COLUMN surtidor_id integer REFERENCES usuarios(id) ON DELETE SET NULL;
  END IF;
END $$;

-- Motivos de rechazo/devolucion
ALTER TABLE requisiciones
  ADD COLUMN IF NOT EXISTS motivo_rechazo text;

ALTER TABLE requisiciones
  ADD COLUMN IF NOT EXISTS motivo_devolucion text;

ALTER TABLE requisiciones
  ADD COLUMN IF NOT EXISTS motivo_vencimiento text;

ALTER TABLE requisiciones
  ADD COLUMN IF NOT EXISTS observaciones_farmacia text;

-- Indices para consultas frecuentes del flujo
CREATE INDEX IF NOT EXISTS idx_requisiciones_receptor_farmacia
  ON requisiciones(receptor_farmacia_id) WHERE receptor_farmacia_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_requisiciones_administrador_centro
  ON requisiciones(administrador_centro_id) WHERE administrador_centro_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_requisiciones_director_centro
  ON requisiciones(director_centro_id) WHERE director_centro_id IS NOT NULL;

-- ============================================================================
-- SECCION 6: TABLA requisicion_historial_estados (nueva)
-- Historial inmutable de cambios de estado para auditoria completa
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
  'FLUJO V2: Historial inmutable de cambios de estado de requisiciones';

-- ============================================================================
-- SECCION 7: TABLA requisicion_ajustes_cantidad (nueva)
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

-- Constraint: tipo_ajuste valido (busca ANY check sobre tipo_ajuste, evita duplicado)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint c
    WHERE c.conrelid = 'requisicion_ajustes_cantidad'::regclass
      AND c.contype = 'c'
      AND pg_get_constraintdef(c.oid) LIKE '%tipo_ajuste%'
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
  'FLUJO V2: Registro de ajustes de cantidad cuando Farmacia autoriza menos de lo solicitado';

-- ============================================================================
-- VERIFICACION FINAL
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
