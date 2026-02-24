-- ============================================================================
-- MIGRACIÓN 017: Tabla de Parcialidades de Lotes
-- ============================================================================
-- Propósito: Registrar el historial de entregas parciales por lote
-- - Cada lote puede tener múltiples entregas parciales
-- - Cada parcialidad tiene fecha de entrega y cantidad
-- - La suma de parcialidades se compara contra contratos (lote y global)
-- 
-- Estados posibles:
-- - PENDIENTE: total_entregado = 0
-- - PARCIAL: 0 < total_entregado < cantidad_contrato
-- - CUMPLIDO: total_entregado == cantidad_contrato
-- - SOBREENTREGA: total_entregado > cantidad_contrato
-- - SIN_CONTRATO: cantidad_contrato no definida
-- ============================================================================

-- Crear tabla de parcialidades
CREATE TABLE IF NOT EXISTS lote_parcialidades (
    id SERIAL PRIMARY KEY,
    lote_id INTEGER NOT NULL REFERENCES lotes(id) ON DELETE CASCADE,
    fecha_entrega DATE NOT NULL,
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    numero_factura VARCHAR(100),
    numero_remision VARCHAR(100),
    proveedor VARCHAR(255),
    notas TEXT,
    -- Campos de auditoría para sobre-entregas
    es_sobreentrega BOOLEAN DEFAULT FALSE,
    motivo_override TEXT,
    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Índices para consultas frecuentes
CREATE INDEX IF NOT EXISTS idx_lote_parcialidades_lote_id ON lote_parcialidades(lote_id);
CREATE INDEX IF NOT EXISTS idx_lote_parcialidades_fecha ON lote_parcialidades(fecha_entrega);
CREATE INDEX IF NOT EXISTS idx_lote_parcialidades_sobreentrega ON lote_parcialidades(es_sobreentrega) WHERE es_sobreentrega = true;

-- Comentarios de documentación
COMMENT ON TABLE lote_parcialidades IS 'Historial de entregas parciales por lote - permite rastrear cuándo y cuánto se recibió';
COMMENT ON COLUMN lote_parcialidades.lote_id IS 'FK al lote padre';
COMMENT ON COLUMN lote_parcialidades.fecha_entrega IS 'Fecha de recepción de esta parcialidad';
COMMENT ON COLUMN lote_parcialidades.cantidad IS 'Cantidad recibida en esta entrega';
COMMENT ON COLUMN lote_parcialidades.numero_factura IS 'Número de factura asociada (opcional)';
COMMENT ON COLUMN lote_parcialidades.numero_remision IS 'Número de remisión o guía (opcional)';
COMMENT ON COLUMN lote_parcialidades.proveedor IS 'Nombre del proveedor que entregó (opcional)';
COMMENT ON COLUMN lote_parcialidades.notas IS 'Observaciones adicionales';
COMMENT ON COLUMN lote_parcialidades.es_sobreentrega IS 'True si esta parcialidad fue autorizada como sobre-entrega';
COMMENT ON COLUMN lote_parcialidades.motivo_override IS 'Motivo obligatorio cuando es sobre-entrega (auditoría)';
COMMENT ON COLUMN lote_parcialidades.usuario_id IS 'Usuario que registró la parcialidad';

-- ============================================================================
-- Vista auxiliar: Resumen de parcialidades por lote (con estados correctos)
-- ============================================================================
CREATE OR REPLACE VIEW vista_lotes_parcialidades AS
SELECT 
    l.id AS lote_id,
    l.numero_lote,
    l.producto_id,
    p.clave AS producto_clave,
    p.nombre AS producto_nombre,
    l.numero_contrato,
    l.cantidad_inicial,
    l.cantidad_contrato,
    l.cantidad_contrato_global,
    -- Parcialidades de este lote
    COALESCE(SUM(lp.cantidad), 0) AS total_parcialidades,
    COUNT(lp.id) AS num_entregas,
    MIN(lp.fecha_entrega) AS primera_entrega,
    MAX(lp.fecha_entrega) AS ultima_entrega,
    -- Sobre-entregas auditadas
    COUNT(CASE WHEN lp.es_sobreentrega THEN 1 END) AS num_sobreentregas,
    -- Comparación con contratos
    CASE 
        WHEN l.cantidad_contrato IS NOT NULL 
        THEN l.cantidad_contrato - COALESCE(SUM(lp.cantidad), 0)
        ELSE NULL 
    END AS pendiente_contrato_lote,
    -- Excedente (si hay sobre-entrega)
    CASE 
        WHEN l.cantidad_contrato IS NOT NULL AND COALESCE(SUM(lp.cantidad), 0) > l.cantidad_contrato
        THEN COALESCE(SUM(lp.cantidad), 0) - l.cantidad_contrato
        ELSE NULL 
    END AS excedente_lote,
    -- Estado del contrato lote (PENDIENTE, PARCIAL, CUMPLIDO, SOBREENTREGA, SIN_CONTRATO)
    CASE 
        WHEN l.cantidad_contrato IS NULL OR l.cantidad_contrato = 0 THEN 'SIN_CONTRATO'
        WHEN COALESCE(SUM(lp.cantidad), 0) = 0 THEN 'PENDIENTE'
        WHEN COALESCE(SUM(lp.cantidad), 0) < l.cantidad_contrato THEN 'PARCIAL'
        WHEN COALESCE(SUM(lp.cantidad), 0) = l.cantidad_contrato THEN 'CUMPLIDO'
        ELSE 'SOBREENTREGA'
    END AS estado_contrato_lote
FROM lotes l
JOIN productos p ON l.producto_id = p.id
LEFT JOIN lote_parcialidades lp ON l.id = lp.lote_id
WHERE l.activo = true
GROUP BY l.id, l.numero_lote, l.producto_id, p.clave, p.nombre, 
         l.numero_contrato, l.cantidad_inicial, l.cantidad_contrato, l.cantidad_contrato_global;

-- ============================================================================
-- Vista auxiliar: Resumen de contratos globales por clave (con estados correctos)
-- ============================================================================
CREATE OR REPLACE VIEW vista_contratos_globales AS
SELECT 
    p.id AS producto_id,
    p.clave AS producto_clave,
    p.nombre AS producto_nombre,
    l.numero_contrato_global AS numero_contrato,
    -- Contrato global (tomamos el máximo porque debería ser igual en todos)
    MAX(l.cantidad_contrato_global) AS cantidad_contrato_global,
    -- Total de parcialidades registradas (suma de todas las entregas)
    COALESCE(SUM(parcialidades.total), 0) AS total_parcialidades,
    -- Cantidad de lotes activos
    COUNT(DISTINCT l.id) AS num_lotes,
    -- Pendiente del contrato global
    CASE 
        WHEN MAX(l.cantidad_contrato_global) IS NOT NULL 
        THEN GREATEST(0, MAX(l.cantidad_contrato_global) - COALESCE(SUM(parcialidades.total), 0))
        ELSE NULL 
    END AS pendiente_global,
    -- Excedente (si hay sobre-entrega)
    CASE 
        WHEN MAX(l.cantidad_contrato_global) IS NOT NULL 
             AND COALESCE(SUM(parcialidades.total), 0) > MAX(l.cantidad_contrato_global)
        THEN COALESCE(SUM(parcialidades.total), 0) - MAX(l.cantidad_contrato_global)
        ELSE NULL 
    END AS excedente_global,
    -- Estado del contrato global (PENDIENTE, PARCIAL, CUMPLIDO, SOBREENTREGA, SIN_CONTRATO)
    CASE 
        WHEN MAX(l.cantidad_contrato_global) IS NULL OR MAX(l.cantidad_contrato_global) = 0 THEN 'SIN_CONTRATO'
        WHEN COALESCE(SUM(parcialidades.total), 0) = 0 THEN 'PENDIENTE'
        WHEN COALESCE(SUM(parcialidades.total), 0) < MAX(l.cantidad_contrato_global) THEN 'PARCIAL'
        WHEN COALESCE(SUM(parcialidades.total), 0) = MAX(l.cantidad_contrato_global) THEN 'CUMPLIDO'
        ELSE 'SOBREENTREGA'
    END AS estado_contrato_global
FROM lotes l
JOIN productos p ON l.producto_id = p.id
LEFT JOIN (
    SELECT lote_id, SUM(cantidad) AS total
    FROM lote_parcialidades
    GROUP BY lote_id
) parcialidades ON l.id = parcialidades.lote_id
WHERE l.activo = true 
  AND l.numero_contrato_global IS NOT NULL 
  AND l.numero_contrato_global != ''
GROUP BY p.id, p.clave, p.nombre, l.numero_contrato_global;

-- ============================================================================
-- Migrar datos existentes: Crear parcialidad inicial para lotes con fecha_fabricacion
-- ============================================================================
-- IDEMPOTENTE: Solo inserta si no existe ya una parcialidad para el lote
INSERT INTO lote_parcialidades (lote_id, fecha_entrega, cantidad, notas, created_at)
SELECT 
    id AS lote_id,
    COALESCE(fecha_fabricacion, created_at::date) AS fecha_entrega,
    cantidad_inicial AS cantidad,
    'Migración automática - primera entrega' AS notas,
    created_at
FROM lotes
WHERE activo = true
  AND cantidad_inicial > 0
  AND NOT EXISTS (
      SELECT 1 FROM lote_parcialidades lp WHERE lp.lote_id = lotes.id
  );

-- ============================================================================
-- FIN DE MIGRACIÓN
-- ============================================================================
