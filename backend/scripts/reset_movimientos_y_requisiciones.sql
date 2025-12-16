-- =====================================================
-- SCRIPT PARA LIMPIAR TABLAS DE DATOS TRANSACCIONALES
-- Conserva: usuarios, centros, lotes, productos, auditoria_logs,
--           auth_group, auth_permission, configuracion_sistema,
--           django_content_type, django_migrations, tema_global, user_profiles
-- Ejecutar en Supabase SQL Editor
-- =====================================================

-- IMPORTANTE: Ejecutar en orden debido a foreign keys

-- =====================================================
-- 1. DESHABILITAR TRIGGERS PROBLEMÁTICOS
-- =====================================================
ALTER TABLE requisiciones DISABLE TRIGGER trigger_validar_transicion_requisicion;
ALTER TABLE requisiciones DISABLE TRIGGER trigger_historial_estado_requisicion;

-- =====================================================
-- 2. LIMPIAR TABLAS EN ORDEN (por dependencias FK)
-- =====================================================

-- 2.1 Tablas hijas de requisiciones
DELETE FROM requisicion_ajustes_cantidad;
DELETE FROM requisicion_historial_estados;
DELETE FROM detalles_requisicion;

-- 2.2 Movimientos (depende de requisiciones, lotes, productos, centros, usuarios)
DELETE FROM movimientos;

-- 2.3 Requisiciones (tabla principal)
DELETE FROM requisiciones;

-- 2.4 Tablas de donaciones
DELETE FROM salidas_donaciones;
DELETE FROM detalle_donaciones;
DELETE FROM donaciones;

-- 2.5 Hojas de recolección
DELETE FROM detalle_hojas_recoleccion;
DELETE FROM hojas_recoleccion;

-- 2.6 Documentos de lotes
DELETE FROM lote_documentos;

-- 2.7 LOTES EN CENTROS (eliminar los que fueron creados por requisiciones)
-- Los lotes de Farmacia Central tienen centro_id = NULL y se conservan
DELETE FROM lotes WHERE centro_id IS NOT NULL;

-- 2.8 Imágenes de productos
DELETE FROM producto_imagenes;

-- 2.8 Notificaciones
DELETE FROM notificaciones;

-- 2.9 Importación logs
DELETE FROM importacion_logs;

-- 2.10 Django admin log
DELETE FROM django_admin_log;

-- 2.11 Django sessions
DELETE FROM django_session;

-- 2.12 Token blacklist (JWT)
DELETE FROM token_blacklist_blacklistedtoken;
DELETE FROM token_blacklist_outstandingtoken;

-- 2.13 Auth group permissions (M2M)
DELETE FROM auth_group_permissions;

-- 2.14 Usuarios groups y permissions (M2M)
DELETE FROM usuarios_groups;
DELETE FROM usuarios_user_permissions;

-- =====================================================
-- 3. RE-HABILITAR TRIGGERS
-- =====================================================
ALTER TABLE requisiciones ENABLE TRIGGER trigger_validar_transicion_requisicion;
ALTER TABLE requisiciones ENABLE TRIGGER trigger_historial_estado_requisicion;

-- =====================================================
-- 4. RESETEAR SECUENCIAS (opcional, para IDs desde 1)
-- =====================================================
-- Descomentar si deseas que los nuevos IDs empiecen desde 1

-- ALTER SEQUENCE requisiciones_id_seq RESTART WITH 1;
-- ALTER SEQUENCE detalles_requisicion_id_seq RESTART WITH 1;
-- ALTER SEQUENCE movimientos_id_seq RESTART WITH 1;
-- ALTER SEQUENCE donaciones_id_seq RESTART WITH 1;
-- ALTER SEQUENCE detalle_donaciones_id_seq RESTART WITH 1;
-- ALTER SEQUENCE hojas_recoleccion_id_seq RESTART WITH 1;
-- ALTER SEQUENCE detalle_hojas_recoleccion_id_seq RESTART WITH 1;
-- ALTER SEQUENCE notificaciones_id_seq RESTART WITH 1;

-- =====================================================
-- 5. VERIFICACIÓN - Tablas que deben quedar CON datos
-- =====================================================
SELECT 'usuarios' as tabla, COUNT(*) as registros FROM usuarios
UNION ALL SELECT 'centros', COUNT(*) FROM centros
UNION ALL SELECT 'productos', COUNT(*) FROM productos
UNION ALL SELECT 'lotes', COUNT(*) FROM lotes
UNION ALL SELECT 'auditoria_logs', COUNT(*) FROM auditoria_logs
UNION ALL SELECT 'auth_group', COUNT(*) FROM auth_group
UNION ALL SELECT 'auth_permission', COUNT(*) FROM auth_permission
UNION ALL SELECT 'configuracion_sistema', COUNT(*) FROM configuracion_sistema
UNION ALL SELECT 'django_content_type', COUNT(*) FROM django_content_type
UNION ALL SELECT 'django_migrations', COUNT(*) FROM django_migrations
UNION ALL SELECT 'tema_global', COUNT(*) FROM tema_global
UNION ALL SELECT 'user_profiles', COUNT(*) FROM user_profiles;

-- =====================================================
-- 6. VERIFICACIÓN - Tablas que deben quedar VACÍAS
-- =====================================================
SELECT 'requisiciones' as tabla, COUNT(*) as registros FROM requisiciones
UNION ALL SELECT 'detalles_requisicion', COUNT(*) FROM detalles_requisicion
UNION ALL SELECT 'movimientos', COUNT(*) FROM movimientos
UNION ALL SELECT 'donaciones', COUNT(*) FROM donaciones
UNION ALL SELECT 'hojas_recoleccion', COUNT(*) FROM hojas_recoleccion
UNION ALL SELECT 'notificaciones', COUNT(*) FROM notificaciones;
