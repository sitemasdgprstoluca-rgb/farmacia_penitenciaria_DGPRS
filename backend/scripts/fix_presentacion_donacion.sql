-- ============================================================================
-- FIX: Aumentar límite del campo presentacion en productos_donacion
-- ============================================================================
-- 
-- PROBLEMA: El campo presentacion tiene VARCHAR(100) pero algunos productos
-- tienen presentaciones más largas, causando error en la importación.
--
-- SOLUCIÓN: Aumentar a VARCHAR(255)
--
-- EJECUTAR EN PRODUCCIÓN (Supabase):
-- ============================================================================

-- 1. Aumentar el límite del campo presentacion
ALTER TABLE productos_donacion 
ALTER COLUMN presentacion TYPE VARCHAR(255);

-- 2. Verificar el cambio
-- SELECT column_name, data_type, character_maximum_length 
-- FROM information_schema.columns 
-- WHERE table_name = 'productos_donacion' AND column_name = 'presentacion';
