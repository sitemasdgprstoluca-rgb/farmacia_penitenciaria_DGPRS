-- =====================================================
-- MIGRACIÓN: Ampliar columnas de URLs de Storage
-- Fecha: 2026-03-13
-- Descripción: Las URLs de Supabase Storage exceden varchar(100).
--              Se amplían a varchar(500) para soportar URLs completas.
-- =====================================================

-- IMPORTANTE: Ejecutar en Supabase Dashboard > SQL Editor

-- 1. producto_imagenes.imagen: varchar(100) -> varchar(500)
ALTER TABLE producto_imagenes
  ALTER COLUMN imagen TYPE varchar(500);

-- 2. productos.imagen: verificar y ampliar si es necesario
ALTER TABLE productos
  ALTER COLUMN imagen TYPE varchar(500);

-- 3. lote_documentos.archivo: verificar y ampliar
ALTER TABLE lote_documentos
  ALTER COLUMN archivo TYPE varchar(500);

-- 4. lote_documentos.nombre_archivo: ampliar por si acaso
ALTER TABLE lote_documentos
  ALTER COLUMN nombre_archivo TYPE varchar(500);

-- =====================================================
-- VERIFICACIÓN
-- =====================================================
SELECT table_name, column_name, character_maximum_length
FROM information_schema.columns
WHERE table_name IN ('producto_imagenes', 'lote_documentos', 'productos')
  AND column_name IN ('imagen', 'archivo', 'nombre_archivo')
ORDER BY table_name, column_name;
