# 📋 FLUJO DE REQUISICIONES - FARMACIA PENITENCIARIA

## 🔄 Diagrama de Estados

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CENTRO PENITENCIARIO                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────┐    ┌─────────────────┐    ┌──────────────────┐                │
│  │ BORRADOR │───►│ PENDIENTE_ADMIN │───►│ PENDIENTE_DIRECTOR│               │
│  │ (Médico) │◄───│ (Administrador) │    │    (Director)     │               │
│  └──────────┘    └─────────────────┘    └──────────────────┘               │
│       ▲                   │                      │                          │
│       │                   │                      │                          │
│       │             ┌─────┴──────┐         ┌─────┴──────┐                   │
│       │             ▼            ▼         ▼            ▼                   │
│       │      ╔════════════╗  ╔════════╗  ╔════════════╗ ╔════════╗         │
│       └──────║ DEVUELTA   ║  ║RECHAZADA║ ║ DEVUELTA   ║ ║RECHAZADA║        │
│  (corrige)   ╚════════════╝  ╚════════╝  ╚════════════╝ ╚════════╝         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ (ENVIADA)
┌─────────────────────────────────────────────────────────────────────────────┐
│                          FARMACIA CENTRAL                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────┐    ┌────────────┐    ┌────────────┐    ┌─────────────┐        │
│  │ ENVIADA │───►│ EN_REVISION│───►│ AUTORIZADA │───►│  EN_SURTIDO │        │
│  │(recibe) │    │  (revisa)  │    │(fecha lím.)│    │  (prepara)  │        │
│  └─────────┘    └────────────┘    └────────────┘    └─────────────┘        │
│       │               │                                    │                │
│       ▼               │                                    ▼                │
│  ╔════════════╗       │                             ┌───────────┐          │
│  ║ RECHAZADA  ║       │                             │  SURTIDA  │          │
│  ╚════════════╝       ▼                             │ (espera)  │          │
│                 ╔════════════╗                      └───────────┘          │
│                 ║ DEVUELTA   ║───────────────────────────┐                 │
│                 ╚════════════╝                           │                 │
│                       │                            ┌─────┴─────┐           │
│                       │ (regresa a BORRADOR)       ▼           ▼           │
│                       │                     ┌───────────┐ ╔═════════╗      │
│                       │                     │ ENTREGADA │ ║ VENCIDA ║      │
│                       ▼                     │   (FIN)   │ ╚═════════╝      │
│              ┌─────────────────┐            └───────────┘                  │
│              │   AL CENTRO     │                                            │
└──────────────┴─────────────────┴────────────────────────────────────────────┘

LEYENDA:
  ╔════════════╗  = Estado FINAL (no puede cambiar)
  └────────────┘  = Estado intermedio
  
  RECHAZADA: Requisición permanentemente rechazada (NO procede)
  DEVUELTA:  Regresa a BORRADOR para que médico corrija y reinicie ciclo
```

## 👥 Roles y Responsabilidades

### Centro Penitenciario

| Rol | Código | Responsabilidades |
|-----|--------|-------------------|
| **Médico** | `medico` | Crear requisiciones de medicamentos para pacientes |
| **Administrador** | `administrador_centro` | Primera autorización, validar necesidad |
| **Director** | `director_centro` | Segunda autorización, aprobación final del centro |

### Farmacia Central

| Rol | Código | Responsabilidades |
|-----|--------|-------------------|
| **Farmacia** | `farmacia` | Recibir, revisar, autorizar, surtir requisiciones |
| **Admin Sistema** | `admin` | Gestión completa, configuración, reportes |

---

## ⏱️ Control de Tiempos (Auditoría)

Cada requisición registra **todas las fechas críticas**:

```
fecha_solicitud ──────────────► Médico crea la requisición
        │
fecha_envio_admin ────────────► Se envía al Administrador
        │
fecha_autorizacion_admin ─────► Administrador autoriza
        │
fecha_envio_director ─────────► Se envía al Director
        │
fecha_autorizacion_director ──► Director autoriza
        │
fecha_envio_farmacia ─────────► Llega a Farmacia Central
        │
fecha_recepcion_farmacia ─────► Farmacia recibe formalmente
        │
fecha_autorizacion_farmacia ──► Farmacia autoriza + asigna fecha límite
        │
fecha_surtido ────────────────► Requisición lista para recolección
        │
   ┌────┴────┐
   │         │
   ▼         ▼
fecha_entrega    fecha_vencimiento
(se recolectó)   (NO se recolectó a tiempo)
```

---

## 🔐 Fecha Límite de Recolección

### ⚠️ PROCESO CRÍTICO

1. **Farmacia autoriza** → Asigna `fecha_recoleccion_limite`
2. **Se surte** → Estado cambia a `surtida`
3. **Centro debe recolectar** antes de la fecha límite

### ⏰ Si NO se recolecta a tiempo:

```
Estado: surtida
fecha_recoleccion_limite: 2024-12-10 17:00

┌─────────────────────────────────────┐
│ SISTEMA AUTOMÁTICO (cron diario)   │
│                                     │
│ IF fecha_recoleccion_limite < NOW() │
│ THEN estado = 'vencida'            │
│                                     │
│ • Se registra fecha_vencimiento    │
│ • Se registra motivo automático    │
│ • Se guarda en historial           │
└─────────────────────────────────────┘
```

---

## 📊 Tabla de Historial (Inmutable)

**Cada cambio de estado se registra automáticamente:**

| Campo | Descripción |
|-------|-------------|
| `requisicion_id` | ID de la requisición |
| `estado_anterior` | Estado antes del cambio |
| `estado_nuevo` | Estado después del cambio |
| `usuario_id` | Quién realizó el cambio |
| `fecha_cambio` | Cuándo se realizó |
| `accion` | Tipo de acción (autorizar, rechazar, etc.) |
| `motivo` | Razón del cambio (si aplica) |
| `ip_address` | IP desde donde se realizó |
| `datos_adicionales` | Contexto extra (JSON) |

---

## 📝 Ajustes de Cantidad

**Cuando Farmacia ajusta cantidades:**

```sql
-- Ejemplo: Farmacia no tiene suficiente stock

Producto: Paracetamol 500mg
Cantidad solicitada: 100 unidades
Cantidad ajustada: 50 unidades
Motivo: sin_stock
Justificación: "Stock insuficiente, próximo abastecimiento en 15 días"

-- Este ajuste queda registrado con:
- Usuario que ajustó
- Fecha del ajuste
- Tipo de ajuste
- Producto sustituto (si aplica)
```

---

## 🔒 Reglas de Transición

### Transiciones Válidas:

| Estado Actual | Puede ir a |
|--------------|------------|
| `borrador` | `pendiente_admin`, `cancelada` |
| `pendiente_admin` | `pendiente_director`, `rechazada`, `devuelta` |
| `pendiente_director` | `enviada`, `rechazada`, `devuelta` |
| `enviada` | `en_revision`, `autorizada`, `rechazada` |
| `en_revision` | `autorizada`, `rechazada`, `devuelta` |
| `autorizada` | `en_surtido`, `surtida`, `cancelada` |
| `en_surtido` | `surtida`, `cancelada` |
| `surtida` | `entregada`, `vencida` |
| `devuelta` | `pendiente_admin`, `cancelada` |

### Estados Finales (no pueden cambiar):
- ✅ `entregada`
- ❌ `rechazada`
- ⏰ `vencida`
- 🚫 `cancelada`

---

## 📈 Métricas Disponibles

La vista `vista_requisiciones_completa` incluye métricas automáticas:

| Métrica | Descripción |
|---------|-------------|
| `horas_en_admin` | Tiempo en autorización del administrador |
| `horas_en_director` | Tiempo en autorización del director |
| `horas_en_farmacia` | Tiempo de procesamiento en farmacia |
| `horas_en_recoleccion` | Tiempo esperando recolección |
| `dias_totales` | Días desde solicitud hasta entrega |

---

## 🛡️ Anti-Fraude

### Medidas implementadas:

1. **Trazabilidad completa**: Cada acción registra usuario, fecha, IP
2. **Historial inmutable**: Tabla de auditoría con triggers automáticos
3. **Validación de transiciones**: Solo estados válidos permitidos
4. **RLS (Row Level Security)**: Usuarios solo ven datos de su centro
5. **Firmas digitales**: Campos de firma obligatorios en puntos clave
6. **Hash de verificación**: Para detectar manipulación de registros

---

## 🔧 Configuración del Cron

Para verificar requisiciones vencidas, configurar en Supabase:

```sql
-- Ejecutar diariamente a las 00:01
SELECT cron.schedule(
    'verificar-requisiciones-vencidas',
    '1 0 * * *',
    'SELECT verificar_requisiciones_vencidas()'
);
```

---

## 📋 Checklist de Implementación

- [x] Ejecutar SQL en Supabase (Production)
- [x] Actualizar modelos Django (`managed = False`)
- [x] Actualizar serializers con nuevos campos
- [x] **Crear endpoints para cada transición de estado**
  - [x] `/enviar-admin/` - borrador → pendiente_admin
  - [x] `/autorizar-admin/` - pendiente_admin → pendiente_director
  - [x] `/autorizar-director/` - pendiente_director → enviada
  - [x] `/recibir-farmacia/` - enviada → en_revision
  - [x] `/autorizar-farmacia/` - en_revision → autorizada (con fecha límite)
  - [x] `/surtir/` - autorizada → surtida
  - [x] `/confirmar-entrega/` - surtida → entregada
  - [x] `/devolver/` - Devuelve al centro para corrección
  - [x] `/reenviar/` - Reenvía requisición devuelta
  - [x] `/marcar-vencida/` - Marca manualmente como vencida
  - [x] `/historial/` - Obtiene historial de cambios
  - [x] `/verificar-vencidas/` - Endpoint para cron
  - [x] `/transiciones-disponibles/` - Retorna acciones por rol
- [x] **Actualizar frontend con nuevo flujo**
  - [x] Actualizar constants/strings.js con nuevos estados y roles
  - [x] Actualizar services/api.js con nuevos endpoints
  - [x] Crear hook useRequisicionFlujo
  - [x] Crear componente EstadoBadge (compartido)
  - [x] Crear componente RequisicionAcciones
  - [x] Crear componente RequisicionHistorial
  - [x] Crear componente FechaRecoleccionModal
  - [x] Refactorizar Requisiciones.jsx para usar helpers compartidos
  - [x] Refactorizar RequisicionDetalle.jsx para usar helpers compartidos
- [x] Implementar pantalla de asignación de fecha límite (FechaRecoleccionModal)
- [x] **Configurar cron de verificación de vencimientos**
  - [x] Crear script `scripts/verificar_vencidas.py`
  - [x] Crear management command `python manage.py verificar_vencidas`
  - [x] Endpoint API: `POST /api/requisiciones/verificar-vencidas/`
- [x] **Pruebas de integración del flujo completo**
  - [x] Crear `inventario/tests/test_flujo_v2.py`
  - [x] Tests del flujo completo exitoso
  - [x] Tests de devolución y reenvío
  - [x] Tests de permisos por rol
  - [x] Tests de validaciones (fecha límite, motivos, etc.)
  - [x] Tests del historial de estados
- [x] Documentar API de transiciones

---

## 🔌 API de Transiciones - Endpoints

### Flujo Jerárquico del Centro

| Endpoint | Método | Transición | Rol Requerido |
|----------|--------|------------|---------------|
| `/api/requisiciones/{id}/enviar-admin/` | POST | borrador → pendiente_admin | medico |
| `/api/requisiciones/{id}/autorizar-admin/` | POST | pendiente_admin → pendiente_director | administrador_centro |
| `/api/requisiciones/{id}/autorizar-director/` | POST | pendiente_director → enviada | director_centro |

### Flujo Farmacia Central

| Endpoint | Método | Transición | Rol Requerido |
|----------|--------|------------|---------------|
| `/api/requisiciones/{id}/recibir-farmacia/` | POST | enviada → en_revision | farmacia |
| `/api/requisiciones/{id}/autorizar-farmacia/` | POST | en_revision → autorizada | farmacia |
| `/api/requisiciones/{id}/surtir/` | POST | autorizada → surtida | farmacia |
| `/api/requisiciones/{id}/confirmar-entrega/` | POST | surtida → entregada | medico/centro |

### Acciones Especiales

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/requisiciones/{id}/devolver/` | POST | Devolver al centro (requiere motivo) |
| `/api/requisiciones/{id}/reenviar/` | POST | Reenviar requisición devuelta |
| `/api/requisiciones/{id}/marcar-vencida/` | POST | Marcar como vencida (admin) |
| `/api/requisiciones/{id}/historial/` | GET | Ver historial de cambios |
| `/api/requisiciones/verificar-vencidas/` | POST | Verificar y marcar vencidas (cron) |
| `/api/requisiciones/transiciones-disponibles/` | GET | Acciones disponibles por rol |

---

*Documento generado: 2024-12-08*
*Última actualización: 2025-12-09*
*Versión: 2.1*
