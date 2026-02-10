-- =====================================================
-- MIGRACIÓN: Flujo Multinivel para Compras de Caja Chica
-- Fecha: 2026-01-14
-- =====================================================
-- 
-- Este script agrega los campos necesarios para implementar
-- un flujo de autorización con verificación de farmacia:
-- Centro → Farmacia (verifica) → Admin → Director → (Compra) → (Recepción)
--
-- Estados del flujo:
-- 1. pendiente: Centro crea solicitud
-- 2. enviada_farmacia: Centro envía a Farmacia para verificar stock
-- 3. sin_stock_farmacia: Farmacia confirma que NO tiene el producto
-- 4. rechazada_farmacia: Farmacia indica que SÍ tiene stock (no procede compra)
-- 5. enviada_admin: Se envía a Admin del centro
-- 6. autorizada_admin: Admin aprueba
-- 7. enviada_director: Admin envía a Director  
-- 8. autorizada: Director aprueba (lista para comprar)
-- 9. comprada: Se realizó la compra
-- 10. recibida: Se recibieron los productos
-- 11. cancelada: Cancelada en cualquier punto
-- 12. rechazada: Rechazada por Admin o Director
-- =====================================================

-- 1. Agregar columnas para flujo con verificación de farmacia
DO $$ 
BEGIN
    -- ========== FLUJO FARMACIA ==========
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'compras_caja_chica' AND column_name = 'fecha_envio_farmacia') THEN
        ALTER TABLE compras_caja_chica ADD COLUMN fecha_envio_farmacia TIMESTAMP WITH TIME ZONE;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'compras_caja_chica' AND column_name = 'fecha_respuesta_farmacia') THEN
        ALTER TABLE compras_caja_chica ADD COLUMN fecha_respuesta_farmacia TIMESTAMP WITH TIME ZONE;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'compras_caja_chica' AND column_name = 'verificado_por_farmacia_id') THEN
        ALTER TABLE compras_caja_chica ADD COLUMN verificado_por_farmacia_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'compras_caja_chica' AND column_name = 'respuesta_farmacia') THEN
        ALTER TABLE compras_caja_chica ADD COLUMN respuesta_farmacia TEXT;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'compras_caja_chica' AND column_name = 'stock_farmacia_verificado') THEN
        ALTER TABLE compras_caja_chica ADD COLUMN stock_farmacia_verificado INTEGER;
    END IF;

    -- ========== FLUJO MULTINIVEL (existentes) ==========
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
    
    RAISE NOTICE 'Columnas de flujo con verificación de farmacia agregadas correctamente';
END $$;

-- 2. Actualizar constraint de estado para incluir nuevos estados
-- Primero verificar si existe el constraint y eliminarlo
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.constraint_column_usage WHERE table_name = 'compras_caja_chica' AND constraint_name = 'compras_caja_chica_estado_check') THEN
        ALTER TABLE compras_caja_chica DROP CONSTRAINT compras_caja_chica_estado_check;
    END IF;
END $$;

-- Agregar nuevo constraint con todos los estados (incluyendo flujo farmacia)
ALTER TABLE compras_caja_chica ADD CONSTRAINT compras_caja_chica_estado_check 
CHECK (estado IN ('pendiente', 'enviada_farmacia', 'sin_stock_farmacia', 'rechazada_farmacia', 'enviada_admin', 'autorizada_admin', 'enviada_director', 'autorizada', 'comprada', 'recibida', 'cancelada', 'rechazada'));

-- 3. Crear índices para mejorar búsquedas
CREATE INDEX IF NOT EXISTS idx_compras_caja_chica_estado ON compras_caja_chica(estado);
CREATE INDEX IF NOT EXISTS idx_compras_caja_chica_centro ON compras_caja_chica(centro_id);
CREATE INDEX IF NOT EXISTS idx_compras_caja_chica_solicitante ON compras_caja_chica(solicitante_id);
CREATE INDEX IF NOT EXISTS idx_compras_caja_chica_fecha ON compras_caja_chica(fecha_solicitud);
CREATE INDEX IF NOT EXISTS idx_compras_caja_chica_verificador ON compras_caja_chica(verificado_por_farmacia_id);

-- 4. Comentarios para documentación
COMMENT ON COLUMN compras_caja_chica.fecha_envio_farmacia IS 'Fecha en que se envió a farmacia para verificar disponibilidad';
COMMENT ON COLUMN compras_caja_chica.fecha_respuesta_farmacia IS 'Fecha en que farmacia respondió sobre disponibilidad';
COMMENT ON COLUMN compras_caja_chica.verificado_por_farmacia_id IS 'Usuario de farmacia que verificó la disponibilidad';
COMMENT ON COLUMN compras_caja_chica.respuesta_farmacia IS 'Respuesta/comentario de farmacia sobre la verificación';
COMMENT ON COLUMN compras_caja_chica.stock_farmacia_verificado IS 'Stock encontrado en farmacia al momento de verificar';
COMMENT ON COLUMN compras_caja_chica.fecha_envio_admin IS 'Fecha en que se envió al administrador del centro';
COMMENT ON COLUMN compras_caja_chica.fecha_autorizacion_admin IS 'Fecha en que el administrador autorizó la solicitud';
COMMENT ON COLUMN compras_caja_chica.fecha_envio_director IS 'Fecha en que se envió al director para autorización final';
COMMENT ON COLUMN compras_caja_chica.fecha_autorizacion_director IS 'Fecha en que el director autorizó la compra';
COMMENT ON COLUMN compras_caja_chica.administrador_centro_id IS 'Usuario admin que autorizó la solicitud';
COMMENT ON COLUMN compras_caja_chica.director_centro_id IS 'Usuario director que autorizó la solicitud';
COMMENT ON COLUMN compras_caja_chica.motivo_rechazo IS 'Motivo del rechazo si aplica';

-- Migración completada exitosamente
