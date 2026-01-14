-- =====================================================
-- MIGRACIÓN: Agregar campo folio_documento a movimientos
-- Fecha: 2026-01-13
-- Descripción: Nuevo campo para almacenar el folio/número
-- de documento oficial de entrada/salida (Formato B)
-- =====================================================

-- Verificar si la columna ya existe antes de agregarla
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'movimientos' 
        AND column_name = 'folio_documento'
    ) THEN
        ALTER TABLE movimientos 
        ADD COLUMN folio_documento VARCHAR(100) NULL;
        
        COMMENT ON COLUMN movimientos.folio_documento IS 
            'Folio o número de documento oficial de entrada/salida para trazabilidad (Formato B)';
        
        RAISE NOTICE 'Columna folio_documento agregada exitosamente a la tabla movimientos';
    ELSE
        RAISE NOTICE 'La columna folio_documento ya existe en la tabla movimientos';
    END IF;
END $$;

-- Crear índice para búsquedas por folio (opcional pero recomendado)
CREATE INDEX IF NOT EXISTS idx_movimientos_folio_documento 
ON movimientos(folio_documento) 
WHERE folio_documento IS NOT NULL;

-- Verificación
SELECT 
    column_name, 
    data_type, 
    character_maximum_length,
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'movimientos' 
AND column_name = 'folio_documento';
