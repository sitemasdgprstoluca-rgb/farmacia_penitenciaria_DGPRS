-- =====================================================
-- MIGRACIÓN: Flujo Multinivel para Compras de Caja Chica
-- Fecha: 2026-01-14
-- =====================================================
-- 
-- Este script agrega los campos necesarios para implementar
-- un flujo de autorización similar a Requisiciones:
-- Médico → Admin → Director → (Compra) → (Recepción)
--
-- Estados del flujo:
-- 1. pendiente: Médico crea solicitud
-- 2. enviada_admin: Médico envía a Admin
-- 3. autorizada_admin: Admin aprueba
-- 4. enviada_director: Admin envía a Director  
-- 5. autorizada: Director aprueba (lista para comprar)
-- 6. comprada: Se realizó la compra
-- 7. recibida: Se recibieron los productos
-- 8. cancelada: Cancelada en cualquier punto
-- 9. rechazada: Rechazada por Admin o Director
-- =====================================================

-- 1. Agregar columnas para flujo multinivel si no existen
DO $$ 
BEGIN
    -- Fechas del flujo
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'compras_caja_chica' AND column_name = 'fecha_envio_admin') THEN
        ALTER TABLE compras_caja_chica ADD COLUMN fecha_envio_admin TIMESTAMP WITH TIME ZONE;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'compras_caja_chica' AND column_name = 'fecha_autorizacion_admin') THEN
        ALTER TABLE compras_caja_chica ADD COLUMN fecha_autorizacion_admin TIMESTAMP WITH TIME ZONE;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'compras_caja_chica' AND column_name = 'fecha_envio_director') THEN
        ALTER TABLE compras_caja_chica ADD COLUMN fecha_envio_director TIMESTAMP WITH TIME ZONE;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'compras_caja_chica' AND column_name = 'fecha_autorizacion_director') THEN
        ALTER TABLE compras_caja_chica ADD COLUMN fecha_autorizacion_director TIMESTAMP WITH TIME ZONE;
    END IF;
    
    -- Actores del flujo
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'compras_caja_chica' AND column_name = 'administrador_centro_id') THEN
        ALTER TABLE compras_caja_chica ADD COLUMN administrador_centro_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'compras_caja_chica' AND column_name = 'director_centro_id') THEN
        ALTER TABLE compras_caja_chica ADD COLUMN director_centro_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL;
    END IF;
    
    -- Motivos de rechazo
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'compras_caja_chica' AND column_name = 'motivo_rechazo') THEN
        ALTER TABLE compras_caja_chica ADD COLUMN motivo_rechazo TEXT;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'compras_caja_chica' AND column_name = 'rechazado_por_id') THEN
        ALTER TABLE compras_caja_chica ADD COLUMN rechazado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL;
    END IF;
    
    -- Proveedor contacto si no existe
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'compras_caja_chica' AND column_name = 'proveedor_contacto') THEN
        ALTER TABLE compras_caja_chica ADD COLUMN proveedor_contacto VARCHAR(200);
    END IF;
    
    RAISE NOTICE 'Columnas de flujo multinivel agregadas correctamente';
END $$;

-- 2. Actualizar constraint de estado para incluir nuevos estados
-- Primero verificar si existe el constraint y eliminarlo
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.constraint_column_usage WHERE table_name = 'compras_caja_chica' AND constraint_name = 'compras_caja_chica_estado_check') THEN
        ALTER TABLE compras_caja_chica DROP CONSTRAINT compras_caja_chica_estado_check;
    END IF;
END $$;

-- Agregar nuevo constraint con todos los estados
ALTER TABLE compras_caja_chica ADD CONSTRAINT compras_caja_chica_estado_check 
CHECK (estado IN ('pendiente', 'enviada_admin', 'autorizada_admin', 'enviada_director', 'autorizada', 'comprada', 'recibida', 'cancelada', 'rechazada'));

-- 3. Crear índices para mejorar búsquedas
CREATE INDEX IF NOT EXISTS idx_compras_caja_chica_estado ON compras_caja_chica(estado);
CREATE INDEX IF NOT EXISTS idx_compras_caja_chica_centro ON compras_caja_chica(centro_id);
CREATE INDEX IF NOT EXISTS idx_compras_caja_chica_solicitante ON compras_caja_chica(solicitante_id);
CREATE INDEX IF NOT EXISTS idx_compras_caja_chica_fecha ON compras_caja_chica(fecha_solicitud);

-- 4. Comentarios para documentación
COMMENT ON COLUMN compras_caja_chica.fecha_envio_admin IS 'Fecha en que el médico envió la solicitud al administrador';
COMMENT ON COLUMN compras_caja_chica.fecha_autorizacion_admin IS 'Fecha en que el administrador autorizó la solicitud';
COMMENT ON COLUMN compras_caja_chica.fecha_envio_director IS 'Fecha en que se envió al director para autorización final';
COMMENT ON COLUMN compras_caja_chica.fecha_autorizacion_director IS 'Fecha en que el director autorizó la compra';
COMMENT ON COLUMN compras_caja_chica.administrador_centro_id IS 'Usuario admin que autorizó la solicitud';
COMMENT ON COLUMN compras_caja_chica.director_centro_id IS 'Usuario director que autorizó la solicitud';
COMMENT ON COLUMN compras_caja_chica.motivo_rechazo IS 'Motivo del rechazo si aplica';

RAISE NOTICE 'Migración completada exitosamente';
