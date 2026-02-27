# Guión Detallado — Nivel: Centros

Objetivo general
- Enseñar a usuarios de Centros (personal que solicita insumos y recibe lotes) a usar el sistema para: solicitar insumos, consultar stock, recibir lotes y validar trazabilidad.
- Público objetivo: personal operativo en centros penitenciarios con conocimientos básicos de computación.
- Formato: serie de 4 micro-videos (3–5 min cada uno) + 1 video resumen (7–9 min).

Resumen de videos (orden recomendado)
1. Introducción y navegación básica (Video 1) — 3:00
2. Solicitar insumos y seguimiento (Video 2) — 4:00
3. Recepción de lotes y validación (Video 3) — 4:30
4. Consulta de stock y trazabilidad rápida (Video 4) — 3:30
5. Video resumen / Escenario completo (Video 5) — 7:00

Notas generales de estilo
- Resolución: 1920×1080, 30fps
- Recorder: mostrar cursor resaltado y clicks con efecto visual
- Usar voz en off clara y pausada (español neutro)
- Incluir subtítulos en español (y opcional en inglés)
- Mostrar callouts (marcadores en pantalla) para botones y campos importantes
- Mantener cada micro-video entre 3 y 5 minutos

Detallado por video

---
Video 1 — Introducción y navegación básica
- Objetivo: Familiarizar al usuario con la interfaz del Centro y menús principales.
- Duración estimada: 3:00
- Tomas / escenas:
  0:00–0:10 — Intro (pantalla con logo del sistema y título: "Uso básico — Centros")
    - Shot: full-screen title card (5s), música breve.
  0:10–0:30 — Acceso y navegación general
    - Shot: Mostrar login (si ya logueado, saltar a dashboard) y barra lateral.
    - Callout: destacar menú "Inventario" y "Solicitudes".
  0:30–1:30 — Dashboard del Centro
    - Shot: recorrer widgets (stock crítico, alertas de caducidad)
    - Voiceover: explicar breves significados
  1:30–2:30 — Menú de inventario (búsqueda rápida)
    - Shot: buscar producto por nombre / código
    - Callout: mostrar filtros y columnas útiles
  2:30–3:00 — Conclusión y CTA (ver Video 2)
    - Shot: texto final y transición

Guion de voz (ejemplo breve):
- "Bienvenido al módulo de Centros. En este video veremos cómo navegar el dashboard y localizar productos rápidamente..."

Checks antes de grabar Video 1
- Cuenta de Centro creada y con permisos
- Datos de dashboard con al menos 5 productos y 1 alerta de caducidad
- Cursor highlight activo

---
Video 2 — Solicitar insumos y seguimiento
- Objetivo: Mostrar cómo crear una solicitud de insumos, asignar prioridad y seguir su estado.
- Duración estimada: 4:00
- Tomas / escenas:
  0:00–0:08 — Intro corto
  0:08–0:40 — Navegar a "Solicitudes" → "Crear nueva"
    - Shot: Formulario de solicitud
    - Callout: Campos obligatorios (producto, cantidad, motivo)
  0:40–1:40 — Añadir productos a la solicitud
    - Shot: búsqueda, seleccionar lote sugerido, agregar cantidad
    - Tip: mostrar validación de cantidad (no mayor a stock disponible o aviso)
  1:40–2:20 — Seleccionar prioridad y proveedor (si aplica)
  2:20–3:00 — Enviar solicitud y ver confirmación
    - Shot: notificación toast, número de solicitud
  3:00–4:00 — Seguimiento: buscar solicitud por ID y ver estados (creada, aprobada, enviada)
    - Shot: mostrar timelines/status badges

Guion de voz (extracto):
- "Para crear una solicitud haga clic en 'Crear nueva', busque el producto, agregue la cantidad y envíe la solicitud. Aparecerá un número de seguimiento..."

Checks antes de grabar Video 2
- Productos con stock suficiente
- Flujo de aprobación simulado (puede ser auto-aprobado en demo)
- Consola del backend lista si necesitas forzar estados

---
Video 3 — Recepción de lotes y validación
- Objetivo: Enseñar cómo registrar la llegada de un lote, validar código y caducidad, y actualizar inventario.
- Duración estimada: 4:30
- Tomas / escenas:
  0:00–0:08 — Intro
  0:08–0:40 — Ir a "Recepciones" → Nueva recepción
    - Shot: formulario de recepción
    - Callout: campos (número de entrega, proveedor, fecha)
  0:40–1:40 — Escanear/añadir lote (manual)
    - Shot: ingresar lote, fecha caducidad, cantidad
    - Tip: mostrar validación de formato de lote
  1:40–2:20 — Verificar y adjuntar documentación (opcional)
  2:20–3:20 — Aceptar recepción y actualizar inventario
    - Shot: mostrar cambio en stock en tiempo real
  3:20–4:30 — Validación de trazabilidad: buscar lote y revisar su historial
    - Shot: trazabilidad (entradas/salidas)

Checks antes de grabar Video 3
- Proveedor y recepción de prueba disponibles
- Datos de lote de ejemplo con diferentes caducidades

---
Video 4 — Consulta de stock y trazabilidad rápida
- Objetivo: Consultas rápidas: filtrar por caducidad, ver lotes con alerta y generar reporte rápido.
- Duración estimada: 3:30
- Tomas / escenas:
  0:00–0:06 — Intro
  0:06–1:00 — Filtros avanzados: caducidad, proveedor, estado
  1:00–1:40 — Exportar lista o generar PDF (si aplica)
  1:40–2:30 — Vista de lote y trazabilidad (historial)
  2:30–3:30 — Recomendaciones para manejo (rotación, ABC)

Checks antes de grabar Video 4
- Varios lotes con diferentes caducidades
- Función de export disponible o simular export

---
Video 5 — Resumen / Escenario completo
- Objetivo: Grabar un escenario que incluya solicitud → aprobación → envío → recepción → ver trazabilidad.
- Duración estimada: 7:00
- Tomas / escenas:
  0:00–0:10 — Intro resumen
  0:10–2:00 — Crear solicitud (resumen rápido)
  2:00–3:00 — Aprobar y marcar como enviada (puede simularse desde otra cuenta o forzar en backend)
  3:00–4:30 — Recepción y registro de lote
  4:30–6:00 — Ver trazabilidad y estado final en inventario
  6:00–7:00 — Conclusiones y mejores prácticas

Checks antes de grabar Video 5
- Todo el flujo probado en demo
- Tiempos de espera minimizados (usar respuestas mock si necesario)

---
Materiales en pantalla (para todos los videos)
- Lower-third con: Título del video + tiempo estimado
- Callouts: etiquetas resaltadas y cajas para campos importantes
- Cursor highlight y clicks visibles
- Short captions para acciones clave ("Haga clic aquí", "Ingrese cantidad")
- Thumbnail sugerido: captura del dashboard con título grande

Guion de voz: plantilla (ejemplo inicio)
- "Hola, soy [Nombre], y en este video veremos cómo ..." (luego explicar objetivos)
- Mantener tono profesional y claro.

Checklist técnico pre-grabación (script rápido)
1. Restaurar DB demo: `copy backend\\db.sqlite3.backup backend\\db.sqlite3`
2. Levantar backend: `python manage.py runserver`
3. Levantar frontend: `cd inventario-front && npm run dev`
4. Abrir navegador en incógnito
5. Verificar cuentas y datos de prueba
6. Ajustar resolución a 1920x1080
7. Desactivar notificaciones del sistema

Criterios de aceptación del video (QA)
- Flujo mostrado coincide con el comportamiento real
- No hay errores JS en consola durante la grabación
- Subtítulos generados y sincronizados
- Audio claro, sin ruido de fondo
- Video entre los tiempos estimados

---
Archivos generados por esta tarea:
- `docs/GUION_CENTROS.md` (este documento)

Siguiente acción sugerida:
- Revisas el guión y confirmas cambios o pides ajustes (p. ej. más detalle en pasos, incluir mensajes legales, o formato de voz en off).
