-- =====================================================
-- MIGRACIÓN: Ampliar columnas de foto_firma en requisiciones
-- Fecha: 2026-03-13
-- Descripción: Las URLs de Supabase Storage exceden varchar(255).
--              Se amplían a varchar(500) para soportar URLs completas.
-- =====================================================

-- IMPORTANTE: Ejecutar en Supabase Dashboard > SQL Editor

-- 1. requisiciones.foto_firma_surtido: varchar(255) -> varchar(500)
ALTER TABLE requisiciones
  ALTER COLUMN foto_firma_surtido TYPE varchar(500);

-- 2. requisiciones.foto_firma_recepcion: varchar(255) -> varchar(500)
ALTER TABLE requisiciones
  ALTER COLUMN foto_firma_recepcion TYPE varchar(500);

-- =====================================================
-- VERIFICACIÓN
-- =====================================================
SELECT table_name, column_name, character_maximum_length
FROM information_schema.columns
WHERE table_name = 'requisiciones'
  AND column_name IN ('foto_firma_surtido', 'foto_firma_recepcion')
ORDER BY column_name;
