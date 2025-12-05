-- ==========================================================================
-- FARMACIA PENITENCIARIA - ESQUEMA COMPLETO DE BASE DE DATOS
-- Ejecutar en Supabase SQL Editor para crear toda la estructura
-- ==========================================================================
-- FILOSOFÍA: La base de datos es la fuente de verdad. Django se adapta a ella.
-- ==========================================================================

-- ========== LIMPIAR Y EMPEZAR FRESCO ==========
-- ADVERTENCIA: Esto elimina TODOS los datos existentes
-- Comentar estas líneas si quieres preservar datos

-- DROP SCHEMA public CASCADE;
-- CREATE SCHEMA public;
-- GRANT ALL ON SCHEMA public TO postgres;
-- GRANT ALL ON SCHEMA public TO public;

-- ==========================================================================
-- TABLAS DE DJANGO (Requeridas por el framework)
-- ==========================================================================

-- Migraciones de Django
CREATE TABLE IF NOT EXISTS django_migrations (
    id SERIAL PRIMARY KEY,
    app VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    applied TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Content Types (para permisos genéricos)
CREATE TABLE IF NOT EXISTS django_content_type (
    id SERIAL PRIMARY KEY,
    app_label VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    UNIQUE(app_label, model)
);

-- Grupos de Django
CREATE TABLE IF NOT EXISTS auth_group (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL UNIQUE
);

-- Permisos de Django
CREATE TABLE IF NOT EXISTS auth_permission (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    content_type_id INTEGER NOT NULL REFERENCES django_content_type(id) ON DELETE CASCADE,
    codename VARCHAR(100) NOT NULL,
    UNIQUE(content_type_id, codename)
);

-- Permisos por grupo
CREATE TABLE IF NOT EXISTS auth_group_permissions (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES auth_group(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES auth_permission(id) ON DELETE CASCADE,
    UNIQUE(group_id, permission_id)
);

-- Sesiones de Django
CREATE TABLE IF NOT EXISTS django_session (
    session_key VARCHAR(40) PRIMARY KEY,
    session_data TEXT NOT NULL,
    expire_date TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS django_session_expire_date_idx ON django_session(expire_date);

-- Admin Log
CREATE TABLE IF NOT EXISTS django_admin_log (
    id SERIAL PRIMARY KEY,
    action_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    object_id TEXT,
    object_repr VARCHAR(200) NOT NULL,
    action_flag SMALLINT NOT NULL CHECK (action_flag >= 0),
    change_message TEXT NOT NULL,
    content_type_id INTEGER REFERENCES django_content_type(id) ON DELETE SET NULL,
    user_id BIGINT NOT NULL
);

-- ==========================================================================
-- TABLAS JWT (Simple JWT Token Blacklist)
-- ==========================================================================

CREATE TABLE IF NOT EXISTS token_blacklist_outstandingtoken (
    id BIGSERIAL PRIMARY KEY,
    token TEXT NOT NULL,
    created_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL,
    user_id BIGINT,
    jti VARCHAR(255) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS token_blacklist_blacklistedtoken (
    id BIGSERIAL PRIMARY KEY,
    blacklisted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    token_id BIGINT NOT NULL UNIQUE REFERENCES token_blacklist_outstandingtoken(id) ON DELETE CASCADE
);

-- ==========================================================================
-- TABLA: CENTROS (Centros penitenciarios)
-- ==========================================================================

CREATE TABLE IF NOT EXISTS centros (
    id SERIAL PRIMARY KEY,
    clave VARCHAR(20) NOT NULL UNIQUE,
    nombre VARCHAR(200) NOT NULL,
    tipo VARCHAR(20) NOT NULL DEFAULT 'cereso' CHECK (tipo IN ('cereso', 'almacen', 'oficina')),
    direccion TEXT,
    telefono VARCHAR(20),
    responsable VARCHAR(200),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_centros_activo ON centros(activo);
CREATE INDEX IF NOT EXISTS idx_centros_clave ON centros(clave);
CREATE INDEX IF NOT EXISTS idx_centros_tipo ON centros(tipo);

-- ==========================================================================
-- TABLA: USUARIOS (Extiende AbstractUser de Django)
-- ==========================================================================

CREATE TABLE IF NOT EXISTS usuarios (
    id BIGSERIAL PRIMARY KEY,
    password VARCHAR(128) NOT NULL,
    last_login TIMESTAMPTZ,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    username VARCHAR(150) NOT NULL UNIQUE,
    first_name VARCHAR(150) NOT NULL DEFAULT '',
    last_name VARCHAR(150) NOT NULL DEFAULT '',
    email VARCHAR(254) NOT NULL DEFAULT '',
    is_staff BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    date_joined TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Campos personalizados
    rol VARCHAR(20) NOT NULL DEFAULT 'usuario_normal' 
        CHECK (rol IN ('admin_sistema', 'farmacia', 'usuario_centro', 'usuario_normal')),
    centro_id INTEGER REFERENCES centros(id) ON DELETE SET NULL,
    adscripcion VARCHAR(200) NOT NULL DEFAULT '',
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Permisos por módulo (NULL = usar default del rol)
    perm_dashboard BOOLEAN,
    perm_productos BOOLEAN,
    perm_lotes BOOLEAN,
    perm_requisiciones BOOLEAN,
    perm_centros BOOLEAN,
    perm_usuarios BOOLEAN,
    perm_reportes BOOLEAN,
    perm_trazabilidad BOOLEAN,
    perm_auditoria BOOLEAN,
    perm_notificaciones BOOLEAN,
    perm_movimientos BOOLEAN
);

CREATE INDEX IF NOT EXISTS idx_usuarios_username ON usuarios(username);
CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email);
CREATE INDEX IF NOT EXISTS idx_usuarios_rol_activo ON usuarios(rol, activo);
CREATE INDEX IF NOT EXISTS idx_usuarios_centro ON usuarios(centro_id);

-- Relaciones M2M de usuarios con grupos y permisos
CREATE TABLE IF NOT EXISTS usuarios_groups (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    group_id INTEGER NOT NULL REFERENCES auth_group(id) ON DELETE CASCADE,
    UNIQUE(user_id, group_id)
);
CREATE INDEX IF NOT EXISTS idx_usuarios_groups_user ON usuarios_groups(user_id);
CREATE INDEX IF NOT EXISTS idx_usuarios_groups_group ON usuarios_groups(group_id);

CREATE TABLE IF NOT EXISTS usuarios_user_permissions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES auth_permission(id) ON DELETE CASCADE,
    UNIQUE(user_id, permission_id)
);
CREATE INDEX IF NOT EXISTS idx_usuarios_perms_user ON usuarios_user_permissions(user_id);
CREATE INDEX IF NOT EXISTS idx_usuarios_perms_perm ON usuarios_user_permissions(permission_id);

-- FK del admin log al usuario
ALTER TABLE django_admin_log 
    ADD CONSTRAINT fk_admin_log_user 
    FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE CASCADE;

-- FK del token al usuario
ALTER TABLE token_blacklist_outstandingtoken 
    ADD CONSTRAINT fk_token_user 
    FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE SET NULL;

-- ==========================================================================
-- TABLA: PRODUCTOS (Catálogo de medicamentos)
-- ==========================================================================

CREATE TABLE IF NOT EXISTS productos (
    id BIGSERIAL PRIMARY KEY,
    clave VARCHAR(50) NOT NULL UNIQUE,
    descripcion VARCHAR(500) NOT NULL,
    unidad_medida VARCHAR(20) NOT NULL DEFAULT 'pieza' 
        CHECK (unidad_medida IN ('pieza', 'caja', 'frasco', 'sobre', 'ampolleta', 'tubo', 'tableta', 'capsula', 'ml', 'litro', 'gramo', 'kg')),
    precio_unitario DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    stock_minimo INTEGER NOT NULL DEFAULT 0 CHECK (stock_minimo >= 0),
    stock_maximo INTEGER NOT NULL DEFAULT 0 CHECK (stock_maximo >= 0),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    codigo_barras VARCHAR(50),
    imagen VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_productos_clave ON productos(clave);
CREATE INDEX IF NOT EXISTS idx_productos_activo ON productos(activo);
CREATE INDEX IF NOT EXISTS idx_productos_descripcion ON productos(descripcion);
CREATE INDEX IF NOT EXISTS idx_productos_codigo_barras ON productos(codigo_barras) WHERE codigo_barras IS NOT NULL;

-- ==========================================================================
-- TABLA: LOTES (Inventario por lote)
-- ==========================================================================

CREATE TABLE IF NOT EXISTS lotes (
    id BIGSERIAL PRIMARY KEY,
    producto_id BIGINT NOT NULL REFERENCES productos(id) ON DELETE PROTECT,
    centro_id INTEGER REFERENCES centros(id) ON DELETE SET NULL,
    numero_lote VARCHAR(100) NOT NULL,
    fecha_caducidad DATE NOT NULL,
    fecha_entrada DATE NOT NULL DEFAULT CURRENT_DATE,
    cantidad_inicial INTEGER NOT NULL CHECK (cantidad_inicial >= 0),
    cantidad_actual INTEGER NOT NULL CHECK (cantidad_actual >= 0),
    precio_compra DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    estado VARCHAR(20) NOT NULL DEFAULT 'disponible' 
        CHECK (estado IN ('disponible', 'agotado', 'caducado', 'cuarentena')),
    ubicacion VARCHAR(100),
    observaciones TEXT,
    documento_soporte VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(producto_id, numero_lote, centro_id)
);

CREATE INDEX IF NOT EXISTS idx_lotes_producto ON lotes(producto_id);
CREATE INDEX IF NOT EXISTS idx_lotes_centro ON lotes(centro_id);
CREATE INDEX IF NOT EXISTS idx_lotes_numero ON lotes(numero_lote);
CREATE INDEX IF NOT EXISTS idx_lotes_caducidad ON lotes(fecha_caducidad);
CREATE INDEX IF NOT EXISTS idx_lotes_estado ON lotes(estado);
CREATE INDEX IF NOT EXISTS idx_lotes_disponible ON lotes(estado, cantidad_actual) WHERE estado = 'disponible' AND cantidad_actual > 0;

-- ==========================================================================
-- TABLA: REQUISICIONES (Solicitudes de medicamentos)
-- ==========================================================================

CREATE TABLE IF NOT EXISTS requisiciones (
    id BIGSERIAL PRIMARY KEY,
    folio VARCHAR(50) NOT NULL UNIQUE,
    centro_id INTEGER NOT NULL REFERENCES centros(id) ON DELETE PROTECT,
    usuario_solicita_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE PROTECT,
    usuario_autoriza_id BIGINT REFERENCES usuarios(id) ON DELETE SET NULL,
    usuario_surte_id BIGINT REFERENCES usuarios(id) ON DELETE SET NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'borrador' 
        CHECK (estado IN ('borrador', 'enviada', 'autorizada', 'rechazada', 'en_surtido', 'surtida', 'parcial', 'cancelada', 'entregada')),
    fecha_solicitud TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha_autorizacion TIMESTAMPTZ,
    fecha_surtido TIMESTAMPTZ,
    fecha_entrega TIMESTAMPTZ,
    comentario TEXT,
    motivo_rechazo TEXT,
    prioridad VARCHAR(10) NOT NULL DEFAULT 'normal' CHECK (prioridad IN ('baja', 'normal', 'alta', 'urgente')),
    lugar_entrega VARCHAR(200),
    foto_firma_recibe VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_requisiciones_folio ON requisiciones(folio);
CREATE INDEX IF NOT EXISTS idx_requisiciones_centro ON requisiciones(centro_id);
CREATE INDEX IF NOT EXISTS idx_requisiciones_estado ON requisiciones(estado);
CREATE INDEX IF NOT EXISTS idx_requisiciones_fecha ON requisiciones(fecha_solicitud DESC);
CREATE INDEX IF NOT EXISTS idx_requisiciones_usuario ON requisiciones(usuario_solicita_id);

-- ==========================================================================
-- TABLA: DETALLE REQUISICION (Items de cada requisición)
-- ==========================================================================

CREATE TABLE IF NOT EXISTS detalles_requisicion (
    id BIGSERIAL PRIMARY KEY,
    requisicion_id BIGINT NOT NULL REFERENCES requisiciones(id) ON DELETE CASCADE,
    producto_id BIGINT NOT NULL REFERENCES productos(id) ON DELETE PROTECT,
    lote_id BIGINT REFERENCES lotes(id) ON DELETE SET NULL,
    cantidad_solicitada INTEGER NOT NULL CHECK (cantidad_solicitada > 0),
    cantidad_autorizada INTEGER CHECK (cantidad_autorizada >= 0),
    cantidad_surtida INTEGER CHECK (cantidad_surtida >= 0),
    observaciones TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(requisicion_id, producto_id)
);

CREATE INDEX IF NOT EXISTS idx_det_req_requisicion ON detalles_requisicion(requisicion_id);
CREATE INDEX IF NOT EXISTS idx_det_req_producto ON detalles_requisicion(producto_id);
CREATE INDEX IF NOT EXISTS idx_det_req_lote ON detalles_requisicion(lote_id);

-- ==========================================================================
-- TABLA: MOVIMIENTOS (Trazabilidad de inventario)
-- ==========================================================================

CREATE TABLE IF NOT EXISTS movimientos (
    id BIGSERIAL PRIMARY KEY,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('entrada', 'salida', 'ajuste', 'requisicion', 'transferencia')),
    lote_id BIGINT NOT NULL REFERENCES lotes(id) ON DELETE PROTECT,
    centro_id INTEGER REFERENCES centros(id) ON DELETE PROTECT,
    requisicion_id BIGINT REFERENCES requisiciones(id) ON DELETE SET NULL,
    usuario_id BIGINT REFERENCES usuarios(id) ON DELETE SET NULL,
    cantidad INTEGER NOT NULL,
    documento_referencia VARCHAR(100),
    observaciones TEXT,
    fecha TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_movimientos_tipo ON movimientos(tipo);
CREATE INDEX IF NOT EXISTS idx_movimientos_lote ON movimientos(lote_id);
CREATE INDEX IF NOT EXISTS idx_movimientos_centro ON movimientos(centro_id);
CREATE INDEX IF NOT EXISTS idx_movimientos_fecha ON movimientos(fecha DESC);
CREATE INDEX IF NOT EXISTS idx_movimientos_requisicion ON movimientos(requisicion_id) WHERE requisicion_id IS NOT NULL;

-- ==========================================================================
-- TABLA: NOTIFICACIONES
-- ==========================================================================

CREATE TABLE IF NOT EXISTS notificaciones (
    id BIGSERIAL PRIMARY KEY,
    usuario_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    tipo VARCHAR(50) NOT NULL,
    titulo VARCHAR(200) NOT NULL,
    mensaje TEXT NOT NULL,
    leida BOOLEAN NOT NULL DEFAULT FALSE,
    datos_extra JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notificaciones_usuario ON notificaciones(usuario_id);
CREATE INDEX IF NOT EXISTS idx_notificaciones_leida ON notificaciones(usuario_id, leida) WHERE leida = FALSE;
CREATE INDEX IF NOT EXISTS idx_notificaciones_fecha ON notificaciones(created_at DESC);

-- ==========================================================================
-- TABLA: CONFIGURACION DEL SISTEMA
-- ==========================================================================

CREATE TABLE IF NOT EXISTS configuracion_sistema (
    id SERIAL PRIMARY KEY,
    clave VARCHAR(100) NOT NULL UNIQUE,
    valor TEXT,
    descripcion VARCHAR(500),
    tipo VARCHAR(20) NOT NULL DEFAULT 'texto' CHECK (tipo IN ('texto', 'numero', 'booleano', 'json')),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ==========================================================================
-- TABLA: TEMA GLOBAL (Personalización visual)
-- ==========================================================================

CREATE TABLE IF NOT EXISTS tema_global (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL DEFAULT 'Gobierno del Estado de México',
    logo_url VARCHAR(500),
    color_primario VARCHAR(7) NOT NULL DEFAULT '#6d1a36',
    color_secundario VARCHAR(7) NOT NULL DEFAULT '#c9a227',
    color_fondo VARCHAR(7) NOT NULL DEFAULT '#faf7f2',
    color_texto VARCHAR(7) NOT NULL DEFAULT '#1a1a1a',
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ==========================================================================
-- TABLA: IMPORTACION LOG (Auditoría de importaciones)
-- ==========================================================================

CREATE TABLE IF NOT EXISTS importacion_log (
    id BIGSERIAL PRIMARY KEY,
    usuario_id BIGINT REFERENCES usuarios(id) ON DELETE SET NULL,
    archivo_nombre VARCHAR(255) NOT NULL,
    tipo_importacion VARCHAR(50) NOT NULL,
    registros_procesados INTEGER NOT NULL DEFAULT 0,
    registros_exitosos INTEGER NOT NULL DEFAULT 0,
    registros_fallidos INTEGER NOT NULL DEFAULT 0,
    errores JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ==========================================================================
-- TABLA: AUDIT LOG (Auditoría de acciones)
-- ==========================================================================

CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,
    usuario_id BIGINT REFERENCES usuarios(id) ON DELETE SET NULL,
    accion VARCHAR(50) NOT NULL,
    modelo VARCHAR(100) NOT NULL,
    objeto_id VARCHAR(100),
    datos_antes JSONB,
    datos_despues JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_usuario ON audit_log(usuario_id);
CREATE INDEX IF NOT EXISTS idx_audit_modelo ON audit_log(modelo);
CREATE INDEX IF NOT EXISTS idx_audit_fecha ON audit_log(created_at DESC);

-- ==========================================================================
-- TABLA: HOJA DE RECOLECCION
-- ==========================================================================

CREATE TABLE IF NOT EXISTS hojas_recoleccion (
    id BIGSERIAL PRIMARY KEY,
    requisicion_id BIGINT NOT NULL REFERENCES requisiciones(id) ON DELETE CASCADE,
    folio VARCHAR(50) NOT NULL UNIQUE,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente' 
        CHECK (estado IN ('pendiente', 'en_proceso', 'completada', 'cancelada')),
    fecha_generacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha_inicio TIMESTAMPTZ,
    fecha_fin TIMESTAMPTZ,
    usuario_recolector_id BIGINT REFERENCES usuarios(id) ON DELETE SET NULL,
    observaciones TEXT
);

CREATE INDEX IF NOT EXISTS idx_hojas_requisicion ON hojas_recoleccion(requisicion_id);
CREATE INDEX IF NOT EXISTS idx_hojas_estado ON hojas_recoleccion(estado);

-- ==========================================================================
-- TABLA: DETALLE HOJA RECOLECCION
-- ==========================================================================

CREATE TABLE IF NOT EXISTS detalles_hoja_recoleccion (
    id BIGSERIAL PRIMARY KEY,
    hoja_recoleccion_id BIGINT NOT NULL REFERENCES hojas_recoleccion(id) ON DELETE CASCADE,
    detalle_requisicion_id BIGINT NOT NULL REFERENCES detalles_requisicion(id) ON DELETE CASCADE,
    lote_id BIGINT REFERENCES lotes(id) ON DELETE SET NULL,
    cantidad_recolectada INTEGER NOT NULL DEFAULT 0 CHECK (cantidad_recolectada >= 0),
    ubicacion VARCHAR(100),
    recolectado BOOLEAN NOT NULL DEFAULT FALSE,
    orden INTEGER NOT NULL DEFAULT 0
);

-- ==========================================================================
-- TABLA: DETALLE SURTIDO (Qué lotes se usaron para surtir)
-- ==========================================================================

CREATE TABLE IF NOT EXISTS detalles_surtido (
    id BIGSERIAL PRIMARY KEY,
    detalle_requisicion_id BIGINT NOT NULL REFERENCES detalles_requisicion(id) ON DELETE CASCADE,
    lote_id BIGINT NOT NULL REFERENCES lotes(id) ON DELETE PROTECT,
    cantidad_surtida INTEGER NOT NULL CHECK (cantidad_surtida > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_det_surtido_detalle ON detalles_surtido(detalle_requisicion_id);
CREATE INDEX IF NOT EXISTS idx_det_surtido_lote ON detalles_surtido(lote_id);

-- ==========================================================================
-- TABLA: DETALLE RECEPCION (Qué recibió el centro)
-- ==========================================================================

CREATE TABLE IF NOT EXISTS detalles_recepcion (
    id BIGSERIAL PRIMARY KEY,
    detalle_requisicion_id BIGINT NOT NULL REFERENCES detalles_requisicion(id) ON DELETE CASCADE,
    lote_centro_id BIGINT NOT NULL REFERENCES lotes(id) ON DELETE PROTECT,
    cantidad_recibida INTEGER NOT NULL CHECK (cantidad_recibida > 0),
    observaciones TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ==========================================================================
-- TABLAS LEGACY (managed = False en Django - Solo referencia)
-- ==========================================================================

-- Contratos (si se usa integración externa)
CREATE TABLE IF NOT EXISTS contratos (
    id BIGSERIAL PRIMARY KEY,
    numero_contrato VARCHAR(100) NOT NULL UNIQUE,
    proveedor VARCHAR(200) NOT NULL,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    monto_total DECIMAL(15,2),
    estado VARCHAR(20) NOT NULL DEFAULT 'activo',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Relación Contrato-Producto
CREATE TABLE IF NOT EXISTS contrato_productos (
    id BIGSERIAL PRIMARY KEY,
    contrato_id BIGINT NOT NULL REFERENCES contratos(id) ON DELETE CASCADE,
    producto_id BIGINT NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
    cantidad_contratada INTEGER NOT NULL,
    precio_unitario DECIMAL(12,2) NOT NULL,
    UNIQUE(contrato_id, producto_id)
);

-- ==========================================================================
-- USUARIO ADMIN INICIAL
-- ==========================================================================

INSERT INTO usuarios (
    password, is_superuser, username, first_name, last_name, 
    email, is_staff, is_active, date_joined, rol, activo
)
SELECT 
    'pbkdf2_sha256$870000$temp$temp=',
    TRUE, 'admin', 'Administrador', 'Sistema',
    'admin@farmacia.gob.mx', TRUE, TRUE, NOW(), 'admin_sistema', TRUE
WHERE NOT EXISTS (SELECT 1 FROM usuarios WHERE username = 'admin');

-- ==========================================================================
-- TEMA INICIAL
-- ==========================================================================

INSERT INTO tema_global (nombre, color_primario, color_secundario, color_fondo, color_texto, activo)
SELECT 'Gobierno del Estado de México', '#6d1a36', '#c9a227', '#faf7f2', '#1a1a1a', TRUE
WHERE NOT EXISTS (SELECT 1 FROM tema_global WHERE activo = TRUE);

-- ==========================================================================
-- REGISTRAR MIGRACIONES DE DJANGO
-- ==========================================================================

DELETE FROM django_migrations;

INSERT INTO django_migrations (app, name, applied) VALUES
    -- Contenttypes
    ('contenttypes', '0001_initial', NOW()),
    ('contenttypes', '0002_remove_content_type_name', NOW()),
    -- Auth
    ('auth', '0001_initial', NOW()),
    ('auth', '0002_alter_permission_name_max_length', NOW()),
    ('auth', '0003_alter_user_email_max_length', NOW()),
    ('auth', '0004_alter_user_username_opts', NOW()),
    ('auth', '0005_alter_user_last_login_null', NOW()),
    ('auth', '0006_require_contenttypes_0002', NOW()),
    ('auth', '0007_alter_validators_add_error_messages', NOW()),
    ('auth', '0008_alter_user_username_max_length', NOW()),
    ('auth', '0009_alter_user_last_name_max_length', NOW()),
    ('auth', '0010_alter_group_name_max_length', NOW()),
    ('auth', '0011_update_proxy_permissions', NOW()),
    ('auth', '0012_alter_user_first_name_max_length', NOW()),
    -- Admin
    ('admin', '0001_initial', NOW()),
    ('admin', '0002_logentry_remove_auto_add', NOW()),
    ('admin', '0003_logentry_add_action_flag_choices', NOW()),
    -- Sessions
    ('sessions', '0001_initial', NOW()),
    -- Token Blacklist
    ('token_blacklist', '0001_initial', NOW()),
    ('token_blacklist', '0002_outstandingtoken_jti_hex', NOW()),
    ('token_blacklist', '0003_auto_20171017_2007', NOW()),
    ('token_blacklist', '0004_auto_20171017_2013', NOW()),
    ('token_blacklist', '0005_remove_outstandingtoken_jti', NOW()),
    ('token_blacklist', '0006_auto_20171017_2113', NOW()),
    ('token_blacklist', '0007_auto_20171017_2214', NOW()),
    ('token_blacklist', '0008_migrate_to_bigautofield', NOW()),
    ('token_blacklist', '0010_fix_migrate_to_bigautofield', NOW()),
    ('token_blacklist', '0011_linearizes_history', NOW()),
    ('token_blacklist', '0012_alter_outstandingtoken_user', NOW()),
    ('token_blacklist', '0013_alter_blacklistedtoken_options_and_more', NOW()),
    -- Core
    ('core', '0001_initial', NOW()),
    ('core', '0002_detallerequisicion_importacionlog_lote_movimiento_and_more', NOW()),
    ('core', '0003_update_importacionlog', NOW()),
    ('core', '0004_remove_userprofile_centro', NOW()),
    ('core', '0005_etapa2_updates', NOW()),
    ('core', '0006_agregar_codigo_barras', NOW()),
    ('core', '0007_lote_idx_lote_stock_lookup_lote_idx_lote_disponible_and_more', NOW()),
    ('core', '0008_lote_centro', NOW()),
    ('core', '0009_lote_centro_fill', NOW()),
    ('core', '0010_etapa3_nuevos_campos', NOW()),
    ('core', '0011_configuracionsistema_detallehojarecoleccion_and_more', NOW()),
    ('core', '0012_add_notificacion_indexes', NOW()),
    ('core', '0013_tema_global', NOW()),
    ('core', '0014_iss018_indices_rendimiento', NOW()),
    ('core', '0015_iss019_constraints_iss032_auditlog', NOW()),
    ('core', '0016_iss005_007_009_auditoria_permisos', NOW()),
    ('core', '0017_iss002_detalle_surtido_iss003_constraints', NOW()),
    ('core', '0018_audit5_contratos_reservas_recepcion', NOW()),
    ('core', '0019_fix_tema_colores_institucionales', NOW()),
    ('core', '0020_producto_imagen_requisicion_firmas', NOW()),
    ('core', '0021_optimize_db_structure', NOW()),
    -- Inventario
    ('inventario', '0001_initial', NOW()),
    ('inventario', '0002_remove_requisicion_centro_alter_lote_unique_together_and_more', NOW());

-- ==========================================================================
-- VERIFICACION FINAL
-- ==========================================================================

SELECT 'TABLAS CREADAS:' as info;
SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;

SELECT 'MIGRACIONES REGISTRADAS:' as info;
SELECT app, COUNT(*) as total FROM django_migrations GROUP BY app ORDER BY app;
