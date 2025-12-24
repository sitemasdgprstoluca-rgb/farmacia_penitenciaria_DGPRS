-- =============================================================================
-- SQL PARA AGREGAR CAMPOS DE AUDITORÍA - NOM-059-SSA1-2015
-- =============================================================================
-- Ejecutar en Supabase para agregar campos de trazabilidad completa
-- Fecha: 2024-12-21
-- 
-- ANÁLISIS DE BD ACTUAL:
-- ✅ Ya existe: subtipo_salida, numero_expediente (con índices)
-- ❌ Falta agregar: subtipo_entrada, subtipo_ajuste, documento_referencia,
--                   es_correccion, movimiento_corregido_id, ip_usuario
-- =============================================================================

-- =============================================================================
-- PASO 1: AGREGAR NUEVAS COLUMNAS A MOVIMIENTOS
-- =============================================================================

-- 1.1 Subtipo de entrada para clasificar entradas de inventario
ALTER TABLE public.movimientos 
ADD COLUMN IF NOT EXISTS subtipo_entrada VARCHAR(30) NULL;

COMMENT ON COLUMN public.movimientos.subtipo_entrada IS 
'NOM-059: Subtipo de entrada - compra, donacion_recibida, transferencia_in, devolucion_centro, ajuste_inventario, inicial, otro';

-- 1.2 Subtipo de ajuste para clasificar ajustes de inventario
ALTER TABLE public.movimientos 
ADD COLUMN IF NOT EXISTS subtipo_ajuste VARCHAR(30) NULL;

COMMENT ON COLUMN public.movimientos.subtipo_ajuste IS 
'NOM-059: Subtipo de ajuste - error_captura, error_conteo, merma, caducidad, robo, sobrante, faltante, reclasificacion, auditoria, otro';

-- 1.3 Documento de referencia (oficio, contrato, etc.)
ALTER TABLE public.movimientos 
ADD COLUMN IF NOT EXISTS documento_referencia VARCHAR(100) NULL;

COMMENT ON COLUMN public.movimientos.documento_referencia IS 
'NOM-059: Número de documento/oficio que respalda el movimiento';

-- 1.4 Marca de corrección
ALTER TABLE public.movimientos 
ADD COLUMN IF NOT EXISTS es_correccion BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN public.movimientos.es_correccion IS 
'NOM-059: Indica si este movimiento es una corrección de otro movimiento';

-- 1.5 Referencia al movimiento corregido (auto-referencia)
ALTER TABLE public.movimientos 
ADD COLUMN IF NOT EXISTS movimiento_corregido_id INTEGER NULL;

-- Agregar FK después de crear la columna
ALTER TABLE public.movimientos 
DROP CONSTRAINT IF EXISTS movimientos_movimiento_corregido_id_fkey;

ALTER TABLE public.movimientos 
ADD CONSTRAINT movimientos_movimiento_corregido_id_fkey 
FOREIGN KEY (movimiento_corregido_id) REFERENCES public.movimientos(id) ON DELETE SET NULL;

COMMENT ON COLUMN public.movimientos.movimiento_corregido_id IS 
'NOM-059: ID del movimiento original que este movimiento corrige';

-- 1.6 IP del usuario para auditoría técnica
ALTER TABLE public.movimientos 
ADD COLUMN IF NOT EXISTS ip_usuario VARCHAR(45) NULL;

COMMENT ON COLUMN public.movimientos.ip_usuario IS 
'Auditoría: Dirección IP desde donde se realizó el movimiento';

-- =============================================================================
-- PASO 2: CREAR ÍNDICES PARA LOS NUEVOS CAMPOS
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_movimientos_subtipo_entrada 
ON public.movimientos(subtipo_entrada) WHERE subtipo_entrada IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_movimientos_subtipo_ajuste 
ON public.movimientos(subtipo_ajuste) WHERE subtipo_ajuste IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_movimientos_documento_ref 
ON public.movimientos(documento_referencia) WHERE documento_referencia IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_movimientos_es_correccion 
ON public.movimientos(es_correccion) WHERE es_correccion = TRUE;

CREATE INDEX IF NOT EXISTS idx_movimientos_corregido_id 
ON public.movimientos(movimiento_corregido_id) WHERE movimiento_corregido_id IS NOT NULL;

-- =============================================================================
-- PASO 3: AGREGAR CONSTRAINTS DE VALIDACIÓN (CHECK)
-- =============================================================================

-- 3.1 Validar subtipo_entrada
ALTER TABLE public.movimientos DROP CONSTRAINT IF EXISTS chk_subtipo_entrada_valido;
ALTER TABLE public.movimientos ADD CONSTRAINT chk_subtipo_entrada_valido CHECK (
    subtipo_entrada IS NULL OR 
    subtipo_entrada IN ('compra', 'donacion_recibida', 'transferencia_in', 'devolucion_centro', 
                        'ajuste_inventario', 'inicial', 'otro')
);

-- 3.2 Validar subtipo_ajuste
ALTER TABLE public.movimientos DROP CONSTRAINT IF EXISTS chk_subtipo_ajuste_valido;
ALTER TABLE public.movimientos ADD CONSTRAINT chk_subtipo_ajuste_valido CHECK (
    subtipo_ajuste IS NULL OR 
    subtipo_ajuste IN ('error_captura', 'error_conteo', 'merma', 'caducidad', 'robo', 
                       'sobrante', 'faltante', 'reclasificacion', 'auditoria', 'otro')
);

-- 3.3 Actualizar/agregar constraint de subtipo_salida (ya existe la columna)
ALTER TABLE public.movimientos DROP CONSTRAINT IF EXISTS chk_subtipo_salida_valido;
ALTER TABLE public.movimientos ADD CONSTRAINT chk_subtipo_salida_valido CHECK (
    subtipo_salida IS NULL OR 
    subtipo_salida IN ('receta', 'consumo_interno', 'transferencia', 'requisicion', 
                       'donacion_salida', 'oficio', 'merma', 'caducidad', 
                       'devolucion_proveedor', 'destruccion', 'otro')
);

-- 3.4 Validar coherencia: corrección debe tener movimiento_corregido_id
ALTER TABLE public.movimientos DROP CONSTRAINT IF EXISTS chk_correccion_coherente;
ALTER TABLE public.movimientos ADD CONSTRAINT chk_correccion_coherente CHECK (
    (es_correccion = FALSE) OR (es_correccion = TRUE AND movimiento_corregido_id IS NOT NULL)
);

-- =============================================================================
-- PASO 4: TABLA DE HISTORIAL DE CORRECCIONES (OPCIONAL)
-- Para auditoría detallada de cambios en movimientos
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.movimientos_historial (
    id SERIAL PRIMARY KEY,
    movimiento_id INTEGER NOT NULL,
    campo_modificado VARCHAR(50) NOT NULL,
    valor_anterior TEXT NULL,
    valor_nuevo TEXT NULL,
    motivo_cambio TEXT NOT NULL,
    usuario_id INTEGER NULL,
    fecha_cambio TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    ip_usuario VARCHAR(45) NULL,
    
    CONSTRAINT movimientos_historial_movimiento_id_fkey 
        FOREIGN KEY (movimiento_id) REFERENCES public.movimientos(id) ON DELETE CASCADE,
    CONSTRAINT movimientos_historial_usuario_id_fkey 
        FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id) ON DELETE SET NULL
);

-- Índices para la tabla de historial
CREATE INDEX IF NOT EXISTS idx_mov_historial_movimiento 
ON public.movimientos_historial(movimiento_id);

CREATE INDEX IF NOT EXISTS idx_mov_historial_fecha 
ON public.movimientos_historial(fecha_cambio);

CREATE INDEX IF NOT EXISTS idx_mov_historial_usuario 
ON public.movimientos_historial(usuario_id);

COMMENT ON TABLE public.movimientos_historial IS 
'NOM-059: Historial de cambios/correcciones a movimientos para auditoría sanitaria';

-- =============================================================================
-- PASO 5: VERIFICACIÓN
-- =============================================================================

-- Verificar columnas agregadas
SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns 
WHERE table_schema = 'public' 
  AND table_name = 'movimientos' 
  AND column_name IN (
    'subtipo_salida', 'subtipo_entrada', 'subtipo_ajuste', 
    'numero_expediente', 'documento_referencia', 
    'es_correccion', 'movimiento_corregido_id', 'ip_usuario'
  )
ORDER BY column_name;

-- Verificar constraints
SELECT 
    conname AS constraint_name,
    contype AS constraint_type
FROM pg_constraint 
WHERE conrelid = 'public.movimientos'::regclass
  AND conname LIKE 'chk_%'
ORDER BY conname;

-- Verificar tabla de historial
SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'movimientos_historial'
) AS historial_existe;
