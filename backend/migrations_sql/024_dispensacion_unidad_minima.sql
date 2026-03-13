-- =====================================================
-- MIGRACIÓN: Sistema de Dispensación por Unidad Mínima
-- Fecha: 2026-03-13
-- Descripción: Agrega campos para conversión de presentación
--              comercial a unidad mínima de dispensación.
--              Ejemplo: 1 caja = 22 tabletas → factor_conversion=22
-- =====================================================

-- IMPORTANTE: Ejecutar en Supabase Dashboard > SQL Editor

-- =====================================================
-- PASO 1: Agregar campos a la tabla productos
-- =====================================================

-- unidad_minima: La unidad real de dispensación al paciente
-- Ej: 'tableta', 'capsula', 'ml', 'ampolleta', 'dosis', 'sobre'
ALTER TABLE productos
  ADD COLUMN IF NOT EXISTS unidad_minima varchar(50) DEFAULT 'pieza';

-- factor_conversion: Cuántas unidades mínimas contiene UNA presentación comercial
-- Ej: 1 caja de 22 tabletas → factor_conversion = 22
-- Ej: 1 frasco de 120 ml → factor_conversion = 120
-- Si la presentación ya ES la unidad mínima → factor_conversion = 1
ALTER TABLE productos
  ADD COLUMN IF NOT EXISTS factor_conversion integer DEFAULT 1
  CHECK (factor_conversion >= 1);

-- Comentarios descriptivos
COMMENT ON COLUMN productos.unidad_minima IS 'Unidad real de dispensación: tableta, capsula, ml, ampolleta, dosis, sobre, pieza';
COMMENT ON COLUMN productos.factor_conversion IS 'Cantidad de unidades mínimas por presentación comercial. Ej: caja de 22 tabletas = 22';

-- =====================================================
-- PASO 2: Agregar campo de presentacion_compra a lotes
-- para saber cuántas "cajas" originales se compraron
-- =====================================================
ALTER TABLE lotes
  ADD COLUMN IF NOT EXISTS cantidad_presentaciones_inicial integer DEFAULT NULL;

COMMENT ON COLUMN lotes.cantidad_presentaciones_inicial IS 'Unidades en presentación comercial compradas. Ej: 3 cajas. NULL = dato anterior al cambio';

-- =====================================================
-- PASO 3: Agregar campo unidad_dispensada a detalle_dispensaciones
-- para registrar en qué unidad se entregó
-- =====================================================
ALTER TABLE detalle_dispensaciones
  ADD COLUMN IF NOT EXISTS unidad_dispensada varchar(50) DEFAULT NULL;

COMMENT ON COLUMN detalle_dispensaciones.unidad_dispensada IS 'Unidad real en que se entregó al paciente: tableta, capsula, etc.';

-- =====================================================
-- VERIFICACIÓN
-- =====================================================
SELECT 'productos' as tabla, column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'productos'
  AND column_name IN ('unidad_minima', 'factor_conversion')
UNION ALL
SELECT 'lotes', column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'lotes'
  AND column_name IN ('cantidad_presentaciones_inicial')
UNION ALL
SELECT 'detalle_dispensaciones', column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'detalle_dispensaciones'
  AND column_name IN ('unidad_dispensada')
ORDER BY tabla, column_name;
