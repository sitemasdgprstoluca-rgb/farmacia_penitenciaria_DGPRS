-- =====================================================
-- MIGRACIÓN: Configurar políticas de Storage buckets
-- Fecha: 2026-03-13
-- Descripción: Asegurar que todos los buckets permitan
--              operaciones CRUD desde el backend (service_role).
--              También permite lectura pública para buckets públicos.
-- =====================================================

-- IMPORTANTE: Ejecutar en Supabase Dashboard > SQL Editor

-- =====================================================
-- 1. Verificar que los buckets existen y son públicos
-- =====================================================
-- Si alguno no existe, crearlo:
INSERT INTO storage.buckets (id, name, public)
VALUES ('productos-imagenes', 'productos-imagenes', true)
ON CONFLICT (id) DO UPDATE SET public = true;

INSERT INTO storage.buckets (id, name, public)
VALUES ('lotes-documentos', 'lotes-documentos', true)
ON CONFLICT (id) DO UPDATE SET public = true;

INSERT INTO storage.buckets (id, name, public)
VALUES ('requisiciones-firmadas', 'requisiciones-firmadas', true)
ON CONFLICT (id) DO UPDATE SET public = true;

INSERT INTO storage.buckets (id, name, public)
VALUES ('dispensaciones-firmadas', 'dispensaciones-firmadas', true)
ON CONFLICT (id) DO UPDATE SET public = true;

-- =====================================================
-- 2. Políticas de lectura pública (SELECT) para todos los buckets
-- =====================================================
-- productos-imagenes: lectura pública
DO $$ BEGIN
  DROP POLICY IF EXISTS "public_read_productos_imagenes" ON storage.objects;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

CREATE POLICY "public_read_productos_imagenes" ON storage.objects
  FOR SELECT USING (bucket_id = 'productos-imagenes');

-- lotes-documentos: lectura pública
DO $$ BEGIN
  DROP POLICY IF EXISTS "public_read_lotes_documentos" ON storage.objects;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

CREATE POLICY "public_read_lotes_documentos" ON storage.objects
  FOR SELECT USING (bucket_id = 'lotes-documentos');

-- requisiciones-firmadas: lectura pública
DO $$ BEGIN
  DROP POLICY IF EXISTS "public_read_requisiciones_firmadas" ON storage.objects;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

CREATE POLICY "public_read_requisiciones_firmadas" ON storage.objects
  FOR SELECT USING (bucket_id = 'requisiciones-firmadas');

-- dispensaciones-firmadas: lectura pública
DO $$ BEGIN
  DROP POLICY IF EXISTS "public_read_dispensaciones_firmadas" ON storage.objects;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

CREATE POLICY "public_read_dispensaciones_firmadas" ON storage.objects
  FOR SELECT USING (bucket_id = 'dispensaciones-firmadas');

-- =====================================================
-- 3. Políticas de escritura (INSERT) - permite service_role y authenticated
-- =====================================================
DO $$ BEGIN
  DROP POLICY IF EXISTS "allow_insert_productos_imagenes" ON storage.objects;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

CREATE POLICY "allow_insert_productos_imagenes" ON storage.objects
  FOR INSERT WITH CHECK (bucket_id = 'productos-imagenes');

DO $$ BEGIN
  DROP POLICY IF EXISTS "allow_insert_lotes_documentos" ON storage.objects;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

CREATE POLICY "allow_insert_lotes_documentos" ON storage.objects
  FOR INSERT WITH CHECK (bucket_id = 'lotes-documentos');

DO $$ BEGIN
  DROP POLICY IF EXISTS "allow_insert_requisiciones_firmadas" ON storage.objects;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

CREATE POLICY "allow_insert_requisiciones_firmadas" ON storage.objects
  FOR INSERT WITH CHECK (bucket_id = 'requisiciones-firmadas');

DO $$ BEGIN
  DROP POLICY IF EXISTS "allow_insert_dispensaciones_firmadas" ON storage.objects;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

CREATE POLICY "allow_insert_dispensaciones_firmadas" ON storage.objects
  FOR INSERT WITH CHECK (bucket_id = 'dispensaciones-firmadas');

-- =====================================================
-- 4. Políticas de actualización (UPDATE) - para upsert
-- =====================================================
DO $$ BEGIN
  DROP POLICY IF EXISTS "allow_update_productos_imagenes" ON storage.objects;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

CREATE POLICY "allow_update_productos_imagenes" ON storage.objects
  FOR UPDATE USING (bucket_id = 'productos-imagenes');

DO $$ BEGIN
  DROP POLICY IF EXISTS "allow_update_lotes_documentos" ON storage.objects;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

CREATE POLICY "allow_update_lotes_documentos" ON storage.objects
  FOR UPDATE USING (bucket_id = 'lotes-documentos');

DO $$ BEGIN
  DROP POLICY IF EXISTS "allow_update_requisiciones_firmadas" ON storage.objects;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

CREATE POLICY "allow_update_requisiciones_firmadas" ON storage.objects
  FOR UPDATE USING (bucket_id = 'requisiciones-firmadas');

DO $$ BEGIN
  DROP POLICY IF EXISTS "allow_update_dispensaciones_firmadas" ON storage.objects;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

CREATE POLICY "allow_update_dispensaciones_firmadas" ON storage.objects
  FOR UPDATE USING (bucket_id = 'dispensaciones-firmadas');

-- =====================================================
-- 5. Políticas de eliminación (DELETE)
-- =====================================================
DO $$ BEGIN
  DROP POLICY IF EXISTS "allow_delete_productos_imagenes" ON storage.objects;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

CREATE POLICY "allow_delete_productos_imagenes" ON storage.objects
  FOR DELETE USING (bucket_id = 'productos-imagenes');

DO $$ BEGIN
  DROP POLICY IF EXISTS "allow_delete_lotes_documentos" ON storage.objects;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

CREATE POLICY "allow_delete_lotes_documentos" ON storage.objects
  FOR DELETE USING (bucket_id = 'lotes-documentos');

DO $$ BEGIN
  DROP POLICY IF EXISTS "allow_delete_requisiciones_firmadas" ON storage.objects;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

CREATE POLICY "allow_delete_requisiciones_firmadas" ON storage.objects
  FOR DELETE USING (bucket_id = 'requisiciones-firmadas');

DO $$ BEGIN
  DROP POLICY IF EXISTS "allow_delete_dispensaciones_firmadas" ON storage.objects;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

CREATE POLICY "allow_delete_dispensaciones_firmadas" ON storage.objects
  FOR DELETE USING (bucket_id = 'dispensaciones-firmadas');

-- =====================================================
-- VERIFICACIÓN
-- =====================================================
SELECT id, name, public FROM storage.buckets
WHERE id IN ('productos-imagenes', 'lotes-documentos', 'requisiciones-firmadas', 'dispensaciones-firmadas');

SELECT policyname, tablename, cmd
FROM pg_policies
WHERE tablename = 'objects' AND schemaname = 'storage'
ORDER BY policyname;
