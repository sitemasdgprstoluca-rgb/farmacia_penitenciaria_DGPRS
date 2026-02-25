-- ============================================================================
-- TABLA: parcialidad_import_fingerprints
-- Propósito: Control de idempotencia para importaciones de parcialidades
-- Garantiza que reimportar el mismo archivo NO duplique ni sume doble
-- ============================================================================

-- Crear tabla de control de fingerprints
CREATE TABLE IF NOT EXISTS parcialidad_import_fingerprints (
    id BIGSERIAL PRIMARY KEY,
    
    -- Fingerprint único (SHA256 de la fila)
    fingerprint VARCHAR(64) NOT NULL,
    
    -- Checksum del archivo completo (para tracking)
    file_checksum VARCHAR(64),
    
    -- Número de fila en el archivo original
    row_number INTEGER,
    
    -- Lote asociado
    lote_id INTEGER NOT NULL REFERENCES lotes(id) ON DELETE CASCADE,
    
    -- Parcialidad creada/actualizada (nullable si hubo error)
    parcialidad_id INTEGER REFERENCES lote_parcialidades(id) ON DELETE SET NULL,
    
    -- Nombre del archivo importado
    archivo_nombre VARCHAR(255),
    
    -- Usuario que realizó la importación
    imported_by_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    
    -- Acción realizada: CREATED, MERGED, SKIPPED
    action_taken VARCHAR(20) NOT NULL DEFAULT 'CREATED',
    
    -- Cantidad importada en esta fila
    cantidad_importada INTEGER NOT NULL DEFAULT 0,
    
    -- Timestamp de creación
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Índice UNIQUE en fingerprint (garantiza idempotencia)
-- Este es el índice crítico que previene duplicados
CREATE UNIQUE INDEX IF NOT EXISTS idx_pif_fingerprint_unique 
    ON parcialidad_import_fingerprints(fingerprint);

-- Índices para consultas frecuentes
CREATE INDEX IF NOT EXISTS idx_pif_file_checksum 
    ON parcialidad_import_fingerprints(file_checksum);

CREATE INDEX IF NOT EXISTS idx_pif_lote_id 
    ON parcialidad_import_fingerprints(lote_id);

CREATE INDEX IF NOT EXISTS idx_pif_created_at 
    ON parcialidad_import_fingerprints(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_pif_action_taken 
    ON parcialidad_import_fingerprints(action_taken);

-- Índice compuesto para búsquedas de reimportación por archivo
CREATE INDEX IF NOT EXISTS idx_pif_file_row 
    ON parcialidad_import_fingerprints(file_checksum, row_number);

-- ============================================================================
-- COMENTARIOS DE TABLA Y COLUMNAS
-- ============================================================================

COMMENT ON TABLE parcialidad_import_fingerprints IS 
    'Tabla de control para idempotencia de importaciones de parcialidades. '
    'Cada fila importada genera un fingerprint único que previene duplicados en reimportaciones.';

COMMENT ON COLUMN parcialidad_import_fingerprints.fingerprint IS 
    'SHA256 hash único de: file_checksum + row_number + lote_id/numero_lote + clave_producto + proveedor + factura + fecha + cantidad';

COMMENT ON COLUMN parcialidad_import_fingerprints.file_checksum IS 
    'SHA256 del contenido completo del archivo Excel importado';

COMMENT ON COLUMN parcialidad_import_fingerprints.action_taken IS 
    'Acción realizada: CREATED (nuevo registro), MERGED (sumado a existente), SKIPPED (omitido por duplicado)';

-- ============================================================================
-- VISTA DE AUDITORÍA (opcional pero útil)
-- ============================================================================

CREATE OR REPLACE VIEW v_import_audit AS
SELECT 
    pif.id,
    pif.fingerprint,
    pif.file_checksum,
    pif.archivo_nombre,
    pif.row_number,
    pif.action_taken,
    pif.cantidad_importada,
    pif.created_at,
    l.numero_lote,
    p.clave AS producto_clave,
    p.nombre AS producto_nombre,
    u.username AS imported_by_username
FROM parcialidad_import_fingerprints pif
JOIN lotes l ON pif.lote_id = l.id
LEFT JOIN productos p ON l.producto_id = p.id
LEFT JOIN usuarios u ON pif.imported_by_id = u.id
ORDER BY pif.created_at DESC;

COMMENT ON VIEW v_import_audit IS 
    'Vista de auditoría de importaciones con detalles de lote, producto y usuario';

-- ============================================================================
-- FUNCIÓN PARA LIMPIAR FINGERPRINTS ANTIGUOS (mantenimiento)
-- Ejecutar periódicamente para evitar crecimiento excesivo
-- ============================================================================

CREATE OR REPLACE FUNCTION cleanup_old_import_fingerprints(days_to_keep INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM parcialidad_import_fingerprints
    WHERE created_at < NOW() - (days_to_keep || ' days')::INTERVAL;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_old_import_fingerprints IS 
    'Elimina fingerprints de importación más antiguos que X días. '
    'Uso: SELECT cleanup_old_import_fingerprints(90); -- Mantener 90 días';

-- ============================================================================
-- GRANT PERMISOS (ajustar según tu schema de roles)
-- ============================================================================

-- Si usas Supabase, los grants van automáticos
-- Si no, descomenta y ajusta:
-- GRANT SELECT, INSERT ON parcialidad_import_fingerprints TO app_user;
-- GRANT SELECT ON v_import_audit TO app_user;
