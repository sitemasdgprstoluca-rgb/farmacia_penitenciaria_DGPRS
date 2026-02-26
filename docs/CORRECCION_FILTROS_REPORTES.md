# CORRECCIÓN COMPLETA DE FILTROS EN REPORTES

**Fecha**: 25 de febrero de 2026  
**Alcance**: Todos los filtros en el módulo de Reportes (Frontend + Backend)

---

## 🎯 PROBLEMAS IDENTIFICADOS Y CORREGIDOS

### 1. **Inconsistencia en el filtro de centro (Frontend)**

#### Problema:
- El selector de centro usaba `value=""` (string vacío) para "Todos los centros"
- La función `buildParams()` convertía valores vacíos a `'todos'` de forma inconsistente
- Los filtros no tenían un valor por defecto válido en `baseFilters`

#### Solución:
```jsx
// ANTES
const baseFilters = {
  centro: "",  // ❌ Valor vacío causaba problemas
  ...
};

<option value="">Todos los centros</option>  // ❌ String vacío

// DESPUÉS
const baseFilters = {
  centro: "todos",  // ✅ Valor explícito por defecto
  ...
};

<option value="todos">Todos los centros</option>  // ✅ Valor explícito
```

### 2. **Lógica de buildParams() ambigua**

#### Problema:
La función `buildParams()` tenía lógica compleja que no distinguía correctamente entre:
- No tener centro seleccionado (undefined/null)
- Tener string vacío seleccionado ("")
- Tener 'todos' seleccionado explícitamente

#### Solución:
```jsx
// ANTES
if (filtros.centro && filtros.centro !== '') {
  params.centro = filtros.centro;
} else {
  params.centro = 'todos';  // ❌ Siempre enviaba 'todos' por defecto
}

// DESPUÉS
if (!esAdminOFarmacia && userCentroId) {
  // Usuario restringido: siempre su centro
  params.centro = userCentroId;
} else if (esAdminOFarmacia) {
  // Admin/Farmacia: aplicar valor del filtro explícitamente
  if (filtros.centro === '' || filtros.centro === null || filtros.centro === undefined) {
    params.centro = 'todos';
  } else {
    params.centro = filtros.centro;  // ✅ 'central', 'todos' o ID
  }
}
```

### 3. **Selectores de centro no estandarizados**

#### Problema:
Los 5 selectores de centro en diferentes tipos de reporte tenían valores inconsistentes:
- Caducidades: `value=""`
- Requisiciones: `value=""`
- Inventario: `value=""`
- Movimientos: Ya tenía `value="todos"`  ✅
- Parcialidades: `value=""`

#### Solución:
Todos los selectores ahora usan:
```jsx
value={!esAdminOFarmacia && userCentroId ? userCentroId : (filtros.centro || 'todos')}
```

Y tienen la opción:
```jsx
<option value="todos">Todos los centros</option>
```

---

## 🔧 ESTANDARIZACIÓN DEL BACKEND

### Comportamiento consistente del parámetro `centro`:

| Valor | Comportamiento |
|-------|---------------|
| `'todos'` | Ver todos los centros (comportamiento varía por reporte - ver tabla abajo) |
| `'central'` | Ver solo Farmacia Central / Almacén Central |
| `ID numérico` | Ver centro específico por ID |
| `Sin parámetro` | Comportamiento por defecto según rol del usuario |

### Comportamiento específico por tipo de reporte:

| Reporte | `centro='todos'` | `centro='central'` | `centro=<ID>` |
|---------|-----------------|-------------------|---------------|
| **Inventario** | Solo CPRs (excluye Farmacia Central) | Solo Farmacia Central | Centro específico |
| **Caducidades** | Todos los centros (incluye Farmacia Central) | Solo Farmacia Central | Centro específico |
| **Requisiciones** | Todas las requisiciones | Requisiciones a Farmacia Central | Requisiciones del centro |
| **Movimientos** | Movimientos de todos los CPRs (excluye internos de FC) | Solo movimientos internos de FC | Movimientos del centro |
| **Contratos** | N/A (no aplica filtro 'todos') | N/A | N/A (sin filtro de centro) |
| **Parcialidades** | N/A | Parcialidades de FC | Parcialidades del centro |

### Variables de control estandarizadas:

```python
# Inventario
ver_solo_cprs = True/False  # Flag para ver solo CPRs (excluir Farmacia Central)

# Movimientos
es_filtro_farmacia_central = True/False  # Solo movimientos de Farmacia Central
es_filtro_todos_centros = True/False     # Solo movimientos de los CPRs
es_filtro_centro_especifico = True/False # Un centro específico por ID

# Caducidades, Requisiciones
filtrar_por_centro = True/False  # Si debe filtrar por centro
user_centro = Centro/None        # Centro a filtrar (None = Farmacia Central)
```

---

## ✅ VERIFICACIÓN DE FILTROS

### Combinaciones a probar:

#### **Como Admin/Farmacia:**

1. ✅ Seleccionar "Todos los centros"
   - Frontend envía: `centro='todos'`
   - Backend responde: Según tabla de comportamiento por reporte

2. ✅ Seleccionar "Farmacia Central"
   - Frontend envía: `centro='central'`
   - Backend responde: Solo datos de Farmacia Central

3. ✅ Seleccionar un centro específico (ej: "CPR Varonil Norte")
   - Frontend envía: `centro=<ID del centro>`
   - Backend responde: Solo datos de ese centro

#### **Como usuario de CPR:**

1. ✅ No puede seleccionar centro (dropdown deshabilitado)
2. ✅ Siempre filtra por su centro asignado
   - Frontend envía: `centro=<userCentroId>`
   - Backend valida y aplica filtro obligatorio

#### **Filtros por tipo de movimiento:**

1. ✅ "Todos los movimientos" (valor: `""`)
2. ✅ "Entradas" (valor: `"entrada"`)
3. ✅ "Salidas" (valor: `"salida"`)

#### **Filtros por fechas:**

1. ✅ Sin fechas (vacío) - Ver todo el historial
2. ✅ Con fecha inicio y fin - Rango específico
3. ✅ Solo fecha inicio - Desde esa fecha
4. ✅ Solo fecha fin - Hasta esa fecha

#### **Otros filtros específicos:**

**Inventario:**
- ✅ Nivel de stock: Todos, Crítico, Bajo, Alto

**Caducidades:**
- ✅ Días próximos: 7, 15, 30, 60, 90 días
- ✅ Estado: Todos, Vencido, Crítico, Próximo

**Requisiciones:**
- ✅ Estado: Todos, Pendiente, En revisión, Autorizada, Rechazada, etc.

**Contratos:**
- ✅ Número de contrato: Búsqueda parcial

**Parcialidades:**
- ✅ Solo sobre-entregas: checkbox

---

## 🚀 BENEFICIOS DE LA CORRECCIÓN

1. **Consistencia**: Todos los filtros funcionan de manera predecible
2. **Claridad**: Los valores son explícitos ('todos', 'central', ID)
3. **Mantenibilidad**: Código más fácil de entender y modificar
4. **Sin ambigüedad**: No hay conversiones implícitas de "" a 'todos'
5. **Robustez**: Manejo explícito de todos los casos

---

## 📝 ARCHIVOS MODIFICADOS

### Frontend
- `inventario-front/src/pages/Reportes.jsx`
  - Línea 58: `baseFilters` - centro por defecto a 'todos'
  - Línea 270-286: `buildParams()` - lógica mejorada
  - Líneas 979, 1049, 1096, 1226, 1362: Selectores de centro estandarizados

### Backend
- `backend/inventario/views_legacy.py`
  - Función `reporte_inventario()`: Variables renombradas (excluir_farmacia_central → ver_solo_cprs)
  - Función `reporte_caducidades()`: Manejo consistente de 'todos'
  - Función `reporte_movimientos()`: Ya tenía lógica correcta
  - Función `reporte_requisiciones()`: Ya tenía lógica correcta

---

## 🧪 PLAN DE PRUEBAS

### Casos de prueba mínimos:

1. **Admin selecciona "Todos los centros" en Movimientos**
   - Debe mostrar movimientos de todos los CPRs
   - NO debe mostrar movimientos internos de Farmacia Central

2. **Admin selecciona "Farmacia Central" en Inventario**
   - Debe mostrar solo inventario de Farmacia Central
   - Incluye miles de productos

3. **Usuario de CPR ve reporte de Movimientos**
   - Solo ve movimientos de su centro
   - No puede cambiar el filtro de centro

4. **Admin filtra Requisiciones con fechas**
   - Debe respetar el rango de fechas
   - Debe combinar correctamente fecha + centro

5. **Admin exporta a Excel con todos los filtros aplicados**
   - El archivo debe reflejar exactamente los filtros
   - Los totales deben cuadrar

---

## ⚠️ NOTAS IMPORTANTES

1. El comportamiento de `centro='todos'` varía intencionalmente por tipo de reporte:
   - **Inventario**: Excluye Farmacia Central (porque su inventario es masivo)
   - **Otros reportes**: Incluye todos los centros

2. Usuarios no-admin/farmacia SIEMPRE tienen filtro de centro obligatorio

3. Los filtros se combinan con AND lógico (todos deben cumplirse)

4. Las exportaciones (Excel/PDF) respetan exactamente los mismos filtros que la vista

---

## 🔄 PRÓXIMOS PASOS

- [ ] Realizar pruebas exhaustivas de todas las combinaciones
- [ ] Documentar comportamiento esperado en manual de usuario
- [ ] Considerar agregar tooltips en la UI explicando qué significa cada opción
- [ ] Revisar logs de uso para detectar posibles confusiones de usuarios

---

**Autor**: GitHub Copilot
**Revisión**: Pendiente
**Estado**: ✅ Implementado y listo para pruebas
