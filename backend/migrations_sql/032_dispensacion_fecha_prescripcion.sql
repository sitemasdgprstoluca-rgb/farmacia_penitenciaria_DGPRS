-- ============================================================================
-- 032_dispensacion_fecha_prescripcion.sql
-- Agrega columna fecha_prescripcion a la tabla dispensaciones
-- Fecha: 2026-03-14
-- ============================================================================
-- INSTRUCCIONES: Ejecutar en Supabase Dashboard > SQL Editor
-- Agrega el campo fecha_prescripcion (DATE) que el frontend recolecta
-- y el backend expone en DispensacionSerializer.
-- ============================================================================

ALTER TABLE dispensaciones
  ADD COLUMN IF NOT EXISTS fecha_prescripcion date;

COMMENT ON COLUMN dispensaciones.fecha_prescripcion IS
  'Fecha de la prescripcion medica (puede diferir de fecha_dispensacion).';

-- Verificacion
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'dispensaciones'
  AND column_name = 'fecha_prescripcion';
