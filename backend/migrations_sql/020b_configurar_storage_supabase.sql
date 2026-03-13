-- =====================================================
-- EJECUTAR EN SUPABASE SQL EDITOR
-- Configuración de Storage para Documentos Firmados
-- =====================================================

-- =====================================================
-- PASO 1: Crear bucket de Storage
-- =====================================================
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'dispensaciones-firmadas',
  'dispensaciones-firmadas',
  false,
  10485760,
  ARRAY['application/pdf']::text[]
)
ON CONFLICT (id) DO NOTHING;

-- =====================================================
-- PASO 2: Crear políticas de seguridad RLS
-- =====================================================

-- Política 1: Permitir subida solo a usuarios autenticados
CREATE POLICY "Usuarios autenticados pueden subir PDFs"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'dispensaciones-firmadas');

-- Política 2: Permitir lectura solo a usuarios autenticados  
CREATE POLICY "Usuarios autenticados pueden leer PDFs"
ON storage.objects FOR SELECT
TO authenticated
USING (bucket_id = 'dispensaciones-firmadas');

-- Política 3: Permitir eliminación solo al propietario o admin
CREATE POLICY "Usuarios pueden eliminar sus propios PDFs"
ON storage.objects FOR DELETE
TO authenticated
USING (bucket_id = 'dispensaciones-firmadas' AND owner = auth.uid());

-- =====================================================
-- VERIFICACIÓN (Ejecutar después de crear el bucket)
-- =====================================================

-- Verificar que el bucket se creó correctamente
SELECT id, name, public, file_size_limit, allowed_mime_types 
FROM storage.buckets 
WHERE id = 'dispensaciones-firmadas';

-- Verificar las políticas creadas
SELECT schemaname, tablename, policyname 
FROM pg_policies 
WHERE tablename = 'objects' 
AND policyname LIKE '%dispensaciones%';

-- =====================================================
-- FIN - Todo listo para usar
-- =====================================================
