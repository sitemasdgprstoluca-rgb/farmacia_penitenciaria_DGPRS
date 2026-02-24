-- ============================================================================
-- MIGRACIÓN 018: Campos de Auditoría para Sobre-entregas
-- ============================================================================
-- Propósito: Agregar campos de auditoría para sobre-entregas en parcialidades
-- - es_sobreentrega: boolean indicando si fue autorizada como sobre-entrega
-- - motivo_override: texto obligatorio para sobre-entregas (auditoría SOX/ISO)
-- ============================================================================

-- Agregar columnas si no existen
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'lote_parcialidades' AND column_name = 'es_sobreentrega'
    ) THEN
        ALTER TABLE lote_parcialidades ADD COLUMN es_sobreentrega BOOLEAN DEFAULT FALSE;
        COMMENT ON COLUMN lote_parcialidades.es_sobreentrega IS 'True si esta parcialidad fue autorizada como sobre-entrega';
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'lote_parcialidades' AND column_name = 'motivo_override'
    ) THEN
        ALTER TABLE lote_parcialidades ADD COLUMN motivo_override TEXT;
        COMMENT ON COLUMN lote_parcialidades.motivo_override IS 'Motivo obligatorio cuando es sobre-entrega (auditoría SOX/ISO)';
    END IF;
END
$$;

-- Crear índice para consultas de auditoría de sobre-entregas
CREATE INDEX IF NOT EXISTS idx_lote_parcialidades_sobreentrega 
ON lote_parcialidades(es_sobreentrega) 
WHERE es_sobreentrega = true;

-- ============================================================================
-- FIN DE MIGRACIÓN
-- ============================================================================
