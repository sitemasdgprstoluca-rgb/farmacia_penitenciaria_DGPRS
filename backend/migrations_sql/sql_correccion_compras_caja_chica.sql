-- Corrección para hacer proveedor_nombre opcional en compras_caja_chica
-- El proveedor puede no conocerse al momento de crear la solicitud

ALTER TABLE compras_caja_chica 
ALTER COLUMN proveedor_nombre DROP NOT NULL;

-- Verificar que quedó nullable
-- SELECT column_name, is_nullable 
-- FROM information_schema.columns 
-- WHERE table_name = 'compras_caja_chica' AND column_name = 'proveedor_nombre';
