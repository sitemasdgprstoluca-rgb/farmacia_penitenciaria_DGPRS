-- =====================================================
-- MÓDULO: COMPRAS DE CAJA CHICA DEL CENTRO
-- =====================================================
-- Este módulo gestiona las compras que realiza el centro
-- penitenciario cuando la farmacia central no tiene
-- disponibilidad de algún medicamento/insumo.
-- 
-- Características:
-- - Inventario SEPARADO del de farmacia
-- - Solo el centro puede crear/modificar
-- - Farmacia puede auditar (solo lectura)
-- =====================================================

-- Tabla principal de solicitudes/compras de caja chica
CREATE TABLE IF NOT EXISTS compras_caja_chica (
    id SERIAL PRIMARY KEY,
    
    -- Folio único de la compra
    folio VARCHAR(50) NOT NULL UNIQUE,
    
    -- Centro que realiza la compra
    centro_id INTEGER NOT NULL REFERENCES centros(id),
    
    -- Requisición relacionada (opcional - si surgió de una requisición rechazada)
    requisicion_origen_id INTEGER REFERENCES requisiciones(id) ON DELETE SET NULL,
    
    -- Datos del proveedor
    proveedor_nombre VARCHAR(200) NOT NULL,
    proveedor_rfc VARCHAR(20),
    proveedor_direccion TEXT,
    proveedor_telefono VARCHAR(50),
    
    -- Datos de la compra
    fecha_solicitud TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    fecha_compra DATE,
    fecha_recepcion TIMESTAMP WITH TIME ZONE,
    
    -- Documento de respaldo (factura, ticket, etc.)
    numero_factura VARCHAR(100),
    documento_respaldo VARCHAR(500), -- URL o path del archivo
    
    -- Montos
    subtotal DECIMAL(12,2) DEFAULT 0,
    iva DECIMAL(12,2) DEFAULT 0,
    total DECIMAL(12,2) DEFAULT 0,
    
    -- Justificación (por qué se compró por caja chica)
    motivo_compra TEXT NOT NULL, -- Ej: "Farmacia sin existencias", "Urgencia médica"
    
    -- Estado del proceso
    estado VARCHAR(30) DEFAULT 'pendiente' CHECK (estado IN (
        'pendiente',        -- Solicitud creada
        'autorizada',       -- Autorizada por jefe/director
        'comprada',         -- Ya se realizó la compra
        'recibida',         -- Productos recibidos en centro
        'cancelada'         -- Cancelada
    )),
    
    -- Usuarios involucrados
    solicitante_id INTEGER REFERENCES usuarios(id),
    autorizado_por_id INTEGER REFERENCES usuarios(id),
    recibido_por_id INTEGER REFERENCES usuarios(id),
    
    -- Observaciones
    observaciones TEXT,
    motivo_cancelacion TEXT,
    
    -- Auditoría
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Detalle de productos en cada compra
CREATE TABLE IF NOT EXISTS detalle_compras_caja_chica (
    id SERIAL PRIMARY KEY,
    
    compra_id INTEGER NOT NULL REFERENCES compras_caja_chica(id) ON DELETE CASCADE,
    
    -- Producto (puede ser del catálogo o descripción libre)
    producto_id INTEGER REFERENCES productos(id) ON DELETE SET NULL,
    descripcion_producto VARCHAR(500) NOT NULL, -- Descripción manual si no está en catálogo
    
    -- Cantidades
    cantidad_solicitada INTEGER NOT NULL,
    cantidad_comprada INTEGER DEFAULT 0,
    cantidad_recibida INTEGER DEFAULT 0,
    
    -- Datos del lote comprado
    numero_lote VARCHAR(100),
    fecha_caducidad DATE,
    
    -- Precios
    precio_unitario DECIMAL(12,2) DEFAULT 0,
    importe DECIMAL(12,2) DEFAULT 0,
    
    -- Unidad de medida
    unidad_medida VARCHAR(50) DEFAULT 'PIEZA',
    
    -- Notas específicas del producto
    notas TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Inventario de Caja Chica del Centro (stock actual)
-- Este es SEPARADO del inventario principal de farmacia
CREATE TABLE IF NOT EXISTS inventario_caja_chica (
    id SERIAL PRIMARY KEY,
    
    -- Centro dueño de este inventario
    centro_id INTEGER NOT NULL REFERENCES centros(id),
    
    -- Producto
    producto_id INTEGER REFERENCES productos(id) ON DELETE SET NULL,
    descripcion_producto VARCHAR(500) NOT NULL,
    
    -- Lote
    numero_lote VARCHAR(100),
    fecha_caducidad DATE,
    
    -- Cantidades
    cantidad_inicial INTEGER NOT NULL DEFAULT 0,
    cantidad_actual INTEGER NOT NULL DEFAULT 0,
    
    -- Referencia a la compra original
    compra_id INTEGER REFERENCES compras_caja_chica(id) ON DELETE SET NULL,
    detalle_compra_id INTEGER REFERENCES detalle_compras_caja_chica(id) ON DELETE SET NULL,
    
    -- Precio de compra (para valorización)
    precio_unitario DECIMAL(12,2) DEFAULT 0,
    
    -- Ubicación dentro del centro
    ubicacion VARCHAR(200),
    
    -- Estado
    activo BOOLEAN DEFAULT TRUE,
    
    -- Auditoría
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Índice único por centro/producto/lote
    CONSTRAINT uk_inventario_caja_centro_lote UNIQUE (centro_id, producto_id, numero_lote)
);

-- Movimientos del inventario de caja chica
CREATE TABLE IF NOT EXISTS movimientos_caja_chica (
    id SERIAL PRIMARY KEY,
    
    inventario_id INTEGER NOT NULL REFERENCES inventario_caja_chica(id),
    
    -- Tipo de movimiento
    tipo VARCHAR(30) NOT NULL CHECK (tipo IN (
        'entrada',          -- Ingreso por compra
        'salida',           -- Uso/dispensación
        'ajuste_positivo',  -- Ajuste de inventario +
        'ajuste_negativo',  -- Ajuste de inventario -
        'merma',            -- Pérdida, caducidad, etc.
        'devolucion'        -- Devolución al proveedor
    )),
    
    cantidad INTEGER NOT NULL,
    cantidad_anterior INTEGER NOT NULL,
    cantidad_nueva INTEGER NOT NULL,
    
    -- Referencia (expediente del paciente, motivo, etc.)
    referencia VARCHAR(200),
    motivo TEXT,
    
    -- Usuario que realizó el movimiento
    usuario_id INTEGER REFERENCES usuarios(id),
    
    -- Auditoría
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Historial de estados de compras (auditoría)
CREATE TABLE IF NOT EXISTS historial_compras_caja_chica (
    id SERIAL PRIMARY KEY,
    
    compra_id INTEGER NOT NULL REFERENCES compras_caja_chica(id) ON DELETE CASCADE,
    
    estado_anterior VARCHAR(30),
    estado_nuevo VARCHAR(30) NOT NULL,
    
    usuario_id INTEGER REFERENCES usuarios(id),
    
    accion VARCHAR(100) NOT NULL,
    observaciones TEXT,
    ip_address VARCHAR(45),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- ÍNDICES
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_compras_caja_centro ON compras_caja_chica(centro_id);
CREATE INDEX IF NOT EXISTS idx_compras_caja_estado ON compras_caja_chica(estado);
CREATE INDEX IF NOT EXISTS idx_compras_caja_fecha ON compras_caja_chica(fecha_solicitud);
CREATE INDEX IF NOT EXISTS idx_compras_caja_folio ON compras_caja_chica(folio);

CREATE INDEX IF NOT EXISTS idx_detalle_compras_caja ON detalle_compras_caja_chica(compra_id);
CREATE INDEX IF NOT EXISTS idx_detalle_compras_producto ON detalle_compras_caja_chica(producto_id);

CREATE INDEX IF NOT EXISTS idx_inventario_caja_centro ON inventario_caja_chica(centro_id);
CREATE INDEX IF NOT EXISTS idx_inventario_caja_producto ON inventario_caja_chica(producto_id);
CREATE INDEX IF NOT EXISTS idx_inventario_caja_caducidad ON inventario_caja_chica(fecha_caducidad);

CREATE INDEX IF NOT EXISTS idx_movimientos_caja_inventario ON movimientos_caja_chica(inventario_id);
CREATE INDEX IF NOT EXISTS idx_movimientos_caja_tipo ON movimientos_caja_chica(tipo);

-- =====================================================
-- TRIGGERS
-- =====================================================

-- Trigger para generar folio automático
CREATE OR REPLACE FUNCTION generar_folio_compra_caja()
RETURNS TRIGGER AS $$
DECLARE
    v_centro_id INTEGER;
    v_prefijo VARCHAR(10);
    v_consecutivo INTEGER;
    v_folio VARCHAR(50);
BEGIN
    v_centro_id := NEW.centro_id;
    
    -- Obtener consecutivo del día para este centro
    SELECT COALESCE(MAX(
        CAST(SUBSTRING(folio FROM '[0-9]+$') AS INTEGER)
    ), 0) + 1
    INTO v_consecutivo
    FROM compras_caja_chica
    WHERE centro_id = v_centro_id
    AND DATE(created_at) = CURRENT_DATE;
    
    -- Formato: CC-{CENTRO_ID}-{YYYYMMDD}-{CONSECUTIVO}
    v_folio := 'CC-' || LPAD(v_centro_id::TEXT, 3, '0') || '-' || 
               TO_CHAR(CURRENT_DATE, 'YYYYMMDD') || '-' || 
               LPAD(v_consecutivo::TEXT, 4, '0');
    
    NEW.folio := v_folio;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_folio_compra_caja ON compras_caja_chica;
CREATE TRIGGER trg_folio_compra_caja
    BEFORE INSERT ON compras_caja_chica
    FOR EACH ROW
    WHEN (NEW.folio IS NULL OR NEW.folio = '')
    EXECUTE FUNCTION generar_folio_compra_caja();

-- Trigger para actualizar updated_at
CREATE OR REPLACE FUNCTION update_compra_caja_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_compra_caja ON compras_caja_chica;
CREATE TRIGGER trg_update_compra_caja
    BEFORE UPDATE ON compras_caja_chica
    FOR EACH ROW
    EXECUTE FUNCTION update_compra_caja_timestamp();

DROP TRIGGER IF EXISTS trg_update_inventario_caja ON inventario_caja_chica;
CREATE TRIGGER trg_update_inventario_caja
    BEFORE UPDATE ON inventario_caja_chica
    FOR EACH ROW
    EXECUTE FUNCTION update_compra_caja_timestamp();

-- Trigger para calcular totales de compra
CREATE OR REPLACE FUNCTION calcular_total_compra_caja()
RETURNS TRIGGER AS $$
DECLARE
    v_subtotal DECIMAL(12,2);
BEGIN
    SELECT COALESCE(SUM(importe), 0)
    INTO v_subtotal
    FROM detalle_compras_caja_chica
    WHERE compra_id = COALESCE(NEW.compra_id, OLD.compra_id);
    
    UPDATE compras_caja_chica
    SET subtotal = v_subtotal,
        iva = v_subtotal * 0.16,
        total = v_subtotal * 1.16,
        updated_at = NOW()
    WHERE id = COALESCE(NEW.compra_id, OLD.compra_id);
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_calc_total_compra_caja ON detalle_compras_caja_chica;
CREATE TRIGGER trg_calc_total_compra_caja
    AFTER INSERT OR UPDATE OR DELETE ON detalle_compras_caja_chica
    FOR EACH ROW
    EXECUTE FUNCTION calcular_total_compra_caja();

-- Trigger para registrar historial de cambios de estado
CREATE OR REPLACE FUNCTION registrar_historial_compra_caja()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.estado IS DISTINCT FROM NEW.estado THEN
        INSERT INTO historial_compras_caja_chica (
            compra_id, estado_anterior, estado_nuevo, accion, observaciones
        ) VALUES (
            NEW.id, OLD.estado, NEW.estado, 
            'cambio_estado',
            'Estado cambiado de ' || COALESCE(OLD.estado, 'nuevo') || ' a ' || NEW.estado
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_historial_compra_caja ON compras_caja_chica;
CREATE TRIGGER trg_historial_compra_caja
    AFTER UPDATE ON compras_caja_chica
    FOR EACH ROW
    EXECUTE FUNCTION registrar_historial_compra_caja();

-- =====================================================
-- PERMISOS EN TABLA USUARIOS
-- =====================================================

-- Agregar permiso para compras de caja chica si no existe
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'usuarios' AND column_name = 'perm_compras_caja_chica'
    ) THEN
        ALTER TABLE usuarios ADD COLUMN perm_compras_caja_chica BOOLEAN DEFAULT FALSE;
    END IF;
END $$;

-- =====================================================
-- COMENTARIOS
-- =====================================================

COMMENT ON TABLE compras_caja_chica IS 'Compras realizadas por el centro con recursos de caja chica cuando farmacia no tiene existencias';
COMMENT ON TABLE detalle_compras_caja_chica IS 'Productos incluidos en cada compra de caja chica';
COMMENT ON TABLE inventario_caja_chica IS 'Inventario de productos comprados por caja chica (separado del inventario de farmacia)';
COMMENT ON TABLE movimientos_caja_chica IS 'Registro de movimientos del inventario de caja chica';
COMMENT ON TABLE historial_compras_caja_chica IS 'Historial de cambios de estado para auditoría';

COMMENT ON COLUMN compras_caja_chica.motivo_compra IS 'Justificación de por qué se compró por caja chica (ej: farmacia sin existencias)';
COMMENT ON COLUMN inventario_caja_chica.centro_id IS 'Centro dueño de este inventario - NO pertenece a farmacia central';
