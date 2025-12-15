-- Script para modificar la tabla productos en Supabase
-- Ajusta las longitudes de los campos para que coincidan con los datos reales
--
-- PROBLEMA DETECTADO:
-- - nombre: tiene valores de hasta 147 caracteres (máximo encontrado)
-- - presentacion: tiene valores de hasta 110 caracteres  
-- - concentracion: tiene valores de hasta 147 caracteres
-- - sustancia_activa: tiene valores de hasta 25 caracteres (OK)
-- - via_administracion: tiene valores de hasta 4 caracteres (OK)
--
-- SOLUCIÓN: Ajustar a límites seguros que permitan todos los datos

-- ⚠️ IMPORTANTE: Ejecuta este script ANTES de importar los productos

-- Modificar columna 'clave' (asegurar 50 es suficiente)
ALTER TABLE productos 
ALTER COLUMN clave TYPE VARCHAR(50);

-- Modificar columna 'nombre' (necesita mínimo 147, usamos 500 por seguridad)
ALTER TABLE productos 
ALTER COLUMN nombre TYPE VARCHAR(500);

-- Modificar columna 'sustancia_activa' (25 actual, usamos 200 por seguridad)
ALTER TABLE productos 
ALTER COLUMN sustancia_activa TYPE VARCHAR(200);

-- Modificar columna 'presentacion' (necesita mínimo 110, usamos 200 por seguridad)
ALTER TABLE productos 
ALTER COLUMN presentacion TYPE VARCHAR(200);

-- Modificar columna 'concentracion' (necesita mínimo 147, usamos 200 por seguridad)
ALTER TABLE productos 
ALTER COLUMN concentracion TYPE VARCHAR(200);

-- Modificar columna 'via_administracion' (4 actual, 50 es suficiente)
ALTER TABLE productos 
ALTER COLUMN via_administracion TYPE VARCHAR(50);

-- Modificar columna 'categoria' (asegurar espacio suficiente)
ALTER TABLE productos 
ALTER COLUMN categoria TYPE VARCHAR(50);

-- Modificar columna 'unidad_medida' (asegurar espacio suficiente)
ALTER TABLE productos 
ALTER COLUMN unidad_medida TYPE VARCHAR(50);

-- Verificar los cambios
SELECT 
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'productos'
AND table_schema = 'public'
ORDER BY ordinal_position;
