# SQL Migrations para Supabase

## Contexto

Este proyecto utiliza Django con `managed = False` en los modelos, lo que significa que Django no gestiona el esquema de la base de datos. Todas las migraciones deben ejecutarse manualmente en Supabase.

---

## Migración: Mejoras de Flujo (Sprint 3+)

**Fecha:** 2024-01  
**Issues relacionados:** MEJORA-FLUJO-3, MEJORA-FLUJO-5

### Descripción

Añade campos para:
1. **motivo_ajuste**: Permite documentar por qué se redujo la cantidad autorizada en una requisición
2. **subtipo_salida**: Clasifica el tipo de salida (receta, consumo_interno, merma, etc.)
3. **numero_expediente**: Almacena el expediente médico para salidas por receta

### SQL a ejecutar en Supabase

```sql
-- ============================================
-- MIGRACIÓN: Mejoras de Flujo de Negocio
-- Ejecutar en: Supabase SQL Editor
-- Autor: Sistema de Farmacia Penitenciaria
-- ============================================

-- 1. Campo para motivo de ajuste en detalles de requisición
-- Se utiliza cuando cantidad_autorizada < cantidad_solicitada
ALTER TABLE detalles_requisicion 
ADD COLUMN IF NOT EXISTS motivo_ajuste VARCHAR(255) NULL;

COMMENT ON COLUMN detalles_requisicion.motivo_ajuste IS 
  'Motivo obligatorio cuando cantidad_autorizada es menor a cantidad_solicitada';

-- 2. Subtipo de salida para clasificación de movimientos
ALTER TABLE movimientos 
ADD COLUMN IF NOT EXISTS subtipo_salida VARCHAR(30) NULL;

COMMENT ON COLUMN movimientos.subtipo_salida IS 
  'Clasificación de salidas: receta, consumo_interno, merma, caducidad, transferencia, otro';

-- 3. Número de expediente para trazabilidad de recetas
ALTER TABLE movimientos 
ADD COLUMN IF NOT EXISTS numero_expediente VARCHAR(50) NULL;

COMMENT ON COLUMN movimientos.numero_expediente IS 
  'Expediente médico del paciente. Obligatorio cuando subtipo_salida = receta';

-- 4. Índices para búsquedas eficientes
CREATE INDEX IF NOT EXISTS idx_movimientos_numero_expediente 
ON movimientos(numero_expediente) 
WHERE numero_expediente IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_movimientos_subtipo_salida 
ON movimientos(subtipo_salida) 
WHERE subtipo_salida IS NOT NULL;

-- 5. Constraint para validar subtipos válidos (opcional)
-- Descomenta si deseas validación a nivel de BD:
-- ALTER TABLE movimientos 
-- ADD CONSTRAINT chk_subtipo_salida_valido 
-- CHECK (subtipo_salida IS NULL OR subtipo_salida IN 
--   ('receta', 'consumo_interno', 'merma', 'caducidad', 'transferencia', 'otro'));
```

### Verificación post-migración

```sql
-- Verificar que las columnas existan
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name IN ('detalles_requisicion', 'movimientos')
  AND column_name IN ('motivo_ajuste', 'subtipo_salida', 'numero_expediente');

-- Verificar índices
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'movimientos' 
  AND indexname LIKE '%expediente%' OR indexname LIKE '%subtipo%';
```

### Rollback (si es necesario)

```sql
-- ⚠️ PRECAUCIÓN: Esto eliminará datos de estas columnas
DROP INDEX IF EXISTS idx_movimientos_numero_expediente;
DROP INDEX IF EXISTS idx_movimientos_subtipo_salida;
ALTER TABLE movimientos DROP COLUMN IF EXISTS numero_expediente;
ALTER TABLE movimientos DROP COLUMN IF EXISTS subtipo_salida;
ALTER TABLE detalles_requisicion DROP COLUMN IF EXISTS motivo_ajuste;
```

---

## Historial de Migraciones

| Fecha | Nombre | Descripción | Estado |
|-------|--------|-------------|--------|
| 2024-01 | Mejoras de Flujo | motivo_ajuste, subtipo_salida, numero_expediente | Pendiente |

---

## ISS-004 (audit14): Constraints Recomendados para Integridad

**Fecha:** 2025-12  
**Issues relacionados:** ISS-001, ISS-004, ISS-006

### Descripción

Dado que los modelos usan `managed = False`, las validaciones de integridad dependen 
de código Python. Se recomienda agregar estos constraints a nivel de BD para garantizar 
consistencia incluso ante operaciones directas o fallas de concurrencia.

### SQL Recomendado

```sql
-- ============================================
-- ISS-004: CONSTRAINTS DE INTEGRIDAD
-- Ejecutar en: Supabase SQL Editor
-- IMPORTANTE: Revisar datos existentes antes de aplicar
-- ============================================

-- ===========================================
-- 1. LOTES: Stock nunca negativo
-- ===========================================
ALTER TABLE lotes 
ADD CONSTRAINT chk_lote_cantidad_positiva 
CHECK (cantidad_actual >= 0);

ALTER TABLE lotes 
ADD CONSTRAINT chk_lote_cantidad_inicial_positiva 
CHECK (cantidad_inicial >= 0);

COMMENT ON CONSTRAINT chk_lote_cantidad_positiva ON lotes IS 
  'ISS-001: Evita stock negativo por operaciones concurrentes o directas';

-- ===========================================
-- 2. MOVIMIENTOS: Validaciones básicas
-- ===========================================
ALTER TABLE movimientos 
ADD CONSTRAINT chk_movimiento_cantidad_positiva 
CHECK (cantidad > 0);

ALTER TABLE movimientos 
ADD CONSTRAINT chk_movimiento_tipo_valido 
CHECK (tipo IN ('entrada', 'salida', 'transferencia', 'ajuste_positivo', 
                'ajuste_negativo', 'devolucion', 'merma', 'caducidad'));

COMMENT ON CONSTRAINT chk_movimiento_cantidad_positiva ON movimientos IS 
  'ISS-002: Cantidad siempre positiva, el tipo determina si suma o resta';

-- ===========================================
-- 3. REQUISICIONES: Estados válidos
-- ===========================================
ALTER TABLE requisiciones 
ADD CONSTRAINT chk_requisicion_estado_valido 
CHECK (estado IN (
  'borrador', 'pendiente_admin', 'pendiente_director', 
  'enviada', 'en_revision', 'autorizada', 'en_surtido', 
  'surtida', 'parcial', 'entregada', 'rechazada', 
  'devuelta', 'vencida', 'cancelada'
));

COMMENT ON CONSTRAINT chk_requisicion_estado_valido ON requisiciones IS 
  'ISS-003: Solo estados válidos de la máquina de estados';

-- ===========================================
-- 4. USUARIOS: Roles válidos
-- ===========================================
ALTER TABLE usuarios 
ADD CONSTRAINT chk_usuario_rol_valido 
CHECK (rol IN (
  'admin', 'admin_sistema', 'farmacia', 'vista',
  'medico', 'administrador_centro', 'director_centro', 
  'centro', 'usuario_centro', 'usuario_normal'
));

COMMENT ON CONSTRAINT chk_usuario_rol_valido ON usuarios IS 
  'ISS-001: Solo roles definidos en el sistema';

-- ===========================================
-- 5. ÍNDICES PARA CONCURRENCIA
-- ===========================================

-- Índice para bloqueos por lote (usado en select_for_update)
CREATE INDEX IF NOT EXISTS idx_lotes_pk_lock ON lotes(id);

-- Índice para búsqueda de movimientos por requisición
CREATE INDEX IF NOT EXISTS idx_movimientos_requisicion_tipo 
ON movimientos(requisicion_id, tipo) WHERE requisicion_id IS NOT NULL;

-- Índice para estado de requisiciones (filtros frecuentes)
CREATE INDEX IF NOT EXISTS idx_requisiciones_estado ON requisiciones(estado);

-- Índice compuesto para stock por centro
CREATE INDEX IF NOT EXISTS idx_lotes_centro_producto 
ON lotes(centro_id, producto_id) WHERE activo = true;

-- ===========================================
-- 6. TRIGGER: Auditoría de cambios de stock
-- ===========================================
CREATE OR REPLACE FUNCTION audit_stock_change()
RETURNS TRIGGER AS $$
BEGIN
  IF OLD.cantidad_actual IS DISTINCT FROM NEW.cantidad_actual THEN
    INSERT INTO audit_log (
      tabla, registro_id, campo, valor_anterior, valor_nuevo, fecha
    ) VALUES (
      'lotes', NEW.id, 'cantidad_actual', 
      OLD.cantidad_actual::text, NEW.cantidad_actual::text, now()
    );
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Crear trigger solo si no existe
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_trigger WHERE tgname = 'trg_audit_lote_stock'
  ) THEN
    CREATE TRIGGER trg_audit_lote_stock
    AFTER UPDATE ON lotes
    FOR EACH ROW EXECUTE FUNCTION audit_stock_change();
  END IF;
END $$;
```

### Verificación pre-aplicación

```sql
-- Verificar datos que violarían constraints ANTES de aplicar
SELECT 'lotes_negativos' as problema, count(*) as cantidad
FROM lotes WHERE cantidad_actual < 0
UNION ALL
SELECT 'movimientos_cero', count(*) FROM movimientos WHERE cantidad <= 0
UNION ALL
SELECT 'estados_invalidos', count(*) FROM requisiciones 
WHERE estado NOT IN (
  'borrador', 'pendiente_admin', 'pendiente_director', 
  'enviada', 'en_revision', 'autorizada', 'en_surtido', 
  'surtida', 'parcial', 'entregada', 'rechazada', 
  'devuelta', 'vencida', 'cancelada'
);
```

### Rollback

```sql
-- Solo si necesita revertir
ALTER TABLE lotes DROP CONSTRAINT IF EXISTS chk_lote_cantidad_positiva;
ALTER TABLE lotes DROP CONSTRAINT IF EXISTS chk_lote_cantidad_inicial_positiva;
ALTER TABLE movimientos DROP CONSTRAINT IF EXISTS chk_movimiento_cantidad_positiva;
ALTER TABLE movimientos DROP CONSTRAINT IF EXISTS chk_movimiento_tipo_valido;
ALTER TABLE requisiciones DROP CONSTRAINT IF EXISTS chk_requisicion_estado_valido;
ALTER TABLE usuarios DROP CONSTRAINT IF EXISTS chk_usuario_rol_valido;
DROP TRIGGER IF EXISTS trg_audit_lote_stock ON lotes;
DROP FUNCTION IF EXISTS audit_stock_change();
```

---

## Notas Importantes

1. **Siempre hacer backup antes de migrar**
2. **Ejecutar en horario de baja actividad**
3. **Probar primero en entorno de desarrollo/staging**
4. **Las migraciones son idempotentes** (se pueden re-ejecutar sin problemas)
