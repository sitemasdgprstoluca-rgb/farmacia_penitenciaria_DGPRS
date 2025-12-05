-- ==========================================================================
-- FARMACIA PENITENCIARIA - CORRECCIÓN COMPLETA DE MIGRACIONES PARA SUPABASE
-- Ejecutar en Supabase SQL Editor para corregir la tabla django_migrations
-- ==========================================================================

-- ========== PASO 0: Añadir columnas faltantes a la tabla usuarios ==========
-- Estas columnas son requeridas por el modelo User personalizado de Django

-- Añadir columna 'rol' si no existe
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'usuarios' AND column_name = 'rol') THEN
        ALTER TABLE usuarios ADD COLUMN rol VARCHAR(20) DEFAULT 'usuario_normal' NOT NULL;
    END IF;
END $$;

-- Añadir columna 'centro_id' (FK) si no existe
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'usuarios' AND column_name = 'centro_id') THEN
        ALTER TABLE usuarios ADD COLUMN centro_id INTEGER NULL;
    END IF;
END $$;

-- Añadir columna 'adscripcion' si no existe
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'usuarios' AND column_name = 'adscripcion') THEN
        ALTER TABLE usuarios ADD COLUMN adscripcion VARCHAR(200) DEFAULT '' NOT NULL;
    END IF;
END $$;

-- Añadir columna 'activo' si no existe
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'usuarios' AND column_name = 'activo') THEN
        ALTER TABLE usuarios ADD COLUMN activo BOOLEAN DEFAULT TRUE NOT NULL;
    END IF;
END $$;

-- Añadir permisos personalizados por módulo
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'usuarios' AND column_name = 'perm_dashboard') THEN
        ALTER TABLE usuarios ADD COLUMN perm_dashboard BOOLEAN NULL;
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'usuarios' AND column_name = 'perm_productos') THEN
        ALTER TABLE usuarios ADD COLUMN perm_productos BOOLEAN NULL;
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'usuarios' AND column_name = 'perm_lotes') THEN
        ALTER TABLE usuarios ADD COLUMN perm_lotes BOOLEAN NULL;
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'usuarios' AND column_name = 'perm_requisiciones') THEN
        ALTER TABLE usuarios ADD COLUMN perm_requisiciones BOOLEAN NULL;
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'usuarios' AND column_name = 'perm_centros') THEN
        ALTER TABLE usuarios ADD COLUMN perm_centros BOOLEAN NULL;
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'usuarios' AND column_name = 'perm_usuarios') THEN
        ALTER TABLE usuarios ADD COLUMN perm_usuarios BOOLEAN NULL;
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'usuarios' AND column_name = 'perm_reportes') THEN
        ALTER TABLE usuarios ADD COLUMN perm_reportes BOOLEAN NULL;
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'usuarios' AND column_name = 'perm_trazabilidad') THEN
        ALTER TABLE usuarios ADD COLUMN perm_trazabilidad BOOLEAN NULL;
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'usuarios' AND column_name = 'perm_auditoria') THEN
        ALTER TABLE usuarios ADD COLUMN perm_auditoria BOOLEAN NULL;
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'usuarios' AND column_name = 'perm_notificaciones') THEN
        ALTER TABLE usuarios ADD COLUMN perm_notificaciones BOOLEAN NULL;
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'usuarios' AND column_name = 'perm_movimientos') THEN
        ALTER TABLE usuarios ADD COLUMN perm_movimientos BOOLEAN NULL;
    END IF;
END $$;

-- Crear índices para la tabla usuarios si no existen
CREATE INDEX IF NOT EXISTS idx_usuarios_rol_activo ON usuarios(rol, activo);
CREATE INDEX IF NOT EXISTS idx_usuarios_centro_activo ON usuarios(centro_id, activo);

-- ========== PASO 0.5: Crear usuario admin si no existe ==========
-- Esto es necesario para el deploy inicial en Render
INSERT INTO usuarios (
    password, last_login, is_superuser, username, first_name, last_name, 
    email, is_staff, is_active, date_joined, 
    rol, centro_id, adscripcion, activo,
    perm_dashboard, perm_productos, perm_lotes, perm_requisiciones,
    perm_centros, perm_usuarios, perm_reportes, perm_trazabilidad,
    perm_auditoria, perm_notificaciones, perm_movimientos
)
SELECT 
    'pbkdf2_sha256$870000$placeholder$placeholder=', -- Password temporal (se cambiará en el build)
    NULL, TRUE, 'admin', 'Administrador', 'Sistema',
    'admin@farmacia.gob.mx', TRUE, TRUE, NOW(),
    'admin_sistema', NULL, '', TRUE,
    TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE
WHERE NOT EXISTS (SELECT 1 FROM usuarios WHERE username = 'admin');

-- ========== PASO 1: Eliminar TODAS las migraciones existentes ==========
DELETE FROM django_migrations;

-- ========== PASO 2: Insertar TODAS las migraciones en orden correcto ==========

-- Contenttypes (PRIMERO - otros dependen de esto)
INSERT INTO django_migrations (app, name, applied) VALUES
    ('contenttypes', '0001_initial', NOW()),
    ('contenttypes', '0002_remove_content_type_name', NOW());

-- Auth
INSERT INTO django_migrations (app, name, applied) VALUES
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
    ('auth', '0012_alter_user_first_name_max_length', NOW());

-- Admin
INSERT INTO django_migrations (app, name, applied) VALUES
    ('admin', '0001_initial', NOW()),
    ('admin', '0002_logentry_remove_auto_add', NOW()),
    ('admin', '0003_logentry_add_action_flag_choices', NOW());

-- Sessions
INSERT INTO django_migrations (app, name, applied) VALUES
    ('sessions', '0001_initial', NOW());

-- Token Blacklist (nombres CORRECTOS)
INSERT INTO django_migrations (app, name, applied) VALUES
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
    ('token_blacklist', '0013_alter_blacklistedtoken_options_and_more', NOW());

-- Core (nombres CORRECTOS y en ORDEN)
INSERT INTO django_migrations (app, name, applied) VALUES
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
    ('core', '0021_optimize_db_structure', NOW());

-- Inventario
INSERT INTO django_migrations (app, name, applied) VALUES
    ('inventario', '0001_initial', NOW()),
    ('inventario', '0002_remove_requisicion_centro_alter_lote_unique_together_and_more', NOW());

-- ========== PASO 3: Verificar ==========
SELECT app, name FROM django_migrations ORDER BY app, id;
