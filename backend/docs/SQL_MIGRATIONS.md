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
-- Verificado contra esquema real de BD: 2025-12
-- ============================================

-- ===========================================
-- 1. LOTES: Stock nunca negativo
-- Campos reales: cantidad_inicial, cantidad_actual (no hay campo 'estado')
-- ===========================================
ALTER TABLE lotes 
ADD CONSTRAINT chk_lote_cantidad_actual_positiva 
CHECK (cantidad_actual >= 0);

ALTER TABLE lotes 
ADD CONSTRAINT chk_lote_cantidad_inicial_positiva 
CHECK (cantidad_inicial >= 0);

ALTER TABLE lotes
ADD CONSTRAINT chk_lote_precio_positivo
CHECK (precio_unitario >= 0);

COMMENT ON CONSTRAINT chk_lote_cantidad_actual_positiva ON lotes IS 
  'ISS-001: Evita stock negativo por operaciones concurrentes o directas';

-- ===========================================
-- 2. MOVIMIENTOS: Validaciones básicas
-- Campos reales: tipo, cantidad, producto_id (NOT NULL), lote_id (nullable)
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
-- Campo real: estado (character varying, NOT NULL)
-- ===========================================
ALTER TABLE requisiciones 
ADD CONSTRAINT chk_requisicion_estado_valido 
CHECK (estado IN (
  'borrador', 'pendiente_admin', 'pendiente_director', 
  'enviada', 'en_revision', 'autorizada', 'en_surtido', 
  'surtida', 'parcial', 'entregada', 'rechazada', 
  'devuelta', 'vencida', 'cancelada'
));

-- Prioridad válida
ALTER TABLE requisiciones
ADD CONSTRAINT chk_requisicion_prioridad_valida
CHECK (prioridad IN ('baja', 'normal', 'alta', 'urgente'));

-- Tipo válido
ALTER TABLE requisiciones
ADD CONSTRAINT chk_requisicion_tipo_valido
CHECK (tipo IN ('normal', 'urgente', 'programada', 'emergencia'));

COMMENT ON CONSTRAINT chk_requisicion_estado_valido ON requisiciones IS 
  'ISS-003: Solo estados válidos de la máquina de estados';

-- ===========================================
-- 4. USUARIOS: Roles válidos
-- Campo real: rol (character varying, NOT NULL)
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
-- 5. DETALLES_REQUISICION: Cantidades válidas
-- ===========================================
ALTER TABLE detalles_requisicion
ADD CONSTRAINT chk_detalle_cantidad_solicitada_positiva
CHECK (cantidad_solicitada > 0);

ALTER TABLE detalles_requisicion
ADD CONSTRAINT chk_detalle_cantidad_autorizada_valida
CHECK (cantidad_autorizada IS NULL OR cantidad_autorizada >= 0);

ALTER TABLE detalles_requisicion
ADD CONSTRAINT chk_detalle_cantidad_surtida_valida
CHECK (cantidad_surtida IS NULL OR cantidad_surtida >= 0);

-- ===========================================
-- 6. PRODUCTOS: Valores válidos
-- ===========================================
ALTER TABLE productos
ADD CONSTRAINT chk_producto_stock_minimo_positivo
CHECK (stock_minimo >= 0);

ALTER TABLE productos
ADD CONSTRAINT chk_producto_stock_actual_positivo
CHECK (stock_actual >= 0);

-- ===========================================
-- 7. CENTROS: Básicos
-- ===========================================
ALTER TABLE centros
ADD CONSTRAINT chk_centro_nombre_no_vacio
CHECK (TRIM(nombre) <> '');

-- ===========================================
-- 8. ÍNDICES PARA PERFORMANCE Y CONCURRENCIA
-- ===========================================

-- Índice para bloqueos por lote (usado en select_for_update)
CREATE INDEX IF NOT EXISTS idx_lotes_pk_lock ON lotes(id);

-- Índice para búsqueda de lotes por producto y centro
CREATE INDEX IF NOT EXISTS idx_lotes_producto_centro 
ON lotes(producto_id, centro_id) WHERE activo = true;

-- Índice para lotes por fecha caducidad (alertas de vencimiento)
CREATE INDEX IF NOT EXISTS idx_lotes_caducidad 
ON lotes(fecha_caducidad) WHERE activo = true;

-- Índice para búsqueda de movimientos por requisición
CREATE INDEX IF NOT EXISTS idx_movimientos_requisicion_tipo 
ON movimientos(requisicion_id, tipo) WHERE requisicion_id IS NOT NULL;

-- Índice para estado de requisiciones (filtros frecuentes)
CREATE INDEX IF NOT EXISTS idx_requisiciones_estado 
ON requisiciones(estado);

-- Índice para requisiciones por centro
CREATE INDEX IF NOT EXISTS idx_requisiciones_centro_origen
ON requisiciones(centro_origen_id) WHERE centro_origen_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_requisiciones_centro_destino
ON requisiciones(centro_destino_id) WHERE centro_destino_id IS NOT NULL;

-- Índice para historial de requisiciones
CREATE INDEX IF NOT EXISTS idx_historial_requisicion
ON requisicion_historial_estados(requisicion_id, fecha_cambio DESC);

-- Índice para usuarios por centro
CREATE INDEX IF NOT EXISTS idx_usuarios_centro
ON usuarios(centro_id) WHERE centro_id IS NOT NULL;

-- ===========================================
-- 9. TRIGGER: Auditoría de cambios de stock (OPCIONAL)
-- Requiere tabla audit_log existente
-- ===========================================
-- CREATE OR REPLACE FUNCTION audit_stock_change()
-- RETURNS TRIGGER AS $$
-- BEGIN
--   IF OLD.cantidad_actual IS DISTINCT FROM NEW.cantidad_actual THEN
--     INSERT INTO auditoria_logs (
--       modelo, objeto_id, accion, datos_anteriores, datos_nuevos, timestamp
--     ) VALUES (
--       'lotes', NEW.id::text, 'UPDATE_STOCK', 
--       jsonb_build_object('cantidad_actual', OLD.cantidad_actual),
--       jsonb_build_object('cantidad_actual', NEW.cantidad_actual),
--       now()
--     );
--   END IF;
--   RETURN NEW;
-- END;
-- $$ LANGUAGE plpgsql;
-- 
-- CREATE TRIGGER trg_audit_lote_stock
-- AFTER UPDATE ON lotes
-- FOR EACH ROW EXECUTE FUNCTION audit_stock_change();
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
