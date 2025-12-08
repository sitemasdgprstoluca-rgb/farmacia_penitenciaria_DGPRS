-- ══════════════════════════════════════════════════════════════════════════════
-- MIGRACIÓN: codigo_barras → clave
-- Ejecutar en Supabase SQL Editor ANTES de insertar productos
-- Fecha: 2025-12-08
-- ══════════════════════════════════════════════════════════════════════════════

-- PASO 1: Verificar estructura actual
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'productos' AND table_schema = 'public'
ORDER BY ordinal_position;

-- PASO 2: Renombrar columna codigo_barras → clave
ALTER TABLE productos RENAME COLUMN codigo_barras TO clave;

-- PASO 3: Asegurar que clave sea NOT NULL (si no lo es ya)
-- Primero, actualizar registros con NULL a un valor temporal si existen
UPDATE productos SET clave = 'TEMP-' || id::text WHERE clave IS NULL;

-- Luego aplicar NOT NULL
ALTER TABLE productos ALTER COLUMN clave SET NOT NULL;

-- PASO 4: Crear o recrear constraint UNIQUE si no existe
-- Eliminar constraint viejo si existe con otro nombre
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'productos_codigo_barras_key') THEN
        ALTER TABLE productos DROP CONSTRAINT productos_codigo_barras_key;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'productos_clave_key') THEN
        ALTER TABLE productos ADD CONSTRAINT productos_clave_key UNIQUE (clave);
    END IF;
END $$;

-- PASO 5: Eliminar índices viejos y crear nuevos
DROP INDEX IF EXISTS productos_codigo_barras_idx;
DROP INDEX IF EXISTS idx_productos_codigo_barras;
CREATE INDEX IF NOT EXISTS idx_productos_clave ON productos(clave);
CREATE INDEX IF NOT EXISTS idx_productos_nombre ON productos(nombre);

-- PASO 6: Verificar estructura final
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'productos' AND table_schema = 'public'
ORDER BY ordinal_position;

-- ══════════════════════════════════════════════════════════════════════════════
-- VERIFICACIÓN DE CONSTRAINTS
-- ══════════════════════════════════════════════════════════════════════════════
SELECT conname, contype, pg_get_constraintdef(oid) 
FROM pg_constraint 
WHERE conrelid = 'productos'::regclass;
