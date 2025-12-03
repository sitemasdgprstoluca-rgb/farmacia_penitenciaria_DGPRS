# Análisis de Infraestructura y Propuesta de Mejora

## 1. Diagnóstico Actual

El sistema opera actualmente bajo una arquitectura "Serverless/Stateless" en capas gratuitas, lo que conlleva limitaciones técnicas específicas que afectan la funcionalidad crítica (como la persistencia de archivos PDF).

### Stack Tecnológico Actual
*   **Backend:** Django (Python) alojado en **Render (Free Tier)**.
*   **Base de Datos:** PostgreSQL alojado en **Supabase (Free Tier)**.
*   **Frontend:** React alojado en Render/Vercel (Static Site).
*   **Almacenamiento de Archivos (Media):** Sistema de archivos local del contenedor (Efímero).

### El Problema de los Archivos PDF
Actualmente, el sistema intenta guardar los archivos PDF generados (reportes, comprobantes) en la carpeta `/media` dentro del servidor en Render.
*   **Causa:** Los servicios gratuitos de Render tienen un **sistema de archivos efímero**. Esto significa que cada vez que el servidor se reinicia (por inactividad o despliegue), todos los archivos creados dinámicamente se borran.
*   **Consecuencia:** Los usuarios pueden generar un PDF y verlo en el momento, pero si intentan acceder a él horas después, el archivo habrá desaparecido (Error 404).

---

## 2. Alcance: ¿Qué se puede y qué no se puede hacer hoy?

| Característica | Estado Actual (Free Tier) | Explicación |
| :--- | :--- | :--- |
| **Base de Datos** | ✅ Funcional | Supabase Free ofrece 500MB. Suficiente para miles de registros de texto. |
| **Persistencia de Archivos (PDFs/Imágenes)** | ❌ **No Funcional** | Los archivos se borran al reiniciarse el servidor. Render no ofrece disco persistente gratis. |
| **Disponibilidad 24/7** | ⚠️ Limitada | Render "duerme" el servidor tras 15 min de inactividad. El primer acceso tarda ~50 segundos en cargar. |
| **Backups** | ⚠️ Manuales | Supabase Free tiene backups diarios pero solo retiene 1 día. No hay Point-in-Time Recovery. |
| **Rendimiento** | ⚠️ Variable | CPU y RAM compartida. Puede haber lentitud en reportes pesados. |
| **Límites de Uso** | ⚠️ Estrictos | Render Free tiene límite de 750 horas/mes. Supabase tiene límite de ancho de banda (egress). |

---

## 3. Soluciones y Propuesta de Costos

Para solucionar el problema de los archivos y mejorar la estabilidad, existen tres caminos:

### Opción A: Arreglo Técnico (Mantener Costo $0)
*Configurar almacenamiento en la nube usando la capa gratuita de Supabase Storage.*
*   **Acción:** Modificar el código de Django para usar `django-storages` conectado a un "Bucket" de Supabase (S3 compatible).
*   **Ventaja:** Los archivos se guardan en Supabase (1GB gratis) y no se borran.
*   **Desventaja:** El servidor de Render seguirá "durmiéndose" (lentitud al inicio).
*   **Costo:** **$0 USD / mes**.

### Opción B: Estabilidad Básica (Recomendado - Bajo Costo)
*Pagar solo por el servidor de aplicaciones para evitar que se duerma.*
*   **Render:** Plan "Starter" ($7 USD/mes).
    *   Evita que el servidor se duerma.
    *   Respuesta rápida siempre.
*   **Supabase:** Mantener Free Tier (hasta llegar a 500MB de datos).
*   **Almacenamiento:** Usar Supabase Storage (1GB gratis).
*   **Costo:** **$7 USD / mes**.

### Opción C: Entorno Profesional (Escalabilidad)
*Para cuando el sistema sea crítico y tenga alto tráfico.*
*   **Render:** Plan "Team/Pro" (desde $19 USD/mes) para mayor RAM/CPU.
*   **Supabase:** Plan "Pro" ($25 USD/mes).
    *   8GB de base de datos.
    *   Backups de 7 días.
    *   100GB de almacenamiento de archivos.
*   **Costo:** **~$44 USD / mes**.

---

## 4. Tabla Comparativa de Costos

| Concepto | Actual (Free) | Opción B (Starter) | Opción C (Pro) |
| :--- | :--- | :--- | :--- |
| **Hosting Backend** | $0 (Render Free) | $7 (Render Starter) | $19+ (Render Team) |
| **Base de Datos** | $0 (Supabase Free) | $0 (Supabase Free) | $25 (Supabase Pro) |
| **Almacenamiento Archivos** | $0 (Roto actualmente) | $0 (Supabase 1GB) | Incluido en Pro (100GB) |
| **Dominio (Opcional)** | $0 (onrender.com) | $10-$15 / año | $10-$15 / año |
| **Total Mensual Estimado** | **$0 USD** | **$7 USD** | **~$44 USD** |
| **Total Anual Estimado** | **$0 USD** | **$84 USD** | **~$528 USD** |

## 5. Recomendación Inmediata

1.  **Prioridad 1 (Crítica):** Implementar la conexión con **Supabase Storage** (u otro servicio S3) en el código. Esto es necesario independientemente de si se paga o no, ya que Render (incluso pagado) no garantiza persistencia de disco local en su arquitectura moderna.
    *   *Esto solucionará el problema de "no se pueden guardar archivos PDF".*
2.  **Prioridad 2 (Mejora UX):** Si el presupuesto lo permite, contratar el plan **Starter de Render ($7/mes)** para eliminar los tiempos de espera iniciales y mejorar la experiencia del usuario.

---
*Generado por GitHub Copilot - 02/12/2025*

---

# 📋 APÉNDICE: Hallazgos de Revisión de Código

## 🔴 Errores Críticos Corregidos

### 1. Error en botón "Eliminar" de `Centros.jsx`
```jsx
// ❌ ANTES (Error)
onClick={() => handleDelete(centro.id)}

// ✅ DESPUÉS (Corregido)
onClick={() => handleDelete(centro)}
```
**Problema:** Se pasaba solo `centro.id` pero `handleDelete` espera el objeto completo para mostrar el nombre en la confirmación.
**Estado:** ✅ CORREGIDO

### 2. Número de fila incorrecto con paginación en `Centros.jsx`
```jsx
// ❌ ANTES
{index + 1}

// ✅ DESPUÉS
{(currentPage - 1) * PAGE_SIZE + index + 1}
```
**Problema:** El índice no consideraba la paginación, mostrando 1-10 en todas las páginas.
**Estado:** ✅ CORREGIDO

### 3. Estado de loading incorrecto en modal de importación
```jsx
// ❌ ANTES
disabled={loading}

// ✅ DESPUÉS
disabled={importLoading}
```
**Problema:** Usaba el estado `loading` genérico en lugar de `importLoading` específico.
**Estado:** ✅ CORREGIDO

---

## 🟠 Problemas de Seguridad Corregidos

### 4. Ventana de vulnerabilidad en filtro de centro (`Movimientos.jsx`)
**Problema:** Un usuario de centro podía ver movimientos de todos los centros brevemente durante la hidratación inicial del usuario.

**Solución implementada:** Se agregó el flag `centroResuelto` que previene la carga de datos hasta que el centro del usuario esté correctamente sincronizado en los filtros.

```jsx
// ✅ Nuevo: Solo cargar cuando el centro está resuelto
const [centroResuelto, setCentroResuelto] = useState(puedeVerTodosCentros || !!centroInicial);

useEffect(() => {
  if (centroResuelto) {
    cargarMovimientos();
  }
}, [cargarMovimientos, centroResuelto]);
```
**Estado:** ✅ CORREGIDO

---

## 🟢 Buenas Prácticas Identificadas

| Característica | Estado | Descripción |
| :--- | :--- | :--- |
| Manejo de Tokens | ✅ | Access token en memoria, refresh en cookie HttpOnly |
| Sistema de Permisos | ✅ | Jerarquía clara: ADMIN > FARMACIA > CENTRO > VISTA |
| Auditoría | ✅ | Logs de acciones con usuario, IP y cambios |
| Rate Limiting | ✅ | Throttling en login y cambio de password |
| Validación Backend | ✅ | Permisos verificados en backend, no solo frontend |

---

## 📊 Resumen de Hallazgos

| Severidad | Cantidad | Estado |
| :--- | :--- | :--- |
| 🔴 Crítico | 1 | ✅ Corregido |
| 🟠 Alto | 1 | ✅ Corregido |
| 🟡 Medio | 2 | ✅ Corregido |

---

*Revisión de código completada - 02/12/2025*
