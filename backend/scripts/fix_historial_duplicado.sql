-- ============================================================================
-- FIX: Deshabilitar trigger que causa duplicación de historial de requisiciones
-- ============================================================================
-- 
-- PROBLEMA: El trigger `trigger_historial_estado_requisicion` registra cambios
-- de estado automáticamente, pero el código Python también registra los cambios
-- con información adicional (usuario, motivo, IP). Esto causa entradas duplicadas.
--
-- SOLUCIÓN: Deshabilitar el trigger y dejar que solo Python registre el historial.
-- El código Python tiene más contexto (usuario, motivo, IP, user_agent).
--
-- EJECUTAR EN PRODUCCIÓN (Supabase):
-- ============================================================================

-- 1. Primero, eliminar duplicados existentes (mantener el registro con más información)
-- Esto elimina las entradas del trigger (que no tienen usuario ni motivo)

WITH duplicados AS (
    SELECT id,
           requisicion_id,
           estado_anterior,
           estado_nuevo,
           fecha_cambio,
           usuario_id,
           motivo,
           ROW_NUMBER() OVER (
               PARTITION BY requisicion_id, estado_anterior, estado_nuevo, 
                            DATE_TRUNC('second', fecha_cambio)
               ORDER BY 
                   -- Priorizar registros CON usuario y motivo
                   CASE WHEN usuario_id IS NOT NULL THEN 0 ELSE 1 END,
                   CASE WHEN motivo IS NOT NULL AND motivo != '' THEN 0 ELSE 1 END,
                   id DESC  -- En caso de empate, mantener el más reciente
           ) as rn
    FROM requisicion_historial_estados
)
DELETE FROM requisicion_historial_estados
WHERE id IN (
    SELECT id FROM duplicados WHERE rn > 1
);

-- 2. Deshabilitar el trigger para evitar duplicados futuros
DROP TRIGGER IF EXISTS trigger_historial_estado_requisicion ON requisiciones;

-- 3. (Opcional) Si quieres mantener la función pero no el trigger:
-- La función queda disponible por si se necesita en el futuro
-- COMMENT ON FUNCTION registrar_cambio_estado_requisicion IS 'Deshabilitada - El historial se registra desde Python con más contexto';

-- 4. Verificar que el trigger fue eliminado
-- SELECT * FROM pg_trigger WHERE tgname = 'trigger_historial_estado_requisicion';

-- ============================================================================
-- VERIFICACIÓN: Contar registros por requisición para confirmar que no hay duplicados
-- ============================================================================
-- SELECT requisicion_id, estado_anterior, estado_nuevo, 
--        DATE_TRUNC('second', fecha_cambio) as momento,
--        COUNT(*) as cantidad
-- FROM requisicion_historial_estados
-- GROUP BY requisicion_id, estado_anterior, estado_nuevo, DATE_TRUNC('second', fecha_cambio)
-- HAVING COUNT(*) > 1
-- ORDER BY requisicion_id, momento;
