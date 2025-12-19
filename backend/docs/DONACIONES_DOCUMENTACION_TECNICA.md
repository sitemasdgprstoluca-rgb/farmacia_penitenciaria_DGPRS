# Documentación Técnica - Módulo de Donaciones

> **Fecha de actualización:** 19 de Diciembre de 2024  
> **Sistema:** Farmacia Penitenciaria - Inventario

---

## 1. Resumen Ejecutivo

El módulo de **Donaciones** opera como un **inventario completamente separado** del inventario principal de la farmacia. Esta separación garantiza:

- ✅ Catálogo de productos independiente (`productos_donacion`)
- ✅ Control de stock separado (`cantidad_disponible` en `detalle_donaciones`)
- ✅ Sin afectación a tabla `movimientos` del inventario principal
- ✅ Sin relación con tabla `lotes` del inventario principal

---

## 2. Archivos del Sistema Modificados

### 2.1 Backend (Django)

| Archivo | Ubicación | Función |
|---------|-----------|---------|
| `models.py` | `backend/core/models.py` | Modelos: `ProductoDonacion`, `Donacion`, `DetalleDonacion`, `SalidaDonacion` |
| `serializers.py` | `backend/core/serializers.py` | Serializers con validación y auto-generación de clave |
| `views.py` | `backend/core/views.py` | ViewSets: `DonacionViewSet`, `ProductoDonacionViewSet`, `DetalleDonacionViewSet`, `SalidaDonacionViewSet` |
| `urls.py` | `backend/core/urls.py` | Rutas API: `/api/donaciones/`, `/api/productos-donacion/`, etc. |

### 2.2 Frontend (React)

| Archivo | Ubicación | Función |
|---------|-----------|---------|
| `Donaciones.jsx` | `inventario-front/src/pages/Donaciones.jsx` | Página principal del módulo |
| `api.js` | `inventario-front/src/services/api.js` | APIs: `donacionesAPI`, `productosDonacionAPI`, `detallesDonacionAPI`, `salidasDonacionesAPI` |

### 2.3 Cambios Recientes

1. **Eliminado import muerto** de `lotesAPI` en `Donaciones.jsx`
2. **Auto-generación de clave** para `ProductoDonacion`: formato `DON-YYYYMMDD-XXXX`
3. **Verificación de separación** de inventarios completada

---

## 3. Estructura de Base de Datos

### 3.1 Tablas del Módulo de Donaciones

#### `productos_donacion` - Catálogo de Productos para Donaciones

```sql
CREATE TABLE productos_donacion (
    id              SERIAL PRIMARY KEY,
    clave           VARCHAR NOT NULL,           -- Ej: "DON-20241219-0001"
    nombre          VARCHAR NOT NULL,
    descripcion     TEXT,
    unidad_medida   VARCHAR DEFAULT 'PIEZA',
    presentacion    VARCHAR,
    activo          BOOLEAN DEFAULT true,
    notas           TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);
```

**Columnas:**
| Columna | Tipo | Nullable | Default | Descripción |
|---------|------|----------|---------|-------------|
| `id` | integer | NO | autoincrement | Llave primaria |
| `clave` | varchar | NO | - | Código único (auto-generado: DON-YYYYMMDD-XXXX) |
| `nombre` | varchar | NO | - | Nombre del producto |
| `descripcion` | text | YES | null | Descripción detallada |
| `unidad_medida` | varchar | YES | 'PIEZA' | Unidad de medida |
| `presentacion` | varchar | YES | null | Presentación del producto |
| `activo` | boolean | YES | true | Estado del producto |
| `notas` | text | YES | null | Notas adicionales |
| `created_at` | timestamptz | YES | now() | Fecha de creación |
| `updated_at` | timestamptz | YES | now() | Fecha de actualización |

**Foreign Keys:** Ninguna (tabla independiente)

---

#### `donaciones` - Registro de Donaciones Recibidas

```sql
CREATE TABLE donaciones (
    id                  SERIAL PRIMARY KEY,
    numero              VARCHAR NOT NULL UNIQUE,
    donante_nombre      VARCHAR NOT NULL,
    donante_tipo        VARCHAR,                -- 'gobierno', 'privado', 'ong', 'otro'
    donante_rfc         VARCHAR(20),
    donante_direccion   TEXT,
    donante_contacto    VARCHAR(100),
    fecha_donacion      DATE NOT NULL,
    fecha_recepcion     TIMESTAMPTZ DEFAULT now(),
    centro_destino_id   INTEGER REFERENCES centros(id),
    recibido_por_id     INTEGER REFERENCES usuarios(id),
    estado              VARCHAR DEFAULT 'pendiente',  -- 'pendiente', 'procesada', 'recibida', 'rechazada'
    notas               TEXT,
    documento_donacion  VARCHAR(255),
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);
```

**Columnas:**
| Columna | Tipo | Nullable | Default | Descripción |
|---------|------|----------|---------|-------------|
| `id` | integer | NO | autoincrement | Llave primaria |
| `numero` | varchar | NO | - | Número único de donación |
| `donante_nombre` | varchar | NO | - | Nombre del donante |
| `donante_tipo` | varchar | YES | null | Tipo: gobierno, privado, ong, otro |
| `donante_rfc` | varchar(20) | YES | null | RFC del donante |
| `donante_direccion` | text | YES | null | Dirección del donante |
| `donante_contacto` | varchar(100) | YES | null | Contacto del donante |
| `fecha_donacion` | date | NO | - | Fecha de la donación |
| `fecha_recepcion` | timestamptz | YES | now() | Fecha de recepción |
| `centro_destino_id` | integer | YES | null | Centro destino (FK) |
| `recibido_por_id` | integer | YES | null | Usuario que recibió (FK) |
| `estado` | varchar | YES | 'pendiente' | Estado de la donación |
| `notas` | text | YES | null | Notas adicionales |
| `documento_donacion` | varchar(255) | YES | null | Documento adjunto |
| `created_at` | timestamptz | YES | now() | Fecha de creación |
| `updated_at` | timestamptz | YES | now() | Fecha de actualización |

**Foreign Keys:**
| Columna | Tabla Referenciada | Columna Referenciada |
|---------|-------------------|---------------------|
| `centro_destino_id` | `centros` | `id` |
| `recibido_por_id` | `usuarios` | `id` |

---

#### `detalle_donaciones` - Detalle de Productos en Cada Donación

```sql
CREATE TABLE detalle_donaciones (
    id                      SERIAL PRIMARY KEY,
    donacion_id             INTEGER NOT NULL REFERENCES donaciones(id),
    producto_id             INTEGER REFERENCES productos(id),           -- LEGACY (opcional)
    producto_donacion_id    INTEGER REFERENCES productos_donacion(id),  -- NUEVO (recomendado)
    numero_lote             VARCHAR,                                     -- Texto libre, NO FK a lotes
    cantidad                INTEGER NOT NULL,
    cantidad_disponible     INTEGER NOT NULL DEFAULT 0,                  -- Stock en almacén donaciones
    fecha_caducidad         DATE,
    estado_producto         VARCHAR DEFAULT 'bueno',
    notas                   TEXT,
    created_at              TIMESTAMPTZ DEFAULT now()
);
```

**Columnas:**
| Columna | Tipo | Nullable | Default | Descripción |
|---------|------|----------|---------|-------------|
| `id` | integer | NO | autoincrement | Llave primaria |
| `donacion_id` | integer | NO | - | Donación padre (FK) |
| `producto_id` | integer | YES | null | **LEGACY** - Producto inventario principal |
| `producto_donacion_id` | integer | YES | null | **NUEVO** - Producto del catálogo donaciones |
| `numero_lote` | varchar | YES | null | Número de lote (TEXTO, no FK) |
| `cantidad` | integer | NO | - | Cantidad donada original |
| `cantidad_disponible` | integer | NO | 0 | Stock actual disponible |
| `fecha_caducidad` | date | YES | null | Fecha de caducidad |
| `estado_producto` | varchar | YES | 'bueno' | Estado del producto |
| `notas` | text | YES | null | Notas adicionales |
| `created_at` | timestamptz | YES | now() | Fecha de creación |

**Foreign Keys:**
| Columna | Tabla Referenciada | Columna Referenciada | Notas |
|---------|-------------------|---------------------|-------|
| `donacion_id` | `donaciones` | `id` | Requerido |
| `producto_donacion_id` | `productos_donacion` | `id` | **Usar este para nuevos registros** |
| `producto_id` | `productos` | `id` | Legacy - para migración |

> ⚠️ **IMPORTANTE:** El campo `numero_lote` es VARCHAR (texto libre), **NO es un FK** a la tabla `lotes`. Esto mantiene la separación del inventario principal.

---

#### `salidas_donaciones` - Entregas desde el Almacén de Donaciones

```sql
CREATE TABLE salidas_donaciones (
    id                      SERIAL PRIMARY KEY,
    detalle_donacion_id     INTEGER NOT NULL REFERENCES detalle_donaciones(id),
    cantidad                INTEGER NOT NULL,
    destinatario            VARCHAR NOT NULL,       -- Nombre del interno/paciente o área
    motivo                  TEXT,
    entregado_por_id        INTEGER REFERENCES usuarios(id),
    fecha_entrega           TIMESTAMPTZ DEFAULT now(),
    notas                   TEXT,
    created_at              TIMESTAMPTZ DEFAULT now()
);
```

**Columnas:**
| Columna | Tipo | Nullable | Default | Descripción |
|---------|------|----------|---------|-------------|
| `id` | integer | NO | autoincrement | Llave primaria |
| `detalle_donacion_id` | integer | NO | - | Detalle de donación (FK) |
| `cantidad` | integer | NO | - | Cantidad entregada |
| `destinatario` | varchar | NO | - | Nombre del destinatario |
| `motivo` | text | YES | null | Motivo de la entrega |
| `entregado_por_id` | integer | YES | null | Usuario que entregó (FK) |
| `fecha_entrega` | timestamptz | YES | now() | Fecha de entrega |
| `notas` | text | YES | null | Notas adicionales |
| `created_at` | timestamptz | YES | now() | Fecha de creación |

**Foreign Keys:**
| Columna | Tabla Referenciada | Columna Referenciada |
|---------|-------------------|---------------------|
| `detalle_donacion_id` | `detalle_donaciones` | `id` |
| `entregado_por_id` | `usuarios` | `id` |

---

### 3.2 Tablas del Inventario Principal (NO usadas por Donaciones)

Las siguientes tablas son del inventario principal y **NO interactúan** con el módulo de donaciones:

| Tabla | Descripción | Relación con Donaciones |
|-------|-------------|------------------------|
| `productos` | Catálogo principal de productos | ❌ Separado |
| `lotes` | Lotes del inventario principal | ❌ Separado |
| `movimientos` | Historial de movimientos | ❌ Separado |
| `requisiciones` | Requisiciones de centros | ❌ Separado |
| `detalles_requisicion` | Detalles de requisiciones | ❌ Separado |

---

## 4. Diagrama de Relaciones

```
┌─────────────────────────────────────────────────────────────────────┐
│                    MÓDULO DE DONACIONES (Separado)                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────┐                                               │
│  │ productos_donacion│  ◄── Catálogo independiente                  │
│  └────────┬─────────┘                                               │
│           │                                                         │
│           │ producto_donacion_id                                    │
│           ▼                                                         │
│  ┌──────────────────┐      ┌──────────────────┐                    │
│  │    donaciones    │──────│ detalle_donaciones│                    │
│  └────────┬─────────┘      └────────┬─────────┘                    │
│           │                         │                               │
│           │ centro_destino_id       │ detalle_donacion_id          │
│           ▼                         ▼                               │
│  ┌──────────────────┐      ┌──────────────────┐                    │
│  │     centros      │      │salidas_donaciones │                    │
│  └──────────────────┘      └──────────────────┘                    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│               INVENTARIO PRINCIPAL (Separado)                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────┐      ┌──────────────────┐                    │
│  │    productos     │──────│      lotes       │                    │
│  └──────────────────┘      └────────┬─────────┘                    │
│                                     │                               │
│                                     ▼                               │
│                            ┌──────────────────┐                    │
│                            │   movimientos    │                    │
│                            └──────────────────┘                    │
│                                     │                               │
│                                     ▼                               │
│                            ┌──────────────────┐                    │
│                            │  requisiciones   │                    │
│                            └──────────────────┘                    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 5. Flujo de Datos

### 5.1 Recepción de Donación

```
1. Usuario crea Donación
   └── donaciones.estado = 'pendiente'

2. Agrega Detalles (productos)
   └── detalle_donaciones.cantidad_disponible = 0

3. Procesa Donación
   └── donaciones.estado = 'procesada'
   └── detalle_donaciones.cantidad_disponible = cantidad

4. NO SE CREA:
   ❌ Registro en tabla 'movimientos'
   ❌ Registro en tabla 'lotes'
```

### 5.2 Salida de Donación

```
1. Usuario registra SalidaDonacion
   └── salidas_donaciones.cantidad = X

2. Se descuenta automáticamente
   └── detalle_donaciones.cantidad_disponible -= X

3. NO SE CREA:
   ❌ Registro en tabla 'movimientos'
```

---

## 6. APIs del Módulo

### 6.1 Endpoints

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/donaciones/` | GET, POST | Listar/Crear donaciones |
| `/api/donaciones/{id}/` | GET, PUT, DELETE | Detalle donación |
| `/api/donaciones/{id}/procesar/` | POST | Procesar donación |
| `/api/donaciones/{id}/recibir/` | POST | Marcar como recibida |
| `/api/donaciones/{id}/rechazar/` | POST | Rechazar donación |
| `/api/productos-donacion/` | GET, POST | Catálogo productos donación |
| `/api/detalle-donaciones/` | GET, POST | Detalles de donaciones |
| `/api/salidas-donaciones/` | GET, POST | Salidas de donaciones |

### 6.2 Permisos

El acceso al módulo requiere el permiso `perm_donaciones = true` en la tabla `usuarios`.

---

## 7. Validaciones del Sistema

### 7.1 En Backend (Django)

```python
# DetalleDonacionSerializer
- Valida que producto_donacion_id exista en productos_donacion
- Valida que donacion_id exista en donaciones

# SalidaDonacion.save()
- Valida cantidad <= cantidad_disponible
- Descuenta automáticamente de cantidad_disponible
```

### 7.2 En Frontend (React)

```javascript
// Donaciones.jsx
- Solo carga productos de productosDonacionAPI
- Solo carga centros de centrosAPI (para destino)
- NO usa lotesAPI ni productosAPI
```

---

## 8. Tablas Relacionadas del Sistema

### 8.1 `centros` - Centros Penitenciarios

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | integer | Llave primaria |
| `nombre` | varchar | Nombre del centro |
| `direccion` | text | Dirección |
| `telefono` | varchar | Teléfono |
| `email` | varchar | Email |
| `activo` | boolean | Estado |

**Uso en Donaciones:** Solo para `donaciones.centro_destino_id`

### 8.2 `usuarios` - Usuarios del Sistema

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | integer | Llave primaria |
| `username` | varchar | Nombre de usuario |
| `perm_donaciones` | boolean | Permiso para módulo donaciones |

**Uso en Donaciones:** 
- `donaciones.recibido_por_id`
- `salidas_donaciones.entregado_por_id`

---

## 9. Consideraciones de Migración

### 9.1 Campo Legacy `producto_id`

El campo `detalle_donaciones.producto_id` es **LEGACY** y apunta a la tabla `productos` del inventario principal. 

**Recomendación:** Para nuevos registros, usar siempre `producto_donacion_id` que apunta al catálogo independiente `productos_donacion`.

### 9.2 Migración de Datos Existentes

Si existen registros con `producto_id` pero sin `producto_donacion_id`:

```sql
-- 1. Crear productos en catálogo de donaciones
INSERT INTO productos_donacion (clave, nombre, unidad_medida, presentacion)
SELECT DISTINCT 
    'DON-MIG-' || p.id,
    p.nombre,
    p.unidad_medida,
    p.presentacion
FROM productos p
INNER JOIN detalle_donaciones dd ON dd.producto_id = p.id
WHERE dd.producto_donacion_id IS NULL;

-- 2. Actualizar referencias
UPDATE detalle_donaciones dd
SET producto_donacion_id = pd.id
FROM productos_donacion pd
WHERE pd.clave = 'DON-MIG-' || dd.producto_id
AND dd.producto_donacion_id IS NULL;
```

---

## 10. Conclusiones

✅ **Inventarios 100% Separados**
- Donaciones NO afecta `movimientos`
- Donaciones NO afecta `lotes`
- Donaciones tiene su propio catálogo `productos_donacion`

✅ **Trazabilidad Independiente**
- `cantidad_disponible` en `detalle_donaciones`
- `salidas_donaciones` para registro de entregas

✅ **Solo Lee Centros**
- `donaciones.centro_destino_id` → solo para saber a qué centro va
- No modifica ni crea datos en otras tablas

---

*Documento generado automáticamente - Sistema Farmacia Penitenciaria*
