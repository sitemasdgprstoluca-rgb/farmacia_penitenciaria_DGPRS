# 🧪 INSTRUCCIONES DE VERIFICACIÓN QA - Notificaciones por Caducidad

## 📋 Requisitos Previos

- [x] Backend corriendo localmente o en ambiente QA
- [x] Acceso a la base de datos (psql, pgAdmin, o DBeaver)
- [x] Python 3.x con entorno virtual activado

---

## 🚀 Pasos de Verificación

### PASO 1: Crear Datos de Prueba

Ejecuta el script SQL de setup:

```bash
# Opción A: Desde psql
psql -U postgres -d farmacia_db -f backend/tests/test_qa_notificaciones_caducidad.sql

# Opción B: Desde DBeaver/pgAdmin
# Abrir backend/tests/test_qa_notificaciones_caducidad.sql y ejecutar las primeras secciones (hasta SETUP COMPLETO)
```

**Resultado esperado:**

```
═══════════════════════════════════════════════════════════════════════════
SETUP: Creando datos de prueba
═══════════════════════════════════════════════════════════════════════════
Centros de prueba creados: TEST-C01, TEST-C02, TEST-C99
Usuarios de prueba creados: qa_farmacia, qa_centro_norte, qa_centro_sur
Producto de prueba creado: QA-TEST-001
Lotes de Farmacia creados:
  - QA-F-CRITICO (10 días, 50 unidades) → Debe generar ALERTA CRÍTICA
  - QA-F-PROXIMO (25 días, 75 unidades) → Debe generar ALERTA PRÓXIMA
  - QA-F-CADUCADO (vencido, 20 unidades) → Debe generar ALERTA CADUCADO
  ...
```

---

### PASO 2: Ejecutar Comando en Modo Simulación (Dry-Run)

```bash
cd backend
python manage.py generar_alertas_inventario --dry-run
```

**Resultado esperado:**

```
============================================================
GENERACIÓN DE ALERTAS DE INVENTARIO
============================================================
Fecha: 2025-01-XX
Modo: SIMULACIÓN
Días caducidad: 30, Crítico: 15

Usuarios a notificar: X

📦 VERIFICANDO STOCK BAJO...
  Productos con stock bajo: X

📅 VERIFICANDO CADUCIDADES...
  Lotes críticos (≤15 días): 1
  Lotes próximos (≤30 días): 1
  Lotes caducados con stock: 1

🏥 VERIFICANDO CADUCIDAD EN CENTROS...
  📍 Centro Pruebas Norte: 1 lotes críticos
  📍 Centro Pruebas Norte: 1 lotes próximos
  📍 Centro Pruebas Sur: 1 lotes críticos
  📍 Centro Pruebas Sur: 1 lotes CADUCADOS
  ⚠️  Centro Sin Usuarios: Sin usuarios activos para notificar

  ✅ Centros notificados: 2

============================================================
📊 RESUMEN:
  • Productos con stock bajo: X
  • Lotes críticos: 1
  • Lotes próximos a caducar: 1
  • Lotes caducados con stock: 1

⚠️  MODO SIMULACIÓN: No se crearon notificaciones
============================================================
```

**✅ VALIDACIÓN PASO 2:**

| Criterio | Esperado | ¿Cumple? |
|----------|----------|----------|
| Lotes críticos Farmacia | 1 (QA-F-CRITICO) | ⬜ |
| Lotes próximos Farmacia | 1 (QA-F-PROXIMO) | ⬜ |
| Lotes caducados Farmacia | 1 (QA-F-CADUCADO) | ⬜ |
| Centros con lotes críticos | 2 (Norte, Sur) | ⬜ |
| Centro sin usuarios | Warning "Sin usuarios" | ⬜ |
| Modo simulación | "No se crearon notificaciones" | ⬜ |

---

### PASO 3: Ejecutar Comando REAL (Crea Notificaciones)

```bash
python manage.py generar_alertas_inventario
```

**Resultado esperado:**

```
============================================================
...
✅ Notificaciones creadas: X
============================================================
```

El número `X` debe ser > 0 (depende de cuántos usuarios tienes).

**Cálculo Esperado:**
- **Farmacia:**
  - Críticos: 1 notificación × N usuarios farmacia
  - Próximos: 1 notificación × N usuarios farmacia
  - Caducados: 1 notificación × N usuarios farmacia
- **Centros:**
  - Centro Norte: 2 notificaciones (crítico + próximo) × usuarios del centro
  - Centro Sur: 2 notificaciones (crítico + caducado) × usuarios del centro

---

### PASO 4: Verificar Notificaciones en Base de Datos

Ejecuta las queries de VERIFICACIÓN del mismo archivo SQL:

```sql
-- NOTIFICACIONES DE FARMACIA
SELECT 
    '🏥 NOTIF FARMACIA' as tipo,
    n.created_at::date as fecha,
    n.tipo as nivel,
    n.titulo,
    u.username as destinatario,
    u.rol,
    n.datos::jsonb->>'tipo_alerta' as tipo_alerta,
    n.datos::jsonb->>'cantidad_lotes' as cantidad
FROM notificaciones n
JOIN usuarios u ON n.usuario_id = u.id
WHERE n.datos::jsonb->>'tipo_alerta' IN (
    'caducidad_critica', 
    'caducidad_proxima', 
    'caducados'
)
  AND n.created_at::date >= CURRENT_DATE
ORDER BY n.created_at DESC;
```

**Resultado esperado:**

| tipo | nivel | titulo | destinatario | tipo_alerta | cantidad |
|------|-------|--------|--------------|-------------|----------|
| 🏥 NOTIF FARMACIA | error | 🚨 CRÍTICO: 1 Lotes por Caducar en 15 días | qa_farmacia | caducidad_critica | 1 |
| 🏥 NOTIF FARMACIA | warning | ⚠️ Alerta: 1 Lotes Próximos a Caducar | qa_farmacia | caducidad_proxima | 1 |
| 🏥 NOTIF FARMACIA | error | 🚫 URGENTE: 1 Lotes CADUCADOS con Stock | qa_farmacia | caducados | 1 |

```sql
-- NOTIFICACIONES DE CENTROS
SELECT 
    '🏥 NOTIF CENTROS' as tipo,
    n.created_at::date as fecha,
    n.tipo as nivel,
    n.datos::jsonb->>'centro_nombre' as centro,
    u.username as destinatario,
    n.titulo,
    n.datos::jsonb->>'tipo_alerta' as tipo_alerta,
    n.datos::jsonb->>'cantidad_lotes' as cantidad
FROM notificaciones n
JOIN usuarios u ON n.usuario_id = u.id
WHERE n.datos::jsonb->>'tipo_alerta' IN (
    'caducidad_critica_centro', 
    'caducidad_proxima_centro', 
    'caducados_centro'
)
  AND n.created_at::date >= CURRENT_DATE
ORDER BY n.datos::jsonb->>'centro_nombre', n.created_at DESC;
```

**Resultado esperado:**

| tipo | centro | destinatario | titulo | tipo_alerta | cantidad |
|------|--------|--------------|--------|-------------|----------|
| 🏥 NOTIF CENTROS | Centro Pruebas Norte | qa_centro_norte | 🚨 Centro Pruebas Norte: 1 Lotes CRÍTICOS (≤15d) | caducidad_critica_centro | 1 |
| 🏥 NOTIF CENTROS | Centro Pruebas Norte | qa_centro_norte | ⚠️ Centro Pruebas Norte: 1 Lotes Próximos a Caducar | caducidad_proxima_centro | 1 |
| 🏥 NOTIF CENTROS | Centro Pruebas Sur | qa_centro_sur | 🚨 Centro Pruebas Sur: 1 Lotes CRÍTICOS (≤15d) | caducidad_critica_centro | 1 |
| 🏥 NOTIF CENTROS | Centro Pruebas Sur | qa_centro_sur | 🚫 Centro Pruebas Sur: 1 Lotes CADUCADOS con Stock | caducados_centro | 1 |

---

### PASO 5: Verificar AISLAMIENTO por Centro

```sql
-- Verificar que qa_centro_norte NO ve notificaciones de Centro Sur
SELECT 
    'AISLAMIENTO: qa_centro_norte' as test,
    COUNT(*) as notificaciones_centro_sur,
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ PASS: No ve centro ajeno'
        ELSE '❌ FAIL: Ve notificaciones de otro centro'
    END as resultado
FROM notificaciones n
JOIN usuarios u ON n.usuario_id = u.id
WHERE u.username = 'qa_centro_norte'
  AND n.datos::jsonb->>'centro_nombre' LIKE '%Sur%'
  AND n.created_at::date >= CURRENT_DATE;
```

**Resultado esperado:**

| test | notificaciones_centro_sur | resultado |
|------|---------------------------|-----------|
| AISLAMIENTO: qa_centro_norte | 0 | ✅ PASS: No ve centro ajeno |

```sql
-- Verificar que qa_centro_sur NO ve notificaciones de Centro Norte
SELECT 
    'AISLAMIENTO: qa_centro_sur' as test,
    COUNT(*) as notificaciones_centro_norte,
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ PASS: No ve centro ajeno'
        ELSE '❌ FAIL: Ve notificaciones de otro centro'
    END as resultado
FROM notificaciones n
JOIN usuarios u ON n.usuario_id = u.id
WHERE u.username = 'qa_centro_sur'
  AND n.datos::jsonb->>'centro_nombre' LIKE '%Norte%'
  AND n.created_at::date >= CURRENT_DATE;
```

**Resultado esperado:**

| test | notificaciones_centro_norte | resultado |
|------|------------------------------|-----------|
| AISLAMIENTO: qa_centro_sur | 0 | ✅ PASS: No ve centro ajeno |

**✅ VALIDACIÓN PASO 5: Aislamiento por Centro PASS**

---

### PASO 6: Verificar PREVENCIÓN DE DUPLICADOS

Ejecuta el comando **por segunda vez** (dentro de las 24 horas):

```bash
python manage.py generar_alertas_inventario
```

**Resultado esperado:**

```
============================================================
...
✅ Notificaciones creadas: 0
============================================================
```

El comando debe crear **0 notificaciones** porque ya existen notificaciones recientes (ventana de 24h).

```sql
-- Contar notificaciones por usuario
SELECT 
    'DUPLICADOS' as test,
    u.username,
    n.datos::jsonb->>'tipo_alerta' as tipo_alerta,
    COUNT(*) as cantidad_notificaciones,
    CASE 
        WHEN COUNT(*) = 1 THEN '✅ PASS: Sin duplicados'
        WHEN COUNT(*) > 1 THEN '⚠️ POSIBLE DUPLICADO'
        ELSE '✅ OK'
    END as resultado
FROM notificaciones n
JOIN usuarios u ON n.usuario_id = u.id
WHERE n.created_at >= NOW() - INTERVAL '24 hours'
  AND n.datos::jsonb->>'tipo_alerta' LIKE '%caducidad%'
GROUP BY u.username, n.datos::jsonb->>'tipo_alerta'
ORDER BY cantidad_notificaciones DESC;
```

**Resultado esperado:**

| username | tipo_alerta | cantidad_notificaciones | resultado |
|----------|-------------|-------------------------|-----------|
| qa_farmacia | caducidad_critica | 1 | ✅ PASS: Sin duplicados |
| qa_centro_norte | caducidad_critica_centro | 1 | ✅ PASS: Sin duplicados |
| ... | ... | 1 | ✅ PASS: Sin duplicados |

**✅ VALIDACIÓN PASO 6: Prevención de Duplicados PASS**

---

### PASO 7: Verificar Flag `--forzar` (Ignorar Duplicados)

```bash
python manage.py generar_alertas_inventario --forzar
```

**Resultado esperado:**

```
✅ Notificaciones creadas: X
```

Ahora el comando **SÍ debe crear** notificaciones (aunque ya existan recientes).

```sql
-- Verificar que ahora hay más de 1 notificación por usuario
SELECT 
    u.username,
    n.datos::jsonb->>'tipo_alerta' as tipo_alerta,
    COUNT(*) as cantidad_notificaciones,
    CASE 
        WHEN COUNT(*) >= 2 THEN '✅ PASS: Flag --forzar funciona'
        ELSE '❌ FAIL: No se forzó creación'
    END as resultado
FROM notificaciones n
JOIN usuarios u ON n.usuario_id = u.id
WHERE n.created_at >= NOW() - INTERVAL '24 hours'
  AND n.datos::jsonb->>'tipo_alerta' = 'caducidad_critica'
  AND u.username = 'qa_farmacia'
GROUP BY u.username, n.datos::jsonb->>'tipo_alerta';
```

**Resultado esperado:**

| username | tipo_alerta | cantidad_notificaciones | resultado |
|----------|-------------|-------------------------|-----------|
| qa_farmacia | caducidad_critica | 2 | ✅ PASS: Flag --forzar funciona |

**✅ VALIDACIÓN PASO 7: Flag --forzar PASS**

---

### PASO 8: Verificar Usuario Inactivo

```sql
SELECT 
    'USUARIO INACTIVO' as test,
    COUNT(*) as notificaciones,
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ PASS: Usuario inactivo no recibe notificaciones'
        ELSE '❌ FAIL: Usuario inactivo recibió notificaciones'
    END as resultado
FROM notificaciones n
JOIN usuarios u ON n.usuario_id = u.id
WHERE u.username = 'qa_centro_inactivo'
  AND u.is_active = false
  AND n.created_at::date >= CURRENT_DATE;
```

**Resultado esperado:**

| test | notificaciones | resultado |
|------|----------------|-----------|
| USUARIO INACTIVO | 0 | ✅ PASS: Usuario inactivo no recibe notificaciones |

**✅ VALIDACIÓN PASO 8: Usuario Inactivo PASS**

---

### PASO 9: Verificar Centro Sin Usuarios

```sql
SELECT 
    'CENTRO SIN USUARIOS' as test,
    c.nombre as centro,
    COUNT(DISTINCT icc.id) as lotes_criticos,
    COUNT(DISTINCT u.id) as usuarios_activos,
    COUNT(DISTINCT n.id) as notificaciones_generadas,
    CASE 
        WHEN COUNT(DISTINCT n.id) = 0 THEN '✅ PASS: No generó notificaciones sin usuarios'
        ELSE '❌ FAIL: Generó notificaciones sin destinatarios'
    END as resultado
FROM centros c
LEFT JOIN inventario_caja_chica icc ON icc.centro_id = c.id 
    AND icc.numero_lote LIKE 'QA-CC-%'
    AND icc.cantidad_actual > 0
LEFT JOIN usuarios u ON u.centro_id = c.id AND u.is_active = true
LEFT JOIN notificaciones n ON n.usuario_id = u.id 
    AND n.created_at::date >= CURRENT_DATE
WHERE c.clave = 'TEST-C99'
GROUP BY c.nombre;
```

**Resultado esperado:**

| test | centro | lotes_criticos | usuarios_activos | notificaciones_generadas | resultado |
|------|--------|----------------|------------------|--------------------------|-----------|
| CENTRO SIN USUARIOS | Centro Sin Usuarios | 1 | 0 | 0 | ✅ PASS: No generó notificaciones sin usuarios |

**✅ VALIDACIÓN PASO 9: Centro Sin Usuarios PASS**

---

### PASO 10: Verificar en UI (Opcional)

1. Iniciar sesión con usuario `qa_farmacia` (password: usa el que configuraste)
2. Ir a Notificaciones (campana 🔔 en navbar)
3. **Debe ver:**
   - 🚨 CRÍTICO: 1 Lotes por Caducar en 15 días
   - ⚠️ Alerta: 1 Lotes Próximos a Caducar
   - 🚫 URGENTE: 1 Lotes CADUCADOS con Stock

4. Iniciar sesión con usuario `qa_centro_norte`
5. Ir a Notificaciones
6. **Debe ver:**
   - 🚨 Centro Pruebas Norte: 1 Lotes CRÍTICOS (≤15d)
   - ⚠️ Centro Pruebas Norte: 1 Lotes Próximos a Caducar
   - **NO debe ver** notificaciones del Centro Sur

**Screenshot:** (Opcional) captura pantalla de notificaciones para evidencia.

---

## 🧹 LIMPIEZA: Eliminar Datos de Prueba

**⚠️ IMPORTANTE:** Solo ejecutar en ambiente QA, **NUNCA en producción**.

```sql
DELETE FROM lotes WHERE numero_lote LIKE 'QA-F-%';
DELETE FROM inventario_caja_chica WHERE numero_lote LIKE 'QA-CC-%';
DELETE FROM notificaciones WHERE datos::jsonb->>'lotes' LIKE '%QA-%';
DELETE FROM productos WHERE clave = 'QA-TEST-001';
DELETE FROM usuarios WHERE username LIKE 'qa_%';
DELETE FROM centros WHERE clave LIKE 'TEST-%';
```

---

## ✅ Checklist Final de Verificación

| # | Caso de Prueba | Resultado | Evidencia |
|---|----------------|-----------|-----------|
| 1 | Lotes críticos Farmacia alertan | ⬜ | SQL/Screenshot |
| 2 | Lotes próximos Farmacia alertan | ⬜ | SQL/Screenshot |
| 3 | Lotes caducados Farmacia alertan | ⬜ | SQL/Screenshot |
| 4 | Lotes sin stock NO alertan | ⬜ | Dry-run output |
| 5 | Stock bajo Farmacia alerta | ⬜ | SQL/Screenshot |
| 6 | Lotes críticos Centro alertan | ⬜ | SQL/Screenshot |
| 7 | Aislamiento por Centro funciona | ⬜ | SQL queries PASO 5 |
| 8 | Prevención duplicados (24h) | ⬜ | SQL queries PASO 6 |
| 9 | Flag --forzar ignora duplicados | ⬜ | SQL queries PASO 7 |
| 10 | Usuario inactivo NO recibe | ⬜ | SQL queries PASO 8 |
| 11 | Centro sin usuarios omitido | ⬜ | SQL queries PASO 9 |
| 12 | Dry-run NO crea notificaciones | ⬜ | PASO 2 output |
| 13 | UI muestra notificaciones | ⬜ | Screenshots PASO 10 |

---

## 🚀 DEPLOYMENT: Activar Cron Job en Render

Una vez que **TODOS los casos de prueba PASAN** en QA:

### 1. Actualizar Plan Render

El cron job requiere plan **Starter** o superior ($7/mes):

1. Ir a https://dashboard.render.com/
2. Seleccionar tu servicio `farmacia-api`
3. Settings → Plan → Upgrade to **Starter**

### 2. Activar Cron Job

El cron job ya está configurado en `render.yaml` (descomentado):

```yaml
- type: cron
  name: farmacia-alertas
  runtime: python
  region: oregon
  plan: starter
  rootDir: backend
  schedule: "0 7 * * *"  # Diariamente 7:00 AM UTC
  startCommand: python manage.py generar_alertas_inventario
```

**Push a producción:**

```bash
git add render.yaml backend/core/management/commands/generar_alertas_inventario.py
git commit -m "feat: Notificaciones caducidad para Farmacia + Centros (15/30 días)"
git push origin main
```

Render detectará el cambio y creará el cron job automáticamente.

### 3. Verificar en Render Dashboard

1. Ir a https://dashboard.render.com/
2. Buscar el servicio `farmacia-alertas` (tipo: Cron Job)
3. Verificar:
   - **Schedule:** `0 7 * * *` (diariamente 7 AM UTC)
   - **Last Run:** (después de la primera ejecución)
   - **Status:** Active

### 4. Ejecutar Manualmente (Primera Vez)

En Render dashboard:

1. Ir a `farmacia-alertas` → Manual Deploy
2. O ejecutar desde shell:

```bash
render run --service farmacia-alertas python manage.py generar_alertas_inventario
```

### 5. Monitorear Logs

```bash
render logs --service farmacia-alertas --tail 100
```

**Verificar output:**

```
============================================================
GENERACIÓN DE ALERTAS DE INVENTARIO
============================================================
Fecha: 2025-XX-XX
Modo: REAL
Días caducidad: 30, Crítico: 15

...
✅ Notificaciones creadas: X
============================================================
```

---

## 📝 Reporte Final

Una vez completadas todas las verificaciones, completa este reporte:

```markdown
# ✅ REPORTE DE VERIFICACIÓN QA - Sistema de Notificaciones por Caducidad

**Fecha:** 2025-XX-XX
**Ejecutado por:** [Tu Nombre]
**Ambiente:** QA / Producción

## Casos de Prueba Ejecutados

- [✅/❌] 1. Lotes críticos Farmacia
- [✅/❌] 2. Lotes próximos Farmacia
- [✅/❌] 3. Lotes caducados Farmacia
- [✅/❌] 4. Lotes sin stock (no alerta)
- [✅/❌] 5. Stock bajo Farmacia
- [✅/❌] 6. Lotes críticos Centros
- [✅/❌] 7. Aislamiento por Centro
- [✅/❌] 8. Prevención duplicados
- [✅/❌] 9. Flag --forzar
- [✅/❌] 10. Usuario inactivo
- [✅/❌] 11. Centro sin usuarios
- [✅/❌] 12. Dry-run mode
- [✅/❌] 13. UI Notificaciones

## Resultado Global

**Status:** ✅ PASS / ❌ FAIL
**Casos Pasados:** X/13
**Casos Fallidos:** X/13

## Notas

[Añadir cualquier observación, bug encontrado, o mejora sugerida]

## Aprobación para Deployment

**QA Lead:** [Firma/Nombre] - Fecha: [YYYY-MM-DD]
**Backend Lead:** [Firma/Nombre] - Fecha: [YYYY-MM-DD]
**DevOps:** [Firma/Nombre] - Fecha: [YYYY-MM-DD]
```

---

## 🆘 Troubleshooting

### Problema: "No module named 'core'"

**Solución:**

```bash
cd backend
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python manage.py generar_alertas_inventario --dry-run
```

### Problema: "relation 'inventario_caja_chica' does not exist"

**Solución:** Ejecutar migraciones:

```bash
python manage.py migrate
```

### Problema: Cron job no aparece en Render

**Causas:**
- Plan gratuito (requiere Starter)
- Sintaxis incorrecta en `render.yaml`
- No se hizo push a main

**Solución:** Verificar plan, revisar YAML, push a main.

### Problema: Notificaciones no se muestran en UI

**Verificar:**
1. Sistema de notificaciones funciona (otra notificación cualquiera)
2. Query SQL devuelve registros
3. Usuario tiene permisos correctos
4. Frontend está usando endpoint correcto de notificaciones

---

**Documentación:** [docs/SISTEMA_NOTIFICACIONES_CADUCIDAD.md](../docs/SISTEMA_NOTIFICACIONES_CADUCIDAD.md)

**Contacto:** [Tu email/Slack]

