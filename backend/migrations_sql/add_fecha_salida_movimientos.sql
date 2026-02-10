-- ============================================================================
-- MIGRACIÓN: Agregar campo fecha_salida a la tabla movimientos
-- Fecha: 2025
-- Descripción: Permite registrar la fecha real de salida física del medicamento,
--              que puede diferir de la fecha de procesamiento en el sistema.
-- ============================================================================

-- Agregar columna fecha_salida (nullable, sin default)
ALTER TABLE movimientos ADD COLUMN IF NOT EXISTS fecha_salida TIMESTAMP WITH TIME ZONE NULL;

-- Índice para consultas por fecha_salida
CREATE INDEX IF NOT EXISTS idx_movimientos_fecha_salida ON movimientos (fecha_salida) WHERE fecha_salida IS NOT NULL;

-- Comentario descriptivo
COMMENT ON COLUMN movimientos.fecha_salida IS 'Fecha real de salida física del medicamento (puede diferir de la fecha de registro en el sistema)';
