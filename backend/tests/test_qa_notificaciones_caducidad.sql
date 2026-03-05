-- ══════════════════════════════════════════════════════════════════════════════
-- SCRIPT DE VERIFICACIÓN QA - Sistema de Notificaciones por Caducidad
-- ══════════════════════════════════════════════════════════════════════════════
-- Fecha: 2025-01-XX
-- Propósito: Crear datos de prueba y verificar notificaciones
-- IMPORTANTE: Ejecutar en ambiente de DESARROLLO/QA, NO en producción
-- ══════════════════════════════════════════════════════════════════════════════

\echo '═══════════════════════════════════════════════════════════════════════════';
\echo 'SETUP: Creando datos de prueba';
\echo '═══════════════════════════════════════════════════════════════════════════';

-- ────────────────────────────────────────────────────────────────────────────
-- 1. CREAR CENTROS DE PRUEBA
-- ────────────────────────────────────────────────────────────────────────────
INSERT INTO centros (clave, nombre, activo, created_at, updated_at)
VALUES 
    ('TEST-C01', 'Centro Pruebas Norte', true, NOW(), NOW()),
    ('TEST-C02', 'Centro Pruebas Sur', true, NOW(), NOW()),
    ('TEST-C99', 'Centro Sin Usuarios', true, NOW(), NOW())
ON CONFLICT (clave) DO UPDATE 
SET activo = true, updated_at = NOW();

\echo 'Centros de prueba creados: TEST-C01, TEST-C02, TEST-C99';

-- ────────────────────────────────────────────────────────────────────────────
-- 2. CREAR USUARIOS DE PRUEBA
-- ────────────────────────────────────────────────────────────────────────────
INSERT INTO usuarios (username, password, rol, centro_id, is_active, created_at, updated_at)
VALUES 
    -- Usuario farmacia (ve lotes de Farmacia)
    ('qa_farmacia', 'pbkdf2_sha256$260000$test', 'farmacia', NULL, true, NOW(), NOW()),
    
    -- Usuarios por centro (ven solo su centro)
    ('qa_centro_norte', 'pbkdf2_sha256$260000$test', 'capturista', 
     (SELECT id FROM centros WHERE clave='TEST-C01'), true, NOW(), NOW()),
    
    ('qa_centro_sur', 'pbkdf2_sha256$260000$test', 'capturista', 
     (SELECT id FROM centros WHERE clave='TEST-C02'), true, NOW(), NOW()),
    
    -- Usuario inactivo (NO debe recibir notificaciones)
    ('qa_centro_inactivo', 'pbkdf2_sha256$260000$test', 'capturista', 
     (SELECT id FROM centros WHERE clave='TEST-C01'), false, NOW(), NOW())
ON CONFLICT (username) DO UPDATE 
SET is_active = EXCLUDED.is_active, updated_at = NOW();

\echo 'Usuarios de prueba creados: qa_farmacia, qa_centro_norte, qa_centro_sur';

-- ────────────────────────────────────────────────────────────────────────────
-- 3. CREAR PRODUCTO DE PRUEBA (si no existe)
-- ────────────────────────────────────────────────────────────────────────────
INSERT INTO productos (
    clave, nombre, descripcion, activo, stock_minimo, 
    created_at, updated_at
)
VALUES (
    'QA-TEST-001', 
    'Producto QA Test', 
    'Producto para pruebas de notificaciones', 
    true, 
    100,  -- stock mínimo para testing stock bajo
    NOW(), 
    NOW()
)
ON CONFLICT (clave) DO UPDATE 
SET activo = true, updated_at = NOW()
RETURNING id;

\echo 'Producto de prueba creado: QA-TEST-001';

-- ────────────────────────────────────────────────────────────────────────────
-- 4. CREAR LOTES DE FARMACIA (Tabla: lotes)
-- ────────────────────────────────────────────────────────────────────────────
DELETE FROM lotes WHERE numero_lote LIKE 'QA-F-%';

INSERT INTO lotes (
    producto_id, numero_lote, fecha_caducidad, 
    cantidad_inicial, cantidad_actual, activo, 
    created_at, updated_at
)
SELECT 
    p.id,
    'QA-F-CRITICO',
    CURRENT_DATE + INTERVAL '10 days',  -- Crítico: 10 días (< 15)
    100,
    50,
    true,
    NOW(),
    NOW()
FROM productos p WHERE p.clave = 'QA-TEST-001'
UNION ALL
SELECT 
    p.id,
    'QA-F-PROXIMO',
    CURRENT_DATE + INTERVAL '25 days',  -- Próximo: 25 días (entre 15-30)
    200,
    75,
    true,
    NOW(),
    NOW()
FROM productos p WHERE p.clave = 'QA-TEST-001'
UNION ALL
SELECT 
    p.id,
    'QA-F-CADUCADO',
    CURRENT_DATE - INTERVAL '5 days',  -- Caducado: hace 5 días
    150,
    20,  -- Con stock (debe alertar)
    true,
    NOW(),
    NOW()
FROM productos p WHERE p.clave = 'QA-TEST-001'
UNION ALL
SELECT 
    p.id,
    'QA-F-AGOTADO',
    CURRENT_DATE - INTERVAL '10 days',  -- Caducado pero SIN stock
    100,
    0,  -- Sin stock (NO debe alertar)
    true,
    NOW(),
    NOW()
FROM productos p WHERE p.clave = 'QA-TEST-001'
UNION ALL
SELECT 
    p.id,
    'QA-F-NORMAL',
    CURRENT_DATE + INTERVAL '90 days',  -- Normal: 90 días
    500,
    300,
    true,
    NOW(),
    NOW()
FROM productos p WHERE p.clave = 'QA-TEST-001';

\echo 'Lotes de Farmacia creados:';
\echo '  - QA-F-CRITICO (10 días, 50 unidades) → Debe generar ALERTA CRÍTICA';
\echo '  - QA-F-PROXIMO (25 días, 75 unidades) → Debe generar ALERTA PRÓXIMA';
\echo '  - QA-F-CADUCADO (vencido, 20 unidades) → Debe generar ALERTA CADUCADO';
\echo '  - QA-F-AGOTADO (vencido, 0 unidades) → NO debe alertar (sin stock)';
\echo '  - QA-F-NORMAL (90 días, 300 unidades) → NO debe alertar';

-- ────────────────────────────────────────────────────────────────────────────
-- 5. CREAR LOTES DE CENTROS (Tabla: inventario_caja_chica)
-- ────────────────────────────────────────────────────────────────────────────
DELETE FROM inventario_caja_chica WHERE numero_lote LIKE 'QA-CC-%';

INSERT INTO inventario_caja_chica (
    centro_id, producto_id, descripcion_producto, numero_lote, 
    fecha_caducidad, cantidad_inicial, cantidad_actual, activo, 
    created_at, updated_at
)
SELECT 
    (SELECT id FROM centros WHERE clave='TEST-C01'),
    p.id,
    'Paracetamol 500mg',
    'QA-CC-N-CRITICO',
    CURRENT_DATE + INTERVAL '8 days',  -- Crítico: 8 días
    100,
    40,
    true,
    NOW(),
    NOW()
FROM productos p WHERE p.clave = 'QA-TEST-001'
UNION ALL
SELECT 
    (SELECT id FROM centros WHERE clave='TEST-C01'),
    p.id,
    'Ibuprofeno 400mg',
    'QA-CC-N-PROXIMO',
    CURRENT_DATE + INTERVAL '20 days',  -- Próximo: 20 días
    50,
    30,
    true,
    NOW(),
    NOW()
FROM productos p WHERE p.clave = 'QA-TEST-001'
UNION ALL
SELECT 
    (SELECT id FROM centros WHERE clave='TEST-C02'),
    p.id,
    'Amoxicilina 500mg',
    'QA-CC-S-CRITICO',
    CURRENT_DATE + INTERVAL '12 days',  -- Crítico: 12 días
    80,
    25,
    true,
    NOW(),
    NOW()
FROM productos p WHERE p.clave = 'QA-TEST-001'
UNION ALL
SELECT 
    (SELECT id FROM centros WHERE clave='TEST-C02'),
    p.id,
    'Omeprazol 20mg',
    'QA-CC-S-CADUCADO',
    CURRENT_DATE - INTERVAL '3 days',  -- Caducado: hace 3 días
    60,
    15,
    true,
    NOW(),
    NOW()
FROM productos p WHERE p.clave = 'QA-TEST-001'
UNION ALL
SELECT 
    (SELECT id FROM centros WHERE clave='TEST-C99'),
    p.id,
    'Producto Sin Usuarios',
    'QA-CC-EMPTY-CENTRO',
    CURRENT_DATE + INTERVAL '5 days',  -- Crítico pero sin usuarios
    30,
    10,
    true,
    NOW(),
    NOW()
FROM productos p WHERE p.clave = 'QA-TEST-001';

\echo 'Lotes de Centros creados:';
\echo '  Centro Norte (TEST-C01):';
\echo '    - QA-CC-N-CRITICO (8 días, 40 u) → qa_centro_norte';
\echo '    - QA-CC-N-PROXIMO (20 días, 30 u) → qa_centro_norte';
\echo '  Centro Sur (TEST-C02):';
\echo '    - QA-CC-S-CRITICO (12 días, 25 u) → qa_centro_sur';
\echo '    - QA-CC-S-CADUCADO (vencido, 15 u) → qa_centro_sur';
\echo '  Centro Sin Usuarios (TEST-C99):';
\echo '    - QA-CC-EMPTY-CENTRO (5 días) → NO debe notificar (sin usuarios)';

-- ════════════════════════════════════════════════════════════════════════════
\echo '';
\echo '═══════════════════════════════════════════════════════════════════════════';
\echo 'SETUP COMPLETO - Ahora ejecuta el comando:';
\echo '';
\echo '  python manage.py generar_alertas_inventario --dry-run';
\echo '';
\echo 'Luego ejecuta las queries de VERIFICACIÓN al final de este script.';
\echo '═══════════════════════════════════════════════════════════════════════════';
\echo '';

-- ════════════════════════════════════════════════════════════════════════════
-- QUERIES DE VERIFICACIÓN (Ejecutar DESPUÉS del comando)
-- ════════════════════════════════════════════════════════════════════════════

\echo '═══════════════════════════════════════════════════════════════════════════';
\echo 'VERIFICACIÓN: Lotes que DEBEN generar alertas';
\echo '═══════════════════════════════════════════════════════════════════════════';

-- Vista de lotes críticos de Farmacia
SELECT 
    '🏥 FARMACIA - CRÍTICOS' as seccion,
    l.numero_lote,
    p.clave as producto,
    l.fecha_caducidad,
    (l.fecha_caducidad - CURRENT_DATE) as dias_restantes,
    l.cantidad_actual,
    CASE 
        WHEN (l.fecha_caducidad - CURRENT_DATE) <= 15 THEN '✅ DEBE ALERTAR'
        ELSE '❌ NO debe alertar'
    END as esperado
FROM lotes l
JOIN productos p ON l.producto_id = p.id
WHERE l.numero_lote LIKE 'QA-F-%'
  AND l.cantidad_actual > 0
  AND l.fecha_caducidad >= CURRENT_DATE
  AND l.fecha_caducidad <= CURRENT_DATE + INTERVAL '15 days'
ORDER BY l.fecha_caducidad;

-- Vista de lotes próximos de Farmacia
SELECT 
    '🏥 FARMACIA - PRÓXIMOS' as seccion,
    l.numero_lote,
    p.clave as producto,
    l.fecha_caducidad,
    (l.fecha_caducidad - CURRENT_DATE) as dias_restantes,
    l.cantidad_actual,
    CASE 
        WHEN (l.fecha_caducidad - CURRENT_DATE) BETWEEN 16 AND 30 THEN '✅ DEBE ALERTAR'
        ELSE '❌ NO debe alertar'
    END as esperado
FROM lotes l
JOIN productos p ON l.producto_id = p.id
WHERE l.numero_lote LIKE 'QA-F-%'
  AND l.cantidad_actual > 0
  AND l.fecha_caducidad > CURRENT_DATE + INTERVAL '15 days'
  AND l.fecha_caducidad <= CURRENT_DATE + INTERVAL '30 days'
ORDER BY l.fecha_caducidad;

-- Vista de lotes caducados de Farmacia
SELECT 
    '🏥 FARMACIA - CADUCADOS' as seccion,
    l.numero_lote,
    p.clave as producto,
    l.fecha_caducidad,
    (CURRENT_DATE - l.fecha_caducidad) as dias_pasados,
    l.cantidad_actual,
    CASE 
        WHEN l.cantidad_actual > 0 THEN '✅ DEBE ALERTAR'
        ELSE '❌ NO debe alertar (sin stock)'
    END as esperado
FROM lotes l
JOIN productos p ON l.producto_id = p.id
WHERE l.numero_lote LIKE 'QA-F-%'
  AND l.fecha_caducidad < CURRENT_DATE
ORDER BY l.fecha_caducidad;

-- Vista de lotes de Centros
SELECT 
    '🏥 CENTROS' as seccion,
    c.nombre as centro,
    icc.numero_lote,
    icc.descripcion_producto,
    icc.fecha_caducidad,
    CASE 
        WHEN icc.fecha_caducidad < CURRENT_DATE THEN 
            CONCAT('VENCIDO (hace ', (CURRENT_DATE - icc.fecha_caducidad), ' días)')
        ELSE 
            CONCAT((icc.fecha_caducidad - CURRENT_DATE), ' días')
    END as dias,
    icc.cantidad_actual,
    CASE 
        WHEN icc.fecha_caducidad < CURRENT_DATE THEN '🚫 CADUCADO'
        WHEN (icc.fecha_caducidad - CURRENT_DATE) <= 15 THEN '🚨 CRÍTICO'
        WHEN (icc.fecha_caducidad - CURRENT_DATE) <= 30 THEN '⚠️ PRÓXIMO'
        ELSE '✅ NORMAL'
    END as nivel_alerta,
    u.username as destinatario
FROM inventario_caja_chica icc
JOIN centros c ON icc.centro_id = c.id
LEFT JOIN usuarios u ON u.centro_id = c.id AND u.is_active = true
WHERE icc.numero_lote LIKE 'QA-CC-%'
  AND icc.cantidad_actual > 0
ORDER BY c.nombre, icc.fecha_caducidad;

\echo '';
\echo '═══════════════════════════════════════════════════════════════════════════';
\echo 'VERIFICACIÓN: Notificaciones creadas (ejecutar después del comando REAL)';
\echo '═══════════════════════════════════════════════════════════════════════════';

-- Notificaciones de Farmacia
SELECT 
    '🏥 NOTIF FARMACIA' as tipo,
    n.created_at::date as fecha,
    n.tipo as nivel,
    n.titulo,
    u.username as destinatario,
    u.rol,
    n.datos::jsonb->>'tipo_alerta' as tipo_alerta,
    n.datos::jsonb->>'cantidad_lotes' as cantidad
FROM notificaciones n
JOIN usuarios u ON n.usuario_id = u.id
WHERE n.datos::jsonb->>'tipo_alerta' IN (
    'caducidad_critica', 
    'caducidad_proxima', 
    'caducados'
)
  AND n.created_at::date >= CURRENT_DATE
ORDER BY n.created_at DESC;

-- Notificaciones de Centros
SELECT 
    '🏥 NOTIF CENTROS' as tipo,
    n.created_at::date as fecha,
    n.tipo as nivel,
    n.datos::jsonb->>'centro_nombre' as centro,
    u.username as destinatario,
    n.titulo,
    n.datos::jsonb->>'tipo_alerta' as tipo_alerta,
    n.datos::jsonb->>'cantidad_lotes' as cantidad
FROM notificaciones n
JOIN usuarios u ON n.usuario_id = u.id
WHERE n.datos::jsonb->>'tipo_alerta' IN (
    'caducidad_critica_centro', 
    'caducidad_proxima_centro', 
    'caducados_centro'
)
  AND n.created_at::date >= CURRENT_DATE
ORDER BY n.datos::jsonb->>'centro_nombre', n.created_at DESC;

\echo '';
\echo '═══════════════════════════════════════════════════════════════════════════';
\echo 'VERIFICACIÓN: Aislamiento por Centro';
\echo '═══════════════════════════════════════════════════════════════════════════';

-- Verificar que qa_centro_norte NO ve notificaciones de Centro Sur
SELECT 
    'AISLAMIENTO: qa_centro_norte' as test,
    COUNT(*) as notificaciones_centro_sur,
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ PASS: No ve centro ajeno'
        ELSE '❌ FAIL: Ve notificaciones de otro centro'
    END as resultado
FROM notificaciones n
JOIN usuarios u ON n.usuario_id = u.id
WHERE u.username = 'qa_centro_norte'
  AND n.datos::jsonb->>'centro_nombre' LIKE '%Sur%'
  AND n.created_at::date >= CURRENT_DATE;

-- Verificar que qa_centro_sur NO ve notificaciones de Centro Norte
SELECT 
    'AISLAMIENTO: qa_centro_sur' as test,
    COUNT(*) as notificaciones_centro_norte,
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ PASS: No ve centro ajeno'
        ELSE '❌ FAIL: Ve notificaciones de otro centro'
    END as resultado
FROM notificaciones n
JOIN usuarios u ON n.usuario_id = u.id
WHERE u.username = 'qa_centro_sur'
  AND n.datos::jsonb->>'centro_nombre' LIKE '%Norte%'
  AND n.created_at::date >= CURRENT_DATE;

\echo '';
\echo '═══════════════════════════════════════════════════════════════════════════';
\echo 'VERIFICACIÓN: Prevención de Duplicados';
\echo '═══════════════════════════════════════════════════════════════════════════';

-- Contar notificaciones por usuario en últimas 24h
SELECT 
    'DUPLICADOS' as test,
    u.username,
    n.datos::jsonb->>'tipo_alerta' as tipo_alerta,
    COUNT(*) as cantidad_notificaciones,
    CASE 
        WHEN COUNT(*) = 1 THEN '✅ PASS: Sin duplicados'
        WHEN COUNT(*) > 1 THEN '⚠️ POSIBLE DUPLICADO (verificar timestamps)'
        ELSE '✅ OK'
    END as resultado
FROM notificaciones n
JOIN usuarios u ON n.usuario_id = u.id
WHERE n.created_at >= NOW() - INTERVAL '24 hours'
  AND n.datos::jsonb->>'tipo_alerta' LIKE '%caducidad%'
GROUP BY u.username, n.datos::jsonb->>'tipo_alerta'
ORDER BY cantidad_notificaciones DESC;

\echo '';
\echo '═══════════════════════════════════════════════════════════════════════════';
\echo 'VERIFICACIÓN: Usuario Inactivo (NO debe tener notificaciones)';
\echo '═══════════════════════════════════════════════════════════════════════════';

SELECT 
    'USUARIO INACTIVO' as test,
    COUNT(*) as notificaciones,
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ PASS: Usuario inactivo no recibe notificaciones'
        ELSE '❌ FAIL: Usuario inactivo recibió notificaciones'
    END as resultado
FROM notificaciones n
JOIN usuarios u ON n.usuario_id = u.id
WHERE u.username = 'qa_centro_inactivo'
  AND u.is_active = false
  AND n.created_at::date >= CURRENT_DATE;

\echo '';
\echo '═══════════════════════════════════════════════════════════════════════════';
\echo 'VERIFICACIÓN: Centro Sin Usuarios (NO debe generar notificaciones)';
\echo '═══════════════════════════════════════════════════════════════════════════';

-- Verificar que Centro TEST-C99 tiene lotes pero NO tiene notificaciones
SELECT 
    'CENTRO SIN USUARIOS' as test,
    c.nombre as centro,
    COUNT(DISTINCT icc.id) as lotes_criticos,
    COUNT(DISTINCT u.id) as usuarios_activos,
    COUNT(DISTINCT n.id) as notificaciones_generadas,
    CASE 
        WHEN COUNT(DISTINCT n.id) = 0 THEN '✅ PASS: No generó notificaciones sin usuarios'
        ELSE '❌ FAIL: Generó notificaciones sin destinatarios'
    END as resultado
FROM centros c
LEFT JOIN inventario_caja_chica icc ON icc.centro_id = c.id 
    AND icc.numero_lote LIKE 'QA-CC-%'
    AND icc.cantidad_actual > 0
LEFT JOIN usuarios u ON u.centro_id = c.id AND u.is_active = true
LEFT JOIN notificaciones n ON n.usuario_id = u.id 
    AND n.created_at::date >= CURRENT_DATE
    AND n.datos::jsonb->>'tipo_alerta' LIKE '%_centro'
WHERE c.clave = 'TEST-C99'
GROUP BY c.nombre;

\echo '';
\echo '═══════════════════════════════════════════════════════════════════════════';
\echo 'RESUMEN DE CASOS DE PRUEBA';
\echo '═══════════════════════════════════════════════════════════════════════════';

-- Matriz resumen
WITH esperados AS (
    SELECT 
        'Farmacia - Lotes críticos' as caso,
        1 as debe_alertar,
        (SELECT COUNT(*) FROM lotes l 
         WHERE l.numero_lote IN ('QA-F-CRITICO')
           AND l.cantidad_actual > 0
           AND l.fecha_caducidad BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '15 days'
        ) as lotes_encontrados
    UNION ALL
    SELECT 
        'Farmacia - Lotes próximos',
        1,
        (SELECT COUNT(*) FROM lotes l 
         WHERE l.numero_lote IN ('QA-F-PROXIMO')
           AND l.cantidad_actual > 0
           AND l.fecha_caducidad BETWEEN CURRENT_DATE + INTERVAL '15 days' AND CURRENT_DATE + INTERVAL '30 days'
        )
    UNION ALL
    SELECT 
        'Farmacia - Lotes caducados',
        1,
        (SELECT COUNT(*) FROM lotes l 
         WHERE l.numero_lote IN ('QA-F-CADUCADO')
           AND l.cantidad_actual > 0
           AND l.fecha_caducidad < CURRENT_DATE
        )
    UNION ALL
    SELECT 
        'Centro Norte - Críticos',
        2,  -- Dos lotes: uno crítico, uno próximo
        (SELECT COUNT(*) FROM inventario_caja_chica icc 
         WHERE icc.numero_lote IN ('QA-CC-N-CRITICO', 'QA-CC-N-PROXIMO')
           AND icc.cantidad_actual > 0
        )
    UNION ALL
    SELECT 
        'Centro Sur - Críticos',
        2,  -- Dos lotes: uno crítico, uno caducado
        (SELECT COUNT(*) FROM inventario_caja_chica icc 
         WHERE icc.numero_lote IN ('QA-CC-S-CRITICO', 'QA-CC-S-CADUCADO')
           AND icc.cantidad_actual > 0
        )
)
SELECT 
    caso,
    debe_alertar as lotes_esperados,
    lotes_encontrados,
    CASE 
        WHEN lotes_encontrados = debe_alertar THEN '✅ PASS'
        ELSE '❌ FAIL'
    END as status
FROM esperados
ORDER BY caso;

\echo '';
\echo '═══════════════════════════════════════════════════════════════════════════';
\echo 'LIMPIEZA: Ejecuta estos comandos para eliminar datos de prueba';
\echo '═══════════════════════════════════════════════════════════════════════════';
\echo '';
\echo 'DELETE FROM lotes WHERE numero_lote LIKE ''QA-F-%'';';
\echo 'DELETE FROM inventario_caja_chica WHERE numero_lote LIKE ''QA-CC-%'';';
\echo 'DELETE FROM notificaciones WHERE datos::jsonb->>''lotes'' LIKE ''%QA-%'';';
\echo 'DELETE FROM productos WHERE clave = ''QA-TEST-001'';';
\echo 'DELETE FROM usuarios WHERE username LIKE ''qa_%'';';
\echo 'DELETE FROM centros WHERE clave LIKE ''TEST-%'';';
\echo '';
