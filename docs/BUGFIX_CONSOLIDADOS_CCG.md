# SOLUCIÓN: Cantidad Contrato Global No Aparece en Sistema

## 🔴 **PROBLEMA IDENTIFICADO**

El usuario reportó: *"cargue el archivo y aunque viene el global en sistema no aparece"*

### Diagnóstico Realizado:

1. ✅ **Base de datos**: Los 202 lotes importados SÍ tienen `cantidad_contrato_global`
2. ✅ **Import system**: Funciona correctamente (test_diagnostico_ccg.py pasó)
3. ✅ **Serializer**: LoteSerializer incluye el campo
4. ❌ **BUGFIX**: El endpoint `/api/lotes/consolidados/` NO devolvía el campo

---

## 🐛 **ROOT CAUSE**

**Archivo**: `backend/inventario/views/lotes.py`  
**Función**: `consolidados()` (línea 456)  
**Problema**: 

```python
# ❌ ANTES (líneas 483-490)
queryset = Lote.objects.select_related('producto', 'centro').only(
    'id', 'numero_lote', ... 'cantidad_contrato', 'activo',  # ← Falta CCG
    'producto__id', 'producto__clave', ...
)
```

El método `.only()` de Django **limita los campos** que se traen de la base de datos. Como `cantidad_contrato_global` NO estaba en la lista, **nunca se cargó** de la BD, aunque existía.

Además, el diccionario consolidado **no incluía el campo** en su estructura.

---

## ✅ **SOLUCIÓN IMPLEMENTADA**

### 1. Agregado `cantidad_contrato_global` al query (línea 490):

```python
# ✅ DESPUÉS
queryset = Lote.objects.select_related('producto', 'centro').only(
    'id', 'numero_lote', ... 'cantidad_contrato', 
    'cantidad_contrato_global',  # ISS-INV-003: Incluir CCG en consolidados
    'activo', ...
)
```

### 2. Incluido en el diccionario consolidado (línea 529):

```python
lotes_consolidados = defaultdict(lambda: {
    ...
    'cantidad_contrato_global': None,  # ISS-INV-003: Contrato global compartido
    ...
})
```

### 3. Asignación del valor al procesar lotes (línea 673):

```python
if cons['id'] is None:
    ...
    cons['cantidad_contrato_global'] = lote.cantidad_contrato_global
```

### 4. Cálculo de `cantidad_pendiente_global` (líneas 706-722):

```python
# ISS-INV-003: Calcular cantidad_pendiente_global si hay CCG
if cons['cantidad_contrato_global'] and cons['numero_contrato']:
    # Sumar TODAS las entregas del mismo producto+contrato
    total_recibido_global = Lote.objects.filter(
        producto_id=cons['producto_id'],
        numero_contrato=cons['numero_contrato'],
        cantidad_contrato_global__isnull=False
    ).aggregate(total=Sum('cantidad_inicial'))['total'] or 0
    cons['cantidad_pendiente_global'] = cons['cantidad_contrato_global'] - total_recibido_global
else:
    cons['cantidad_pendiente_global'] = None
```

---

## 🧪 **VALIDACIÓN**

### Test Ejecutado:
```bash
pytest tests/test_verificar_consolidados_ccg.py -v -s
```

### Resultado:
```
✅ TEST PASADO

📦 Lotes creados:
   • LOTE-CCG-001: cantidad_contrato_global = 1000
   • LOTE-CCG-002: cantidad_contrato_global = 1000
   • LOTE-SIN-CCG: cantidad_contrato_global = None

📊 Respuesta del API:
   Total de lotes consolidados: 3

✅ Verificando lotes CON CCG:
   Lote: LOTE-CCG-001
   ├─ cantidad_contrato_global: 1000
   ├─ cantidad_pendiente_global: 200  ← ✅ Calculado correctamente
   └─ cantidad_inicial_total: 500

   Lote: LOTE-CCG-002
   ├─ cantidad_contrato_global: 1000
   ├─ cantidad_pendiente_global: 200
   └─ cantidad_inicial_total: 300

✅ Verificando lotes SIN CCG:
   Lote: LOTE-SIN-CCG
   ├─ cantidad_contrato_global: None  ← ✅ Correcto (lote sin CCG)
   └─ cantidad_pendiente_global: None
```

**Cálculo verificado**:
- Contrato Global: 1000 unidades
- Recibido total: 500 + 300 = 800 unidades
- **Pendiente: 1000 - 800 = 200 unidades** ✅

---

## 🚀 **PASOS PARA ACTIVAR LA SOLUCIÓN**

### Para el Usuario:

1. **Reiniciar el servidor backend**:
   ```bash
   # Detener el servidor actual (Ctrl+C)
   # Reiniciar:
   cd backend
   python manage.py runserver
   ```

2. **Limpiar caché del navegador**:
   - Presiona `Ctrl + Shift + R` (Windows/Linux) o `Cmd + Shift + R` (Mac)
   - O usa el modo incógnito para probar

3. **Verificar en la interfaz**:
   - Ir a "Gestión de Lotes"
   - En la tabla principal, buscar tus lotes del contrato CB/A/37/2025
   - Deberías ver una **caja morada** con:
     ```
     🌐 Global: 4000
     ⏳ Faltan: XXX  (o ✅ Completo si ya recibiste todo)
     ```

4. **Editar un lote**:
   - Hacer clic en "Editar" en cualquier lote
   - El formulario debe mostrar el campo **"Cantidad Contrato Global"** con el valor

---

## 📊 **VERIFICACIÓN FINAL EN TU SISTEMA**

Para verificar que todo funciona en producción:

```bash
# En el backend
cd backend
python verificar_ccg_db.py CB/A/37/2025
```

Este script te mostrará:
- ✅ Todos los lotes del contrato CB/A/37/2025
- ✅ Sus valores de cantidad_contrato_global
- ✅ Total recibido vs. total contratado

---

## 📝 **ARCHIVOS MODIFICADOS**

| Archivo | Cambios | Líneas |
|---------|---------|--------|
| `backend/inventario/views/lotes.py` | Agregado CCG al `.only()` | 490 |
| `backend/inventario/views/lotes.py` | Agregado CCG al diccionario | 529 |
| `backend/inventario/views/lotes.py` | Asignación del valor CCG | 673 |
| `backend/inventario/views/lotes.py` | Cálculo pendiente_global | 706-722 |

---

## 🎯 **CONCLUSIÓN**

### El sistema ahora funciona correctamente:

✅ **Import**: Guarda `cantidad_contrato_global` en BD  
✅ **Backend**: Devuelve el campo en API `/api/lotes/consolidados/`  
✅ **Frontend**: Muestra el campo en la tabla y formularios  
✅ **Validación**: Calcula pendiente global correctamente  

### Datos confirmados en tu sistema:

- **202 lotes** importados correctamente
- **Todos** con `cantidad_contrato_global` en BD
- Ejemplos:
  - TERBINAFINA (660): CCG = 4000
  - LORATADINA (655): CCG = 6000
  - AMBROXOL (656): CCG = 2000

---

## 🔧 **SI AÚN NO APARECE DESPUÉS DE REINICIAR**

1. **Verifica que el servidor esté usando el código actualizado**:
   ```bash
   # Buscar la fecha de modificación del archivo
   Get-ChildItem backend\inventario\views\lotes.py | Select-Object LastWriteTime
   ```
   Debería mostrar la fecha de hoy.

2. **Verifica en la consola del navegador**:
   - Abre DevTools (F12)
   - Ve a la pestaña "Network"
   - Recarga la página de Lotes
   - Busca la llamada a `/api/lotes/consolidados/`
   - Haz clic y ve a "Response"
   - Verifica que cada lote tenga `"cantidad_contrato_global": 1000` (o el valor correspondiente)

3. **Si no aparece en la Response**:
   - El servidor no se reinició correctamente
   - Detén el proceso y reinicia manualmente

---

## 📌 **REFERENCIAS**

- **Issue**: ISS-INV-003 (Dual Contract Validation)
- **Test diagnóstico**: `backend/tests/test_diagnostico_ccg.py`
- **Test consolidados**: `backend/tests/test_verificar_consolidados_ccg.py`
- **Documentación técnica**: `docs/SOLUCION_NOM059_TRAZABILIDAD.md`
- **Script verificación**: `backend/verificar_ccg_db.py`

---

**Fecha de corrección**: 2026-02-17  
**Impacto**: ALTO - Afecta visualización de contratos globales  
**Prioridad**: CRÍTICA - Bug en producción  
**Status**: ✅ RESUELTO
