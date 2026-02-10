# Flujo de Compras de Caja Chica con Verificación de Farmacia

## Descripción

El flujo de compras de caja chica ahora incluye un paso obligatorio de verificación con Farmacia Central antes de que el centro pueda proceder con la compra.

## Diagrama del Flujo

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                     FLUJO DE COMPRAS CAJA CHICA                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌───────────────┐
│   PENDIENTE   │  ← Centro crea solicitud con justificación
│  (Médico/Centro)│
└───────┬───────┘
        │
        │ enviar_farmacia
        ▼
┌───────────────────┐
│ ENVIADA_FARMACIA  │  ← Farmacia Central recibe para verificar
│    (Farmacia)     │
└───────┬───────────┘
        │
        ├──────────────────────────────────────┐
        │                                      │
        │ confirmar_sin_stock                  │ rechazar_tiene_stock
        ▼                                      ▼
┌───────────────────┐              ┌────────────────────────┐
│ SIN_STOCK_FARMACIA│              │  RECHAZADA_FARMACIA    │
│   (Continúa)      │              │ (Usar requisición normal)│
└───────┬───────────┘              └────────────────────────┘
        │
        │ enviar_admin
        ▼
┌───────────────────┐
│   ENVIADA_ADMIN   │  ← Admin del centro recibe para autorizar
│      (Admin)      │
└───────┬───────────┘
        │
        │ autorizar_admin
        ▼
┌───────────────────┐
│ AUTORIZADA_ADMIN  │  ← Admin autoriza, envía a Director
│      (Admin)      │
└───────┬───────────┘
        │
        │ enviar_director
        ▼
┌───────────────────┐
│ ENVIADA_DIRECTOR  │  ← Director del centro recibe
│    (Director)     │
└───────┬───────────┘
        │
        │ autorizar_director
        ▼
┌───────────────────┐
│    AUTORIZADA     │  ← Lista para comprar
│  (Médico/Centro)  │
└───────┬───────────┘
        │
        │ registrar_compra
        ▼
┌───────────────────┐
│     COMPRADA      │  ← Se realizó la compra
│  (Médico/Centro)  │
└───────┬───────────┘
        │
        │ registrar_recepcion
        ▼
┌───────────────────┐
│     RECIBIDA      │  ← Productos ingresados al inventario
│     (Final)       │
└───────────────────┘
```

## Estados del Flujo

| Estado | Descripción | Actor | Color UI |
|--------|-------------|-------|----------|
| `pendiente` | Centro crea solicitud | Médico/Centro | Amarillo |
| `enviada_farmacia` | Esperando verificación de stock | Farmacia | Ámbar |
| `sin_stock_farmacia` | Farmacia confirma NO disponibilidad | Médico/Centro | Verde Azulado |
| `rechazada_farmacia` | Farmacia indica SÍ hay stock | Médico/Centro | Rosa |
| `enviada_admin` | Esperando autorización de Admin | Admin Centro | Naranja |
| `autorizada_admin` | Admin aprobó, listo para Director | Admin Centro | Púrpura |
| `enviada_director` | Esperando autorización de Director | Director Centro | Índigo |
| `autorizada` | Director aprobó, lista para comprar | Médico/Centro | Verde |
| `comprada` | Compra realizada | Médico/Centro | Azul |
| `recibida` | Productos recibidos | - | Verde (final) |
| `cancelada` | Cancelada en cualquier punto | - | Gris |
| `rechazada` | Rechazada por Admin/Director | - | Rojo |

## Permisos por Rol

### Médico/Centro
- Crear solicitudes
- Enviar a Farmacia (desde `pendiente`)
- Enviar a Admin (desde `sin_stock_farmacia`)
- Registrar compra (desde `autorizada`)
- Registrar recepción (desde `comprada`)
- Cancelar (estados intermedios)

### Farmacia
- Verificar stock (`enviada_farmacia`)
  - Confirmar sin stock → `sin_stock_farmacia`
  - Rechazar con stock → `rechazada_farmacia`

### Administrador del Centro
- Autorizar (`enviada_admin` → `autorizada_admin`)
- Enviar a Director (`autorizada_admin` → `enviada_director`)
- Rechazar o devolver

### Director del Centro
- Autorizar final (`enviada_director` → `autorizada`)
- Rechazar o devolver

## Endpoints API

### Flujo Farmacia
```
POST /api/compras-caja-chica/{id}/enviar-farmacia/
POST /api/compras-caja-chica/{id}/confirmar-sin-stock/
POST /api/compras-caja-chica/{id}/rechazar-tiene-stock/
```

### Flujo Multinivel
```
POST /api/compras-caja-chica/{id}/enviar-admin/
POST /api/compras-caja-chica/{id}/autorizar-admin/
POST /api/compras-caja-chica/{id}/enviar-director/
POST /api/compras-caja-chica/{id}/autorizar-director/
POST /api/compras-caja-chica/{id}/rechazar/
POST /api/compras-caja-chica/{id}/devolver/
```

### Compra y Recepción
```
POST /api/compras-caja-chica/{id}/registrar_compra/
POST /api/compras-caja-chica/{id}/recibir/
POST /api/compras-caja-chica/{id}/cancelar/
```

## Migración SQL

El archivo `backend/sql_caja_chica_flujo_multinivel.sql` contiene las migraciones necesarias para:

1. **Nuevos campos de Farmacia:**
   - `fecha_envio_farmacia` - Timestamp
   - `fecha_respuesta_farmacia` - Timestamp
   - `verificado_por_farmacia_id` - FK a usuarios
   - `respuesta_farmacia` - TEXT
   - `stock_farmacia_verificado` - INTEGER

2. **Actualización de constraint de estado** para incluir los 12 estados.

3. **Índices** para optimizar consultas.

### Ejecutar migración en Supabase

```sql
-- Copiar y ejecutar el contenido de:
-- backend/sql_caja_chica_flujo_multinivel.sql
```

## Archivos Modificados

### Backend
- `backend/core/models.py` - Modelo CompraCajaChica con nuevos estados y campos
- `backend/core/serializers.py` - Serializer con campos de farmacia y acciones
- `backend/core/views.py` - Nuevos endpoints de farmacia

### Frontend
- `inventario-front/src/pages/ComprasCajaChica.jsx` - UI completa con flujo farmacia
- `inventario-front/src/services/api.js` - Endpoints de farmacia

## Lógica de Negocio

### ¿Por qué este flujo?

1. **Prevención de compras innecesarias**: Farmacia Central debe confirmar que NO tiene el producto antes de que el centro gaste recursos propios.

2. **Trazabilidad**: Se registra quién verificó, cuándo y qué stock encontró.

3. **Transparencia**: Si Farmacia tiene stock, el centro debe hacer una requisición regular en lugar de compra de caja chica.

### Casos de Uso

**Caso 1: Farmacia NO tiene stock**
```
Centro crea solicitud → Envía a Farmacia → Farmacia confirma "sin stock" 
→ Centro envía a Admin → Admin autoriza → Envía a Director 
→ Director autoriza → Centro compra → Centro recibe
```

**Caso 2: Farmacia SÍ tiene stock**
```
Centro crea solicitud → Envía a Farmacia → Farmacia rechaza "hay stock" 
→ Centro hace requisición normal en lugar de compra de caja chica
```
