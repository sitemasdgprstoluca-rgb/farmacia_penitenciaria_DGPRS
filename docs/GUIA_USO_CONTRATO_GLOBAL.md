# 📋 Guía de Uso: Sistema de Contrato Global (ISS-INV-003)

## 🎯 ¿Qué es el Contrato Global?

El **Contrato Global** es el total contratado para **TODA UNA CLAVE DE PRODUCTO** dentro de un mismo contrato.

### Ejemplo Real

Si firmas un contrato para adquirir **1000 unidades de Paracetamol 500mg** (clave 615):

- **Cantidad Contrato Global** = 1000
- Este total puede llegar en **múltiples lotes** con diferentes fechas de caducidad
- El sistema calcula automáticamente cuánto falta recibir del total contratado

---

## 📊 Diferencia entre los Campos

| Campo | Alcance | Ejemplo | ¿Se suma? |
|-------|---------|---------|-----------|
| **Cantidad Contrato (Lote)** | Solo este lote específico | 290 | ✅ SÍ |
| **Cantidad Contrato Global** | Toda la clave + contrato | 300 | ❌ NO |
| **Cantidad Inicial** | Lo que llegó en este lote | 290 | ✅ SÍ |

---

## ✅ Cómo Importar Correctamente desde Excel

### Estructura del Excel

Tu Excel debe tener **ESTAS COLUMNAS** (ejemplo con clave 615):

| Clave Producto | Nombre Producto | Número Lote | Fecha Recepción | Fecha Caducidad | Cantidad Inicial | **Número Contrato** | **Cantidad Contrato Global** |
|----------------|-----------------|-------------|-----------------|-----------------|------------------|---------------------|------------------------------|
| 615 | KETOCONAZOL | 2503022 | 2026-01-26 | 2027-10-01 | 290 | **CONT-2026-001** | **300** |
| 615 | KETOCONAZOL | 25103022 | 2025-11-13 | 2027-10-01 | 216 | **CONT-2026-001** | **300** |
| 615 | KETOCONAZOL | 2502062 | 2025-11-13 | 2027-07-01 | 84 | **CONT-2026-001** | **300** |

### ⚠️ IMPORTANTE

1. **El "Número Contrato" es OBLIGATORIO** para que el sistema pueda agrupar los lotes
2. **La "Cantidad Contrato Global" debe ser LA MISMA en todas las filas** del mismo producto + contrato
3. El sistema **NO suma** el Contrato Global, siempre toma el **valor más reciente**
   - ⚠️ Si pone 300 en una fila y 500 en otra, el sistema usará 500
   - Por eso es CRÍTICO usar el mismo valor en todas las filas

---

## 🎨 Visualización en la Interfaz

Después de importar, verás:

```
Producto: 615 - KETOCONAZOL/CLINDAMICINA
Lote: 2503022
Inventario: 
  84 de 290
  📋 CONT-2026-001
  🌐 Global: 300
  ⏳ Faltan: 0
```

### Interpretación

- **84** → Existencia actual después de movimientos
- **de 290** → Cantidad inicial recibida en este lote
- **📋 CONT-2026-001** → Número de contrato
- **🌐 Global: 300** → Total contratado para toda la clave 615
- **⏳ Faltan: 0** → Ya se recibieron las 300 unidades (290 + 216 + 84 = 590, hay exceso)

---

## 🔧 Cómo Editar el Contrato Global

### Desde la Interfaz Web (Solo Farmacia/Admin)

1. Click en **Editar** (botón azul de lápiz)
2. Busca la sección morada: **🌐 CANTIDAD CONTRATO GLOBAL**
3. Ingresa el total contratado (ej: 1000)
4. El sistema automáticamente propagará este valor a **TODOS** los lotes activos con el mismo producto + número de contrato

### ⚡ Propagación Automática

Si defines CCG = 1000 en un lote de Paracetamol con contrato "CONT-2026-001", el sistema:

1. Busca TODOS los lotes activos de Paracetamol
2. Que tengan el mismo número de contrato "CONT-2026-001"
3. Les asigna automáticamente CCG = 1000

---

## 📈 Cálculos del Sistema

### Cantidad Pendiente Global

```
Pendiente Global = Contrato Global - Σ(Cantidad Inicial de todos los lotes activos)
```

**Ejemplo:**

- Contrato Global: 1000
- Lote 1: Cantidad Inicial = 300
- Lote 2: Cantidad Inicial = 250
- Lote 3: Cantidad Inicial = 200

**Pendiente Global = 1000 - (300 + 250 + 200) = 250**

---

## 🚨 Alertas Automáticas

El sistema muestra alertas con código de colores:

- **Cantidad Pendiente Global > 0**: "⏳ Faltan X unidades" (naranja)
- **Cantidad Pendiente Global < 0**: "⚠️ Exceso: X unidades" (rojo - se recibió más de lo contratado)
- **Cantidad Pendiente Global = 0**: "✅ Completo" (verde)

---

## 🎯 Caso de Uso: Entregas Parciales

### Contrato Firmado
- **Producto:** Paracetamol 500mg (Clave 615)
- **Total Contratado:** 1000 unidades
- **Número de Contrato:** CONT-2026-PAR-001

### Entregas

| Fecha | Número Lote | Cantidad Recibida | Pendiente Global |
|-------|-------------|-------------------|------------------|
| 15-Feb-2026 | LOT-001 | 300 | 700 |
| 28-Feb-2026 | LOT-002 | 250 | 450 |
| 15-Mar-2026 | LOT-003 | 200 | 250 |
| 30-Mar-2026 | LOT-004 | 250 | **0** ✅ |

---

## ❌ Errores Comunes

### 1. No definir el Número de Contrato

**Problema:** Si no especificas el número de contrato, el sistema no puede agrupar los lotes.

**Solución:** Siempre llena la columna "Número Contrato" en el Excel.

### 2. Poner diferentes valores de CCG en el Excel

**Problema:**
```
615 | KETOCONAZOL | ... | CONT-2026-001 | 300
615 | KETOCONAZOL | ... | CONT-2026-001 | 500  ← DIFERENTE
```

**Solución:** El sistema toma el valor más reciente (500), pero es confuso. **Usa siempre el mismo valor**.

### 3. Confundir Cantidad Contrato (Lote) con Contrato Global

| ❌ Incorrecto | ✅ Correcto |
|--------------|------------|
| CCG = suma de los lotes | CCG = total del contrato firmado |
| CCG diferente en cada lote | CCG igual en todos los lotes del mismo contrato |

---

## 💡 Recomendaciones

1. **Define el CCG desde el primer lote** que recibas del contrato
2. **Usa números de contrato claros:** CONT-2026-001, CONT-2026-PAR-002, etc.
3. **Verifica en la interfaz** que el "Pendiente Global" coincida con lo esperado
4. **Si hay exceso,** revisa con el proveedor si hubo un error en el envío

---

## 🛠️ Mantenimiento Manual

Si necesitas corregir el CCG de todos los lotes de un contrato:

1. Edita cualquier lote del contrato
2. Modifica el valor en **🌐 CANTIDAD CONTRATO GLOBAL**
3. Guarda
4. El sistema propagará automáticamente a todos los lotes hermanos

---

## 📞 Soporte

Si tienes dudas sobre:
- Cómo interpretar los valores
- Por qué aparece "Sin contrato"
- Cómo corregir datos importados

Consulta este documento o contacta al equipo de desarrollo.

---

**Última actualización:** 17-Feb-2026
**Versión:** ISS-INV-003
