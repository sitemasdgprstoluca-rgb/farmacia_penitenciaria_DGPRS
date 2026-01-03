# CORRECCIONES CONSISTENCIA MOVIMIENTOS

## Fecha: 2026-01-03

## Problema Identificado

Discrepancia entre las métricas mostradas en:
1. **Dashboard**: Mostraba "5 movimientos este mes"
2. **Reporte de Movimientos**: Mostraba "22 movimientos" con datos inconsistentes en los paneles

### Causa Raíz

1. **Dashboard** contaba registros individuales de la tabla `movimientos`
2. **Reporte** agrupaba por transacción (referencia) y sumaba productos
3. Los campos `total_entradas` y `total_salidas` eran **sumas de unidades**, no conteos de registros
4. El frontend del reporte no mostraba claramente qué representaba cada número

## Correcciones Implementadas

### 1. Backend - Reporte de Movimientos (`views_legacy.py`)

```python
# Añadidos nuevos campos al resumen:
resumen = {
    'total_transacciones': len(datos),           # Grupos únicos por referencia
    'total_movimientos': sum(total_productos),   # Registros individuales
    'total_entradas': total_entradas,            # UNIDADES de entrada
    'total_salidas': total_salidas,              # UNIDADES de salida
    'diferencia': total_entradas - total_salidas, # Balance de unidades
    'count_entradas': count_entradas,            # CONTEO de registros entrada
    'count_salidas': count_salidas,              # CONTEO de registros salida
}
```

### 2. Frontend - Reporte de Movimientos (`Reportes.jsx`)

- Filtro por defecto del mes actual (igual que dashboard)
- Indicador visual del período seleccionado
- Etiquetas claras para cada métrica:
  - **Transacciones**: grupos únicos
  - **Movimientos**: registros individuales
  - **Entradas/Salidas**: unidades (con conteo de registros)
  - **Balance**: diferencia neta de unidades
- Botones rápidos "Este mes" / "Todo el historial"

### 3. Pruebas Unitarias Creadas

#### `tests/test_movimientos_consistencia.py`
- `TestMovimientosConsistencia`: Verifica conteos y agrupaciones
- `TestDashboardMovimientos`: Verifica KPI del dashboard
- `TestReporteMovimientos`: Verifica API del reporte
- `TestConsistenciaFrontBackDB`: Documenta definiciones de métricas

#### `tests/test_api_movimientos_reportes.py`
- `TestReporteMovimientosAPI`: Tests de integración para endpoint
- `TestDashboardKPIsAPI`: Tests para KPIs del dashboard

## Definiciones de Métricas (ESTÁNDAR)

| Métrica | Definición | Ejemplo |
|---------|------------|---------|
| `total_transacciones` | Número de referencias únicas | 3 transacciones |
| `total_movimientos` | Registros individuales en tabla | 4 registros |
| `total_entradas` | Suma de cantidades tipo entrada | 180 unidades |
| `total_salidas` | Suma de cantidades tipo salida | 20 unidades |
| `count_entradas` | Número de registros tipo entrada | 3 registros |
| `count_salidas` | Número de registros tipo salida | 1 registro |
| `diferencia` | `total_entradas - total_salidas` | 160 unidades |

## Estructura de Transacciones

Una **transacción** agrupa múltiples **movimientos** (registros) que comparten la misma `referencia`:

```
Transacción REP-TEST-001
├── Movimiento 1: entrada 100 unidades
└── Movimiento 2: entrada 50 unidades
    → total_productos: 2
    → total_cantidad: 150
```

## Ejecución de Pruebas

```bash
cd backend
python -m pytest tests/test_movimientos_consistencia.py -v
python -m pytest tests/test_api_movimientos_reportes.py -v
```

## Archivos Modificados

1. `backend/inventario/views_legacy.py` - Endpoint reporte_movimientos
2. `inventario-front/src/pages/Reportes.jsx` - UI del reporte
3. `backend/tests/test_movimientos_consistencia.py` - Pruebas nuevas
4. `backend/tests/test_api_movimientos_reportes.py` - Pruebas API
