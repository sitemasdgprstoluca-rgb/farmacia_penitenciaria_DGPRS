# 🔔 Sistema de Notificaciones por Caducidad de Lotes

**Fecha:** 2025-01-XX  
**Responsable:** QA Lead + Backend Lead  
**Sprint:** Sistema de Alertas Automáticas

---

## 📋 Resumen Ejecutivo

Sistema automático de notificaciones que alerta a usuarios sobre lotes próximos a caducar, tanto en **Farmacia Central** como en **Inventarios de Caja Chica por Centro**.

### ✅ Características Implementadas

| Característica | Estado | Descripción |
|---------------|---------|-------------|
| Notificaciones Farmacia | ✅ IMPLEMENTADO | Alertas para Lote (inventario central) |
| Notificaciones Centros | ✅ **NUEVO** | Alertas para InventarioCajaChica (por centro) |
| Aislamiento por Centro | ✅ **NUEVO** | Usuarios solo ven alertas de su centro |
| Umbrales Configurables | ✅ IMPLEMENTADO | `--dias-caducidad=30`, `--dias-critico=15` |
| Prevención Duplicados | ✅ IMPLEMENTADO | Ventana de 24h por tipo de alerta |
| Stock Bajo | ✅ IMPLEMENTADO | Productos con stock < mínimo |
| Lotes Caducados | ✅ IMPLEMENTADO | Lotes vencidos con stock >0 |
| Cron Job | ✅ CONFIGURADO | Diariamente 7:00 AM UTC (requiere plan Starter) |
| Dry-Run Mode | ✅ IMPLEMENTADO | Simulación sin crear notificaciones |

---

## 🎯 Requisitos Cumplidos

### 1. Ventanas de Alerta

| Nivel | Umbral | Tipo Notificación |
|-------|--------|-------------------|
| **Crítico** | ≤15 días | 🚨 `error` |
| **Urgente** | Entre 15-30 días | ⚠️ `warning` |
| **Vencido** | <hoy | 🚫 `error` |

**Modificación:** Se ajustó el umbral crítico de 7 días (anterior) a **15 días** según requerimientos.

### 2. Alcance por Inventario

#### Farmacia (Lote)
- **Destinatarios:** Usuarios con rol `farmacia`, `admin_farmacia`, `admin`, `admin_sistema`, `superusuario`
- **Scope:** Todos los lotes del inventario central
- **URL:** `/lotes?filtro=por_caducar`

#### Centros (InventarioCajaChica)
- **Destinatarios:** Usuarios del **mismo centro** (aislamiento estricto)
- **Scope:** Lotes de caja chica del centro específico
- **URL:** `/centros/{centro_id}/inventario?filtro=por_caducar`

### 3. Prevención de Duplicados

```python
# Verifica notificaciones en últimas 24 horas
existe_reciente = Notificacion.objects.filter(
    usuario=usuario,
    tipo='error',  # o 'warning'
    titulo__icontains='Caducidad Crítica',  # según tipo
    datos__centro_id=centro.id,  # solo centros
    created_at__gte=timezone.now() - timedelta(hours=24)
).exists()
```

**Criterio:** Una notificación por (usuario, tipo_alerta, centro) cada 24 horas.

### 4. Performance

- **Select Related:** `select_related('producto', 'centro')` en queries
- **Filtros Eficientes:** Índices en `fecha_caducidad`, `cantidad_actual`, `centro_id`
- **Batch Processing:** Notificaciones creadas en lote por centro

---

## 🏗️ Arquitectura

### Comando Management

**Archivo:** `backend/core/management/commands/generar_alertas_inventario.py`

#### Argumentos

```bash
python manage.py generar_alertas_inventario [OPTIONS]

--dry-run              Solo mostrar alertas sin crear notificaciones
--dias-caducidad=30    Días antes de caducidad para alertar (default: 30)
--dias-critico=15      Días antes de caducidad para alerta crítica (default: 15)
--forzar               Crear notificaciones aunque ya existan recientes
```

#### Secciones del Comando

1. **Stock Bajo (Farmacia)**
   - Productos con `stock_total < stock_minimo`
   - Solo lotes no vencidos

2. **Lotes Críticos (Farmacia)**
   - `fecha_caducidad <= hoy + dias_critico`
   - `cantidad_actual > 0`
   - Notificación `tipo='error'`

3. **Lotes Próximos (Farmacia)**
   - `dias_critico < fecha_caducidad <= hoy + dias_caducidad`
   - Notificación `tipo='warning'`

4. **Lotes Caducados (Farmacia)**
   - `fecha_caducidad < hoy`
   - `cantidad_actual > 0`

5. **🆕 Lotes Críticos (Centros)**
   - Por cada Centro activo
   - InventarioCajaChica con `fecha_caducidad <= hoy + dias_critico`
   - Usuarios filtrados por `centro=centro, is_active=True`
   - Excluye roles de farmacia: `.exclude(rol__in=['farmacia', 'admin_farmacia'])`

6. **🆕 Lotes Próximos (Centros)**
   - Similar a críticos pero rango [dias_critico, dias_caducidad]

7. **🆕 Lotes Caducados (Centros)**
   - `fecha_caducidad < hoy` con stock

#### Estructura de Notificación

```python
Notificacion.objects.create(
    usuario=usuario,
    tipo='error',  # 'warning', 'error'
    titulo='🚨 {Centro}: {N} Lotes CRÍTICOS (≤15d)',
    mensaje='Lotes del inventario de caja chica...\n\n{lista lotes}',
    datos={
        'tipo_alerta': 'caducidad_critica_centro',
        'centro_id': centro.id,
        'centro_nombre': centro.nombre,
        'cantidad_lotes': N,
        'lotes': ['LOTE-001', 'LOTE-002', ...]
    },
    url=f'/centros/{centro.id}/inventario?filtro=por_caducar'
)
```

#### Tipos de Alerta

| tipo_alerta | Scope | Descripción |
|-------------|-------|-------------|
| `stock_bajo` | Farmacia | Productos bajo stock mínimo |
| `caducidad_critica` | Farmacia | Lotes ≤15 días |
| `caducidad_proxima` | Farmacia | Lotes 15-30 días |
| `caducados` | Farmacia | Lotes vencidos |
| `caducidad_critica_centro` | Centro | Lotes ≤15 días en centro |
| `caducidad_proxima_centro` | Centro | Lotes 15-30 días en centro |
| `caducados_centro` | Centro | Lotes vencidos en centro |

---

## ⚙️ Configuración Cron Job

### Render.com

**Archivo:** `render.yaml`

```yaml
- type: cron
  name: farmacia-alertas
  runtime: python
  region: oregon
  plan: starter  # ⚠️ Requiere plan pago ($7/mes)
  rootDir: backend
  schedule: "0 7 * * *"  # Diariamente 7:00 AM UTC
  buildCommand: pip install -r requirements.txt
  startCommand: python manage.py generar_alertas_inventario
  envVars:
    - key: DATABASE_URL
      sync: false
    - key: DEBUG
      value: "False"
```

**Horario:**
- **7:00 AM UTC** = 1:00 AM México (horario estándar)
- **7:00 AM UTC** = 2:00 AM México (horario de verano)

### Ejecución Manual

Si usas plan gratuito o para pruebas:

```bash
# Simulación (no crea notificaciones)
python manage.py generar_alertas_inventario --dry-run

# Ejecución real
python manage.py generar_alertas_inventario

# Con umbrales personalizados
python manage.py generar_alertas_inventario --dias-critico=10 --dias-caducidad=20

# Forzar notificaciones (ignorar duplicados)
python manage.py generar_alertas_inventario --forzar
```

---

## 🧪 Plan de Verificación QA

### Escenario 1: Farmacia - Lotes Críticos

**Setup:**
```sql
-- Crear lote que vence en 14 días
INSERT INTO lotes (producto_id, numero_lote, fecha_caducidad, cantidad_actual, activo)
VALUES (1, 'F-CRIT-001', CURRENT_DATE + INTERVAL '14 days', 100, true);

-- Crear usuario farmacia
INSERT INTO usuarios (username, rol, is_active) 
VALUES ('farmacia_test', 'farmacia', true);
```

**Ejecutar:**
```bash
python manage.py generar_alertas_inventario --dry-run
```

**Verificar Output:**
```
📅 VERIFICANDO CADUCIDADES...
  Lotes críticos (≤15 días): 1
  Lotes próximos (≤30 días): 0
  Lotes caducados con stock: 0

📊 RESUMEN:
  • Lotes críticos: 1
⚠️  MODO SIMULACIÓN: No se crearon notificaciones
```

**Ejecutar Real:**
```bash
python manage.py generar_alertas_inventario
```

**Verificar BD:**
```sql
SELECT 
    n.titulo, n.tipo, n.mensaje, u.username, 
    n.datos::jsonb->>'tipo_alerta' as tipo_alerta,
    n.datos::jsonb->>'cantidad_lotes' as cantidad
FROM notificaciones n
JOIN usuarios u ON n.usuario_id = u.id
WHERE n.datos::jsonb->>'tipo_alerta' = 'caducidad_critica'
ORDER BY n.created_at DESC
LIMIT 5;
```

**Resultado Esperado:**
| titulo | tipo | username | tipo_alerta | cantidad |
|--------|------|----------|-------------|----------|
| 🚨 CRÍTICO: 1 Lotes por Caducar en 15 días | error | farmacia_test | caducidad_critica | 1 |

**Status:** ⬜ POR VERIFICAR

---

### Escenario 2: Centro - Lotes Críticos con Aislamiento

**Setup:**
```sql
-- Crear 2 centros
INSERT INTO centros (clave, nombre, activo) VALUES 
('C01', 'Centro Norte', true),
('C02', 'Centro Sur', true);

-- Lote crítico para Centro Norte
INSERT INTO inventario_caja_chica 
(centro_id, descripcion_producto, numero_lote, fecha_caducidad, cantidad_actual, activo)
VALUES 
((SELECT id FROM centros WHERE clave='C01'), 'Paracetamol 500mg', 'CC-N-001', CURRENT_DATE + INTERVAL '10 days', 50, true);

-- Lote crítico para Centro Sur
INSERT INTO inventario_caja_chica 
(centro_id, descripcion_producto, numero_lote, fecha_caducidad, cantidad_actual, activo)
VALUES 
((SELECT id FROM centros WHERE clave='C02'), 'Ibuprofeno 400mg', 'CC-S-001', CURRENT_DATE + INTERVAL '12 days', 30, true);

-- Usuarios por centro
INSERT INTO usuarios (username, rol, centro_id, is_active) VALUES
('usuario_norte', 'capturista', (SELECT id FROM centros WHERE clave='C01'), true),
('usuario_sur', 'capturista', (SELECT id FROM centros WHERE clave='C02'), true);
```

**Ejecutar:**
```bash
python manage.py generar_alertas_inventario
```

**Verificar Aislamiento:**
```sql
-- Notificaciones para usuario_norte (debe ver solo Centro Norte)
SELECT 
    n.titulo, 
    n.datos::jsonb->>'centro_nombre' as centro,
    n.datos::jsonb->>'lotes' as lotes,
    u.username
FROM notificaciones n
JOIN usuarios u ON n.usuario_id = u.id
WHERE u.username = 'usuario_norte'
  AND n.datos::jsonb->>'tipo_alerta' LIKE '%_centro'
ORDER BY n.created_at DESC;
```

**Resultado Esperado:**
| titulo | centro | lotes | username |
|--------|--------|-------|----------|
| 🚨 Centro Norte: 1 Lotes CRÍTICOS (≤15d) | Centro Norte | ["CC-N-001"] | usuario_norte |

**Verificar NO debe ver Centro Sur:**
```sql
SELECT COUNT(*) as debe_ser_cero
FROM notificaciones n
JOIN usuarios u ON n.usuario_id = u.id
WHERE u.username = 'usuario_norte'
  AND n.datos::jsonb->>'centro_nombre' = 'Centro Sur';
```

**Resultado Esperado:** `debe_ser_cero = 0`

**Status:** ⬜ POR VERIFICAR

---

### Escenario 3: Prevención de Duplicados

**Setup:**
```sql
-- Ya existen notificaciones del Escenario 2
```

**Ejecutar por segunda vez (dentro de 24h):**
```bash
python manage.py generar_alertas_inventario
```

**Verificar Output:**
```
🏥 VERIFICANDO CADUCIDAD EN CENTROS...
  📍 Centro Norte: 1 lotes críticos
  📍 Centro Sur: 1 lotes críticos

✅ Notificaciones creadas: 0  ← ⚠️ Debe ser 0 (duplicados prevenidos)
```

**Verificar BD:**
```sql
-- Contar notificaciones creadas en últimas 24h para usuario_norte
SELECT COUNT(*) as debe_ser_1
FROM notificaciones n
JOIN usuarios u ON n.usuario_id = u.id
WHERE u.username = 'usuario_norte'
  AND n.datos::jsonb->>'tipo_alerta' = 'caducidad_critica_centro'
  AND n.created_at >= CURRENT_TIMESTAMP - INTERVAL '24 hours';
```

**Resultado Esperado:** `debe_ser_1 = 1` (solo la primera ejecución)

**Forzar duplicados:**
```bash
python manage.py generar_alertas_inventario --forzar
```

**Verificar:**
```sql
-- Ahora debe haber 2
SELECT COUNT(*) as debe_ser_2
FROM notificaciones n
JOIN usuarios u ON n.usuario_id = u.id
WHERE u.username = 'usuario_norte'
  AND n.datos::jsonb->>'tipo_alerta' = 'caducidad_critica_centro'
  AND n.created_at >= CURRENT_TIMESTAMP - INTERVAL '24 hours';
```

**Status:** ⬜ POR VERIFICAR

---

### Escenario 4: Lotes sin Stock (No debe alertar)

**Setup:**
```sql
-- Lote caducado pero sin stock (NO debe generar alerta)
INSERT INTO lotes 
(producto_id, numero_lote, fecha_caducidad, cantidad_actual, activo)
VALUES (1, 'F-AGOT-001', CURRENT_DATE - INTERVAL '10 days', 0, true);
```

**Ejecutar:**
```bash
python manage.py generar_alertas_inventario --dry-run
```

**Verificar Output:**
```
📅 VERIFICANDO CADUCIDADES...
  Lotes caducados con stock: 0  ← ⚠️ Debe ser 0
```

**Status:** ⬜ POR VERIFICAR

---

### Escenario 5: Lotes Próximos (15-30 días)

**Setup:**
```sql
-- Lote que vence en 25 días (fuera de crítico, dentro de próximo)
INSERT INTO lotes 
(producto_id, numero_lote, fecha_caducidad, cantidad_actual, activo)
VALUES (1, 'F-PROX-001', CURRENT_DATE + INTERVAL '25 days', 200, true);
```

**Ejecutar:**
```bash
python manage.py generar_alertas_inventario
```

**Verificar:**
```sql
SELECT 
    n.titulo, n.tipo, 
    n.datos::jsonb->>'tipo_alerta' as tipo_alerta
FROM notificaciones n
WHERE n.datos::jsonb->>'tipo_alerta' = 'caducidad_proxima'
ORDER BY n.created_at DESC
LIMIT 1;
```

**Resultado Esperado:**
| titulo | tipo | tipo_alerta |
|--------|------|-------------|
| ⚠️ Alerta: 1 Lotes Próximos a Caducar | warning | caducidad_proxima |

**Status:** ⬜ POR VERIFICAR

---

## 📊 Matriz de Verificación Completa

| # | Escenario | Inventario | Criterio | Status | Evidencia |
|---|-----------|------------|----------|--------|-----------|
| 1 | Lote crítico ≤15d | Farmacia | Notifica tipo=error | ⬜ | SQL query + screenshot |
| 2 | Lote próximo 15-30d | Farmacia | Notifica tipo=warning | ⬜ | SQL query + screenshot |
| 3 | Lote caducado | Farmacia | Notifica tipo=error | ⬜ | SQL query + screenshot |
| 4 | Lote sin stock | Farmacia | NO notifica | ⬜ | Output dry-run |
| 5 | Stock bajo | Farmacia | Notifica tipo=warning | ⬜ | SQL query + screenshot |
| 6 | Lote crítico centro | Centro | Notifica solo usuarios del centro | ⬜ | SQL aislamiento |
| 7 | Múltiples centros | Centros | Cada centro ve solo sus lotes | ⬜ | SQL count por centro |
| 8 | Duplicados 24h | Ambos | NO crea si existe reciente | ⬜ | Output + COUNT(*) |
| 9 | Flag --forzar | Ambos | Crea aunque existan duplicados | ⬜ | COUNT incrementa |
| 10 | Dry-run mode | Ambos | Muestra alertas pero COUNT=0 | ⬜ | Output + SQL COUNT |
| 11 | Usuarios inactivos | Ambos | NO notifica | ⬜ | SQL with is_active=false |
| 12 | Centros sin usuarios | Centro | Omite centro | ⬜ | Output warning |

---

## 🚨 Casos Límite

### 1. Centro sin Usuarios Activos

```sql
-- Centro activo pero sin usuarios
INSERT INTO centros (clave, nombre, activo) VALUES ('C99', 'Centro Vacío', true);

-- Lote crítico en ese centro
INSERT INTO inventario_caja_chica 
(centro_id, descripcion_producto, fecha_caducidad, cantidad_actual, activo)
VALUES 
((SELECT id FROM centros WHERE clave='C99'), 'Producto Test', CURRENT_DATE + INTERVAL '5 days', 10, true);
```

**Comportamiento Esperado:**
```
🏥 VERIFICANDO CADUCIDAD EN CENTROS...
  ⚠️  Centro Vacío: Sin usuarios activos para notificar
```

**Status:** ⬜ POR VERIFICAR

### 2. Lote sin fecha_caducidad

```sql
-- Lote sin fecha (campo nullable)
INSERT INTO inventario_caja_chica 
(centro_id, descripcion_producto, fecha_caducidad, cantidad_actual, activo)
VALUES 
((SELECT id FROM centros WHERE clave='C01'), 'Producto Sin Fecha', NULL, 50, true);
```

**Comportamiento Esperado:** NO debe incluirse en ninguna alerta de caducidad.

**Verificación:**
```python
# En el query hay filtro:
InventarioCajaChica.objects.filter(
    fecha_caducidad__isnull=False,  # ✅ Excluye NULL
    ...
)
```

**Status:** ⬜ POR VERIFICAR

### 3. Performance con Muchos Lotes

**Setup:**
```python
# Crear 1000 lotes críticos
from datetime import date, timedelta
from core.models import Lote, Producto

producto = Producto.objects.first()
hoy = date.today()

lotes = [
    Lote(
        producto=producto,
        numero_lote=f'PERF-{i:04d}',
        fecha_caducidad=hoy + timedelta(days=10),
        cantidad_actual=10,
        activo=True
    )
    for i in range(1000)
]
Lote.objects.bulk_create(lotes)
```

**Ejecutar con tiempo:**
```bash
time python manage.py generar_alertas_inventario
```

**Verificar:**
- Tiempo ejecución <10 segundos
- Output muestra "... y 990 más" (limita a 10 en mensaje)
- Solo 1 notificación por usuario (notifica agrupado)

**Status:** ⬜ POR VERIFICAR

---

## 🐛 Debugging

### Ver Notificaciones Creadas

```sql
-- Últimas 20 notificaciones de caducidad
SELECT 
    n.id,
    n.created_at,
    n.tipo,
    n.titulo,
    u.username,
    u.rol,
    u.centro_id,
    n.datos::jsonb->>'tipo_alerta' as tipo_alerta,
    n.datos::jsonb->>'centro_nombre' as centro,
    n.datos::jsonb->>'cantidad_lotes' as cantidad
FROM notificaciones n
JOIN usuarios u ON n.usuario_id = u.id
WHERE n.datos::jsonb->>'tipo_alerta' LIKE '%caducidad%'
   OR n.datos::jsonb->>'tipo_alerta' LIKE '%caducados%'
ORDER BY n.created_at DESC
LIMIT 20;
```

### Ver Lotes Críticos (Debe coincidir con output)

```sql
-- Farmacia
SELECT COUNT(*) as lotes_criticos_farmacia
FROM lotes
WHERE activo = true
  AND cantidad_actual > 0
  AND fecha_caducidad >= CURRENT_DATE
  AND fecha_caducidad <= CURRENT_DATE + INTERVAL '15 days';

-- Por Centro
SELECT 
    c.nombre as centro,
    COUNT(*) as lotes_criticos
FROM inventario_caja_chica icc
JOIN centros c ON icc.centro_id = c.id
WHERE icc.activo = true
  AND icc.cantidad_actual > 0
  AND icc.fecha_caducidad IS NOT NULL
  AND icc.fecha_caducidad >= CURRENT_DATE
  AND icc.fecha_caducidad <= CURRENT_DATE + INTERVAL '15 days'
GROUP BY c.nombre
ORDER BY lotes_criticos DESC;
```

### Logs del Comando

```bash
# Ver logs en Render
render logs --service farmacia-alertas --tail 100

# Localmente con DEBUG
python manage.py generar_alertas_inventario 2>&1 | tee alertas.log
```

---

## 📝 Checklist de Deployment

### Pre-Despliegue

- [x] Código revisado y testeado localmente
- [x] Umbrales ajustados a 15/30 días
- [x] Comando extendido con soporte para InventarioCajaChica
- [x] Aislamiento por centro validado
- [x] Prevención de duplicados implementada
- [x] Cron job configurado en render.yaml
- [ ] Todos los casos de prueba ejecutados (Matriz QA)
- [ ] Documentación completa revisada

### Post-Despliegue

- [ ] Ejecutar `--dry-run` en producción
- [ ] Verificar BD no tiene lotes test antiguos
- [ ] Confirmar plan Render permite cron jobs
- [ ] Activar cron job en dashboard Render
- [ ] Monitorear primera ejecución (logs)
- [ ] Validar notificaciones en UI de usuarios
- [ ] Confirmar emails/alertas si están configurados

### Rollback Plan

Si algo falla:

1. **Desactivar cron job** en Render dashboard
2. **Revertir comando** a versión anterior:
   ```bash
   git revert <commit_hash>
   git push origin main
   ```
3. **Notificaciones ya creadas** permanecen (no se eliminan)
4. **Ejecutar manual** mientras se soluciona:
   ```bash
   python manage.py generar_alertas_inventario --dry-run
   ```

---

## 📚 Referencias

### Archivos Modificados

- `backend/core/management/commands/generar_alertas_inventario.py`
  - Línea 36: Ajuste umbral crítico 7→15 días
  - Línea 54: Import InventarioCajaChica, Centro
  - Líneas 295-490: Sección completa de alertas para centros

- `render.yaml`
  - Líneas 133-165: Cron job descomentado y documentado

### Modelos Relacionados

- `Lote` (models.py:1039) - Inventario Farmacia
- `InventarioCajaChica` (models.py:4224) - Inventario Centros
- `Notificacion` (models.py:???) - Sistema de notificaciones
- `User` (custom user model) - Campo `centro_id` para filtrado

### Documentación Relacionada

- `docs/AUDITORIA_COMPRAS_CAJA_CHICA.md` - Notificaciones de compras
- `docs/FLUJO_CAJA_CHICA_FARMACIA.md` - Flujo general caja chica
- `docs/IMPORTADOR_LOTES_ACTUALIZADO.md` - Gestión de lotes

---

## 🔄 Próximas Mejoras

### Corto Plazo

- [ ] **UI Dashboard:** Panel visual con métricas de lotes críticos
- [ ] **Email Alerts:** Enviar emails además de notificaciones in-app
- [ ] **Webhook Slack/Teams:** Notificar equipos externos
- [ ] **Reporte Semanal:** Resumen consolidado de lotes por centro

### Medio Plazo

- [ ] **Umbrales Personalizables por Centro:** Cada centro define sus días críticos
- [ ] **Alertas por Producto Controlado:** Mayor urgencia para NOM-059
- [ ] **Predicción de Caducidad:** ML para estimar consumo y alertar antes
- [ ] **Integración con Compras:** Sugerir reabastecimiento automático

### Largo Plazo

- [ ] **App Móvil:** Push notifications en iOS/Android
- [ ] **Sistema de Escalamiento:** Alertas escalan a supervisores si no se atienden
- [ ] **Auditoría Regulatoria:** Evidencia de alertas para COFEPRIS/SSA
- [ ] **Recomendaciones IA:** "Transferir lote X a Centro Y para consumirlo a tiempo"

---

## 👥 Responsables

| Rol | Nombre | Responsabilidad |
|-----|--------|-----------------|
| QA Lead | [Tu Nombre] | Validación completa de casos |
| Backend Lead | [Tu Nombre] | Implementación y performance |
| DevOps | [Tu Nombre] | Configuración cron y monitoring |
| Product Owner | [Stakeholder] | Aprobación de umbrales y alcance |

---

## 📞 Soporte

**Errores en producción:**
1. Revisar logs: `render logs --service farmacia-alertas`
2. Verificar BD: Ejecutar queries de debugging (sección 🐛)
3. Deshabilitar cron si es crítico
4. Escalar a Backend Lead

**Preguntas frecuentes:**

**Q: ¿Por qué no recibo notificaciones?**  
A: Verifica:
- Tu usuario tiene `is_active=True`
- Tu `centro_id` coincide con lotes del InventarioCajaChica
- No hay notificaciones recientes (24h window)
- Ejecutar `--dry-run` para ver si hay lotes críticos

**Q: ¿Puedo cambiar los umbrales?**  
A: Sí, usa flags: `--dias-critico=10 --dias-caducidad=20`

**Q: ¿Cómo probar sin afectar producción?**  
A: Usa `--dry-run` - muestra alertas pero no crea notificaciones.

---

**Última actualización:** 2025-01-XX  
**Versión:** 1.0  
**Status:** ✅ IMPLEMENTADO, ⏳ PENDIENTE QA VERIFICATION

