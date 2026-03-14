-- ============================================================================
-- 028_dispensacion_tracking_unidades.sql
-- Tracking de stock en unidades mínimas para dispensación granular
-- ============================================================================
-- PROBLEMA: cantidad_actual es un solo entero (cajas o unidades mezcladas).
--           Al dispensar 1 tableta de una caja de 20, no se puede representar
--           "20 cajas completas + 1 caja con 19 tabletas".
--
-- SOLUCIÓN: Agregar cantidad_actual_unidades que SIEMPRE está en unidades
--           mínimas dispensables (tabletas, cápsulas, ml, etc.)
--           - factor_conversion del producto indica cuántas unidades por presentación
--           - presentaciones_completas = cantidad_actual_unidades / factor_conversion
--           - unidades_sueltas = cantidad_actual_unidades % factor_conversion
--
-- EJEMPLO:  21 cajas × 20 tabletas = 420 tabletas totales
--           Dispensar 1 tableta → 419 tabletas
--           → 20 cajas completas + 19 tabletas sueltas
-- ============================================================================

-- 1. Agregar columna de tracking en unidades mínimas
ALTER TABLE lotes
  ADD COLUMN IF NOT EXISTS cantidad_actual_unidades integer;

-- 2. Backfill: convertir cantidad_actual existente usando factor_conversion del producto
-- NOTA: Asume que cantidad_actual está en PRESENTACIONES (cajas, frascos, etc.)
-- Para productos con factor_conversion=1, no hay cambio (pieza = pieza)
UPDATE lotes l
SET cantidad_actual_unidades = l.cantidad_actual * COALESCE(p.factor_conversion, 1)
FROM productos p
WHERE l.producto_id = p.id
  AND l.cantidad_actual_unidades IS NULL;

-- 3. Asegurar que no queden NULLs
UPDATE lotes SET cantidad_actual_unidades = cantidad_actual
WHERE cantidad_actual_unidades IS NULL;

-- 4. Aplicar NOT NULL y default
ALTER TABLE lotes
  ALTER COLUMN cantidad_actual_unidades SET NOT NULL,
  ALTER COLUMN cantidad_actual_unidades SET DEFAULT 0;

-- 5. Constraint: no puede ser negativo
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

-- 6. Comentario descriptivo
COMMENT ON COLUMN lotes.cantidad_actual_unidades IS
  'Stock en unidades mínimas dispensables (tabletas, cápsulas, ml, etc.). '
  'Ej: 21 cajas × 20 tabs/caja = 420. Al dispensar 1 tab → 419. '
  'Presentaciones completas = cantidad_actual_unidades / factor_conversion. '
  'Unidades sueltas = cantidad_actual_unidades % factor_conversion.';

-- ============================================================================
-- VERIFICACIÓN: Ejecutar después de la migración para validar datos
-- ============================================================================
-- SELECT l.id, l.numero_lote, l.cantidad_actual, l.cantidad_actual_unidades,
--        p.factor_conversion, p.unidad_minima, p.presentacion,
--        l.cantidad_actual_unidades / NULLIF(p.factor_conversion, 0) as presentaciones_calc,
--        l.cantidad_actual_unidades % NULLIF(p.factor_conversion, 0) as unidades_sueltas
-- FROM lotes l
-- JOIN productos p ON l.producto_id = p.id
-- WHERE l.activo = true AND l.cantidad_actual > 0
-- ORDER BY l.id;
