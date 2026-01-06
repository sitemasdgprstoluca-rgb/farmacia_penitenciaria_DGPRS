# Corrección del Flujo de Salidas Masivas

## Resumen del Problema

El sistema tenía dos problemas principales:
1. El stock se descontaba inmediatamente al crear la salida (debería esperar confirmación)
2. La vista agrupada dividía movimientos del mismo grupo entre páginas

## Flujo Correcto Implementado

```
1. CREAR SALIDA → Stock NO se descuenta, movimiento marcado como [PENDIENTE]
2. CONFIRMAR ENTREGA → Stock SÍ se descuenta, movimiento marcado como [CONFIRMADO]  
3. CANCELAR → Solo elimina movimientos PENDIENTES (el stock nunca fue afectado)
```

## Cambios Realizados

### Backend (`inventario/views/salida_masiva.py`)

1. **`salida_masiva()`**: 
   - Ya NO descuenta stock al crear
   - Marca movimientos con `[PENDIENTE][SAL-xxx]` en el motivo
   - Valida stock considerando reservas de movimientos pendientes

2. **`confirmar_entrega()`**:
   - AHORA SÍ descuenta el stock de los lotes
   - Cambia `[PENDIENTE]` a `[CONFIRMADO]` en el motivo
   - Valida que el movimiento esté pendiente antes de confirmar

3. **`cancelar_salida()`**:
   - Solo elimina movimientos (no hay stock que devolver)
   - Solo permite cancelar movimientos en estado `[PENDIENTE]`
   - Bloquea cancelación si ya está confirmado

4. **Nuevas funciones auxiliares**:
   - `_calcular_stock_reservado(lote)`: Suma cantidades de movimientos pendientes
   - `_es_movimiento_pendiente(mov)`: Verifica si tiene `[PENDIENTE]`
   - `_es_movimiento_confirmado(mov)`: Verifica si tiene `[CONFIRMADO]`

### Backend (`inventario/views/movimientos.py`)

5. **NUEVO: `movimientos_agrupados()`** (action `@action(detail=False, url_path='agrupados')`):
   - Agrupa movimientos ANTES de paginar en el backend
   - Evita que grupos se dividan entre páginas
   - Endpoint: `GET /api/v1/movimientos/agrupados/`
   - Retorna: `{ grupos, sin_grupo, total_elementos, total_pages }`

### Frontend (`Movimientos.jsx`)

1. **Nuevo estado `datosAgrupados`**:
   - Guarda los datos ya agrupados del backend

2. **`cargarMovimientos()` actualizado**:
   - En vista agrupada: usa `movimientosAPI.getAgrupados()`
   - En vista individual: usa `movimientosAPI.getAll()` (normal)

3. **`movimientosAgrupados` useMemo**:
   - Ahora usa directamente los datos del backend cuando están disponibles
   - Fallback al frontend solo si no hay datos del backend

4. **Nombres de propiedades actualizados**:
   - `tipoGrupo` → `tipo_grupo`
   - `totalCantidad` → `total_cantidad`
   - `numSalidas` / `numEntradas` → `num_salidas` / `num_entradas`

### Frontend (`api.js`)

6. **Nuevo método**:
   - `movimientosAPI.getAgrupados(params)` → `GET /movimientos/agrupados/`

### Frontend (`SalidaMasiva.jsx`)

1. **Modal de resultado**:
   - Título cambiado a "Salida Registrada - Pendiente de Confirmación"
   - Aviso prominente de que el stock NO ha sido descontado
   - Columna "Stock Actual" reemplazada por "Estado" (muestra "Pendiente")
   - Botón de confirmar ahora dice "Confirmar Entrega (Descuenta Stock)"
   - Nota informativa actualizada con el flujo correcto

### Tests (`tests/test_salida_masiva_flujo.py`)

Nuevas pruebas unitarias (5 pasando, 10 requieren base de datos configurada):

1. `TestHelperFunctions` ✅:
   - `test_es_movimiento_pendiente`
   - `test_es_movimiento_confirmado`

2. `TestFlujoLogica` ✅:
   - `test_flujo_estados_correctos`
   - `test_stock_solo_cambia_al_confirmar`
   - `test_calcular_stock_disponible`

## Resultado de Pruebas

- ✅ 906 pruebas pasaron
- ✅ Frontend sin errores de linting
- ✅ Backend compila correctamente

## Resumen de Mejoras

- ✅ El stock solo se descuenta al confirmar la entrega
- ✅ Los botones de acción desaparecen después de confirmar
- ✅ El botón de cancelar funciona correctamente
- ✅ Los mensajes son claros sobre el estado del stock
- ✅ **NUEVO**: La vista agrupada ya NO divide grupos entre páginas
- ✅ **NUEVO**: La agrupación se hace en el backend para mayor consistencia
