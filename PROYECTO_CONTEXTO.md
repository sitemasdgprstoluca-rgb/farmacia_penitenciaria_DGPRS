# 📋 Sistema de Control de Abasto - Farmacia Penitenciaria

## 📊 Resumen del Proyecto

**Nombre:** Sistema de Control de Abasto para Farmacias Penitenciarias  
**Tecnologías:** Django REST Framework + React + Vite  
**Base de Datos:** SQLite (desarrollo) / PostgreSQL (producción)  
**Propósito:** Gestión integral de inventario de medicamentos, lotes, requisiciones, centros penitenciarios y auditoría para la Subsecretaría del Sistema Penitenciario del Estado de México

---

## 🗂️ Estructura General del Proyecto

```
farmacia_penitenciaria/
├── backend/                    # API Django REST Framework
├── inventario-front/          # Frontend React + Vite
├── apps/                      # Apps Django antiguas (legacy)
├── fix_encoding.py           # Script de corrección de encoding
├── add-devusa.ps1
├── patch_stub.ps1
└── fix_encoding.py
```

---

## 🔧 BACKEND - Django REST Framework

### 📁 Estructura del Backend

```
backend/
├── manage.py                  # Django management script
├── db.sqlite3                # Base de datos SQLite (desarrollo)
├── requirements.txt          # Dependencias Python
├── settings.py               # Configuración principal Django
├── urls.py                   # URLs principales del proyecto
├── wsgi.py / asgi.py        # Servidores WSGI/ASGI
├── middleware.py             # Middlewares personalizados
│
├── backend/                  # Configuración del proyecto Django
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── config/                   # Configuración centralizada
│   ├── settings.py          # Settings alternativo
│   ├── urls.py              # URLs de configuración
│   └── api_urls.py          # URLs de API
│
├── core/                     # App principal del sistema
│   ├── models.py            # Modelos core del sistema
│   ├── views.py             # Vistas principales
│   ├── serializers.py       # Serializadores DRF
│   ├── permissions.py       # Permisos personalizados
│   ├── middleware.py        # Middlewares específicos
│   ├── signals.py           # Señales Django
│   ├── constants.py         # Constantes del sistema
│   ├── exceptions.py        # Excepciones personalizadas
│   ├── urls.py
│   ├── admin.py
│   ├── management/          # Comandos de gestión
│   ├── migrations/          # Migraciones de BD
│   ├── tests/               # Tests unitarios
│   └── utils/               # Utilidades
│
├── farmacia/                # App de gestión de farmacia
│   ├── models.py           # Modelos de farmacia
│   ├── views.py            # Vistas de farmacia
│   ├── serializers.py      # Serializadores
│   ├── permissions.py      # Permisos específicos
│   ├── signals.py          # Señales
│   ├── urls.py
│   ├── admin.py
│   ├── management/         # Comandos personalizados
│   ├── migrations/
│   └── reports/            # Generación de reportes
│
├── inventario/             # App de inventario
│   ├── admin.py
│   ├── apps.py
│   ├── serializers.py
│   ├── urls.py
│   ├── views.py
│   ├── management/
│   ├── migrations/
│   └── tests/
│
├── reports/                # Sistema de reportes
│
└── scripts/               # Scripts de utilidad
    ├── connection_check.py
    └── db_check.py
```

### 🗄️ Modelos de Base de Datos

#### **1. User (Usuario Personalizado)**
```python
# Ubicación: core/models.py o farmacia/models.py
Campos:
- username (unique)
- email
- first_name
- last_name
- password (encriptado)
- is_active
- is_staff
- is_superuser
- groups (ManyToMany a Group)
- user_permissions
- centro (ForeignKey a Centro) - Centro asignado
- fecha_creacion
- fecha_actualizacion

Roles (Django Groups):
- SUPERUSER (superusuario)
- FARMACIA_ADMIN (administrador de farmacia)
- CENTRO_USER (usuario de centro penitenciario)
- VISTA_USER (solo lectura)
```

#### **2. Centro (Centro Penitenciario)**
```python
Campos:
- nombre (max_length=200)
- clave (unique, max_length=50)
- direccion (text)
- telefono (max_length=20)
- email
- responsable (CharField)
- activo (BooleanField, default=True)
- fecha_creacion
- fecha_actualizacion
- creado_por (ForeignKey a User)
- modificado_por (ForeignKey a User)

Relaciones:
- usuarios (reverse de User.centro)
- requisiciones (reverse de Requisicion.centro)
```

#### **3. Producto**
```python
Campos:
- clave (unique, max_length=50) - Código único del producto
- descripcion (max_length=500)
- presentacion (max_length=100) - Ej: "Caja con 20 tabletas"
- unidad_medida (max_length=20) - Ej: "pieza", "caja", "frasco"
- precio_unitario (Decimal)
- stock_minimo (Integer) - Nivel mínimo de stock
- stock_actual (Integer) - Calculado desde lotes
- activo (Boolean, default=True)
- categoria (CharField) - Clasificación del medicamento
- sustancia_activa (CharField, opcional)
- fecha_creacion
- fecha_actualizacion
- creado_por (ForeignKey a User)
- modificado_por (ForeignKey a User)

Relaciones:
- lotes (reverse de Lote.producto)
- movimientos (reverse de Movimiento.producto)
```

#### **4. Lote**
```python
Campos:
- producto (ForeignKey a Producto)
- numero_lote (CharField, max_length=100)
- fecha_caducidad (DateField)
- cantidad_inicial (Integer)
- cantidad_actual (Integer) - Se actualiza con movimientos
- precio_compra (Decimal)
- proveedor (CharField, max_length=200)
- factura (CharField, max_length=100, opcional)
- observaciones (TextField, opcional)
- activo (Boolean, default=True)
- fecha_creacion
- fecha_actualizacion
- creado_por (ForeignKey a User)
- modificado_por (ForeignKey a User)

Constraints:
- unique_together = ('producto', 'numero_lote')

Métodos:
- dias_para_caducar() - Calcula días restantes
- nivel_alerta() - Retorna: 'vencido', 'critico', 'proximo', 'normal'
```

#### **5. Movimiento**
```python
Campos:
- tipo (CharField, choices=['ENTRADA', 'SALIDA', 'AJUSTE', 'MERMA'])
- producto (ForeignKey a Producto)
- lote (ForeignKey a Lote, nullable)
- cantidad (Integer)
- centro_origen (ForeignKey a Centro, nullable)
- centro_destino (ForeignKey a Centro, nullable)
- requisicion (ForeignKey a Requisicion, nullable)
- motivo (CharField, max_length=200)
- observaciones (TextField, opcional)
- documento_referencia (CharField, max_length=100)
- fecha_movimiento (DateTimeField, auto_now_add)
- realizado_por (ForeignKey a User)

Validaciones:
- Verificar stock suficiente en SALIDA
- Actualizar cantidad_actual del Lote
```

#### **6. Requisicion (Solicitud de Medicamentos)**
```python
Campos:
- folio (unique, generado automáticamente) - Ej: REQ-202400001
- centro (ForeignKey a Centro) - Centro solicitante
- estado (CharField, choices)
  * 'borrador' - En edición
  * 'enviada' - Enviada a farmacia
  * 'autorizada' - Aprobada por farmacia
  * 'rechazada' - Rechazada
  * 'surtida' - Medicamentos entregados
  * 'cancelada' - Cancelada
- fecha_solicitud (DateTimeField)
- fecha_autorizacion (DateTimeField, nullable)
- fecha_surtido (DateTimeField, nullable)
- usuario_solicita (ForeignKey a User) - Quien crea
- usuario_autoriza (ForeignKey a User, nullable) - Admin farmacia
- usuario_surte (ForeignKey a User, nullable)
- comentario (TextField, opcional)
- comentario_rechazo (TextField, opcional)
- total_items (Integer) - Cantidad de productos
- total_solicitado (Decimal) - Valor total
- total_autorizado (Decimal, nullable)
- activo (Boolean, default=True)
- fecha_creacion
- fecha_actualizacion

Relaciones:
- items (reverse de DetalleRequisicion.requisicion)
- movimientos (reverse de Movimiento.requisicion)

Métodos:
- puede_editar(user) - Solo borrador y creador
- puede_enviar(user)
- puede_autorizar(user) - Solo FARMACIA_ADMIN
```

#### **7. DetalleRequisicion**
```python
Campos:
- requisicion (ForeignKey a Requisicion)
- producto (ForeignKey a Producto)
- cantidad_solicitada (Integer)
- cantidad_autorizada (Integer, nullable)
- precio_unitario (Decimal)
- subtotal_solicitado (Decimal)
- subtotal_autorizado (Decimal, nullable)
- observaciones (TextField, opcional)
- fecha_creacion

Constraints:
- unique_together = ('requisicion', 'producto')
```

#### **8. AuditoriaLog (Registro de Auditoría)**
```python
Campos:
- usuario (ForeignKey a User)
- accion (CharField, max_length=100)
  * 'CREATE', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT', etc.
- modulo (CharField, max_length=50)
  * 'productos', 'lotes', 'requisiciones', 'usuarios', etc.
- objeto_tipo (CharField) - Nombre del modelo
- objeto_id (Integer) - ID del objeto afectado
- descripcion (TextField) - Descripción detallada
- ip_address (GenericIPAddressField)
- user_agent (TextField)
- datos_anteriores (JSONField, nullable) - Estado previo
- datos_nuevos (JSONField, nullable) - Estado nuevo
- fecha_accion (DateTimeField, auto_now_add)

Indices:
- usuario, fecha_accion
- modulo, accion
```

#### **9. ImportacionLog (Log de Importaciones Excel)**
```python
Campos:
- tipo (CharField) - 'productos', 'lotes', etc.
- archivo_nombre (CharField)
- usuario (ForeignKey a User)
- registros_procesados (Integer)
- registros_creados (Integer)
- registros_actualizados (Integer)
- registros_errores (Integer)
- errores (JSONField) - Lista de errores
- fecha_importacion (DateTimeField, auto_now_add)
- exitosa (Boolean)
```

### 🔐 Sistema de Permisos

#### **Permisos Personalizados (DRF)**
```python
# core/permissions.py o farmacia/permissions.py

class IsFarmaciaAdmin(BasePermission):
    """Solo usuarios con rol FARMACIA_ADMIN o superuser"""
    
class IsCentroUser(BasePermission):
    """Usuarios de centros penitenciarios"""
    
class CanAuthorizeRequisicion(BasePermission):
    """Puede autorizar requisiciones (FARMACIA_ADMIN)"""
    
class CanCreateRequisicion(BasePermission):
    """Puede crear requisiciones (CENTRO_USER)"""
```

#### **Permisos por Endpoint**
```python
# Global en settings.py
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# Específicos por ViewSet:
- ProductoViewSet: IsAuthenticated + IsFarmaciaAdmin (write)
- LoteViewSet: IsAuthenticated + IsFarmaciaAdmin (write)
- RequisicionViewSet: IsAuthenticated (list/retrieve), permisos específicos por acción
- CentroViewSet: IsAuthenticated + IsFarmaciaAdmin
- UserViewSet: IsAuthenticated + IsFarmaciaAdmin
```

### 🌐 Endpoints de la API

**Base URL:** `http://localhost:8000/api/`

#### **Autenticación**
```
POST   /api/auth/login/              # Login (JWT)
POST   /api/auth/refresh/            # Refresh token
POST   /api/auth/logout/             # Logout
GET    /api/auth/me/                 # Usuario actual
```

#### **Usuarios**
```
GET    /api/usuarios/                # Listar usuarios
POST   /api/usuarios/                # Crear usuario
GET    /api/usuarios/{id}/           # Detalle usuario
PUT    /api/usuarios/{id}/           # Actualizar usuario
DELETE /api/usuarios/{id}/           # Eliminar usuario
PATCH  /api/usuarios/{id}/cambiar_password/  # Cambiar contraseña
```

#### **Centros Penitenciarios**
```
GET    /api/centros/                 # Listar centros
POST   /api/centros/                 # Crear centro
GET    /api/centros/{id}/            # Detalle centro
PUT    /api/centros/{id}/            # Actualizar centro
DELETE /api/centros/{id}/            # Soft delete
POST   /api/centros/importar_excel/  # Importación Excel
```

#### **Productos**
```
GET    /api/productos/               # Listar productos (paginado)
POST   /api/productos/               # Crear producto
GET    /api/productos/{id}/          # Detalle producto
PUT    /api/productos/{id}/          # Actualizar producto
DELETE /api/productos/{id}/          # Soft delete
POST   /api/productos/importar_excel/  # Importación Excel
GET    /api/productos/export_excel/  # Exportar a Excel
GET    /api/productos/{id}/auditoria/  # Historial de cambios
GET    /api/productos/stock_critico/  # Productos con stock bajo
```

#### **Lotes**
```
GET    /api/lotes/                   # Listar lotes
POST   /api/lotes/                   # Crear lote
GET    /api/lotes/{id}/              # Detalle lote
PUT    /api/lotes/{id}/              # Actualizar lote
DELETE /api/lotes/{id}/              # Soft delete
GET    /api/lotes/proximos_vencer/   # Lotes próximos a caducar
POST   /api/lotes/importar_excel/    # Importación Excel
```

#### **Requisiciones**
```
GET    /api/requisiciones/           # Listar requisiciones
POST   /api/requisiciones/           # Crear requisición
GET    /api/requisiciones/{id}/      # Detalle requisición
PUT    /api/requisiciones/{id}/      # Actualizar requisición
DELETE /api/requisiciones/{id}/      # Soft delete
POST   /api/requisiciones/{id}/enviar/      # Enviar a farmacia
POST   /api/requisiciones/{id}/autorizar/   # Autorizar (admin)
POST   /api/requisiciones/{id}/rechazar/    # Rechazar
POST   /api/requisiciones/{id}/surtir/      # Marcar como surtida
POST   /api/requisiciones/{id}/cancelar/    # Cancelar
GET    /api/requisiciones/{id}/pdf/         # Generar PDF
```

#### **Movimientos**
```
GET    /api/movimientos/             # Listar movimientos
POST   /api/movimientos/             # Registrar movimiento
GET    /api/movimientos/{id}/        # Detalle movimiento
GET    /api/movimientos/trazabilidad/?producto=X  # Trazabilidad producto
GET    /api/movimientos/trazabilidad/?lote=Y      # Trazabilidad lote
```

#### **Auditoría**
```
GET    /api/auditoria/               # Listar registros
GET    /api/auditoria/?modulo=X      # Filtrar por módulo
GET    /api/auditoria/?usuario=Y     # Filtrar por usuario
GET    /api/auditoria/?accion=Z      # Filtrar por acción
```

#### **Reportes**
```
GET    /api/reportes/inventario/     # Reporte de inventario
GET    /api/reportes/caducidades/    # Lotes próximos a caducar
GET    /api/reportes/movimientos/    # Reporte de movimientos
GET    /api/reportes/requisiciones/  # Reporte de requisiciones
```

### 🛡️ Autenticación JWT

```python
# settings.py
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ALGORITHM': 'HS256',
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# Flujo:
1. POST /api/auth/login/ → { access, refresh, user }
2. Headers: Authorization: Bearer {access_token}
3. POST /api/auth/refresh/ → Renovar access_token
```

---

## ⚛️ FRONTEND - React + Vite

### 📁 Estructura del Frontend

```
inventario-front/
├── index.html                # HTML principal
├── package.json             # Dependencias npm
├── vite.config.js          # Configuración Vite
├── tailwind.config.js      # Configuración Tailwind CSS
├── postcss.config.js       # PostCSS config
│
├── public/                 # Archivos estáticos
│
└── src/
    ├── main.jsx           # Entry point
    ├── App.jsx            # Componente principal
    ├── index.css          # Estilos globales
    ├── App.css
    │
    ├── assets/            # Imágenes, iconos, etc.
    │
    ├── components/        # Componentes reutilizables
    │   ├── PageHeader.jsx          # Header de páginas
    │   ├── ProtectedAction.jsx     # Botones con permisos
    │   └── [otros componentes]
    │
    ├── config/            # Configuración
    │   └── dev.js         # DEV_CONFIG para desarrollo
    │
    ├── constants/         # Constantes
    │   └── theme.js       # COLORS del tema (vino, guinda, dorado)
    │
    ├── context/           # Contextos React
    │   └── PermissionContext.jsx   # Gestión de permisos
    │
    ├── hooks/             # Custom hooks
    │   └── usePermissions.js       # Hook de permisos
    │
    ├── pages/             # Páginas principales
    │   ├── Login.jsx                    # Página de login
    │   ├── Dashboard.jsx                # Dashboard principal
    │   ├── Productos.jsx                # Gestión de productos
    │   ├── Lotes.jsx                    # Gestión de lotes
    │   ├── Requisiciones.jsx            # Lista de requisiciones
    │   ├── RequisicionDetalle.jsx       # Detalle/crear requisición
    │   ├── Centros.jsx                  # Gestión de centros
    │   ├── Usuarios.jsx                 # Gestión de usuarios
    │   ├── Auditoria.jsx                # Registros de auditoría
    │   ├── Trazabilidad.jsx             # Trazabilidad de productos/lotes
    │   ├── Reportes.jsx                 # Generación de reportes
    │   └── AccesoRestringido.jsx        # Página 403
    │
    ├── services/          # Servicios de API
    │   └── api.js         # Axios configurado + endpoints
    │
    ├── styles/            # Estilos adicionales
    │
    └── utils/             # Utilidades
```

### 📦 Dependencias del Frontend

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "axios": "^1.6.0",
    "react-hot-toast": "^2.4.1",
    "react-icons": "^4.12.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.0",
    "vite": "^5.0.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.32",
    "autoprefixer": "^10.4.16"
  }
}
```

### 🎨 Tema y Colores

```javascript
// constants/theme.js
export const COLORS = {
  vino: '#9F2241',      // Color principal (botones, headers)
  guinda: '#6B1839',    // Color secundario (títulos, labels)
  dorado: '#B8860B',    // Color de acento (alertas, badges)
  // ... más colores
};
```

### 🔐 Sistema de Autenticación Frontend

```javascript
// services/api.js - Configuración Axios
const api = axios.create({
  baseURL: 'http://localhost:8000/api',
});

// Interceptor para agregar token
api.interceptors.request.use(config => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Interceptor para manejar errores 401
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      localStorage.clear();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

### 🧭 Rutas de la Aplicación

```javascript
// App.jsx
<Routes>
  <Route path="/login" element={<Login />} />
  <Route path="/" element={<Dashboard />} />
  <Route path="/productos" element={<Productos />} />
  <Route path="/lotes" element={<Lotes />} />
  <Route path="/requisiciones" element={<Requisiciones />} />
  <Route path="/requisiciones/nueva" element={<RequisicionDetalle />} />
  <Route path="/requisiciones/:id" element={<RequisicionDetalle />} />
  <Route path="/centros" element={<Centros />} />
  <Route path="/usuarios" element={<Usuarios />} />
  <Route path="/auditoria" element={<Auditoria />} />
  <Route path="/trazabilidad" element={<Trazabilidad />} />
  <Route path="/reportes" element={<Reportes />} />
  <Route path="/acceso-restringido" element={<AccesoRestringido />} />
</Routes>
```

### 📄 Páginas Principales - Funcionalidades

#### **1. Login.jsx**
```javascript
Funciones:
- handleLogin(credentials) - Autenticación
- Modo desarrollador (DEV_CONFIG.ENABLED)
- Almacena: token, user, permisos en localStorage
- Redirección a Dashboard tras login exitoso

UI:
- Form con username/password
- Botón "Iniciar Sesión"
- Logo/branding Subsecretaría
```

#### **2. Dashboard.jsx**
```javascript
Funciones:
- Mostrar KPIs principales:
  * Total productos
  * Lotes próximos a caducar
  * Requisiciones pendientes
  * Stock crítico
- Últimos movimientos (tabla)
- Alertas de caducidad
- Gráficas/estadísticas

Estados:
- loading
- productos, lotes, requisiciones (arrays)
- kpis (objeto con métricas)
```

#### **3. Productos.jsx**
```javascript
Funciones:
- cargarProductos(params) - GET /api/productos/
- handleCreate() - POST /api/productos/
- handleUpdate(id, data) - PUT /api/productos/{id}/
- handleDelete(id) - DELETE /api/productos/{id}/
- handleImportExcel(file) - POST /api/productos/importar_excel/
- exportarExcel() - GET /api/productos/export_excel/
- verAuditoria(id) - GET /api/productos/{id}/auditoria/

Filtros:
- Búsqueda por clave/descripción
- Filtro por stock (sin_stock, critico, bajo, normal, alto)
- Paginación (10, 25, 50 items)

UI Components:
- Tabla de productos
- Modal de crear/editar
- Modal de auditoría
- Botones: Nuevo, Importar, Exportar, Editar, Eliminar
```

#### **4. Lotes.jsx**
```javascript
Funciones:
- cargarLotes(params) - GET /api/lotes/
- handleCreate() - POST /api/lotes/
- handleUpdate(id, data) - PUT /api/lotes/{id}/
- handleDelete(id) - DELETE /api/lotes/{id}/
- handleImportExcel(file) - POST /api/lotes/importar_excel/

Filtros:
- Búsqueda por número de lote/producto
- Filtro por caducidad:
  * vencido
  * critico (≤7 días)
  * proximo (≤30 días)
  * normal (>30 días)
- Paginación

UI:
- Tabla con:
  * Producto
  * Número de lote
  * Fecha caducidad
  * Días restantes (con badge de color)
  * Stock actual
  * Proveedor
  * Acciones
- Modal de crear/editar lote
- Badges de alerta por caducidad
```

#### **5. Requisiciones.jsx**
```javascript
Funciones:
- cargarRequisiciones() - GET /api/requisiciones/
- handleEnviar(id) - POST /api/requisiciones/{id}/enviar/
- handleAutorizar(id) - POST /api/requisiciones/{id}/autorizar/
- handleRechazar(id, motivo) - POST /api/requisiciones/{id}/rechazar/
- handleSurtir(id) - POST /api/requisiciones/{id}/surtir/
- handleCancelar(id) - POST /api/requisiciones/{id}/cancelar/
- verDetalle(id) - Navega a /requisiciones/{id}
- descargarPDF(id) - GET /api/requisiciones/{id}/pdf/

Filtros:
- Por estado: borrador, enviada, autorizada, rechazada, surtida, cancelada
- Búsqueda por folio/centro
- Paginación

UI:
- Tabla de requisiciones:
  * Folio
  * Centro
  * Fecha solicitud
  * Estado (badge con color)
  * Total items
  * Total autorizado
  * Acciones según estado
- Botón "Nueva Requisición"
- Permisos según rol
```

#### **6. RequisicionDetalle.jsx**
```javascript
Funciones:
- cargarRequisicion(id) - GET /api/requisiciones/{id}/
- agregarProducto(producto) - Agregar a detalle
- eliminarProducto(index) - Quitar de detalle
- actualizarCantidad(index, cantidad)
- guardarRequisicion() - POST/PUT /api/requisiciones/
- enviarRequisicion() - POST /api/requisiciones/{id}/enviar/
- autorizarRequisicion() - POST /api/requisiciones/{id}/autorizar/

Estados:
- requisicion (objeto)
- detalles (array de productos)
- modoEdicion (boolean)
- permisos del usuario

UI:
- Información general (folio, centro, fecha)
- Tabla de productos:
  * Producto (select o texto)
  * Cantidad solicitada (input)
  * Cantidad autorizada (input, solo admin)
  * Precio unitario
  * Subtotal
  * Acciones (eliminar)
- Botones: Guardar, Enviar, Autorizar, Rechazar
- Modal de agregar producto
```

#### **7. Centros.jsx**
```javascript
Funciones:
- cargarCentros() - GET /api/centros/
- handleCreate() - POST /api/centros/
- handleUpdate(id) - PUT /api/centros/{id}/
- handleDelete(id) - DELETE /api/centros/{id}/
- handleImportExcel(file) - POST /api/centros/importar_excel/

UI:
- Tabla de centros:
  * Clave
  * Nombre
  * Dirección
  * Teléfono
  * Responsable
  * Activo
  * Acciones
- Modal de crear/editar
- Importación Excel
```

#### **8. Usuarios.jsx**
```javascript
Funciones:
- cargarUsuarios() - GET /api/usuarios/
- handleCreate() - POST /api/usuarios/
- handleUpdate(id) - PUT /api/usuarios/{id}/
- handleDelete(id) - DELETE /api/usuarios/{id}/
- cambiarPassword(id, passwords) - PATCH /api/usuarios/{id}/cambiar_password/

UI:
- Tabla de usuarios:
  * Username
  * Nombre completo
  * Email
  * Rol/Grupo
  * Centro asignado
  * Activo
  * Acciones
- Modal de crear/editar
- Modal de cambiar contraseña
```

#### **9. Auditoria.jsx**
```javascript
Funciones:
- cargarRegistros(params) - GET /api/auditoria/

Filtros:
- Por módulo (productos, lotes, requisiciones, usuarios, etc.)
- Por acción (CREATE, UPDATE, DELETE, LOGIN, LOGOUT)
- Por usuario
- Búsqueda general
- Rango de fechas
- Paginación

UI:
- Tabla de auditoría:
  * Fecha/Hora
  * Usuario
  * Acción
  * Módulo
  * Descripción
  * IP
  * Detalles (modal con JSON)
```

#### **10. Trazabilidad.jsx**
```javascript
Funciones:
- buscarTrazabilidad(tipo, codigo)
  * tipo: 'producto' o 'lote'
  * codigo: clave del producto o número de lote
- GET /api/movimientos/trazabilidad/?producto=X
- GET /api/movimientos/trazabilidad/?lote=Y

UI:
- Form de búsqueda:
  * Tipo de búsqueda (radio)
  * Input de código
  * Botón buscar
- Resultado:
  * Información del producto/lote
  * Línea de tiempo de movimientos:
    - Fecha
    - Tipo (ENTRADA/SALIDA)
    - Cantidad
    - Centro origen/destino
    - Usuario
    - Observaciones
```

#### **11. Reportes.jsx**
```javascript
Funciones:
- generarReporteInventario() - GET /api/reportes/inventario/
- generarReporteCaducidades(dias) - GET /api/reportes/caducidades/
- generarReporteMovimientos(filtros) - GET /api/reportes/movimientos/
- generarReporteRequisiciones(filtros) - GET /api/reportes/requisiciones/
- descargarExcel(tipo, datos)
- descargarPDF(tipo, datos)

UI:
- Cards de tipos de reportes:
  1. Inventario General
  2. Lotes próximos a vencer
  3. Movimientos de inventario
  4. Requisiciones
- Filtros específicos por reporte
- Botones: Ver, Descargar Excel, Descargar PDF
```

### 🔧 Servicios y Utilidades

#### **services/api.js**
```javascript
// Configuración de Axios
export const api = axios.create({
  baseURL: 'http://localhost:8000/api',
});

// Endpoints organizados
export const authAPI = {
  login: (credentials) => api.post('/auth/login/', credentials),
  logout: () => api.post('/auth/logout/'),
  me: () => api.get('/auth/me/'),
};

export const productosAPI = {
  getAll: (params) => api.get('/productos/', { params }),
  getOne: (id) => api.get(`/productos/${id}/`),
  create: (data) => api.post('/productos/', data),
  update: (id, data) => api.put(`/productos/${id}/`, data),
  delete: (id) => api.delete(`/productos/${id}/`),
  importar: (file) => api.post('/productos/importar_excel/', file),
  exportar: () => api.get('/productos/export_excel/', { responseType: 'blob' }),
  auditoria: (id) => api.get(`/productos/${id}/auditoria/`),
};

export const lotesAPI = {
  // Similar estructura a productosAPI
};

export const requisicionesAPI = {
  // Similar + acciones específicas (enviar, autorizar, etc.)
};

export const centrosAPI = { /* ... */ };
export const usuariosAPI = { /* ... */ };
export const auditoriaAPI = { /* ... */ };
export const movimientosAPI = { /* ... */ };
export const reportesAPI = { /* ... */ };
```

#### **context/PermissionContext.jsx**
```javascript
export const PermissionProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [permisos, setPermisos] = useState([]);
  const [loading, setLoading] = useState(true);

  // Funciones:
  - checkPermission(permission) - Verificar permiso
  - hasRole(role) - Verificar rol
  - getRolPrincipal() - Obtener rol principal del usuario
  - isFarmaciaAdmin() - Es administrador?
  - isCentroUser() - Es usuario de centro?
  
  return (
    <PermissionContext.Provider value={{
      user, permisos, loading,
      checkPermission, hasRole, getRolPrincipal,
      isFarmaciaAdmin, isCentroUser
    }}>
      {children}
    </PermissionContext.Provider>
  );
};
```

#### **hooks/usePermissions.js**
```javascript
export const usePermissions = () => {
  const context = useContext(PermissionContext);
  if (!context) {
    throw new Error('usePermissions debe usarse dentro de PermissionProvider');
  }
  return context;
};
```

#### **components/ProtectedAction.jsx**
```javascript
export const ProtectedButton = ({ 
  permission, 
  onClick, 
  children,
  className,
  ...props 
}) => {
  const { checkPermission } = usePermissions();
  
  if (!checkPermission(permission)) {
    return null; // No renderiza el botón si no tiene permiso
  }
  
  return (
    <button onClick={onClick} className={className} {...props}>
      {children}
    </button>
  );
};
```

### 🎯 Modo Desarrollador

```javascript
// config/dev.js
export const DEV_CONFIG = {
  ENABLED: true, // Cambiar a false en producción
  MOCK_DATA: true,
  DEFAULT_USER: {
    username: 'admin',
    password: 'admin',
  },
};

// Uso en componentes:
if (DEV_CONFIG.ENABLED) {
  // Cargar datos mock
  setProductos(MOCK_PRODUCTOS);
} else {
  // Llamar API real
  const response = await productosAPI.getAll();
  setProductos(response.data.results);
}
```

---

## 🔄 Flujos de Trabajo Principales

### **1. Flujo de Requisición de Medicamentos**

```
1. CENTRO_USER crea nueva requisición (estado: borrador)
   ↓
2. Agrega productos con cantidades solicitadas
   ↓
3. Guarda como borrador (puede editar)
   ↓
4. Envía requisición (estado: enviada)
   ↓
5. FARMACIA_ADMIN revisa requisición
   ↓
6a. AUTORIZA (estado: autorizada)
    - Puede modificar cantidades autorizadas
    - Sistema crea movimientos SALIDA
    ↓
6b. RECHAZA (estado: rechazada)
    - Debe proporcionar motivo
    ↓
7. FARMACIA_ADMIN marca como surtida (estado: surtida)
   - Se descontan del inventario de farmacia
   - Se agregan al inventario del centro
```

### **2. Flujo de Control de Inventario**

```
ENTRADAS:
- Compra de productos → Crear lote → Movimiento ENTRADA
- Devolución de centro → Movimiento ENTRADA

SALIDAS:
- Requisición autorizada → Movimiento SALIDA
- Merma/caducidad → Movimiento MERMA
- Ajuste de inventario → Movimiento AJUSTE

ALERTAS:
- Lote con ≤7 días para caducar → Alerta CRÍTICA
- Lote con ≤30 días → Alerta PRÓXIMO
- Stock actual < stock_minimo → Alerta STOCK CRÍTICO
```

### **3. Flujo de Auditoría**

```
1. Usuario realiza acción (CREATE/UPDATE/DELETE)
   ↓
2. Signal post_save/post_delete captura evento
   ↓
3. Se crea registro en AuditoriaLog:
   - Usuario
   - Acción
   - Módulo
   - Datos anteriores (JSON)
   - Datos nuevos (JSON)
   - IP, user_agent
   ↓
4. Disponible en página de Auditoría
   - Filtrable por usuario, módulo, acción, fecha
   - Ver detalles completos (antes/después)
```

---

## 🛠️ Scripts y Utilidades

### **Backend Scripts**

```bash
# Crear superusuario
python manage.py createsuperuser

# Migraciones
python manage.py makemigrations
python manage.py migrate

# Poblar base de datos (script personalizado)
python backend/poblar_db.py

# Resetear base de datos
python backend/reset_db.py

# Inicializar base de datos
python backend/init_db.py

# Verificar base de datos
python backend/verificar_db.py

# Crear admin rápido
python backend/crear_admin.py

# Ejecutar servidor
python manage.py runserver

# Ejecutar tests
python manage.py test
```

### **Frontend Scripts**

```bash
# Instalar dependencias
npm install

# Ejecutar en desarrollo
npm run dev

# Build para producción
npm run build

# Preview de build
npm run preview
```

### **Script de Corrección de Encoding**

```bash
# Corregir todos los encoding errors
python fix_encoding.py
```

---

## 📊 Datos de Ejemplo (Mock Data)

### **Productos Mock**
```javascript
const MOCK_PRODUCTOS = [
  {
    id: 1,
    clave: 'MED-001',
    descripcion: 'Paracetamol 500mg',
    presentacion: 'Caja con 20 tabletas',
    unidad_medida: 'pieza',
    precio_unitario: 50.00,
    stock_minimo: 100,
    stock_actual: 500,
    categoria: 'ANALGESICO',
  },
  // ... más productos
];
```

### **Roles de Usuario**
```
SUPERUSER: Acceso total al sistema
FARMACIA_ADMIN: Gestión de productos, lotes, autorizar requisiciones
CENTRO_USER: Crear requisiciones, ver inventario de su centro
VISTA_USER: Solo lectura
```

---

## 🚀 Despliegue y Hosting

### **Recomendaciones de Hosting Gratuito**

**Backend (Django):**
1. **Render.com** (Recomendado)
   - Free tier con PostgreSQL incluido
   - Deploy automático desde Git
   - HTTPS gratuito

2. **Railway**
   - $5 crédito mensual gratis
   - Deploy fácil

3. **PythonAnywhere**
   - Tier gratuito con limitaciones

**Frontend (React):**
1. **Vercel** (Recomendado)
   - Deploy automático
   - CDN global
   - HTTPS gratuito

2. **Netlify**
   - Similar a Vercel
   - CI/CD integrado

3. **GitHub Pages**
   - Gratis para repos públicos

**Base de Datos:**
- Render PostgreSQL (512 MB gratis)
- ElephantSQL (20 MB gratis)
- Supabase (500 MB gratis)

### **Variables de Entorno (.env)**

**Backend:**
```env
DEBUG=False
SECRET_KEY=tu-secret-key-super-segura
DATABASE_URL=postgresql://user:pass@host:5432/dbname
ALLOWED_HOSTS=tu-dominio.com
CORS_ALLOWED_ORIGINS=https://tu-frontend.vercel.app
```

**Frontend:**
```env
VITE_API_URL=https://tu-backend.onrender.com/api
```

---

## 📚 Documentación Adicional

### **Tecnologías Utilizadas**

**Backend:**
- Python 3.10+
- Django 4.2+
- Django REST Framework 3.14+
- djangorestframework-simplejwt 5.5+
- django-cors-headers
- WhiteNoise (archivos estáticos)
- openpyxl (Excel)
- reportlab (PDF)

**Frontend:**
- React 18.2+
- Vite 5.0+
- React Router 6.20+
- Axios 1.6+
- Tailwind CSS 3.4+
- React Hot Toast 2.4+
- React Icons 4.12+

**Base de Datos:**
- SQLite (desarrollo)
- PostgreSQL (producción recomendada)

### **Convenciones de Código**

**Python (Backend):**
- PEP 8 style guide
- snake_case para funciones y variables
- PascalCase para clases
- Docstrings en funciones importantes

**JavaScript (Frontend):**
- camelCase para funciones y variables
- PascalCase para componentes React
- Componentes funcionales con hooks
- Destructuring de props

### **Seguridad**

- Tokens JWT con expiración
- CORS configurado correctamente
- Validación de datos en backend
- Sanitización de inputs en frontend
- Permisos por rol en cada endpoint
- Auditoría de todas las acciones
- HTTPS obligatorio en producción

---

## 📞 Información de Contacto

**Proyecto:** Sistema de Control de Abasto - Farmacia Penitenciaria  
**Cliente:** Subsecretaría del Sistema Penitenciario - Estado de México  
**Repositorio:** farmacia_penitenciaria  
**Branch:** dev

---

## ✅ Checklist de Funcionalidades

### Backend
- [x] Autenticación JWT
- [x] CRUD Productos
- [x] CRUD Lotes
- [x] CRUD Requisiciones
- [x] CRUD Centros
- [x] CRUD Usuarios
- [x] Sistema de permisos por rol
- [x] Auditoría completa
- [x] Trazabilidad de productos/lotes
- [x] Importación Excel
- [x] Exportación Excel
- [x] Generación de reportes
- [x] Alertas de caducidad
- [x] Control de stock

### Frontend
- [x] Login con JWT
- [x] Dashboard con KPIs
- [x] Gestión de productos
- [x] Gestión de lotes
- [x] Gestión de requisiciones
- [x] Gestión de centros
- [x] Gestión de usuarios
- [x] Auditoría con filtros
- [x] Trazabilidad
- [x] Generación de reportes
- [x] Importación Excel
- [x] Exportación Excel
- [x] Sistema de permisos UI
- [x] Modo desarrollador
- [x] Responsive design
- [x] Notificaciones toast

---

**Última actualización:** 19 de noviembre de 2025  
**Versión del documento:** 1.0
