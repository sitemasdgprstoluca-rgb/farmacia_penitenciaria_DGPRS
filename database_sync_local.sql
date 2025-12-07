-- ============================================================================
-- SCRIPT DE SINCRONIZACIÓN: Base de Datos Local → Esquema Supabase
-- ============================================================================
-- Este script asegura que la BD local tenga la misma estructura que Supabase
-- Ejecutar en la BD local PostgreSQL
-- ============================================================================

-- Habilitar extensión pg_trgm si no existe (para búsqueda en productos)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================================
-- TABLA: centros
-- ============================================================================
CREATE TABLE IF NOT EXISTS centros (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL UNIQUE,
    direccion TEXT,
    telefono VARCHAR(20),
    email VARCHAR(254),
    activo BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_centros_activo ON centros(activo);
CREATE INDEX IF NOT EXISTS idx_centros_nombre ON centros(nombre);

-- ============================================================================
-- TABLA: usuarios
-- ============================================================================
CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    password VARCHAR(128) NOT NULL,
    last_login TIMESTAMP WITH TIME ZONE,
    is_superuser BOOLEAN NOT NULL DEFAULT false,
    username VARCHAR(150) NOT NULL UNIQUE,
    first_name VARCHAR(150) NOT NULL DEFAULT '',
    last_name VARCHAR(150) NOT NULL DEFAULT '',
    email VARCHAR(254) NOT NULL DEFAULT '',
    is_staff BOOLEAN NOT NULL DEFAULT false,
    is_active BOOLEAN NOT NULL DEFAULT true,
    date_joined TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    rol VARCHAR(20) NOT NULL DEFAULT 'usuario_normal',
    centro_id INTEGER REFERENCES centros(id) ON DELETE SET NULL,
    adscripcion VARCHAR(200) NOT NULL DEFAULT '',
    activo BOOLEAN NOT NULL DEFAULT true,
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
CREATE INDEX IF NOT EXISTS idx_usuarios_centro_activo ON usuarios(centro_id, activo);

-- ============================================================================
-- TABLA: user_profiles
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_profiles (
    id SERIAL PRIMARY KEY,
    rol VARCHAR(30) NOT NULL DEFAULT 'visualizador',
    telefono VARCHAR(20),
    centro_id INTEGER REFERENCES centros(id) ON DELETE SET NULL,
    usuario_id INTEGER NOT NULL UNIQUE REFERENCES usuarios(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_profiles_rol ON user_profiles(rol);
CREATE INDEX IF NOT EXISTS idx_user_profiles_centro ON user_profiles(centro_id);

-- ============================================================================
-- TABLA: productos
-- ============================================================================
CREATE TABLE IF NOT EXISTS productos (
    id SERIAL PRIMARY KEY,
    codigo_barras VARCHAR(50) UNIQUE,
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT,
    unidad_medida VARCHAR(50) NOT NULL DEFAULT 'pieza',
    categoria VARCHAR(50) NOT NULL DEFAULT 'medicamento',
    stock_minimo INTEGER NOT NULL DEFAULT 10,
    stock_actual INTEGER NOT NULL DEFAULT 0,
    sustancia_activa VARCHAR(255),
    presentacion VARCHAR(100),
    concentracion VARCHAR(50),
    via_administracion VARCHAR(50),
    requiere_receta BOOLEAN NOT NULL DEFAULT false,
    es_controlado BOOLEAN NOT NULL DEFAULT false,
    activo BOOLEAN NOT NULL DEFAULT true,
    imagen VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_productos_activo ON productos(activo);
CREATE INDEX IF NOT EXISTS idx_productos_categoria ON productos(categoria);
CREATE INDEX IF NOT EXISTS idx_productos_codigo_barras ON productos(codigo_barras);
CREATE INDEX IF NOT EXISTS idx_productos_nombre ON productos(nombre);
CREATE INDEX IF NOT EXISTS idx_productos_nombre_trgm ON productos USING gin(nombre gin_trgm_ops);

-- ============================================================================
-- TABLA: lotes
-- ============================================================================
CREATE TABLE IF NOT EXISTS lotes (
    id SERIAL PRIMARY KEY,
    numero_lote VARCHAR(100) NOT NULL,
    producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE RESTRICT,
    cantidad_inicial INTEGER NOT NULL,
    cantidad_actual INTEGER NOT NULL DEFAULT 0,
    fecha_fabricacion DATE,
    fecha_caducidad DATE NOT NULL,
    precio_unitario NUMERIC(12,2) NOT NULL DEFAULT 0,
    numero_contrato VARCHAR(100),
    marca VARCHAR(100),
    ubicacion VARCHAR(100),
    centro_id INTEGER REFERENCES centros(id) ON DELETE SET NULL,
    activo BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    UNIQUE(numero_lote, producto_id)
);

CREATE INDEX IF NOT EXISTS idx_lotes_activo ON lotes(activo);
CREATE INDEX IF NOT EXISTS idx_lotes_centro ON lotes(centro_id);
CREATE INDEX IF NOT EXISTS idx_lotes_fecha_caducidad ON lotes(fecha_caducidad);
CREATE INDEX IF NOT EXISTS idx_lotes_numero_lote ON lotes(numero_lote);
CREATE INDEX IF NOT EXISTS idx_lotes_producto ON lotes(producto_id);
CREATE INDEX IF NOT EXISTS idx_lotes_producto_activo ON lotes(producto_id, activo);
CREATE INDEX IF NOT EXISTS idx_lotes_caducidad_activo ON lotes(fecha_caducidad, activo) WHERE activo = true;

-- ============================================================================
-- TABLA: requisiciones
-- ============================================================================
CREATE TABLE IF NOT EXISTS requisiciones (
    id SERIAL PRIMARY KEY,
    numero VARCHAR(50) NOT NULL UNIQUE,
    centro_origen_id INTEGER REFERENCES centros(id) ON DELETE SET NULL,
    centro_destino_id INTEGER REFERENCES centros(id) ON DELETE SET NULL,
    solicitante_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    autorizador_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    estado VARCHAR(30) NOT NULL DEFAULT 'borrador',
    tipo VARCHAR(30) NOT NULL DEFAULT 'normal',
    prioridad VARCHAR(20) NOT NULL DEFAULT 'normal',
    notas TEXT,
    lugar_entrega VARCHAR(255),
    fecha_solicitud TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    fecha_autorizacion TIMESTAMP WITH TIME ZONE,
    fecha_surtido TIMESTAMP WITH TIME ZONE,
    fecha_entrega TIMESTAMP WITH TIME ZONE,
    foto_firma_surtido VARCHAR(255),
    foto_firma_recepcion VARCHAR(255),
    usuario_firma_surtido_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    usuario_firma_recepcion_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    fecha_firma_surtido TIMESTAMP WITH TIME ZONE,
    fecha_firma_recepcion TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_requisiciones_numero ON requisiciones(numero);
CREATE INDEX IF NOT EXISTS idx_requisiciones_estado ON requisiciones(estado);
CREATE INDEX IF NOT EXISTS idx_requisiciones_centro_origen ON requisiciones(centro_origen_id);
CREATE INDEX IF NOT EXISTS idx_requisiciones_centro_destino ON requisiciones(centro_destino_id);
CREATE INDEX IF NOT EXISTS idx_requisiciones_solicitante ON requisiciones(solicitante_id);
CREATE INDEX IF NOT EXISTS idx_requisiciones_fecha_solicitud ON requisiciones(fecha_solicitud);
CREATE INDEX IF NOT EXISTS idx_requisiciones_estado_fecha ON requisiciones(estado, fecha_solicitud DESC);

-- ============================================================================
-- TABLA: detalles_requisicion
-- ============================================================================
CREATE TABLE IF NOT EXISTS detalles_requisicion (
    id SERIAL PRIMARY KEY,
    requisicion_id INTEGER NOT NULL REFERENCES requisiciones(id) ON DELETE CASCADE,
    producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE RESTRICT,
    lote_id INTEGER REFERENCES lotes(id) ON DELETE SET NULL,
    cantidad_solicitada INTEGER NOT NULL,
    cantidad_autorizada INTEGER,
    cantidad_surtida INTEGER DEFAULT 0,
    cantidad_recibida INTEGER,
    notas TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_detalles_requisicion_requisicion ON detalles_requisicion(requisicion_id);
CREATE INDEX IF NOT EXISTS idx_detalles_requisicion_producto ON detalles_requisicion(producto_id);
CREATE INDEX IF NOT EXISTS idx_detalles_requisicion_lote ON detalles_requisicion(lote_id);
CREATE INDEX IF NOT EXISTS idx_detalles_req_requisicion_producto ON detalles_requisicion(requisicion_id, producto_id);

-- ============================================================================
-- TABLA: movimientos
-- ============================================================================
CREATE TABLE IF NOT EXISTS movimientos (
    id SERIAL PRIMARY KEY,
    tipo VARCHAR(30) NOT NULL,
    producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE RESTRICT,
    lote_id INTEGER REFERENCES lotes(id) ON DELETE SET NULL,
    cantidad INTEGER NOT NULL,
    centro_origen_id INTEGER REFERENCES centros(id) ON DELETE SET NULL,
    centro_destino_id INTEGER REFERENCES centros(id) ON DELETE SET NULL,
    requisicion_id INTEGER REFERENCES requisiciones(id) ON DELETE SET NULL,
    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    motivo TEXT,
    referencia VARCHAR(100),
    fecha TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_movimientos_tipo ON movimientos(tipo);
CREATE INDEX IF NOT EXISTS idx_movimientos_producto ON movimientos(producto_id);
CREATE INDEX IF NOT EXISTS idx_movimientos_lote ON movimientos(lote_id);
CREATE INDEX IF NOT EXISTS idx_movimientos_requisicion ON movimientos(requisicion_id);
CREATE INDEX IF NOT EXISTS idx_movimientos_usuario ON movimientos(usuario_id);
CREATE INDEX IF NOT EXISTS idx_movimientos_fecha ON movimientos(fecha);
CREATE INDEX IF NOT EXISTS idx_movimientos_producto_fecha ON movimientos(producto_id, fecha DESC);

-- ============================================================================
-- TABLA: notificaciones
-- ============================================================================
CREATE TABLE IF NOT EXISTS notificaciones (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    tipo VARCHAR(50) NOT NULL,
    titulo VARCHAR(200) NOT NULL,
    mensaje TEXT NOT NULL,
    leida BOOLEAN NOT NULL DEFAULT false,
    datos JSONB,
    url VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_notificaciones_usuario ON notificaciones(usuario_id);
CREATE INDEX IF NOT EXISTS idx_notificaciones_tipo ON notificaciones(tipo);
CREATE INDEX IF NOT EXISTS idx_notificaciones_leida ON notificaciones(leida);

-- ============================================================================
-- TABLA: auditoria_logs
-- ============================================================================
CREATE TABLE IF NOT EXISTS auditoria_logs (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    accion VARCHAR(50) NOT NULL,
    modelo VARCHAR(100) NOT NULL,
    objeto_id VARCHAR(50),
    datos_anteriores JSONB,
    datos_nuevos JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    detalles JSONB,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_auditoria_logs_usuario ON auditoria_logs(usuario_id);
CREATE INDEX IF NOT EXISTS idx_auditoria_logs_accion ON auditoria_logs(accion);
CREATE INDEX IF NOT EXISTS idx_auditoria_logs_modelo ON auditoria_logs(modelo);
CREATE INDEX IF NOT EXISTS idx_auditoria_logs_timestamp ON auditoria_logs(timestamp);

-- ============================================================================
-- TABLA: importacion_logs
-- ============================================================================
CREATE TABLE IF NOT EXISTS importacion_logs (
    id SERIAL PRIMARY KEY,
    archivo VARCHAR(255) NOT NULL,
    tipo_importacion VARCHAR(50) NOT NULL,
    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    registros_totales INTEGER NOT NULL DEFAULT 0,
    registros_exitosos INTEGER NOT NULL DEFAULT 0,
    registros_fallidos INTEGER NOT NULL DEFAULT 0,
    errores JSONB,
    estado VARCHAR(30) NOT NULL DEFAULT 'procesando',
    fecha_inicio TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    fecha_fin TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_importacion_logs_usuario ON importacion_logs(usuario_id);
CREATE INDEX IF NOT EXISTS idx_importacion_logs_estado ON importacion_logs(estado);

-- ============================================================================
-- TABLA: hojas_recoleccion
-- ============================================================================
CREATE TABLE IF NOT EXISTS hojas_recoleccion (
    id SERIAL PRIMARY KEY,
    numero VARCHAR(50) NOT NULL UNIQUE,
    centro_id INTEGER REFERENCES centros(id) ON DELETE SET NULL,
    responsable_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    estado VARCHAR(30) NOT NULL DEFAULT 'pendiente',
    fecha_programada DATE NOT NULL,
    fecha_recoleccion TIMESTAMP WITH TIME ZONE,
    notas TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_hojas_recoleccion_centro ON hojas_recoleccion(centro_id);
CREATE INDEX IF NOT EXISTS idx_hojas_recoleccion_estado ON hojas_recoleccion(estado);
CREATE INDEX IF NOT EXISTS idx_hojas_recoleccion_fecha_programada ON hojas_recoleccion(fecha_programada);

-- ============================================================================
-- TABLA: detalle_hojas_recoleccion
-- ============================================================================
CREATE TABLE IF NOT EXISTS detalle_hojas_recoleccion (
    id SERIAL PRIMARY KEY,
    hoja_id INTEGER NOT NULL REFERENCES hojas_recoleccion(id) ON DELETE CASCADE,
    lote_id INTEGER NOT NULL REFERENCES lotes(id) ON DELETE CASCADE,
    cantidad_recolectar INTEGER NOT NULL,
    cantidad_recolectada INTEGER DEFAULT 0,
    motivo VARCHAR(50) NOT NULL DEFAULT 'caducidad',
    observaciones TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_detalle_hojas_hoja ON detalle_hojas_recoleccion(hoja_id);
CREATE INDEX IF NOT EXISTS idx_detalle_hojas_lote ON detalle_hojas_recoleccion(lote_id);

-- ============================================================================
-- TABLA: tema_global
-- ============================================================================
CREATE TABLE IF NOT EXISTS tema_global (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    es_activo BOOLEAN NOT NULL DEFAULT false,
    logo_url VARCHAR(500),
    logo_width INTEGER DEFAULT 160,
    logo_height INTEGER DEFAULT 60,
    favicon_url VARCHAR(500),
    titulo_sistema VARCHAR(100) DEFAULT 'Sistema de Inventario Farmacéutico',
    subtitulo_sistema VARCHAR(200) DEFAULT 'Gobierno del Estado',
    color_primario VARCHAR(20) DEFAULT '#9F2241',
    color_primario_hover VARCHAR(20) DEFAULT '#6B1839',
    color_secundario VARCHAR(20) DEFAULT '#424242',
    color_secundario_hover VARCHAR(20) DEFAULT '#2E2E2E',
    color_exito VARCHAR(20) DEFAULT '#4a7c4b',
    color_exito_hover VARCHAR(20) DEFAULT '#3d663e',
    color_alerta VARCHAR(20) DEFAULT '#d4a017',
    color_alerta_hover VARCHAR(20) DEFAULT '#b38b14',
    color_error VARCHAR(20) DEFAULT '#c53030',
    color_error_hover VARCHAR(20) DEFAULT '#a52828',
    color_info VARCHAR(20) DEFAULT '#3182ce',
    color_info_hover VARCHAR(20) DEFAULT '#2c6cb0',
    color_fondo_principal VARCHAR(20) DEFAULT '#f7f8fa',
    color_fondo_sidebar VARCHAR(20) DEFAULT '#9F2241',
    color_fondo_header VARCHAR(20) DEFAULT '#9F2241',
    color_texto_principal VARCHAR(20) DEFAULT '#1f2937',
    color_texto_sidebar VARCHAR(20) DEFAULT '#ffffff',
    color_texto_header VARCHAR(20) DEFAULT '#ffffff',
    color_texto_links VARCHAR(20) DEFAULT '#9F2241',
    color_borde_inputs VARCHAR(20) DEFAULT '#d1d5db',
    color_borde_focus VARCHAR(20) DEFAULT '#9F2241',
    reporte_color_encabezado VARCHAR(20) DEFAULT '#9F2241',
    reporte_color_texto VARCHAR(20) DEFAULT '#1f2937',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- ============================================================================
-- TABLA: configuracion_sistema
-- ============================================================================
CREATE TABLE IF NOT EXISTS configuracion_sistema (
    id SERIAL PRIMARY KEY,
    clave VARCHAR(100) NOT NULL UNIQUE,
    valor TEXT NOT NULL,
    descripcion TEXT,
    tipo VARCHAR(20) NOT NULL DEFAULT 'string',
    es_publica BOOLEAN NOT NULL DEFAULT false,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- ============================================================================
-- TABLAS DE DJANGO (auth, sessions, etc.)
-- ============================================================================
CREATE TABLE IF NOT EXISTS auth_group (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS auth_permission (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    content_type_id INTEGER NOT NULL,
    codename VARCHAR(100) NOT NULL,
    UNIQUE(content_type_id, codename)
);

CREATE TABLE IF NOT EXISTS auth_group_permissions (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES auth_group(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES auth_permission(id) ON DELETE CASCADE,
    UNIQUE(group_id, permission_id)
);

CREATE INDEX IF NOT EXISTS idx_auth_group_permissions_group ON auth_group_permissions(group_id);
CREATE INDEX IF NOT EXISTS idx_auth_group_permissions_permission ON auth_group_permissions(permission_id);

CREATE TABLE IF NOT EXISTS django_content_type (
    id SERIAL PRIMARY KEY,
    app_label VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    UNIQUE(app_label, model)
);

CREATE TABLE IF NOT EXISTS django_admin_log (
    id SERIAL PRIMARY KEY,
    action_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    object_id TEXT,
    object_repr VARCHAR(200) NOT NULL,
    action_flag SMALLINT NOT NULL,
    change_message TEXT NOT NULL DEFAULT '',
    content_type_id INTEGER REFERENCES django_content_type(id) ON DELETE SET NULL,
    user_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_django_admin_log_content_type ON django_admin_log(content_type_id);
CREATE INDEX IF NOT EXISTS idx_django_admin_log_user ON django_admin_log(user_id);

CREATE TABLE IF NOT EXISTS django_session (
    session_key VARCHAR(40) PRIMARY KEY,
    session_data TEXT NOT NULL,
    expire_date TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_django_session_expire_date ON django_session(expire_date);

CREATE TABLE IF NOT EXISTS django_migrations (
    id SERIAL PRIMARY KEY,
    app VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    applied TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- ============================================================================
-- TABLAS DE JWT TOKENS
-- ============================================================================
CREATE TABLE IF NOT EXISTS token_blacklist_outstandingtoken (
    id SERIAL PRIMARY KEY,
    token TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    user_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    jti VARCHAR(255) NOT NULL UNIQUE
);

CREATE INDEX IF NOT EXISTS idx_token_blacklist_outstanding_user ON token_blacklist_outstandingtoken(user_id);
CREATE INDEX IF NOT EXISTS idx_token_blacklist_outstanding_jti ON token_blacklist_outstandingtoken(jti);

CREATE TABLE IF NOT EXISTS token_blacklist_blacklistedtoken (
    id SERIAL PRIMARY KEY,
    blacklisted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    token_id INTEGER NOT NULL UNIQUE REFERENCES token_blacklist_outstandingtoken(id) ON DELETE CASCADE
);

-- ============================================================================
-- TABLAS DE GRUPOS Y PERMISOS DE USUARIOS
-- ============================================================================
CREATE TABLE IF NOT EXISTS usuarios_groups (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    group_id INTEGER NOT NULL REFERENCES auth_group(id) ON DELETE CASCADE,
    UNIQUE(user_id, group_id)
);

CREATE INDEX IF NOT EXISTS idx_usuarios_groups_user_id ON usuarios_groups(user_id);
CREATE INDEX IF NOT EXISTS idx_usuarios_groups_group_id ON usuarios_groups(group_id);

CREATE TABLE IF NOT EXISTS usuarios_user_permissions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES auth_permission(id) ON DELETE CASCADE,
    UNIQUE(user_id, permission_id)
);

CREATE INDEX IF NOT EXISTS idx_usuarios_user_permissions_user_id ON usuarios_user_permissions(user_id);
CREATE INDEX IF NOT EXISTS idx_usuarios_user_permissions_permission_id ON usuarios_user_permissions(permission_id);

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================
-- Para ejecutar:
-- psql -h localhost -U postgres -d farmacia_db -f database_sync_local.sql
-- ============================================================================
