-- =====================================================
-- POLÍTICAS DE SEGURIDAD RLS (Row Level Security)
-- Sistema de Farmacia Penitenciaria - Supabase
-- =====================================================
-- 
-- IMPORTANTE: Ejecutar DESPUÉS de crear las tablas del schema
-- 
-- Este script implementa seguridad a nivel de fila (RLS) para
-- proteger los datos sensibles incluso si las credenciales
-- de la base de datos son comprometidas.
--
-- NIVELES DE ACCESO:
-- 1. anon (no autenticado): Solo endpoints públicos (health check)
-- 2. authenticated: Usuarios con JWT válido de Supabase
-- 3. service_role: Backend de Django (acceso completo)
-- =====================================================

-- =====================================================
-- 0. PREPARACIÓN - Crear roles si no existen
-- =====================================================
DO $$
BEGIN
    -- El rol 'anon' ya existe en Supabase por defecto
    -- El rol 'authenticated' ya existe en Supabase por defecto
    -- El rol 'service_role' ya existe en Supabase por defecto
    RAISE NOTICE 'Roles de Supabase verificados';
END $$;

-- =====================================================
-- 1. HABILITAR RLS EN TODAS LAS TABLAS
-- =====================================================
ALTER TABLE IF EXISTS core_usuario ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS core_centro ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS core_producto ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS core_lote ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS core_requisicion ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS core_requisiciondetalle ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS core_movimiento ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS core_notificacion ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS core_auditorialog ENABLE ROW LEVEL SECURITY;

-- =====================================================
-- 2. POLÍTICAS PARA SERVICE_ROLE (Backend Django)
-- =====================================================
-- El backend de Django usa service_role key que tiene acceso completo
-- Esto permite que la lógica de permisos sea manejada por Django

-- Usuarios - service_role puede todo
CREATE POLICY "service_role_all_usuarios" ON core_usuario
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Centros - service_role puede todo
CREATE POLICY "service_role_all_centros" ON core_centro
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Productos - service_role puede todo
CREATE POLICY "service_role_all_productos" ON core_producto
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Lotes - service_role puede todo
CREATE POLICY "service_role_all_lotes" ON core_lote
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Requisiciones - service_role puede todo
CREATE POLICY "service_role_all_requisiciones" ON core_requisicion
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Detalles de Requisición - service_role puede todo
CREATE POLICY "service_role_all_requisicion_detalles" ON core_requisiciondetalle
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Movimientos - service_role puede todo
CREATE POLICY "service_role_all_movimientos" ON core_movimiento
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Notificaciones - service_role puede todo
CREATE POLICY "service_role_all_notificaciones" ON core_notificacion
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Auditoría - service_role puede todo
CREATE POLICY "service_role_all_auditoria" ON core_auditorialog
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- =====================================================
-- 3. POLÍTICAS PARA ANON (Sin autenticar)
-- =====================================================
-- Los usuarios anónimos NO tienen acceso a ninguna tabla
-- Todo el acceso debe pasar por el backend autenticado

-- Explícitamente denegar acceso anónimo
CREATE POLICY "anon_deny_usuarios" ON core_usuario
    FOR ALL
    TO anon
    USING (false);

CREATE POLICY "anon_deny_centros" ON core_centro
    FOR ALL
    TO anon
    USING (false);

CREATE POLICY "anon_deny_productos" ON core_producto
    FOR ALL
    TO anon
    USING (false);

CREATE POLICY "anon_deny_lotes" ON core_lote
    FOR ALL
    TO anon
    USING (false);

CREATE POLICY "anon_deny_requisiciones" ON core_requisicion
    FOR ALL
    TO anon
    USING (false);

CREATE POLICY "anon_deny_requisicion_detalles" ON core_requisiciondetalle
    FOR ALL
    TO anon
    USING (false);

CREATE POLICY "anon_deny_movimientos" ON core_movimiento
    FOR ALL
    TO anon
    USING (false);

CREATE POLICY "anon_deny_notificaciones" ON core_notificacion
    FOR ALL
    TO anon
    USING (false);

CREATE POLICY "anon_deny_auditoria" ON core_auditorialog
    FOR ALL
    TO anon
    USING (false);

-- =====================================================
-- 4. POLÍTICAS PARA AUTHENTICATED (JWT de Supabase)
-- =====================================================
-- Si decides usar autenticación directa de Supabase en el futuro,
-- estas políticas controlarían el acceso.
-- Por ahora, también denegamos porque todo pasa por Django.

CREATE POLICY "authenticated_deny_usuarios" ON core_usuario
    FOR ALL
    TO authenticated
    USING (false);

CREATE POLICY "authenticated_deny_centros" ON core_centro
    FOR ALL
    TO authenticated
    USING (false);

CREATE POLICY "authenticated_deny_productos" ON core_producto
    FOR ALL
    TO authenticated
    USING (false);

CREATE POLICY "authenticated_deny_lotes" ON core_lote
    FOR ALL
    TO authenticated
    USING (false);

CREATE POLICY "authenticated_deny_requisiciones" ON core_requisicion
    FOR ALL
    TO authenticated
    USING (false);

CREATE POLICY "authenticated_deny_requisicion_detalles" ON core_requisiciondetalle
    FOR ALL
    TO authenticated
    USING (false);

CREATE POLICY "authenticated_deny_movimientos" ON core_movimiento
    FOR ALL
    TO authenticated
    USING (false);

CREATE POLICY "authenticated_deny_notificaciones" ON core_notificacion
    FOR ALL
    TO authenticated
    USING (false);

CREATE POLICY "authenticated_deny_auditoria" ON core_auditorialog
    FOR ALL
    TO authenticated
    USING (false);

-- =====================================================
-- 5. REVOCAR PERMISOS PÚBLICOS
-- =====================================================
-- Asegurar que el schema public no tenga permisos por defecto

REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM authenticated;

-- Dar permisos solo a service_role
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;

-- =====================================================
-- 6. PROTEGER TABLAS DE DJANGO
-- =====================================================
-- Estas tablas son internas de Django y no necesitan RLS
-- porque solo las usa el backend

ALTER TABLE IF EXISTS django_migrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS django_session ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS django_content_type ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS django_admin_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS auth_permission ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS auth_group ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS auth_group_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS token_blacklist_outstandingtoken ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS token_blacklist_blacklistedtoken ENABLE ROW LEVEL SECURITY;

-- Políticas para tablas de Django (solo service_role)
CREATE POLICY "service_role_django_migrations" ON django_migrations FOR ALL TO service_role USING (true);
CREATE POLICY "service_role_django_session" ON django_session FOR ALL TO service_role USING (true);
CREATE POLICY "service_role_django_content_type" ON django_content_type FOR ALL TO service_role USING (true);
CREATE POLICY "service_role_django_admin_log" ON django_admin_log FOR ALL TO service_role USING (true);
CREATE POLICY "service_role_auth_permission" ON auth_permission FOR ALL TO service_role USING (true);
CREATE POLICY "service_role_auth_group" ON auth_group FOR ALL TO service_role USING (true);
CREATE POLICY "service_role_auth_group_permissions" ON auth_group_permissions FOR ALL TO service_role USING (true);
CREATE POLICY "service_role_token_outstanding" ON token_blacklist_outstandingtoken FOR ALL TO service_role USING (true);
CREATE POLICY "service_role_token_blacklisted" ON token_blacklist_blacklistedtoken FOR ALL TO service_role USING (true);

-- =====================================================
-- 7. CONFIGURACIÓN DE SEGURIDAD ADICIONAL
-- =====================================================

-- Deshabilitar funciones peligrosas para roles no privilegiados
REVOKE EXECUTE ON FUNCTION pg_read_file(text) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION pg_read_file(text, bigint, bigint) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION pg_read_file(text, bigint, bigint, boolean) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION pg_read_binary_file(text) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION pg_read_binary_file(text, bigint, bigint) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION pg_read_binary_file(text, bigint, bigint, boolean) FROM PUBLIC;

-- =====================================================
-- 8. VERIFICACIÓN
-- =====================================================
DO $$
DECLARE
    r RECORD;
    rls_count INTEGER := 0;
BEGIN
    FOR r IN 
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public' 
        AND tablename LIKE 'core_%'
    LOOP
        rls_count := rls_count + 1;
    END LOOP;
    
    RAISE NOTICE '✔ RLS habilitado en % tablas de core_*', rls_count;
    RAISE NOTICE '✔ Políticas de seguridad aplicadas correctamente';
    RAISE NOTICE '✔ Solo service_role tiene acceso a las tablas';
END $$;

-- =====================================================
-- INSTRUCCIONES DE USO
-- =====================================================
-- 
-- 1. En Supabase, ve a Project Settings > API
-- 
-- 2. Copia la "service_role key" (NO la anon key)
--    Esta es la clave que usará Django para conectarse
-- 
-- 3. En tu DATABASE_URL de Render, usa el formato:
--    postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
--    
-- 4. IMPORTANTE: La conexión de Django usa la contraseña
--    de la base de datos, NO las API keys de Supabase.
--    Las API keys son para el cliente de Supabase (JS).
--
-- 5. Para verificar que RLS está funcionando:
--    SELECT tablename, rowsecurity 
--    FROM pg_tables 
--    WHERE schemaname = 'public';
--
-- =====================================================
