-- ============================================
-- CATÁLOGO INDEPENDIENTE DE PRODUCTOS DE DONACIONES
-- Ejecutar en: Supabase SQL Editor
-- Fecha: 2025-01
-- ============================================
-- 
-- IMPORTANTE: Este catálogo es COMPLETAMENTE SEPARADO del catálogo principal.
-- Las donaciones pueden tener productos con claves y nombres diferentes.
-- El inventario de donaciones NO se mezcla con el inventario principal.
--
-- ============================================

-- 1. Crear tabla de catálogo de productos exclusivo para donaciones
CREATE TABLE IF NOT EXISTS productos_donacion (
    id SERIAL PRIMARY KEY,
    clave VARCHAR(50) UNIQUE NOT NULL,
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT,
    unidad_medida VARCHAR(50) DEFAULT 'PIEZA',
    presentacion VARCHAR(100),
    activo BOOLEAN DEFAULT TRUE,
    notas TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Índices para búsquedas eficientes
CREATE INDEX IF NOT EXISTS idx_productos_donacion_clave ON productos_donacion(clave);
CREATE INDEX IF NOT EXISTS idx_productos_donacion_nombre ON productos_donacion(nombre);
CREATE INDEX IF NOT EXISTS idx_productos_donacion_activo ON productos_donacion(activo);

-- 3. Trigger para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_productos_donacion_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_productos_donacion_updated_at ON productos_donacion;
CREATE TRIGGER trg_productos_donacion_updated_at
    BEFORE UPDATE ON productos_donacion
    FOR EACH ROW
    EXECUTE FUNCTION update_productos_donacion_updated_at();

-- 4. Comentario descriptivo
COMMENT ON TABLE productos_donacion IS 'Catálogo independiente de productos para donaciones - NO se mezcla con productos principales';

-- ============================================
-- MODIFICAR detalle_donaciones para soportar nuevo catálogo
-- ============================================

-- 5. Agregar columna para nuevo catálogo (si no existe)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'detalle_donaciones' 
        AND column_name = 'producto_donacion_id'
    ) THEN
        ALTER TABLE detalle_donaciones 
        ADD COLUMN producto_donacion_id INTEGER REFERENCES productos_donacion(id) ON DELETE RESTRICT;
    END IF;
END $$;

-- 6. Hacer producto_id nullable (legacy) - solo si existe y no es ya nullable
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'detalle_donaciones' 
        AND column_name = 'producto_id'
        AND is_nullable = 'NO'
    ) THEN
        ALTER TABLE detalle_donaciones 
        ALTER COLUMN producto_id DROP NOT NULL;
    END IF;
END $$;

-- 7. Índice para nuevo catálogo
CREATE INDEX IF NOT EXISTS idx_detalle_donaciones_producto_donacion 
ON detalle_donaciones(producto_donacion_id);

-- 8. Comentarios descriptivos
COMMENT ON COLUMN detalle_donaciones.producto_donacion_id IS 'Referencia al catálogo independiente de productos de donaciones';
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'detalle_donaciones' 
        AND column_name = 'producto_id'
    ) THEN
        COMMENT ON COLUMN detalle_donaciones.producto_id IS 'Legacy - Referencia al catálogo principal (deprecated)';
    END IF;
END $$;

-- ============================================
-- VERIFICACIÓN
-- ============================================
SELECT 'Tabla productos_donacion creada correctamente' AS mensaje
WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'productos_donacion');

SELECT 'Columna producto_donacion_id agregada a detalle_donaciones' AS mensaje
WHERE EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'detalle_donaciones' 
    AND column_name = 'producto_donacion_id'
);
