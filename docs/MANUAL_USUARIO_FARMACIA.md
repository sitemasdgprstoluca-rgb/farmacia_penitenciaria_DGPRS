# Manual de Usuario - Sistema de Gestión Farmacéutica (Perfil Farmacia)

Este manual proporciona una guía detallada y exhaustiva para el uso del Sistema de Inventario y Gestión Farmacéutica. Está diseñado específicamente para operarios y administradores con perfil **Farmacia**, cubriendo desde el acceso inicial hasta la generación de reportes avanzados y trazabilidad.

---

## ÍNDICE

1. [Acceso y Seguridad](#1-acceso-y-seguridad)
2. [Tablero Principal (Dashboard)](#2-tablero-principal-dashboard)
3. [Gestión de Inventario](#3-gestión-de-inventario)
   - Productos
   - Lotes y Caducidades (Semáforo)
   - Donaciones
4. [Gestión de Requisiciones](#4-gestión-de-requisiciones)
   - Ciclo de Vida
   - Proceso de Atención
   - Hoja de Consulta
5. [Movimientos y Trazabilidad](#5-movimientos-y-trazabilidad)
6. [Generación de Reportes](#6-generación-de-reportes)
7. [Solución de Problemas Frecuentes](#7-solución-de-problemas-frecuentes)

---

## 1. ACCESO Y SEGURIDAD

### 1.1 Iniciar Sesión (Login)
Para acceder al sistema, ingrese a la dirección web proporcionada por el administrador.
1. Ingrese su **Correo Electrónico**.
2. Ingrese su **Contraseña**.
3. Haga clic en el botón **"Ingresar"**.

> **Nota:** Si es su primera vez, asegúrese de tener las credenciales asignadas por el administrador del sistema.

### 1.2 Recuperación de Contraseña
Si ha olvidado su contraseña, el sistema cuenta con un mecanismo seguro de restauración vía correo electrónico.

1. En la pantalla de Login, haga clic en el enlace **"¿Olvidaste tu contraseña?"**.
2. Ingrese el correo electrónico asociado a su cuenta.
3. Haga clic en **"Enviar Instrucciones"**.
4. Recibirá un correo electrónico (vía *Resend*) con un enlace seguro.
5. Haga clic en el enlace del correo, el cual lo llevará a una pantalla para establecer su nueva contraseña.
6. Ingrese la nueva contraseña dos veces para confirmar.

---

## 2. TABLERO PRINCIPAL (DASHBOARD)

Al ingresar, visualizará el **Dashboard**, diseñado para brindar una vista rápida del estado operativo:

- **Métricas Clave:** Total de productos, alertas de stock bajo, requisiciones pendientes.
- **Semáforo de Caducidad:** Gráfica o conteo de lotes próximos a vencer.
- **Accesos Rápidos:** Botones para ir directamente a Requisiciones o Reportes.

---

## 3. GESTIÓN DE INVENTARIO

El módulo de inventario es el corazón del sistema. Aquí se controla el stock real.

### 3.1 Productos
En la sección **Productos**, encontrará el catálogo maestro.
- **Búsqueda:** Utilice la barra superior para buscar por nombre, código o principio activo.
- **Detalle:** Al hacer clic en un producto, verá su ficha técnica, stock total y distribución por lotes.

### 3.2 Lotes y Caducidades (El Semáforo)
La gestión de lotes es crítica para evitar pérdidas por caducidad.
- **Rojo (Crítico):** Lotes caducados o por caducar en menos de 3 meses. Prioridad absoluta de salida.
- **Amarillo (Alerta):** Lotes que caducan entre 3 y 6 meses.
- **Verde (Óptimo):** Lotes con fecha de caducidad superior a 6 meses.

**Acciones recomendadas:**
- Revise periódicamente la pestaña **Lotes**.
- Al surtir una requisición, el sistema (o el operario) debe priorizar los lotes más antiguos (*PEPS: Primeras Entradas, Primeras Salidas* o *PCPS: Primeros en Caducar, Primeros en Salir*).

### 3.3 Donaciones
Registro de entradas extraordinarias de medicamentos.
- Permite ingresar stock etiquetado como "Donación" para efectos de trazabilidad y auditoría separada si es necesario.

---

## 4. GESTIÓN DE REQUISICIONES

Las requisiciones son las solicitudes de medicamentos que realizan los Centros (o áreas solicitantes) a la Farmacia Central. Este es el flujo de trabajo diario principal.

### 4.1 Ciclo de Vida de una Requisición
Una solicitud pasa por los siguientes estados:

1. **Pendiente:** El Centro la ha creado pero Farmacia aún no la revisa.
2. **Aprobada/En Proceso:** Farmacia ha aceptado la solicitud y está preparando los insumos.
3. **Rechazada:** La solicitud no procede (falta de stock, error en solicitud, etc.).
4. **Surtida:** Los medicamentos han sido separados del inventario de Farmacia y empaquetados.
5. **Entregada:** El Centro confirma la recepción física de los bienes.
6. **Cancelada:** Anulada antes de ser procesada.

### 4.2 Proceso de Atención (Paso a Paso)

1. **Revisión:** Vaya al módulo **Requisiciones**. Verá una lista con las solicitudes "Pendientes".
2. **Análisis:** Abra el detalle de la requisición. Verifique:
   - Centro Solicitante.
   - Lista de productos y cantidades pedidas.
   - Observaciones del solicitante.
3. **Aprobación/Ajuste:**
   - Puede aprobar la cantidad total.
   - Si no hay stock suficiente, puede aprobar una **cantidad parcial**.
4. **Autorización:** Al cambiar el estado a **Aprobada/Surtida**, el sistema descontará las existencias de su inventario.
   - *Importante:* Verifique que los Lotes descontados coincidan con el físico que está entregando.

### 4.3 Hoja de Consulta
Dentro del detalle de la requisición, encontrará el botón para generar la **Hoja de Consulta (PDF)**.
- Este documento sirve como "Picking List" o comprobante de entrega.
- Contiene: ID de la requisición, Fecha, Centro Solicitante, y la lista clara de ítems a entregar.
- **Impresión:** Imprima este documento para que el receptor lo firme al momento de la entrega física.

---

## 5. MOVIMIENTOS Y TRAZABILIDAD

### 5.1 Movimientos
Historial bruto de todas las transacciones de entrada y salida.
- **Entradas:** Compras, donaciones, ajustes positivos. (Columna Origen muestra de dónde vino).
- **Salidas:** Surtido de requisiciones, ajustes negativos, mermas. (Columna Destino muestra a quién se entregó).

### 5.2 Trazabilidad
Permite rastrear la historia de un producto o lote específico.
- ¿Quién registró el movimiento?
- ¿Cuándo ocurrió exactamente?
- ¿A qué requisición pertenece?

---

## 6. GENERACIÓN DE REPORTES

El sistema permite exportar información para auditorías y control administrativo.

### Filtros Disponibles
- **Rango de Fechas:** Defina "Desde" y "Hasta".
- **Centro:** Filtre reportes para un centro específico (ej. "Enfermería Hombre", "Maternidad") o seleccione "Todos" (o "Central") para ver el global.

### Tipos de Reportes
1. **Reporte de Inventario Actual:** Snapshot de lo que hay hoy.
2. **Reporte de Movimientos:** Detalle de entradas y salidas en el periodo seleccionado.
3. **Kardex:** Movimientos detallados por producto.

### Formatos de Exportación
- **PDF:** Ideal para impresión, firmas y archivo físico. Formato oficial no editable.
- **Excel (.xlsx):** Ideal para análisis de datos, tablas dinámicas y cálculos externos.

> **Tip:** Si genera un reporte muy grande (ej. Movimientos de todo el año), prefiera la versión Excel para facilitar la lectura.

---

## 7. SOLUCIÓN DE PROBLEMAS FRECUENTES

| Problema | Causa Probable | Solución |
| :--- | :--- | :--- |
| **Error 500 al generar reporte** | Seleccionó un filtro inválido o muy amplio. | Intente reducir el rango de fechas. Si persiste, contacte a soporte (el error de "Central" como texto ya fue corregido). |
| **Texto cortado en PDF** | Nombres de centros muy largos. | El sistema ajusta automáticamente el texto (word-wrap). Si aún se corta, verifique la vista previa antes de imprimir. |
| **No llega el correo de contraseña** | Filtros de Spam o configuración de API. | Revise su carpeta de Spam/No deseados. El remitente es seguro (*Resend*). |
| **Stock no cuadra con físico** | Movimiento no registrado o error humano. | Realice una auditoría de Lotes y ajuste el inventario mediante una "Entrada/Salida por Ajuste". |

---
*Documento generado para la versión actual del sistema (Enero 2026).*
