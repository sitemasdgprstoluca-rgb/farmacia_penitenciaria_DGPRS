# Auditoría Dashboard Analytics

**Fecha:** 2026-03-06 09:59:19
**Endpoint:** `/api/dashboard/analytics/`

## Resumen

| Métrica | Valor |
|---------|-------|
| Total Tests | 3 |
| ✅ Pasados | 0 |
| ❌ Fallidos | 3 |
| 🔴 Críticos | 1 |

## Estado General

❌ **FAIL** - Hay tests fallidos
⚠️ **ATENCIÓN:** Hay fallos críticos de seguridad que requieren corrección inmediata

## Resultados Detallados

### ❌ 1.1 Sin autenticación [INFO]

- **Estado:** FAIL
- **Detalles:** Status: ERROR

### ❌ 1.2 Token inválido [INFO]

- **Estado:** FAIL
- **Detalles:** Status: ERROR

### ❌ 2.0 Obtención de tokens [CRITICAL]

- **Estado:** FAIL
- **Detalles:** No se pudo obtener ningún token. Verificar credenciales.


## Queries de Verificación (Cross-check SQL)

```sql
-- TOP PRODUCTOS SURTIDOS
SELECT 
    p.clave, p.nombre,
    COALESCE(SUM(dr.cantidad_surtida), 0) as total_surtido
FROM core_detallerequisicion dr
JOIN core_requisicion r ON dr.requisicion_id = r.id
JOIN core_producto p ON dr.producto_id = p.id
WHERE r.estado IN ('surtida', 'entregada', 'parcial')
GROUP BY p.id, p.clave, p.nombre
ORDER BY total_surtido DESC
LIMIT 10;

-- TOP CENTROS SOLICITANTES
SELECT 
    c.nombre,
    COUNT(r.id) as total_requisiciones,
    COUNT(r.id) FILTER (WHERE r.estado IN ('surtida', 'entregada')) as surtidas
FROM core_requisicion r
JOIN core_centro c ON r.centro_destino_id = c.id
GROUP BY c.id, c.nombre
ORDER BY total_requisiciones DESC
LIMIT 10;

-- CADUCIDADES
SELECT 
    COUNT(*) FILTER (WHERE fecha_caducidad < CURRENT_DATE) as vencidos,
    COUNT(*) FILTER (WHERE fecha_caducidad >= CURRENT_DATE 
                     AND fecha_caducidad < CURRENT_DATE + 15) as vencen_15,
    COUNT(*) FILTER (WHERE fecha_caducidad >= CURRENT_DATE 
                     AND fecha_caducidad < CURRENT_DATE + 30) as vencen_30
FROM core_lote
WHERE activo = true AND cantidad_actual > 0 AND centro_id IS NULL;

-- DONACIONES TOTALES
SELECT COUNT(*) as total_donaciones FROM core_donacion;

-- CAJA CHICA TOTALES
SELECT 
    COUNT(*) as total_compras,
    COALESCE(SUM(total), 0) as monto_total
FROM core_compracajachica 
WHERE estado IN ('comprada', 'recibida');
```

