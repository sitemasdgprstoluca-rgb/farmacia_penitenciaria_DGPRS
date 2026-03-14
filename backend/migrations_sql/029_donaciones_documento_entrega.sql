-- ============================================================================
-- MIGRACIÓN 029: Documento de Hoja de Entrega para Donaciones
-- ============================================================================
-- Agrega campos para almacenar PDF de hoja de entrega en donaciones
-- Patrón idéntico a documento_firmado en dispensaciones
-- ============================================================================

-- 1. Agregar columnas de documento de entrega a la tabla donaciones
ALTER TABLE donaciones
ADD COLUMN IF NOT EXISTS documento_entrega_url TEXT,
ADD COLUMN IF NOT EXISTS documento_entrega_nombre VARCHAR(255),
ADD COLUMN IF NOT EXISTS documento_entrega_fecha TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS documento_entrega_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS documento_entrega_tamano INTEGER;

-- 2. Crear índice para consultas por documentos existentes
CREATE INDEX IF NOT EXISTS idx_donaciones_documento_entrega
ON donaciones (id)
WHERE documento_entrega_url IS NOT NULL;

-- 3. Crear bucket de storage para documentos de donaciones
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'donaciones-entregas',
  'donaciones-entregas',
  false,
  10485760, -- 10MB
  ARRAY['application/pdf']::text[]
)
ON CONFLICT (id) DO NOTHING;

-- 4. Políticas RLS para el bucket
CREATE POLICY "Usuarios autenticados pueden subir documentos de donaciones"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'donaciones-entregas');

CREATE POLICY "Usuarios autenticados pueden ver documentos de donaciones"
ON storage.objects FOR SELECT
TO authenticated
USING (bucket_id = 'donaciones-entregas');

CREATE POLICY "Usuarios autenticados pueden eliminar documentos de donaciones"
ON storage.objects FOR DELETE
TO authenticated
USING (bucket_id = 'donaciones-entregas');

-- 5. Verificación
DO $$
BEGIN
  RAISE NOTICE '✅ Migración 029 completada: documento_entrega_* agregado a donaciones';
  RAISE NOTICE '✅ Bucket donaciones-entregas creado';
END $$;
