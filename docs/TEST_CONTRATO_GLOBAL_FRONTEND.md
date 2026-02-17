# Plan de Testing Frontend - Sistema de Contrato Global (ISS-INV-003)

## Resumen

Este documento define los escenarios de prueba E2E para verificar la correcta implementación del sistema de contrato global en el frontend.

---

## 1. Escenarios de Testing Funcional

### 1.1 Verificación de Cálculos Visibles

| ID | Escenario | Pasos | Resultado Esperado |
|----|-----------|-------|-------------------|
| F01 | Cálculo de pendiente global | 1. Crear lote con CCG=500, cantidad_inicial=200 | `cantidad_pendiente_global = 300` |
| F02 | Múltiples lotes | 1. Crear lote A (200), lote B (150), ambos CCG=500 | Pendiente = 150 en ambos lotes |
| F03 | Salidas no afectan pendiente | 1. Lote con CCG=500, inicial=200<br>2. Registrar salida de 100 | Pendiente sigue en 300 (no 400) |
| F04 | Entrada aumenta cumplimiento | 1. Lote CCG=500, inicial=200<br>2. Entrada de 100 | Pendiente baja a 200 |

### 1.2 Alertas Visuales

| ID | Escenario | Pasos | Resultado Esperado |
|----|-----------|-------|-------------------|
| A01 | Alerta al crear excediendo | 1. Existe lote CCG=500, inicial=450<br>2. Crear lote con cantidad=100 | Alerta amarilla: "Se excede el contrato global" |
| A02 | Sin alerta dentro de límite | 1. Existe lote CCG=500, inicial=200<br>2. Crear lote con cantidad=100 | Sin alerta (total 300 < 500) |
| A03 | Alerta en ajustar stock | 1. Lote CCG=500, inicial=400<br>2. Ajustar stock entrada +150 | Alerta en respuesta |
| A04 | Sin alerta en salidas | 1. Lote CCG=500, inicial=400<br>2. Registrar salida de 100 | Sin alerta de contrato |

### 1.3 Renderización de Tablas

| ID | Escenario | Pasos | Resultado Esperado |
|----|-----------|-------|-------------------|
| R01 | Columnas de contrato | 1. Ir a vista de Lotes | Columnas visibles: CCG, Pendiente Global |
| R02 | Formato numérico | 1. Ver lote con CCG=1000, pendiente=250 | Números formateados correctamente |
| R03 | Color de pendiente | 1. Ver lote con pendiente=0 | Indicador verde/completado |
| R04 | Color de excedido | 1. Ver lote donde total > CCG | Indicador rojo/excedido |

---

## 2. Flujos Completos de Usuario

### 2.1 Flujo: Registro de Entrada de Mercancía

```
DADO un contrato global de 500 unidades
Y un lote existente con 200 unidades recibidas

CUANDO el usuario registra una entrada de 100 unidades

ENTONCES:
- cantidad_inicial del lote = 300
- cantidad_actual del lote = 300
- cantidad_pendiente_global = 200
- Si se excede el CCG, se muestra alerta
```

### 2.2 Flujo: Registro de Salida a Centro

```
DADO un lote con CCG=500, inicial=300, actual=300

CUANDO el usuario registra una salida de 100 unidades

ENTONCES:
- cantidad_inicial del lote = 300 (SIN CAMBIO)
- cantidad_actual del lote = 200
- cantidad_pendiente_global = 200 (SIN CAMBIO)
- NO se muestra alerta de contrato
```

### 2.3 Flujo: Creación de Nuevo Lote

```
DADO un producto con contrato existente:
- Lote A: CCG=500, inicial=200
- Lote B: CCG=500, inicial=150
- Total actual: 350, Pendiente: 150

CUANDO el usuario crea Lote C con inicial=200

ENTONCES:
- Lote C hereda CCG=500 automáticamente
- Total nuevo: 550 (excede CCG)
- Se muestra alerta NO bloqueante
- El lote se crea normalmente
```

### 2.4 Flujo: Edición de Lote

```
DADO un lote con CCG=500, inicial=200

CUANDO el usuario edita cantidad_inicial a 600

ENTONCES:
- Se muestra alerta de que excede CCG
- La edición se permite (no bloqueante)
- Pendiente global = 0 (max de 500-600=0)
```

---

## 3. Casos de Sincronización

### 3.1 Actualización en Tiempo Real

| ID | Escenario | Verificación |
|----|-----------|-------------|
| S01 | Después de ajustar stock | Datos en tabla se actualizan inmediatamente |
| S02 | Después de crear lote | Nuevo lote aparece en lista sin refresh |
| S03 | Después de importar Excel | Lotes importados visibles con CCG correcto |
| S04 | Alertas en respuesta API | Toast/alerta visible al usuario |

### 3.2 Consistencia Cross-Component

| ID | Escenario | Verificación |
|----|-----------|-------------|
| C01 | Dashboard vs Detalle | Totales en dashboard = suma de detalles |
| C02 | Lista vs Form de edición | Datos al abrir form = datos en lista |
| C03 | Reportes vs Inventario | Cantidades en reportes = datos actuales |

---

## 4. Testing de Formularios

### 4.1 Formulario de Lote

| Campo | Validación | Mensaje de Error Esperado |
|-------|-----------|---------------------------|
| cantidad_contrato_global | Opcional, numérico ≥ 0 | "Debe ser un número positivo" |
| cantidad_inicial | Requerido, numérico > 0 | "Cantidad requerida" |
| numero_contrato | Opcional, string | - |

### 4.2 Importador Excel

| Escenario | Verificación |
|-----------|-------------|
| CCG en plantilla | Columna `cantidad_contrato_global` acepta valores |
| Sin CCG | Se hereda de lotes existentes |
| CCG excedido | Alerta de advertencia pre-importación |

---

## 5. Comandos de Verificación Manual

### 5.1 Verificar Backend

```bash
cd backend
python manage.py shell
```

```python
from core.models import Lote
from core.serializers import LoteSerializer

# Verificar lote específico
lote = Lote.objects.get(numero_lote='XXX')
s = LoteSerializer(lote)
print(f"CCG: {s.data['cantidad_contrato_global']}")
print(f"Pendiente: {s.data['cantidad_pendiente_global']}")

# Verificar suma por contrato
from django.db.models import Sum
Lote.objects.filter(
    numero_contrato='CONTRATO-001',
    producto__clave='MED-001'
).aggregate(Sum('cantidad_inicial'))
```

### 5.2 Verificar API

```bash
# GET lote con campos de contrato
curl -H "Authorization: Bearer TOKEN" http://localhost:8000/api/lotes/1/

# POST ajustar stock entrada
curl -X POST -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tipo": "entrada", "cantidad": 100}' \
  http://localhost:8000/api/lotes/1/ajustar_stock/
```

---

## 6. Checklist de Verificación

### Frontend - Lotes.jsx

- [ ] Campo `cantidad_contrato_global` editable en formulario
- [ ] Campo `cantidad_pendiente_global` mostrado (solo lectura)
- [ ] Alerta visible cuando API retorna `alerta_contrato_global`
- [ ] Tooltip explicativo en columna de pendiente global

### Frontend - Movimientos.jsx

- [ ] Tipo "entrada" incrementa cantidad_inicial
- [ ] Tipo "salida" NO afecta cantidad_inicial
- [ ] Alerta de CCG mostrada en movimientos de entrada

### Frontend - ImportadorModerno.jsx

- [ ] Columna CCG en plantilla descargable
- [ ] Validación previa muestra alertas de CCG excedido
- [ ] Confirmación del usuario antes de importar con alertas

---

## 7. Resultados de Pruebas Backend

**Fecha:** 2026-02-17  
**Total Tests:** 52  
**Pasados:** 52  
**Fallidos:** 0  

### Categorías Verificadas:

| Categoría | Tests | Estado |
|-----------|-------|--------|
| Modelo Lote | 4 | ✅ |
| Serializer | 10 | ✅ |
| API ViewSet | 5 | ✅ |
| Escenarios Integración | 5 | ✅ |
| Importer | 2 | ✅ |
| Edge Cases | 6 | ✅ |
| Integridad BD | 5 | ✅ |
| API Errores | 4 | ✅ |
| Reportes | 4 | ✅ |
| Flujos Usuario | 3 | ✅ |
| Concurrencia | 3 | ✅ |

---

## 8. SQL para Migración en Producción

```sql
-- Agregar campo si no existe
ALTER TABLE lotes ADD COLUMN IF NOT EXISTS cantidad_contrato_global INTEGER NULL;

-- Comentario descriptivo
COMMENT ON COLUMN lotes.cantidad_contrato_global IS 
    'Cantidad total contratada para toda la clave de producto en el centro. ISS-INV-003';

-- Índice para optimizar consultas de agregación
CREATE INDEX IF NOT EXISTS idx_lotes_contrato_producto 
ON lotes (numero_contrato, producto_id) 
WHERE activo = true;
```

---

## Aprobación

| Rol | Nombre | Fecha | Firma |
|-----|--------|-------|-------|
| QA Lead | | | |
| Dev Lead | | | |
| Product Owner | | | |
