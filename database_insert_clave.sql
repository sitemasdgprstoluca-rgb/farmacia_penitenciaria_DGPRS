-- ══════════════════════════════════════════════════════════════════════════════
-- INSERCIÓN DE PRODUCTOS Y LOTES - FARMACIA PENITENCIARIA
-- Ejecutar en Supabase SQL Editor DESPUÉS de la migración (database_migration_clave.sql)
-- Fecha: 2025-12-08
-- ══════════════════════════════════════════════════════════════════════════════

-- NOTA: Ejecutar PRIMERO: database_migration_clave.sql para renombrar codigo_barras → clave
-- Los productos se insertan primero, luego los lotes
-- centro_id = 1 corresponde al Almacén Central

-- ══════════════════════════════════════════════════════════════════════════════
-- PASO 1: INSERTAR PRODUCTOS (ON CONFLICT para evitar duplicados)
-- ══════════════════════════════════════════════════════════════════════════════

INSERT INTO productos (clave, nombre, presentacion, concentracion, categoria, unidad_medida, stock_minimo, activo, created_at, updated_at)
VALUES
-- Fila 1-10
('ATP', 'ATORVASTATINA', 'CAJA CON 10 TABLETAS', '40MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('ATFD01', 'ATORVASTATINA CALCICA', 'CAJA CON 10 TABLETAS', '10MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('ACP', 'ACICLOVIR (CLAV.ABURATO DE POTASIO)', 'CAJA CON 8 TABLETAS', '200MG/28', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('ACPD01', 'ACICLOVIR (CLAVALUNATO DE POTASIO)', 'CAJA CON 8 TABLETAS', '500MG/125', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('ANFIB', 'ANFIBULINA', 'TABLETAS', NULL, 'medicamento', 'caja', 10, true, NOW(), NOW()),
('AMIK1', 'AMIKACINA', 'SOLUCION INYECTABLE', '500MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('AMIK2', 'AMIKACINA', 'TABLETAS/AMPOLLETAS', '100MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('AMP1', 'AMPICILINA', 'CAJA CON 20 CAPSULAS', '500MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('AMP2', 'AMPICILINA', 'TABLETAS/AMPOLLETAS', NULL, 'medicamento', 'caja', 10, true, NOW(), NOW()),
('AMPT', 'AMPITILINA', 'CAJA CON 20 CAPSULAS', '500MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),

-- Fila 11-20
('AMPTS', 'AMPITILINA (SOBRES/FRASCOS)', 'TABLETAS/AMPOLLETAS', NULL, 'medicamento', 'caja', 10, true, NOW(), NOW()),
('AZIT', 'AZITROMICINA', 'CAJA CON 3 TABLETAS', '500MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('BRUZ', 'BRUZSALTINA POLYVALEADA', 'TABLETAS/AMPOLLETAS', NULL, 'medicamento', 'caja', 10, true, NOW(), NOW()),
('BENZ1', 'BENZATINATO', 'FRASCO AMPULA', '1200', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('BENDZ', 'BENZONATATO', 'CAJA CON 20 PERLAS', '100MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('BETAH', 'BETAHISTINA', 'CAJA CON 30 TABLETAS', '24MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),

-- Medicamentos con B
('BUTB', 'BUTILHIOSINA METAMIZOL', 'CAJA CON 10 TABLETAS', '10MG/250MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('CARBS', 'CARBOCISTEINA', 'JARABE ADULTO', '250MG', 'medicamento', 'frasco', 10, true, NOW(), NOW()),

-- Medicamentos con C
('CAPT', 'CAPTOPRIL', 'CAJA CON 30 TABLETAS', '25MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('CEFT1', 'CEFTRIAXONA', 'SOL INYECTABLE', '1G', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('CEFT500', 'CEFTRIAXONA', 'SOL INYECTABLE', '500MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('CIPR', 'CIPROFLOXACINO', 'TABLETAS/AMPOLLETAS', '500MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('CIPRO2', 'CIPROFLOXACINO', 'TABLETAS/AMPOLLETAS', '250MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('CIPROFT', 'CIPROFLOXACINO OFTALMICO', 'TABLETAS/AMPOLLETAS', '3MG/ML', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('CLAV', 'CLAVULANATO', 'TABLETAS', NULL, 'medicamento', 'caja', 10, true, NOW(), NOW()),
('CLARH', 'CLARITROMICINA (2 OTC VIB)', 'CAJA CON 10 CAPSULAS', '500MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('CLRZ', 'CLARITROMICINA', 'CAJA CON 10 CAPSULAS', '250MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('CLIND', 'CLINDAMICINA', 'SOL INYECTABLE', '300MG/2ML', 'medicamento', 'caja', 10, true, NOW(), NOW()),

-- Medicamentos con C (continuación)
('CLORF', 'CLORFENAMINA', 'CAJA CON 20 TABLETAS', '4MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('CLORF2', 'CLORFENAMINA COMPUESTA', 'TABLETAS/AMPOLLETAS', NULL, 'medicamento', 'caja', 10, true, NOW(), NOW()),
('CLOTR', 'CLOTRIMAZOL', 'CREMA', '1%', 'medicamento', 'tubo', 10, true, NOW(), NOW()),
('CLOTR2', 'CLOTRIMAZOL', 'OVULOS', '100MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('CLORP', 'CLORPROMAZINA', 'TABLETAS', '25MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('CPLX', 'COMPLEJO B', 'TABLETAS', NULL, 'medicamento', 'caja', 10, true, NOW(), NOW()),
('CPLXJ', 'COMPLEJO B JARABE', 'JARABE', NULL, 'medicamento', 'frasco', 10, true, NOW(), NOW()),

-- Medicamentos con D
('DIAZ', 'DIAZEPAM', 'TABLETAS', '10MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('DICL1', 'DICLOFENACO', 'SOL INYECTABLE', '75MG/3ML', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('DICL2', 'DICLOFENACO', 'TABLETAS', '100MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('DICLG', 'DICLOFENACO GEL', 'GEL', '1%', 'medicamento', 'tubo', 10, true, NOW(), NOW()),
('DIFEN', 'DIFENIDOL', 'TABLETAS', '25MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('DIGOX', 'DIGOXINA', 'TABLETAS', '0.25MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('DIMEN', 'DIMENHIDRINATO', 'TABLETAS', '50MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),

-- Medicamentos con D (continuación)
('DOXIC', 'DOXICICLINA', 'CAPSULAS', '100MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('DEXT4', 'DEXTROMETORFANO', 'JARABE', '15MG/5ML', 'medicamento', 'frasco', 10, true, NOW(), NOW()),
('DEXT5', 'DEXTROSA 5%', 'SOLUCION', '1000ML', 'medicamento', 'bolsa', 10, true, NOW(), NOW()),
('DEXT10', 'DEXTROSA 10%', 'SOLUCION', '500ML', 'medicamento', 'bolsa', 10, true, NOW(), NOW()),
('DOXT', 'DOXILAMINA/PIRIDOXINA', 'TABLETAS', '10MG/10MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),

-- Medicamentos con E
('ENAL', 'ENALAPRIL', 'TABLETAS', '10MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('ERIT', 'ERITROMICINA', 'CAPSULAS', '500MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('ESPIR', 'ESPIRONOLACTONA', 'TABLETAS', '25MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),

-- Medicamentos con F
('FEN1', 'FENITOINA', 'TABLETAS', '100MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('FLUCON', 'FLUCONAZOL', 'CAPSULAS', '150MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('FLUOX', 'FLUOXETINA', 'CAPSULAS', '20MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('FUROS', 'FUROSEMIDA', 'TABLETAS', '40MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),

-- Medicamentos con G
('GABA', 'GABAPENTINA', 'CAPSULAS', '300MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('GENTA', 'GENTAMICINA', 'SOL INYECTABLE', '80MG/2ML', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('GLIB', 'GLIBENCLAMIDA', 'TABLETAS', '5MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('GLUC', 'GLUCOSAMINA', 'TABLETAS', '1500MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),

-- Medicamentos con H
('HALOP', 'HALOPERIDOL', 'TABLETAS', '5MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('HIDRO', 'HIDROCLOROTIAZIDA', 'TABLETAS', '25MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('HIDROC', 'HIDROCORTISONA', 'CREMA', '1%', 'medicamento', 'tubo', 10, true, NOW(), NOW()),

-- Medicamentos con I
('IBUP4', 'IBUPROFENO', 'TABLETAS', '400MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('IBUP8', 'IBUPROFENO', 'TABLETAS', '800MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('IMIP', 'IMIPRAMINA', 'TABLETAS', '25MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('INDOME', 'INDOMETACINA', 'CAPSULAS', '25MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('INSUL', 'INSULINA NPH', 'SUSPENSION INYECTABLE', '100UI/ML', 'medicamento', 'frasco', 10, true, NOW(), NOW()),
('ISOSB', 'ISOSORBIDA', 'TABLETAS', '10MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),

-- Medicamentos con K
('KETO', 'KETOCONAZOL', 'TABLETAS', '200MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('KETOCR', 'KETOCONAZOL CREMA', 'CREMA', '2%', 'medicamento', 'tubo', 10, true, NOW(), NOW()),
('KETOR', 'KETOROLACO', 'TABLETAS', '10MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('KETORI', 'KETOROLACO INYECTABLE', 'SOL INYECTABLE', '30MG/ML', 'medicamento', 'caja', 10, true, NOW(), NOW()),

-- Medicamentos con L
('LACTU', 'LACTULOSA', 'JARABE', '66.7G/100ML', 'medicamento', 'frasco', 10, true, NOW(), NOW()),
('LEVOF', 'LEVOFLOXACINO', 'TABLETAS', '500MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('LIDOC', 'LIDOCAINA', 'SOL INYECTABLE', '2%', 'medicamento', 'frasco', 10, true, NOW(), NOW()),
('LORAT', 'LORATADINA', 'TABLETAS', '10MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('LOSAR', 'LOSARTAN', 'TABLETAS', '50MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),

-- Medicamentos con M
('MAGAL', 'MAGALDRATO/SIMETICONA', 'SUSPENSION', '800MG/40MG', 'medicamento', 'frasco', 10, true, NOW(), NOW()),
('MEBEND', 'MEBENDAZOL', 'TABLETAS', '100MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('MELOX', 'MELOXICAM', 'TABLETAS', '15MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('METAM', 'METAMIZOL', 'TABLETAS', '500MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('METAMJ', 'METAMIZOL JARABE', 'JARABE', '500MG/5ML', 'medicamento', 'frasco', 10, true, NOW(), NOW()),
('METF', 'METFORMINA', 'TABLETAS', '850MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('METOC', 'METOCLOPRAMIDA', 'TABLETAS', '10MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('METOP', 'METOPROLOL', 'TABLETAS', '100MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('METRO', 'METRONIDAZOL', 'TABLETAS', '500MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('METROO', 'METRONIDAZOL OVULOS', 'OVULOS', '500MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('MICONA', 'MICONAZOL', 'CREMA', '2%', 'medicamento', 'tubo', 10, true, NOW(), NOW()),

-- Medicamentos con N
('NAFAZ', 'NAFAZOLINA', 'GOTAS NASALES', '0.1%', 'medicamento', 'frasco', 10, true, NOW(), NOW()),
('NAPRO', 'NAPROXENO', 'TABLETAS', '250MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('NIFED', 'NIFEDIPINO', 'TABLETAS', '10MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('NIMESUL', 'NIMESULIDA', 'TABLETAS', '100MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('NIST', 'NISTATINA', 'SUSPENSION', '100,000UI/ML', 'medicamento', 'frasco', 10, true, NOW(), NOW()),
('NITR', 'NITROFURANTOINA', 'CAPSULAS', '100MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('NORFLOX', 'NORFLOXACINO', 'TABLETAS', '400MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),

-- Medicamentos con O
('OMEP', 'OMEPRAZOL', 'CAPSULAS', '20MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('ONDANS', 'ONDANSETRON', 'TABLETAS', '8MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),

-- Medicamentos con P
('PANTO', 'PANTOPRAZOL', 'TABLETAS', '40MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('PARAC', 'PARACETAMOL', 'TABLETAS', '500MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('PARACJ', 'PARACETAMOL JARABE', 'JARABE', '120MG/5ML', 'medicamento', 'frasco', 10, true, NOW(), NOW()),
('PARACS', 'PARACETAMOL SUPOSITORIOS', 'SUPOSITORIOS', '300MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('PENIC', 'PENICILINA PROCAINICA', 'SOL INYECTABLE', '400,000UI', 'medicamento', 'frasco', 10, true, NOW(), NOW()),
('PIRAN', 'PIRANTEL', 'SUSPENSION', '250MG/5ML', 'medicamento', 'frasco', 10, true, NOW(), NOW()),
('PIROX', 'PIROXICAM', 'CAPSULAS', '20MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('PRED', 'PREDNISONA', 'TABLETAS', '5MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('PROPAN', 'PROPANOLOL', 'TABLETAS', '40MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),

-- Medicamentos con R
('RANIT', 'RANITIDINA', 'TABLETAS', '150MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('RIFAMP', 'RIFAMPICINA', 'CAPSULAS', '300MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('RISPER', 'RISPERIDONA', 'TABLETAS', '2MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),

-- Medicamentos con S
('SALBU', 'SALBUTAMOL', 'JARABE', '2MG/5ML', 'medicamento', 'frasco', 10, true, NOW(), NOW()),
('SALBI', 'SALBUTAMOL INHALADOR', 'INHALADOR', '100MCG', 'medicamento', 'pieza', 10, true, NOW(), NOW()),
('SERTR', 'SERTRALINA', 'TABLETAS', '50MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('SILDEN', 'SILDENAFIL', 'TABLETAS', '50MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('SIMVA', 'SIMVASTATINA', 'TABLETAS', '20MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('SOLFT', 'SOLUCION FISIOLOGICA', 'SOLUCION', '1000ML', 'medicamento', 'bolsa', 10, true, NOW(), NOW()),
('SOLHR', 'SOLUCION HARTMANN', 'SOLUCION', '1000ML', 'medicamento', 'bolsa', 10, true, NOW(), NOW()),
('SULFAM', 'SULFAMETOXAZOL/TRIMETOPRIMA', 'TABLETAS', '800MG/160MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),

-- Medicamentos con T
('TAMSU', 'TAMSULOSINA', 'CAPSULAS', '0.4MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('TETRA', 'TETRACICLINA', 'CAPSULAS', '500MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('TIAMIN', 'TIAMINA (VIT B1)', 'TABLETAS', '100MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('TIZANID', 'TIZANIDINA', 'TABLETAS', '4MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('TRAM', 'TRAMADOL', 'CAPSULAS', '50MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('TRAMI', 'TRAMADOL INYECTABLE', 'SOL INYECTABLE', '100MG/2ML', 'medicamento', 'caja', 10, true, NOW(), NOW()),

-- Medicamentos con V
('VALPR', 'VALPROATO DE MAGNESIO', 'TABLETAS', '500MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('VENLAF', 'VENLAFAXINA', 'CAPSULAS', '75MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('VERAP', 'VERAPAMILO', 'TABLETAS', '80MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('VITAE', 'VITAMINA E', 'CAPSULAS', '400UI', 'medicamento', 'caja', 10, true, NOW(), NOW()),

-- Material de Curación
('ALGOD', 'ALGODON', 'PAQUETE', '500G', 'material_curacion', 'paquete', 10, true, NOW(), NOW()),
('GASA', 'GASAS ESTERILES', 'PAQUETE', '10X10CM', 'material_curacion', 'paquete', 10, true, NOW(), NOW()),
('VENDA', 'VENDA ELASTICA', 'ROLLO', '10CMX5M', 'material_curacion', 'rollo', 10, true, NOW(), NOW()),
('VENDG', 'VENDA DE GASA', 'ROLLO', '10CMX5M', 'material_curacion', 'rollo', 10, true, NOW(), NOW()),
('JERING3', 'JERINGA 3ML', 'PIEZA', '3ML', 'material_curacion', 'pieza', 10, true, NOW(), NOW()),
('JERING5', 'JERINGA 5ML', 'PIEZA', '5ML', 'material_curacion', 'pieza', 10, true, NOW(), NOW()),
('JERING10', 'JERINGA 10ML', 'PIEZA', '10ML', 'material_curacion', 'pieza', 10, true, NOW(), NOW()),
('GUANT', 'GUANTES LATEX', 'CAJA', 'MEDIANO', 'material_curacion', 'caja', 10, true, NOW(), NOW()),
('CUBREB', 'CUBREBOCAS', 'CAJA', '50 PIEZAS', 'material_curacion', 'caja', 10, true, NOW(), NOW()),
('SUTURA', 'SUTURA SEDA', 'SOBRE', '3-0', 'material_curacion', 'sobre', 10, true, NOW(), NOW()),
('CINT', 'CINTA MICROPORE', 'ROLLO', '2.5CMX9M', 'material_curacion', 'rollo', 10, true, NOW(), NOW()),
('CLNA09', 'CLORURO DE SODIO 0.9%', 'SOLUCION', '1000ML', 'medicamento', 'bolsa', 10, true, NOW(), NOW()),
('CLNA45', 'CLORURO DE SODIO 0.45%', 'SOLUCION', '500ML', 'medicamento', 'bolsa', 10, true, NOW(), NOW()),

-- Productos adicionales
('AMPMAB', 'AMPOLLETA BARRIO DE CABALERO', 'AMPOLLETA', NULL, 'medicamento', 'ampolleta', 10, true, NOW(), NOW()),
('DIACEF', 'DIACEFICA SODICO DICLUMINA CON LIDOSINA', 'AMPOLLETAS', NULL, 'medicamento', 'ampolleta', 10, true, NOW(), NOW()),
('KETOR30', 'KETOROLACO TROMETAMINA', 'SOL INYECTABLE', '30MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('LIDOCEP', 'LIDOCAINA Y EPINEFRINA', 'SOL INYECTABLE', NULL, 'medicamento', 'caja', 10, true, NOW(), NOW()),
('ONDAN8', 'ONDANSETRON', 'SOL INYECTABLE', '8MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('TRAMIT', 'TRAMADOL Y PARACETAMOL', 'TABLETAS', '37.5MG/325MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('PARACIV', 'PARACETAMOL', 'SOL INYECTABLE', '10MG/ML', 'medicamento', 'frasco', 10, true, NOW(), NOW()),
('METROFLAG', 'METRONIDAZOL (FLAGENASA)', 'OVULOS', NULL, 'medicamento', 'caja', 10, true, NOW(), NOW()),
('NACLAUR', 'NACLOR AURINE', 'TABLETAS', NULL, 'medicamento', 'caja', 10, true, NOW(), NOW()),
('OXITOC', 'OXITOCINA', 'SOL INYECTABLE', '5UI/ML', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('DECLOPSA', 'DECLOPSA O AMETOCLOP', 'TABLETAS', NULL, 'medicamento', 'caja', 10, true, NOW(), NOW()),
('DECOPRESS', 'DECOPRESS O METOCLAPRAMIDA', 'SOL INYECTABLE', NULL, 'medicamento', 'caja', 10, true, NOW(), NOW()),
('CARBAMAZEP', 'CARBAMAZEPINA', 'TABLETAS', '200MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('CITICOL', 'CITICOLINA', 'SOL INYECTABLE', '500MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('DEXAM', 'DEXAMETASONA', 'SOL INYECTABLE', '8MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('DIPIR', 'DIPIRONA', 'TABLETAS', '500MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('DORZOL', 'DORZOLAMIDA', 'GOTAS OFTALMICAS', '2%', 'medicamento', 'frasco', 10, true, NOW(), NOW()),
('ERMF', 'ERITROMICINA OFTALMICA', 'UNGUENTO', '0.5%', 'medicamento', 'tubo', 10, true, NOW(), NOW()),
('GLUCOF', 'GLUCOSAMINA CON CONDROITINA', 'TABLETAS', '500MG/400MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('LAGRART', 'LAGRIMAS ARTIFICIALES', 'GOTAS', NULL, 'medicamento', 'frasco', 10, true, NOW(), NOW()),
('LEVOCET', 'LEVOCETIRIZINA', 'TABLETAS', '5MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('LOPERAMID', 'LOPERAMIDA', 'TABLETAS', '2MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('METOTREX', 'METOTREXATO', 'TABLETAS', '2.5MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('MISOPR', 'MISOPROSTOL', 'TABLETAS', '200MCG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('MULTIVIT', 'MULTIVITAMINICO', 'TABLETAS', NULL, 'medicamento', 'caja', 10, true, NOW(), NOW()),
('PENTOX', 'PENTOXIFILINA', 'TABLETAS', '400MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('PERIMETRINA', 'PERIMETRINA CONCENTRADA', 'LOCION', NULL, 'medicamento', 'frasco', 10, true, NOW(), NOW()),
('PRAZOS', 'PRAZOSINA', 'TABLETAS', '1MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('RABEPR', 'RABEPRAZOL', 'TABLETAS', '20MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('SACCHAR', 'SACCHAROMYCES BOULARDII', 'CAPSULAS', '250MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('SULFAS', 'SULFASALAZINA', 'TABLETAS', '500MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('TERBINAF', 'TERBINAFINA', 'TABLETAS', '250MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('TRIMEBU', 'TRIMEBUTINA', 'TABLETAS', '200MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),

-- SOLUCIONES Y OTROS
('SOLMIX', 'SOLUCION MIXTA', 'SOLUCION', '1000ML', 'medicamento', 'bolsa', 10, true, NOW(), NOW()),
('CLNA', 'CLORURO DE SODIO 0.9%', 'AMPOLLETA', '10ML', 'medicamento', 'ampolleta', 10, true, NOW(), NOW()),
('HIDROX1', 'HIDROXICINA', 'TABLETAS', '10MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('HIDROX2', 'HIDROXICINA', 'TABLETAS', '25MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('INYECTADORA', 'AGUA INYECTABLE', 'AMPOLLETAS', '10ML', 'medicamento', 'ampolleta', 10, true, NOW(), NOW()),

-- NALOXONA Y OTROS
('NALOX', 'NALOXONA', 'SOL INYECTABLE', '0.4MG/ML', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('NALBUFIN', 'NALBUFINA', 'SOL INYECTABLE', '10MG/ML', 'medicamento', 'caja', 10, true, NOW(), NOW()),

-- Medicamentos psiquiátricos
('CLONAZ', 'CLONAZEPAM', 'TABLETAS', '2MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('ALPRAZ', 'ALPRAZOLAM', 'TABLETAS', '0.5MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('LORAZE', 'LORAZEPAM', 'TABLETAS', '2MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('QUETIAP', 'QUETIAPINA', 'TABLETAS', '100MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('OLANZ', 'OLANZAPINA', 'TABLETAS', '10MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('LEVOMEP', 'LEVOMEPROMAZINA', 'TABLETAS', '25MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),

-- Antihipertensivos adicionales
('AMLOD', 'AMLODIPINO', 'TABLETAS', '5MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('TELMISAR', 'TELMISARTAN', 'TABLETAS', '40MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('IRBES', 'IRBESARTAN', 'TABLETAS', '150MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('PRAVAS', 'PRAVASTATINA', 'TABLETAS', '20MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('BEZAF', 'BEZAFIBRATO', 'TABLETAS', '200MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('ACICLO', 'ACICLOVIR', 'TABLETAS', '200MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('ACICLOCR', 'ACICLOVIR CREMA', 'CREMA', '5%', 'medicamento', 'tubo', 10, true, NOW(), NOW()),

-- Antiinflamatorios oftálmicos
('PREDNOFT', 'PREDNISOLONA OFTALMICA', 'GOTAS', '1%', 'medicamento', 'frasco', 10, true, NOW(), NOW()),
('TOBRAMOFT', 'TOBRAMICINA OFTALMICA', 'GOTAS', '0.3%', 'medicamento', 'frasco', 10, true, NOW(), NOW()),

-- Vitaminas y minerales
('VITB12', 'VITAMINA B12', 'SOL INYECTABLE', '1000MCG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('VITC', 'VITAMINA C', 'TABLETAS', '500MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('HIERRO', 'HIERRO', 'TABLETAS', '100MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('ACIDOF', 'ACIDO FOLICO', 'TABLETAS', '5MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('CALCIO', 'CALCIO', 'TABLETAS', '500MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('ZINC', 'ZINC', 'TABLETAS', '20MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),

-- Antiespasmódicos
('BUTILHIO', 'BUTILHIOSCINA', 'TABLETAS', '10MG', 'medicamento', 'caja', 10, true, NOW(), NOW()),
('BUTILHIOI', 'BUTILHIOSCINA INYECTABLE', 'SOL INYECTABLE', '20MG/ML', 'medicamento', 'caja', 10, true, NOW(), NOW())

ON CONFLICT (clave) DO UPDATE SET
    nombre = EXCLUDED.nombre,
    presentacion = EXCLUDED.presentacion,
    concentracion = EXCLUDED.concentracion,
    updated_at = NOW();

-- ══════════════════════════════════════════════════════════════════════════════
-- PASO 2: INSERTAR LOTES (todos en Almacén Central - centro_id = 1)
-- ══════════════════════════════════════════════════════════════════════════════

INSERT INTO lotes (numero_lote, producto_id, cantidad_inicial, cantidad_actual, fecha_caducidad, precio_unitario, numero_contrato, marca, centro_id, activo, created_at, updated_at)
SELECT 
    v.numero_lote,
    p.id as producto_id,
    v.cantidad as cantidad_inicial,
    v.cantidad as cantidad_actual,
    v.fecha_caducidad::date,
    0.00 as precio_unitario,
    v.numero_contrato,
    NULL as marca,
    1 as centro_id,
    true as activo,
    NOW() as created_at,
    NOW() as updated_at
FROM (VALUES
    ('ATP', 'SN480623', 944, '2027-02-01', 'LPAAPP2'),
    ('ATFD01', 'B23016', 1000, '2028-01-01', 'PANMD027'),
    ('ANFIB', '3AP0923', 148, '2027-02-01', 'LPAAPP2'),
    ('AMP1', 'S24007', 1800, '2027-06-01', 'PANMD027'),
    ('AMP2', '104019', 1300, '2026-03-01', NULL),
    ('AMPT', '22J4', 3670, '2028-06-01', 'PANMD027'),
    ('AZIT', 'SN470323', 2000, '2027-03-01', 'LPAAPP2'),
    ('BENZ1', 'L23L02', 500, '2027-05-01', 'LPAAPP2'),
    ('BENDZ', 'J23L54', 500, '2027-03-01', 'PANMD027'),
    ('BETAH', '23060-B', 500, '2026-11-01', 'PANMD027'),
    ('BUTB', 'HM20031', 700, '2027-09-01', 'LPAAPP2'),
    ('CARBS', 'C43108', 300, '2027-01-01', 'LPAAPP2'),
    ('CIPRO2', 'A9J005', 410, '2027-01-01', 'LPAAPP2'),
    ('CIPROFT', 'B22037', 65, '2027-03-01', 'LPAAPP2'),
    ('CLARH', '36JL0081', 100, '2028-01-01', 'PANMD027'),
    ('CLRZ', '35J8020', 300, '2027-09-01', 'PANMD027'),
    ('CLORF', 'SN31023', 1950, '2027-03-01', 'LPAAPP2'),
    ('CLOTR', 'RE23010', 350, '2026-10-01', 'LPAAPP2'),
    ('CLOTR2', '23J040', 150, '2027-03-01', 'LPAAPP2'),
    ('CPLX', 'MX23-01', 500, '2027-02-01', 'LPAAPP2'),
    ('CPLXJ', 'J23B-04', 200, '2026-11-01', 'LPAAPP2'),
    ('DICL1', 'L23D10', 2000, '2027-02-01', 'PANMD027'),
    ('DICL2', '23J002', 1000, '2027-08-01', 'PANMD027'),
    ('DICLG', 'G23K01', 200, '2027-05-01', 'LPAAPP2'),
    ('DIFEN', '23L006', 150, '2027-09-01', 'LPAAPP2'),
    ('DIMEN', 'DM23J01', 300, '2027-11-01', 'LPAAPP2'),
    ('ENAL', 'EN23K05', 500, '2028-02-01', 'PANMD027'),
    ('ERIT', 'ER23L04', 200, '2027-06-01', 'LPAAPP2'),
    ('FEN1', 'FN23K02', 300, '2027-09-01', 'PANMD027'),
    ('FLUCON', 'FL23J05', 600, '2028-03-01', 'PANMD027'),
    ('FLUOX', 'FX23K01', 400, '2027-11-01', 'LPAAPP2'),
    ('FUROS', 'FR23L03', 800, '2028-01-01', 'PANMD027'),
    ('GABA', 'GB23K04', 500, '2027-08-01', 'PANMD027'),
    ('GLIB', 'GL23L02', 600, '2028-02-01', 'PANMD027'),
    ('GLUC', 'GC23K01', 200, '2027-05-01', 'LPAAPP2'),
    ('HIDRO', 'HD23K05', 700, '2028-01-01', 'PANMD027'),
    ('HIDROC', 'HC23L01', 150, '2027-04-01', 'LPAAPP2'),
    ('IBUP4', 'IB23K02', 1500, '2028-03-01', 'PANMD027'),
    ('IBUP8', 'IB23L04', 800, '2027-09-01', 'PANMD027'),
    ('KETOR', 'KT23J06', 1200, '2028-01-01', 'PANMD027'),
    ('KETORI', 'KI23K03', 500, '2027-06-01', 'LPAAPP2'),
    ('LORAT', 'LR23K05', 800, '2028-02-01', 'PANMD027'),
    ('LOSAR', 'LS23L02', 1000, '2028-03-01', 'PANMD027'),
    ('METAM', 'MT23J08', 2000, '2028-01-01', 'PANMD027'),
    ('METAMJ', 'MJ23K04', 400, '2027-08-01', 'LPAAPP2'),
    ('METF', 'MF23L01', 1500, '2028-02-01', 'PANMD027'),
    ('METOC', 'MC23J05', 600, '2027-11-01', 'LPAAPP2'),
    ('METRO', 'MR23K03', 1000, '2028-01-01', 'PANMD027'),
    ('OMEP', 'OM23K06', 2500, '2028-03-01', 'PANMD027'),
    ('PARAC', 'PR23J04', 3000, '2028-02-01', 'PANMD027'),
    ('PARACJ', 'PJ23K02', 500, '2027-09-01', 'LPAAPP2'),
    ('RANIT', 'RN23L05', 800, '2028-01-01', 'PANMD027'),
    ('SOLFT', 'SF23K01', 500, '2027-12-01', 'LPAAPP2'),
    ('SOLHR', 'SH23J03', 300, '2027-11-01', 'LPAAPP2'),
    ('CLNA09', 'CL23K04', 600, '2028-01-01', 'PANMD027'),
    ('ALGOD', 'AL23L01', 100, '2028-06-01', 'LPAAPP2'),
    ('GASA', 'GS23K02', 500, '2028-03-01', 'LPAAPP2'),
    ('VENDA', 'VE23J04', 200, '2027-12-01', 'LPAAPP2'),
    ('JERING3', 'JR23K05', 1000, '2028-06-01', 'PANMD027'),
    ('JERING5', 'JR23L06', 800, '2028-06-01', 'PANMD027'),
    ('GUANT', 'GU23J01', 50, '2027-09-01', 'LPAAPP2'),
    ('CUBREB', 'CB23K03', 100, '2028-01-01', 'LPAAPP2'),
    ('AMLOD', 'AM23K07', 600, '2028-02-01', 'PANMD027'),
    ('CLONAZ', 'CZ23L02', 300, '2027-08-01', 'LPAAPP2'),
    ('ALPRAZ', 'AZ23J04', 200, '2027-09-01', 'LPAAPP2'),
    ('QUETIAP', 'QT23K01', 150, '2027-11-01', 'PANMD027'),
    ('ACIDOF', 'AF23L05', 1000, '2028-03-01', 'PANMD027'),
    ('VITB12', 'VB23K03', 400, '2027-10-01', 'LPAAPP2'),
    ('VITC', 'VC23J02', 800, '2028-01-01', 'PANMD027'),
    ('HIERRO', 'HI23K04', 500, '2027-12-01', 'PANMD027'),
    ('BUTILHIO', 'BH23L01', 600, '2028-02-01', 'PANMD027')
) AS v(clave, numero_lote, cantidad, fecha_caducidad, numero_contrato)
JOIN productos p ON p.clave = v.clave
ON CONFLICT ON CONSTRAINT lote_producto_unique DO UPDATE SET
    cantidad_inicial = EXCLUDED.cantidad_inicial,
    cantidad_actual = EXCLUDED.cantidad_actual,
    fecha_caducidad = EXCLUDED.fecha_caducidad,
    numero_contrato = EXCLUDED.numero_contrato,
    updated_at = NOW();

-- ══════════════════════════════════════════════════════════════════════════════
-- PASO 3: ACTUALIZAR STOCK_ACTUAL EN PRODUCTOS
-- ══════════════════════════════════════════════════════════════════════════════

UPDATE productos p
SET stock_actual = COALESCE((
    SELECT SUM(l.cantidad_actual)
    FROM lotes l
    WHERE l.producto_id = p.id AND l.activo = true
), 0),
updated_at = NOW();

-- ══════════════════════════════════════════════════════════════════════════════
-- VERIFICACIÓN
-- ══════════════════════════════════════════════════════════════════════════════

SELECT 'Productos insertados:' as info, COUNT(*) as total FROM productos;
SELECT 'Lotes insertados:' as info, COUNT(*) as total FROM lotes;
SELECT 'Productos con stock:' as info, COUNT(*) as total FROM productos WHERE stock_actual > 0;
