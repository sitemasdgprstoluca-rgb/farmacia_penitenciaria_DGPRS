-- =============================================================================
-- SCRIPT DE CREACIÓN DE BASE DE DATOS DE DESARROLLO/PRUEBAS
-- Sistema de Inventario Farmacéutico Penitenciario
-- Fecha: 2024-12-19
-- Descripción: Crea todas las tablas necesarias (idéntico a producción)
-- =============================================================================

-- Habilitar extensiones necesarias
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- FUNCIONES DE UTILIDAD
-- =============================================================================

-- Función para actualizar timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Función para actualizar updated_at en donaciones
CREATE OR REPLACE FUNCTION update_donaciones_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Función para actualizar updated_at en productos_donacion
CREATE OR REPLACE FUNCTION update_productos_donacion_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Función para registrar cambios de estado en requisiciones
CREATE OR REPLACE FUNCTION registrar_cambio_estado_requisicion()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.estado IS DISTINCT FROM NEW.estado THEN
        INSERT INTO requisicion_historial_estados (
            requisicion_id,
            estado_anterior,
            estado_nuevo,
            fecha_cambio,
            accion
        ) VALUES (
            NEW.id,
            OLD.estado,
            NEW.estado,
            NOW(),
            'cambio_estado'
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Función para validar transiciones de estado en requisiciones
CREATE OR REPLACE FUNCTION validar_transicion_estado_requisicion()
RETURNS TRIGGER AS $$
DECLARE
    transicion_valida BOOLEAN := FALSE;
BEGIN
    -- Definir transiciones válidas
    CASE OLD.estado
        WHEN 'borrador' THEN
            transicion_valida := NEW.estado IN ('pendiente_admin', 'cancelada');
        WHEN 'pendiente_admin' THEN
            transicion_valida := NEW.estado IN ('pendiente_director', 'rechazada', 'devuelta', 'cancelada');
        WHEN 'pendiente_director' THEN
            transicion_valida := NEW.estado IN ('enviada', 'rechazada', 'devuelta', 'cancelada');
        WHEN 'enviada' THEN
            transicion_valida := NEW.estado IN ('en_revision', 'rechazada', 'cancelada');
        WHEN 'en_revision' THEN
            transicion_valida := NEW.estado IN ('autorizada', 'rechazada', 'devuelta');
        WHEN 'autorizada' THEN
            transicion_valida := NEW.estado IN ('en_surtido', 'cancelada');
        WHEN 'en_surtido' THEN
            transicion_valida := NEW.estado IN ('surtida', 'parcial', 'cancelada');
        WHEN 'surtida' THEN
            transicion_valida := NEW.estado IN ('entregada', 'vencida');
        WHEN 'parcial' THEN
            transicion_valida := NEW.estado IN ('surtida', 'entregada', 'vencida');
        ELSE
            transicion_valida := FALSE;
    END CASE;

    IF NOT transicion_valida THEN
        RAISE EXCEPTION 'Transición de estado no válida: % -> %', OLD.estado, NEW.estado;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- TABLAS DE AUTENTICACIÓN Y PERMISOS (Django)
-- =============================================================================

-- Tabla de tipos de contenido de Django
CREATE TABLE IF NOT EXISTS public.django_content_type (
    id SERIAL PRIMARY KEY,
    app_label VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    CONSTRAINT django_content_type_app_label_model_key UNIQUE (app_label, model)
);

-- Tabla de permisos de Django
CREATE TABLE IF NOT EXISTS public.auth_permission (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    content_type_id INTEGER NOT NULL REFERENCES django_content_type(id) ON DELETE CASCADE,
    codename VARCHAR(100) NOT NULL,
    CONSTRAINT auth_permission_content_type_id_codename_key UNIQUE (content_type_id, codename)
);

CREATE INDEX IF NOT EXISTS idx_auth_permission_content_type ON public.auth_permission(content_type_id);

-- Tabla de grupos de Django
CREATE TABLE IF NOT EXISTS public.auth_group (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL UNIQUE
);

-- Tabla de permisos de grupos
CREATE TABLE IF NOT EXISTS public.auth_group_permissions (
    id BIGSERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES auth_group(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES auth_permission(id) ON DELETE CASCADE,
    CONSTRAINT auth_group_permissions_group_id_permission_id_key UNIQUE (group_id, permission_id)
);

CREATE INDEX IF NOT EXISTS idx_auth_group_permissions_group ON public.auth_group_permissions(group_id);
CREATE INDEX IF NOT EXISTS idx_auth_group_permissions_permission ON public.auth_group_permissions(permission_id);

-- =============================================================================
-- TABLA DE CENTROS (debe crearse antes de usuarios)
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.centros (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    codigo VARCHAR(20) NOT NULL UNIQUE,
    tipo VARCHAR(50) NOT NULL DEFAULT 'centro_penitenciario',
    direccion TEXT,
    telefono VARCHAR(20),
    email VARCHAR(254),
    responsable VARCHAR(200),
    capacidad INTEGER DEFAULT 0,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    es_almacen_central BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT valid_tipo_centro CHECK (
        tipo IN ('centro_penitenciario', 'almacen_central', 'hospital', 'clinica', 'oficina')
    )
);

CREATE INDEX IF NOT EXISTS idx_centros_codigo ON public.centros(codigo);
CREATE INDEX IF NOT EXISTS idx_centros_nombre ON public.centros(nombre);
CREATE INDEX IF NOT EXISTS idx_centros_activo ON public.centros(activo);
CREATE INDEX IF NOT EXISTS idx_centros_tipo ON public.centros(tipo);

DROP TRIGGER IF EXISTS update_centros_updated_at ON centros;
CREATE TRIGGER update_centros_updated_at
    BEFORE UPDATE ON centros
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- TABLA DE USUARIOS
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.usuarios (
    id SERIAL PRIMARY KEY,
    password VARCHAR(128) NOT NULL,
    last_login TIMESTAMP WITH TIME ZONE NULL,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    username VARCHAR(150) NOT NULL UNIQUE,
    first_name VARCHAR(150) NOT NULL DEFAULT '',
    last_name VARCHAR(150) NOT NULL DEFAULT '',
    email VARCHAR(254) NOT NULL DEFAULT '',
    is_staff BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    date_joined TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    rol VARCHAR(20) NOT NULL DEFAULT 'usuario_normal',
    centro_id INTEGER NULL REFERENCES centros(id) ON DELETE SET NULL,
    adscripcion VARCHAR(200) NOT NULL DEFAULT '',
    perm_dashboard BOOLEAN NULL,
    perm_productos BOOLEAN NULL,
    perm_lotes BOOLEAN NULL,
    perm_requisiciones BOOLEAN NULL,
    perm_centros BOOLEAN NULL,
    perm_usuarios BOOLEAN NULL,
    perm_reportes BOOLEAN NULL,
    perm_trazabilidad BOOLEAN NULL,
    perm_auditoria BOOLEAN NULL,
    perm_notificaciones BOOLEAN NULL,
    perm_movimientos BOOLEAN NULL,
    perm_donaciones BOOLEAN NULL DEFAULT FALSE,
    perm_crear_requisicion BOOLEAN NULL,
    perm_autorizar_admin BOOLEAN NULL,
    perm_autorizar_director BOOLEAN NULL,
    perm_recibir_farmacia BOOLEAN NULL,
    perm_autorizar_farmacia BOOLEAN NULL,
    perm_surtir BOOLEAN NULL,
    perm_confirmar_entrega BOOLEAN NULL,
    activo BOOLEAN NULL DEFAULT TRUE,
    CONSTRAINT chk_usuario_rol_valido CHECK (
        rol IN (
            'admin', 'admin_sistema', 'farmacia', 'vista', 'medico',
            'administrador_centro', 'director_centro', 'centro',
            'usuario_centro', 'usuario_normal'
        )
    )
);

CREATE INDEX IF NOT EXISTS idx_usuarios_username ON public.usuarios(username);
CREATE INDEX IF NOT EXISTS idx_usuarios_email ON public.usuarios(email);
CREATE INDEX IF NOT EXISTS idx_usuarios_centro ON public.usuarios(centro_id) WHERE centro_id IS NOT NULL;

-- =============================================================================
-- TABLAS DE RELACIÓN USUARIOS-GRUPOS Y USUARIOS-PERMISOS
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.usuarios_groups (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    group_id INTEGER NOT NULL REFERENCES auth_group(id) ON DELETE CASCADE,
    CONSTRAINT usuarios_groups_user_id_group_id_key UNIQUE (user_id, group_id)
);

CREATE INDEX IF NOT EXISTS idx_usuarios_groups_user_id ON public.usuarios_groups(user_id);
CREATE INDEX IF NOT EXISTS idx_usuarios_groups_group_id ON public.usuarios_groups(group_id);

CREATE TABLE IF NOT EXISTS public.usuarios_user_permissions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES auth_permission(id) ON DELETE CASCADE,
    CONSTRAINT usuarios_user_permissions_user_id_permission_id_key UNIQUE (user_id, permission_id)
);

CREATE INDEX IF NOT EXISTS idx_usuarios_user_permissions_user_id ON public.usuarios_user_permissions(user_id);
CREATE INDEX IF NOT EXISTS idx_usuarios_user_permissions_permission_id ON public.usuarios_user_permissions(permission_id);

-- =============================================================================
-- TABLA DE PERFILES DE USUARIO
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.user_profiles (
    id SERIAL PRIMARY KEY,
    rol VARCHAR(30) NOT NULL DEFAULT 'visualizador',
    telefono VARCHAR(20) NULL,
    centro_id INTEGER NULL REFERENCES centros(id) ON DELETE SET NULL,
    usuario_id INTEGER NOT NULL UNIQUE REFERENCES usuarios(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT valid_rol CHECK (
        rol IN (
            'admin', 'admin_sistema', 'farmacia', 'almacenista', 'medico',
            'enfermero', 'centro', 'usuario_centro', 'usuario_normal',
            'visualizador', 'vista'
        )
    )
);

CREATE INDEX IF NOT EXISTS idx_user_profiles_centro ON public.user_profiles(centro_id);
CREATE INDEX IF NOT EXISTS idx_user_profiles_rol ON public.user_profiles(rol);

DROP TRIGGER IF EXISTS update_user_profiles_updated_at ON user_profiles;
CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- TABLAS DE TOKENS JWT
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.token_blacklist_outstandingtoken (
    id SERIAL PRIMARY KEY,
    token TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    user_id INTEGER NULL REFERENCES usuarios(id) ON DELETE SET NULL,
    jti VARCHAR(255) NOT NULL UNIQUE
);

CREATE INDEX IF NOT EXISTS idx_token_blacklist_outstanding_user ON public.token_blacklist_outstandingtoken(user_id);
CREATE INDEX IF NOT EXISTS idx_token_blacklist_outstanding_jti ON public.token_blacklist_outstandingtoken(jti);

CREATE TABLE IF NOT EXISTS public.token_blacklist_blacklistedtoken (
    id SERIAL PRIMARY KEY,
    blacklisted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    token_id INTEGER NOT NULL UNIQUE REFERENCES token_blacklist_outstandingtoken(id) ON DELETE CASCADE
);

-- =============================================================================
-- TABLA DE TEMA GLOBAL
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.tema_global (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    es_activo BOOLEAN NOT NULL DEFAULT FALSE,
    logo_url VARCHAR(500) NULL,
    logo_width INTEGER NULL DEFAULT 160,
    logo_height INTEGER NULL DEFAULT 60,
    favicon_url VARCHAR(500) NULL,
    titulo_sistema VARCHAR(100) NULL DEFAULT 'Sistema de Inventario Farmacéutico',
    subtitulo_sistema VARCHAR(200) NULL DEFAULT 'Gobierno del Estado',
    color_primario VARCHAR(20) NULL DEFAULT '#9F2241',
    color_primario_hover VARCHAR(20) NULL DEFAULT '#6B1839',
    color_secundario VARCHAR(20) NULL DEFAULT '#424242',
    color_secundario_hover VARCHAR(20) NULL DEFAULT '#2E2E2E',
    color_exito VARCHAR(20) NULL DEFAULT '#4a7c4b',
    color_exito_hover VARCHAR(20) NULL DEFAULT '#3d663e',
    color_alerta VARCHAR(20) NULL DEFAULT '#d4a017',
    color_alerta_hover VARCHAR(20) NULL DEFAULT '#b38b14',
    color_error VARCHAR(20) NULL DEFAULT '#c53030',
    color_error_hover VARCHAR(20) NULL DEFAULT '#a52828',
    color_info VARCHAR(20) NULL DEFAULT '#3182ce',
    color_info_hover VARCHAR(20) NULL DEFAULT '#2c6cb0',
    color_fondo_principal VARCHAR(20) NULL DEFAULT '#f7f8fa',
    color_fondo_sidebar VARCHAR(20) NULL DEFAULT '#9F2241',
    color_fondo_header VARCHAR(20) NULL DEFAULT '#9F2241',
    color_texto_principal VARCHAR(20) NULL DEFAULT '#1f2937',
    color_texto_sidebar VARCHAR(20) NULL DEFAULT '#ffffff',
    color_texto_header VARCHAR(20) NULL DEFAULT '#ffffff',
    color_texto_links VARCHAR(20) NULL DEFAULT '#9F2241',
    color_borde_inputs VARCHAR(20) NULL DEFAULT '#d1d5db',
    color_borde_focus VARCHAR(20) NULL DEFAULT '#9F2241',
    reporte_color_encabezado VARCHAR(20) NULL DEFAULT '#9F2241',
    reporte_color_texto VARCHAR(20) NULL DEFAULT '#1f2937',
    reporte_color_filas_alternas VARCHAR(20) NULL,
    reporte_pie_pagina TEXT NULL,
    reporte_ano_visible BOOLEAN NULL DEFAULT TRUE,
    fuente_principal VARCHAR(100) NULL DEFAULT 'Montserrat',
    fuente_titulos VARCHAR(100) NULL DEFAULT 'Montserrat',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS update_tema_global_updated_at ON tema_global;
CREATE TRIGGER update_tema_global_updated_at
    BEFORE UPDATE ON tema_global
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- TABLA DE PRODUCTOS
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.productos (
    id SERIAL PRIMARY KEY,
    clave VARCHAR(50) NOT NULL UNIQUE,
    nombre VARCHAR(500) NOT NULL,
    descripcion TEXT NULL,
    unidad_medida VARCHAR(50) NOT NULL DEFAULT 'pieza',
    categoria VARCHAR(50) NOT NULL DEFAULT 'medicamento',
    stock_minimo INTEGER NOT NULL DEFAULT 10,
    stock_actual INTEGER NOT NULL DEFAULT 0,
    sustancia_activa VARCHAR(200) NULL,
    presentacion VARCHAR(200) NULL,
    concentracion VARCHAR(200) NULL,
    via_administracion VARCHAR(50) NULL,
    requiere_receta BOOLEAN NOT NULL DEFAULT FALSE,
    es_controlado BOOLEAN NOT NULL DEFAULT FALSE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    imagen VARCHAR(255) NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_producto_stock_minimo_positivo CHECK (stock_minimo >= 0),
    CONSTRAINT chk_producto_stock_actual_positivo CHECK (stock_actual >= 0),
    CONSTRAINT valid_categoria CHECK (
        categoria IN ('medicamento', 'material_curacion', 'equipo_medico', 'insumo', 'otro')
    )
);

CREATE INDEX IF NOT EXISTS idx_productos_clave ON public.productos(clave);
CREATE INDEX IF NOT EXISTS idx_productos_nombre ON public.productos(nombre);
CREATE INDEX IF NOT EXISTS idx_productos_nombre_trgm ON public.productos USING gin(nombre gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_productos_categoria ON public.productos(categoria);
CREATE INDEX IF NOT EXISTS idx_productos_activo ON public.productos(activo);

DROP TRIGGER IF EXISTS update_productos_updated_at ON productos;
CREATE TRIGGER update_productos_updated_at
    BEFORE UPDATE ON productos
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- TABLA DE IMÁGENES DE PRODUCTOS
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.producto_imagenes (
    id SERIAL PRIMARY KEY,
    producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
    imagen VARCHAR(255) NOT NULL,
    es_principal BOOLEAN NULL DEFAULT FALSE,
    orden INTEGER NULL DEFAULT 0,
    descripcion VARCHAR(255) NULL,
    created_at TIMESTAMP WITH TIME ZONE NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_producto_imagenes_producto ON public.producto_imagenes(producto_id);

-- =============================================================================
-- TABLA DE LOTES
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.lotes (
    id SERIAL PRIMARY KEY,
    numero_lote VARCHAR(100) NOT NULL,
    producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
    cantidad_inicial INTEGER NOT NULL,
    cantidad_actual INTEGER NOT NULL DEFAULT 0,
    fecha_fabricacion DATE NULL,
    fecha_caducidad DATE NOT NULL,
    precio_unitario NUMERIC(12, 2) NOT NULL DEFAULT 0,
    numero_contrato VARCHAR(100) NULL,
    marca VARCHAR(100) NULL,
    ubicacion VARCHAR(100) NULL,
    centro_id INTEGER NULL REFERENCES centros(id) ON DELETE SET NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT lote_producto_centro_unique UNIQUE (numero_lote, producto_id, centro_id),
    CONSTRAINT chk_lote_precio_positivo CHECK (precio_unitario >= 0),
    CONSTRAINT chk_lote_cantidad_actual_positiva CHECK (cantidad_actual >= 0),
    CONSTRAINT chk_lote_cantidad_inicial_positiva CHECK (cantidad_inicial >= 0)
);

CREATE INDEX IF NOT EXISTS idx_lotes_producto ON public.lotes(producto_id);
CREATE INDEX IF NOT EXISTS idx_lotes_centro ON public.lotes(centro_id);
CREATE INDEX IF NOT EXISTS idx_lotes_fecha_caducidad ON public.lotes(fecha_caducidad);
CREATE INDEX IF NOT EXISTS idx_lotes_activo ON public.lotes(activo);
CREATE INDEX IF NOT EXISTS idx_lotes_numero_lote ON public.lotes(numero_lote);
CREATE INDEX IF NOT EXISTS idx_lotes_producto_activo ON public.lotes(producto_id, activo);
CREATE INDEX IF NOT EXISTS idx_lotes_caducidad_activo ON public.lotes(fecha_caducidad, activo) WHERE activo = TRUE;
CREATE INDEX IF NOT EXISTS idx_lotes_pk_lock ON public.lotes(id);
CREATE INDEX IF NOT EXISTS idx_lotes_producto_centro ON public.lotes(producto_id, centro_id) WHERE activo = TRUE;
CREATE INDEX IF NOT EXISTS idx_lotes_caducidad ON public.lotes(fecha_caducidad) WHERE activo = TRUE;
CREATE INDEX IF NOT EXISTS idx_lotes_stock_disponible ON public.lotes(producto_id, centro_id, activo, fecha_caducidad) WHERE activo = TRUE AND cantidad_actual > 0;

DROP TRIGGER IF EXISTS update_lotes_updated_at ON lotes;
CREATE TRIGGER update_lotes_updated_at
    BEFORE UPDATE ON lotes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- TABLA DE DOCUMENTOS DE LOTES
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.lote_documentos (
    id SERIAL PRIMARY KEY,
    lote_id INTEGER NOT NULL REFERENCES lotes(id) ON DELETE CASCADE,
    tipo_documento VARCHAR(50) NOT NULL,
    numero_documento VARCHAR(100) NULL,
    archivo VARCHAR(255) NOT NULL,
    nombre_archivo VARCHAR(255) NULL,
    fecha_documento DATE NULL,
    notas TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE NULL DEFAULT NOW(),
    created_by INTEGER NULL REFERENCES usuarios(id) ON DELETE SET NULL,
    CONSTRAINT lote_documentos_tipo_documento_check CHECK (
        tipo_documento IN ('factura', 'contrato', 'remision', 'otro')
    )
);

CREATE INDEX IF NOT EXISTS idx_lote_documentos_lote ON public.lote_documentos(lote_id);
CREATE INDEX IF NOT EXISTS idx_lote_documentos_tipo ON public.lote_documentos(tipo_documento);

-- =============================================================================
-- TABLA DE MOVIMIENTOS
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.movimientos (
    id SERIAL PRIMARY KEY,
    tipo VARCHAR(30) NOT NULL,
    producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
    lote_id INTEGER NULL REFERENCES lotes(id) ON DELETE SET NULL,
    cantidad INTEGER NOT NULL,
    centro_origen_id INTEGER NULL REFERENCES centros(id) ON DELETE SET NULL,
    centro_destino_id INTEGER NULL REFERENCES centros(id) ON DELETE SET NULL,
    requisicion_id INTEGER NULL,
    usuario_id INTEGER NULL REFERENCES usuarios(id) ON DELETE SET NULL,
    motivo TEXT NULL,
    referencia VARCHAR(100) NULL,
    fecha TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    subtipo_salida VARCHAR(30) NULL,
    numero_expediente VARCHAR(50) NULL,
    CONSTRAINT chk_movimiento_tipo_valido CHECK (
        tipo IN ('entrada', 'salida', 'transferencia', 'ajuste_positivo', 'ajuste_negativo', 'devolucion', 'merma', 'caducidad')
    ),
    CONSTRAINT chk_movimiento_cantidad_positiva CHECK (cantidad > 0)
);

CREATE INDEX IF NOT EXISTS idx_movimientos_producto ON public.movimientos(producto_id);
CREATE INDEX IF NOT EXISTS idx_movimientos_lote ON public.movimientos(lote_id);
CREATE INDEX IF NOT EXISTS idx_movimientos_requisicion ON public.movimientos(requisicion_id);
CREATE INDEX IF NOT EXISTS idx_movimientos_tipo ON public.movimientos(tipo);
CREATE INDEX IF NOT EXISTS idx_movimientos_fecha ON public.movimientos(fecha);
CREATE INDEX IF NOT EXISTS idx_movimientos_usuario ON public.movimientos(usuario_id);
CREATE INDEX IF NOT EXISTS idx_movimientos_producto_fecha ON public.movimientos(producto_id, fecha DESC);
CREATE INDEX IF NOT EXISTS idx_movimientos_numero_expediente ON public.movimientos(numero_expediente) WHERE numero_expediente IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_movimientos_subtipo_salida ON public.movimientos(subtipo_salida) WHERE subtipo_salida IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_movimientos_requisicion_tipo ON public.movimientos(requisicion_id, tipo) WHERE requisicion_id IS NOT NULL;

-- =============================================================================
-- TABLA DE REQUISICIONES
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.requisiciones (
    id SERIAL PRIMARY KEY,
    numero VARCHAR(50) NOT NULL UNIQUE,
    centro_origen_id INTEGER NULL REFERENCES centros(id) ON DELETE SET NULL,
    centro_destino_id INTEGER NULL REFERENCES centros(id) ON DELETE SET NULL,
    solicitante_id INTEGER NULL REFERENCES usuarios(id) ON DELETE SET NULL,
    autorizador_id INTEGER NULL REFERENCES usuarios(id) ON DELETE SET NULL,
    estado VARCHAR(30) NOT NULL DEFAULT 'borrador',
    tipo VARCHAR(30) NOT NULL DEFAULT 'normal',
    prioridad VARCHAR(20) NOT NULL DEFAULT 'normal',
    notas TEXT NULL,
    lugar_entrega VARCHAR(255) NULL,
    fecha_solicitud TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    fecha_autorizacion TIMESTAMP WITH TIME ZONE NULL,
    fecha_surtido TIMESTAMP WITH TIME ZONE NULL,
    fecha_entrega TIMESTAMP WITH TIME ZONE NULL,
    foto_firma_surtido VARCHAR(255) NULL,
    foto_firma_recepcion VARCHAR(255) NULL,
    usuario_firma_surtido_id INTEGER NULL REFERENCES usuarios(id) ON DELETE SET NULL,
    usuario_firma_recepcion_id INTEGER NULL REFERENCES usuarios(id) ON DELETE SET NULL,
    fecha_firma_surtido TIMESTAMP WITH TIME ZONE NULL,
    fecha_firma_recepcion TIMESTAMP WITH TIME ZONE NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    firma_solicitante VARCHAR(255) NULL,
    nombre_solicitante VARCHAR(255) NULL,
    cargo_solicitante VARCHAR(100) NULL,
    firma_jefe_area VARCHAR(255) NULL,
    nombre_jefe_area VARCHAR(255) NULL,
    cargo_jefe_area VARCHAR(100) NULL,
    firma_director VARCHAR(255) NULL,
    nombre_director VARCHAR(255) NULL,
    cargo_director VARCHAR(100) NULL,
    fecha_entrega_solicitada DATE NULL,
    es_urgente BOOLEAN NULL DEFAULT FALSE,
    motivo_urgencia TEXT NULL,
    fecha_envio_admin TIMESTAMP WITH TIME ZONE NULL,
    fecha_autorizacion_admin TIMESTAMP WITH TIME ZONE NULL,
    fecha_envio_director TIMESTAMP WITH TIME ZONE NULL,
    fecha_autorizacion_director TIMESTAMP WITH TIME ZONE NULL,
    fecha_envio_farmacia TIMESTAMP WITH TIME ZONE NULL,
    fecha_recepcion_farmacia TIMESTAMP WITH TIME ZONE NULL,
    fecha_autorizacion_farmacia TIMESTAMP WITH TIME ZONE NULL,
    fecha_recoleccion_limite TIMESTAMP WITH TIME ZONE NULL,
    fecha_vencimiento TIMESTAMP WITH TIME ZONE NULL,
    administrador_centro_id INTEGER NULL REFERENCES usuarios(id),
    director_centro_id INTEGER NULL REFERENCES usuarios(id),
    receptor_farmacia_id INTEGER NULL REFERENCES usuarios(id),
    autorizador_farmacia_id INTEGER NULL REFERENCES usuarios(id),
    surtidor_id INTEGER NULL REFERENCES usuarios(id),
    motivo_rechazo TEXT NULL,
    motivo_devolucion TEXT NULL,
    motivo_vencimiento TEXT NULL,
    observaciones_farmacia TEXT NULL,
    CONSTRAINT requisiciones_estado_check CHECK (
        estado IN (
            'borrador', 'pendiente_admin', 'pendiente_director', 'enviada',
            'en_revision', 'autorizada', 'en_surtido', 'surtida', 'parcial',
            'entregada', 'rechazada', 'vencida', 'cancelada', 'devuelta'
        )
    ),
    CONSTRAINT valid_tipo CHECK (
        tipo IN ('normal', 'urgente', 'programada', 'transferencia', 'emergencia')
    ),
    CONSTRAINT valid_prioridad CHECK (
        prioridad IN ('baja', 'normal', 'alta', 'urgente')
    )
);

CREATE INDEX IF NOT EXISTS idx_requisiciones_centro_origen ON public.requisiciones(centro_origen_id);
CREATE INDEX IF NOT EXISTS idx_requisiciones_centro_destino ON public.requisiciones(centro_destino_id);
CREATE INDEX IF NOT EXISTS idx_requisiciones_solicitante ON public.requisiciones(solicitante_id);
CREATE INDEX IF NOT EXISTS idx_requisiciones_estado ON public.requisiciones(estado);
CREATE INDEX IF NOT EXISTS idx_requisiciones_fecha_solicitud ON public.requisiciones(fecha_solicitud);
CREATE INDEX IF NOT EXISTS idx_requisiciones_numero ON public.requisiciones(numero);
CREATE INDEX IF NOT EXISTS idx_requisiciones_estado_fecha ON public.requisiciones(estado, fecha_solicitud DESC);
CREATE INDEX IF NOT EXISTS idx_requisiciones_centro_estado ON public.requisiciones(centro_origen_id, estado);
CREATE INDEX IF NOT EXISTS idx_requisiciones_fecha_recoleccion ON public.requisiciones(fecha_recoleccion_limite) WHERE estado = 'surtida';
CREATE INDEX IF NOT EXISTS idx_requisiciones_surtidas_limite ON public.requisiciones(estado, fecha_recoleccion_limite) WHERE estado = 'surtida';

-- Agregar FK solo si no existe
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'movimientos_requisicion_id_fkey') THEN
        ALTER TABLE public.movimientos 
            ADD CONSTRAINT movimientos_requisicion_id_fkey 
            FOREIGN KEY (requisicion_id) REFERENCES requisiciones(id) ON DELETE SET NULL;
    END IF;
END $$;

-- ISS-FIX: Trigger de historial DESHABILITADO - causa duplicados
-- El historial de cambios de estado se registra desde Python con más contexto
-- (usuario, motivo, IP, user_agent). El trigger solo registra estado anterior/nuevo.
-- DROP TRIGGER IF EXISTS trigger_historial_estado_requisicion ON requisiciones;
-- CREATE TRIGGER trigger_historial_estado_requisicion
--     AFTER UPDATE ON requisiciones
--     FOR EACH ROW
--     EXECUTE FUNCTION registrar_cambio_estado_requisicion();

DROP TRIGGER IF EXISTS trigger_validar_transicion_requisicion ON requisiciones;
CREATE TRIGGER trigger_validar_transicion_requisicion
    BEFORE UPDATE ON requisiciones
    FOR EACH ROW
    WHEN (OLD.estado IS DISTINCT FROM NEW.estado)
    EXECUTE FUNCTION validar_transicion_estado_requisicion();

DROP TRIGGER IF EXISTS update_requisiciones_updated_at ON requisiciones;
CREATE TRIGGER update_requisiciones_updated_at
    BEFORE UPDATE ON requisiciones
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- TABLA DE DETALLES DE REQUISICIÓN
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.detalles_requisicion (
    id SERIAL PRIMARY KEY,
    requisicion_id INTEGER NOT NULL REFERENCES requisiciones(id) ON DELETE CASCADE,
    producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
    cantidad_solicitada INTEGER NOT NULL,
    cantidad_autorizada INTEGER NULL,
    cantidad_surtida INTEGER NULL DEFAULT 0,
    cantidad_entregada INTEGER NULL DEFAULT 0,
    lote_id INTEGER NULL REFERENCES lotes(id) ON DELETE SET NULL,
    notas TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_detalle_cantidad_solicitada_positiva CHECK (cantidad_solicitada > 0),
    CONSTRAINT chk_detalle_cantidad_autorizada_positiva CHECK (cantidad_autorizada IS NULL OR cantidad_autorizada >= 0),
    CONSTRAINT chk_detalle_cantidad_surtida_positiva CHECK (cantidad_surtida >= 0),
    CONSTRAINT chk_detalle_cantidad_entregada_positiva CHECK (cantidad_entregada >= 0)
);

CREATE INDEX IF NOT EXISTS idx_detalles_requisicion_requisicion ON public.detalles_requisicion(requisicion_id);
CREATE INDEX IF NOT EXISTS idx_detalles_requisicion_producto ON public.detalles_requisicion(producto_id);
CREATE INDEX IF NOT EXISTS idx_detalles_requisicion_lote ON public.detalles_requisicion(lote_id);

DROP TRIGGER IF EXISTS update_detalles_requisicion_updated_at ON detalles_requisicion;
CREATE TRIGGER update_detalles_requisicion_updated_at
    BEFORE UPDATE ON detalles_requisicion
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- TABLA DE HISTORIAL DE ESTADOS DE REQUISICIÓN
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.requisicion_historial_estados (
    id SERIAL PRIMARY KEY,
    requisicion_id INTEGER NOT NULL REFERENCES requisiciones(id) ON DELETE CASCADE,
    estado_anterior VARCHAR(50) NULL,
    estado_nuevo VARCHAR(50) NOT NULL,
    usuario_id INTEGER NULL REFERENCES usuarios(id),
    fecha_cambio TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    accion VARCHAR(100) NOT NULL,
    motivo TEXT NULL,
    observaciones TEXT NULL,
    ip_address VARCHAR(45) NULL,
    user_agent TEXT NULL,
    datos_adicionales JSONB NULL,
    hash_verificacion VARCHAR(64) NULL
);

CREATE INDEX IF NOT EXISTS idx_historial_fecha ON public.requisicion_historial_estados(fecha_cambio);
CREATE INDEX IF NOT EXISTS idx_historial_requisicion ON public.requisicion_historial_estados(requisicion_id);
CREATE INDEX IF NOT EXISTS idx_historial_usuario ON public.requisicion_historial_estados(usuario_id);
CREATE INDEX IF NOT EXISTS idx_historial_estado_nuevo ON public.requisicion_historial_estados(estado_nuevo);

-- =============================================================================
-- TABLA DE AJUSTES DE CANTIDAD EN REQUISICIONES
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.requisicion_ajustes_cantidad (
    id SERIAL PRIMARY KEY,
    detalle_requisicion_id INTEGER NOT NULL REFERENCES detalles_requisicion(id) ON DELETE CASCADE,
    cantidad_original INTEGER NOT NULL,
    cantidad_ajustada INTEGER NOT NULL,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    fecha_ajuste TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    motivo_ajuste TEXT NOT NULL,
    tipo_ajuste VARCHAR(50) NOT NULL,
    producto_sustituto_id INTEGER NULL REFERENCES productos(id),
    ip_address VARCHAR(45) NULL,
    created_at TIMESTAMP WITH TIME ZONE NULL DEFAULT NOW(),
    CONSTRAINT requisicion_ajustes_cantidad_tipo_ajuste_check CHECK (
        tipo_ajuste IN ('sin_stock', 'producto_agotado', 'sustitucion', 'correccion_cantidad', 'lote_proximo_caducar')
    )
);

CREATE INDEX IF NOT EXISTS idx_ajustes_detalle ON public.requisicion_ajustes_cantidad(detalle_requisicion_id);
CREATE INDEX IF NOT EXISTS idx_ajustes_usuario ON public.requisicion_ajustes_cantidad(usuario_id);

-- =============================================================================
-- TABLAS DE DONACIONES
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.donaciones (
    id SERIAL PRIMARY KEY,
    numero VARCHAR(50) NOT NULL UNIQUE,
    donante_nombre VARCHAR(255) NOT NULL,
    donante_tipo VARCHAR(50) NULL,
    donante_rfc VARCHAR(20) NULL,
    donante_direccion TEXT NULL,
    donante_contacto VARCHAR(100) NULL,
    fecha_donacion DATE NOT NULL,
    fecha_recepcion TIMESTAMP WITH TIME ZONE NULL DEFAULT NOW(),
    centro_destino_id INTEGER NULL REFERENCES centros(id) ON DELETE SET NULL,
    recibido_por_id INTEGER NULL REFERENCES usuarios(id) ON DELETE SET NULL,
    estado VARCHAR(30) NULL DEFAULT 'pendiente',
    notas TEXT NULL,
    documento_donacion VARCHAR(255) NULL,
    created_at TIMESTAMP WITH TIME ZONE NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NULL DEFAULT NOW(),
    CONSTRAINT donaciones_donante_tipo_check CHECK (
        donante_tipo IN ('empresa', 'gobierno', 'ong', 'particular', 'otro')
    ),
    CONSTRAINT donaciones_estado_check CHECK (
        estado IN ('pendiente', 'recibida', 'procesada', 'rechazada')
    )
);

CREATE INDEX IF NOT EXISTS idx_donaciones_estado ON public.donaciones(estado);
CREATE INDEX IF NOT EXISTS idx_donaciones_centro ON public.donaciones(centro_destino_id);
CREATE INDEX IF NOT EXISTS idx_donaciones_fecha ON public.donaciones(fecha_donacion);

DROP TRIGGER IF EXISTS trigger_donaciones_updated_at ON donaciones;
CREATE TRIGGER trigger_donaciones_updated_at
    BEFORE UPDATE ON donaciones
    FOR EACH ROW
    EXECUTE FUNCTION update_donaciones_updated_at();

-- =============================================================================
-- TABLA DE PRODUCTOS DE DONACIÓN
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.productos_donacion (
    id SERIAL PRIMARY KEY,
    clave VARCHAR(50) NOT NULL UNIQUE,
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT NULL,
    unidad_medida VARCHAR(50) NULL DEFAULT 'PIEZA',
    presentacion VARCHAR(100) NULL,
    activo BOOLEAN NULL DEFAULT TRUE,
    notas TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_productos_donacion_clave ON public.productos_donacion(clave);
CREATE INDEX IF NOT EXISTS idx_productos_donacion_nombre ON public.productos_donacion(nombre);
CREATE INDEX IF NOT EXISTS idx_productos_donacion_activo ON public.productos_donacion(activo);

DROP TRIGGER IF EXISTS trg_productos_donacion_updated_at ON productos_donacion;
CREATE TRIGGER trg_productos_donacion_updated_at
    BEFORE UPDATE ON productos_donacion
    FOR EACH ROW
    EXECUTE FUNCTION update_productos_donacion_updated_at();

-- =============================================================================
-- TABLA DE DETALLE DE DONACIONES
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.detalle_donaciones (
    id SERIAL PRIMARY KEY,
    donacion_id INTEGER NOT NULL REFERENCES donaciones(id) ON DELETE CASCADE,
    producto_donacion_id INTEGER NULL REFERENCES productos_donacion(id) ON DELETE SET NULL,
    producto_id INTEGER NULL REFERENCES productos(id) ON DELETE SET NULL,
    cantidad INTEGER NOT NULL,
    cantidad_disponible INTEGER NOT NULL DEFAULT 0,
    lote VARCHAR(100) NULL,
    fecha_caducidad DATE NULL,
    notas TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE NULL DEFAULT NOW(),
    CONSTRAINT chk_detalle_donacion_cantidad_positiva CHECK (cantidad > 0),
    CONSTRAINT chk_detalle_donacion_cantidad_disponible_positiva CHECK (cantidad_disponible >= 0)
);

CREATE INDEX IF NOT EXISTS idx_detalle_donaciones_donacion ON public.detalle_donaciones(donacion_id);
CREATE INDEX IF NOT EXISTS idx_detalle_donaciones_producto ON public.detalle_donaciones(producto_id);
CREATE INDEX IF NOT EXISTS idx_detalle_donaciones_producto_donacion ON public.detalle_donaciones(producto_donacion_id);

-- =============================================================================
-- TABLA DE SALIDAS DE DONACIONES
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.salidas_donaciones (
    id SERIAL PRIMARY KEY,
    detalle_donacion_id INTEGER NOT NULL REFERENCES detalle_donaciones(id) ON DELETE RESTRICT,
    cantidad INTEGER NOT NULL,
    destinatario VARCHAR(255) NOT NULL,
    motivo TEXT NULL,
    entregado_por_id INTEGER NULL REFERENCES usuarios(id) ON DELETE SET NULL,
    fecha_entrega TIMESTAMP WITH TIME ZONE NULL DEFAULT NOW(),
    notas TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE NULL DEFAULT NOW(),
    CONSTRAINT salidas_donaciones_cantidad_check CHECK (cantidad > 0)
);

CREATE INDEX IF NOT EXISTS idx_salidas_donaciones_detalle ON public.salidas_donaciones(detalle_donacion_id);
CREATE INDEX IF NOT EXISTS idx_salidas_donaciones_fecha ON public.salidas_donaciones(fecha_entrega);

-- =============================================================================
-- TABLA DE HOJAS DE RECOLECCIÓN
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.hojas_recoleccion (
    id SERIAL PRIMARY KEY,
    numero VARCHAR(50) NOT NULL UNIQUE,
    centro_id INTEGER NULL REFERENCES centros(id) ON DELETE SET NULL,
    responsable_id INTEGER NULL REFERENCES usuarios(id) ON DELETE SET NULL,
    estado VARCHAR(30) NOT NULL DEFAULT 'pendiente',
    fecha_programada DATE NOT NULL,
    fecha_recoleccion TIMESTAMP WITH TIME ZONE NULL,
    notas TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT valid_estado_hoja CHECK (
        estado IN ('pendiente', 'en_proceso', 'completada', 'cancelada')
    )
);

CREATE INDEX IF NOT EXISTS idx_hojas_recoleccion_centro ON public.hojas_recoleccion(centro_id);
CREATE INDEX IF NOT EXISTS idx_hojas_recoleccion_estado ON public.hojas_recoleccion(estado);
CREATE INDEX IF NOT EXISTS idx_hojas_recoleccion_fecha_programada ON public.hojas_recoleccion(fecha_programada);

DROP TRIGGER IF EXISTS update_hojas_recoleccion_updated_at ON hojas_recoleccion;
CREATE TRIGGER update_hojas_recoleccion_updated_at
    BEFORE UPDATE ON hojas_recoleccion
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- TABLA DE DETALLE DE HOJAS DE RECOLECCIÓN
-- =============================================================================
-- NOTA: requisicion_id removido porque no existe en la BD de producción

CREATE TABLE IF NOT EXISTS public.detalle_hojas_recoleccion (
    id SERIAL PRIMARY KEY,
    hoja_recoleccion_id INTEGER NOT NULL REFERENCES hojas_recoleccion(id) ON DELETE CASCADE,
    orden INTEGER NOT NULL DEFAULT 0,
    recolectado BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_recoleccion TIMESTAMP WITH TIME ZONE NULL,
    notas TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_detalle_hojas_hoja ON public.detalle_hojas_recoleccion(hoja_recoleccion_id);

-- =============================================================================
-- TABLA DE NOTIFICACIONES
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.notificaciones (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    tipo VARCHAR(50) NOT NULL,
    titulo VARCHAR(200) NOT NULL,
    mensaje TEXT NOT NULL,
    leida BOOLEAN NOT NULL DEFAULT FALSE,
    datos JSONB NULL,
    url VARCHAR(500) NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notificaciones_usuario ON public.notificaciones(usuario_id);
CREATE INDEX IF NOT EXISTS idx_notificaciones_leida ON public.notificaciones(leida);
CREATE INDEX IF NOT EXISTS idx_notificaciones_tipo ON public.notificaciones(tipo);

-- =============================================================================
-- TABLA DE LOGS DE IMPORTACIÓN
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.importacion_logs (
    id SERIAL PRIMARY KEY,
    archivo VARCHAR(255) NOT NULL,
    tipo_importacion VARCHAR(50) NOT NULL,
    usuario_id INTEGER NULL REFERENCES usuarios(id) ON DELETE SET NULL,
    registros_totales INTEGER NOT NULL DEFAULT 0,
    registros_exitosos INTEGER NOT NULL DEFAULT 0,
    registros_fallidos INTEGER NOT NULL DEFAULT 0,
    errores JSONB NULL,
    estado VARCHAR(30) NOT NULL DEFAULT 'procesando',
    fecha_inicio TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    fecha_fin TIMESTAMP WITH TIME ZONE NULL,
    CONSTRAINT valid_estado_importacion CHECK (
        estado IN ('procesando', 'completado', 'fallido', 'parcial')
    )
);

CREATE INDEX IF NOT EXISTS idx_importacion_logs_usuario ON public.importacion_logs(usuario_id);
CREATE INDEX IF NOT EXISTS idx_importacion_logs_estado ON public.importacion_logs(estado);

-- =============================================================================
-- TABLA DE SESIONES DE DJANGO
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.django_session (
    session_key VARCHAR(40) PRIMARY KEY,
    session_data TEXT NOT NULL,
    expire_date TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_django_session_expire_date ON public.django_session(expire_date);

-- =============================================================================
-- TABLA DE MIGRACIONES DE DJANGO
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.django_migrations (
    id SERIAL PRIMARY KEY,
    app VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    applied TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- TABLA DE LOG DE ADMIN DE DJANGO
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.django_admin_log (
    id SERIAL PRIMARY KEY,
    action_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    object_id TEXT NULL,
    object_repr VARCHAR(200) NOT NULL,
    action_flag SMALLINT NOT NULL,
    change_message TEXT NOT NULL DEFAULT '',
    content_type_id INTEGER NULL REFERENCES django_content_type(id) ON DELETE SET NULL,
    user_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    CONSTRAINT django_admin_log_action_flag_check CHECK (action_flag >= 0)
);

CREATE INDEX IF NOT EXISTS idx_django_admin_log_content_type ON public.django_admin_log(content_type_id);
CREATE INDEX IF NOT EXISTS idx_django_admin_log_user ON public.django_admin_log(user_id);

-- =============================================================================
-- TABLA DE AUDITORÍA (auditoria_logs)
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.auditoria_logs (
    id SERIAL PRIMARY KEY,
    tabla VARCHAR(100) NOT NULL,
    registro_id INTEGER NOT NULL,
    accion VARCHAR(20) NOT NULL,
    usuario_id INTEGER NULL REFERENCES usuarios(id) ON DELETE SET NULL,
    datos_anteriores JSONB NULL,
    datos_nuevos JSONB NULL,
    ip_address VARCHAR(45) NULL,
    user_agent TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT valid_accion_auditoria CHECK (
        accion IN ('INSERT', 'UPDATE', 'DELETE')
    )
);

CREATE INDEX IF NOT EXISTS idx_auditoria_logs_tabla ON public.auditoria_logs(tabla);
CREATE INDEX IF NOT EXISTS idx_auditoria_logs_registro ON public.auditoria_logs(registro_id);
CREATE INDEX IF NOT EXISTS idx_auditoria_logs_usuario ON public.auditoria_logs(usuario_id);
CREATE INDEX IF NOT EXISTS idx_auditoria_logs_fecha ON public.auditoria_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_auditoria_logs_accion ON public.auditoria_logs(accion);

-- =============================================================================
-- TABLA DE CONFIGURACIÓN DEL SISTEMA
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.configuracion_sistema (
    id SERIAL PRIMARY KEY,
    clave VARCHAR(100) NOT NULL UNIQUE,
    valor TEXT NULL,
    tipo VARCHAR(20) NOT NULL DEFAULT 'string',
    descripcion TEXT NULL,
    categoria VARCHAR(50) NULL DEFAULT 'general',
    es_publica BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT valid_tipo_config CHECK (
        tipo IN ('string', 'integer', 'boolean', 'json', 'float', 'date')
    )
);

DROP TRIGGER IF EXISTS update_configuracion_sistema_updated_at ON configuracion_sistema;
CREATE TRIGGER update_configuracion_sistema_updated_at
    BEFORE UPDATE ON configuracion_sistema
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- VISTA: vista_requisiciones_completa
-- =============================================================================

CREATE OR REPLACE VIEW vista_requisiciones_completa AS
SELECT 
    r.id,
    r.numero,
    r.estado,
    r.tipo,
    r.prioridad,
    r.notas,
    r.lugar_entrega,
    r.fecha_solicitud,
    r.fecha_autorizacion,
    r.fecha_surtido,
    r.fecha_entrega,
    r.fecha_entrega_solicitada,
    r.es_urgente,
    r.motivo_urgencia,
    r.motivo_rechazo,
    r.motivo_devolucion,
    r.observaciones_farmacia,
    r.created_at,
    r.updated_at,
    -- Centro origen
    r.centro_origen_id,
    co.nombre AS centro_origen_nombre,
    co.codigo AS centro_origen_codigo,
    -- Centro destino
    r.centro_destino_id,
    cd.nombre AS centro_destino_nombre,
    cd.codigo AS centro_destino_codigo,
    -- Solicitante
    r.solicitante_id,
    us.username AS solicitante_username,
    us.first_name || ' ' || us.last_name AS solicitante_nombre_completo,
    us.email AS solicitante_email,
    -- Autorizador
    r.autorizador_id,
    ua.username AS autorizador_username,
    ua.first_name || ' ' || ua.last_name AS autorizador_nombre_completo,
    -- Administrador centro
    r.administrador_centro_id,
    uac.username AS administrador_centro_username,
    uac.first_name || ' ' || uac.last_name AS administrador_centro_nombre,
    -- Director centro
    r.director_centro_id,
    udc.username AS director_centro_username,
    udc.first_name || ' ' || udc.last_name AS director_centro_nombre,
    -- Receptor farmacia
    r.receptor_farmacia_id,
    urf.username AS receptor_farmacia_username,
    urf.first_name || ' ' || urf.last_name AS receptor_farmacia_nombre,
    -- Autorizador farmacia
    r.autorizador_farmacia_id,
    uaf.username AS autorizador_farmacia_username,
    uaf.first_name || ' ' || uaf.last_name AS autorizador_farmacia_nombre,
    -- Surtidor
    r.surtidor_id,
    usur.username AS surtidor_username,
    usur.first_name || ' ' || usur.last_name AS surtidor_nombre,
    -- Fechas de flujo
    r.fecha_envio_admin,
    r.fecha_autorizacion_admin,
    r.fecha_envio_director,
    r.fecha_autorizacion_director,
    r.fecha_envio_farmacia,
    r.fecha_recepcion_farmacia,
    r.fecha_autorizacion_farmacia,
    r.fecha_recoleccion_limite,
    r.fecha_vencimiento,
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
    -- Conteos
    (SELECT COUNT(*) FROM detalles_requisicion dr WHERE dr.requisicion_id = r.id) AS total_items,
    (SELECT COALESCE(SUM(dr.cantidad_solicitada), 0) FROM detalles_requisicion dr WHERE dr.requisicion_id = r.id) AS total_cantidad_solicitada,
    (SELECT COALESCE(SUM(dr.cantidad_autorizada), 0) FROM detalles_requisicion dr WHERE dr.requisicion_id = r.id) AS total_cantidad_autorizada,
    (SELECT COALESCE(SUM(dr.cantidad_surtida), 0) FROM detalles_requisicion dr WHERE dr.requisicion_id = r.id) AS total_cantidad_surtida,
    (SELECT COALESCE(SUM(dr.cantidad_entregada), 0) FROM detalles_requisicion dr WHERE dr.requisicion_id = r.id) AS total_cantidad_entregada
FROM requisiciones r
LEFT JOIN centros co ON co.id = r.centro_origen_id
LEFT JOIN centros cd ON cd.id = r.centro_destino_id
LEFT JOIN usuarios us ON us.id = r.solicitante_id
LEFT JOIN usuarios ua ON ua.id = r.autorizador_id
LEFT JOIN usuarios uac ON uac.id = r.administrador_centro_id
LEFT JOIN usuarios udc ON udc.id = r.director_centro_id
LEFT JOIN usuarios urf ON urf.id = r.receptor_farmacia_id
LEFT JOIN usuarios uaf ON uaf.id = r.autorizador_farmacia_id
LEFT JOIN usuarios usur ON usur.id = r.surtidor_id;

-- =============================================================================
-- COMENTARIOS EN TABLAS
-- =============================================================================

COMMENT ON TABLE usuarios IS 'Usuarios del sistema con permisos granulares';
COMMENT ON TABLE centros IS 'Centros penitenciarios y almacenes';
COMMENT ON TABLE productos IS 'Catálogo de productos farmacéuticos';
COMMENT ON TABLE lotes IS 'Lotes de productos con control de caducidad';
COMMENT ON TABLE movimientos IS 'Registro de todos los movimientos de inventario';
COMMENT ON TABLE requisiciones IS 'Solicitudes de productos entre centros';
COMMENT ON TABLE donaciones IS 'Registro de donaciones recibidas';
COMMENT ON TABLE tema_global IS 'Configuración de tema visual del sistema';
COMMENT ON TABLE auditoria_logs IS 'Registro de auditoría de cambios en el sistema';
COMMENT ON TABLE notificaciones IS 'Notificaciones para usuarios';

-- =============================================================================
-- DESHABILITAR RLS EN TODAS LAS TABLAS
-- =============================================================================

ALTER TABLE IF EXISTS public.auditoria_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.auth_group DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.auth_group_permissions DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.auth_permission DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.centros DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.configuracion_sistema DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.detalle_donaciones DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.detalle_hojas_recoleccion DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.detalles_requisicion DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.django_admin_log DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.django_content_type DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.django_migrations DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.django_session DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.donaciones DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.hojas_recoleccion DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.importacion_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.lote_documentos DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.lotes DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.movimientos DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.notificaciones DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.producto_imagenes DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.productos DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.productos_donacion DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.requisicion_ajustes_cantidad DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.requisicion_historial_estados DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.requisiciones DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.salidas_donaciones DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.tema_global DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.token_blacklist_blacklistedtoken DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.token_blacklist_outstandingtoken DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.user_profiles DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.usuarios DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.usuarios_groups DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.usuarios_user_permissions DISABLE ROW LEVEL SECURITY;

-- =============================================================================
-- FIN DEL SCRIPT
-- =============================================================================

SELECT 'Base de datos de desarrollo creada exitosamente (sin RLS)' AS mensaje;
