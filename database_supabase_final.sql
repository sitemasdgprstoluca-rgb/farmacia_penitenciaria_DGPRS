-- ==========================================================================
-- FARMACIA PENITENCIARIA - CORRECCIÓN DE MIGRACIONES PARA SUPABASE
-- Ejecutar en Supabase SQL Editor para corregir la tabla django_migrations
-- ==========================================================================

-- Eliminar las entradas incorrectas de token_blacklist
DELETE FROM django_migrations WHERE app = 'token_blacklist';

-- Insertar las migraciones correctas de token_blacklist
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

-- Verificar que todas las migraciones estén registradas
SELECT app, name FROM django_migrations WHERE app = 'token_blacklist' ORDER BY id;
