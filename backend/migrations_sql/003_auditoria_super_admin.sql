-- ============================================================================
-- MIGRACIÓN: Panel de Auditoría SUPER ADMIN
-- Fecha: 2026-03-06
-- Base de datos: Supabase PostgreSQL
-- ============================================================================

-- ============================================================================
-- PARTE 1: EXTENSIÓN DE TABLA auditoria_logs
-- ============================================================================

-- Agregar columnas faltantes para auditoría completa
ALTER TABLE auditoria_logs 
ADD COLUMN IF NOT EXISTS resultado VARCHAR(20) DEFAULT 'success',
ADD COLUMN IF NOT EXISTS status_code INTEGER DEFAULT 200,
ADD COLUMN IF NOT EXISTS endpoint VARCHAR(255),
ADD COLUMN IF NOT EXISTS request_id VARCHAR(100),
ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(255),
ADD COLUMN IF NOT EXISTS rol_usuario VARCHAR(50),
ADD COLUMN IF NOT EXISTS centro_id INTEGER REFERENCES centros(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS metodo_http VARCHAR(10);

-- Agregar constraint CHECK para resultado (si no existe)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_resultado'
    ) THEN
        ALTER TABLE auditoria_logs 
        ADD CONSTRAINT chk_resultado 
        CHECK (resultado IN ('success', 'fail', 'error', 'warning'));
    END IF;
END $$;

-- Comentarios de documentación
COMMENT ON COLUMN auditoria_logs.resultado IS 'Resultado de la operación: success, fail, error, warning';
COMMENT ON COLUMN auditoria_logs.status_code IS 'Código HTTP de respuesta (200, 201, 400, 403, 500, etc)';
COMMENT ON COLUMN auditoria_logs.endpoint IS 'Endpoint de la API que se accedió';
COMMENT ON COLUMN auditoria_logs.request_id IS 'ID único de la petición para correlación';
COMMENT ON COLUMN auditoria_logs.idempotency_key IS 'Clave de idempotencia si existe';
COMMENT ON COLUMN auditoria_logs.rol_usuario IS 'Rol del usuario al momento de la acción';
COMMENT ON COLUMN auditoria_logs.centro_id IS 'Centro del usuario al momento de la acción';
COMMENT ON COLUMN auditoria_logs.metodo_http IS 'Método HTTP: GET, POST, PUT, PATCH, DELETE';

-- ============================================================================
-- PARTE 2: ÍNDICES PARA PERFORMANCE
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_audit_fecha_usuario 
ON auditoria_logs(timestamp DESC, usuario_id);

CREATE INDEX IF NOT EXISTS idx_audit_modelo_accion 
ON auditoria_logs(modelo, accion);

CREATE INDEX IF NOT EXISTS idx_audit_resultado 
ON auditoria_logs(resultado) WHERE resultado != 'success';

CREATE INDEX IF NOT EXISTS idx_audit_centro 
ON auditoria_logs(centro_id) WHERE centro_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_audit_request_id 
ON auditoria_logs(request_id) WHERE request_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_audit_objeto 
ON auditoria_logs(modelo, objeto_id);

-- Nota: Índice parcial para registros recientes no soportado con NOW()
-- PostgreSQL requiere funciones IMMUTABLE en predicados de índices
-- Alternativa: usar índice completo sobre timestamp
CREATE INDEX IF NOT EXISTS idx_audit_timestamp 
ON auditoria_logs(timestamp DESC);

-- ============================================================================
-- PARTE 3: VISTAS
-- ============================================================================

CREATE OR REPLACE VIEW v_auditoria_stats_diarias AS
SELECT 
    DATE(timestamp) as fecha,
    COUNT(*) as total_eventos,
    COUNT(DISTINCT usuario_id) as usuarios_activos,
    COUNT(CASE WHEN resultado = 'success' THEN 1 END) as exitosos,
    COUNT(CASE WHEN resultado IN ('fail', 'error') THEN 1 END) as fallidos,
    COUNT(DISTINCT modelo) as modulos_afectados
FROM auditoria_logs
WHERE timestamp >= NOW() - INTERVAL '90 days'
GROUP BY DATE(timestamp)
ORDER BY fecha DESC;

CREATE OR REPLACE VIEW v_auditoria_criticos AS
SELECT 
    al.id,
    al.timestamp,
    u.username,
    u.rol,
    c.nombre as centro_nombre,
    al.accion,
    al.modelo,
    al.objeto_id,
    al.resultado,
    al.status_code,
    al.endpoint,
    al.ip_address,
    al.detalles
FROM auditoria_logs al
LEFT JOIN usuarios u ON al.usuario_id = u.id
LEFT JOIN centros c ON al.centro_id = c.id
WHERE al.resultado IN ('fail', 'error') 
   OR al.status_code >= 400
ORDER BY al.timestamp DESC
LIMIT 1000;

CREATE OR REPLACE VIEW v_auditoria_super_admin AS
SELECT 
    al.id,
    al.timestamp,
    al.usuario_id,
    u.username as usuario_username,
    COALESCE(u.first_name || ' ' || u.last_name, u.username) as usuario_nombre_completo,
    COALESCE(al.rol_usuario, u.rol) as rol,
    al.centro_id,
    c.nombre as centro_nombre,
    al.accion,
    al.modelo,
    al.objeto_id,
    al.resultado,
    al.status_code,
    al.metodo_http,
    al.endpoint,
    al.request_id,
    al.idempotency_key,
    al.ip_address,
    al.user_agent,
    al.datos_anteriores,
    al.datos_nuevos,
    al.detalles
FROM auditoria_logs al
LEFT JOIN usuarios u ON al.usuario_id = u.id
LEFT JOIN centros c ON al.centro_id = c.id;

-- ============================================================================
-- PARTE 4: FUNCIONES
-- ============================================================================

CREATE OR REPLACE FUNCTION fn_registrar_auditoria(
    p_usuario_id INTEGER,
    p_accion VARCHAR(50),
    p_modelo VARCHAR(100),
    p_objeto_id VARCHAR(50),
    p_datos_anteriores JSONB DEFAULT NULL,
    p_datos_nuevos JSONB DEFAULT NULL,
    p_ip_address VARCHAR(45) DEFAULT NULL,
    p_user_agent TEXT DEFAULT NULL,
    p_detalles JSONB DEFAULT NULL,
    p_resultado VARCHAR(20) DEFAULT 'success',
    p_status_code INTEGER DEFAULT 200,
    p_endpoint VARCHAR(255) DEFAULT NULL,
    p_request_id VARCHAR(100) DEFAULT NULL,
    p_idempotency_key VARCHAR(255) DEFAULT NULL,
    p_metodo_http VARCHAR(10) DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    v_rol_usuario VARCHAR(50);
    v_centro_id INTEGER;
    v_audit_id INTEGER;
BEGIN
    SELECT rol, centro_id INTO v_rol_usuario, v_centro_id
    FROM usuarios WHERE id = p_usuario_id;
    
    INSERT INTO auditoria_logs (
        usuario_id, accion, modelo, objeto_id,
        datos_anteriores, datos_nuevos,
        ip_address, user_agent, detalles,
        resultado, status_code, endpoint,
        request_id, idempotency_key,
        rol_usuario, centro_id, metodo_http,
        timestamp
    ) VALUES (
        p_usuario_id, p_accion, p_modelo, p_objeto_id,
        p_datos_anteriores, p_datos_nuevos,
        p_ip_address, p_user_agent, p_detalles,
        p_resultado, p_status_code, p_endpoint,
        p_request_id, p_idempotency_key,
        v_rol_usuario, v_centro_id, p_metodo_http,
        NOW()
    ) RETURNING id INTO v_audit_id;
    
    RETURN v_audit_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_limpiar_auditoria_antigua(
    p_dias_retencion INTEGER DEFAULT 365
) RETURNS INTEGER AS $$
DECLARE
    v_eliminados INTEGER;
BEGIN
    DELETE FROM auditoria_logs
    WHERE timestamp < NOW() - (p_dias_retencion || ' days')::INTERVAL;
    
    GET DIAGNOSTICS v_eliminados = ROW_COUNT;
    RETURN v_eliminados;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- VERIFICACIÓN
-- ============================================================================
SELECT 'Migración completada' as status,
       (SELECT COUNT(*) FROM information_schema.columns 
        WHERE table_name = 'auditoria_logs' AND column_name = 'resultado') as columna_resultado_existe;
