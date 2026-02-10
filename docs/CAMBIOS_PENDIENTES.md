# Cambios entre 18 Dic (e53be15) y 22 Dic (598f952)

Este documento lista las **21 funcionalidades** desarrolladas entre el 18 y 22 de diciembre de 2025.

**Estado Actual**: La versión actual (598f952) YA INCLUYE todos estos cambios.

**EXCLUIDO**: Todo lo relacionado con healthcheck, "servidor iniciando", y ConnectionIndicator (eliminados por causar problemas).

---

## 📋 Lista de Commits (21 total)

```
598f952 feat: mejoras integrales - donaciones simplificadas, salidas a centros, PDFs con firmas, trazabilidad NOM-059
1086bae fix: Corregir error limpiar datos + mejorar importador productos + presentacion en lotes
d331f20 fix: Corregir lotes en Movimientos y hacer presentación obligatoria
3d3016b fix: Simplificar formulario movimientos - solo Salida y Transferencia a centro
28e7211 Simplificar plantilla de donaciones a una sola hoja y añadir columna Estado
9379167 fix: Corregir trazabilidad - busqueda, PDF y display
54fdce4 fix: Mejorar plantilla e importacion Excel productos donacion
82e87f0 fix: Corregir plantilla e importación de productos donación
588c215 feat: Agregar finalización de entregas donaciones, PDF con firmas para movimientos
fd26f69 fix(trazabilidad): corregir errores y mejorar PDF
d13ddde fix(trazabilidad): corregir error mostrarSaldo y mejorar filtros exportacion
9434334 fix(trazabilidad): sincronizar front-back-BD, agregar filtros fecha
4655db4 feat(trazabilidad): exportar PDF de lotes + exportacion global
afb2551 fix(trazabilidad): restaurar busqueda por lote + corregir mapeo campos
e340ea2 fix(trazabilidad): corregir mapeo de campos producto
916e5b6 refactor(trazabilidad): eliminar selector producto/lote
37bb6d9 fix(ui): bordes visibles en campo de busqueda y boton Limpiar
cf3516f feat(frontend): mejoras UX en busqueda, donaciones y trazabilidad
f7136d6 feat(search): Mejorar componente AutocompleteInput
b3a707a fix(trazabilidad): Permitir busqueda por nombre de producto
031c2a7 fix(trazabilidad/reportes): Corregir campos PDF y verificar separacion donaciones
```

---

## 🏷️ 1. Lotes.jsx - Campo Presentación (+69 líneas)

**Archivo**: `inventario-front/src/pages/Lotes.jsx`

### Funcionalidades agregadas:
- ✅ Campo `presentacion_producto` en formulario de lotes
- ✅ Validación: presentación es **OBLIGATORIA** al crear lote
- ✅ Auto-actualización del producto cuando se guarda lote con nueva presentación
- ✅ Selector de producto auto-rellena el campo presentación
- ✅ Columna "Presentación" en tabla de lotes

### Código clave:
```jsx
// Validación
if (!nuevoLote.presentacion_producto?.trim()) {
  toast.error('La presentación es obligatoria');
  return;
}

// Auto-update del producto
if (presentacion_changed) {
  await productosAPI.update(producto_id, { presentacion: nuevoLote.presentacion_producto });
}
```

---

## 📦 2. Movimientos.jsx - Simplificación a Salidas (+92 líneas)

**Archivo**: `inventario-front/src/pages/Movimientos.jsx`

### Funcionalidades agregadas:
- ✅ Tipo de movimiento **FIJO** a "salida"
- ✅ Subtipo **FIJO** a "transferencia"
- ✅ Nueva función `descargarReciboSalida()` - genera PDF con campos de firma
- ✅ Filtro: Farmacia/Admin ven lotes de farmacia "central"
- ✅ Campos de firma en PDF: Autoriza, Entrega, Recibe

### Código clave:
```jsx
const descargarReciboSalida = async (movimiento) => {
  const response = await movimientosAPI.getReciboSalida(movimiento.id);
  // Genera PDF con campos de firma para control interno
};
```

### Beneficio:
Simplifica el flujo - ahora es exclusivamente para salidas/transferencias a centros penitenciarios.

---

## 🔍 3. Trazabilidad.jsx - Mejoras Mayores (+644 líneas)

**Archivo**: `inventario-front/src/pages/Trazabilidad.jsx`

### Funcionalidades agregadas:
- ✅ Helper `getCentroNombre()` - maneja centros como string u objeto
- ✅ Función mejorada `mapMovimiento()` con campos normalizados
- ✅ Función mejorada `mapLote()` con todos los campos
- ✅ `normalizeProductoResponse()` con mapeo correcto de:
  - presentacion
  - descripcion  
  - precio_unitario
  - unidad_medida
  - marca
- ✅ Mejor manejo de centros (nombre vs ID)
- ✅ Filtros de fecha y caducidad funcionales
- ✅ Exportación PDF de lotes individuales
- ✅ Exportación global de trazabilidad
- ✅ Variable `mostrarSaldo` (solo visible en trazabilidad de lote)
- ✅ Búsqueda por nombre de producto (no solo clave)
- ✅ Botón "Limpiar" con mejor UX

### Código clave:
```jsx
const getCentroNombre = (centro) => {
  if (!centro) return 'Sin centro';
  if (typeof centro === 'string') return centro;
  return centro.nombre || centro.name || `Centro ${centro.id}`;
};

const normalizeProductoResponse = (data) => {
  return {
    clave: data.clave || '',
    descripcion: data.descripcion || data.nombre || '',
    presentacion: data.presentacion || '',
    precio_unitario: data.precio_unitario || data.precio || 0,
    unidad_medida: data.unidad_medida || 'PIEZA',
    // ... más campos
  };
};
```

### Beneficio:
Trazabilidad completa según NOM-059 con exportación a PDF.

---

## 🎁 4. Donaciones.jsx - Funcionalidades Nuevas (+918 líneas)

**Archivo**: `inventario-front/src/pages/Donaciones.jsx`

### Funcionalidades agregadas:
- ✅ Campo `centro_destino` obligatorio (antes era `destinatario` texto libre)
- ✅ Número de donación auto-generado (`siguienteNumero`)
- ✅ Modal rápido para crear producto desde formulario (`showQuickProductModal`)
- ✅ Carga masiva de productos (`showBulkAddModal`, `bulkText`, `bulkProducts`)
- ✅ Importación/Exportación de catálogo de productos donación
- ✅ Columna "Estado" en listado de salidas
- ✅ Plantilla Excel simplificada (UNA sola hoja)
- ✅ Finalización de entregas de donaciones
- ✅ Iconos nuevos: FaCheckCircle, FaClock, FaTable, FaClipboardCheck, FaFilePdf

### Código clave:
```jsx
// Estados nuevos
const [showQuickProductModal, setShowQuickProductModal] = useState(false);
const [showBulkAddModal, setShowBulkAddModal] = useState(false);
const [siguienteNumero, setSiguienteNumero] = useState('');

// Salida form cambiado
const [salidaForm, setSalidaForm] = useState({
  cantidad: '',
  centro_destino: '',  // ID del centro destino (obligatorio)
  motivo: '',
  notas: '',
});
```

### Beneficio:
Flujo de donaciones completamente simplificado con trazabilidad obligatoria a centros.

---

## 📄 5. pdf_reports.py - PDFs con Firmas (+580 líneas)

**Archivo**: `backend/core/utils/pdf_reports.py`

### Funciones nuevas/mejoradas:

#### 5.1 `generar_recibo_salida_donacion()` - NUEVA
```python
def generar_recibo_salida_donacion(salida_data, detalles_data=None, finalizado=False):
    """
    Genera un recibo PDF para una salida de donación.
    
    Si finalizado=False: Muestra campos de firma (Autoriza, Entrega, Recibe)
    Si finalizado=True: Muestra sello de ENTREGADO
    """
```

#### 5.2 Reporte de inventario mejorado
- Columnas actualizadas: Clave, Descripción, **Presentación**, Inventario, Nivel, Unidad, **Precio**, **Marca**
- Elimina `stock_minimo` (no usado en sistema)
- Agrega `marca` desde lote principal del producto

#### 5.3 Reporte de trazabilidad mejorado
- Presentación como campo único para forma farmacéutica
- Precio formateado con símbolo $
- Proveedor/Marca si existe en datos

---

## 🔧 6. views.py - Backend (+1248 líneas)

**Archivo**: `backend/core/views.py`

### ReportesViewSet:
```python
# Campo presentacion en datos de inventario
datos.append({
    'presentacion': producto.presentacion or '',
    'marca': lote_principal.marca if lote_principal else '',
    # ...
})

# Elimina productos_bajo_minimo (se usa nivel de stock)
resumen = {
    'productos_stock_critico': sum(1 for d in datos if d['nivel_stock'] == 'critico'),
    # ...
}
```

### DonacionViewSet:
- Plantilla Excel simplificada a UNA sola hoja
- Importación vinculada a catálogo de productos donación
- Validación por clave de producto con lista de claves válidas

---

## 🔄 7. AutocompleteInput.jsx - Mejoras UX

**Archivo**: `inventario-front/src/components/AutocompleteInput.jsx`

### Cambios:
- ✅ Bordes visibles en campo de búsqueda
- ✅ Botón "Limpiar" mejorado
- ✅ Mejor manejo de resultados vacíos
- ✅ Estilos consistentes con el tema

---

## 📊 8. serializers.py - Campos Adicionales

**Archivo**: `backend/core/serializers.py`

### Cambios en ProductoSerializer:
```python
# Campos adicionales
presentacion = serializers.CharField(required=False)
marca = serializers.SerializerMethodField()

def get_marca(self, obj):
    """Obtiene marca del lote principal"""
    lote = obj.lotes.filter(activo=True, cantidad_actual__gt=0).first()
    return lote.marca if lote else None
```

### Cambios en LoteSerializer:
```python
producto_info = serializers.SerializerMethodField()

def get_producto_info(self, obj):
    if obj.producto:
        return {
            'presentacion': obj.producto.presentacion or '',
            'unidad_medida': obj.producto.unidad_medida or 'PIEZA',
        }
    return None
```

---

## ❌ Funcionalidades ELIMINADAS (NO re-implementar)

Estas funcionalidades causaban errores graves y fueron removidas intencionalmente:

| Componente | Razón de eliminación |
|------------|---------------------|
| `ConnectionIndicator.jsx` | Errores 401 en cascada |
| Pantalla "Servidor Iniciando..." | Bloqueaba uso del sistema |
| `RETRY_CONFIG` en api.js | Causaba loops infinitos de reintentos |
| Healthcheck/Warmup en Login | No compatible con Render cold starts |

---

## ✅ Resumen de Estado

| Módulo | Líneas | Estado |
|--------|--------|--------|
| Lotes con presentación | +69 | ✅ Incluido |
| Movimientos simplificados | +92 | ✅ Incluido |
| Trazabilidad NOM-059 | +644 | ✅ Incluido |
| Donaciones mejoradas | +918 | ✅ Incluido |
| PDFs con firmas | +580 | ✅ Incluido |
| Backend views | +1248 | ✅ Incluido |
| AutocompleteInput | +mejoras | ✅ Incluido |
| Connection Indicator | - | ❌ Eliminado |
| Servidor Iniciando | - | ❌ Eliminado |

---

## 📝 Conclusión

La versión actual (commit 598f952 + simplificación de Login) contiene:
- ✅ **Todas las mejoras funcionales** de los 21 commits
- ✅ **Sin la funcionalidad problemática** de conexión/healthcheck
- ✅ **Sistema estable** y listo para producción

**Total de cambios**: +6,520 líneas / -1,025 líneas en 28 archivos

---

*Documento generado el 24 de diciembre de 2025*
