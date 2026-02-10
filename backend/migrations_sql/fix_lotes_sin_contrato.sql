-- =====================================================================
-- Script para actualizar numero_contrato en lotes de centros
-- que fueron creados sin este campo
-- =====================================================================
-- 
-- Este script actualiza lotes en centros (centro_id IS NOT NULL) 
-- que no tienen numero_contrato, buscando el contrato del lote original
-- en Farmacia Central (centro_id IS NULL) con el mismo numero_lote y producto.
--
-- Ejecutar en Supabase SQL Editor
-- =====================================================================

-- Primero, ver cuántos lotes necesitan actualización
SELECT 
    lc.id as lote_centro_id,
    lc.numero_lote,
    lc.numero_contrato as contrato_actual,
    lfc.numero_contrato as contrato_farmacia,
    c.nombre as centro,
    p.clave as producto_clave
FROM inventario_lote lc
LEFT JOIN inventario_lote lfc ON (
    lfc.numero_lote = lc.numero_lote 
    AND lfc.producto_id = lc.producto_id 
    AND lfc.centro_id IS NULL
)
LEFT JOIN inventario_centro c ON c.id = lc.centro_id
LEFT JOIN inventario_producto p ON p.id = lc.producto_id
WHERE lc.centro_id IS NOT NULL  -- Solo lotes en centros
  AND (lc.numero_contrato IS NULL OR lc.numero_contrato = '')  -- Sin contrato
  AND lfc.numero_contrato IS NOT NULL  -- El original sí tiene contrato
  AND lfc.numero_contrato != '';

-- Actualizar los lotes de centros con el contrato del lote original
UPDATE inventario_lote lc
SET numero_contrato = lfc.numero_contrato,
    updated_at = NOW()
FROM inventario_lote lfc
WHERE lfc.numero_lote = lc.numero_lote 
  AND lfc.producto_id = lc.producto_id 
  AND lfc.centro_id IS NULL
  AND lc.centro_id IS NOT NULL  -- Solo lotes en centros
  AND (lc.numero_contrato IS NULL OR lc.numero_contrato = '')  -- Sin contrato
  AND lfc.numero_contrato IS NOT NULL  -- El original sí tiene contrato
  AND lfc.numero_contrato != '';

-- Verificar el resultado
SELECT 
    COUNT(*) as lotes_actualizados
FROM inventario_lote lc
WHERE lc.centro_id IS NOT NULL
  AND lc.numero_contrato IS NOT NULL
  AND lc.numero_contrato != '';
