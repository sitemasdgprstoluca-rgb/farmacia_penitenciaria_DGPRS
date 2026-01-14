# Análisis de Formatos Oficiales de Farmacia Penitenciaria

## Resumen de Formatos

Los formatos oficiales del sistema penitenciario se dividen en dos contextos:
- **CIA** = Centro de Información y Abastecimiento (Farmacia Central/Almacén Central)
- **CPRS** = Centros Penitenciarios y de Reinserción Social (Centros destino)

---

## 1. Requisición de Medicamento (Formato J)

### Descripción
Formato que utilizan los **CPRS** para solicitar medicamentos al **CIA**.

### Campos del Formato Oficial
| Campo | Descripción |
|-------|-------------|
| Centro Penitenciario | Nombre del centro que solicita |
| Fecha | Fecha de elaboración |
| Periodo correspondiente | Periodo para el cual se solicita |
| **Clave** | Clave del medicamento/material |
| **Medicamento/Material** | Nombre del producto |
| **Presentación** | Forma farmacéutica |
| **Existencia** | Stock actual en el centro |
| **Cantidad Solicitada** | Lo que el centro necesita |
| **Cantidad Aprobada** | Lo que CIA autoriza |

### ✅ Adaptación en el Sistema

El sistema implementa el **Módulo de Requisiciones** que cubre este formato:

```
Sistema                          →  Formato Oficial
─────────────────────────────────────────────────────
Requisicion.centro               →  Centro Penitenciario
Requisicion.fecha_creacion       →  Fecha
Requisicion.periodo              →  Periodo correspondiente
DetalleRequisicion.producto.clave →  Clave
DetalleRequisicion.producto.nombre →  Medicamento/Material
DetalleRequisicion.producto.presentacion → Presentación
DetalleRequisicion.cantidad_solicitada →  Cantidad Solicitada
DetalleRequisicion.cantidad_aprobada →  Cantidad Aprobada
Lote.cantidad_actual (del centro) →  Existencia
```

**Funcionalidades:**
- Los centros crean requisiciones seleccionando productos
- El sistema calcula automáticamente la existencia actual
- El CIA aprueba/modifica las cantidades
- Se genera el surtido creando lotes en el centro destino

---

## 2. Control Mensual de Almacén (Formato A)

### Descripción
Registro mensual consolidado de todos los insumos médicos, mostrando existencias, entradas, salidas y saldo final.

### Campos del Formato Oficial
| # | Campo | Descripción |
|---|-------|-------------|
| 1 | Institución Penitenciaria | CIA o nombre del CPRS |
| 2 | Fecha de Elaboración | Cuándo se elaboró el reporte |
| 3 | Periodo | Mes/año correspondiente |
| 4 | **Clave (insumo)** | Identificador del producto |
| 5 | **Insumo médico** | Nombre del medicamento |
| 6 | **Presentación** | Forma farmacéutica |
| 7 | **Fecha de Caducidad** | Vencimiento del lote |
| 8 | **Existencias Anteriores** | Stock al inicio del periodo |
| 9 | **Documento de Entrada (Folio)** | Referencia del documento de entrada |
| 10 | **Entrada** | Cantidad ingresada |
| 11 | **Salida** | Cantidad despachada |
| 12 | **Existencia** | Saldo final |

### ✅ Adaptación en el Sistema

El sistema puede generar este reporte desde **Reportes → Inventario**:

```
Sistema                          →  Formato Oficial
─────────────────────────────────────────────────────
Centro.nombre / "Almacén Central" →  Institución Penitenciaria
Fecha actual                     →  Fecha de Elaboración
Filtro de fechas del reporte     →  Periodo
Producto.clave                   →  Clave (insumo)
Producto.nombre                  →  Insumo médico
Producto.presentacion            →  Presentación
Lote.fecha_caducidad             →  Fecha de Caducidad
Lote.cantidad_inicial            →  Existencias Anteriores
Movimientos tipo ENTRADA         →  Entrada
Movimientos tipo SALIDA          →  Salida
Lote.cantidad_actual             →  Existencia
Requisicion.folio / Movimiento.id →  Documento de Entrada (Folio)
```

**Nota:** El folio del documento de entrada se mapea a:
- Para entradas por requisición: `folio` de la requisición
- Para entradas por donación: `observaciones` del movimiento
- Para entradas directas: ID del movimiento

### 🔧 Mejora Sugerida
Agregar campo `folio_documento` en el modelo `Movimiento` para almacenar explícitamente el número de documento de entrada.

---

## 3. Tarjeta de Entradas y Salidas (Formato B)

### Descripción
Kardex individual por producto/lote que registra cada movimiento con detalle. **Es el historial detallado de un lote específico.**

### Campos del Formato Oficial
| # | Campo | Descripción |
|---|-------|-------------|
| 1 | Institución Penitenciaria | CIA o CPRS |
| 2 | **Insumo médico** | Nombre del medicamento |
| 3 | **Clave** | Identificador del producto |
| 4 | **Presentación** | Forma farmacéutica |
| 5 | **Fecha de caducidad** | Vencimiento |
| 6 | **Fecha** | Fecha del movimiento |
| 7 | **Documento de entrada** | Folio/referencia |
| 8 | **Entrada (Cajas/Piezas)** | Cantidad ingresada |
| 9 | **Salida (Cajas)** | Cantidad salida |
| 10 | **Existencias (Cajas/Piezas)** | Saldo acumulado |
| 11 | **Nombre y firma del personal** | Responsable |

### ✅ Adaptación en el Sistema

**Módulo de Trazabilidad** implementa exactamente este formato:

```
Sistema                          →  Formato Oficial
─────────────────────────────────────────────────────
Centro.nombre / "Almacén Central" →  Institución Penitenciaria
Lote.producto.nombre             →  Insumo médico
Lote.producto.clave              →  Clave
Lote.producto.presentacion       →  Presentación
Lote.fecha_caducidad             →  Fecha de caducidad
Movimiento.fecha                 →  Fecha
Movimiento.observaciones         →  Documento de entrada (parcial)
Movimiento.cantidad (si entrada) →  Entrada
Movimiento.cantidad (si salida)  →  Salida
Saldo calculado                  →  Existencias
Usuario.nombre                   →  Nombre del personal
```

**Vista actual del sistema:**
- `Trazabilidad → Buscar producto → Ver lote` muestra:
  - Información del lote (producto, clave, presentación, caducidad)
  - Tabla de movimientos con fecha, tipo, cantidad, observaciones
  - Cálculo de saldo actualizado

### 🔧 Mejora Sugerida
- Agregar campo `numero_documento` o `folio` en movimientos
- La firma se maneja actualmente con el campo `usuario` del movimiento
- Considerar agregar opción de exportar como PDF con formato oficial

---

## 4. Tarjeta para la Distribución de Insumos Médicos (Formato C)

### Descripción
Registro de **dispensación a pacientes/internos**. Es específico para tracking de medicamentos controlados y tratamientos.

### Campos del Formato Oficial
| # | Campo | Descripción |
|---|-------|-------------|
| 1 | Institución Penitenciaria | CPRS donde se dispensa |
| 2 | **Insumo médico** | Medicamento |
| 3 | **Clave** | Identificador |
| 4 | **Presentación** | Forma farmacéutica |
| 5 | **Fecha de caducidad** | Vencimiento |
| 6 | **Fecha** | Fecha de dispensación |
| 7 | **Documento de entrada (folio)** | Referencia de entrada |
| 8 | **Entrada (Caja/pieza)** | Cantidad recibida |
| 9 | **Salida (Pieza)** | Cantidad dispensada |
| 10 | **Existencias (Pieza/caja)** | Saldo |
| 11 | **A. y/o AJ** | Tipo: Adolescente y/o Adulto Joven |
| 12 | **S.P.** | Servidor Público (si aplica) |
| 13 | **Nombre de la persona** | Paciente que recibe |
| 14 | **Firma (1ª, 2ª, 3ª Dosis)** | Firma por cada dosis |
| 15 | **Nombre y firma del personal** | Personal médico responsable |

### ⚠️ Adaptación Parcial en el Sistema

El sistema maneja dispensación a través de:
- **Movimientos tipo "Salida"** con subtipo "Médico"
- Campo `observaciones` donde se puede anotar el paciente

**Mapeo actual:**
```
Sistema                          →  Formato Oficial
─────────────────────────────────────────────────────
Centro.nombre                    →  Institución Penitenciaria
Producto.nombre                  →  Insumo médico
Producto.clave                   →  Clave
Producto.presentacion            →  Presentación
Lote.fecha_caducidad             →  Fecha de caducidad
Movimiento.fecha                 →  Fecha
Movimiento.cantidad              →  Salida
Lote.cantidad_actual             →  Existencias
Movimiento.observaciones         →  Nombre de la persona (parcial)
Movimiento.usuario               →  Personal médico
```

### 🔧 Mejoras Necesarias para Cumplimiento Total

Para implementar completamente el Formato C, se necesitaría:

1. **Modelo de Paciente/Interno** (opcional):
   ```python
   class Paciente(models.Model):
       nombre = models.CharField(max_length=200)
       tipo = models.CharField(choices=[('A', 'Adolescente'), ('AJ', 'Adulto Joven'), ('SP', 'Servidor Público')])
       centro = models.ForeignKey(Centro, on_delete=models.CASCADE)
   ```

2. **Modelo de Dispensación** (opcional):
   ```python
   class Dispensacion(models.Model):
       lote = models.ForeignKey(Lote, on_delete=models.CASCADE)
       paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE)
       fecha = models.DateField()
       cantidad = models.IntegerField()
       dosis_numero = models.IntegerField()  # 1, 2, 3
       firma_recibido = models.BooleanField(default=False)
       personal_medico = models.ForeignKey(User, on_delete=models.CASCADE)
   ```

**Alternativa Actual:** Usar el campo `observaciones` del movimiento para registrar:
- Nombre del paciente
- Tipo (A/AJ/SP)
- Número de dosis

Ejemplo: `"Juan Pérez (AJ) - 1ª Dosis"`

---

## 5. Recibo de Salida del Almacén

### Descripción
Documento que acompaña el envío físico de medicamentos del CIA a un CPRS.

### Campos del Formato (del Excel ejemplo)
| Campo | Descripción |
|-------|-------------|
| Folio | Número de documento |
| Fecha de Elaboración | Fecha del envío |
| C.P.R.S. | Centro destino |
| No. Prog. | Número progresivo de línea |
| Clave | Identificador del producto |
| Medicamento/Material/Descripción | Nombre del producto |
| Cantidad Surtida | Piezas enviadas |

### ✅ Adaptación en el Sistema

Se genera desde el **Módulo de Requisiciones** cuando se surte:

```
Sistema                          →  Formato Oficial
─────────────────────────────────────────────────────
Requisicion.folio                →  Folio
Requisicion.fecha_surtido        →  Fecha de Elaboración
Requisicion.centro.nombre        →  C.P.R.S.
DetalleRequisicion (índice)      →  No. Prog.
DetalleRequisicion.producto.clave →  Clave
DetalleRequisicion.producto.nombre →  Medicamento/Material
DetalleRequisicion.cantidad_surtida →  Cantidad Surtida
```

### 🔧 Mejora Sugerida
Implementar generación automática de PDF/Excel con formato de "Recibo de Salida" cuando se surte una requisición.

---

## Resumen de Cobertura

| Formato | Adaptación | Notas |
|---------|------------|-------|
| 1. Requisición (J) | ✅ **Completo** | Módulo de Requisiciones |
| 2. Control Mensual (A) | ✅ **90%** | Falta campo folio_documento explícito |
| 3. Tarjeta Entradas/Salidas (B) | ✅ **95%** | Trazabilidad - Falta exportación formal |
| 4. Distribución Insumos (C) | ⚠️ **60%** | Falta tracking de pacientes y dosis |
| 5. Recibo de Salida | ✅ **85%** | Falta generación de documento formal |

---

## Recomendaciones de Mejora

### Prioridad Alta
1. **Agregar campo `folio_documento`** en modelo `Movimiento` para registrar referencias oficiales
2. **Exportación PDF** del reporte de Trazabilidad con formato oficial (B)

### Prioridad Media
3. **Exportación PDF** del Recibo de Salida al surtir requisición
4. **Reporte Control Mensual (A)** exportable con formato oficial

### Prioridad Baja (Futuro)
5. **Módulo de Dispensación a Pacientes** para cumplir Formato C
6. **Catálogo de Pacientes/Internos** si se requiere tracking individual

---

## Conclusión

El sistema cubre **~85%** de los requerimientos de los formatos oficiales. Las funcionalidades principales (requisiciones, inventario, trazabilidad) están implementadas y mapean correctamente a los campos oficiales.

Las mejoras sugeridas son principalmente de **exportación/presentación** para generar documentos con el formato exacto requerido por las autoridades penitenciarias.
