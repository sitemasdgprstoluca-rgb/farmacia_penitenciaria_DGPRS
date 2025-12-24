-- =========================================================================
-- SCRIPT: Agregar columnas de finalización a salidas_donaciones
-- Fecha: 2024-12-23
-- Descripción: Agrega columnas finalizado, fecha_finalizado, finalizado_por_id
-- 
-- NOTA: centro_destino_id YA EXISTE en la BD (como bigint)
-- 
-- EJECUTAR EN SUPABASE DASHBOARD > SQL EDITOR
-- =========================================================================

-- Agregar columna finalizado (para marcar entregas completadas)
ALTER TABLE public.salidas_donaciones 
ADD COLUMN IF NOT EXISTS finalizado BOOLEAN DEFAULT FALSE;

-- Agregar columna fecha_finalizado
ALTER TABLE public.salidas_donaciones 
ADD COLUMN IF NOT EXISTS fecha_finalizado TIMESTAMP WITH TIME ZONE;

-- Agregar columna finalizado_por_id (FK a usuarios)
ALTER TABLE public.salidas_donaciones 
ADD COLUMN IF NOT EXISTS finalizado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL;

-- NOTA: centro_destino_id YA EXISTE como bigint - No es necesario agregarlo
-- Si necesitas la FK, ejecuta esto (opcional):
-- ALTER TABLE public.salidas_donaciones 
-- ADD CONSTRAINT salidas_donaciones_centro_destino_fk 
-- FOREIGN KEY (centro_destino_id) REFERENCES centros(id) ON DELETE SET NULL;

-- Crear índices para las nuevas columnas
CREATE INDEX IF NOT EXISTS idx_salidas_donaciones_finalizado 
ON public.salidas_donaciones(finalizado);

-- Índice para centro_destino_id (si no existe ya)
CREATE INDEX IF NOT EXISTS idx_salidas_donaciones_centro_destino 
ON public.salidas_donaciones(centro_destino_id);

-- Comentarios informativos
COMMENT ON COLUMN public.salidas_donaciones.finalizado IS 
'Indica si la entrega física se completó (con firmas)';

COMMENT ON COLUMN public.salidas_donaciones.fecha_finalizado IS 
'Fecha y hora cuando se marcó como finalizada';

COMMENT ON COLUMN public.salidas_donaciones.finalizado_por_id IS 
'Usuario que marcó la entrega como finalizada';

-- =========================================================================
-- VERIFICACIÓN
-- =========================================================================
-- Ejecutar para verificar que las columnas se crearon:
SELECT column_name, data_type, is_nullable, column_default 
FROM information_schema.columns 
WHERE table_name = 'salidas_donaciones' 
  AND column_name IN ('finalizado', 'fecha_finalizado', 'finalizado_por_id', 'centro_destino_id')
ORDER BY column_name;
