# Arquitectura del Sistema de Farmacia Penitenciaria

## Índice
1. [Visión General](#visión-general)
2. [Backend](#backend)
3. [Frontend](#frontend)
4. [Base de Datos](#base-de-datos)
5. [Flujos Críticos](#flujos-críticos)
6. [Generación de Reportes](#generación-de-reportes)
7. [Configuración y Personalización](#configuración-y-personalización)
8. [Seguridad y Autenticación](#seguridad-y-autenticación)

---

## Visión General

### Stack Tecnológico
- **Backend**: Django 5.2 + Django REST Framework
- **Frontend**: React 18 + Vite + TailwindCSS
- **Base de Datos**: PostgreSQL (producción) / SQLite (desarrollo)
- **Autenticación**: JWT con SimpleJWT (access token en memoria, refresh token en cookie HttpOnly)
- **Generación de PDFs**: ReportLab
- **Generación de Excel**: OpenPyXL
- **Despliegue**: Render (backend + frontend)

### Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              CLIENTE                                     │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    React SPA (Vite)                              │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │   │
│  │  │Dashboard │ │Productos │ │  Lotes   │ │Requisic. │  ...      │   │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘           │   │
│  │       └────────────┴────────────┴────────────┘                  │   │
│  │                           │                                      │   │
│  │              ┌────────────▼────────────┐                        │   │
│  │              │    API Client (Axios)   │                        │   │
│  │              │    + Token Manager      │                        │   │
│  │              └────────────┬────────────┘                        │   │
│  └───────────────────────────┼─────────────────────────────────────┘   │
└──────────────────────────────┼──────────────────────────────────────────┘
                               │ HTTPS
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           SERVIDOR (Render)                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Django REST Framework                         │   │
│  │                                                                  │   │
│  │  ┌─────────────────────────────────────────────────────────┐   │   │
│  │  │                   MIDDLEWARE                             │   │   │
│  │  │  - CORS  - CSRF  - Auth  - Audit  - WhiteNoise         │   │   │
│  │  └───────────────────────┬─────────────────────────────────┘   │   │
│  │                          │                                      │   │
│  │  ┌───────────────────────▼─────────────────────────────────┐   │   │
│  │  │                    ROUTER (urls.py)                      │   │   │
│  │  └───────────────────────┬─────────────────────────────────┘   │   │
│  │                          │                                      │   │
│  │  ┌───────────────────────▼─────────────────────────────────┐   │   │
│  │  │                     VIEWSETS                             │   │   │
│  │  │  - ProductoViewSet   - LoteViewSet                      │   │   │
│  │  │  - RequisicionViewSet - MovimientoViewSet               │   │   │
│  │  │  - CentroViewSet     - UsuarioViewSet                   │   │   │
│  │  │  - ReportesViewSet   - DashboardViewSet                 │   │   │
│  │  └───────────────────────┬─────────────────────────────────┘   │   │
│  │                          │                                      │   │
│  │  ┌───────────────────────▼─────────────────────────────────┐   │   │
│  │  │                    SERIALIZERS                           │   │   │
│  │  └───────────────────────┬─────────────────────────────────┘   │   │
│  │                          │                                      │   │
│  │  ┌───────────────────────▼─────────────────────────────────┐   │   │
│  │  │                      MODELS                              │   │   │
│  │  │  User, Centro, Producto, Lote, Requisicion, Movimiento  │   │   │
│  │  └───────────────────────┬─────────────────────────────────┘   │   │
│  │                          │                                      │   │
│  └──────────────────────────┼──────────────────────────────────────┘   │
│                             │                                          │
│  ┌──────────────────────────▼─────────────────────────────────────┐   │
│  │                      PostgreSQL                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Backend

### Estructura de Carpetas

```
backend/
├── config/                     # Configuración principal de Django
│   ├── settings.py            # Settings principales (DEBUG, DATABASES, etc.)
│   ├── urls.py                # URLs raíz del proyecto
│   ├── wsgi.py                # Punto de entrada WSGI
│   └── api_urls.py            # URLs de la API REST
│
├── core/                       # App principal con modelos y lógica de negocio
│   ├── models.py              # Modelos: User, Centro, Producto, Lote, Requisicion, etc.
│   ├── views.py               # Vistas generales (health check, config)
│   ├── serializers.py         # Serializadores DRF para los modelos
│   ├── serializers_jwt.py     # Serializadores personalizados para JWT
│   ├── permissions.py         # Clases de permisos personalizados
│   ├── constants.py           # Constantes del sistema (estados, roles, etc.)
│   ├── signals.py             # Señales Django para auditoría
│   ├── middleware.py          # Middleware de auditoría y seguridad
│   ├── admin.py               # Configuración del admin de Django
│   ├── utils/
│   │   ├── pdf_reports.py     # Generación de PDFs con ReportLab
│   │   ├── excel_utils.py     # Utilidades para Excel
│   │   └── stock_manager.py   # Lógica de gestión de inventarios
│   ├── migrations/            # Migraciones de base de datos
│   └── tests/                 # Tests unitarios y de integración
│
├── inventario/                 # App de inventario (ViewSets principales)
│   ├── views.py               # ViewSets: Producto, Lote, Movimiento, Requisicion, etc.
│   ├── urls.py                # URLs del router DRF
│   └── admin.py               # Admin de inventario
│
├── static/                     # Archivos estáticos
│   └── img/pdf/
│       └── fondoOficial.png   # Fondo institucional para PDFs
│
└── manage.py                   # Script de gestión Django
```

### Módulos Principales

#### 1. Autenticación (`core/serializers_jwt.py`)
- **CustomTokenObtainPairSerializer**: Login con JWT
- Almacena access token en memoria del cliente
- Refresh token en cookie HttpOnly (seguridad XSS)
- Endpoints:
  - `POST /api/token/` - Obtener tokens
  - `POST /api/token/refresh/` - Refrescar access token
  - `POST /api/logout/` - Cerrar sesión

#### 2. Usuarios (`inventario/views.py` - UsuarioViewSet)
- CRUD completo de usuarios
- Gestión de roles y permisos
- Campo `adscripcion` para centro/área de dependencia
- Endpoints:
  - `GET/POST /api/usuarios/`
  - `GET/PUT/DELETE /api/usuarios/{id}/`
  - `GET /api/usuarios/me/` - Perfil del usuario actual

#### 3. Centros (`inventario/views.py` - CentroViewSet)
- CRUD de centros penitenciarios
- Import/Export Excel
- Endpoints:
  - `GET/POST /api/centros/`
  - `GET/PUT/DELETE /api/centros/{id}/`
  - `GET /api/centros/exportar-excel/`
  - `POST /api/centros/importar_excel/`

#### 4. Productos (`inventario/views.py` - ProductoViewSet)
- Catálogo de medicamentos/productos
- Filtros por estado, unidad, stock
- Import/Export Excel
- Endpoints:
  - `GET/POST /api/productos/`
  - `GET/PUT/DELETE /api/productos/{id}/`
  - `GET /api/productos/exportar-excel/`
  - `POST /api/productos/importar-excel/`
  - `GET /api/productos/bajo-stock/`
  - `GET /api/productos/{id}/auditoria/`

#### 5. Lotes (`inventario/views.py` - LoteViewSet)
- Gestión de lotes con trazabilidad
- Documento PDF adjunto por lote
- Vinculación farmacia → centro
- Endpoints:
  - `GET/POST /api/lotes/`
  - `GET/PUT/DELETE /api/lotes/{id}/`
  - `GET /api/lotes/exportar-excel/`
  - `POST /api/lotes/importar-excel/`
  - `GET /api/lotes/por-caducar/`
  - `GET /api/lotes/vencidos/`
  - `POST /api/lotes/{id}/ajustar-stock/`

#### 6. Requisiciones (`inventario/views.py` - RequisicionViewSet)
- Flujo completo de requisiciones
- Máquina de estados: borrador → enviada → autorizada → surtida → recibida
- Lugar de entrega y campos de recepción
- Endpoints:
  - `GET/POST /api/requisiciones/`
  - `GET/PUT/DELETE /api/requisiciones/{id}/`
  - `POST /api/requisiciones/{id}/enviar/`
  - `POST /api/requisiciones/{id}/autorizar/`
  - `POST /api/requisiciones/{id}/rechazar/`
  - `POST /api/requisiciones/{id}/surtir/`
  - `POST /api/requisiciones/{id}/marcar-recibida/`
  - `GET /api/requisiciones/{id}/hoja-recoleccion/`
  - `GET /api/requisiciones/exportar-pdf/`

#### 7. Movimientos (`inventario/views.py` - MovimientoViewSet)
- Registro de todas las entradas/salidas
- Trazabilidad completa por lote
- Endpoints:
  - `GET /api/movimientos/`
  - `GET /api/movimientos/exportar/`
  - `GET /api/movimientos/trazabilidad/`
  - `GET /api/movimientos/por-lote/{lote_id}/`

#### 8. Dashboard (`inventario/views.py` - DashboardViewSet)
- KPIs del sistema
- Gráficas de consumo y stock
- Filtro por centro
- Endpoints:
  - `GET /api/dashboard/` - Resumen con KPIs
  - `GET /api/dashboard/graficas/` - Datos para gráficas

#### 9. Reportes (`inventario/views.py` - ReportesViewSet)
- Reportes de inventario, caducidades, requisiciones
- Exportación PDF y Excel
- Endpoints:
  - `GET /api/reportes/inventario-pdf/`
  - `GET /api/reportes/inventario-excel/`
  - `GET /api/reportes/caducidades-pdf/`
  - `GET /api/reportes/caducidades-excel/`
  - `GET /api/reportes/requisiciones-pdf/`
  - `GET /api/reportes/requisiciones-excel/`

#### 10. Trazabilidad
- Historial de movimientos por lote
- Ruta completa: farmacia → centro
- Endpoints:
  - `GET /api/lotes/{id}/trazabilidad/`
  - `GET /api/movimientos/trazabilidad/?lote={id}`

#### 11. Auditoría (`core/models.py` - AuditoriaLog)
- Registro automático de acciones
- Modelo, objeto, usuario, cambios, IP
- Endpoints:
  - `GET /api/auditoria/`
  - `GET /api/auditoria/exportar/`

#### 12. Notificaciones (`core/models.py` - Notificacion)
- Alertas de stock, caducidades, requisiciones
- Filtro por rol/usuario
- Endpoints:
  - `GET /api/notificaciones/`
  - `POST /api/notificaciones/{id}/marcar-leida/`

---

## Frontend

### Estructura de Carpetas

```
inventario-front/
├── src/
│   ├── main.jsx               # Punto de entrada React
│   ├── App.jsx                # Componente raíz con rutas
│   │
│   ├── pages/                 # Páginas/vistas principales
│   │   ├── Login.jsx          # Autenticación
│   │   ├── Dashboard.jsx      # Panel de control con KPIs
│   │   ├── Productos.jsx      # Gestión de productos
│   │   ├── Lotes.jsx          # Gestión de lotes
│   │   ├── Requisiciones.jsx  # Gestión de requisiciones
│   │   ├── Movimientos.jsx    # Historial de movimientos
│   │   ├── Centros.jsx        # Gestión de centros
│   │   ├── Usuarios.jsx       # Gestión de usuarios
│   │   ├── Reportes.jsx       # Generación de reportes
│   │   ├── Trazabilidad.jsx   # Vista de trazabilidad
│   │   ├── Auditoria.jsx      # Logs de auditoría
│   │   ├── Notificaciones.jsx # Centro de notificaciones
│   │   └── Perfil.jsx         # Perfil del usuario
│   │
│   ├── components/            # Componentes reutilizables
│   │   ├── Layout.jsx         # Layout principal con sidebar
│   │   ├── Sidebar.jsx        # Menú lateral
│   │   ├── Header.jsx         # Cabecera
│   │   ├── ProtectedRoute.jsx # Rutas protegidas
│   │   ├── CentroSelector.jsx # Selector de centro
│   │   ├── Pagination.jsx     # Paginación
│   │   ├── Modal.jsx          # Modal genérico
│   │   └── ...
│   │
│   ├── services/              # Servicios de API
│   │   ├── api.js             # Cliente Axios + interceptores
│   │   └── tokenManager.js    # Gestión de tokens en memoria
│   │
│   ├── context/               # Contextos React
│   │   ├── AuthContext.jsx    # Estado de autenticación
│   │   └── PermissionContext.jsx # Permisos y rol
│   │
│   ├── hooks/                 # Hooks personalizados
│   │   └── usePermissions.js  # Hook para verificar permisos
│   │
│   ├── utils/                 # Utilidades
│   │   ├── reportExport.js    # Exportación de reportes
│   │   └── formatters.js      # Formateadores de datos
│   │
│   ├── constants/             # Constantes
│   │   └── theme.js           # Colores y tema
│   │
│   └── styles/                # Estilos CSS
│       ├── Dashboard.css
│       └── ...
│
├── public/                    # Archivos públicos
├── index.html
├── vite.config.js             # Configuración de Vite
├── tailwind.config.js         # Configuración de Tailwind
└── package.json
```

### Flujo de Navegación

```
Login
  │
  ▼
Dashboard ──────────────────────────────────────────────────────────────────┐
  │                                                                          │
  ├──► Productos ────► Detalle ────► Editar/Eliminar                        │
  │         │                                                                │
  │         └──► Importar/Exportar Excel                                    │
  │                                                                          │
  ├──► Lotes ────► Detalle ────► Ajustar Stock                              │
  │         │          │                                                     │
  │         │          └──► Ver Documento PDF adjunto                       │
  │         │          └──► Trazabilidad del Lote                           │
  │         └──► Importar/Exportar Excel                                    │
  │                                                                          │
  ├──► Requisiciones ────► Crear/Editar ────► Enviar                        │
  │         │                    │              │                           │
  │         │                    │              ▼                           │
  │         │                    │         Autorizar/Rechazar               │
  │         │                    │              │                           │
  │         │                    │              ▼                           │
  │         │                    │          Surtir ────► Hoja Recolección   │
  │         │                    │              │                           │
  │         │                    │              ▼                           │
  │         │                    │     Marcar Recibida                      │
  │         │                    │                                          │
  │         └──► Filtrar por estado (enviadas, autorizadas, etc.)           │
  │         └──► Exportar PDF/Excel                                         │
  │                                                                          │
  ├──► Movimientos ────► Filtrar ────► Ver Trazabilidad                     │
  │         └──► Exportar                                                   │
  │                                                                          │
  ├──► Centros ────► CRUD                                                   │
  │         └──► Importar/Exportar                                          │
  │                                                                          │
  ├──► Usuarios ────► CRUD ────► Editar Permisos                            │
  │                                                                          │
  ├──► Reportes ────► Inventario (PDF/Excel)                                │
  │         │──► Caducidades (PDF/Excel)                                    │
  │         └──► Requisiciones (PDF/Excel)                                  │
  │                                                                          │
  ├──► Trazabilidad ────► Buscar por Lote/Producto                          │
  │         └──► Exportar                                                   │
  │                                                                          │
  ├──► Auditoría ────► Filtrar ────► Exportar                               │
  │                                                                          │
  ├──► Notificaciones ────► Ver ────► Marcar Leída                          │
  │                                                                          │
  └──► Perfil ────► Editar Datos ────► Cambiar Contraseña                   │
```

### Conexión Frontend ↔ Backend

```javascript
// src/services/api.js

// Cliente Axios con interceptores
const apiClient = axios.create({
  baseURL: 'https://api.ejemplo.com/api/',
  withCredentials: true,  // Enviar cookies
});

// Interceptor: Agregar token desde memoria
apiClient.interceptors.request.use((config) => {
  const token = getAccessToken();  // De tokenManager.js
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Interceptor: Refresh automático en 401
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401 && !error.config._retry) {
      // Intentar refresh
      const newToken = await refreshToken();
      // Reintentar request original
    }
  }
);

// APIs por módulo
export const productosAPI = {
  getAll: (params) => apiClient.get('/productos/', { params }),
  create: (data) => apiClient.post('/productos/', data),
  update: (id, data) => apiClient.put(`/productos/${id}/`, data),
  delete: (id) => apiClient.delete(`/productos/${id}/`),
  exportar: (params) => apiClient.get('/productos/exportar-excel/', { 
    params, responseType: 'blob' 
  }),
  importar: (formData) => apiClient.post('/productos/importar-excel/', formData),
};

// Similar para: lotesAPI, requisicionesAPI, centrosAPI, usuariosAPI, etc.
```

---

## Base de Datos

### Diagrama Entidad-Relación

```
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│      User        │       │      Centro      │       │     Producto     │
├──────────────────┤       ├──────────────────┤       ├──────────────────┤
│ id               │       │ id               │       │ id               │
│ username         │       │ clave            │       │ clave            │
│ email            │       │ nombre           │       │ descripcion      │
│ password         │  FK   │ tipo             │       │ unidad_medida    │
│ rol              │◄──────│ direccion        │       │ precio_unitario  │
│ centro_id        │───────│ telefono         │       │ stock_minimo     │
│ adscripcion      │       │ responsable      │       │ activo           │
│ activo           │       │ activo           │       │ codigo_barras    │
│ perm_*           │       │ created_at       │       │ created_at       │
│ created_at       │       │ updated_at       │       │ updated_at       │
└────────┬─────────┘       └────────┬─────────┘       │ created_by_id    │
         │                          │                 └────────┬─────────┘
         │                          │                          │
         │     ┌────────────────────┴──────────────────────────┤
         │     │                                               │
         │     │  ┌──────────────────┐                        │
         │     │  │       Lote       │                        │
         │     │  ├──────────────────┤                        │
         │     │  │ id               │                        │
         │     │  │ producto_id      │◄───────────────────────┘
         │     │  │ centro_id        │◄───────────────────────┐
         │     │  │ numero_lote      │                        │
         │     │  │ fecha_caducidad  │                        │
         │     │  │ cantidad_inicial │                        │
         │     │  │ cantidad_actual  │                        │
         │     │  │ estado           │                        │
         │     │  │ precio_compra    │                        │
         │     │  │ proveedor        │                        │
         │     │  │ numero_contrato  │                        │
         │     │  │ marca            │                        │
         │     │  │ documento_pdf    │  ◄── NUEVO             │
         │     │  │ documento_nombre │  ◄── NUEVO             │
         │     │  │ lote_origen_id   │─────┐ (self-ref)       │
         │     │  │ created_at       │     │                  │
         │     │  │ deleted_at       │     │                  │
         │     │  └────────┬─────────┘     │                  │
         │     │           │               │                  │
         │     │           └───────────────┘                  │
         │     │                                               │
         │     │  ┌──────────────────┐                        │
         │     │  │   Requisicion    │                        │
         │     │  ├──────────────────┤                        │
         │     │  │ id               │                        │
         │     │  │ folio            │                        │
         │     │  │ centro_id        │◄───────────────────────┘
         │     │  │ usuario_solicita │◄───────────────────────┐
         │     │  │ fecha_solicitud  │                        │
         │     │  │ estado           │  (borrador→enviada→    │
         │     │  │                  │   autorizada→surtida→  │
         │     │  │                  │   recibida)            │
         │     │  │ usuario_autoriza │◄───────────────────────┤
         │     │  │ fecha_autorizac. │                        │
         │     │  │ lugar_entrega    │  ◄── NUEVO             │
         │     │  │ fecha_recibido   │  ◄── NUEVO             │
         │     │  │ usuario_recibe   │  ◄── NUEVO             │
         │     │  │ observ_recepcion │  ◄── NUEVO             │
         │     │  │ created_at       │                        │
         │     │  └────────┬─────────┘                        │
         │     │           │                                  │
         │     │           ▼                                  │
         │     │  ┌──────────────────┐                        │
         │     │  │DetalleRequisicion│                        │
         │     │  ├──────────────────┤                        │
         │     │  │ requisicion_id   │                        │
         │     │  │ producto_id      │                        │
         │     │  │ lote_id          │                        │
         │     │  │ cant_solicitada  │                        │
         │     │  │ cant_autorizada  │                        │
         │     │  │ cant_surtida     │                        │
         │     │  └──────────────────┘                        │
         │     │                                               │
         │     │  ┌──────────────────┐                        │
         │     │  │    Movimiento    │                        │
         │     │  ├──────────────────┤                        │
         │     │  │ id               │                        │
         │     │  │ tipo             │  (entrada/salida/      │
         │     │  │                  │   ajuste/requisicion)  │
         │     │  │ lote_id          │                        │
         │     │  │ centro_id        │                        │
         │     │  │ cantidad         │                        │
         │     │  │ usuario_id       │◄───────────────────────┤
         │     │  │ requisicion_id   │                        │
         │     │  │ doc_referencia   │                        │
         │     │  │ lugar_entrega    │  ◄── NUEVO             │
         │     │  │ observaciones    │                        │
         │     │  │ fecha            │                        │
         │     │  └──────────────────┘                        │
         │                                                     │
         │     ┌──────────────────┐                            │
         │     │   AuditoriaLog   │                            │
         │     ├──────────────────┤                            │
         │     │ usuario_id       │◄───────────────────────────┤
         │     │ accion           │                            │
         │     │ modelo           │                            │
         │     │ objeto_id        │                            │
         │     │ cambios (JSON)   │                            │
         │     │ ip_address       │                            │
         │     │ fecha            │                            │
         │     └──────────────────┘                            │
         │                                                     │
         │     ┌──────────────────┐                            │
         │     │   Notificacion   │                            │
         │     ├──────────────────┤                            │
         │     │ usuario_id       │◄───────────────────────────┘
         │     │ titulo           │
         │     │ mensaje          │
         │     │ tipo             │
         │     │ requisicion_id   │
         │     │ leida            │
         │     │ fecha_creacion   │
         │     └──────────────────┘

┌──────────────────────────┐
│  ConfiguracionSistema    │  (Singleton)
├──────────────────────────┤
│ nombre_sistema           │
│ nombre_institucion       │  ◄── NUEVO
│ subtitulo_institucion    │  ◄── NUEVO
│ logo_url                 │
│ logo_header              │  ◄── NUEVO
│ logo_pdf                 │  ◄── NUEVO
│ color_primario           │
│ color_secundario         │
│ color_* (todos los demás)│
│ tema_activo              │
│ updated_at               │
│ updated_by_id            │
└──────────────────────────┘
```

### Campos Clave para Trazabilidad

| Tabla | Campo | Propósito |
|-------|-------|-----------|
| Lote | `lote_origen_id` | Vincula lote de centro con lote origen de farmacia |
| Lote | `numero_contrato` | Trazabilidad de adquisición/contrato |
| Lote | `documento_pdf` | Documento de soporte (contrato, certificado) |
| Movimiento | `lote_id` | Vincula movimiento con lote específico |
| Movimiento | `requisicion_id` | Vincula movimiento con requisición |
| Movimiento | `lugar_entrega` | Detalle del lugar de entrega |
| Requisicion | `estado` | Estados del flujo (incluye `recibida`) |
| Requisicion | `usuario_recibe` | Usuario que confirmó recepción |
| Requisicion | `fecha_recibido` | Timestamp de recepción |
| Requisicion | `lugar_entrega` | Centro/servicio/área de entrega |
| Producto/Lote/Centro | `created_at` | Fecha de alta en el sistema |

---

## Flujos Críticos

### 1. Flujo de Requisición

```
Centro crea requisición (borrador)
         │
         ▼
Agrega productos al detalle
         │
         ▼
Envía requisición ───────────────────────────────────────────────┐
         │                                                        │
         ▼                                                        │
Farmacia revisa ───► ¿Aprueba? ──No──► Rechaza (terminal)        │
         │               │                                        │
         │              Sí                                        │
         ▼               │                                        │
Autoriza (total) ◄──────┘                                        │
    o Parcial                                                     │
         │                                                        │
         ▼                                                        │
Farmacia surte:                                                   │
  - Descuenta de lotes de farmacia                               │
  - Crea lotes en centro (con lote_origen)                       │
  - Registra movimientos de salida                               │
  - Genera hoja de recolección                                   │
         │                                                        │
         ▼                                                        │
Centro recibe:                                                    │
  - Marca como recibida                                          │
  - Registra usuario_recibe y fecha_recibido                     │
  - Actualiza inventario del centro                              │
         │                                                        │
         ▼                                                        │
Requisición completada (terminal)                                 │
                                                                  │
◄─────────────────────────────────────────────────────────────────┘
```

### 2. Flujo de Movimientos

```
Entrada de producto (compra/donación)
         │
         ▼
Se crea Lote en farmacia central (centro=NULL)
         │
         ▼
Se registra Movimiento tipo='entrada'
         │
         ▼
Stock actualizado en Lote.cantidad_actual

═══════════════════════════════════════════

Salida por requisición
         │
         ▼
Se selecciona lote de farmacia (FEFO)
         │
         ▼
Se crea Lote espejo en centro destino
  (con lote_origen apuntando al de farmacia)
         │
         ▼
Se registra Movimiento tipo='requisicion'
  - Salida en farmacia (cantidad negativa)
  - Entrada en centro
         │
         ▼
Stock actualizado en ambos lotes
```

### 3. Flujo de Trazabilidad por Lote

```
Consulta: /api/lotes/{id}/trazabilidad/

Respuesta:
{
  "lote": { 
    "numero_lote": "LOTE-001",
    "producto": "Paracetamol 500mg",
    "cantidad_inicial": 1000,
    "cantidad_actual": 750,
    "fecha_entrada": "2025-01-15",
    "documento_pdf": "/media/lotes/documentos/contrato.pdf"
  },
  "origen": {
    "tipo": "farmacia_central",
    "fecha": "2025-01-15"
  },
  "movimientos": [
    { "tipo": "entrada", "cantidad": 1000, "fecha": "2025-01-15" },
    { "tipo": "requisicion", "cantidad": -100, "centro": "CP01", "fecha": "2025-01-20" },
    { "tipo": "requisicion", "cantidad": -150, "centro": "CP02", "fecha": "2025-01-25" }
  ],
  "destinos": [
    { "centro": "CP01 - Centro Penitenciario 1", "cantidad_transferida": 100 },
    { "centro": "CP02 - Centro Penitenciario 2", "cantidad_transferida": 150 }
  ],
  "requisiciones_vinculadas": [
    { "folio": "REQ-CP01-20250120-0001", "estado": "recibida" },
    { "folio": "REQ-CP02-20250125-0003", "estado": "surtida" }
  ]
}
```

---

## Generación de Reportes

### Ubicación del Código
- **PDFs**: `backend/core/utils/pdf_reports.py`
- **Excel**: Generados en cada ViewSet con OpenPyXL

### Arquitectura de PDFs

```python
# backend/core/utils/pdf_reports.py

class FondoOficialCanvas(Canvas):
    """Canvas personalizado con fondo institucional"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fondo_path = self._get_fondo_path()
    
    def _get_fondo_path(self):
        # Buscar en ConfiguracionSistema.logo_pdf primero
        # Si no existe, usar static/img/pdf/fondoOficial.png
        pass
    
    def draw_page_background(self):
        # Dibuja el fondo en cada página
        pass


def generar_reporte_inventario(queryset, filtros):
    """Genera PDF de reporte de inventario"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    
    # Usar FondoOficialCanvas para el fondo
    story = []
    
    # Agregar título institucional
    story.append(_crear_encabezado_institucional())
    
    # Crear tabla con datos
    story.append(_crear_tabla_institucional(datos))
    
    # Generar PDF
    doc.build(story, canvasmaker=FondoOficialCanvas)
    return buffer.getvalue()
```

### Personalización desde ConfiguracionSistema

```python
# El PDF lee la configuración:
config = ConfiguracionSistema.get_config()

# Logo/fondo para PDF
logo_path = config.logo_pdf.path if config.logo_pdf else 'static/img/pdf/fondoOficial.png'

# Textos institucionales
nombre_institucion = config.nombre_institucion
subtitulo = config.subtitulo_institucion

# Colores (para títulos, etc.)
color_primario = config.color_primario
```

---

## Configuración y Personalización

### Modelo ConfiguracionSistema (Singleton)

```python
# backend/core/models.py

class ConfiguracionSistema(models.Model):
    """Singleton para configuración global"""
    
    # Identificación
    nombre_sistema = models.CharField(max_length=100)
    nombre_institucion = models.CharField(max_length=200)
    subtitulo_institucion = models.CharField(max_length=200)
    
    # Logos
    logo_url = models.URLField(blank=True)
    logo_header = models.ImageField(upload_to='configuracion/logos/')
    logo_pdf = models.ImageField(upload_to='configuracion/logos/')
    
    # Colores del tema
    color_primario = models.CharField(max_length=7)  # #RRGGBB
    color_secundario = models.CharField(max_length=7)
    color_acento = models.CharField(max_length=7)
    # ... más colores
    
    tema_activo = models.CharField(choices=TEMAS_PREDEFINIDOS)
    
    @classmethod
    def get_config(cls):
        """Obtiene la configuración (crea si no existe)"""
        config, created = cls.objects.get_or_create(pk=1)
        return config
    
    def to_css_variables(self):
        """Retorna colores como CSS variables"""
        return {
            '--color-primary': self.color_primario,
            '--color-secondary': self.color_secundario,
            # ...
        }
```

### Endpoint para el Frontend

```python
# GET /api/configuracion/

{
  "nombre_sistema": "Sistema de Farmacia Penitenciaria",
  "nombre_institucion": "Secretaría de Seguridad",
  "subtitulo_institucion": "Dirección General de Prevención y Reinserción Social",
  "logo_header_url": "/media/configuracion/logos/logo.png",
  "colores": {
    "primario": "#9F2241",
    "secundario": "#6B1839",
    "acento": "#BC955C",
    "fondo": "#F5F5F5",
    // ...
  },
  "tema_activo": "custom"
}
```

### Aplicación en Frontend

```jsx
// src/hooks/useTheme.js
import { useEffect, useState } from 'react';
import { configAPI } from '../services/api';

export const useTheme = () => {
  const [theme, setTheme] = useState(null);
  
  useEffect(() => {
    configAPI.getConfig().then(res => {
      const { colores } = res.data;
      // Aplicar como CSS variables
      Object.entries(colores).forEach(([key, value]) => {
        document.documentElement.style.setProperty(`--color-${key}`, value);
      });
      setTheme(res.data);
    });
  }, []);
  
  return theme;
};
```

---

## Seguridad y Autenticación

### Sistema de Tokens

```
┌─────────────────────────────────────────────────────────────────┐
│                       FLUJO DE AUTENTICACIÓN                    │
│                                                                 │
│  1. Login: POST /api/token/                                     │
│     Request: { username, password }                             │
│     Response: { access: "...", user: {...} }                   │
│     + Cookie HttpOnly: refresh_token                            │
│                                                                 │
│  2. Requests autenticados:                                      │
│     Header: Authorization: Bearer {access_token}                │
│     (access_token guardado en memoria JS, no localStorage)      │
│                                                                 │
│  3. Refresh automático (cuando access expira):                  │
│     POST /api/token/refresh/                                    │
│     Cookie: refresh_token (automático)                          │
│     Response: { access: "nuevo_token" }                         │
│                                                                 │
│  4. Logout: POST /api/logout/                                   │
│     Invalida refresh token en servidor                          │
│     Limpia access de memoria                                    │
└─────────────────────────────────────────────────────────────────┘
```

### Roles y Permisos

| Rol | Descripción | Permisos |
|-----|-------------|----------|
| `admin_sistema` | Administrador global | Todo el sistema |
| `farmacia` | Usuario de farmacia central | Productos, lotes, autorizar requisiciones, reportes |
| `centro` | Usuario de centro penitenciario | Crear requisiciones, ver inventario del centro |
| `vista` | Solo consulta | Ver sin modificar |

### Permisos por Módulo (User.perm_*)

```python
# El usuario puede tener permisos específicos que sobreescriben el rol base
user.perm_productos = True   # Puede ver productos (aunque su rol no lo incluya)
user.perm_usuarios = False   # No puede ver usuarios (aunque su rol sí lo incluya)

# En el frontend, se verifica así:
const { permisos } = usePermissions();
if (permisos.verProductos) { /* mostrar módulo */ }
```

---

## Resumen de Endpoints Principales

| Módulo | Endpoint | Métodos | Descripción |
|--------|----------|---------|-------------|
| Auth | `/api/token/` | POST | Login |
| Auth | `/api/token/refresh/` | POST | Refresh token |
| Auth | `/api/logout/` | POST | Cerrar sesión |
| Usuarios | `/api/usuarios/` | GET, POST | Listar/crear usuarios |
| Usuarios | `/api/usuarios/{id}/` | GET, PUT, DELETE | CRUD usuario |
| Usuarios | `/api/usuarios/me/` | GET | Perfil actual |
| Productos | `/api/productos/` | GET, POST | Listar/crear productos |
| Productos | `/api/productos/exportar-excel/` | GET | Exportar Excel |
| Productos | `/api/productos/importar-excel/` | POST | Importar Excel |
| Lotes | `/api/lotes/` | GET, POST | Listar/crear lotes |
| Lotes | `/api/lotes/{id}/trazabilidad/` | GET | Ver trazabilidad |
| Requisiciones | `/api/requisiciones/` | GET, POST | Listar/crear |
| Requisiciones | `/api/requisiciones/{id}/enviar/` | POST | Cambiar estado |
| Requisiciones | `/api/requisiciones/{id}/autorizar/` | POST | Autorizar |
| Requisiciones | `/api/requisiciones/{id}/surtir/` | POST | Surtir |
| Requisiciones | `/api/requisiciones/{id}/marcar-recibida/` | POST | Confirmar recepción |
| Movimientos | `/api/movimientos/` | GET | Listar movimientos |
| Movimientos | `/api/movimientos/trazabilidad/` | GET | Trazabilidad general |
| Dashboard | `/api/dashboard/` | GET | KPIs |
| Dashboard | `/api/dashboard/graficas/` | GET | Datos gráficas |
| Reportes | `/api/reportes/inventario-pdf/` | GET | PDF inventario |
| Reportes | `/api/reportes/inventario-excel/` | GET | Excel inventario |
| Configuración | `/api/configuracion/` | GET, PUT | Leer/actualizar config |
| Auditoría | `/api/auditoria/` | GET | Logs de auditoría |
| Notificaciones | `/api/notificaciones/` | GET | Listar notificaciones |

---

*Documento generado el 1 de Diciembre de 2025*
*Sistema de Farmacia Penitenciaria v2.0*
