-- =====================================================
-- MIGRACIÓN: Módulo de Dispensación a Pacientes (Formato C)
-- Fecha: 2026-01-13
-- Descripción: Crea tablas para gestión de pacientes/internos
-- y dispensación de medicamentos con trazabilidad completa
-- =====================================================

-- =====================================================
-- TABLA: pacientes (Catálogo de Internos)
-- =====================================================
CREATE TABLE IF NOT EXISTS pacientes (
    id SERIAL PRIMARY KEY,
    -- Identificación
    numero_expediente VARCHAR(50) NOT NULL UNIQUE,
    nombre VARCHAR(100) NOT NULL,
    apellido_paterno VARCHAR(100) NOT NULL,
    apellido_materno VARCHAR(100),
    curp VARCHAR(18),
    fecha_nacimiento DATE,
    sexo VARCHAR(1) CHECK (sexo IN ('M', 'F')),
    
    -- Ubicación en el centro
    centro_id INTEGER REFERENCES centros(id) ON DELETE SET NULL,
    dormitorio VARCHAR(50),
    celda VARCHAR(50),
    
    -- Información médica
    tipo_sangre VARCHAR(10),
    alergias TEXT,
    enfermedades_cronicas TEXT,
    observaciones_medicas TEXT,
    
    -- Control
    activo BOOLEAN DEFAULT TRUE,
    fecha_ingreso DATE,
    fecha_egreso DATE,
    motivo_egreso VARCHAR(100),
    
    -- Auditoría
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL
);

-- Índices para búsqueda rápida
CREATE INDEX IF NOT EXISTS idx_pacientes_expediente ON pacientes(numero_expediente);
CREATE INDEX IF NOT EXISTS idx_pacientes_centro ON pacientes(centro_id);
CREATE INDEX IF NOT EXISTS idx_pacientes_nombre ON pacientes(nombre, apellido_paterno);
CREATE INDEX IF NOT EXISTS idx_pacientes_curp ON pacientes(curp) WHERE curp IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_pacientes_activo ON pacientes(activo);

COMMENT ON TABLE pacientes IS 'Catálogo de pacientes/internos para dispensación de medicamentos';
COMMENT ON COLUMN pacientes.numero_expediente IS 'Número único de expediente del interno';
COMMENT ON COLUMN pacientes.dormitorio IS 'Dormitorio/Módulo donde se encuentra ubicado';
COMMENT ON COLUMN pacientes.celda IS 'Celda o espacio específico dentro del dormitorio';

-- =====================================================
-- TABLA: dispensaciones (Registro de entregas)
-- =====================================================
CREATE TABLE IF NOT EXISTS dispensaciones (
    id SERIAL PRIMARY KEY,
    -- Identificación
    folio VARCHAR(50) NOT NULL UNIQUE,
    
    -- Relaciones principales
    paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE RESTRICT,
    centro_id INTEGER NOT NULL REFERENCES centros(id) ON DELETE RESTRICT,
    
    -- Información de la dispensación
    fecha_dispensacion TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    tipo_dispensacion VARCHAR(30) DEFAULT 'normal' CHECK (tipo_dispensacion IN ('normal', 'urgente', 'tratamiento_cronico', 'dosis_unica')),
    
    -- Prescripción médica
    diagnostico TEXT,
    indicaciones TEXT,
    medico_prescriptor VARCHAR(200),
    cedula_medico VARCHAR(20),
    
    -- Estado del registro
    estado VARCHAR(20) DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'dispensada', 'parcial', 'cancelada')),
    
    -- Responsables
    dispensado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    autorizado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    
    -- Firmas digitales (rutas a imágenes)
    firma_paciente VARCHAR(255),
    firma_dispensador VARCHAR(255),
    
    -- Observaciones
    observaciones TEXT,
    motivo_cancelacion TEXT,
    
    -- Auditoría
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_dispensaciones_folio ON dispensaciones(folio);
CREATE INDEX IF NOT EXISTS idx_dispensaciones_paciente ON dispensaciones(paciente_id);
CREATE INDEX IF NOT EXISTS idx_dispensaciones_centro ON dispensaciones(centro_id);
CREATE INDEX IF NOT EXISTS idx_dispensaciones_fecha ON dispensaciones(fecha_dispensacion);
CREATE INDEX IF NOT EXISTS idx_dispensaciones_estado ON dispensaciones(estado);
CREATE INDEX IF NOT EXISTS idx_dispensaciones_tipo ON dispensaciones(tipo_dispensacion);

COMMENT ON TABLE dispensaciones IS 'Registro de dispensación de medicamentos a pacientes (Formato C)';
COMMENT ON COLUMN dispensaciones.folio IS 'Folio único de la dispensación (ej: DISP-20260113-0001)';
COMMENT ON COLUMN dispensaciones.tipo_dispensacion IS 'Tipo: normal, urgente, tratamiento_cronico, dosis_unica';

-- =====================================================
-- TABLA: detalle_dispensaciones (Items dispensados)
-- =====================================================
CREATE TABLE IF NOT EXISTS detalle_dispensaciones (
    id SERIAL PRIMARY KEY,
    -- Relación con dispensación
    dispensacion_id INTEGER NOT NULL REFERENCES dispensaciones(id) ON DELETE CASCADE,
    
    -- Producto dispensado
    producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE RESTRICT,
    lote_id INTEGER REFERENCES lotes(id) ON DELETE SET NULL,
    
    -- Cantidades
    cantidad_prescrita INTEGER NOT NULL CHECK (cantidad_prescrita > 0),
    cantidad_dispensada INTEGER DEFAULT 0 CHECK (cantidad_dispensada >= 0),
    
    -- Información de dosificación
    dosis VARCHAR(100),
    frecuencia VARCHAR(100),
    duracion_tratamiento VARCHAR(100),
    via_administracion VARCHAR(50),
    
    -- Horarios específicos
    horarios TEXT,
    
    -- Estado
    estado VARCHAR(20) DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'dispensado', 'sin_stock', 'sustituido')),
    
    -- Sustitución (si aplica)
    producto_sustituto_id INTEGER REFERENCES productos(id) ON DELETE SET NULL,
    motivo_sustitucion TEXT,
    
    -- Observaciones
    notas TEXT,
    
    -- Auditoría
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_detalle_disp_dispensacion ON detalle_dispensaciones(dispensacion_id);
CREATE INDEX IF NOT EXISTS idx_detalle_disp_producto ON detalle_dispensaciones(producto_id);
CREATE INDEX IF NOT EXISTS idx_detalle_disp_lote ON detalle_dispensaciones(lote_id);
CREATE INDEX IF NOT EXISTS idx_detalle_disp_estado ON detalle_dispensaciones(estado);

COMMENT ON TABLE detalle_dispensaciones IS 'Detalle de productos dispensados a pacientes';
COMMENT ON COLUMN detalle_dispensaciones.cantidad_prescrita IS 'Cantidad indicada por el médico';
COMMENT ON COLUMN detalle_dispensaciones.cantidad_dispensada IS 'Cantidad realmente entregada';
COMMENT ON COLUMN detalle_dispensaciones.horarios IS 'Horarios específicos (ej: 8:00, 14:00, 20:00)';

-- =====================================================
-- TABLA: historial_dispensaciones (Auditoría de cambios)
-- =====================================================
CREATE TABLE IF NOT EXISTS historial_dispensaciones (
    id SERIAL PRIMARY KEY,
    dispensacion_id INTEGER NOT NULL REFERENCES dispensaciones(id) ON DELETE CASCADE,
    accion VARCHAR(50) NOT NULL,
    estado_anterior VARCHAR(20),
    estado_nuevo VARCHAR(20),
    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    detalles JSONB,
    ip_address VARCHAR(45),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hist_disp_dispensacion ON historial_dispensaciones(dispensacion_id);
CREATE INDEX IF NOT EXISTS idx_hist_disp_fecha ON historial_dispensaciones(created_at);

COMMENT ON TABLE historial_dispensaciones IS 'Historial de cambios en dispensaciones para auditoría';

-- =====================================================
-- FUNCIÓN: Generar folio automático de dispensación
-- =====================================================
CREATE OR REPLACE FUNCTION generar_folio_dispensacion()
RETURNS TRIGGER AS $$
DECLARE
    fecha_actual TEXT;
    secuencia INT;
    nuevo_folio TEXT;
BEGIN
    -- Formato: DISP-YYYYMMDD-XXXX
    fecha_actual := TO_CHAR(CURRENT_DATE, 'YYYYMMDD');
    
    -- Obtener siguiente secuencia del día
    SELECT COALESCE(MAX(
        CAST(SUBSTRING(folio FROM 'DISP-\d{8}-(\d+)') AS INTEGER)
    ), 0) + 1
    INTO secuencia
    FROM dispensaciones
    WHERE folio LIKE 'DISP-' || fecha_actual || '-%';
    
    -- Generar folio
    nuevo_folio := 'DISP-' || fecha_actual || '-' || LPAD(secuencia::TEXT, 4, '0');
    
    NEW.folio := nuevo_folio;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para generar folio automático
DROP TRIGGER IF EXISTS trigger_folio_dispensacion ON dispensaciones;
CREATE TRIGGER trigger_folio_dispensacion
    BEFORE INSERT ON dispensaciones
    FOR EACH ROW
    WHEN (NEW.folio IS NULL OR NEW.folio = '')
    EXECUTE FUNCTION generar_folio_dispensacion();

-- =====================================================
-- FUNCIÓN: Actualizar updated_at automáticamente
-- =====================================================
CREATE OR REPLACE FUNCTION update_updated_at_dispensaciones()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers para updated_at
DROP TRIGGER IF EXISTS trigger_updated_pacientes ON pacientes;
CREATE TRIGGER trigger_updated_pacientes
    BEFORE UPDATE ON pacientes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_dispensaciones();

DROP TRIGGER IF EXISTS trigger_updated_dispensaciones ON dispensaciones;
CREATE TRIGGER trigger_updated_dispensaciones
    BEFORE UPDATE ON dispensaciones
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_dispensaciones();

-- =====================================================
-- PERMISOS: Agregar columna de permiso a usuarios
-- =====================================================
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'usuarios' AND column_name = 'perm_dispensaciones'
    ) THEN
        ALTER TABLE usuarios ADD COLUMN perm_dispensaciones BOOLEAN DEFAULT FALSE;
        COMMENT ON COLUMN usuarios.perm_dispensaciones IS 'Permiso para gestionar dispensaciones a pacientes';
    END IF;
END $$;

-- =====================================================
-- VERIFICACIÓN FINAL
-- =====================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Tabla pacientes creada correctamente';
    RAISE NOTICE '✅ Tabla dispensaciones creada correctamente';
    RAISE NOTICE '✅ Tabla detalle_dispensaciones creada correctamente';
    RAISE NOTICE '✅ Tabla historial_dispensaciones creada correctamente';
    RAISE NOTICE '✅ Triggers y funciones configurados';
    RAISE NOTICE '✅ Índices creados para optimización';
    RAISE NOTICE '';
    RAISE NOTICE '🎉 Módulo de Dispensación a Pacientes instalado correctamente';
END $$;
