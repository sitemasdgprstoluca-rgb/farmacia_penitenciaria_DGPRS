-- ============================================================================
-- MIGRACIÓN 019: Constraint UNIQUE anti-duplicados para lote_parcialidades
-- ============================================================================
-- Propósito: Evitar registros duplicados de parcialidades
-- Un lote no puede tener dos entregas con la misma fecha Y factura
-- 
-- Lógica: Si fecha_entrega + lote_id + numero_factura son iguales, es duplicado
-- (numero_factura puede ser NULL, entonces solo fecha+lote es el criterio)
-- ============================================================================

-- Crear índice único para prevenir duplicados
-- COALESCE maneja el caso de numero_factura NULL
CREATE UNIQUE INDEX IF NOT EXISTS idx_lote_parcialidades_unique_entrega
ON lote_parcialidades (lote_id, fecha_entrega, COALESCE(numero_factura, ''));

-- Comentario de documentación
COMMENT ON INDEX idx_lote_parcialidades_unique_entrega IS 
'Previene registros duplicados: mismo lote + fecha + factura no puede repetirse';

-- ============================================================================
-- FIN DE MIGRACIÓN
-- ============================================================================
