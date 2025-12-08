-- ============================================================================
-- SQL PARA NUEVAS FUNCIONALIDADES - FARMACIA PENITENCIARIA
-- Ejecutar en Supabase SQL Editor
-- Fecha: Diciembre 2024
-- ============================================================================

-- ============================================================================
-- 1. TABLA PRODUCTO_IMAGENES (Multiples fotos por producto)
-- ============================================================================
CREATE TABLE IF NOT EXISTS producto_imagenes (
    id SERIAL PRIMARY KEY,
    producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
    imagen VARCHAR(255) NOT NULL,
    es_principal BOOLEAN DEFAULT false,
    orden INTEGER DEFAULT 0,
    descripcion VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indice para busqueda por producto
CREATE INDEX IF NOT EXISTS idx_producto_imagenes_producto ON producto_imagenes(producto_id);

-- Comentario de tabla
COMMENT ON TABLE producto_imagenes IS 'Galeria de imagenes para productos';


-- ============================================================================
-- 2. TABLA LOTE_DOCUMENTOS (Facturas, contratos por lote)
-- ============================================================================
CREATE TABLE IF NOT EXISTS lote_documentos (
    id SERIAL PRIMARY KEY,
    lote_id INTEGER NOT NULL REFERENCES lotes(id) ON DELETE CASCADE,
    tipo_documento VARCHAR(50) NOT NULL CHECK (tipo_documento IN ('factura', 'contrato', 'remision', 'otro')),
    numero_documento VARCHAR(100),
    archivo VARCHAR(255) NOT NULL,
    nombre_archivo VARCHAR(255),
    fecha_documento DATE,
    notas TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by INTEGER REFERENCES usuarios(id) ON DELETE SET NULL
);

-- Indices
CREATE INDEX IF NOT EXISTS idx_lote_documentos_lote ON lote_documentos(lote_id);
CREATE INDEX IF NOT EXISTS idx_lote_documentos_tipo ON lote_documentos(tipo_documento);

-- Comentario de tabla
COMMENT ON TABLE lote_documentos IS 'Documentos asociados a lotes (facturas, contratos, remisiones)';


-- ============================================================================
-- 3. TABLAS PARA DONACIONES (ALMACEN SEPARADO - NO AFECTA INVENTARIO PRINCIPAL)
-- ============================================================================
-- IMPORTANTE: El modulo de donaciones funciona como un ALMACEN INDEPENDIENTE.
-- - NO afecta el stock de la tabla 'productos'
-- - NO genera registros en la tabla 'movimientos' (no entra en auditoria)
-- - Tiene su propio control de stock separado
-- - Solo para registro interno del centro, sin afectar trazabilidad oficial
-- ============================================================================

-- Tabla principal de donaciones
CREATE TABLE IF NOT EXISTS donaciones (
    id SERIAL PRIMARY KEY,
    numero VARCHAR(50) UNIQUE NOT NULL,
    donante_nombre VARCHAR(255) NOT NULL,
    donante_tipo VARCHAR(50) CHECK (donante_tipo IN ('empresa', 'gobierno', 'ong', 'particular', 'otro')),
    donante_rfc VARCHAR(20),
    donante_direccion TEXT,
    donante_contacto VARCHAR(100),
    fecha_donacion DATE NOT NULL,
    fecha_recepcion TIMESTAMPTZ DEFAULT NOW(),
    centro_destino_id INTEGER REFERENCES centros(id) ON DELETE SET NULL,
    recibido_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    estado VARCHAR(30) DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'recibida', 'procesada', 'rechazada')),
    notas TEXT,
    documento_donacion VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indices para donaciones
CREATE INDEX IF NOT EXISTS idx_donaciones_estado ON donaciones(estado);
CREATE INDEX IF NOT EXISTS idx_donaciones_centro ON donaciones(centro_destino_id);
CREATE INDEX IF NOT EXISTS idx_donaciones_fecha ON donaciones(fecha_donacion);

-- Comentario de tabla
COMMENT ON TABLE donaciones IS 'Registro de donaciones - ALMACEN SEPARADO que NO afecta inventario principal ni auditoria';

-- Tabla de detalle de donaciones (stock independiente)
CREATE TABLE IF NOT EXISTS detalle_donaciones (
    id SERIAL PRIMARY KEY,
    donacion_id INTEGER NOT NULL REFERENCES donaciones(id) ON DELETE CASCADE,
    producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE RESTRICT,
    -- NO usa lote_id del inventario principal, tiene su propio numero_lote
    numero_lote VARCHAR(100),
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    cantidad_disponible INTEGER NOT NULL DEFAULT 0, -- Stock disponible en almacen donaciones
    fecha_caducidad DATE,
    estado_producto VARCHAR(50) DEFAULT 'bueno' CHECK (estado_producto IN ('bueno', 'regular', 'malo')),
    notas TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Constraint para que cantidad_disponible no sea mayor a cantidad
ALTER TABLE detalle_donaciones ADD CONSTRAINT chk_cantidad_disponible 
    CHECK (cantidad_disponible >= 0 AND cantidad_disponible <= cantidad);

-- Indices para detalle de donaciones
CREATE INDEX IF NOT EXISTS idx_detalle_donaciones_donacion ON detalle_donaciones(donacion_id);
CREATE INDEX IF NOT EXISTS idx_detalle_donaciones_producto ON detalle_donaciones(producto_id);
CREATE INDEX IF NOT EXISTS idx_detalle_donaciones_disponible ON detalle_donaciones(cantidad_disponible) WHERE cantidad_disponible > 0;

-- Comentario de tabla
COMMENT ON TABLE detalle_donaciones IS 'Stock de donaciones - inventario separado del principal';
COMMENT ON COLUMN detalle_donaciones.cantidad_disponible IS 'Cantidad disponible en el almacen de donaciones (se descuenta al entregar)';


-- ============================================================================
-- 3.1 TABLA SALIDAS_DONACIONES (Control de entregas del almacen donaciones)
-- ============================================================================
-- Para registrar cuando se entregan productos del almacén de donaciones
-- Esto permite trazabilidad interna sin afectar movimientos principales

CREATE TABLE IF NOT EXISTS salidas_donaciones (
    id SERIAL PRIMARY KEY,
    detalle_donacion_id INTEGER NOT NULL REFERENCES detalle_donaciones(id) ON DELETE RESTRICT,
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    destinatario VARCHAR(255) NOT NULL,  -- Nombre del interno/paciente o area
    motivo TEXT,
    entregado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    fecha_entrega TIMESTAMPTZ DEFAULT NOW(),
    notas TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indices
CREATE INDEX IF NOT EXISTS idx_salidas_donaciones_detalle ON salidas_donaciones(detalle_donacion_id);
CREATE INDEX IF NOT EXISTS idx_salidas_donaciones_fecha ON salidas_donaciones(fecha_entrega);

-- Comentario
COMMENT ON TABLE salidas_donaciones IS 'Registro de entregas del almacen de donaciones - control interno';


-- ============================================================================
-- 3.2 AGREGAR PERMISO DONACIONES A USUARIOS
-- ============================================================================
-- Para mantener consistencia con los demas permisos (perm_productos, perm_lotes, etc.)

ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS perm_donaciones BOOLEAN DEFAULT false;

COMMENT ON COLUMN usuarios.perm_donaciones IS 'Permiso para acceder al modulo de donaciones';


-- ============================================================================
-- 4. MOVIMIENTOS - NO SE MODIFICA
-- ============================================================================
-- NOTA: El modulo de donaciones NO usa la tabla 'movimientos'.
-- Las donaciones tienen su propio control independiente y NO entran en auditoria.
-- Por lo tanto, NO se agrega el tipo 'donacion' a movimientos.


-- ============================================================================
-- 5. CAMPOS ADICIONALES EN REQUISICIONES
-- ============================================================================

-- Campos para formato de requisicion del centro (firmas) - solo para PDF/impresion
ALTER TABLE requisiciones ADD COLUMN IF NOT EXISTS firma_solicitante VARCHAR(255);
ALTER TABLE requisiciones ADD COLUMN IF NOT EXISTS nombre_solicitante VARCHAR(255);
ALTER TABLE requisiciones ADD COLUMN IF NOT EXISTS cargo_solicitante VARCHAR(100);
ALTER TABLE requisiciones ADD COLUMN IF NOT EXISTS firma_jefe_area VARCHAR(255);
ALTER TABLE requisiciones ADD COLUMN IF NOT EXISTS nombre_jefe_area VARCHAR(255);
ALTER TABLE requisiciones ADD COLUMN IF NOT EXISTS cargo_jefe_area VARCHAR(100);
ALTER TABLE requisiciones ADD COLUMN IF NOT EXISTS firma_director VARCHAR(255);
ALTER TABLE requisiciones ADD COLUMN IF NOT EXISTS nombre_director VARCHAR(255);
ALTER TABLE requisiciones ADD COLUMN IF NOT EXISTS cargo_director VARCHAR(100);

-- Campos de urgencia y fecha de entrega solicitada
ALTER TABLE requisiciones ADD COLUMN IF NOT EXISTS fecha_entrega_solicitada DATE;
ALTER TABLE requisiciones ADD COLUMN IF NOT EXISTS es_urgente BOOLEAN DEFAULT false;
ALTER TABLE requisiciones ADD COLUMN IF NOT EXISTS motivo_urgencia TEXT;

-- Comentarios
COMMENT ON COLUMN requisiciones.firma_solicitante IS 'URL/path de imagen de firma del solicitante (para formato PDF)';
COMMENT ON COLUMN requisiciones.nombre_solicitante IS 'Nombre del solicitante para el formato de requisicion';
COMMENT ON COLUMN requisiciones.cargo_solicitante IS 'Cargo del solicitante para el formato de requisicion';
COMMENT ON COLUMN requisiciones.firma_jefe_area IS 'URL/path de imagen de firma del jefe de area (para formato PDF)';
COMMENT ON COLUMN requisiciones.nombre_jefe_area IS 'Nombre del jefe de area para el formato de requisicion';
COMMENT ON COLUMN requisiciones.cargo_jefe_area IS 'Cargo del jefe de area para el formato de requisicion';
COMMENT ON COLUMN requisiciones.firma_director IS 'URL/path de imagen de firma del director (para formato PDF)';
COMMENT ON COLUMN requisiciones.nombre_director IS 'Nombre del director para el formato de requisicion';
COMMENT ON COLUMN requisiciones.cargo_director IS 'Cargo del director para el formato de requisicion';
COMMENT ON COLUMN requisiciones.fecha_entrega_solicitada IS 'Fecha en que se solicita la entrega de los productos';
COMMENT ON COLUMN requisiciones.es_urgente IS 'Indica si la requisicion es urgente';
COMMENT ON COLUMN requisiciones.motivo_urgencia IS 'Motivo por el cual la requisicion es urgente';


-- ============================================================================
-- 6. TRIGGER PARA UPDATED_AT EN DONACIONES
-- ============================================================================

-- Funcion para actualizar updated_at
CREATE OR REPLACE FUNCTION update_donaciones_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger
DROP TRIGGER IF EXISTS trigger_donaciones_updated_at ON donaciones;
CREATE TRIGGER trigger_donaciones_updated_at
    BEFORE UPDATE ON donaciones
    FOR EACH ROW
    EXECUTE FUNCTION update_donaciones_updated_at();


-- ============================================================================
-- 7. POLITICAS RLS (Row Level Security) - OPCIONAL
-- ============================================================================
-- NOTA: Ejecutar solo si RLS esta habilitado en otras tablas del proyecto.
-- Si no usa RLS, puede omitir esta seccion.

-- Habilitar RLS en nuevas tablas
ALTER TABLE producto_imagenes ENABLE ROW LEVEL SECURITY;
ALTER TABLE lote_documentos ENABLE ROW LEVEL SECURITY;
ALTER TABLE donaciones ENABLE ROW LEVEL SECURITY;
ALTER TABLE detalle_donaciones ENABLE ROW LEVEL SECURITY;
ALTER TABLE salidas_donaciones ENABLE ROW LEVEL SECURITY;

-- Eliminar politicas existentes (si las hay) antes de crear nuevas
DROP POLICY IF EXISTS "producto_imagenes_select_all" ON producto_imagenes;
DROP POLICY IF EXISTS "producto_imagenes_insert_auth" ON producto_imagenes;
DROP POLICY IF EXISTS "producto_imagenes_update_auth" ON producto_imagenes;
DROP POLICY IF EXISTS "producto_imagenes_delete_auth" ON producto_imagenes;

DROP POLICY IF EXISTS "lote_documentos_select_all" ON lote_documentos;
DROP POLICY IF EXISTS "lote_documentos_insert_auth" ON lote_documentos;
DROP POLICY IF EXISTS "lote_documentos_update_auth" ON lote_documentos;
DROP POLICY IF EXISTS "lote_documentos_delete_auth" ON lote_documentos;

DROP POLICY IF EXISTS "donaciones_select_all" ON donaciones;
DROP POLICY IF EXISTS "donaciones_insert_auth" ON donaciones;
DROP POLICY IF EXISTS "donaciones_update_auth" ON donaciones;
DROP POLICY IF EXISTS "donaciones_delete_auth" ON donaciones;

DROP POLICY IF EXISTS "detalle_donaciones_select_all" ON detalle_donaciones;
DROP POLICY IF EXISTS "detalle_donaciones_insert_auth" ON detalle_donaciones;
DROP POLICY IF EXISTS "detalle_donaciones_update_auth" ON detalle_donaciones;
DROP POLICY IF EXISTS "detalle_donaciones_delete_auth" ON detalle_donaciones;

DROP POLICY IF EXISTS "salidas_donaciones_select_all" ON salidas_donaciones;
DROP POLICY IF EXISTS "salidas_donaciones_insert_auth" ON salidas_donaciones;
DROP POLICY IF EXISTS "salidas_donaciones_update_auth" ON salidas_donaciones;
DROP POLICY IF EXISTS "salidas_donaciones_delete_auth" ON salidas_donaciones;

-- Crear politicas permisivas (acceso abierto - ajustar segun necesidades)
-- Producto imagenes
CREATE POLICY "producto_imagenes_select_all" ON producto_imagenes FOR SELECT USING (true);
CREATE POLICY "producto_imagenes_insert_auth" ON producto_imagenes FOR INSERT WITH CHECK (true);
CREATE POLICY "producto_imagenes_update_auth" ON producto_imagenes FOR UPDATE USING (true);
CREATE POLICY "producto_imagenes_delete_auth" ON producto_imagenes FOR DELETE USING (true);

-- Lote documentos
CREATE POLICY "lote_documentos_select_all" ON lote_documentos FOR SELECT USING (true);
CREATE POLICY "lote_documentos_insert_auth" ON lote_documentos FOR INSERT WITH CHECK (true);
CREATE POLICY "lote_documentos_update_auth" ON lote_documentos FOR UPDATE USING (true);
CREATE POLICY "lote_documentos_delete_auth" ON lote_documentos FOR DELETE USING (true);

-- Donaciones
CREATE POLICY "donaciones_select_all" ON donaciones FOR SELECT USING (true);
CREATE POLICY "donaciones_insert_auth" ON donaciones FOR INSERT WITH CHECK (true);
CREATE POLICY "donaciones_update_auth" ON donaciones FOR UPDATE USING (true);
CREATE POLICY "donaciones_delete_auth" ON donaciones FOR DELETE USING (true);

-- Detalle donaciones
CREATE POLICY "detalle_donaciones_select_all" ON detalle_donaciones FOR SELECT USING (true);
CREATE POLICY "detalle_donaciones_insert_auth" ON detalle_donaciones FOR INSERT WITH CHECK (true);
CREATE POLICY "detalle_donaciones_update_auth" ON detalle_donaciones FOR UPDATE USING (true);
CREATE POLICY "detalle_donaciones_delete_auth" ON detalle_donaciones FOR DELETE USING (true);

-- Salidas donaciones
CREATE POLICY "salidas_donaciones_select_all" ON salidas_donaciones FOR SELECT USING (true);
CREATE POLICY "salidas_donaciones_insert_auth" ON salidas_donaciones FOR INSERT WITH CHECK (true);
CREATE POLICY "salidas_donaciones_update_auth" ON salidas_donaciones FOR UPDATE USING (true);
CREATE POLICY "salidas_donaciones_delete_auth" ON salidas_donaciones FOR DELETE USING (true);


-- ============================================================================
-- VERIFICACION FINAL
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '======================================================';
    RAISE NOTICE 'MIGRACION COMPLETADA EXITOSAMENTE';
    RAISE NOTICE '======================================================';
    RAISE NOTICE 'Tablas creadas:';
    RAISE NOTICE '  - producto_imagenes (galeria de fotos)';
    RAISE NOTICE '  - lote_documentos (facturas, contratos)';
    RAISE NOTICE '  - donaciones (ALMACEN SEPARADO)';
    RAISE NOTICE '  - detalle_donaciones (stock independiente)';
    RAISE NOTICE '  - salidas_donaciones (control de entregas)';
    RAISE NOTICE '';
    RAISE NOTICE 'Modificaciones a tablas existentes:';
    RAISE NOTICE '  - requisiciones: campos de firmas y urgencia';
    RAISE NOTICE '  - usuarios: nuevo permiso perm_donaciones';
    RAISE NOTICE '';
    RAISE NOTICE 'IMPORTANTE: Donaciones funciona como almacen separado';
    RAISE NOTICE '  - NO afecta stock de productos';
    RAISE NOTICE '  - NO genera movimientos (sin auditoria)';
    RAISE NOTICE '  - Control independiente para uso interno del centro';
    RAISE NOTICE '======================================================';
END $$;
