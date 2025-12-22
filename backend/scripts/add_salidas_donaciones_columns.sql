-- =========================================================================
-- SCRIPT: Agregar columnas faltantes a salidas_donaciones
-- Fecha: 2024-12-21
-- Descripción: Agrega columnas finalizado, fecha_finalizado, finalizado_por_id
--              y centro_destino_id a la tabla salidas_donaciones
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

-- Agregar columna centro_destino_id (FK a centros)
ALTER TABLE public.salidas_donaciones 
ADD COLUMN IF NOT EXISTS centro_destino_id INTEGER REFERENCES centros(id) ON DELETE SET NULL;

-- Crear índices para las nuevas columnas
CREATE INDEX IF NOT EXISTS idx_salidas_donaciones_finalizado 
ON public.salidas_donaciones(finalizado);

CREATE INDEX IF NOT EXISTS idx_salidas_donaciones_centro_destino 
ON public.salidas_donaciones(centro_destino_id);

-- Comentario informativo
COMMENT ON COLUMN public.salidas_donaciones.finalizado IS 
'Indica si la entrega física se completó (con firmas)';

COMMENT ON COLUMN public.salidas_donaciones.fecha_finalizado IS 
'Fecha y hora cuando se marcó como finalizada';

COMMENT ON COLUMN public.salidas_donaciones.finalizado_por_id IS 
'Usuario que marcó la entrega como finalizada';

COMMENT ON COLUMN public.salidas_donaciones.centro_destino_id IS 
'Centro de destino de la donación (opcional)';

-- =========================================================================
-- VERIFICACIÓN
-- =========================================================================
-- Ejecutar para verificar que las columnas se crearon:
-- SELECT column_name, data_type, is_nullable, column_default 
-- FROM information_schema.columns 
-- WHERE table_name = 'salidas_donaciones' 
-- ORDER BY ordinal_position;
