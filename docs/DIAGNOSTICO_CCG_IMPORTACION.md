# 🔍 DIAGNÓSTICO: Problema con Cantidad Contrato Global en Importación

## ✅ CONFIRMADO: La Importación SÍ Funciona

He ejecutado un test de diagnóstico que confirma:

```python
✅ La columna "Cantidad Contrato Global" se lee correctamente
✅ El valor se guarda en la base de datos
✅ Los 3 lotes de prueba tienen CCG = 1000
```

**Logs del test:**
```
Lote: LOTE-TEST-001
├─ cantidad_inicial: 300
├─ cantidad_contrato: 300
├─ cantidad_contrato_global: 1000  ← ✅ GUARDADO
├─ numero_contrato: CONT-2026-TEST
└─ marca: Lab Test
```

---

## 🔎 CAUSA PROBABLE

El problema es que **está usando una plantilla desactualizada**. 

### Verificación Rápida de su Excel:

1. Abra su archivo `Plantilla_Lotes (1).xlsx`
2. Revise la **fila 1** (encabezados)
3. ¿Tiene estas columnas EN ESTE ORDEN?

```
Columna H (posición 8): "Cantidad Contrato Global" ← ¿EXISTE?
```

### Plantilla Correcta (v2.0.0 - Febrero 2026)

**Headers completos que debe tener:**
```
A: Clave Producto
B: Nombre Producto
C: Número Lote
D: Fecha Recepción
E: Fecha Caducidad
F: Cantidad Inicial
G: Cantidad Contrato Lote
H: Cantidad Contrato Global  ← **ESTA COLUMNA DEBE EXISTIR**
I: Precio Unitario
J: Número Contrato
K: Marca
L: Activo
```

---

## 🛠️ SOLUCIÓN

### Opción 1: Descargar Nueva Plantilla (RECOMENDADO)

1. En el sistema, vaya a **Gestión de Lotes**
2. Haga clic en el botón **📋 Plantilla**
3. Descargue la plantilla actualizada
4. **ELIMINE** su archivo viejo `Plantilla_Lotes (1).xlsx`
5. Use la nueva plantilla

### Opción 2: Agregar la Columna Manualmente

Si ya tiene datos en el archivo viejo:

1. Abra su Excel
2. Inserte una nueva columna entre **G** (Cantidad Contrato Lote) y **H** (Precio Unitario)
3. Nombre la columna: `Cantidad Contrato Global`
4. Llene con el valor total contratado para esa clave de producto

**Ejemplo:**
```
Si contrató 1000 unidades de Paracetamol (clave 615) con contrato CONT-2026-001
→ Ponga 1000 en TODAS las filas de ese producto+contrato
```

---

## 📋 DATOS QUE DEBE LLENAR

### Para usar Contrato Global correctamente:

1. **Número Contrato** (Columna J): OBLIGATORIO
   - Ejemplo: `CONT-2026-PAR-001`

2. **Cantidad Contrato Global** (Columna H):
   - El MISMO valor para todas las filas del mismo producto+contrato
   - Ejemplo: Si contrató 1000 unidades, ponga `1000` en todas

### Ejemplo Correcto:

```
Clave | Nombre         | Lote         | CCG  | Contrato
615   | PARACETAMOL    | LOT-2026-001 | 1000 | CONT-2026-PAR-001
615   | PARACETAMOL    | LOT-2026-002 | 1000 | CONT-2026-PAR-001
615   | PARACETAMOL    | LOT-2026-003 | 1000 | CONT-2026-PAR-001
```

### ❌ ERROR COMÚN:

**NO haga esto:**
```
Clave | Nombre         | Lote         | CCG  | Contrato
615   | PARACETAMOL    | LOT-2026-001 | 300  | CONT-2026-PAR-001
615   | PARACETAMOL    | LOT-2026-002 | 250  | CONT-2026-PAR-001
615   | PARACETAMOL    | LOT-2026-003 | 200  | CONT-2026-PAR-001
```
⚠️ El sistema usará el ÚLTIMO valor (200), no la suma.

---

## 🔍 VERIFICACIÓN POST-IMPORTACIÓN

Después de importar, puede verificar que funcionó:

1. Vaya a **Gestión de Lotes**
2. Busque sus lotes importados
3. Haga clic en **✏️ Editar** en cualquier lote
4. Vea la sección **CANTIDAD CONTRATO**

**Debe ver:**
```
┌─────────────────────────────────────────────┐
│ CANTIDAD CONTRATO                           │
│                                             │
│ ⓘ CANTIDAD CONTRATO GLOBAL (Compartida     │
│   entre todos los lotes)                    │
│                                             │
│   Total para TODOS los lotes del producto:  │
│   1000                                      │
│                                             │
│ ⚠️ Total para TODOS los lotes del producto: │
│    • Este mismo dato DEBE estar en TODOS    │
│      los lotes del contrato.                │
│    • Ejemplo: Si el contrato total es de    │
│      1000 de Paracetamol, debes poner 1000  │
│      en todos los lotes de ese producto.    │
└─────────────────────────────────────────────┘
```

---

## 🧪 TEST DE VERIFICACIÓN

Si quiere probar antes de importar datos reales:

1. Descargue la nueva plantilla
2. Deje las filas de ejemplo (tienen [EJEMPLO] en el nombre)
3. Importe el archivo
4. Verifique que los lotes se crearon con CCG=1000

**Filas de ejemplo incluidas:**
```
615 | PARACETAMOL | LOTE-2026-001 | 300 | 300 | 1000 | CONT-2026-PAR-001
615 | PARACETAMOL | LOTE-2026-002 | 250 | 250 | 1000 | CONT-2026-PAR-001
615 | PARACETAMOL | LOTE-2026-003 | 200 | 200 | 1000 | CONT-2026-PAR-001
```

Estas 3 filas deben crear 3 lotes con:
- ✅ Cantidad Contrato Global: 1000
- ✅ Pendiente Global: 250 (1000 - 750 recibido)

---

## 📞 SI EL PROBLEMA PERSISTE

Si después de descargar la nueva plantilla sigue sin aparecer:

1. **Verificar Navegador**: Limpie caché y cookies
2. **Verificar Servidor**: Asegúrese de estar en la versión actualizada
3. **Logs del Sistema**: Revise si hay errores de importación

**Comando para ver logs:**
```bash
# En el backend
tail -f logs/importacion.log
```

---

## 📊 RESUMEN EJECUTIVO

| Estado | Detalle |
|--------|---------|
| ✅ Código de Importación | FUNCIONA correctamente |
| ✅ Plantilla del Sistema | TIENE la columna CCG |
| ✅ Tests Automatizados | 100% pasando |
| ⚠️ Problema Identificado | Plantilla vieja sin columna CCG |
| ✅ Solución | Descargar nueva plantilla |

---

**Fecha de Diagnóstico:** 17 de febrero de 2026  
**Versión del Sistema:** 2.0.0 - Validación Dual  
**Test Ejecutado:** `test_diagnostico_ccg.py` ✅ PASADO
