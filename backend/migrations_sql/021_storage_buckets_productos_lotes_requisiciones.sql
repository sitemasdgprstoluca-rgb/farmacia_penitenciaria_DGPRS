-- =====================================================
-- MIGRACIÓN: Crear buckets de Supabase Storage para Productos, Lotes y Requisiciones
-- Fecha: 2026-03-13
-- Descripción: Buckets para imágenes de productos, PDFs de lotes y documentos firmados de requisiciones
-- =====================================================

-- IMPORTANTE: Este script debe ejecutarse en Supabase Dashboard > SQL Editor

-- =====================================================
-- 1. BUCKET: productos-imagenes
-- =====================================================
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'productos-imagenes',
  'productos-imagenes',
  false,  -- No público, requiere autenticación
  5242880,  -- 5 MB máximo por archivo
  ARRAY['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']::text[]
)
ON CONFLICT (id) DO NOTHING;

-- Política RLS: Permitir lectura a usuarios autenticados
DROP POLICY IF EXISTS "productos_read_policy" ON storage.objects;
CREATE POLICY "productos_read_policy"
  ON storage.objects FOR SELECT
  USING (bucket_id = 'productos-imagenes' AND auth.role() = 'authenticated');

-- Política RLS: Permitir upload a usuarios autenticados
DROP POLICY IF EXISTS "productos_upload_policy" ON storage.objects;
CREATE POLICY "productos_upload_policy"
  ON storage.objects FOR INSERT
  WITH CHECK (bucket_id = 'productos-imagenes' AND auth.role() = 'authenticated');

-- Política RLS: Permitir eliminación solo al creador
DROP POLICY IF EXISTS "productos_delete_policy" ON storage.objects;
CREATE POLICY "productos_delete_policy"
  ON storage.objects FOR DELETE
  USING (bucket_id = 'productos-imagenes' AND auth.role() = 'authenticated');


-- =====================================================
-- 2. BUCKET: lotes-documentos
-- =====================================================
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'lotes-documentos',
  'lotes-documentos',
  false,  -- No público, requiere autenticación
  20971520,  -- 20 MB máximo por archivo
  ARRAY['application/pdf']::text[]
)
ON CONFLICT (id) DO NOTHING;

-- Política RLS: Permitir lectura a usuarios autenticados
DROP POLICY IF EXISTS "lotes_read_policy" ON storage.objects;
CREATE POLICY "lotes_read_policy"
  ON storage.objects FOR SELECT
  USING (bucket_id = 'lotes-documentos' AND auth.role() = 'authenticated');

-- Política RLS: Permitir upload a usuarios autenticados
DROP POLICY IF EXISTS "lotes_upload_policy" ON storage.objects;
CREATE POLICY "lotes_upload_policy"
  ON storage.objects FOR INSERT
  WITH CHECK (bucket_id = 'lotes-documentos' AND auth.role() = 'authenticated');

-- Política RLS: Permitir eliminación solo al creador
DROP POLICY IF EXISTS "lotes_delete_policy" ON storage.objects;
CREATE POLICY "lotes_delete_policy"
  ON storage.objects FOR DELETE
  USING (bucket_id = 'lotes-documentos' AND auth.role() = 'authenticated');


-- =====================================================
-- 3. BUCKET: requisiciones-firmadas
-- =====================================================
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'requisiciones-firmadas',
  'requisiciones-firmadas',
  false,  -- No público, requiere autenticación
  10485760,  -- 10 MB máximo por archivo
  ARRAY['application/pdf', 'image/jpeg', 'image/jpg', 'image/png']::text[]
)
ON CONFLICT (id) DO NOTHING;

-- Política RLS: Permitir lectura a usuarios autenticados
DROP POLICY IF EXISTS "requisiciones_read_policy" ON storage.objects;
CREATE POLICY "requisiciones_read_policy"
  ON storage.objects FOR SELECT
  USING (bucket_id = 'requisiciones-firmadas' AND auth.role() = 'authenticated');

-- Política RLS: Permitir upload a usuarios autenticados
DROP POLICY IF EXISTS "requisiciones_upload_policy" ON storage.objects;
CREATE POLICY "requisiciones_upload_policy"
  ON storage.objects FOR INSERT
  WITH CHECK (bucket_id = 'requisiciones-firmadas' AND auth.role() = 'authenticated');

-- Política RLS: Permitir eliminación solo al creador
DROP POLICY IF EXISTS "requisiciones_delete_policy" ON storage.objects;
CREATE POLICY "requisiciones_delete_policy"
  ON storage.objects FOR DELETE
  USING (bucket_id = 'requisiciones-firmadas' AND auth.role() = 'authenticated');


-- =====================================================
-- VERIFICACIÓN
-- =====================================================
-- Verificar que los buckets se crearon correctamente
SELECT id, name, public, file_size_limit,  allowed_mime_types
FROM storage.buckets
WHERE id IN ('productos-imagenes', 'lotes-documentos', 'requisiciones-firmadas');
