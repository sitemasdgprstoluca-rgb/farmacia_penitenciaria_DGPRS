-- =====================================================
-- MIGRACIÓN: Agregar campos para documentos firmados en dispensaciones
-- Fecha: 2026-03-13
-- Descripción: Permite subir PDFs firmados reales en lugar de generar temporales
-- Requiere: Supabase Pro con Storage habilitado
-- =====================================================

-- =====================================================
-- 1. Agregar columnas a tabla dispensaciones
-- =====================================================
ALTER TABLE dispensaciones 
ADD COLUMN IF NOT EXISTS documento_firmado_url TEXT,
ADD COLUMN IF NOT EXISTS documento_firmado_nombre VARCHAR(255),
ADD COLUMN IF NOT EXISTS documento_firmado_fecha TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS documento_firmado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS documento_firmado_tamano INTEGER;

-- Índice para búsquedas por documento
CREATE INDEX IF NOT EXISTS idx_dispensaciones_documento_firmado 
ON dispensaciones(documento_firmado_url) 
WHERE documento_firmado_url IS NOT NULL;

-- Comentarios
COMMENT ON COLUMN dispensaciones.documento_firmado_url IS 'URL del documento PDF firmado subido (almacenado en Supabase Storage)';
COMMENT ON COLUMN dispensaciones.documento_firmado_nombre IS 'Nombre original del archivo PDF firmado';
COMMENT ON COLUMN dispensaciones.documento_firmado_fecha IS 'Fecha y hora en que se subió el documento firmado';
COMMENT ON COLUMN dispensaciones.documento_firmado_por_id IS 'Usuario que subió el documento firmado';
COMMENT ON COLUMN dispensaciones.documento_firmado_tamano IS 'Tamaño del archivo en bytes';

-- =====================================================
-- 2. Crear bucket de Storage en Supabase (ejecutar en Supabase Dashboard)
-- =====================================================
-- NOTA: Este comando se debe ejecutar en el SQL Editor de Supabase:
-- 
-- INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
-- VALUES (
--   'dispensaciones-firmadas',
--   'dispensaciones-firmadas',
--   false,  -- No público, requiere autenticación
--   10485760,  -- 10 MB máximo por archivo
--   ARRAY['application/pdf']::text[]
-- )
-- ON CONFLICT (id) DO NOTHING;

-- =====================================================
-- 3. Política de seguridad RLS para el bucket (ejecutar en Supabase Dashboard)
-- =====================================================
-- NOTA: Estas políticas se deben crear en Supabase Dashboard > Storage > Policies:
--
-- Política 1: Permitir subida solo a usuarios autenticados
-- CREATE POLICY "Usuarios autenticados pueden subir PDFs"
-- ON storage.objects FOR INSERT
-- TO authenticated
-- WITH CHECK (bucket_id = 'dispensaciones-firmadas');
--
-- Política 2: Permitir lectura solo a usuarios autenticados  
-- CREATE POLICY "Usuarios autenticados pueden leer PDFs"
-- ON storage.objects FOR SELECT
-- TO authenticated
-- USING (bucket_id = 'dispensaciones-firmadas');
--
-- Política 3: Permitir eliminación solo al propietario o admin
-- CREATE POLICY "Usuarios pueden eliminar sus propios PDFs"
-- ON storage.objects FOR DELETE
-- TO authenticated
-- USING (bucket_id = 'dispensaciones-firmadas' AND owner = auth.uid());

-- =====================================================
-- 4. Función para validar y limpiar documentos huérfanos
-- =====================================================
CREATE OR REPLACE FUNCTION limpiar_documentos_huerfanos_dispensaciones()
RETURNS INTEGER AS $$
DECLARE
    registros_afectados INTEGER := 0;
BEGIN
    -- Limpiar referencias a documentos eliminados
    UPDATE dispensaciones 
    SET 
        documento_firmado_url = NULL,
        documento_firmado_nombre = NULL,
        documento_firmado_fecha = NULL,
        documento_firmado_por_id = NULL,
        documento_firmado_tamano = NULL
    WHERE documento_firmado_url IS NOT NULL
    AND documento_firmado_url NOT IN (
        SELECT name FROM storage.objects 
        WHERE bucket_id = 'dispensaciones-firmadas'
    );
    
    GET DIAGNOSTICS registros_afectados = ROW_COUNT;
    
    RETURN registros_afectados;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION limpiar_documentos_huerfanos_dispensaciones() IS 
'Limpia referencias a documentos que ya no existen en Storage';

-- =====================================================
-- 5. Trigger para actualizar updated_at al subir documento
-- =====================================================
CREATE OR REPLACE FUNCTION actualizar_fecha_documento_dispensacion()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.documento_firmado_url IS DISTINCT FROM OLD.documento_firmado_url THEN
        NEW.updated_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_actualizar_fecha_documento_dispensacion ON dispensaciones;

CREATE TRIGGER trigger_actualizar_fecha_documento_dispensacion
    BEFORE UPDATE ON dispensaciones
    FOR EACH ROW
    EXECUTE FUNCTION actualizar_fecha_documento_dispensacion();

COMMENT ON FUNCTION actualizar_fecha_documento_dispensacion() IS 
'Actualiza automáticamente la fecha de modificación al cambiar el documento firmado';

-- =====================================================
-- 6. Vista para dispensaciones con información de documento
-- =====================================================
CREATE OR REPLACE VIEW dispensaciones_con_documento AS
SELECT 
    d.*,
    CASE 
        WHEN d.documento_firmado_url IS NOT NULL THEN true 
        ELSE false 
    END AS tiene_documento_firmado,
    u.username AS documento_firmado_por_username,
    u.email AS documento_firmado_por_email
FROM dispensaciones d
LEFT JOIN usuarios u ON d.documento_firmado_por_id = u.id;

COMMENT ON VIEW dispensaciones_con_documento IS 
'Vista de dispensaciones que incluye información sobre documentos firmados';

-- =====================================================
-- 7. Función para obtener estadísticas de documentos
-- =====================================================
CREATE OR REPLACE FUNCTION stats_documentos_firmados_dispensaciones(
    p_centro_id INTEGER DEFAULT NULL,
    p_fecha_inicio DATE DEFAULT NULL,
    p_fecha_fin DATE DEFAULT NULL
)
RETURNS TABLE(
    total_dispensaciones BIGINT,
    con_documento_firmado BIGINT,
    sin_documento_firmado BIGINT,
    porcentaje_con_documento NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*) AS total_dispensaciones,
        COUNT(documento_firmado_url) AS con_documento_firmado,
        COUNT(*) - COUNT(documento_firmado_url) AS sin_documento_firmado,
        ROUND(
            (COUNT(documento_firmado_url)::NUMERIC / NULLIF(COUNT(*), 0)) * 100, 
            2
        ) AS porcentaje_con_documento
    FROM dispensaciones
    WHERE 
        (p_centro_id IS NULL OR centro_id = p_centro_id)
        AND (p_fecha_inicio IS NULL OR DATE(fecha_dispensacion) >= p_fecha_inicio)
        AND (p_fecha_fin IS NULL OR DATE(fecha_dispensacion) <= p_fecha_fin);
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION stats_documentos_firmados_dispensaciones IS 
'Retorna estadísticas sobre documentos firmados subidos en dispensaciones';

-- =====================================================
-- 8. Índices adicionales para optimización
-- =====================================================
CREATE INDEX IF NOT EXISTS idx_dispensaciones_doc_firmado_fecha 
ON dispensaciones(documento_firmado_fecha DESC) 
WHERE documento_firmado_fecha IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_dispensaciones_doc_firmado_por 
ON dispensaciones(documento_firmado_por_id) 
WHERE documento_firmado_por_id IS NOT NULL;

-- =====================================================
-- INSTRUCCIONES DE DEPLOYMENT
-- =====================================================
-- 
-- 1. Ejecutar este archivo en PostgreSQL/Supabase
-- 2. En Supabase Dashboard > Storage, crear el bucket manualmente:
--    - Nombre: dispensaciones-firmadas
--    - Público: No
--    - File size limit: 10 MB
--    - Allowed MIME types: application/pdf
-- 
-- 3. En Supabase Dashboard > Storage > Policies, crear las políticas de seguridad
--    mencionadas en la sección 3
-- 
-- 4. Verificar creación:
--    SELECT * FROM pg_tables WHERE tablename = 'dispensaciones';
--    SELECT * FROM information_schema.columns 
--    WHERE table_name = 'dispensaciones' 
--    AND column_name LIKE 'documento_firmado%';
-- 
-- 5. Probar función de estadísticas:
--    SELECT * FROM stats_documentos_firmados_dispensaciones();
--

-- =====================================================
-- FIN DE MIGRACIÓN
-- =====================================================
