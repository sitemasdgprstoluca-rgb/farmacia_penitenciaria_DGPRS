-- ==========================================================================
-- SQL de Corrección: Asignar centro_destino a movimientos de salida
-- desde Farmacia Central que tienen requisición asociada
-- ==========================================================================
-- Fecha: 2026-01-13
-- Descripción: Corrige los movimientos de tipo 'salida' que fueron creados
-- desde Farmacia Central (centro_origen IS NULL) y que pertenecen a una
-- requisición, pero que no tienen centro_destino asignado.
--
-- El centro_destino debe ser el centro_destino de la requisición asociada.
-- ==========================================================================

-- ============================================
-- 1. CONSULTA DE VERIFICACIÓN (ANTES)
-- ============================================
-- Ver cuántos movimientos necesitan corrección

SELECT 
    'ANTES DE CORRECCIÓN' as estado,
    COUNT(*) as total_movimientos_afectados
FROM movimientos m
WHERE m.tipo = 'salida'
  AND m.centro_origen_id IS NULL
  AND m.centro_destino_id IS NULL
  AND m.requisicion_id IS NOT NULL;

-- Detalle de los movimientos a corregir con su requisición
SELECT 
    m.id as movimiento_id,
    m.tipo,
    m.referencia,
    m.fecha,
    m.centro_origen_id,
    m.centro_destino_id,
    m.requisicion_id,
    r.numero as requisicion_numero,
    r.centro_destino_id as requisicion_centro_destino_id,
    c.nombre as centro_destino_nombre
FROM movimientos m
JOIN requisiciones r ON m.requisicion_id = r.id
LEFT JOIN centros c ON r.centro_destino_id = c.id
WHERE m.tipo = 'salida'
  AND m.centro_origen_id IS NULL
  AND m.centro_destino_id IS NULL
  AND m.requisicion_id IS NOT NULL
ORDER BY m.fecha DESC;

-- ============================================
-- 2. UPDATE PRINCIPAL - Corregir movimientos
-- ============================================
-- IMPORTANTE: Esta query actualiza centro_destino_id de los movimientos
-- tipo 'salida' que salen de Farmacia Central (centro_origen IS NULL),
-- tienen una requisición asociada, pero no tienen centro_destino.
--
-- El centro_destino se toma de la requisición asociada.

UPDATE movimientos m
SET centro_destino_id = r.centro_destino_id
FROM requisiciones r
WHERE m.requisicion_id = r.id
  AND m.tipo = 'salida'
  AND m.centro_origen_id IS NULL
  AND m.centro_destino_id IS NULL
  AND r.centro_destino_id IS NOT NULL;

-- ============================================
-- 3. CONSULTA DE VERIFICACIÓN (DESPUÉS)
-- ============================================
-- Verificar que ya no hay movimientos sin centro_destino

SELECT 
    'DESPUÉS DE CORRECCIÓN' as estado,
    COUNT(*) as movimientos_sin_centro_destino
FROM movimientos m
WHERE m.tipo = 'salida'
  AND m.centro_origen_id IS NULL
  AND m.centro_destino_id IS NULL
  AND m.requisicion_id IS NOT NULL;

-- ============================================
-- 4. RESUMEN DE CORRECCIONES POR CENTRO
-- ============================================
-- Ver distribución de movimientos corregidos por centro

SELECT 
    c.nombre as centro,
    COUNT(*) as movimientos_corregidos
FROM movimientos m
JOIN requisiciones r ON m.requisicion_id = r.id
JOIN centros c ON m.centro_destino_id = c.id
WHERE m.tipo = 'salida'
  AND m.centro_origen_id IS NULL
  AND m.centro_destino_id IS NOT NULL
GROUP BY c.nombre
ORDER BY movimientos_corregidos DESC;

-- ============================================
-- 5. VERIFICACIÓN ADICIONAL: Entradas sin centro_destino
-- ============================================
-- Por si también hay entradas que necesiten corrección

UPDATE movimientos m
SET centro_destino_id = r.centro_destino_id
FROM requisiciones r
WHERE m.requisicion_id = r.id
  AND m.tipo = 'entrada'
  AND m.centro_destino_id IS NULL
  AND r.centro_destino_id IS NOT NULL;

-- ============================================
-- 6. REPORTE FINAL
-- ============================================
-- Ver estado final de los movimientos

SELECT 
    m.tipo,
    CASE 
        WHEN m.centro_origen_id IS NULL AND m.centro_destino_id IS NOT NULL 
            THEN 'Salida desde Farmacia Central'
        WHEN m.centro_origen_id IS NOT NULL AND m.centro_destino_id IS NULL 
            THEN 'Salida desde Centro (Dispensación)'
        WHEN m.centro_origen_id IS NULL AND m.centro_destino_id IS NULL 
            THEN 'SIN CENTRO (REVISAR)'
        WHEN m.tipo = 'entrada' AND m.centro_destino_id IS NOT NULL 
            THEN 'Entrada a Centro'
        ELSE 'Otro'
    END as clasificacion,
    COUNT(*) as cantidad
FROM movimientos m
WHERE m.requisicion_id IS NOT NULL
GROUP BY 
    m.tipo,
    CASE 
        WHEN m.centro_origen_id IS NULL AND m.centro_destino_id IS NOT NULL 
            THEN 'Salida desde Farmacia Central'
        WHEN m.centro_origen_id IS NOT NULL AND m.centro_destino_id IS NULL 
            THEN 'Salida desde Centro (Dispensación)'
        WHEN m.centro_origen_id IS NULL AND m.centro_destino_id IS NULL 
            THEN 'SIN CENTRO (REVISAR)'
        WHEN m.tipo = 'entrada' AND m.centro_destino_id IS NOT NULL 
            THEN 'Entrada a Centro'
        ELSE 'Otro'
    END
ORDER BY m.tipo, clasificacion;
