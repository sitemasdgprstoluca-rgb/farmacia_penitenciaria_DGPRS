-- Script de inserción de lotes para Supabase (CONSOLIDADO)
-- Generado: 2025-12-15 12:36:58
-- Total de lotes: 141
-- Nota: Lotes duplicados fueron consolidados sumando cantidades

-- IMPORTANTE: Los productos deben estar ya insertados en la tabla productos

-- Verificar productos existentes (opcional)
SELECT COUNT(*) as total_productos FROM productos;

-- =============================================================================
-- INSERCIÓN DE LOTES CONSOLIDADOS
-- =============================================================================

-- Lote: 18285 - Producto: 629 (Cant Total: 216)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '18285',
    p.id,
    216,
    216,
    '2025-11-18',
    '2026-10-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '629'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 19186 - Producto: 657 (Cant Total: 800)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '19186',
    p.id,
    800,
    800,
    '2025-09-15',
    '2026-12-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '657'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 19792 - Producto: 629 (Cant Total: 336)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '19792',
    p.id,
    336,
    336,
    '2025-11-18',
    '2027-01-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '629'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 20221 - Producto: 637 (Cant Total: 42)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '20221',
    p.id,
    42,
    42,
    '2025-11-18',
    '2027-02-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '637'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 21842 - Producto: 637 (Cant Total: 76)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '21842',
    p.id,
    76,
    76,
    '2025-11-18',
    '2027-08-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '637'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 22771 - Producto: 629 (Cant Total: 1232)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '22771',
    p.id,
    1232,
    1232,
    '2025-11-13',
    '2027-06-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '629'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 22772 - Producto: 629 (Cant Total: 1745)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '22772',
    p.id,
    1745,
    1745,
    '2025-11-18',
    '2027-06-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '629'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 22816 - Producto: 637 (Cant Total: 2538)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '22816',
    p.id,
    2538,
    2538,
    '2025-11-18',
    '2027-06-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '637'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 23037 - Producto: 642 (Cant Total: 236)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '23037',
    p.id,
    236,
    236,
    '2025-11-13',
    '2027-06-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '642'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 23482 - Producto: 642 (Cant Total: 234)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '23482',
    p.id,
    234,
    234,
    '2025-11-18',
    '2027-08-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '642'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 25135 - Producto: 633 (Cant Total: 1083)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '25135',
    p.id,
    1083,
    1083,
    '2025-11-13',
    '2028-06-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '633'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 25191 - Producto: 633 (Cant Total: 180)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '25191',
    p.id,
    180,
    180,
    '1900-01-13',
    '2028-08-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '633'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 25431 - Producto: 662 (Cant Total: 568)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '25431',
    p.id,
    568,
    568,
    '2025-11-13',
    '2027-10-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '662'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 25554 - Producto: 662 (Cant Total: 1232)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '25554',
    p.id,
    1232,
    1232,
    '2025-11-13',
    '2027-10-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '662'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 51770 - Producto: 711 (Cant Total: 499)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '51770',
    p.id,
    499,
    499,
    '2025-11-13',
    '2027-08-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '711'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 197075 - Producto: 630 (Cant Total: 800)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '197075',
    p.id,
    800,
    800,
    '2025-11-13',
    '2027-07-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '630'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 224085 - Producto: 645 (Cant Total: 2997)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '224085',
    p.id,
    2997,
    2997,
    '2025-11-13',
    '2027-08-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '645'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 247011 - Producto: 706 (Cant Total: 809)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '247011',
    p.id,
    809,
    809,
    '2025-09-15',
    '2026-11-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '706'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 250503 - Producto: 706 (Cant Total: 691)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '250503',
    p.id,
    691,
    691,
    '2025-11-13',
    '2027-02-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '706'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 250595 - Producto: 619 (Cant Total: 2304)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '250595',
    p.id,
    2304,
    2304,
    '2025-09-15',
    '2027-05-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '619'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 250665 - Producto: 641 (Cant Total: 690)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '250665',
    p.id,
    690,
    690,
    '2025-11-13',
    '2027-06-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '641'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 250770 - Producto: 704 (Cant Total: 30)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '250770',
    p.id,
    30,
    30,
    '2025-11-18',
    '2027-04-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '704'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 250800 - Producto: 619 (Cant Total: 1736)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '250800',
    p.id,
    1736,
    1736,
    '2025-11-13',
    '2027-07-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '619'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 250840 - Producto: 691 (Cant Total: 3000)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '250840',
    p.id,
    3000,
    3000,
    '2025-11-13',
    '2027-07-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '691'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 251009 - Producto: 692 (Cant Total: 220)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '251009',
    p.id,
    220,
    220,
    '2025-09-15',
    '2027-03-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '692'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 251010 - Producto: 692 (Cant Total: 480)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '251010',
    p.id,
    480,
    480,
    '2025-09-15',
    '2027-03-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '692'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 251026 - Producto: 669 (Cant Total: 1415)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '251026',
    p.id,
    1415,
    1415,
    '2025-09-15',
    '2027-02-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '669'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 251143 - Producto: 704 (Cant Total: 895)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '251143',
    p.id,
    895,
    895,
    '2025-11-13',
    '2027-06-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '704'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 251195 - Producto: 703 (Cant Total: 1152)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '251195',
    p.id,
    1152,
    1152,
    '2025-11-13',
    '2028-03-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '703'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 251208 - Producto: 703 (Cant Total: 432)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '251208',
    p.id,
    432,
    432,
    '2025-11-13',
    '2028-03-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '703'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 251808 - Producto: 644 (Cant Total: 2000)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '251808',
    p.id,
    2000,
    2000,
    '2025-11-13',
    '2027-08-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '644'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 251920 - Producto: 669 (Cant Total: 1085)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '251920',
    p.id,
    1085,
    1085,
    '2025-11-13',
    '2027-04-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '669'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 253244 - Producto: 672 (Cant Total: 2060)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '253244',
    p.id,
    2060,
    2060,
    '2025-11-18',
    '2027-06-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '672'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 254005 - Producto: 672 (Cant Total: 240)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '254005',
    p.id,
    240,
    240,
    '2025-11-13',
    '2027-07-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '672'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 254541 - Producto: 624 (Cant Total: 400)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '254541',
    p.id,
    400,
    400,
    '2025-11-13',
    '2027-08-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '624'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 427871 - Producto: 666 (Cant Total: 85)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '427871',
    p.id,
    85,
    85,
    '2025-11-18',
    '2026-10-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '666'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 430279 - Producto: 666 (Cant Total: 86)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '430279',
    p.id,
    86,
    86,
    '2025-11-13',
    '2027-01-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '666'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 432546 - Producto: 666 (Cant Total: 108)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '432546',
    p.id,
    108,
    108,
    '2025-11-18',
    '2027-04-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '666'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 730015 - Producto: 684 (Cant Total: 20)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '730015',
    p.id,
    20,
    20,
    '2025-11-13',
    '2027-05-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '684'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 2502736 - Producto: 649 (Cant Total: 1500)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '2502736',
    p.id,
    1500,
    1500,
    '2025-09-15',
    '2027-02-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '649'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 2503182 - Producto: 647 (Cant Total: 600)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '2503182',
    p.id,
    600,
    600,
    '2025-11-13',
    '2027-03-19',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '647'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 2503202 - Producto: 690 (Cant Total: 450)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '2503202',
    p.id,
    450,
    450,
    '2025-09-15',
    '2027-03-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '690'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 2506136 - Producto: 670 (Cant Total: 88)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '2506136',
    p.id,
    88,
    88,
    '2025-11-18',
    '2027-06-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '670'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 2506139 - Producto: 670 (Cant Total: 409)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '2506139',
    p.id,
    409,
    409,
    '2025-11-13',
    '2027-06-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '670'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 2506185 - Producto: 707 (Cant Total: 250)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '2506185',
    p.id,
    250,
    250,
    '2025-11-13',
    '2027-06-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '707'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 2508032 - Producto: 695 (Cant Total: 480)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '2508032',
    p.id,
    480,
    480,
    '2025-11-13',
    '2027-08-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '695'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 2508950 - Producto: 649 (Cant Total: 1000)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '2508950',
    p.id,
    1000,
    1000,
    '2025-11-13',
    '2027-08-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '649'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 3630725 - Producto: 715 (Cant Total: 1500)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '3630725',
    p.id,
    1500,
    1500,
    '2025-11-13',
    '2027-07-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '715'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 3930725 - Producto: 716 (Cant Total: 50)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '3930725',
    p.id,
    50,
    50,
    '2025-11-13',
    '2027-07-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '716'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 5040514 - Producto: 663 (Cant Total: 859)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '5040514',
    p.id,
    859,
    859,
    '2025-09-15',
    '2027-05-02',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '663'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 5040554 - Producto: 632 (Cant Total: 1014)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '5040554',
    p.id,
    1014,
    1014,
    '2025-09-15',
    '2027-04-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '632'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 5040594 - Producto: 663 (Cant Total: 941)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '5040594',
    p.id,
    941,
    941,
    '2025-09-15',
    '2027-06-27',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '663'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 5050658 - Producto: 632 (Cant Total: 1386)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '5050658',
    p.id,
    1386,
    1386,
    '2025-09-15',
    '2027-06-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '632'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 5060791 - Producto: 663 (Cant Total: 372)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '5060791',
    p.id,
    372,
    372,
    '2025-11-13',
    '2027-07-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '663'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 24240630 - Producto: 616 (Cant Total: 1300)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '24240630',
    p.id,
    1300,
    1300,
    '2025-09-15',
    '2027-01-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '616'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 25020118 - Producto: 677 (Cant Total: 300)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '25020118',
    p.id,
    300,
    300,
    '2025-09-15',
    '2028-03-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '677'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 25061672 - Producto: 653 (Cant Total: 87)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '25061672',
    p.id,
    87,
    87,
    '2025-11-18',
    '2027-06-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '653'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 25071953 - Producto: 653 (Cant Total: 1380)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '25071953',
    p.id,
    1380,
    1380,
    '2025-11-13',
    '2027-07-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '653'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 25072052 - Producto: 615 (Cant Total: 84)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '25072052',
    p.id,
    84,
    84,
    '2025-11-13',
    '2027-07-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '615'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 25103022 - Producto: 615 (Cant Total: 216)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '25103022',
    p.id,
    216,
    216,
    '2025-11-13',
    '2027-10-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '615'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 25140952 - Producto: 671 (Cant Total: 2301)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '25140952',
    p.id,
    2301,
    2301,
    '2027-03-01',
    '2027-03-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '671'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 25141394 - Producto: 671 (Cant Total: 360)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '25141394',
    p.id,
    360,
    360,
    '2027-03-01',
    '2027-04-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '671'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 25141899 - Producto: 627 (Cant Total: 2119)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '25141899',
    p.id,
    2119,
    2119,
    '2025-11-13',
    '2027-06-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '627'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 0206B25 - Producto: 675 (Cant Total: 100)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '0206B25',
    p.id,
    100,
    100,
    '2025-11-18',
    '2027-02-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '675'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 25288P - Producto: 659 (Cant Total: 800)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '25288P',
    p.id,
    800,
    800,
    '2025-11-13',
    '2027-05-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '659'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 25J020 - Producto: 650 (Cant Total: 4000)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '25J020',
    p.id,
    4000,
    4000,
    '2025-09-15',
    '2027-06-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '650'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 25Y027 - Producto: 650 (Cant Total: 1984)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '25Y027',
    p.id,
    1984,
    1984,
    '2025-11-13',
    '2027-05-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '650'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 5BM291A - Producto: 625 (Cant Total: 500)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '5BM291A',
    p.id,
    500,
    500,
    '2025-11-13',
    '2027-02-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '625'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 5DN377B - Producto: 678 (Cant Total: 47)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '5DN377B',
    p.id,
    47,
    47,
    '2025-11-18',
    '2027-04-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '678'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 5E0882 - Producto: 661 (Cant Total: 60)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '5E0882',
    p.id,
    60,
    60,
    '2025-11-18',
    '2027-05-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '661'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 5E0885 - Producto: 661 (Cant Total: 840)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '5E0885',
    p.id,
    840,
    840,
    '2025-09-15',
    '2027-05-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '661'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 5F1054 - Producto: 688 (Cant Total: 480)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '5F1054',
    p.id,
    480,
    480,
    '2025-11-13',
    '2027-06-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '688'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 5G1252 - Producto: 661 (Cant Total: 280)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '5G1252',
    p.id,
    280,
    280,
    '2025-11-18',
    '2027-07-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '661'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 5GN194B - Producto: 694 (Cant Total: 400)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '5GN194B',
    p.id,
    400,
    400,
    '2025-09-15',
    '2027-07-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '694'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: 5JN212A - Producto: 694 (Cant Total: 200)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    '5JN212A',
    p.id,
    200,
    200,
    '2025-11-13',
    '2027-09-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '694'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: AJ25005 - Producto: 629 (Cant Total: 938)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'AJ25005',
    p.id,
    938,
    938,
    '2025-09-15',
    '2027-06-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '629'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: AS25006 - Producto: 708 (Cant Total: 550)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'AS25006',
    p.id,
    550,
    550,
    '2025-09-15',
    '2027-05-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '708'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: B247401 - Producto: 643 (Cant Total: 24)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'B247401',
    p.id,
    24,
    24,
    '2025-11-13',
    '2026-10-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '643'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: B24T515 - Producto: 626 (Cant Total: 184)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'B24T515',
    p.id,
    184,
    184,
    '2025-11-13',
    '2026-10-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '626'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: B25 J504 - Producto: 651 (Cant Total: 1320)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'B25 J504',
    p.id,
    1320,
    1320,
    '2025-09-15',
    '2027-06-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '651'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: B2507316 - Producto: 616 (Cant Total: 700)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'B2507316',
    p.id,
    700,
    700,
    '2025-11-13',
    '2027-07-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '616'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: B25F404 - Producto: 643 (Cant Total: 586)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'B25F404',
    p.id,
    586,
    586,
    '2025-11-13',
    '2027-02-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '643'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: B25J200 - Producto: 638 (Cant Total: 1360)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'B25J200',
    p.id,
    1360,
    1360,
    '2025-11-13',
    '2028-06-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '638'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: B25J403 - Producto: 643 (Cant Total: 1890)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'B25J403',
    p.id,
    1890,
    1890,
    '2025-09-15',
    '2027-06-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '643'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: B25J505 - Producto: 651 (Cant Total: 240)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'B25J505',
    p.id,
    240,
    240,
    '2025-11-13',
    '2027-06-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '651'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: B25M505 - Producto: 626 (Cant Total: 1315)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'B25M505',
    p.id,
    1315,
    1315,
    '2025-11-13',
    '2027-03-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '626'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: B25U316 - Producto: 707 (Cant Total: 1350)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'B25U316',
    p.id,
    1350,
    1350,
    '2025-09-15',
    '2027-07-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '707'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: B25Y500 - Producto: 651 (Cant Total: 40)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'B25Y500',
    p.id,
    40,
    40,
    '2025-11-18',
    '2027-05-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '651'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: B25Y506 - Producto: 638 (Cant Total: 140)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'B25Y506',
    p.id,
    140,
    140,
    '2025-11-13',
    '2028-05-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '638'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: BDL050 - Producto: 687 (Cant Total: 129)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'BDL050',
    p.id,
    129,
    129,
    '2025-09-15',
    '2027-11-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '687'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: BED046 - Producto: 687 (Cant Total: 21)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'BED046',
    p.id,
    21,
    21,
    '2025-09-15',
    '2028-04-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '687'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: BG25001 - Producto: 700 (Cant Total: 874)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'BG25001',
    p.id,
    874,
    874,
    '2025-09-15',
    '2027-04-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '700'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: BH25004 - Producto: 632 (Cant Total: 540)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'BH25004',
    p.id,
    540,
    540,
    '2025-11-13',
    '2027-07-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '632'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: CE2502 - Producto: 660 (Cant Total: 1000)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'CE2502',
    p.id,
    1000,
    1000,
    '2025-11-13',
    '2027-05-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '660'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: CH2501 - Producto: 660 (Cant Total: 2180)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'CH2501',
    p.id,
    2180,
    2180,
    '2025-09-15',
    '2027-05-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '660'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: I25Y073 - Producto: 621 (Cant Total: 1240)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'I25Y073',
    p.id,
    1240,
    1240,
    '2025-11-13',
    '2027-03-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '621'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: I25Y074 - Producto: 621 (Cant Total: 1260)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'I25Y074',
    p.id,
    1260,
    1260,
    '2025-11-13',
    '2027-03-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '621'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: J24N045 - Producto: 667 (Cant Total: 1699)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'J24N045',
    p.id,
    1699,
    1699,
    '2025-09-15',
    '2026-11-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '667'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: LC2515 - Producto: 685 (Cant Total: 17)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'LC2515',
    p.id,
    17,
    17,
    '2025-09-15',
    '2027-03-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '685'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: LE2502 - Producto: 685 (Cant Total: 3)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'LE2502',
    p.id,
    3,
    3,
    '2025-11-18',
    '2027-05-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '685'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: LG2501 - Producto: 683 (Cant Total: 20)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'LG2501',
    p.id,
    20,
    20,
    '2025-11-13',
    '2027-07-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '683'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: PP8061 - Producto: 631 (Cant Total: 87)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'PP8061',
    p.id,
    87,
    87,
    '2025-11-13',
    '2027-04-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '631'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: Q0325183 - Producto: 618 (Cant Total: 340)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'Q0325183',
    p.id,
    340,
    340,
    NULL,
    '2027-03-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '618'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: Q0325187 - Producto: 617 (Cant Total: 1470)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'Q0325187',
    p.id,
    1470,
    1470,
    '2025-09-15',
    '2021-04-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '617'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: Q0425226 - Producto: 617 (Cant Total: 882)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'Q0425226',
    p.id,
    882,
    882,
    '2025-09-15',
    '2027-04-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '617'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: Q0425257 - Producto: 617 (Cant Total: 148)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'Q0425257',
    p.id,
    148,
    148,
    '2025-09-15',
    '2027-04-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '617'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: Q0425289 - Producto: 618 (Cant Total: 380)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'Q0425289',
    p.id,
    380,
    380,
    NULL,
    '2027-04-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '618'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: Q0425297 - Producto: 618 (Cant Total: 1520)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'Q0425297',
    p.id,
    1520,
    1520,
    '2025-09-15',
    '2027-05-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '618'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: Q0525401 - Producto: 618 (Cant Total: 760)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'Q0525401',
    p.id,
    760,
    760,
    '2025-11-13',
    '2027-05-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '618'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: R2502360 - Producto: 665 (Cant Total: 2000)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'R2502360',
    p.id,
    2000,
    2000,
    '2025-11-13',
    '2027-03-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '665'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: R2505672 - Producto: 710 (Cant Total: 500)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'R2505672',
    p.id,
    500,
    500,
    '2025-09-15',
    '2027-05-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '710'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: RCN064 - Producto: 700 (Cant Total: 2700)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'RCN064',
    p.id,
    2700,
    2700,
    '2025-11-13',
    '2027-07-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '700'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: RFN045 - Producto: 713 (Cant Total: 3253)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'RFN045',
    p.id,
    3253,
    3253,
    '2025-11-13',
    '2027-06-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '713'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: S235739 - Producto: 693 (Cant Total: 28)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'S235739',
    p.id,
    28,
    28,
    '2025-09-08',
    '2026-09-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '693'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: S24A006 - Producto: 693 (Cant Total: 473)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'S24A006',
    p.id,
    473,
    473,
    '2025-09-08',
    '2027-04-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '693'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: S24N353 - Producto: 693 (Cant Total: 7)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'S24N353',
    p.id,
    7,
    7,
    '2025-11-18',
    '2027-11-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '693'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: S24T304 - Producto: 693 (Cant Total: 31)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'S24T304',
    p.id,
    31,
    31,
    '2025-11-18',
    '2027-10-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '693'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: S24Y035 - Producto: 693 (Cant Total: 1)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'S24Y035',
    p.id,
    1,
    1,
    '2025-11-18',
    '2027-05-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '693'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: S24Y045 - Producto: 693 (Cant Total: 132)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'S24Y045',
    p.id,
    132,
    132,
    '2025-09-08',
    '2027-05-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '693'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: S25F479 - Producto: 693 (Cant Total: 28)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'S25F479',
    p.id,
    28,
    28,
    '2025-11-18',
    '2028-02-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '693'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: S4559 - Producto: 681 (Cant Total: 20)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'S4559',
    p.id,
    20,
    20,
    '2025-11-13',
    '2026-09-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '681'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: SA2550 - Producto: 689 (Cant Total: 472)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'SA2550',
    p.id,
    472,
    472,
    '2025-09-15',
    '2027-01-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '689'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: SD25071 - Producto: 648 (Cant Total: 104)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'SD25071',
    p.id,
    104,
    104,
    '2025-11-13',
    '2027-04-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '648'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: SD2509 - Producto: 656 (Cant Total: 1200)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'SD2509',
    p.id,
    1200,
    1200,
    '2025-09-15',
    '2027-04-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '656'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: SD25101 - Producto: 648 (Cant Total: 16)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'SD25101',
    p.id,
    16,
    16,
    '2025-11-13',
    '2027-04-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '648'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: SD25104 - Producto: 648 (Cant Total: 165)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'SD25104',
    p.id,
    165,
    165,
    '2025-11-13',
    '2027-04-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '648'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: SDM3208 - Producto: 627 (Cant Total: 881)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'SDM3208',
    p.id,
    881,
    881,
    '2025-09-15',
    '2028-02-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '627'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: SF2527 - Producto: 689 (Cant Total: 328)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'SF2527',
    p.id,
    328,
    328,
    '2025-09-15',
    '2027-06-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '689'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: SG24300 - Producto: 648 (Cant Total: 1358)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'SG24300',
    p.id,
    1358,
    1358,
    '2025-09-15',
    '2026-07-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '648'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: SH2524 - Producto: 655 (Cant Total: 5000)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'SH2524',
    p.id,
    5000,
    5000,
    '2025-11-13',
    '2027-08-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '655'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: T0285 - Producto: 622 (Cant Total: 1750)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'T0285',
    p.id,
    1750,
    1750,
    '2025-09-15',
    '2027-05-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '622'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: T0509 - Producto: 622 (Cant Total: 249)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'T0509',
    p.id,
    249,
    249,
    '2025-11-13',
    '2027-05-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '622'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: U25A468 - Producto: 635 (Cant Total: 250)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'U25A468',
    p.id,
    250,
    250,
    '2025-11-13',
    '2027-04-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '635'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: U25J025 - Producto: 690 (Cant Total: 450)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'U25J025',
    p.id,
    450,
    450,
    '2025-11-13',
    '2027-06-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '690'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: U25J399 - Producto: 635 (Cant Total: 1260)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'U25J399',
    p.id,
    1260,
    1260,
    '2025-09-15',
    '2027-03-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '635'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: U25M374 - Producto: 635 (Cant Total: 90)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'U25M374',
    p.id,
    90,
    90,
    '2025-11-13',
    '2027-03-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '635'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: U25U090 - Producto: 668 (Cant Total: 500)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'U25U090',
    p.id,
    500,
    500,
    '2025-11-13',
    '2027-07-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '668'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: U25U469 - Producto: 709 (Cant Total: 700)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'U25U469',
    p.id,
    700,
    700,
    '2025-11-13',
    '2027-07-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '709'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: V25E20K - Producto: 695 (Cant Total: 120)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'V25E20K',
    p.id,
    120,
    120,
    '2025-11-13',
    '2027-04-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '695'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: V25E26A - Producto: 696 (Cant Total: 1500)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'V25E26A',
    p.id,
    1500,
    1500,
    '2025-11-13',
    '2027-04-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '696'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;

-- Lote: XC2549 - Producto: 628 (Cant Total: 500)
INSERT INTO lotes (
    numero_lote, producto_id, cantidad_inicial, cantidad_actual,
    fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo
) 
SELECT
    'XC2549',
    p.id,
    500,
    500,
    '2025-11-13',
    '2027-04-01',
    0.0,
    '2025',
    'S/N',
    'FARMCIA',
    NULL,  -- centro_id (NULL = farmacia central)
    TRUE
FROM productos p
WHERE p.clave = '628'
ON CONFLICT (numero_lote, producto_id) DO NOTHING;


-- =============================================================================
-- VERIFICACIÓN POST-INSERCIÓN
-- =============================================================================

-- Contar lotes insertados
SELECT COUNT(*) as total_lotes FROM lotes;

-- Lotes por producto (top 10)
SELECT 
    p.clave,
    p.nombre,
    COUNT(l.id) as total_lotes,
    SUM(l.cantidad_actual) as stock_total
FROM productos p
LEFT JOIN lotes l ON p.id = l.producto_id
GROUP BY p.id, p.clave, p.nombre
ORDER BY total_lotes DESC
LIMIT 10;

-- Verificar lotes próximos a caducar (6 meses)
SELECT 
    l.numero_lote,
    p.clave,
    p.nombre,
    l.fecha_caducidad,
    l.cantidad_actual
FROM lotes l
JOIN productos p ON l.producto_id = p.id
WHERE l.fecha_caducidad <= CURRENT_DATE + INTERVAL '6 months'
AND l.cantidad_actual > 0
ORDER BY l.fecha_caducidad
LIMIT 20;