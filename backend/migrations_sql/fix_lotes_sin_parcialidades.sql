-- ==============================================================================
-- FIX: Crear parcialidades para lotes existentes que no tengan ninguna
-- 
-- Este script crea registros de parcialidades para lotes que fueron importados
-- antes de la implementación del sistema de entregas parciales.
-- 
-- Se ejecuta idempotentemente: solo crea parcialidades para lotes que no tengan.
-- ==============================================================================

-- Primero verificar cantidad de lotes sin parcialidades
SELECT 
    COUNT(*) as lotes_sin_parcialidades,
    COUNT(CASE WHEN fecha_fabricacion IS NOT NULL THEN 1 END) as con_fecha_fab,
    COUNT(CASE WHEN fecha_fabricacion IS NULL THEN 1 END) as sin_fecha_fab
FROM lotes l
WHERE l.activo = true
  AND NOT EXISTS (SELECT 1 FROM lote_parcialidades lp WHERE lp.lote_id = l.id);

-- Crear parcialidades iniciales para lotes sin parcialidades
-- Usa fecha_fabricacion si existe, sino CURRENT_DATE
INSERT INTO lote_parcialidades (
    lote_id,
    fecha_entrega,
    cantidad,
    notas,
    es_sobreentrega,
    created_at
)
SELECT 
    l.id as lote_id,
    COALESCE(l.fecha_fabricacion, CURRENT_DATE) as fecha_entrega,
    l.cantidad_inicial as cantidad,
    'Carga inicial retroactiva (lote preexistente sin historial)' as notas,
    false as es_sobreentrega,
    NOW() as created_at
FROM lotes l
WHERE l.activo = true
  AND l.cantidad_inicial > 0
  AND NOT EXISTS (
      SELECT 1 
      FROM lote_parcialidades lp 
      WHERE lp.lote_id = l.id
  );

-- Verificar resultado
SELECT 
    'Parcialidades creadas' as resultado,
    COUNT(*) as total
FROM lote_parcialidades lp
WHERE lp.notas LIKE '%retroactiva%';

-- Verificar que ya no hay lotes sin parcialidades
SELECT 
    'Lotes aún sin parcialidades' as verificacion,
    COUNT(*) as total
FROM lotes l
WHERE l.activo = true
  AND l.cantidad_inicial > 0
  AND NOT EXISTS (SELECT 1 FROM lote_parcialidades lp WHERE lp.lote_id = l.id);
