# Corrección de Visualización de Lotes por Centro

## Problema Reportado
1. **Lotes no se visualizan correctamente por centro**: Un producto mostraba inventario de 2, pero solo 1 lote cuando deberían ser 2 lotes separados.
2. **Módulo de movimientos**: Solo permite filtrar por producto, debería filtrar por lote limitado al centro.
3. **Carga lenta del log**: Con errores del servidor después de un tiempo.

## Causa Raíz Identificada
Posible inconsistencia entre la constraint de unicidad en Django y Supabase:
- **Django Model**: `unique_together = [['numero_lote', 'producto', 'centro']]`
- **Supabase (sospecha)**: `lote_producto_unique (numero_lote, producto_id)` - SIN `centro_id`

Esto causaría que cuando se surte una requisición:
1. Farmacia Central tiene Lote "ABC-001" del Producto 615
2. Al surtir al Centro A, `_obtener_o_crear_lote_destino` intenta crear lote "ABC-001" con centro=Centro_A
3. Si la constraint en Supabase solo considera `(numero_lote, producto_id)`, el INSERT falla
4. El sistema actualiza el lote existente de Farmacia Central en lugar de crear uno nuevo

## Archivos Modificados

### 1. `backend/inventario/services/requisicion_service.py`

**Cambio**: Mejorado `_obtener_o_crear_lote_destino()` para manejar errores de constraint

```python
def _obtener_o_crear_lote_destino(self, lote_origen, centro_destino, cantidad):
    """
    ISS-FIX (lotes-centro): Manejo robusto de creación de lotes en destino.
    
    Cambios:
    - Agrega manejo de IntegrityError si la constraint difiere de lo esperado
    - Logging detallado para diagnóstico
    - Fallback a actualización si la creación falla
    """
```

### 2. `backend/inventario/views_legacy.py`

**Cambios**:

a) **Endpoint `lotes` en ProductoViewSet** - Añadido logging de diagnóstico:
```python
@action(detail=True, methods=['get'], url_path='lotes')
def lotes(self, request, pk=None):
    """
    ISS-FIX (lotes-centro): Agregado logging detallado para diagnóstico.
    Registra antes/después del filtrado para identificar problemas.
    """
```

b) **Nuevo endpoint `lotes-diagnostico`**:
```
GET /api/productos/{id}/lotes-diagnostico/
```
- Solo accesible para admin/farmacia
- Muestra TODOS los lotes del producto sin filtros de centro
- Agrupa lotes por centro con estadísticas

### 3. `backend/inventario/views/lotes.py`

**Nuevo endpoint `diagnostico-centro`**:
```
GET /api/lotes/diagnostico-centro/?producto_id={id}
```
- Solo accesible para admin/farmacia
- Muestra distribución de lotes de un producto entre todos los centros
- Lista centros con y sin lotes del producto

### 4. `inventario-front/src/pages/Movimientos.jsx`

**Cambios**:

a) **Mejorada función `cargarCatalogos`**:
```javascript
// Antes: No pasaba centro explícitamente
const lotesRes = await api.get('/lotes/', { params: { ... } });

// Después: Pasa centro explícito y usa con_stock
const lotesRes = await api.get('/lotes/', {
  params: {
    centro: centroUsuario?.id || 'central',
    con_stock: 'con_stock',
    ...
  }
});
```

b) **Filtro de lote cambiado de texto a select**:
```jsx
// Antes: Input de texto para buscar número de lote
<input type="text" value={filtros.lote} ... />

// Después: Select dropdown con lotes disponibles
<select value={filtros.lote} ...>
  {lotesDisponibles.map(lote => (
    <option value={lote.numero_lote}>
      {lote.numero_lote} - {lote.producto_nombre} (Stock: {lote.cantidad_actual})
    </option>
  ))}
</select>
```

## Verificación de Constraint en Supabase

Para verificar si la constraint en Supabase incluye `centro_id`, ejecutar:

```sql
SELECT 
    conname as constraint_name,
    pg_get_constraintdef(oid) as constraint_definition
FROM pg_constraint 
WHERE conrelid = 'lotes'::regclass 
  AND contype = 'u';
```

**Si la constraint NO incluye `centro_id`**, corregir con:

```sql
-- Eliminar constraint antigua
ALTER TABLE lotes DROP CONSTRAINT lote_producto_unique;

-- Crear constraint correcta
ALTER TABLE lotes ADD CONSTRAINT lote_producto_centro_unique 
    UNIQUE (numero_lote, producto_id, centro_id);
```

## Endpoints de Diagnóstico

### Uso del endpoint de diagnóstico de productos:
```bash
GET /api/productos/615/lotes-diagnostico/
Authorization: Bearer <token_admin>
```

Respuesta:
```json
{
  "producto": {
    "id": 615,
    "clave": "010.000.0...",
    "nombre": "PARACETAMOL..."
  },
  "diagnostico": {
    "total_lotes_bd": 3,
    "total_stock_global": 150,
    "lotes_activos": 3,
    "lotes_con_stock": 2
  },
  "lotes_por_centro": {
    "Farmacia Central (NULL)": {
      "centro_id": null,
      "lotes": [...],
      "total_stock": 100,
      "total_lotes": 1
    },
    "Centro A": {
      "centro_id": 1,
      "lotes": [...],
      "total_stock": 25,
      "total_lotes": 1
    }
  }
}
```

### Uso del endpoint de diagnóstico de lotes:
```bash
GET /api/lotes/diagnostico-centro/?producto_id=615
Authorization: Bearer <token_admin>
```

## Pruebas Recomendadas

1. **Verificar lotes por centro**:
   - Iniciar sesión como admin
   - Usar endpoint de diagnóstico para ver distribución real de lotes
   - Comparar con lo que ve un usuario de centro

2. **Probar creación de lote por requisición**:
   - Crear requisición desde Centro A
   - Surtir requisición desde Farmacia Central
   - Verificar que se cree un nuevo lote en Centro A (no se actualice el de Farmacia)

3. **Verificar filtro de movimientos**:
   - Iniciar sesión como usuario de centro
   - Ir a Movimientos
   - El dropdown de lotes solo debe mostrar lotes de su centro con stock

## Logs de Diagnóstico

Los cambios agregan logs que aparecerán en:
- `[ISS-FIX]` - Prefijo para cambios relacionados con este issue
- `[LOTES-ENDPOINT]` - Logs del endpoint de lotes de productos
- `[OBTENER_O_CREAR_LOTE]` - Logs de creación de lotes en surtido

Revisar logs en:
```bash
tail -f backend/logs/app.log | grep -E "ISS-FIX|LOTES-ENDPOINT|OBTENER_O_CREAR_LOTE"
```
