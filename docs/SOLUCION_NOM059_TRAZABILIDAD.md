# Solución Integral NOM-059-SSA1-2015 - Sistema de Farmacia Penitenciaria

## 📋 Resumen Ejecutivo

Este documento describe la solución integral implementada para cumplir con la **NOM-059-SSA1-2015** (Buenas prácticas de fabricación de medicamentos) en el Sistema de Farmacia Penitenciaria, enfocándose en la trazabilidad completa de medicamentos.

---

## 🎯 Objetivos Cumplidos

| # | Requisito | Estado | Implementación |
|---|-----------|--------|----------------|
| 1 | Identificación del producto por clave, nombre o descripción | ✅ | Búsqueda inteligente multi-campo |
| 2 | Campos Unidad y Presentación correctos | ✅ | Normalización y fallbacks |
| 3 | Subtipos de salida (receta, transferencia, etc.) | ✅ | `SUBTIPOS_SALIDA` en constants.py |
| 4 | Subtipos de ajuste (error, merma, robo, etc.) | ✅ | `SUBTIPOS_AJUSTE` en constants.py |
| 5 | Motivo obligatorio para ciertos movimientos | ✅ | Validación en modelo |
| 6 | Número de expediente para recetas | ✅ | Campo `numero_expediente` |
| 7 | Referencia documental (oficio, contrato) | ✅ | Campo `documento_referencia` |
| 8 | Historial auditable de correcciones | ✅ | Campos `es_correccion`, `movimiento_corregido_id` |
| 9 | PDF con información completa | ✅ | Reporte mejorado con subtipos |

---

## 🔹 1. Identificación del Producto

### Búsqueda Inteligente
El sistema permite localizar productos mediante:
- **Clave exacta**: Búsqueda por código único
- **Nombre exacto**: Búsqueda por nombre del producto
- **Búsqueda parcial**: En clave, nombre o descripción

```python
# Orden de búsqueda implementado en views_legacy.py
1. Producto.objects.filter(clave__iexact=termino)
2. Producto.objects.filter(nombre__iexact=termino)
3. Producto.objects.filter(Q(clave__icontains=termino) | Q(nombre__icontains=termino) | Q(descripcion__icontains=termino))
```

### Campos del Producto
| Campo | Descripción | Requerido |
|-------|-------------|-----------|
| `clave` | Identificador único | ✅ Sí |
| `nombre` | Nombre del medicamento | ✅ Sí |
| `descripcion` | Descripción extendida | No |
| `presentacion` | Forma farmacéutica (tabletas, frasco, etc.) | Recomendado |
| `unidad_medida` | Unidad de medición (PIEZA, CAJA, etc.) | ✅ Sí (default: PIEZA) |
| `concentracion` | Concentración del principio activo | No |
| `sustancia_activa` | Principio activo | No |

---

## 🔹 2. Donaciones

### Modelo Actual
Las donaciones están implementadas como **almacén separado** con su propio catálogo:
- `ProductoDonacion`: Catálogo independiente para productos de donación
- `Donacion`: Registro principal de la donación
- `DetalleDonacion`: Productos incluidos en cada donación

### Flujo de Donaciones
1. Se registra la donación con datos del donante
2. Se asigna clave interna automática (`DON-{numero}`)
3. Los productos se registran en el catálogo de donaciones
4. No afecta el inventario principal hasta que se transfiere

### Mejoras Pendientes (Roadmap)
- [ ] Integrar donaciones al inventario principal con movimiento tipo `donacion_recibida`
- [ ] Trazabilidad de distribución a múltiples centros
- [ ] Reportes específicos de donaciones

---

## 🔹 3. Movimientos de Inventario

### Tipos de Movimiento (TIPOS_MOVIMIENTO)
```python
TIPOS_MOVIMIENTO = [
    ('entrada', 'Entrada'),
    ('salida', 'Salida'),
    ('transferencia', 'Transferencia'),
    ('ajuste_positivo', 'Ajuste Positivo'),
    ('ajuste_negativo', 'Ajuste Negativo'),
    ('devolucion', 'Devolucion'),
    ('merma', 'Merma'),
    ('caducidad', 'Caducidad'),
]
```

### Subtipos de SALIDA (NOM-059)
```python
SUBTIPOS_SALIDA = [
    ('receta', 'Receta Médica'),                    # Requiere expediente
    ('consumo_interno', 'Consumo Interno'),         # Uso en centro
    ('transferencia', 'Transferencia a Centro'),    # Requiere referencia
    ('requisicion', 'Por Requisición'),             # Automático
    ('donacion_salida', 'Donación Otorgada'),       # Requiere documento
    ('oficio', 'Oficio Administrativo'),            # Requiere documento
    ('merma', 'Merma'),                             # Requiere motivo
    ('caducidad', 'Caducidad'),                     # Requiere motivo
    ('devolucion_proveedor', 'Devolución a Proveedor'),
    ('destruccion', 'Destrucción'),                 # Requiere documento
    ('otro', 'Otro'),                               # Requiere motivo
]
```

### Subtipos de ENTRADA
```python
SUBTIPOS_ENTRADA = [
    ('compra', 'Compra/Adquisición'),               # Requiere contrato
    ('donacion_recibida', 'Donación Recibida'),
    ('transferencia_in', 'Transferencia Recibida'),
    ('devolucion_centro', 'Devolución de Centro'),
    ('ajuste_inventario', 'Ajuste de Inventario'),
    ('inicial', 'Inventario Inicial'),
    ('otro', 'Otro'),
]
```

---

## 🔹 4. Ajustes de Inventario

### Subtipos de AJUSTE (NOM-059)
```python
SUBTIPOS_AJUSTE = [
    ('error_captura', 'Error de Captura'),          # Corrección administrativa
    ('error_conteo', 'Error de Conteo'),            # Después de inventario físico
    ('merma', 'Merma/Deterioro'),                   # Pérdida por daño
    ('caducidad', 'Por Caducidad'),                 # Ajuste por vencimiento
    ('robo', 'Robo/Extravío'),                      # Falta por robo
    ('sobrante', 'Sobrante'),                       # Excedente encontrado
    ('faltante', 'Faltante'),                       # Faltante detectado
    ('reclasificacion', 'Reclasificación'),         # Cambio ubicación
    ('auditoria', 'Ajuste por Auditoría'),          # Resultado auditoría
    ('otro', 'Otro'),                               # Requiere motivo
]
```

### Reglas de Validación
| Subtipo | Motivo Obligatorio | Referencia Documental |
|---------|-------------------|----------------------|
| `error_captura` | ✅ Sí | No |
| `error_conteo` | ✅ Sí | No |
| `merma` | ✅ Sí | No |
| `robo` | ✅ Sí | Recomendado |
| `sobrante` | ✅ Sí | No |
| `faltante` | ✅ Sí | No |
| `auditoria` | ✅ Sí | ✅ Sí |
| `otro` | ✅ Sí | Recomendado |

---

## 🔹 5. Marca de Error y Auditoría de Correcciones

### Campos de Auditoría en Modelo Movimiento
```python
# Campos para identificar correcciones
es_correccion = models.BooleanField(default=False)
movimiento_corregido = models.ForeignKey('self', null=True, blank=True)

# Campos para trazabilidad técnica
ip_usuario = models.CharField(max_length=45, null=True)
```

### Flujo de Corrección
1. Usuario identifica error en movimiento anterior
2. Crea nuevo movimiento con `es_correccion=True`
3. Vincula al movimiento original con `movimiento_corregido_id`
4. Especifica motivo obligatorio de la corrección
5. El sistema registra automáticamente usuario y timestamp

### Tabla de Historial (Opcional)
```sql
-- Tabla para historial detallado de cambios
CREATE TABLE movimientos_historial (
    id SERIAL PRIMARY KEY,
    movimiento_id INTEGER NOT NULL,
    campo_modificado VARCHAR(50) NOT NULL,
    valor_anterior TEXT NULL,
    valor_nuevo TEXT NULL,
    motivo_cambio TEXT NOT NULL,
    usuario_id INTEGER NULL,
    fecha_cambio TIMESTAMP DEFAULT NOW(),
    ip_usuario VARCHAR(45) NULL
);
```

---

## 🔹 6. Reporte de Trazabilidad (PDF)

### Información del Producto
| Campo | Descripción |
|-------|-------------|
| Clave | Identificador único |
| Descripción | Nombre del producto |
| Unidad | Unidad de medida normalizada |
| Presentación | Forma farmacéutica (o "N/A") |
| Stock Actual | Cantidad disponible |
| Precio | Precio unitario del lote principal |
| No. Contrato | Número de contrato (si aplica) |
| No. Lote | Lote principal |

### Historial de Movimientos
| Columna | Contenido |
|---------|-----------|
| Fecha | Fecha y hora del movimiento |
| Tipo/Subtipo | Tipo principal y subtipo clasificador |
| Lote | Número de lote afectado |
| Cantidad | Cantidad con signo (+/-) |
| Centro | Centro destino o origen |
| Usuario | Usuario responsable |
| Referencia/Motivo | Documento, expediente o motivo |

### Resumen de Trazabilidad
- Total de Entradas
- Total de Salidas
- Total de Transferencias
- Total de Ajustes (+/-)
- Total de Mermas
- Total por Caducidad
- **TOTAL MOVIMIENTOS**

---

## 📁 Archivos Modificados

### Backend
| Archivo | Cambios |
|---------|---------|
| `core/constants.py` | Agregados SUBTIPOS_SALIDA, SUBTIPOS_ENTRADA, SUBTIPOS_AJUSTE |
| `core/models.py` | Campos NOM-059 en Movimiento (subtipo_entrada, subtipo_ajuste, documento_referencia, es_correccion, movimiento_corregido_id) |
| `core/utils/pdf_reports.py` | Reporte de trazabilidad mejorado con subtipos |
| `inventario/views_legacy.py` | Endpoints de trazabilidad con campos completos |

### SQL
| Archivo | Propósito |
|---------|-----------|
| `docs/SQL_NOM059_AUDIT_FIELDS.sql` | Script para agregar campos de auditoría en Supabase |

---

## 🚀 Implementación en Producción

### Paso 1: Ejecutar migración SQL
```sql
-- En Supabase SQL Editor, ejecutar:
-- docs/SQL_NOM059_AUDIT_FIELDS.sql
```

### Paso 2: Verificar campos
```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'movimientos';
```

### Paso 3: Desplegar código actualizado
```bash
git add .
git commit -m "feat(NOM-059): Implementar trazabilidad completa según normativa sanitaria"
git push
```

---

## 📊 Validaciones NOM-059 Implementadas

### En Modelo (clean())
```python
# Validación de subtipos
if self.subtipo_salida not in SUBTIPOS_SALIDA_VALIDOS:
    raise ValidationError('Subtipo de salida inválido')

# Validación de expediente para recetas
if self.subtipo_salida == 'receta' and not self.numero_expediente:
    raise ValidationError('Número de expediente requerido')

# Validación de motivo obligatorio
if subtipo in SUBTIPOS_REQUIEREN_MOTIVO and not self.motivo:
    raise ValidationError('Motivo obligatorio para este tipo de movimiento')

# Validación de correcciones
if self.es_correccion and not self.movimiento_corregido_id:
    raise ValidationError('Debe indicar el movimiento que se corrige')
```

---

## ✅ Checklist de Cumplimiento NOM-059

- [x] Identificación única de productos (clave)
- [x] Búsqueda por nombre o descripción
- [x] Unidad de medida normalizada
- [x] Presentación del medicamento
- [x] Clasificación de salidas por subtipo
- [x] Clasificación de ajustes por subtipo
- [x] Motivo obligatorio para ajustes
- [x] Número de expediente para recetas
- [x] Referencia documental para oficios
- [x] Historial de correcciones
- [x] Usuario responsable de cada movimiento
- [x] Timestamp de cada operación
- [x] Reporte PDF con información completa
- [x] Nota de cumplimiento normativo en reportes

---

## 📞 Soporte

Para dudas sobre la implementación, consultar:
- **Documentación técnica**: `ARQUITECTURA.md`
- **Constantes del sistema**: `core/constants.py`
- **Modelo de movimientos**: `core/models.py`

---

*Documento generado: Diciembre 2024*
*Sistema de Farmacia Penitenciaria - Gobierno del Estado de México*
