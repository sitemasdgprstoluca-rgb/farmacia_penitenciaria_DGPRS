-- =============================================================================
-- MIGRACIÓN: Agregar campo cantidad_contrato a tabla lotes
-- Fecha: 2026-02-10
-- Descripción: Permite registrar la cantidad total del contrato, separada de
--              la cantidad que realmente llegó (cantidad_inicial/surtida)
-- =============================================================================

-- 1. Agregar columna cantidad_contrato
ALTER TABLE lotes 
ADD COLUMN IF NOT EXISTS cantidad_contrato INTEGER NULL;

-- 2. Agregar comentario descriptivo
COMMENT ON COLUMN lotes.cantidad_contrato IS 
'Cantidad total según contrato. Ej: Si el contrato dice 100 pero solo llegaron 80, aquí se guarda 100. La cantidad_inicial guarda lo que realmente llegó.';

-- 3. OPCIONAL: Establecer cantidad_contrato igual a cantidad_inicial para lotes existentes
-- (Solo ejecutar si se desea que lotes actuales tengan el dato poblado)
-- UPDATE lotes SET cantidad_contrato = cantidad_inicial WHERE cantidad_contrato IS NULL;

-- =============================================================================
-- VERIFICACIÓN
-- =============================================================================
-- Verificar que la columna se agregó correctamente:
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'lotes' AND column_name = 'cantidad_contrato';

-- Ver estructura actual de la tabla lotes:
-- \d lotes

-- =============================================================================
-- NOTAS IMPORTANTES
-- =============================================================================
-- 
-- LÓGICA DE INVENTARIO DESPUÉS DE ESTA MIGRACIÓN:
-- 
-- | Campo              | Descripción                              | Ejemplo |
-- |--------------------|------------------------------------------|---------|
-- | cantidad_contrato  | Total que establece el contrato          | 100     |
-- | cantidad_inicial   | Total que ha llegado (se acumula)        | 80      |
-- | cantidad_actual    | Stock disponible (después de salidas)    | 75      |
-- | CALCULADO: Pendiente = cantidad_contrato - cantidad_inicial         | 20      |
-- 
-- Al RE-IMPORTAR un lote existente:
-- - cantidad_inicial SE SUMA (ej: llegaron 20 más → 80+20=100)
-- - cantidad_actual SE SUMA (ej: 75+20=95)
-- - cantidad_contrato NO CAMBIA (se mantiene en 100)
--
