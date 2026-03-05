# Mejoras Pendientes - Sistema Caja Chica

**Fecha:** 5 de marzo de 2026  
**Status:** PENDIENTE

## 🔴 Problemas Identificados

### 1. Modal de Recepción - Faltan Campos Críticos

**Archivo:** `inventario-front/src/pages/ComprasCajaChica.jsx` (líneas 2392-2530)

**Problema:** 
El modal de "Registrar Recepción" NO permite capturar:
- ❌ **Número de lote** (solo muestra el existente en read-only)
- ❌ **Fecha de caducidad** (campo inexistente)

**Impacto:**  
Los productos ingresan al inventario sin rastreabilidad completa. La tabla `inventario_caja_chica` sí tiene los campos:
- `numero_lote` (character varying)
- `fecha_caducidad` (date)

Pero el frontend no los captura al momento de la recepción.

**Solución Requerida:**
Agregar dos columnas más a la tabla del modal de recepción:
```jsx
<th>Lote *</th>
<th>Caducidad *</th>
```

Con inputs editables:
```jsx
<input 
  type="text" 
  value={detalle.numero_lote || ''}
  onChange={(e) => /* actualizar estado */}
  placeholder="Ingrese lote"
/>
<input 
  type="date" 
  value={detalle.fecha_caducidad || ''}
  onChange={(e) => /* actualizar estado */}
  min={new Date().toISOString().split('T')[0]}
/>
```

---

### 2. Modales de Salida y Ajuste - STATUS OK ✅

**Archivo:** inventario-front/src/pages/InventarioCajaChica.jsx` (líneas 615-720+)

**Status:** Los modales YA están bien diseñados:
- ✅ Modal "Registrar Salida" tiene: cantidad, motivo, referencia
- ✅ Modal "Ajustar Inventario" tiene: nueva cantidad, motivo

**Verificar:**
- Backend debe soportar estos endpoints correctamente
- Verificar que los movimientos se registren en `movimientos_caja_chica`

---

### 3. Backend - Endpoints de Salida y Ajuste

**Archivos a revisar:**
- `backend/core/views.py` (InventarioCajaChicaViewSet)
- Buscar actions: `registrar_salida`, `ajustar`

**QA Request:**
```python
# POST /api/inventario-caja-chica/{id}/registrar_salida/
{
  "cantidad": 5,
  "motivo": "Uso en paciente Juan Pérez",
  "referencia": "EXP-12345"
}

# POST /api/inventario-caja-chica/{id}/ajustar/
{
  "cantidad_nueva": 10,
  "motivo": "Inventario físico - merma detectada"
}
```

Verificar que:
1. Se actualice `cantidad_actual` en `inventario_caja_chica`
2. Se cree registro en `movimientos_caja_chica`
3. Se valide que no haya stock negativo

---

### 4. Visibilidad para Farmacia - Dashboard Requerido

**Problema:** 
Farmacia no tiene vista consolidada del inventario de caja chica de todos los centros.

**Solución Propuesta:**
Crear vista SQL para reportes:

```sql
CREATE OR REPLACE VIEW vista_inventario_caja_chica_global AS
SELECT 
  icc.id,
  icc.centro_id,
  c.nombre AS centro_nombre,
  icc.producto_id,
  p.clave AS producto_clave,
  p.nombre AS producto_nombre,
  icc.numero_lote,
  icc.fecha_caducidad,
  icc.cantidad_actual,
  icc.precio_unitario,
  icc.ubicacion,
  CASE 
    WHEN icc.fecha_caducidad < CURRENT_DATE THEN 'caducado'
    WHEN icc.fecha_caducidad <= CURRENT_DATE + INTERVAL '15 days' THEN 'por_caducar'
    ELSE 'vigente'
  END AS estado_caducidad,
  icc.created_at,
  cca.folio AS compra_folio
FROM inventario_caja_chica icc
INNER JOIN centros c ON icc.centro_id = c.id
LEFT JOIN productos p ON icc.producto_id = p.id
LEFT JOIN compras_caja_chica cca ON icc.compra_id = cca.id
WHERE icc.activo = true
ORDER BY c.nombre, p.nombre, icc.fecha_caducidad;
```

**Frontend:**
- Agregar pestaña "Inventario Caja Chica" en módulo de Reportes
- Permitir filtrar por centro, producto, estado de caducidad
- Exportar a Excel

---

## 📋 Plan de Implementación

### Prioridad ALTA (Critical Path)
1. **Agregar campos lote y caducidad al modal de recepción** (ComprasCajaChica.jsx)
   - Estado actual: ❌ Campo inexistente
   - Tiempo estimado: 30 minutos

### Prioridad MEDIA
2. **Verificar endpoints backend de salida/ajuste** (views.py)
   - Verificar que existan y funcionen
   - Agregar validaciones si faltan

3. **Crear vista SQL para farmacia**
   - Script SQL listo (arriba)
   - Agregar migración
   - Crear endpoint GET /api/inventario-caja-chica/reporte-global/

### Prioridad BAJA
4. **Dashboard para farmacia**
   - Componente React nuevo
   - Gráficas de stock por centro
   - Alertas de caducidad

---

## 🛠️ Correcciones Técnicas Requeridas

### Archivo: ComprasCajaChica.jsx

**Cambio 1:** Agregar columnas en la tabla del modal de recepción

```jsx
// ANTES (línea 2448 - incompleto)
<thead className="bg-gray-50">
  <tr>
    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Producto</th>
    <th className="px-4 py-2 text-center text-xs font-medium text-gray-500">Lote</th>
    <th className="px-4 py-2 text-center text-xs font-medium text-gray-500">Comprado</th>
    <th className="px-4 py-2 text-center text-xs font-medium text-gray-500">Recibido *</th>
  </tr>
</thead>

// DESPUÉS (corregido)
<thead className="bg-gray-50">
  <tr>
    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Producto</th>
    <th className="px-4 py-2 text-center text-xs font-medium text-gray-500">Comprado</th>
    <th className="px-4 py-2 text-center text-xs font-medium text-gray-500">Recibido *</th>
    <th className="px-4 py-2 text-center text-xs font-medium text-gray-500">Lote *</th>
    <th className="px-4 py-2 text-center text-xs font-medium text-gray-500">Caducidad *</th>
  </tr>
</thead>
```

**Cambio 2:** Agregar inputs editables en tbody

```jsx
// DESPUÉS de la columna de cantidad_recibida (línea ~2470)
<td className="px-4 py-2 text-center">
  <input
    type="text"
    value={detalle.numero_lote || ''}
    onChange={(e) => {
      const newDetalles = [...recibirModal.detalles];
      newDetalles[index].numero_lote = e.target.value;
      setRecibirModal(prev => ({ ...prev, detalles: newDetalles }));
    }}
    placeholder="LOT-123"
    className="w-full px-2 py-1 border rounded text-center text-sm"
    required
  />
</td>
<td className="px-4 py-2 text-center">
  <input
    type="date"
    value={detalle.fecha_caducidad || ''}
    onChange={(e) => {
      const newDetalles = [...recibirModal.detalles];
      newDetalles[index].fecha_caducidad = e.target.value;
      setRecibirModal(prev => ({ ...prev, detalles: newDetalles }));
    }}
    min={new Date().toISOString().split('T')[0]}
    className="w-full px-2 py-1 border rounded text-sm"
    required
  />
</td>
```

**Cambio 3:** Validar campos antes de enviar (función `iniciarRecibir`)

```jsx
// Línea 1018 - Agregar validación de lote y caducidad
const detallesInvalidos = recibirModal.detalles.filter(d => {
  return !d.cantidad_recibida || 
         d.cantidad_recibida <= 0 || 
         d.cantidad_recibida > d.cantidad_comprada ||
         !d.numero_lote || // NUEVO
         !d.fecha_caducidad; // NUEVO
});

if (detallesInvalidos.length > 0) {
  toast.error('Todos los productos deben tener cantidad, lote y fecha de caducidad válidos');
  return;
}
```

**Cambio 4:** Enviar lote y caducidad al backend

```jsx
// Línea 1050 - Agregar campos al payload
await comprasCajaChicaAPI.recibir(recibirModal.compra.id, recibirModal.detalles.map(d => ({
  detalle_compra_id: d.id,
  cantidad_recibida: parseInt(d.cantidad_recibida),
  numero_lote: d.numero_lote, // NUEVO
  fecha_caducidad: d.fecha_caducidad // NUEVO
})));
```

---

### Archivo: views.py (Backend)

**Verificar endpoint:** `InventarioCajaChicaViewSet.registrar_salida`

```python
@action(detail=True, methods=['post'])
def registrar_salida(self, request, pk=None):
    """Registra una salida de inventario de caja chica"""
    item = self.get_object()
    
    cantidad = request.data.get('cantidad')
    motivo = request.data.get('motivo')
    referencia = request.data.get('referencia', '')
    
    # Validaciones
    if not cantidad or not motivo:
        return Response({'error': 'Cantidad y motivo son requeridos'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    cantidad = int(cantidad)
    if cantidad <= 0 or cantidad > item.cantidad_actual:
        return Response({'error': 'Cantidad inválida'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    # Actualizar inventario
    item.cantidad_actual -= cantidad
    item.save()
    
    # Registrar movimiento
    MovimientoCajaChica.objects.create(
        inventario=item,
        tipo='salida',
        cantidad=cantidad,
        cantidad_anterior=item.cantidad_actual + cantidad,
        cantidad_nueva=item.cantidad_actual,
        motivo=motivo,
        referencia=referencia,
        usuario=request.user
    )
    
    return Response({'success': True, 'mensaje': 'Salida registrada'})
```

---

## 🎯 Testing Requerido

### Test 1: Recepción con Lote y Caducidad
```
1. Crear compra de caja chica (médico)
2. Enviar a farmacia (farmacia verifica sin stock)
3. Autorizar (admin → director)
4. Registrar compra (fecha + factura)
5. Recibir productos:
   - Ingresar cantidad recibida
   - Ingresar lote: "LOT-2026-001"
   - Ingresar caducidad: "2027-03-01"
6. Verificar en Supabase:
   - inventario_caja_chica tiene numero_lote y fecha_caducidad
```

### Test 2: Salida de Inventario
```
1. Ir a Inventario Caja Chica
2. Seleccionar producto con stock > 0
3. Click "Registrar Salida"
4. Ingresar:
   - Cantidad: 2
   - Motivo: "Dispensación paciente"
   - Referencia: "EXP-12345"
5. Confirmar
6. Verificar:
   - cantidad_actual redujo correctamente
   - Registro en movimientos_caja_chica
```

### Test 3: Ajuste de Inventario
```
1. Ir a Inventario Caja Chica
2. Seleccionar producto
3. Click "Ajustar Inventario"
4. Cambiar cantidad (ej: de 10 a 8)
5. Motivo: "Inventario físico - merma"
6. Verificar movimiento de ajuste
```

---

## ✅ Checklist de Validación

- [ ] Frontend captura lote y caducidad en recepción
- [ ] Backend guarda lote y caducidad en `inventario_caja_chica`
- [ ] Modal de salida funciona correctamente
- [ ] Modal de ajuste funciona correctamente
- [ ] Movimientos se registran en `movimientos_caja_chica`
- [ ] Validaciones previenen stock negativo
- [ ] Vista SQL creada para reportes de farmacia
- [ ] Farmacia puede ver inventario global de centros
- [ ] Notificaciones de caducidad incluyen también caja chica
- [ ] Tests E2E pasan correctamente

---

## 📝 Notas del Desarrollador

**Arquitectura Actual:**
- Base de datos: PostgreSQL/Supabase ✅
- Tablas creadas correctamente ✅
- Campos de lote y caducidad existen en DB ✅
- **Gap:** Frontend no captura estos campos ❌

**Próximos Pasos:**
1. Implementar cambios en ComprasCajaChica.jsx (1 hora)
2. Verificar/crear endpoints backend (30 min)
3. Testing completo (1 hora)
4. Desplegar a producción (Render auto-deploy)

**Deployment:**
```bash
git add inventario-front/src/pages/ComprasCajaChica.jsx
git add backend/core/views.py  # si se modifica
git commit -m "feat: Agregar campos lote y caducidad a recepción caja chica"
git push origin main
```

---

**Documento creado:** 5 de marzo de 2026  
**Última actualización:** Pendiente de implementación  
**Responsable:** Equipo Dev
