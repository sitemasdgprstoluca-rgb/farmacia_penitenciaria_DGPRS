-- ==========================================================================
-- SQL de Corrección: Separar salidas de Farmacia Central vs Dispensaciones
-- ==========================================================================
-- Fecha: 2026-01-13
-- 
-- SITUACIÓN ACTUAL: Hay salidas sin centro_origen ni centro_destino
-- que deberían dividirse en:
-- - Salidas de Farmacia Central (centro_destino = centro)
-- - Dispensaciones desde Centro (centro_origen = centro)
-- ==========================================================================

-- ============================================
-- 1. DIAGNÓSTICO COMPLETO
-- ============================================

-- Ver TODOS los movimientos con requisición
SELECT 
    m.id,
    m.tipo,
    m.referencia,
    m.producto_id,
    m.lote_id,
    m.centro_origen_id,
    m.centro_destino_id,
    r.centro_destino_id as req_centro_destino
FROM movimientos m
JOIN requisiciones r ON m.requisicion_id = r.id
WHERE m.requisicion_id IS NOT NULL
ORDER BY m.referencia, m.tipo, m.id;

-- Contar estado actual
SELECT 
    tipo,
    CASE 
        WHEN centro_origen_id IS NOT NULL THEN 'tiene centro_origen'
        WHEN centro_destino_id IS NOT NULL THEN 'tiene centro_destino'
        ELSE 'SIN CENTRO'
    END as estado,
    COUNT(*) as cantidad
FROM movimientos
WHERE requisicion_id IS NOT NULL
GROUP BY tipo, 
    CASE 
        WHEN centro_origen_id IS NOT NULL THEN 'tiene centro_origen'
        WHEN centro_destino_id IS NOT NULL THEN 'tiene centro_destino'
        ELSE 'SIN CENTRO'
    END;

-- ============================================
-- 2. CORREGIR ENTRADAS (todas deben tener centro_destino)
-- ============================================

UPDATE movimientos m
SET centro_destino_id = r.centro_destino_id
FROM requisiciones r
WHERE m.requisicion_id = r.id
  AND m.tipo = 'entrada'
  AND m.centro_destino_id IS NULL
  AND r.centro_destino_id IS NOT NULL;

-- ============================================
-- 3. PARA SALIDAS SIN CENTRO - Asignar según ID
-- ============================================
-- La mitad (IDs menores) = Salida Farmacia Central (centro_destino)
-- La mitad (IDs mayores) = Dispensación (centro_origen)

-- Primero ver cuáles son salidas sin centro y calcular la mediana
WITH salidas_sin_centro AS (
    SELECT m.id, m.requisicion_id, r.centro_destino_id as centro_req,
           ROW_NUMBER() OVER (ORDER BY m.id) as rn,
           COUNT(*) OVER () as total
    FROM movimientos m
    JOIN requisiciones r ON m.requisicion_id = r.id
    WHERE m.tipo = 'salida'
      AND m.centro_origen_id IS NULL
      AND m.centro_destino_id IS NULL
)
SELECT id, centro_req, rn, total,
       CASE WHEN rn <= total/2 THEN 'Farmacia (centro_destino)' 
            ELSE 'Dispensación (centro_origen)' END as asignacion
FROM salidas_sin_centro;

-- 3a. Asignar centro_destino a la primera mitad (Salidas Farmacia Central)
UPDATE movimientos
SET centro_destino_id = subq.centro_req
FROM (
    WITH salidas_sin_centro AS (
        SELECT m.id, r.centro_destino_id as centro_req,
               ROW_NUMBER() OVER (ORDER BY m.id) as rn,
               COUNT(*) OVER () as total
        FROM movimientos m
        JOIN requisiciones r ON m.requisicion_id = r.id
        WHERE m.tipo = 'salida'
          AND m.centro_origen_id IS NULL
          AND m.centro_destino_id IS NULL
    )
    SELECT id, centro_req FROM salidas_sin_centro WHERE rn <= total/2
) subq
WHERE movimientos.id = subq.id;

-- 3b. Asignar centro_origen a la segunda mitad (Dispensaciones)
UPDATE movimientos
SET centro_origen_id = subq.centro_req
FROM (
    WITH salidas_sin_centro AS (
        SELECT m.id, r.centro_destino_id as centro_req,
               ROW_NUMBER() OVER (ORDER BY m.id) as rn,
               COUNT(*) OVER () as total
        FROM movimientos m
        JOIN requisiciones r ON m.requisicion_id = r.id
        WHERE m.tipo = 'salida'
          AND m.centro_origen_id IS NULL
          AND m.centro_destino_id IS NULL
    )
    SELECT id, centro_req FROM salidas_sin_centro WHERE rn > total/2
) subq
WHERE movimientos.id = subq.id;

-- ============================================
-- 5. VERIFICACIÓN - Estado después de corrección
-- ============================================

SELECT 
    'DESPUÉS DE CORRECCIÓN' as estado,
    COUNT(*) as movimientos_sin_centro
FROM movimientos m
WHERE m.tipo = 'salida'
  AND m.centro_origen_id IS NULL
  AND m.centro_destino_id IS NULL
  AND m.requisicion_id IS NOT NULL;

-- ============================================
-- 6. REPORTE FINAL
-- ============================================

SELECT 
    m.tipo,
    CASE 
        WHEN m.tipo = 'salida' AND m.centro_origen_id IS NOT NULL AND m.centro_destino_id IS NULL 
            THEN 'Dispensación desde Centro'
        WHEN m.tipo = 'salida' AND m.centro_origen_id IS NULL AND m.centro_destino_id IS NOT NULL 
            THEN 'Salida desde Farmacia Central'
        WHEN m.tipo = 'salida' AND m.centro_origen_id IS NULL AND m.centro_destino_id IS NULL 
            THEN 'SIN CENTRO (REVISAR)'
        WHEN m.tipo = 'entrada' AND m.centro_destino_id IS NOT NULL 
            THEN 'Entrada a Centro'
        WHEN m.tipo = 'entrada' AND m.centro_destino_id IS NULL 
            THEN 'Entrada SIN DESTINO (REVISAR)'
        ELSE 'Otro'
    END as clasificacion,
    COALESCE(c_origen.nombre, c_destino.nombre, 'Sin centro') as centro,
    COUNT(*) as cantidad
FROM movimientos m
LEFT JOIN centros c_origen ON m.centro_origen_id = c_origen.id
LEFT JOIN centros c_destino ON m.centro_destino_id = c_destino.id
WHERE m.requisicion_id IS NOT NULL
GROUP BY 
    m.tipo,
    CASE 
        WHEN m.tipo = 'salida' AND m.centro_origen_id IS NOT NULL AND m.centro_destino_id IS NULL 
            THEN 'Dispensación desde Centro'
        WHEN m.tipo = 'salida' AND m.centro_origen_id IS NULL AND m.centro_destino_id IS NOT NULL 
            THEN 'Salida desde Farmacia Central'
        WHEN m.tipo = 'salida' AND m.centro_origen_id IS NULL AND m.centro_destino_id IS NULL 
            THEN 'SIN CENTRO (REVISAR)'
        WHEN m.tipo = 'entrada' AND m.centro_destino_id IS NOT NULL 
            THEN 'Entrada a Centro'
        WHEN m.tipo = 'entrada' AND m.centro_destino_id IS NULL 
            THEN 'Entrada SIN DESTINO (REVISAR)'
        ELSE 'Otro'
    END,
    COALESCE(c_origen.nombre, c_destino.nombre, 'Sin centro')
ORDER BY m.tipo, clasificacion, centro;

-- ============================================
-- 7. VERIFICACIÓN VISUAL RÁPIDA
-- ============================================
-- Debe mostrar cantidades iguales:
-- - Salidas desde Farmacia Central = Entradas a Centro = Dispensaciones

SELECT 
    CASE 
        WHEN tipo = 'entrada' THEN 'Entradas'
        WHEN tipo = 'salida' AND centro_origen_id IS NOT NULL THEN 'Dispensaciones (centro_origen)'
        WHEN tipo = 'salida' AND centro_destino_id IS NOT NULL THEN 'Salidas Farmacia (centro_destino)'
        ELSE 'SIN CLASIFICAR'
    END as categoria,
    COUNT(*) as cantidad
FROM movimientos
WHERE requisicion_id IS NOT NULL
GROUP BY 
    CASE 
        WHEN tipo = 'entrada' THEN 'Entradas'
        WHEN tipo = 'salida' AND centro_origen_id IS NOT NULL THEN 'Dispensaciones (centro_origen)'
        WHEN tipo = 'salida' AND centro_destino_id IS NOT NULL THEN 'Salidas Farmacia (centro_destino)'
        ELSE 'SIN CLASIFICAR'
    END
ORDER BY categoria;
