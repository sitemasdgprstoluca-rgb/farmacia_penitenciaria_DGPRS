# INFORME DE ALINEACIÓN: MÓDULO MOVIMIENTOS Y REPORTES

**Fecha de Verificación:** 3 de enero de 2026  
**Proyecto:** Farmacia Penitenciaria (Django + React)  

---

## 1. ESQUEMA DE BASE DE DATOS (REFERENCIA)

Según el esquema proporcionado, la tabla `movimientos` contiene los siguientes campos:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | PK | Identificador único |
| `tipo` | varchar | entrada/salida/ajuste/transferencia/etc |
| `producto_id` | FK | Referencia a productos (NOT NULL) |
| `lote_id` | FK | Referencia a lotes (nullable) |
| `cantidad` | integer | Cantidad del movimiento |
| `centro_origen_id` | FK | Centro de origen (nullable) |
| `centro_destino_id` | FK | Centro de destino (nullable) |
| `requisicion_id` | FK | Requisición relacionada (nullable) |
| `usuario_id` | FK | Usuario que creó el movimiento |
| `motivo` | text | Observaciones/motivo del movimiento |
| `referencia` | varchar(100) | Referencia/código de transacción |
| `fecha` | datetime | Fecha del movimiento |
| `created_at` | datetime | Fecha de creación |
| `subtipo_salida` | varchar(30) | Subtipo para salidas (receta, consumo_interno, etc) |
| `numero_expediente` | varchar(50) | Expediente médico para salidas por receta |

---

## 2. ANÁLISIS DEL BACKEND

### 2.1 Modelo Django (`core/models.py` líneas 1095-1200)

```python
class Movimiento(models.Model):
    # Campos definidos:
    tipo = models.CharField(max_length=30)
    producto = models.ForeignKey(Producto, ...)  # db_column='producto_id'
    lote = models.ForeignKey(Lote, null=True, blank=True, ...)  # db_column='lote_id'
    cantidad = models.IntegerField()
    centro_origen = models.ForeignKey('Centro', null=True, blank=True, ...)  # db_column='centro_origen_id'
    centro_destino = models.ForeignKey('Centro', null=True, blank=True, ...)  # db_column='centro_destino_id'
    requisicion = models.ForeignKey('Requisicion', null=True, blank=True, ...)  # db_column='requisicion_id'
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, ...)  # db_column='usuario_id'
    motivo = models.TextField(blank=True, null=True)
    referencia = models.CharField(max_length=100, blank=True, null=True)
    subtipo_salida = models.CharField(max_length=30, blank=True, null=True, db_column='subtipo_salida')  # ✅
    numero_expediente = models.CharField(max_length=50, blank=True, null=True, db_column='numero_expediente')  # ✅
    fecha = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'movimientos'
        managed = False  # Tabla manejada externamente
```

#### ✅ Verificación Modelo vs BD:
| Campo BD | Campo Modelo Django | Estado |
|----------|---------------------|--------|
| id | id (PK automático) | ✅ OK |
| tipo | tipo | ✅ OK |
| producto_id | producto (FK) | ✅ OK |
| lote_id | lote (FK) | ✅ OK |
| cantidad | cantidad | ✅ OK |
| centro_origen_id | centro_origen (FK) | ✅ OK |
| centro_destino_id | centro_destino (FK) | ✅ OK |
| requisicion_id | requisicion (FK) | ✅ OK |
| usuario_id | usuario (FK) | ✅ OK |
| motivo | motivo | ✅ OK |
| referencia | referencia | ✅ OK |
| fecha | fecha | ✅ OK |
| created_at | created_at | ✅ OK |
| subtipo_salida | subtipo_salida | ✅ OK |
| numero_expediente | numero_expediente | ✅ OK |

---

### 2.2 Serializer (`core/serializers.py` líneas 1434-1570)

```python
class MovimientoSerializer(serializers.ModelSerializer):
    # Campos adicionales/calculados:
    lote_numero = serializers.CharField(source='lote.numero_lote', read_only=True)
    numero_lote = serializers.CharField(source='lote.numero_lote', read_only=True)  # Alias
    lote_codigo = serializers.CharField(source='lote.numero_lote', read_only=True)  # Alias
    producto_nombre = serializers.SerializerMethodField()
    producto_clave = serializers.CharField(source='lote.producto.clave', read_only=True)
    producto_descripcion = serializers.CharField(source='lote.producto.nombre', read_only=True)
    centro_origen_nombre = serializers.CharField(source='centro_origen.nombre', read_only=True)
    centro_destino_nombre = serializers.CharField(source='centro_destino.nombre', read_only=True)
    centro_nombre = serializers.SerializerMethodField()
    usuario_nombre = serializers.SerializerMethodField()
    observaciones = serializers.CharField(source='motivo', read_only=True)  # Alias
    requisicion_folio = serializers.CharField(source='requisicion.numero', read_only=True)
    fecha_movimiento = serializers.DateTimeField(source='fecha', read_only=True)
    subtipo_salida = serializers.CharField(required=False, allow_null=True)  # ✅
    numero_expediente = serializers.CharField(required=False, allow_null=True)  # ✅
    
    class Meta:
        model = Movimiento
        fields = [
            'id', 'tipo', 'producto', 'producto_nombre', 'producto_clave', 'producto_descripcion',
            'lote', 'lote_numero', 'numero_lote', 'lote_codigo',
            'centro_origen', 'centro_origen_nombre', 'centro_destino', 'centro_destino_nombre', 'centro_nombre',
            'cantidad', 'usuario', 'usuario_nombre', 'requisicion', 'requisicion_folio',
            'motivo', 'observaciones', 'referencia', 'subtipo_salida', 'numero_expediente',
            'fecha', 'fecha_movimiento', 'created_at'
        ]
```

#### ✅ Campos expuestos por el Serializer:

| Campo | Tipo | Para Frontend | Estado |
|-------|------|---------------|--------|
| id | integer | ✅ | ✅ OK |
| tipo | string | ✅ | ✅ OK |
| producto | FK id | ✅ | ✅ OK |
| producto_nombre | calculado | ✅ | ✅ OK |
| producto_clave | nested | ✅ | ✅ OK |
| producto_descripcion | nested | ✅ | ✅ OK |
| lote | FK id | ✅ | ✅ OK |
| lote_numero/numero_lote/lote_codigo | nested | ✅ (3 alias) | ✅ OK |
| centro_origen | FK id | ✅ | ✅ OK |
| centro_origen_nombre | nested | ✅ | ✅ OK |
| centro_destino | FK id | ✅ | ✅ OK |
| centro_destino_nombre | nested | ✅ | ✅ OK |
| centro_nombre | calculado | ✅ | ✅ OK |
| cantidad | integer | ✅ | ✅ OK |
| usuario | FK id | ✅ | ✅ OK |
| usuario_nombre | calculado | ✅ | ✅ OK |
| requisicion | FK id | ✅ | ✅ OK |
| requisicion_folio | nested | ✅ | ✅ OK |
| motivo | text | ✅ | ✅ OK |
| observaciones | alias de motivo | ✅ | ✅ OK |
| referencia | string | ✅ | ✅ OK |
| subtipo_salida | string | ✅ | ✅ OK |
| numero_expediente | string | ✅ | ✅ OK |
| fecha | datetime | ✅ | ✅ OK |
| fecha_movimiento | alias de fecha | ✅ | ✅ OK |
| created_at | datetime | ✅ | ✅ OK |

---

### 2.3 ViewSet de Movimientos (`inventario/views/movimientos.py`)

- **Clase:** `MovimientoViewSet`
- **Permisos:** `IsCentroCanManageInventory` (excluye médicos de escritura)
- **Operaciones:** List, Retrieve, Create (no Update/Delete)
- **Filtros disponibles:**
  - `tipo` - entrada/salida/ajuste
  - `centro` - ID del centro
  - `producto` - ID del producto
  - `lote` - ID o número de lote
  - `subtipo_salida` - receta, consumo_interno, merma, caducidad, transferencia
  - `fecha_inicio` / `fecha_fin` - rango de fechas
  - `search` - búsqueda en motivo, lote, producto, numero_expediente

#### ✅ Verificación de Filtros:
| Filtro | Implementado | Estado |
|--------|-------------|--------|
| tipo | ✅ | ✅ OK |
| centro | ✅ | ✅ OK |
| producto | ✅ | ✅ OK |
| lote | ✅ (ID y texto) | ✅ OK |
| subtipo_salida | ✅ | ✅ OK |
| fecha_inicio | ✅ | ✅ OK |
| fecha_fin | ✅ | ✅ OK |
| search | ✅ (incluye numero_expediente) | ✅ OK |

---

### 2.4 Endpoint de Reportes de Movimientos (`views_legacy.py` línea 8274)

**Ruta:** `/api/reportes/movimientos/`  
**Función:** `reporte_movimientos`  
**Formatos:** `json`, `excel`, `pdf`

#### Datos que retorna el reporte (formato JSON):
```python
# Por cada transacción agrupada:
{
    'referencia': str,           # Código de la transacción
    'fecha': str,                # Fecha formateada
    'tipo': 'ENTRADA'|'SALIDA',  # Clasificación general
    'tipo_original': str,        # Tipo específico (entrada, salida, ajuste, etc)
    'centro_origen': str,        # Nombre del centro origen
    'centro_destino': str,       # Nombre del centro destino
    'total_productos': int,      # Cantidad de productos distintos
    'total_cantidad': int,       # Suma de cantidades
    'observaciones': str,        # Motivo/observaciones
    'detalles': [                # Lista de items de la transacción
        {
            'producto': str,     # Clave - Nombre
            'lote': str,         # Número de lote
            'cantidad': int
        }
    ]
}
```

#### ⚠️ CAMPOS NO INCLUIDOS EN REPORTE:
| Campo BD | En Reporte | Observación |
|----------|-----------|-------------|
| subtipo_salida | ❌ NO | Solo muestra tipo general (ENTRADA/SALIDA) |
| numero_expediente | ❌ NO | No se incluye en los datos |

---

## 3. ANÁLISIS DEL FRONTEND

### 3.1 Página de Movimientos (`Movimientos.jsx`)

**Campos mostrados en tabla principal:**
- Producto (nombre + lote)
- Tipo (con badge de color)
- Subtipo salida (emoji visual) ✅
- Cantidad
- Centro
- Fecha

**Campos en vista expandida/detalle:**
- ID Movimiento
- Producto (clave + nombre)
- Lote
- Centro
- Usuario
- Requisición folio
- Subtipo Salida (con etiqueta descriptiva) ✅
- Número Expediente (solo si subtipo='receta') ✅
- Fecha exacta
- Observaciones

#### ✅ Verificación Frontend Movimientos:
| Campo | Mostrado | Estado |
|-------|----------|--------|
| id | ✅ (en detalle) | ✅ OK |
| tipo | ✅ | ✅ OK |
| producto_nombre | ✅ | ✅ OK |
| producto_clave | ✅ (en detalle) | ✅ OK |
| lote_codigo/numero_lote | ✅ | ✅ OK |
| centro_nombre | ✅ | ✅ OK |
| cantidad | ✅ | ✅ OK |
| usuario_nombre | ✅ (en detalle) | ✅ OK |
| requisicion_folio | ✅ (en detalle) | ✅ OK |
| subtipo_salida | ✅ | ✅ OK |
| numero_expediente | ✅ (condicional) | ✅ OK |
| fecha/fecha_movimiento | ✅ | ✅ OK |
| observaciones | ✅ (en detalle) | ✅ OK |

---

### 3.2 Página de Reportes (`Reportes.jsx`)

**Columnas configuradas para movimientos:**
```javascript
movimientos: [
    { key: 'expand', label: '', width: '50px' },
    { key: 'fecha', label: 'Fecha', width: '140px' },
    { key: 'tipo', label: 'Tipo', width: '120px' },
    { key: 'referencia', label: 'Referencia', width: '200px' },
    { key: 'centro_origen', label: 'Origen', width: '180px' },
    { key: 'centro_destino', label: 'Destino', width: '180px' },
    { key: 'total_productos', label: 'Productos', width: '100px' },
    { key: 'total_cantidad', label: 'Cantidad', width: '100px' },
]
```

#### ⚠️ CAMPOS NO MOSTRADOS EN REPORTES:
| Campo | En Reporte | Razón |
|-------|-----------|-------|
| subtipo_salida | ❌ NO | El backend no lo incluye en la respuesta agrupada |
| numero_expediente | ❌ NO | El backend no lo incluye en la respuesta agrupada |
| observaciones | ❌ NO | Se agrupa, solo se ve en detalles expandidos |

---

### 3.3 Servicio API (`api.js`)

```javascript
// Movimientos directos
export const movimientosAPI = {
  getAll: (params) => apiClient.get('/movimientos/', { params }),
  create: (data) => apiClient.post('/movimientos/', data),
  exportarExcel: ...,
  exportarPdf: ...,
  getReciboSalida: ...,
  confirmarEntrega: ...,
};

// Reportes de movimientos
export const reportesAPI = {
  movimientos: (params) => apiClient.get('/reportes/movimientos/', { params: { ...params, formato: 'json' } }),
  exportarMovimientosExcel: (params) => apiClient.get('/reportes/movimientos/', { params: { ...params, formato: 'excel' }, responseType: 'blob' }),
  exportarMovimientosPDF: (params) => apiClient.get('/reportes/movimientos/', { params: { ...params, formato: 'pdf' }, responseType: 'blob' }),
};
```

---

## 4. RESUMEN DE DISCREPANCIAS

### 4.1 ✅ Alineación Correcta

| Componente | Estado | Detalles |
|------------|--------|----------|
| Modelo Django vs BD | ✅ ALINEADO | Todos los campos coinciden |
| Serializer vs Modelo | ✅ ALINEADO | Expone todos los campos + campos calculados |
| ViewSet Movimientos | ✅ ALINEADO | Filtros y permisos correctos |
| Frontend Movimientos.jsx | ✅ ALINEADO | Muestra todos los campos relevantes |
| API Service Frontend | ✅ ALINEADO | Endpoints correctos |

### 4.2 ⚠️ Discrepancias Encontradas

| Issue | Descripción | Impacto | Severidad |
|-------|-------------|---------|-----------|
| ISS-REP-001 | Reporte de movimientos NO incluye `subtipo_salida` | El reporte no muestra si una salida fue por receta, merma, etc. | MEDIA |
| ISS-REP-002 | Reporte de movimientos NO incluye `numero_expediente` | No hay trazabilidad de pacientes en reportes | MEDIA |
| ISS-REP-003 | Reportes.jsx no tiene columna para subtipo | Aunque el backend lo incluyera, no se mostraría | BAJA |

---

## 5. RECOMENDACIONES DE CORRECCIÓN

### 5.1 Backend - Agregar campos al reporte de movimientos

**Archivo:** `backend/inventario/views_legacy.py`  
**Función:** `reporte_movimientos` (línea ~8340)

**Cambio sugerido:** Incluir `subtipo_salida` y `numero_expediente` en los datos de cada transacción:

```python
# Dentro del bucle que construye transacciones:
if ref not in transacciones:
    transacciones[ref] = {
        'referencia': ref,
        'fecha': mov.fecha.strftime('%d/%m/%Y %H:%M'),
        'tipo': 'ENTRADA' if es_entrada else 'SALIDA',
        'tipo_original': tipo_mov.upper(),
        'subtipo_salida': mov.subtipo_salida or '',  # ← AGREGAR
        'numero_expediente': mov.numero_expediente or '',  # ← AGREGAR
        # ... resto de campos
    }
```

### 5.2 Frontend - Agregar columna opcional en Reportes.jsx

**Archivo:** `inventario-front/src/pages/Reportes.jsx`  
**Sección:** `COLUMNAS_CONFIG.movimientos`

**Cambio sugerido:** Agregar columna de subtipo para mejor visibilidad:

```javascript
movimientos: [
    { key: 'expand', label: '', width: '50px' },
    { key: 'fecha', label: 'Fecha', width: '140px' },
    { key: 'tipo', label: 'Tipo', width: '100px' },
    { key: 'subtipo_salida', label: 'Subtipo', width: '120px' },  // ← AGREGAR
    { key: 'referencia', label: 'Referencia', width: '180px' },
    { key: 'centro_origen', label: 'Origen', width: '160px' },
    { key: 'centro_destino', label: 'Destino', width: '160px' },
    { key: 'total_productos', label: 'Productos', width: '90px' },
    { key: 'total_cantidad', label: 'Cantidad', width: '90px' },
]
```

### 5.3 Exportación Excel - Incluir campos adicionales

**Archivo:** `backend/inventario/views_legacy.py`  
**Sección:** Generación de Excel (~línea 8460)

**Cambio sugerido:** Agregar columnas para subtipo y expediente en la hoja Excel.

---

## 6. CONCLUSIÓN

| Aspecto | Calificación | Notas |
|---------|--------------|-------|
| **Modelo vs BD** | 100% ✅ | Perfecto |
| **Serializer** | 100% ✅ | Completo con alias para frontend |
| **API Movimientos** | 100% ✅ | Filtros y seguridad correctos |
| **Frontend Movimientos** | 100% ✅ | Muestra todos los campos |
| **Reporte Movimientos** | 85% ⚠️ | Falta subtipo_salida y numero_expediente |
| **Exportaciones** | 85% ⚠️ | Misma limitación que el reporte |

### Alineación General: **95%** ✅

El sistema está bien alineado en general. Las únicas discrepancias son en el módulo de **Reportes de Movimientos**, donde no se incluyen los campos `subtipo_salida` y `numero_expediente` que sí existen en la BD y se muestran correctamente en la página de Movimientos individual.

---

*Informe generado automáticamente - Verificación de alineación fullstack*
