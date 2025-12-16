-- =====================================================
-- SCRIPT PARA RESETEAR MOVIMIENTOS Y REQUISICIONES
-- Ejecutar en Supabase SQL Editor
-- =====================================================

-- 1. Eliminar todos los movimientos de prueba
DELETE FROM movimientos;

-- 2. Resetear los lotes en centros (creados por surtidos anteriores)
-- Los lotes de farmacia central (centro_id IS NULL) se mantienen
UPDATE lotes 
SET cantidad_actual = cantidad_inicial,
    updated_at = NOW()
WHERE centro_id IS NOT NULL;

-- 3. Eliminar lotes que fueron creados en centros por requisiciones
-- (Opcional - si quieres empezar completamente limpio con lotes)
-- DELETE FROM lotes WHERE centro_id IS NOT NULL;

-- 4. Resetear estados de requisiciones a 'autorizada' para probar surtido
UPDATE requisiciones 
SET estado = 'autorizada',
    fecha_surtido = NULL,
    surtidor_id = NULL,
    foto_firma_surtido = NULL,
    fecha_firma_surtido = NULL,
    usuario_firma_surtido_id = NULL,
    updated_at = NOW()
WHERE estado IN ('en_surtido', 'surtida', 'parcial');

-- 5. Resetear cantidades surtidas en detalles de requisiciones
UPDATE detalles_requisicion
SET cantidad_surtida = 0,
    updated_at = NOW();

-- 6. Auto-asignar cantidad_autorizada donde sea NULL (fix para requisiciones legacy)
UPDATE detalles_requisicion
SET cantidad_autorizada = cantidad_solicitada,
    updated_at = NOW()
WHERE cantidad_autorizada IS NULL OR cantidad_autorizada = 0;

-- 7. Verificar estado final
SELECT 
    r.id, 
    r.numero, 
    r.estado, 
    r.centro_destino_id,
    COUNT(d.id) as total_detalles,
    SUM(d.cantidad_solicitada) as total_solicitado,
    SUM(d.cantidad_autorizada) as total_autorizado,
    SUM(d.cantidad_surtida) as total_surtido
FROM requisiciones r
LEFT JOIN detalles_requisicion d ON d.requisicion_id = r.id
GROUP BY r.id, r.numero, r.estado, r.centro_destino_id
ORDER BY r.id;

-- 8. Verificar stock en lotes de farmacia central
SELECT 
    l.id,
    l.numero_lote,
    p.clave as producto_clave,
    p.nombre as producto_nombre,
    l.cantidad_inicial,
    l.cantidad_actual,
    l.fecha_caducidad,
    l.activo,
    CASE WHEN l.centro_id IS NULL THEN 'Farmacia Central' ELSE c.nombre END as centro
FROM lotes l
JOIN productos p ON p.id = l.producto_id
LEFT JOIN centros c ON c.id = l.centro_id
WHERE l.activo = true AND l.cantidad_actual > 0
ORDER BY l.centro_id NULLS FIRST, p.clave, l.fecha_caducidad;
