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

## Notas Importantes

1. **Siempre hacer backup antes de migrar**
2. **Ejecutar en horario de baja actividad**
3. **Probar primero en entorno de desarrollo/staging**
4. **Las migraciones son idempotentes** (se pueden re-ejecutar sin problemas)
