# SQL para Módulo de Donaciones

**Fecha:** 2025-01  
**Issues relacionados:** DONACIONES-001

## Estado Actual

✅ **Las tablas ya existen en Supabase:**
- `donaciones` - Registro de donaciones recibidas
- `detalle_donaciones` - Productos en cada donación  
- `salidas_donaciones` - Entregas del almacén de donaciones
- `productos_donacion` - **NUEVO: Catálogo independiente de productos de donaciones**

**NO es necesario crear las tablas existentes.**

---

## IMPORTANTE: Catálogo Independiente de Productos de Donaciones

Las donaciones ahora usan un **catálogo completamente separado** del catálogo principal de productos.
Esto significa:
- Las donaciones pueden tener productos con **claves y nombres diferentes** al catálogo ordinario
- El inventario de donaciones es un **almacén separado** que NO se mezcla con el inventario principal
- NO se suman, dividen ni afectan los datos del inventario principal

### Crear tabla productos_donacion (EJECUTAR EN SUPABASE)

```sql
-- ============================================
-- CATÁLOGO INDEPENDIENTE DE PRODUCTOS DE DONACIONES
-- Ejecutar en: Supabase SQL Editor
-- Fecha: 2025-01
-- ============================================

-- Tabla de catálogo de productos exclusivo para donaciones
CREATE TABLE IF NOT EXISTS productos_donacion (
    id SERIAL PRIMARY KEY,
    clave VARCHAR(50) UNIQUE NOT NULL,
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT,
    unidad_medida VARCHAR(50) DEFAULT 'PIEZA',
    presentacion VARCHAR(100),
    activo BOOLEAN DEFAULT TRUE,
    notas TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_productos_donacion_clave ON productos_donacion(clave);
CREATE INDEX IF NOT EXISTS idx_productos_donacion_nombre ON productos_donacion(nombre);
CREATE INDEX IF NOT EXISTS idx_productos_donacion_activo ON productos_donacion(activo);

-- Trigger para actualizar updated_at
CREATE OR REPLACE FUNCTION update_productos_donacion_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_productos_donacion_updated_at ON productos_donacion;
CREATE TRIGGER trg_productos_donacion_updated_at
    BEFORE UPDATE ON productos_donacion
    FOR EACH ROW
    EXECUTE FUNCTION update_productos_donacion_updated_at();

COMMENT ON TABLE productos_donacion IS 'Catálogo independiente de productos para donaciones - NO se mezcla con productos principales';


-- ============================================
-- MODIFICAR detalle_donaciones para soportar nuevo catálogo
-- ============================================

-- Agregar columna para nuevo catálogo (si no existe)
ALTER TABLE detalle_donaciones 
ADD COLUMN IF NOT EXISTS producto_donacion_id INTEGER REFERENCES productos_donacion(id) ON DELETE RESTRICT;

-- Hacer producto_id nullable (legacy)
ALTER TABLE detalle_donaciones 
ALTER COLUMN producto_id DROP NOT NULL;

-- Índice para nuevo catálogo
CREATE INDEX IF NOT EXISTS idx_detalle_donaciones_producto_donacion 
ON detalle_donaciones(producto_donacion_id);

COMMENT ON COLUMN detalle_donaciones.producto_donacion_id IS 'Referencia al catálogo independiente de productos de donaciones';
COMMENT ON COLUMN detalle_donaciones.producto_id IS 'Legacy - Referencia al catálogo principal (deprecated)';
```

---

## Si el Módulo de Donaciones muestra error:

### 1. Verificar que las tablas tienen datos accesibles

```sql
-- Verificar acceso a las tablas
SELECT COUNT(*) as total_donaciones FROM donaciones;
SELECT COUNT(*) as total_detalles FROM detalle_donaciones;
SELECT COUNT(*) as total_salidas FROM salidas_donaciones;
```

### 2. Verificar que los constraints son compatibles

```sql
-- Si hay problemas de constraints, quitar los que bloquean
-- (el modelo Django no necesita constraints de BD estrictos)
ALTER TABLE donaciones DROP CONSTRAINT IF EXISTS chk_donacion_estado_valido;
ALTER TABLE donaciones DROP CONSTRAINT IF EXISTS chk_donacion_tipo_valido;
ALTER TABLE detalle_donaciones DROP CONSTRAINT IF EXISTS chk_detalle_estado_valido;
```

### 3. Verificar permisos del usuario en Supabase

El usuario autenticado debe tener SELECT/INSERT/UPDATE/DELETE en estas tablas.

---

## Referencia de Esquema (para consulta)

Ejecutar en el **SQL Editor de Supabase**:

```sql
-- ============================================
-- MÓDULO DE DONACIONES: Tablas
-- Ejecutar en: Supabase SQL Editor
-- Fecha: 2025-01
-- ============================================

-- 1. Tabla principal: donaciones
CREATE TABLE IF NOT EXISTS donaciones (
    id SERIAL PRIMARY KEY,
    numero VARCHAR(50) UNIQUE NOT NULL,
    donante_nombre VARCHAR(255) NOT NULL,
    donante_tipo VARCHAR(50) DEFAULT 'otro',
    donante_rfc VARCHAR(20),
    donante_direccion TEXT,
    donante_contacto VARCHAR(100),
    fecha_donacion DATE NOT NULL,
    fecha_recepcion TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    centro_destino_id INTEGER REFERENCES centros(id) ON DELETE SET NULL,
    recibido_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    estado VARCHAR(30) DEFAULT 'pendiente' NOT NULL,
    notas TEXT,
    documento_donacion VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Constraints para donaciones (ignorar error si ya existen)
DO $$ BEGIN
    ALTER TABLE donaciones ADD CONSTRAINT chk_donacion_estado_valido 
    CHECK (estado IN ('pendiente', 'recibida', 'procesada', 'rechazada'));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE donaciones ADD CONSTRAINT chk_donacion_tipo_valido 
    CHECK (donante_tipo IN ('empresa', 'gobierno', 'ong', 'particular', 'otro'));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Índices para donaciones
CREATE INDEX IF NOT EXISTS idx_donaciones_estado ON donaciones(estado);
CREATE INDEX IF NOT EXISTS idx_donaciones_fecha ON donaciones(fecha_donacion);
CREATE INDEX IF NOT EXISTS idx_donaciones_donante ON donaciones(donante_nombre);
CREATE INDEX IF NOT EXISTS idx_donaciones_centro ON donaciones(centro_destino_id);

-- Trigger para actualizar updated_at
CREATE OR REPLACE FUNCTION update_donaciones_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_donaciones_updated_at ON donaciones;
CREATE TRIGGER trg_donaciones_updated_at
    BEFORE UPDATE ON donaciones
    FOR EACH ROW
    EXECUTE FUNCTION update_donaciones_updated_at();

COMMENT ON TABLE donaciones IS 'Registro de donaciones de medicamentos recibidas';


-- 2. Tabla detalle_donaciones (productos en cada donación)
CREATE TABLE IF NOT EXISTS detalle_donaciones (
    id SERIAL PRIMARY KEY,
    donacion_id INTEGER NOT NULL REFERENCES donaciones(id) ON DELETE CASCADE,
    producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE RESTRICT,
    numero_lote VARCHAR(100),
    cantidad INTEGER NOT NULL,
    cantidad_disponible INTEGER DEFAULT 0,
    fecha_caducidad DATE,
    estado_producto VARCHAR(50) DEFAULT 'bueno',
    notas TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Constraints para detalle_donaciones (ignorar error si ya existen)
DO $$ BEGIN
    ALTER TABLE detalle_donaciones ADD CONSTRAINT chk_detalle_cantidad_positiva 
    CHECK (cantidad > 0);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE detalle_donaciones ADD CONSTRAINT chk_detalle_disponible_no_negativo 
    CHECK (cantidad_disponible >= 0);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE detalle_donaciones ADD CONSTRAINT chk_detalle_estado_valido 
    CHECK (estado_producto IN ('bueno', 'regular', 'malo'));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Índices para detalle_donaciones
CREATE INDEX IF NOT EXISTS idx_detalle_donaciones_donacion ON detalle_donaciones(donacion_id);
CREATE INDEX IF NOT EXISTS idx_detalle_donaciones_producto ON detalle_donaciones(producto_id);
CREATE INDEX IF NOT EXISTS idx_detalle_donaciones_disponible ON detalle_donaciones(cantidad_disponible) 
WHERE cantidad_disponible > 0;

COMMENT ON TABLE detalle_donaciones IS 'Productos incluidos en cada donación - almacén separado';


-- 3. Tabla salidas_donaciones (entregas del almacén de donaciones)
CREATE TABLE IF NOT EXISTS salidas_donaciones (
    id SERIAL PRIMARY KEY,
    detalle_donacion_id INTEGER NOT NULL REFERENCES detalle_donaciones(id) ON DELETE RESTRICT,
    cantidad INTEGER NOT NULL,
    destinatario VARCHAR(255) NOT NULL,
    motivo TEXT,
    entregado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    fecha_entrega TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    notas TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Constraints para salidas_donaciones (ignorar error si ya existen)
DO $$ BEGIN
    ALTER TABLE salidas_donaciones ADD CONSTRAINT chk_salida_cantidad_positiva 
    CHECK (cantidad > 0);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Índices para salidas_donaciones
CREATE INDEX IF NOT EXISTS idx_salidas_donaciones_detalle ON salidas_donaciones(detalle_donacion_id);
CREATE INDEX IF NOT EXISTS idx_salidas_donaciones_fecha ON salidas_donaciones(fecha_entrega);
CREATE INDEX IF NOT EXISTS idx_salidas_donaciones_destinatario ON salidas_donaciones(destinatario);

COMMENT ON TABLE salidas_donaciones IS 'Registro de entregas del almacén de donaciones';
```

---

## Verificación post-migración

```sql
-- Verificar que las tablas existan
SELECT table_name 
FROM information_schema.tables 
WHERE table_name IN ('donaciones', 'detalle_donaciones', 'salidas_donaciones')
  AND table_schema = 'public';

-- Verificar constraints
SELECT tc.table_name, tc.constraint_name, tc.constraint_type
FROM information_schema.table_constraints tc
WHERE tc.table_name IN ('donaciones', 'detalle_donaciones', 'salidas_donaciones')
ORDER BY tc.table_name;
```

---

## Rollback (si es necesario)

```sql
-- ⚠️ PRECAUCIÓN: Esto eliminará TODOS los datos de donaciones
DROP TABLE IF EXISTS salidas_donaciones CASCADE;
DROP TABLE IF EXISTS detalle_donaciones CASCADE;
DROP TABLE IF EXISTS donaciones CASCADE;
DROP FUNCTION IF EXISTS update_donaciones_updated_at();
```

---

## RLS (Row Level Security) - Opcional

Si su proyecto usa RLS en Supabase, descomentar y ejecutar:

```sql
ALTER TABLE donaciones ENABLE ROW LEVEL SECURITY;
ALTER TABLE detalle_donaciones ENABLE ROW LEVEL SECURITY;
ALTER TABLE salidas_donaciones ENABLE ROW LEVEL SECURITY;

-- Todos pueden ver donaciones
CREATE POLICY "Todos pueden ver donaciones" ON donaciones 
    FOR SELECT USING (true);

-- Solo farmacia/admin pueden modificar
CREATE POLICY "Solo farmacia/admin pueden modificar donaciones" ON donaciones 
    FOR ALL USING (auth.role() IN ('admin', 'farmacia'));
```
