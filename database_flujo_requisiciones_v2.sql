-- ============================================================================
-- SISTEMA DE REQUISICIONES JERÁRQUICAS - FARMACIA PENITENCIARIA
-- Versión 2.0 - Flujo completo con trazabilidad anti-fraude
-- Fecha: 2024-12-08
-- ============================================================================

-- ============================================================================
-- PARTE 1: EXTENSIÓN DE ROLES DE USUARIO
-- ============================================================================

-- Agregar nuevos roles al campo 'rol' de la tabla usuarios
-- Los roles existentes se mantienen, se agregan los específicos del centro

COMMENT ON COLUMN usuarios.rol IS 'Roles del sistema:
FARMACIA CENTRAL:
  - admin: Administrador del sistema (acceso total)
  - farmacia: Personal de farmacia central (recibe, autoriza, surte)
  - vista: Solo consulta

CENTROS PENITENCIARIOS:
  - medico: Médico del centro (crea solicitudes)
  - administrador_centro: Administrador del centro (primera autorización)
  - director_centro: Director del centro (segunda autorización)
  - centro: Usuario genérico del centro (solo consulta)
';

-- ============================================================================
-- PARTE 2: NUEVOS ESTADOS DE REQUISICIÓN
-- ============================================================================

-- Actualizar el constraint de estados para incluir los nuevos
-- Primero eliminamos el constraint existente si lo hay

DO $$
BEGIN
    -- Intentar eliminar constraint existente
    ALTER TABLE requisiciones DROP CONSTRAINT IF EXISTS requisiciones_estado_check;
EXCEPTION
    WHEN undefined_object THEN NULL;
END $$;

-- Agregar nuevo constraint con todos los estados
ALTER TABLE requisiciones ADD CONSTRAINT requisiciones_estado_check 
CHECK (estado IN (
    -- Estados del flujo del centro
    'borrador',              -- Médico creando la solicitud
    'pendiente_admin',       -- Esperando autorización del Administrador del Centro
    'pendiente_director',    -- Esperando autorización del Director del Centro
    
    -- Estados del flujo de farmacia
    'enviada',               -- Enviada a Farmacia Central
    'en_revision',           -- Farmacia está revisando
    'autorizada',            -- Farmacia autorizó y asignó fecha de recolección
    'en_surtido',            -- En proceso de preparación
    'surtida',               -- Lista para recolección (esperando al centro)
    'entregada',             -- Entregada y confirmada
    
    -- Estados finales negativos
    'rechazada',             -- Rechazada en cualquier punto del flujo
    'vencida',               -- No se recolectó en la fecha límite
    'cancelada',             -- Cancelada por el solicitante
    'devuelta'               -- Devuelta al centro para corrección
));

-- ============================================================================
-- PARTE 3: NUEVAS COLUMNAS PARA TRAZABILIDAD TEMPORAL
-- ============================================================================

-- Columnas de fechas para auditoría completa del flujo
ALTER TABLE requisiciones 
ADD COLUMN IF NOT EXISTS fecha_envio_admin TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS fecha_autorizacion_admin TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS fecha_envio_director TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS fecha_autorizacion_director TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS fecha_envio_farmacia TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS fecha_recepcion_farmacia TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS fecha_autorizacion_farmacia TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS fecha_recoleccion_limite TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS fecha_vencimiento TIMESTAMP WITH TIME ZONE;

-- Columnas para identificar quién realizó cada acción (trazabilidad anti-fraude)
ALTER TABLE requisiciones
ADD COLUMN IF NOT EXISTS administrador_centro_id INTEGER REFERENCES usuarios(id),
ADD COLUMN IF NOT EXISTS director_centro_id INTEGER REFERENCES usuarios(id),
ADD COLUMN IF NOT EXISTS receptor_farmacia_id INTEGER REFERENCES usuarios(id),
ADD COLUMN IF NOT EXISTS autorizador_farmacia_id INTEGER REFERENCES usuarios(id),
ADD COLUMN IF NOT EXISTS surtidor_id INTEGER REFERENCES usuarios(id);

-- Columnas para motivos de rechazo/devolución (auditoría)
ALTER TABLE requisiciones
ADD COLUMN IF NOT EXISTS motivo_rechazo TEXT,
ADD COLUMN IF NOT EXISTS motivo_devolucion TEXT,
ADD COLUMN IF NOT EXISTS motivo_vencimiento TEXT;

-- Columna para observaciones de farmacia (ajustes de cantidades, etc.)
ALTER TABLE requisiciones
ADD COLUMN IF NOT EXISTS observaciones_farmacia TEXT;

-- Índices para consultas frecuentes por estado y fechas
CREATE INDEX IF NOT EXISTS idx_requisiciones_estado ON requisiciones(estado);
CREATE INDEX IF NOT EXISTS idx_requisiciones_centro_estado ON requisiciones(centro_origen_id, estado);
CREATE INDEX IF NOT EXISTS idx_requisiciones_fecha_recoleccion ON requisiciones(fecha_recoleccion_limite) WHERE estado = 'surtida';
-- Nota: No se puede crear índice parcial con NOW() porque no es IMMUTABLE
-- Las consultas de requisiciones vencidas usarán: WHERE estado = 'surtida' AND fecha_recoleccion_limite < NOW()
CREATE INDEX IF NOT EXISTS idx_requisiciones_surtidas_limite ON requisiciones(estado, fecha_recoleccion_limite) WHERE estado = 'surtida';

-- ============================================================================
-- PARTE 4: TABLA DE HISTORIAL DE ESTADOS (AUDITORÍA COMPLETA)
-- ============================================================================

CREATE TABLE IF NOT EXISTS requisicion_historial_estados (
    id SERIAL PRIMARY KEY,
    requisicion_id INTEGER NOT NULL REFERENCES requisiciones(id) ON DELETE CASCADE,
    
    -- Estado anterior y nuevo
    estado_anterior VARCHAR(50),
    estado_nuevo VARCHAR(50) NOT NULL,
    
    -- Quién y cuándo
    usuario_id INTEGER REFERENCES usuarios(id),
    fecha_cambio TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    
    -- Contexto del cambio
    accion VARCHAR(100) NOT NULL, -- 'crear', 'enviar_admin', 'autorizar_admin', 'rechazar_admin', etc.
    motivo TEXT,
    observaciones TEXT,
    
    -- Datos adicionales para auditoría
    ip_address VARCHAR(45),
    user_agent TEXT,
    datos_adicionales JSONB,
    
    -- Firma digital (hash de los datos para verificar integridad)
    hash_verificacion VARCHAR(64)
);

-- Índices para historial
CREATE INDEX IF NOT EXISTS idx_historial_requisicion ON requisicion_historial_estados(requisicion_id);
CREATE INDEX IF NOT EXISTS idx_historial_usuario ON requisicion_historial_estados(usuario_id);
CREATE INDEX IF NOT EXISTS idx_historial_fecha ON requisicion_historial_estados(fecha_cambio);
CREATE INDEX IF NOT EXISTS idx_historial_estado_nuevo ON requisicion_historial_estados(estado_nuevo);

COMMENT ON TABLE requisicion_historial_estados IS 
'Historial inmutable de todos los cambios de estado de las requisiciones.
Cada cambio queda registrado con fecha, usuario responsable y contexto.
El hash_verificacion permite detectar manipulación de registros.';

-- ============================================================================
-- PARTE 5: TABLA DE AJUSTES DE CANTIDADES (CUANDO FARMACIA MODIFICA)
-- ============================================================================

CREATE TABLE IF NOT EXISTS requisicion_ajustes_cantidad (
    id SERIAL PRIMARY KEY,
    detalle_requisicion_id INTEGER NOT NULL REFERENCES detalles_requisicion(id) ON DELETE CASCADE,
    
    -- Cantidades
    cantidad_original INTEGER NOT NULL,
    cantidad_ajustada INTEGER NOT NULL,
    
    -- Quién y cuándo
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    fecha_ajuste TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    
    -- Justificación (obligatoria para auditoría)
    motivo_ajuste TEXT NOT NULL,
    tipo_ajuste VARCHAR(50) NOT NULL CHECK (tipo_ajuste IN (
        'sin_stock',           -- No hay suficiente inventario
        'producto_agotado',    -- Producto completamente agotado
        'sustitucion',         -- Se sustituye por otro producto
        'correccion_cantidad', -- Ajuste por cantidad incorrecta
        'lote_proximo_caducar' -- Ajuste por lote próximo a caducar
    )),
    
    -- Si hay sustitución, qué producto se ofrece
    producto_sustituto_id INTEGER REFERENCES productos(id),
    
    -- Datos de auditoría
    ip_address VARCHAR(45),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ajustes_detalle ON requisicion_ajustes_cantidad(detalle_requisicion_id);
CREATE INDEX IF NOT EXISTS idx_ajustes_usuario ON requisicion_ajustes_cantidad(usuario_id);

COMMENT ON TABLE requisicion_ajustes_cantidad IS 
'Registro de todos los ajustes de cantidad realizados por Farmacia.
Cada modificación queda trazada con el motivo y usuario responsable.';

-- ============================================================================
-- PARTE 6: PERMISOS GRANULARES PARA EL FLUJO
-- ============================================================================

-- Agregar nuevos permisos a la tabla de usuarios
ALTER TABLE usuarios
ADD COLUMN IF NOT EXISTS perm_crear_requisicion BOOLEAN DEFAULT NULL,
ADD COLUMN IF NOT EXISTS perm_autorizar_admin BOOLEAN DEFAULT NULL,
ADD COLUMN IF NOT EXISTS perm_autorizar_director BOOLEAN DEFAULT NULL,
ADD COLUMN IF NOT EXISTS perm_recibir_farmacia BOOLEAN DEFAULT NULL,
ADD COLUMN IF NOT EXISTS perm_autorizar_farmacia BOOLEAN DEFAULT NULL,
ADD COLUMN IF NOT EXISTS perm_surtir BOOLEAN DEFAULT NULL,
ADD COLUMN IF NOT EXISTS perm_confirmar_entrega BOOLEAN DEFAULT NULL;

COMMENT ON COLUMN usuarios.perm_crear_requisicion IS 'Permiso para crear requisiciones (médicos)';
COMMENT ON COLUMN usuarios.perm_autorizar_admin IS 'Permiso para autorizar como Administrador del Centro';
COMMENT ON COLUMN usuarios.perm_autorizar_director IS 'Permiso para autorizar como Director del Centro';
COMMENT ON COLUMN usuarios.perm_recibir_farmacia IS 'Permiso para recibir requisiciones en Farmacia Central';
COMMENT ON COLUMN usuarios.perm_autorizar_farmacia IS 'Permiso para autorizar requisiciones en Farmacia Central';
COMMENT ON COLUMN usuarios.perm_surtir IS 'Permiso para surtir requisiciones';
COMMENT ON COLUMN usuarios.perm_confirmar_entrega IS 'Permiso para confirmar entrega/recepción';

-- ============================================================================
-- PARTE 7: FUNCIÓN PARA VERIFICAR REQUISICIONES VENCIDAS
-- ============================================================================

CREATE OR REPLACE FUNCTION verificar_requisiciones_vencidas()
RETURNS INTEGER AS $$
DECLARE
    cantidad_vencidas INTEGER;
BEGIN
    -- Actualizar requisiciones que pasaron su fecha límite de recolección
    UPDATE requisiciones
    SET 
        estado = 'vencida',
        fecha_vencimiento = NOW(),
        motivo_vencimiento = 'No se recolectó antes de la fecha límite establecida',
        updated_at = NOW()
    WHERE 
        estado = 'surtida' 
        AND fecha_recoleccion_limite IS NOT NULL
        AND fecha_recoleccion_limite < NOW();
    
    GET DIAGNOSTICS cantidad_vencidas = ROW_COUNT;
    
    -- Registrar en historial cada requisición vencida
    INSERT INTO requisicion_historial_estados (
        requisicion_id,
        estado_anterior,
        estado_nuevo,
        usuario_id,
        fecha_cambio,
        accion,
        motivo,
        datos_adicionales
    )
    SELECT 
        id,
        'surtida',
        'vencida',
        NULL, -- Sistema automático
        NOW(),
        'vencer_automatico',
        'Requisición vencida por no recolección en fecha límite',
        jsonb_build_object(
            'fecha_recoleccion_limite', fecha_recoleccion_limite,
            'dias_vencida', EXTRACT(DAY FROM NOW() - fecha_recoleccion_limite)
        )
    FROM requisiciones
    WHERE 
        estado = 'vencida' 
        AND fecha_vencimiento = (
            SELECT MAX(fecha_vencimiento) FROM requisiciones WHERE estado = 'vencida'
        );
    
    RETURN cantidad_vencidas;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION verificar_requisiciones_vencidas IS 
'Función que debe ejecutarse periódicamente (cron) para marcar como vencidas
las requisiciones que no fueron recolectadas en su fecha límite.';

-- ============================================================================
-- PARTE 8: FUNCIÓN TRIGGER PARA REGISTRAR HISTORIAL AUTOMÁTICAMENTE
-- ============================================================================

CREATE OR REPLACE FUNCTION registrar_cambio_estado_requisicion()
RETURNS TRIGGER AS $$
BEGIN
    -- Solo registrar si el estado cambió
    IF OLD.estado IS DISTINCT FROM NEW.estado THEN
        INSERT INTO requisicion_historial_estados (
            requisicion_id,
            estado_anterior,
            estado_nuevo,
            usuario_id,
            fecha_cambio,
            accion,
            motivo,
            datos_adicionales
        ) VALUES (
            NEW.id,
            OLD.estado,
            NEW.estado,
            COALESCE(
                NEW.autorizador_farmacia_id,
                NEW.surtidor_id,
                NEW.receptor_farmacia_id,
                NEW.director_centro_id,
                NEW.administrador_centro_id,
                NEW.solicitante_id
            ),
            NOW(),
            CASE NEW.estado
                WHEN 'pendiente_admin' THEN 'enviar_a_administrador'
                WHEN 'pendiente_director' THEN 'autorizar_administrador'
                WHEN 'enviada' THEN 'autorizar_director'
                WHEN 'en_revision' THEN 'recibir_farmacia'
                WHEN 'autorizada' THEN 'autorizar_farmacia'
                WHEN 'en_surtido' THEN 'iniciar_surtido'
                WHEN 'surtida' THEN 'completar_surtido'
                WHEN 'entregada' THEN 'confirmar_entrega'
                WHEN 'rechazada' THEN 'rechazar'
                WHEN 'devuelta' THEN 'devolver_centro'
                WHEN 'vencida' THEN 'vencer'
                WHEN 'cancelada' THEN 'cancelar'
                ELSE 'cambio_estado'
            END,
            COALESCE(NEW.motivo_rechazo, NEW.motivo_devolucion, NEW.motivo_vencimiento),
            jsonb_build_object(
                'estado_anterior', OLD.estado,
                'estado_nuevo', NEW.estado,
                'updated_at', NEW.updated_at
            )
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Crear trigger
DROP TRIGGER IF EXISTS trigger_historial_estado_requisicion ON requisiciones;
CREATE TRIGGER trigger_historial_estado_requisicion
    AFTER UPDATE ON requisiciones
    FOR EACH ROW
    EXECUTE FUNCTION registrar_cambio_estado_requisicion();

-- ============================================================================
-- PARTE 9: VISTA PARA CONSULTA DE REQUISICIONES CON TRAZABILIDAD COMPLETA
-- ============================================================================

CREATE OR REPLACE VIEW vista_requisiciones_completa AS
SELECT 
    r.id,
    r.numero,
    r.estado,
    r.tipo,
    r.prioridad,
    r.es_urgente,
    r.motivo_urgencia,
    r.notas,
    r.observaciones_farmacia,
    
    -- Centro origen
    r.centro_origen_id,
    co.nombre AS centro_origen_nombre,
    
    -- Centro destino (Farmacia Central)
    r.centro_destino_id,
    cd.nombre AS centro_destino_nombre,
    
    -- Solicitante (Médico)
    r.solicitante_id,
    sol.username AS solicitante_username,
    CONCAT(sol.first_name, ' ', sol.last_name) AS solicitante_nombre,
    sol.rol AS solicitante_rol,
    
    -- Administrador del Centro (primera autorización)
    r.administrador_centro_id,
    adm.username AS administrador_username,
    CONCAT(adm.first_name, ' ', adm.last_name) AS administrador_nombre,
    r.fecha_autorizacion_admin,
    
    -- Director del Centro (segunda autorización)
    r.director_centro_id,
    dir.username AS director_username,
    CONCAT(dir.first_name, ' ', dir.last_name) AS director_nombre,
    r.fecha_autorizacion_director,
    
    -- Farmacia - Receptor
    r.receptor_farmacia_id,
    rec.username AS receptor_username,
    CONCAT(rec.first_name, ' ', rec.last_name) AS receptor_nombre,
    r.fecha_recepcion_farmacia,
    
    -- Farmacia - Autorizador
    r.autorizador_farmacia_id AS autorizador_id,
    aut.username AS autorizador_username,
    CONCAT(aut.first_name, ' ', aut.last_name) AS autorizador_nombre,
    r.fecha_autorizacion_farmacia AS fecha_autorizacion,
    
    -- Farmacia - Surtidor
    r.surtidor_id,
    sur.username AS surtidor_username,
    CONCAT(sur.first_name, ' ', sur.last_name) AS surtidor_nombre,
    r.fecha_surtido,
    
    -- Fechas del flujo completo
    r.fecha_solicitud,
    r.fecha_envio_admin,
    r.fecha_envio_director,
    r.fecha_envio_farmacia,
    r.fecha_recoleccion_limite,
    r.fecha_entrega,
    r.fecha_vencimiento,
    
    -- Rechazos/Devoluciones
    r.motivo_rechazo,
    r.motivo_devolucion,
    r.motivo_vencimiento,
    
    -- Firmas
    r.firma_solicitante,
    r.nombre_solicitante,
    r.cargo_solicitante,
    r.firma_jefe_area,
    r.nombre_jefe_area,
    r.cargo_jefe_area,
    r.firma_director,
    r.nombre_director,
    r.cargo_director,
    
    -- Fotos de firma
    r.foto_firma_surtido,
    r.foto_firma_recepcion,
    
    -- Metadatos
    r.created_at,
    r.updated_at,
    
    -- Tiempo transcurrido en cada etapa (para reportes)
    EXTRACT(EPOCH FROM (r.fecha_autorizacion_admin - r.fecha_envio_admin))/3600 AS horas_en_admin,
    EXTRACT(EPOCH FROM (r.fecha_autorizacion_director - r.fecha_envio_director))/3600 AS horas_en_director,
    EXTRACT(EPOCH FROM (r.fecha_autorizacion_farmacia - r.fecha_recepcion_farmacia))/3600 AS horas_en_farmacia,
    EXTRACT(EPOCH FROM (r.fecha_entrega - r.fecha_surtido))/3600 AS horas_en_recoleccion,
    EXTRACT(EPOCH FROM (COALESCE(r.fecha_entrega, NOW()) - r.fecha_solicitud))/86400 AS dias_totales

FROM requisiciones r
LEFT JOIN centros co ON r.centro_origen_id = co.id
LEFT JOIN centros cd ON r.centro_destino_id = cd.id
LEFT JOIN usuarios sol ON r.solicitante_id = sol.id
LEFT JOIN usuarios adm ON r.administrador_centro_id = adm.id
LEFT JOIN usuarios dir ON r.director_centro_id = dir.id
LEFT JOIN usuarios rec ON r.receptor_farmacia_id = rec.id
LEFT JOIN usuarios aut ON r.autorizador_farmacia_id = aut.id
LEFT JOIN usuarios sur ON r.surtidor_id = sur.id;

COMMENT ON VIEW vista_requisiciones_completa IS 
'Vista que muestra todas las requisiciones con información completa de trazabilidad.
Incluye todos los actores involucrados en cada paso del flujo y tiempos de respuesta.';

-- ============================================================================
-- PARTE 10: POLÍTICAS DE SEGURIDAD RLS (Row Level Security)
-- ============================================================================

-- NOTA: Las políticas RLS de Supabase usan auth.uid() que retorna UUID.
-- Como esta aplicación usa Django con IDs INTEGER, las políticas RLS
-- se manejarán desde el backend de Django, no desde Supabase directamente.
-- 
-- Si en el futuro se migra a autenticación de Supabase, descomentar y adaptar:

/*
-- Habilitar RLS en la tabla de requisiciones
ALTER TABLE requisiciones ENABLE ROW LEVEL SECURITY;

-- Para usar RLS con Django, se necesitaría:
-- 1. Crear una función que obtenga el usuario actual del contexto
-- 2. O usar variables de sesión (SET LOCAL app.current_user_id = X)

-- Ejemplo de política usando variable de sesión:
CREATE POLICY requisiciones_centro_policy ON requisiciones
    FOR ALL
    USING (
        -- Obtener user_id de variable de sesión
        centro_origen_id = (
            SELECT centro_id FROM usuarios 
            WHERE id = current_setting('app.current_user_id', true)::INTEGER
        )
        OR
        -- O es admin/farmacia
        EXISTS (
            SELECT 1 FROM usuarios 
            WHERE id = current_setting('app.current_user_id', true)::INTEGER
            AND rol IN ('admin', 'farmacia')
        )
    );
*/

-- Por ahora, la seguridad se maneja en el backend Django con:
-- - Permisos de Django (IsAuthenticated, IsFarmaciaRole, etc.)
-- - Filtros en los QuerySets según el centro del usuario
-- - Decoradores y mixins personalizados

-- ============================================================================
-- PARTE 11: DATOS INICIALES PARA ROLES
-- ============================================================================

-- Actualizar permisos por defecto según el rol
UPDATE usuarios SET
    perm_crear_requisicion = true,
    perm_autorizar_admin = false,
    perm_autorizar_director = false,
    perm_recibir_farmacia = false,
    perm_autorizar_farmacia = false,
    perm_surtir = false,
    perm_confirmar_entrega = true
WHERE rol = 'medico';

UPDATE usuarios SET
    perm_crear_requisicion = false,
    perm_autorizar_admin = true,
    perm_autorizar_director = false,
    perm_recibir_farmacia = false,
    perm_autorizar_farmacia = false,
    perm_surtir = false,
    perm_confirmar_entrega = true
WHERE rol = 'administrador_centro';

UPDATE usuarios SET
    perm_crear_requisicion = false,
    perm_autorizar_admin = false,
    perm_autorizar_director = true,
    perm_recibir_farmacia = false,
    perm_autorizar_farmacia = false,
    perm_surtir = false,
    perm_confirmar_entrega = true
WHERE rol = 'director_centro';

UPDATE usuarios SET
    perm_crear_requisicion = false,
    perm_autorizar_admin = false,
    perm_autorizar_director = false,
    perm_recibir_farmacia = true,
    perm_autorizar_farmacia = true,
    perm_surtir = true,
    perm_confirmar_entrega = false
WHERE rol = 'farmacia';

UPDATE usuarios SET
    perm_crear_requisicion = true,
    perm_autorizar_admin = true,
    perm_autorizar_director = true,
    perm_recibir_farmacia = true,
    perm_autorizar_farmacia = true,
    perm_surtir = true,
    perm_confirmar_entrega = true
WHERE rol = 'admin' OR is_superuser = true;

-- ============================================================================
-- PARTE 12: COMENTARIOS DE DOCUMENTACIÓN
-- ============================================================================

COMMENT ON COLUMN requisiciones.estado IS 'Estados del flujo:
CENTRO:
  - borrador: Médico creando solicitud
  - pendiente_admin: Esperando autorización del Administrador
  - pendiente_director: Esperando autorización del Director
  
FARMACIA:
  - enviada: Recibida en Farmacia Central
  - en_revision: En proceso de revisión
  - autorizada: Autorizada con fecha de recolección
  - en_surtido: Preparando medicamentos
  - surtida: Lista para recolección
  - entregada: Entregada y confirmada
  
FINALES:
  - rechazada: Rechazada en cualquier punto
  - vencida: No recolectada en fecha límite
  - cancelada: Cancelada por solicitante
  - devuelta: Devuelta al centro para corrección';

COMMENT ON COLUMN requisiciones.fecha_recoleccion_limite IS 
'Fecha límite establecida por Farmacia Central para recolectar la requisición.
Si la requisición está en estado "surtida" y esta fecha pasa, 
el sistema la marca automáticamente como "vencida".';

COMMENT ON COLUMN requisiciones.administrador_centro_id IS 
'ID del Administrador del Centro que autorizó la requisición (primera autorización).
Registrado para trazabilidad y auditoría.';

COMMENT ON COLUMN requisiciones.director_centro_id IS 
'ID del Director del Centro que autorizó la requisición (segunda autorización).
Registrado para trazabilidad y auditoría.';

-- ============================================================================
-- PARTE 13: FUNCIÓN PARA VALIDAR TRANSICIONES DE ESTADO
-- ============================================================================

CREATE OR REPLACE FUNCTION validar_transicion_estado_requisicion()
RETURNS TRIGGER AS $$
DECLARE
    transicion_valida BOOLEAN := FALSE;
BEGIN
    -- Definir transiciones válidas
    transicion_valida := CASE
        -- Desde borrador
        WHEN OLD.estado = 'borrador' AND NEW.estado IN ('pendiente_admin', 'cancelada') THEN TRUE
        
        -- Desde pendiente_admin
        WHEN OLD.estado = 'pendiente_admin' AND NEW.estado IN ('pendiente_director', 'rechazada', 'devuelta') THEN TRUE
        
        -- Desde pendiente_director
        WHEN OLD.estado = 'pendiente_director' AND NEW.estado IN ('enviada', 'rechazada', 'devuelta') THEN TRUE
        
        -- Desde enviada
        WHEN OLD.estado = 'enviada' AND NEW.estado IN ('en_revision', 'autorizada', 'rechazada') THEN TRUE
        
        -- Desde en_revision
        WHEN OLD.estado = 'en_revision' AND NEW.estado IN ('autorizada', 'rechazada', 'devuelta') THEN TRUE
        
        -- Desde autorizada
        WHEN OLD.estado = 'autorizada' AND NEW.estado IN ('en_surtido', 'surtida', 'cancelada') THEN TRUE
        
        -- Desde en_surtido
        WHEN OLD.estado = 'en_surtido' AND NEW.estado IN ('surtida', 'cancelada') THEN TRUE
        
        -- Desde surtida
        WHEN OLD.estado = 'surtida' AND NEW.estado IN ('entregada', 'vencida', 'cancelada') THEN TRUE
        
        -- Desde devuelta (puede reiniciar el flujo)
        WHEN OLD.estado = 'devuelta' AND NEW.estado IN ('pendiente_admin', 'cancelada') THEN TRUE
        
        -- Estados finales no pueden cambiar
        WHEN OLD.estado IN ('entregada', 'rechazada', 'vencida', 'cancelada') THEN FALSE
        
        ELSE FALSE
    END;
    
    IF NOT transicion_valida THEN
        RAISE EXCEPTION 'Transición de estado no válida: % -> %', OLD.estado, NEW.estado;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Crear trigger de validación
DROP TRIGGER IF EXISTS trigger_validar_transicion_requisicion ON requisiciones;
CREATE TRIGGER trigger_validar_transicion_requisicion
    BEFORE UPDATE ON requisiciones
    FOR EACH ROW
    WHEN (OLD.estado IS DISTINCT FROM NEW.estado)
    EXECUTE FUNCTION validar_transicion_estado_requisicion();

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================

-- Mostrar resumen de cambios
DO $$
BEGIN
    RAISE NOTICE '============================================';
    RAISE NOTICE 'SCRIPT DE MIGRACIÓN COMPLETADO';
    RAISE NOTICE '============================================';
    RAISE NOTICE 'Cambios realizados:';
    RAISE NOTICE '1. Nuevos estados de requisición agregados';
    RAISE NOTICE '2. Columnas de fechas para trazabilidad temporal';
    RAISE NOTICE '3. Columnas para identificar actores en cada paso';
    RAISE NOTICE '4. Tabla requisicion_historial_estados creada';
    RAISE NOTICE '5. Tabla requisicion_ajustes_cantidad creada';
    RAISE NOTICE '6. Nuevos permisos granulares agregados';
    RAISE NOTICE '7. Función verificar_requisiciones_vencidas creada';
    RAISE NOTICE '8. Triggers de auditoría configurados';
    RAISE NOTICE '9. Vista vista_requisiciones_completa creada';
    RAISE NOTICE '10. Políticas RLS configuradas';
    RAISE NOTICE '11. Función de validación de transiciones creada';
    RAISE NOTICE '============================================';
END $$;
