-- =====================================================
-- MIGRACIÓN: Campos para evidencia de entrega firmada
-- Fecha: 2026-03-13
-- Descripción: Agrega campos para subir PDF/imagen escaneada
--              de hojas de entrega firmadas (salida masiva y requisiciones)
-- =====================================================

-- IMPORTANTE: Ejecutar en Supabase Dashboard > SQL Editor

BEGIN;

-- 1. Campo en movimientos para evidencia de salida masiva
-- Se almacena la URL del documento escaneado (PDF/imagen)
ALTER TABLE movimientos
ADD COLUMN IF NOT EXISTS documento_evidencia_url VARCHAR(500);

-- 2. Campo en requisiciones para evidencia de entrega
-- Separado de foto_firma_recepcion (que es la foto de la firma)
-- Este campo es para el documento completo escaneado
ALTER TABLE requisiciones
ADD COLUMN IF NOT EXISTS documento_entrega_url VARCHAR(500);

-- 3. Índice para buscar movimientos con evidencia
CREATE INDEX IF NOT EXISTS idx_mov_doc_evidencia
    ON movimientos (documento_evidencia_url)
    WHERE documento_evidencia_url IS NOT NULL;

COMMIT;

-- Total: 2 columnas agregadas (movimientos.documento_evidencia_url, requisiciones.documento_entrega_url)
