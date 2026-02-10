-- Script de inserción de productos para Supabase
-- Con manejo de conflictos y validación
-- Generado: 2025-12-15
-- Total de productos: 76

-- IMPORTANTE: Ejecuta esto DESPUÉS de ajustar las columnas con supabase_ajustar_columnas.sql

-- Instrucciones:
-- 1. Si quieres REEMPLAZAR productos existentes, ejecuta primero:
--    DELETE FROM productos WHERE clave LIKE '%';
-- 2. Si solo quieres insertar nuevos (recomendado), ejecuta este script directamente
-- 3. Los INSERT usan ON CONFLICT DO NOTHING para evitar duplicados

-- Verificar productos actuales (opcional)
SELECT COUNT(*) as productos_actuales FROM productos;

-- =============================================================================
-- INSERCIÓN DE PRODUCTOS CON MANEJO DE CONFLICTOS
-- =============================================================================

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('615', 'KETOCONAZOL /CLINDAMICINA', NULL, 'CAJA', 'medicamento', 'FEMITAB', 'CAJA CON 7 OVULOS', '400 MILIGRAMOS/ 100 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('616', 'AMOXICILINA / CLAVULANATO DE POTASIO', NULL, 'CAJA', 'medicamento', 'ACARBIXIN (GIMACLAV)', 'CAJA CON 10 TABLETAS', '875 MILIGRAMOS/125 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('617', 'AMOXICILINA', NULL, 'CAJA', 'medicamento', 'GENERICO', 'CAJA CON 12 CAPSULAS', '500 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('618', 'AMPICILINA', NULL, 'CAJA', 'medicamento', 'GENERICO', 'CAJA CON 20 CAPSULAS', '500 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('619', 'AZITROMICINA 500 MILIGRAMOS', NULL, 'CAJA', 'medicamento', 'CHARYN 3', 'CAJA CON 3 TABLETAS', '500 MILIGRAMOS', NULL, 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('621', 'BENZATINA', NULL, 'CAJA', 'medicamento', 'GENERICO', 'CAJA CON 1 FRASCO AMPULA', '1,200,000 UI', NULL, 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('622', 'BENZONATATO', NULL, 'CAJA', 'medicamento', 'PROGLEBEN', 'CAJA CON 20 CAPSULAS', '100 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('624', 'CARBOCISTEINA', NULL, 'CAJA', 'medicamento', 'GU-PMAX', 'CAJA CON 10 CAPSULAS', '75 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('625', 'CIANOCOBALAMINA /DICLOFENACO/ PIRIDOXINA', NULL, 'CAJA', 'medicamento', 'ARTIFRAX FORACOL', 'CAJA CON 30 CAPSULAS', 'MILIGRAMOS/25 MILIGRAMOS/ 50 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('626', 'CLONIXINATO DE LISINA', NULL, 'CAJA', 'medicamento', 'GENERICO', 'CAJA CON 5 AMPOLLETAS', '100 MILIGRAMOS', NULL, 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('627', 'CIPROFLOXACINO', NULL, 'CAJA', 'medicamento', 'GENERICO', 'CAJA CON 12 TABLETAS', '500 MILIGRAMOS', NULL, 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('628', 'CLORANFENICOL OFTALMICO', NULL, 'FRASCO', 'medicamento', 'GENERICO', 'FRASCO GOTERO CON 15 MILILITROS', '5 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('629', 'PARACETAMOL', NULL, 'CAJA', 'medicamento', 'BROLICEN', 'CAJA CON 12 TABLETAS', '500 MILIGRAMOS', NULL, 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('630', 'CLORODIAZEPOXIDO + CLORPIRAMINA', NULL, 'CAJA', 'medicamento', 'GENERICO', 'EN CAJA CON 25 TABLETAS', 'MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('631', 'CLOPIDOGREL', NULL, 'CAJA', 'medicamento', 'AVAPENA', 'CAJA CON 5 AMPOLLETAS', '20 MILIGRAMOS', NULL, 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('632', 'LOPEAMIDA', NULL, 'CAJA', 'medicamento', 'GENERICO', 'CAJA CON 12 TABLETAS', 'MILIGRAMOS', NULL, 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('633', 'CMEFMAZONA', NULL, 'CAJA', 'medicamento', 'NOVOLEXIN', 'CAJA CON 10 CAPSULAS', '140 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('635', 'KETOPROFENO', NULL, 'CAJA', 'medicamento', 'GENERICO', 'CAJA CON 1 AMPOLLETA', '100 MILIGRAMOS', NULL, 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('637', 'ERITROMICINA', NULL, 'CAJA', 'medicamento', 'BIOTRIL', 'CAJA CON 20 COMPRIMIDOS', '500 MILIGRAMOS', NULL, 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('638', 'FOSFALUGEL', NULL, 'CAJA', 'medicamento', 'GENERICO', 'CAJA CON UN FRASCO', 'MILIGRAMOS', NULL, 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('641', 'GABAPENTINA', NULL, 'CAJA', 'medicamento', 'WERMY', 'CAJA CON 30 CAPSULAS', '300 MILIGRAMOS', NULL, 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('642', 'FUROSEMIDA', NULL, 'CAJA', 'medicamento', 'GEVAREM', 'CAJA CON 20 TABLETAS', '40 MILIGRAMOS', NULL, 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('643', 'GENTAMICINA', NULL, 'CAJA', 'medicamento', 'GENERICO', 'CAJA CON 5 AMOLLETAS', '160 MILIGRAMOS', NULL, 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('644', 'IBUPROFENO', NULL, 'CAJA', 'medicamento', 'ALGIDOL', 'CAJA CON 10 TABLETAS', '400 MILIGRAMOS', NULL, 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('645', 'INDOMETACINA', NULL, 'CAJA', 'medicamento', 'INDOMETIL', 'CAJA CON 20 CAPSULAS', '25 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('647', 'HIDROCORTI ACETATO', NULL, 'CAJA', 'medicamento', 'FLEBONADRE', 'CAJA CON UN UNGÜENTO', '500 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('648', 'ITRACONAZOL', NULL, 'CAJA', 'medicamento', 'ZITRASOL', 'CAJA CON 10 TABLETAS', '100 MILIGRAMOS', NULL, 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('649', 'KETOROLACO', NULL, 'CAJA', 'medicamento', 'GENERICO', 'CAJA CON 10 TABLETAS', '10 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('650', 'KETOPROFENO', NULL, 'CAJA', 'medicamento', 'GENERICO', 'CAJA R 3 AMPOLLETAS', '20 MILIGRAMOS', NULL, 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('651', 'TRAMADOL', NULL, 'CAJA', 'medicamento', 'GENERICO', 'CAJA CON 5 AMPOLLETAS', '100 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('653', 'MEBENDAZOL', NULL, 'CAJA', 'medicamento', 'EXBENZOL', 'CAJA CON 6 COMPRIMIDOS', '100 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('655', 'LORATADINA OFTALMICO', NULL, 'CAJA', 'medicamento', 'GENERICO', 'CAJA CON 20 TABLETAS', '10 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('656', 'AMBROXOL', NULL, 'CAJA', 'medicamento', 'OXOLVAN (GLYPHARD AMBROXOL)', 'CAJA CON 20 TABLETAS', '30 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('657', 'METRONIDAZOL', NULL, 'CAJA', 'medicamento', 'LAMBDA', 'CAJA CON 30 TABLETAS', '500 MILIGRAMOS', NULL, 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('659', 'NEOMICINA/POLIMIXINA B/ GRAMICIDINA', NULL, 'FRASCO', 'medicamento', 'GENERICO', 'GOTERO CON 7 MILILITROS', '1,750 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('660', 'TERBINAFINA', NULL, 'CAJA', 'medicamento', 'ANZTEC', 'CAJA CON TIL', '0,01', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('661', 'NORFLOXACINO', NULL, 'CAJA', 'medicamento', 'NORQUINOL/ROSILCAL', 'CAJA CON 20 TABLETAS', '400 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('662', 'FENAZOPIRIMIDIN/ TRIMETOPRIMA', NULL, 'CAJA', 'medicamento', 'BIOFERINA', 'CAJA CON 20 TABLETAS', '100 MILIGRAMOS', NULL, 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('663', 'PARACETAMOL SUSPENSIÓN', NULL, 'CAJA', 'medicamento', 'TOYTEM', 'CAJA CON 10 SOBRES', '500 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('665', 'NITAZOXANIDA', NULL, 'CAJA', 'medicamento', 'ROSANIL', 'CAJA CON 6 TABLETAS', '500 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('666', 'PAROXETINA', NULL, 'CAJA', 'medicamento', 'FINA-D LB', 'CAJA CON 20 TABLETAS', '10 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('667', 'CEFTRIAXONA', NULL, 'CAJA', 'medicamento', 'GENERICO', 'CAJA CON AK 1 GRAMO', 'oral', NULL, 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('668', 'PENTOXIFILINA', NULL, 'CAJA', 'medicamento', 'GENERICO', 'CAJA CON 30 TABLETAS', '400 MILIGRAMOS', NULL, 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('669', 'IVERMECTINA', NULL, 'CAJA', 'medicamento', 'VERIDEX', 'CAJA CON 2 TABLETAS', '6,0 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('670', 'OSELTAMIVIR', NULL, 'CAJA', 'medicamento', 'GENRICO', 'CAJA CON 10 TABLETAS', '75 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('671', 'LEVOFLOXACINA', NULL, 'CAJA', 'medicamento', 'LEVEREX', 'CAJA CON 7 TABLETAS', '500 MILIGRAMOS', NULL, 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('672', 'CLARITROMICINA', NULL, 'CAJA', 'medicamento', 'KLARIX', 'CAJA CON 14 TABLETAS', '500 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('687', 'PERMETRINA', NULL, 'FRASCO', 'medicamento', 'S5480-CO15', 'FRASCO CON 60 GRAMOS', 'oral', NULL, 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('688', 'GLIBENCLAMIDA', NULL, 'CAJA', 'medicamento', 'GENERICO', 'CAJA CON 60 TABLETAS', '5 MILIGRAMOS/500 MILIGRAMOS', NULL, 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('689', 'GLIBENCLAMIDA Y METEORMINA', NULL, 'CAJA', 'medicamento', 'GORYX', 'CAJA CON 50 TABLETAS', '5 MILIGRAMOS', NULL, 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('690', 'METFORMINA', NULL, 'CAJA', 'medicamento', 'GENERICO', 'CAJA CON 30 TABLETAS', '850 MILIGRAMOS', NULL, 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('691', 'LOSARTAN', NULL, 'CAJA', 'medicamento', 'PUNAB', 'CAJA CON 30 TABLETAS', '50 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('692', 'HIDROXICLOROQUINA', NULL, 'CAJA', 'medicamento', 'GENERICO', 'CAJA CON 25 COMPRIMIDOS', 'MILIGRAMOS', NULL, 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('693', 'INSULINA HUMANA DE ACCION RAPIDA', NULL, 'FRASCO', 'medicamento', 'GENERICO (INSULINA)', 'FRASCO DE 100 UI', 'oral', NULL, 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('694', 'NIFEDIPINO', NULL, 'CAJA', 'medicamento', 'GENERICO', 'CAJA CON 30 CAPSULAS', '500 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('695', 'CLORURO DE BENZALCONIO', NULL, 'CAJA', 'medicamento', 'GENERICO', 'BOLSA FLEX', '9%', NULL, 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('696', 'GLUCOSA', NULL, 'CAJA', 'medicamento', 'GENERICO', 'BOLSA FLEX -AL 5%', 'oral', NULL, 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('700', 'METOCLOPRAMIDA', NULL, 'CAJA', 'medicamento', 'GENERICO', 'CAJA CON 20 TABLETAS', '10 MILIGRAMOS', NULL, 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('703', 'CEFALEXINA', NULL, 'CAJA', 'medicamento', 'CEFALVER', 'CAJA CON 20 CAPSULAS', '500 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('704', 'IBUPROFENO EN SUSPENCION', NULL, 'CAJA', 'medicamento', 'BROUSAL', 'CAJA CON 1 FRASCO', '400 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('706', 'AMBROXOL/ CLOROFENILAM', NULL, 'CAJA', 'medicamento', 'FLUXOL', 'ENVASE CON 120 MILILITROS', '0,040/0,150 GRAMOS/ 100 MILIGRAMOS', NULL, 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('707', 'DICLOFENACO', NULL, 'CAJA', 'medicamento', 'GENERICO', 'CAJA CON 275 MILILITROS', 'MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('708', 'METAMIZOL SODICO', NULL, 'CAJA', 'medicamento', 'INDIGON', 'CAJA CON 1 FRASCO', '500 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('709', 'SERTRAUNA', NULL, 'CAJA', 'medicamento', 'GENERICO', 'CAJA CON 1 FRASCO', '50 MILIGRAMOS', NULL, 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('710', 'FENITOINA SODICA', NULL, 'CAJA', 'medicamento', 'FENIFFER-TE', 'CAJA CON 50 TABLETAS', '100 MILIGRAMOS', NULL, 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('711', 'CARBAMAZEPINA', NULL, 'CAJA', 'medicamento', 'GENERICO', 'CAJA CON 20 TABLETAS', '200 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('713', 'OLANZAPINA', NULL, 'TABLETA', 'medicamento', 'EFLECON', 'ENVASE CON 14 TABLETAS', '10 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('715', 'RISPERIDONA', NULL, 'CAJA', 'medicamento', 'GENERICO', 'CAJA CON 40 TABLETAS', '2 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('716', 'CLONAZEPAM', NULL, 'CAJA', 'medicamento', 'GENERICO', 'CAJA CON 30 TABLETAS', '2 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('675', 'HALOPERIDOL', NULL, 'CAJA', 'medicamento', 'GENERICO', 'CAJA CON 20 TABLETAS', '5 MILIGRAMOS', NULL, 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('677', 'VALPROATO DE MAGNESIO', NULL, 'CAJA', 'medicamento', 'GENERICO', 'CAJA CON 20 TABLETAS', '600 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('678', 'PAROXETINA', NULL, 'CAJA', 'medicamento', 'GENERICO', 'CAJA CON 10 TABLETAS', '20 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('681', 'AMOXICILINA', NULL, 'FRASCO', 'medicamento', 'VANDIX', 'ENVASE CON POLVO PARA 75 MILILITROS', '7,5 GRAMOS (500 MILIGRAMOS/5 MILILITROS)', NULL, 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('683', 'PARACETAMOL', NULL, 'FRASCO', 'medicamento', 'WAMINDEL', 'ENVASE CON 15 MILILITROS', '100 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('684', 'TRIMETOPRIMA/SUFAMETOXASOL SUSPENSIÓN', NULL, 'FRASCO', 'medicamento', 'GENERICO', 'FRASCO CON 120 MILILITROS CON VASO DOSIFICADOR', '40 MILIGRAMOS /200 MILIGRAMOS EN 5 MILILITROS', NULL, 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

INSERT INTO productos (clave, nombre, descripcion, unidad_medida, categoria, sustancia_activa, presentacion, concentracion, via_administracion, stock_minimo, stock_actual, requiere_receta, es_controlado, activo)
VALUES ('685', 'LORATADINA JARABE', NULL, 'FRASCO', 'medicamento', 'GENERICO', 'ENVASE CON 60 MILILITROS', '5 MILIGRAMOS', 'oral', 1, 0, FALSE, FALSE, TRUE)
ON CONFLICT (clave) DO NOTHING;

-- =============================================================================
-- VERIFICACIÓN POST-INSERCIÓN
-- =============================================================================

-- Contar productos insertados
SELECT COUNT(*) as total_productos FROM productos;

-- Mostrar los primeros 10 productos
SELECT id, clave, nombre, categoria, stock_actual 
FROM productos 
ORDER BY clave 
LIMIT 10;

-- Verificar que no hay claves duplicadas
SELECT clave, COUNT(*) as cantidad
FROM productos
GROUP BY clave
HAVING COUNT(*) > 1;
