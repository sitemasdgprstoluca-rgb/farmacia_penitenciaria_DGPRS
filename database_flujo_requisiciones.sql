-- =============================================================================
-- MIGRACIÓN: Flujo Jerárquico de Requisiciones para Centros Penitenciarios
-- Base de datos: Supabase (PostgreSQL)
-- Fecha: 2024-12-08
-- Descripción: Implementa el flujo de autorización de 5 niveles:
--   1. Médico → 2. Jefe de Área → 3. Director → 4. Farmacia Central → 5. Responsable Farmacia
-- =============================================================================

-- =============================================================================
-- PARTE 1: NUEVOS ROLES DE USUARIO
-- =============================================================================

-- Actualizar constraint de roles en la tabla usuarios
-- Primero eliminar el constraint existente si existe
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'usuarios_rol_check') THEN
        ALTER TABLE usuarios DROP CONSTRAINT usuarios_rol_check;
    END IF;
END $$;

-- Crear nuevo constraint con roles expandidos
ALTER TABLE usuarios ADD CONSTRAINT usuarios_rol_check 
CHECK (rol IN (
    -- Roles de Centro (jerarquía)
    'medico',                    -- Médicos que crean requisiciones
    'jefe_area',                 -- Jefe de Área - autoriza requisiciones
    'director_centro',           -- Director del Centro - autoriza requisiciones
    'centro',                    -- Usuario genérico de centro (legacy/compatibilidad)
    
    -- Roles de Farmacia Central (jerarquía)
    'recepcionista_farmacia',    -- Recibe y revisa requisiciones
    'responsable_farmacia',      -- Autoriza medicamentos y surte
    'farmacia',                  -- Usuario genérico de farmacia (legacy/compatibilidad)
    
    -- Roles administrativos
    'admin_farmacia',            -- Administrador de Farmacia Central
    'admin_sistema',             -- Administrador del sistema completo
    'vista',                     -- Usuario de solo consulta
    
    -- Roles legacy (mantener para compatibilidad)
    'superusuario',
    'usuario_normal',
    'usuario_vista'
));

-- Agregar columna para área/departamento del usuario (para agrupar médicos por área)
ALTER TABLE usuarios 
ADD COLUMN IF NOT EXISTS area_departamento VARCHAR(100);

COMMENT ON COLUMN usuarios.area_departamento IS 'Área o departamento dentro del centro (ej: Urgencias, Consulta Externa, Enfermería)';

-- =============================================================================
-- PARTE 2: NUEVOS ESTADOS DE REQUISICIÓN
-- =============================================================================

-- Actualizar constraint de estados en la tabla requisiciones
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'requisiciones_estado_check') THEN
        ALTER TABLE requisiciones DROP CONSTRAINT requisiciones_estado_check;
    END IF;
END $$;

-- Crear nuevo constraint con estados expandidos para flujo jerárquico
ALTER TABLE requisiciones ADD CONSTRAINT requisiciones_estado_check 
CHECK (estado IN (
    -- Estados iniciales (Centro)
    'borrador',                  -- Médico creando la requisición
    'pendiente_jefe',            -- Esperando autorización del Jefe de Área
    'pendiente_director',        -- Esperando autorización del Director
    
    -- Estados Farmacia Central
    'enviada',                   -- Enviada a Farmacia Central
    'en_revision',               -- Farmacia revisando la requisición
    'autorizada',                -- Autorizada por Responsable de Farmacia
    'en_surtido',                -- En proceso de surtido
    'parcial',                   -- Parcialmente surtida
    'surtida',                   -- Completamente surtida, lista para recolección
    
    -- Estados finales
    'entregada',                 -- Entregada al centro
    
    -- Estados de rechazo/devolución
    'rechazada_jefe',            -- Rechazada por Jefe de Área
    'rechazada_director',        -- Rechazada por Director
    'rechazada_farmacia',        -- Rechazada por Farmacia Central
    'devuelta_centro',           -- Devuelta al centro para corrección
    'cancelada',                 -- Cancelada
    
    -- Estados legacy (compatibilidad)
    'rechazada'                  -- Estado genérico de rechazo (legacy)
));

-- =============================================================================
-- PARTE 3: NUEVAS COLUMNAS PARA TRAZABILIDAD DEL FLUJO
-- =============================================================================

-- Columnas para autorización del Jefe de Área
ALTER TABLE requisiciones 
ADD COLUMN IF NOT EXISTS jefe_area_id INTEGER REFERENCES usuarios(id),
ADD COLUMN IF NOT EXISTS fecha_autorizacion_jefe TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS notas_jefe TEXT,
ADD COLUMN IF NOT EXISTS firma_jefe VARCHAR(500);

-- Columnas para autorización del Director
ALTER TABLE requisiciones 
ADD COLUMN IF NOT EXISTS director_id INTEGER REFERENCES usuarios(id),
ADD COLUMN IF NOT EXISTS fecha_autorizacion_director TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS notas_director TEXT,
ADD COLUMN IF NOT EXISTS firma_director_centro VARCHAR(500);

-- Columnas para recepción en Farmacia
ALTER TABLE requisiciones 
ADD COLUMN IF NOT EXISTS recepcionista_id INTEGER REFERENCES usuarios(id),
ADD COLUMN IF NOT EXISTS fecha_recepcion_farmacia TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS notas_recepcion TEXT;

-- Columna para motivo de rechazo/devolución (consolidar)
ALTER TABLE requisiciones 
ADD COLUMN IF NOT EXISTS motivo_rechazo TEXT,
ADD COLUMN IF NOT EXISTS rechazado_por_id INTEGER REFERENCES usuarios(id),
ADD COLUMN IF NOT EXISTS fecha_rechazo TIMESTAMP WITH TIME ZONE;

-- Columna para historial de devoluciones
ALTER TABLE requisiciones 
ADD COLUMN IF NOT EXISTS veces_devuelta INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS ultima_devolucion TIMESTAMP WITH TIME ZONE;

-- Comentarios descriptivos
COMMENT ON COLUMN requisiciones.jefe_area_id IS 'ID del Jefe de Área que autorizó la requisición';
COMMENT ON COLUMN requisiciones.fecha_autorizacion_jefe IS 'Fecha/hora de autorización por Jefe de Área';
COMMENT ON COLUMN requisiciones.director_id IS 'ID del Director que autorizó la requisición';
COMMENT ON COLUMN requisiciones.fecha_autorizacion_director IS 'Fecha/hora de autorización por Director';
COMMENT ON COLUMN requisiciones.recepcionista_id IS 'ID del recepcionista de Farmacia que recibió';
COMMENT ON COLUMN requisiciones.fecha_recepcion_farmacia IS 'Fecha/hora de recepción en Farmacia Central';
COMMENT ON COLUMN requisiciones.motivo_rechazo IS 'Motivo del rechazo o devolución';
COMMENT ON COLUMN requisiciones.veces_devuelta IS 'Número de veces que la requisición ha sido devuelta para corrección';

-- =============================================================================
-- PARTE 4: TABLA DE HISTORIAL DE AUTORIZACIONES (TRAZABILIDAD COMPLETA)
-- =============================================================================

CREATE TABLE IF NOT EXISTS historial_autorizaciones (
    id SERIAL PRIMARY KEY,
    requisicion_id INTEGER NOT NULL REFERENCES requisiciones(id) ON DELETE CASCADE,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    accion VARCHAR(50) NOT NULL,  -- autorizar_jefe, autorizar_director, autorizar_farmacia, rechazar, devolver, etc.
    estado_anterior VARCHAR(50),
    estado_nuevo VARCHAR(50),
    notas TEXT,
    firma_digital VARCHAR(500),
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para rendimiento
CREATE INDEX IF NOT EXISTS idx_historial_auth_requisicion ON historial_autorizaciones(requisicion_id);
CREATE INDEX IF NOT EXISTS idx_historial_auth_usuario ON historial_autorizaciones(usuario_id);
CREATE INDEX IF NOT EXISTS idx_historial_auth_fecha ON historial_autorizaciones(created_at);
CREATE INDEX IF NOT EXISTS idx_historial_auth_accion ON historial_autorizaciones(accion);

COMMENT ON TABLE historial_autorizaciones IS 'Historial completo de autorizaciones y cambios de estado de requisiciones';
COMMENT ON COLUMN historial_autorizaciones.accion IS 'Tipo de acción: enviar_jefe, autorizar_jefe, rechazar_jefe, autorizar_director, rechazar_director, enviar_farmacia, autorizar_farmacia, rechazar_farmacia, devolver, surtir, entregar';
COMMENT ON COLUMN historial_autorizaciones.firma_digital IS 'Firma o sello digital del autorizador (base64 o URL)';

-- =============================================================================
-- PARTE 5: PERMISOS GRANULARES POR ROL
-- =============================================================================

-- Agregar columnas de permisos específicos para el flujo de requisiciones
ALTER TABLE usuarios
ADD COLUMN IF NOT EXISTS perm_autorizar_jefe BOOLEAN DEFAULT NULL,
ADD COLUMN IF NOT EXISTS perm_autorizar_director BOOLEAN DEFAULT NULL,
ADD COLUMN IF NOT EXISTS perm_recibir_farmacia BOOLEAN DEFAULT NULL,
ADD COLUMN IF NOT EXISTS perm_autorizar_farmacia BOOLEAN DEFAULT NULL,
ADD COLUMN IF NOT EXISTS perm_surtir BOOLEAN DEFAULT NULL;

COMMENT ON COLUMN usuarios.perm_autorizar_jefe IS 'Permiso para autorizar requisiciones como Jefe de Área';
COMMENT ON COLUMN usuarios.perm_autorizar_director IS 'Permiso para autorizar requisiciones como Director';
COMMENT ON COLUMN usuarios.perm_recibir_farmacia IS 'Permiso para recibir requisiciones en Farmacia Central';
COMMENT ON COLUMN usuarios.perm_autorizar_farmacia IS 'Permiso para autorizar requisiciones en Farmacia Central';
COMMENT ON COLUMN usuarios.perm_surtir IS 'Permiso para surtir requisiciones';

-- =============================================================================
-- PARTE 6: ÍNDICES ADICIONALES PARA RENDIMIENTO
-- =============================================================================

-- Índices para filtros comunes del nuevo flujo
CREATE INDEX IF NOT EXISTS idx_requisiciones_estado_centro 
ON requisiciones(estado, centro_origen_id) 
WHERE estado IN ('borrador', 'pendiente_jefe', 'pendiente_director', 'devuelta_centro');

CREATE INDEX IF NOT EXISTS idx_requisiciones_jefe_area 
ON requisiciones(jefe_area_id, fecha_autorizacion_jefe);

CREATE INDEX IF NOT EXISTS idx_requisiciones_director 
ON requisiciones(director_id, fecha_autorizacion_director);

CREATE INDEX IF NOT EXISTS idx_requisiciones_farmacia 
ON requisiciones(estado) 
WHERE estado IN ('enviada', 'en_revision', 'autorizada', 'en_surtido', 'parcial', 'surtida');

-- Índice para área/departamento de usuarios
CREATE INDEX IF NOT EXISTS idx_usuarios_area 
ON usuarios(centro_id, area_departamento) 
WHERE area_departamento IS NOT NULL;

-- =============================================================================
-- PARTE 7: VISTAS ÚTILES PARA REPORTES Y DASHBOARDS
-- =============================================================================

-- Vista: Requisiciones pendientes por nivel de autorización
CREATE OR REPLACE VIEW v_requisiciones_pendientes AS
SELECT 
    r.id,
    r.numero,
    r.estado,
    r.fecha_solicitud,
    c_origen.nombre AS centro_origen,
    sol.username AS solicitante,
    sol.first_name || ' ' || sol.last_name AS nombre_solicitante,
    CASE 
        WHEN r.estado = 'pendiente_jefe' THEN 'Jefe de Área'
        WHEN r.estado = 'pendiente_director' THEN 'Director'
        WHEN r.estado = 'enviada' THEN 'Farmacia Central'
        WHEN r.estado = 'autorizada' THEN 'Surtido'
        ELSE r.estado
    END AS pendiente_de,
    EXTRACT(EPOCH FROM (NOW() - r.fecha_solicitud))/3600 AS horas_pendiente
FROM requisiciones r
LEFT JOIN centros c_origen ON r.centro_origen_id = c_origen.id
LEFT JOIN usuarios sol ON r.solicitante_id = sol.id
WHERE r.estado IN ('pendiente_jefe', 'pendiente_director', 'enviada', 'autorizada', 'en_surtido')
ORDER BY r.fecha_solicitud ASC;

-- Vista: Estadísticas de autorizaciones por usuario
CREATE OR REPLACE VIEW v_estadisticas_autorizadores AS
SELECT 
    u.id AS usuario_id,
    u.username,
    u.first_name || ' ' || u.last_name AS nombre_completo,
    u.rol,
    c.nombre AS centro,
    COUNT(CASE WHEN ha.accion LIKE 'autorizar%' THEN 1 END) AS total_autorizadas,
    COUNT(CASE WHEN ha.accion LIKE 'rechazar%' THEN 1 END) AS total_rechazadas,
    COUNT(CASE WHEN ha.accion = 'devolver' THEN 1 END) AS total_devueltas,
    AVG(
        CASE WHEN ha.accion LIKE 'autorizar%' 
        THEN EXTRACT(EPOCH FROM (ha.created_at - r.fecha_solicitud))/3600 
        END
    ) AS promedio_horas_autorizacion
FROM usuarios u
LEFT JOIN centros c ON u.centro_id = c.id
LEFT JOIN historial_autorizaciones ha ON u.id = ha.usuario_id
LEFT JOIN requisiciones r ON ha.requisicion_id = r.id
WHERE u.rol IN ('jefe_area', 'director_centro', 'responsable_farmacia', 'admin_farmacia')
GROUP BY u.id, u.username, u.first_name, u.last_name, u.rol, c.nombre;

-- Vista: Flujo completo de una requisición (para trazabilidad)
CREATE OR REPLACE VIEW v_trazabilidad_requisicion AS
SELECT 
    r.id AS requisicion_id,
    r.numero,
    ha.accion,
    ha.estado_anterior,
    ha.estado_nuevo,
    ha.notas,
    u.username AS usuario,
    u.first_name || ' ' || u.last_name AS nombre_usuario,
    u.rol AS rol_usuario,
    ha.created_at AS fecha_accion,
    ha.ip_address
FROM requisiciones r
JOIN historial_autorizaciones ha ON r.id = ha.requisicion_id
JOIN usuarios u ON ha.usuario_id = u.id
ORDER BY r.id, ha.created_at;

-- =============================================================================
-- PARTE 8: FUNCIÓN PARA VALIDAR TRANSICIONES DE ESTADO
-- =============================================================================

CREATE OR REPLACE FUNCTION validar_transicion_estado(
    estado_actual VARCHAR(50),
    estado_nuevo VARCHAR(50),
    rol_usuario VARCHAR(50)
) RETURNS BOOLEAN AS $$
DECLARE
    transicion_valida BOOLEAN := FALSE;
BEGIN
    -- Definir transiciones válidas según rol
    CASE 
        -- Médico puede: borrador → pendiente_jefe, devuelta_centro → pendiente_jefe
        WHEN rol_usuario = 'medico' THEN
            transicion_valida := (
                (estado_actual = 'borrador' AND estado_nuevo = 'pendiente_jefe') OR
                (estado_actual = 'devuelta_centro' AND estado_nuevo = 'pendiente_jefe') OR
                (estado_actual = 'borrador' AND estado_nuevo = 'cancelada')
            );
            
        -- Jefe de Área puede: pendiente_jefe → pendiente_director, pendiente_jefe → rechazada_jefe
        WHEN rol_usuario = 'jefe_area' THEN
            transicion_valida := (
                (estado_actual = 'pendiente_jefe' AND estado_nuevo = 'pendiente_director') OR
                (estado_actual = 'pendiente_jefe' AND estado_nuevo = 'rechazada_jefe') OR
                (estado_actual = 'pendiente_jefe' AND estado_nuevo = 'devuelta_centro')
            );
            
        -- Director puede: pendiente_director → enviada, pendiente_director → rechazada_director
        WHEN rol_usuario = 'director_centro' THEN
            transicion_valida := (
                (estado_actual = 'pendiente_director' AND estado_nuevo = 'enviada') OR
                (estado_actual = 'pendiente_director' AND estado_nuevo = 'rechazada_director') OR
                (estado_actual = 'pendiente_director' AND estado_nuevo = 'devuelta_centro')
            );
            
        -- Recepcionista Farmacia puede: enviada → en_revision, enviada → devuelta_centro
        WHEN rol_usuario = 'recepcionista_farmacia' THEN
            transicion_valida := (
                (estado_actual = 'enviada' AND estado_nuevo = 'en_revision') OR
                (estado_actual = 'enviada' AND estado_nuevo = 'devuelta_centro')
            );
            
        -- Responsable Farmacia puede: en_revision → autorizada, en_revision → rechazada_farmacia
        -- También: autorizada → surtida, surtida → entregada
        WHEN rol_usuario IN ('responsable_farmacia', 'admin_farmacia', 'farmacia') THEN
            transicion_valida := (
                (estado_actual = 'enviada' AND estado_nuevo = 'en_revision') OR
                (estado_actual = 'en_revision' AND estado_nuevo = 'autorizada') OR
                (estado_actual = 'en_revision' AND estado_nuevo = 'rechazada_farmacia') OR
                (estado_actual = 'autorizada' AND estado_nuevo = 'en_surtido') OR
                (estado_actual = 'autorizada' AND estado_nuevo = 'surtida') OR
                (estado_actual = 'en_surtido' AND estado_nuevo = 'surtida') OR
                (estado_actual = 'en_surtido' AND estado_nuevo = 'parcial') OR
                (estado_actual = 'surtida' AND estado_nuevo = 'entregada') OR
                (estado_actual = 'parcial' AND estado_nuevo = 'surtida') OR
                -- Flujo directo si no hay recepcionista separado
                (estado_actual = 'enviada' AND estado_nuevo = 'autorizada')
            );
            
        -- Admin sistema puede hacer cualquier transición
        WHEN rol_usuario IN ('admin_sistema', 'superusuario') THEN
            transicion_valida := TRUE;
            
        ELSE
            transicion_valida := FALSE;
    END CASE;
    
    RETURN transicion_valida;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION validar_transicion_estado IS 'Valida si una transición de estado es permitida según el rol del usuario';

-- =============================================================================
-- PARTE 9: TRIGGER PARA REGISTRAR HISTORIAL AUTOMÁTICAMENTE
-- =============================================================================

CREATE OR REPLACE FUNCTION registrar_cambio_estado_requisicion()
RETURNS TRIGGER AS $$
BEGIN
    -- Solo registrar si el estado cambió
    IF OLD.estado IS DISTINCT FROM NEW.estado THEN
        INSERT INTO historial_autorizaciones (
            requisicion_id,
            usuario_id,
            accion,
            estado_anterior,
            estado_nuevo,
            notas,
            created_at
        ) VALUES (
            NEW.id,
            COALESCE(
                NEW.autorizador_id,
                NEW.jefe_area_id,
                NEW.director_id,
                NEW.recepcionista_id,
                NEW.solicitante_id
            ),
            CASE 
                WHEN NEW.estado = 'pendiente_jefe' THEN 'enviar_jefe'
                WHEN NEW.estado = 'pendiente_director' THEN 'autorizar_jefe'
                WHEN NEW.estado = 'enviada' THEN 'autorizar_director'
                WHEN NEW.estado = 'en_revision' THEN 'recibir_farmacia'
                WHEN NEW.estado = 'autorizada' THEN 'autorizar_farmacia'
                WHEN NEW.estado = 'surtida' THEN 'surtir'
                WHEN NEW.estado = 'entregada' THEN 'entregar'
                WHEN NEW.estado LIKE 'rechazada%' THEN 'rechazar'
                WHEN NEW.estado = 'devuelta_centro' THEN 'devolver'
                WHEN NEW.estado = 'cancelada' THEN 'cancelar'
                ELSE 'cambio_estado'
            END,
            OLD.estado,
            NEW.estado,
            NEW.notas,
            NOW()
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Crear trigger si no existe
DROP TRIGGER IF EXISTS trg_registrar_cambio_estado ON requisiciones;
CREATE TRIGGER trg_registrar_cambio_estado
    AFTER UPDATE ON requisiciones
    FOR EACH ROW
    EXECUTE FUNCTION registrar_cambio_estado_requisicion();

-- =============================================================================
-- PARTE 10: DATOS INICIALES / MIGRACIÓN DE ROLES EXISTENTES
-- =============================================================================

-- Actualizar usuarios existentes con rol 'centro' a 'medico' si no tienen otro rol específico
-- NOTA: Ejecutar con cuidado, revisar primero con SELECT
-- UPDATE usuarios 
-- SET rol = 'medico' 
-- WHERE rol = 'centro' 
--   AND NOT EXISTS (
--     SELECT 1 FROM usuarios u2 
--     WHERE u2.centro_id = usuarios.centro_id 
--       AND u2.rol IN ('jefe_area', 'director_centro')
--   );

-- Ejemplo: Crear roles jerárquicos para un centro existente
-- Descomentar y ajustar según necesidad:
/*
INSERT INTO usuarios (username, email, password, first_name, last_name, rol, centro_id, is_active, date_joined, adscripcion)
VALUES 
    ('jefe_area_centro1', 'jefe@centro1.gob.mx', 'pbkdf2_sha256$...', 'Juan', 'Pérez', 'jefe_area', 1, true, NOW(), 'Centro 1'),
    ('director_centro1', 'director@centro1.gob.mx', 'pbkdf2_sha256$...', 'María', 'López', 'director_centro', 1, true, NOW(), 'Centro 1');
*/

-- =============================================================================
-- VERIFICACIÓN FINAL
-- =============================================================================

-- Verificar que las tablas tienen las nuevas columnas
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name IN ('requisiciones', 'usuarios', 'historial_autorizaciones')
  AND column_name IN (
    'jefe_area_id', 'director_id', 'recepcionista_id',
    'fecha_autorizacion_jefe', 'fecha_autorizacion_director',
    'motivo_rechazo', 'veces_devuelta',
    'area_departamento', 'perm_autorizar_jefe', 'perm_autorizar_director'
  )
ORDER BY table_name, column_name;

-- Mensaje de confirmación
DO $$
BEGIN
    RAISE NOTICE '=============================================================';
    RAISE NOTICE 'MIGRACIÓN COMPLETADA: Flujo Jerárquico de Requisiciones';
    RAISE NOTICE '=============================================================';
    RAISE NOTICE 'Nuevos roles agregados: medico, jefe_area, director_centro, recepcionista_farmacia, responsable_farmacia';
    RAISE NOTICE 'Nuevos estados agregados: pendiente_jefe, pendiente_director, en_revision, rechazada_jefe, rechazada_director, rechazada_farmacia, devuelta_centro';
    RAISE NOTICE 'Nueva tabla: historial_autorizaciones (trazabilidad completa)';
    RAISE NOTICE 'Vistas creadas: v_requisiciones_pendientes, v_estadisticas_autorizadores, v_trazabilidad_requisicion';
    RAISE NOTICE '=============================================================';
END $$;
