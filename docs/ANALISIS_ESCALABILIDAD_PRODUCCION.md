# 📊 ANÁLISIS DE ESCALABILIDAD PARA PRODUCCIÓN

**Fecha**: 5 de marzo de 2026  
**Sistema**: Farmacia Penitenciaria - Estado de México  
**Preparado para**: Uso masivo multi-centro

---

## ❌ ESTADO ACTUAL - CONFIGURACIÓN NO APTA PARA PRODUCCIÓN MASIVA

### 🔴 Hallazgos Críticos

| Componente | Estado Actual | Problema | Impacto |
|------------|---------------|----------|---------|
| **Plan Render** | `free` | Servidor duerme en inactividad | ❌ Esperas de 30-60s en primera conexión |
| **Workers Gunicorn** | `2` | Muy bajo para carga concurrente | ❌ Bloqueos con 5+ usuarios simultáneos |
| **Autoscaling** | ❌ No configurado | Sin escalado automático | ❌ Caídas con tráfico alto |
| **Instancias** | `1` | Instancia única sin redundancia | ❌ Punto único de falla |
| **Caché Redis** | ❌ No conectado | Sin caché distribuido | ❌ Consultas repetitivas a BD |
| **Conexiones BD** | `conn_max_age=600s` | ✅ Configurado | ✅ Pool de conexiones activo |
| **Pool de conexiones** | Por defecto | Sin tuning específico | ⚠️ Puede saturarse |

---

## 📈 CONFIGURACIÓN RECOMENDADA PARA USO MASIVO

### 🎯 Escenario: 50-200 usuarios simultáneos en múltiples centros

### 1️⃣ **PLAN RENDER - UPGRADE NECESARIO**

```yaml
# Actualización en render.yaml
plan: standard  # $25/mes (MÍNIMO para producción)
# o
plan: pro       # $85/mes (recomendado para 100+ usuarios)
```

**Beneficios Standard/Pro:**
- ✅ Servidor SIEMPRE activo (sin cold starts)
- ✅ Más CPU y RAM
- ✅ Autoscaling disponible
- ✅ Soporte prioritario

---

### 2️⃣ **AUTOSCALING - CONFIGURACIÓN CRÍTICA**

**Agregar a render.yaml:**

```yaml
services:
  - type: web
    name: farmacia-api
    plan: standard  # o pro
    
    # ═══════════════════════════════════════════════════════════
    # AUTOSCALING - Escalado automático basado en carga
    # ═══════════════════════════════════════════════════════════
    autoDeploy: true
    
    scaling:
      minInstances: 2        # Mínimo 2 instancias (redundancia)
      maxInstances: 5        # Hasta 5 instancias en picos
      targetMemoryPercent: 80   # Escalar si RAM > 80%
      targetCPUPercent: 70      # Escalar si CPU > 70%
    
    # Más workers para manejar concurrencia
    startCommand: >
      gunicorn config.wsgi:application 
      --bind 0.0.0.0:$PORT 
      --workers 4 
      --threads 2
      --timeout 300
      --max-requests 1000
      --max-requests-jitter 50
      --access-logfile -
      --error-logfile -
      --log-level info
```

**Explicación de workers:**
- **4 workers**: Fórmula `(2 x núcleos CPU) + 1`
- **2 threads por worker**: Total 8 conexiones concurrentes por instancia
- **Con 2-5 instancias**: 16-40 conexiones simultáneas
- **max-requests**: Reinicia workers cada 1000 requests (previene memory leaks)

---

### 3️⃣ **REDIS CACHE - OBLIGATORIO PARA ESCALABILIDAD**

**Agregar servicio Redis en render.yaml:**

```yaml
  # ═══════════════════════════════════════════════════════════════════════════
  # REDIS - Cache distribuido (CRÍTICO para múltiples instancias)
  # ═══════════════════════════════════════════════════════════════════════════
  - type: redis
    name: farmacia-redis
    plan: starter       # $7/mes - 256MB (suficiente para empezar)
    # plan: standard    # $15/mes - 1GB (recomendado para 100+ usuarios)
    maxmemoryPolicy: allkeys-lru  # Eliminar keys menos usadas cuando se llena
    
    # Redis se conecta automáticamente al backend vía REDIS_URL
```

**¿Por qué Redis es crítico?**
- ✅ Cache compartido entre todas las instancias
- ✅ Sesiones persistentes (sin pérdida al escalar)
- ✅ Reduce carga en BD en 60-80%
- ✅ Respuestas de dashboard en <50ms vs 500ms

---

### 4️⃣ **OPTIMIZACIONES DE BASE DE DATOS**

**Actualizar variables de entorno en Render Dashboard:**

```bash
# Conexiones por worker
DB_CONN_MAX_AGE=600              # Pool de conexiones (10 min)
DB_POOL_SIZE_MIN=5               # Mínimo 5 conexiones por instancia
DB_POOL_SIZE_MAX=20              # Máximo 20 conexiones por instancia

# Timeouts
DB_CONNECT_TIMEOUT=10            # Timeout de conexión
DB_STATEMENT_TIMEOUT=30000       # Timeout de query (30s)
DB_IDLE_IN_TRANSACTION_TIMEOUT=60000  # Timeout de transacción idle
```

**Supabase/PostgreSQL - Configuración recomendada:**
```bash
# Usar Connection Pooler SIEMPRE
DATABASE_URL=postgresql://postgres.[REF]:[PASS]@[region].pooler.supabase.com:6543/postgres

# Pool settings en Supabase Dashboard:
- Pool mode: Transaction (mejor para Django)
- Pool size: 50-100 (dependiendo del plan)
```

---

### 5️⃣ **HEALTH CHECKS Y MONITORING**

**Agregar a render.yaml:**

```yaml
  - type: web
    name: farmacia-api
    
    # Health check para load balancer
    healthCheckPath: /api/health/
    
    # Variables de monitoreo
    envVars:
      - key: ENABLE_METRICS
        value: "True"
      
      - key: SENTRY_DSN
        sync: false  # Configurar Sentry para error tracking
```

**Crear endpoint de health en Django:**
```python
# backend/core/views.py
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache

def health_check(request):
    """Health check para load balancer"""
    status = {"status": "healthy", "checks": {}}
    
    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        status["checks"]["database"] = "ok"
    except Exception as e:
        status["checks"]["database"] = f"error: {str(e)}"
        status["status"] = "unhealthy"
    
    # Check cache
    try:
        cache.set("health_check", "ok", 10)
        cache.get("health_check")
        status["checks"]["cache"] = "ok"
    except Exception as e:
        status["checks"]["cache"] = f"error: {str(e)}"
    
    return JsonResponse(status)
```

---

## 📊 ESTIMACIÓN DE CAPACIDAD

### Con configuración actual (free plan + 2 workers):
- ❌ **Usuarios simultáneos**: 3-5
- ❌ **Requests/segundo**: ~5
- ❌ **Cold start**: 30-60 segundos
- ❌ **Uptime**: ~99% (con dormidas frecuentes)

### Con configuración optimizada (Standard + autoscaling + Redis):
- ✅ **Usuarios simultáneos**: 50-150
- ✅ **Requests/segundo**: ~100
- ✅ **Latencia promedio**: <200ms
- ✅ **Uptime**: 99.9%
- ✅ **Sin cold starts**: Servidor siempre activo

### Con configuración Pro + autoscaling avanzado:
- ✅ **Usuarios simultáneos**: 200-500
- ✅ **Requests/segundo**: ~300
- ✅ **Latencia promedio**: <100ms
- ✅ **Uptime**: 99.95%

---

## 💰 COSTOS MENSUALES ESTIMADOS

| Configuración | Costo Mensual | Usuarios Soportados |
|---------------|---------------|---------------------|
| **Actual (Free)** | $0 | 3-5 ❌ |
| **Básica: Standard + Redis Starter** | $32/mes | 50-100 ✅ |
| **Recomendada: Pro + Redis Standard** | $100/mes | 100-200 ✅ |
| **Enterprise: Pro + Redis Pro + PG** | $200+/mes | 500+ ✅ |

**Desglose configuración recomendada:**
```
Backend (Pro):         $85/mes
Redis (Standard):      $15/mes
Total:                $100/mes
```

---

## 🚀 PLAN DE IMPLEMENTACIÓN

### Fase 1: Upgrade Inmediato (Sin downtime)
1. ✅ Cambiar plan de `free` a `standard` en Render Dashboard
2. ✅ Agregar servicio Redis Starter ($7/mes)
3. ✅ Actualizar workers a 4 en startCommand
4. ✅ Configurar variables de entorno (REDIS_URL se conecta auto)

**Tiempo**: 15 minutos  
**Downtime**: 0 (cambio en caliente)  
**Costo**: +$32/mes  
**Capacidad**: 3-5 → 50-100 usuarios

---

### Fase 2: Autoscaling (Planificado)
1. Actualizar `render.yaml` con configuración de scaling
2. Agregar health check endpoint
3. Commit y push a repositorio
4. Render redeploy automático

**Tiempo**: 30 minutos  
**Downtime**: 2-3 minutos en redeploy  
**Costo**: $0 adicional  
**Capacidad**: 50-100 → 100-150 usuarios

---

### Fase 3: Production-Ready (Opcional)
1. Upgrade a plan Pro
2. Redis Standard o Pro
3. Configurar Sentry para error tracking
4. Implementar métricas con Prometheus/Grafana
5. Agregar CDN para assets estáticos

**Tiempo**: 2 horas  
**Costo**: +$68/mes (total $100/mes)  
**Capacidad**: 100-150 → 200-500 usuarios

---

## ⚠️ RIESGOS ACTUALES SIN UPGRADE

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Caída por tráfico alto | 🔴 Alta | Crítico | Upgrade a Standard + autoscaling |
| Cold starts (esperas 60s) | 🔴 Muy Alta | Alto | Upgrade a Standard |
| Sin redundancia | 🔴 Alta | Crítico | Autoscaling con minInstances: 2 |
| Sesiones perdidas al redeploy | 🟡 Media | Medio | Redis para sesiones |
| Queries lentas sin caché | 🔴 Alta | Alto | Redis cache |

---

## ✅ CHECKLIST DE VALIDACIÓN POST-UPGRADE

Después de implementar, verificar:

```bash
# 1. Verificar múltiples instancias activas
curl https://farmacia-api.onrender.com/api/health/
# Ejecutar varias veces y verificar diferentes instance IDs

# 2. Test de carga con Apache Bench
ab -n 1000 -c 50 https://farmacia-api.onrender.com/api/dashboard/

# 3. Verificar Redis conectado
# En Django shell:
from django.core.cache import cache
cache.set('test', 'ok', 60)
print(cache.get('test'))  # Debe retornar 'ok'

# 4. Verificar workers activos
# En logs de Render buscar:
"Booting worker with pid: XXXX"  # Debe aparecer 4 veces
```

---

## 📞 SOPORTE Y SIGUIENTES PASOS

**Recomendación**: Implementar **Fase 1** INMEDIATAMENTE antes del lanzamiento oficial.

**Contacto**: 
- Documentación Render: https://render.com/docs/scaling
- Documentación Gunicorn: https://docs.gunicorn.org/en/stable/settings.html
- Redis Django: https://django-redis-cache.readthedocs.io/

---

**Último actualizado**: 5 de marzo de 2026  
**Revisión**: v1.0 - Análisis inicial de escalabilidad
