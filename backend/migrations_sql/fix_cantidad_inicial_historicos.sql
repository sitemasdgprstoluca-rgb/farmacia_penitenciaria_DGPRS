-- ============================================================================
-- ISS-MIG-001: Migración para llenar cantidad_inicial en registros históricos
-- ============================================================================
-- Problema: Lotes creados antes de la implementación del campo cantidad_inicial
-- pueden tener NULL o 0, lo que rompe reportes y cálculos.
--
-- Estrategia:
-- 1. Si cantidad_inicial es NULL → igualar a cantidad_actual (snapshot actual)
-- 2. Si cantidad_inicial es 0 y cantidad_actual > 0 → igualar a cantidad_actual
-- 3. Registrar los cambios en auditoria_logs para trazabilidad
--
-- EJECUTAR EN UNA TRANSACCIÓN
-- ============================================================================

BEGIN;

-- Paso 1: Identificar registros afectados (solo diagnóstico, no modifica)
SELECT 
    id, 
    numero_lote, 
    cantidad_inicial, 
    cantidad_actual,
    cantidad_contrato,
    created_at
FROM lotes 
WHERE cantidad_inicial IS NULL 
   OR (cantidad_inicial = 0 AND cantidad_actual > 0);

-- Paso 2: Actualizar cantidad_inicial con snapshot de cantidad_actual
-- Para lotes donde cantidad_inicial es NULL
UPDATE lotes 
SET cantidad_inicial = cantidad_actual,
    updated_at = NOW()
WHERE cantidad_inicial IS NULL;

-- Paso 3: Para lotes donde cantidad_inicial = 0 pero tienen stock
-- (significa que se crearon sin registrar la primera entrega)
UPDATE lotes 
SET cantidad_inicial = cantidad_actual,
    updated_at = NOW()
WHERE cantidad_inicial = 0 
  AND cantidad_actual > 0;

-- Paso 4: Registrar la migración en auditoría
INSERT INTO auditoria_logs (accion, modelo, objeto_id, datos_nuevos, detalles, timestamp)
SELECT 
    'migracion_cantidad_inicial',
    'Lote',
    id::text,
    jsonb_build_object(
        'cantidad_inicial_original', NULL,
        'cantidad_inicial_migrada', cantidad_actual
    ),
    jsonb_build_object(
        'motivo', 'Migración ISS-MIG-001: llenar cantidad_inicial en registros históricos',
        'numero_lote', numero_lote
    ),
    NOW()
FROM lotes 
WHERE cantidad_inicial = cantidad_actual 
  AND updated_at >= NOW() - INTERVAL '1 minute';

COMMIT;

-- Verificación post-migración
SELECT 
    COUNT(*) as total_lotes,
    COUNT(CASE WHEN cantidad_inicial IS NULL THEN 1 END) as sin_cantidad_inicial,
    COUNT(CASE WHEN cantidad_inicial = 0 AND cantidad_actual > 0 THEN 1 END) as cantidad_inicial_cero_con_stock,
    COUNT(CASE WHEN cantidad_inicial > 0 THEN 1 END) as con_cantidad_inicial
FROM lotes;
