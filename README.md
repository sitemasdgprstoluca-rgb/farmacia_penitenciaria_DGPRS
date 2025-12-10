# Sistema de Farmacia Penitenciaria

Sistema de Control de Abasto de Medicamentos para instituciones penitenciarias.

## 🏗️ Stack Tecnológico

### Backend
- **Framework**: Django 5.2 + Django REST Framework
- **Autenticación**: JWT (SimpleJWT)
- **Base de datos**: PostgreSQL (producción) / SQLite (desarrollo)
- **Generación de reportes**: ReportLab (PDF), OpenPyXL (Excel)

### Frontend
- **Framework**: React 18 + Vite
- **Estilos**: TailwindCSS
- **Gráficos**: Recharts
- **Routing**: React Router DOM

## 📁 Estructura del Proyecto

```
farmacia_penitenciaria/
├── backend/                 # API Django REST
│   ├── config/             # Configuración Django
│   ├── core/               # Modelos y lógica principal
│   ├── inventario/         # ViewSets de inventario
│   └── static/             # Archivos estáticos
├── inventario-front/       # Frontend React
│   ├── src/
│   │   ├── components/     # Componentes reutilizables
│   │   ├── pages/          # Páginas/vistas
│   │   ├── services/       # Servicios de API
│   │   └── context/        # Contextos React
│   └── public/
├── infrastructure/         # Scripts de infraestructura
└── render.yaml            # Configuración para Render
```

## 🚀 Inicio Rápido

### Prerrequisitos
- Python 3.12+
- Node.js 18+
- PostgreSQL (para producción)

### Backend

```bash
# Navegar al directorio backend
cd backend

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt

# Copiar archivo de configuración
cp .env.example .env
# Editar .env con tus configuraciones

# Aplicar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Iniciar servidor de desarrollo
python manage.py runserver
```

### Frontend

```bash
# Navegar al directorio frontend
cd inventario-front

# Instalar dependencias
npm install

# Copiar archivo de configuración
cp .env.example .env
# Editar .env con la URL del API

# Iniciar servidor de desarrollo
npm run dev
```

## 🧪 Ejecutar Tests

### Backend
```bash
cd backend
DEBUG=True python -m pytest
```

### Con Cobertura
```bash
cd backend
DEBUG=True python -m pytest --cov=core --cov=inventario --cov-report=html --cov-report=term-missing
# Reporte HTML generado en backend/htmlcov/index.html
```

### Matriz de Cobertura de Tests

| Módulo | Archivo | Cobertura | Prioridad |
|--------|---------|-----------|-----------|
| **core** | `models.py` | ✅ Alta | Crítico |
| **core** | `permissions.py` | ✅ Alta | Crítico |
| **core** | `views.py` | ✅ Alta | Crítico |
| **inventario** | `services/state_machine.py` | ✅ Alta | Crítico |
| **inventario** | `services/stock_service.py` | ✅ Alta | Crítico |
| **inventario** | `views.py` | ✅ Media | Alto |
| **core** | `serializers.py` | ✅ Media | Medio |
| **core** | `middleware.py` | ⚠️ Baja | Medio |

### Áreas Críticas Cubiertas
- **Máquina de estados**: Transiciones válidas/inválidas, bypass bloqueados
- **Permisos por rol**: RBAC para cada endpoint y acción
- **Validaciones de inventario**: Stock insuficiente, lotes vencidos
- **Segregación de funciones**: Validación de acciones incompatibles

### Ejecutar Tests Específicos
```bash
# Tests de state machine
DEBUG=True python -m pytest core/tests/test_state_machine.py -v

# Tests de permisos
DEBUG=True python -m pytest core/tests/test_permissions.py -v

# Tests de inventario
DEBUG=True python -m pytest inventario/tests/ -v
```

### Frontend
```bash
cd inventario-front
npm test
```

## 🔐 Variables de Entorno

### Backend (`.env`)

| Variable | Requerida | Default | Descripción |
|----------|-----------|---------|-------------|
| `SECRET_KEY` | ✅ Sí | - | Clave secreta para criptografía. **DEBE** ser única en producción. Generar con `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DEBUG` | No | `False` | Modo debug. **NUNCA** usar `True` en producción |
| `ALLOWED_HOSTS` | ✅ Sí (prod) | `localhost,127.0.0.1` | Lista de hosts permitidos separados por coma |
| `DATABASE_URL` | ✅ Sí (prod) | SQLite local | URL de conexión PostgreSQL (ej: `postgres://user:pass@host:5432/db`) |
| `CORS_ALLOWED_ORIGINS` | No | `http://localhost:5173` | Orígenes CORS permitidos separados por coma |
| `CSRF_TRUSTED_ORIGINS` | No | `http://localhost:5173` | Orígenes confiables para CSRF separados por coma |
| `SECURE_SSL_REDIRECT` | No | `False` | Redirigir HTTP a HTTPS. Usar `True` en producción |
| `SECURE_HSTS_SECONDS` | No | `0` | Segundos para HSTS. Recomendado `31536000` (1 año) en producción |
| `SESSION_COOKIE_SECURE` | No | `False` | Cookies solo por HTTPS. Usar `True` en producción |
| `CSRF_COOKIE_SECURE` | No | `False` | Cookie CSRF solo por HTTPS. Usar `True` en producción |
| `SUPABASE_URL` | ✅ Sí (prod) | - | URL del proyecto Supabase para almacenamiento de documentos |
| `SUPABASE_KEY` | ✅ Sí (prod) | - | API Key de Supabase (usar `service_role` para backend) |
| `SUPABASE_STORAGE_BUCKET` | No | `documentos` | Nombre del bucket para documentos de lotes |

#### Ejemplo `.env` Desarrollo
```env
SECRET_KEY=dev-only-key-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173
CSRF_TRUSTED_ORIGINS=http://localhost:5173
```

#### Ejemplo `.env` Producción
```env
SECRET_KEY=<clave-generada-aleatoriamente-64-chars>
DEBUG=False
ALLOWED_HOSTS=farmacia.ejemplo.gob.mx,api.farmacia.ejemplo.gob.mx
DATABASE_URL=postgres://farmacia_user:secure_password@db.render.com:5432/farmacia_prod
CORS_ALLOWED_ORIGINS=https://farmacia.ejemplo.gob.mx
CSRF_TRUSTED_ORIGINS=https://farmacia.ejemplo.gob.mx
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
# Supabase Storage para documentos de lotes
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_STORAGE_BUCKET=documentos
```

### Frontend (`.env`)

| Variable | Requerida | Default | Descripción |
|----------|-----------|---------|-------------|
| `VITE_API_BASE_URL` | ✅ Sí | - | URL base del API backend (incluir `/api/` al final) |

#### Ejemplo Frontend
```env
# Desarrollo
VITE_API_BASE_URL=http://127.0.0.1:8000/api/

# Producción
VITE_API_BASE_URL=https://api.farmacia.ejemplo.gob.mx/api/
```

### Notas de Seguridad
- **NUNCA** commitear archivos `.env` al repositorio
- Usar gestores de secretos en producción (AWS Secrets Manager, HashiCorp Vault, etc.)
- Rotar `SECRET_KEY` periódicamente (requiere invalidar sesiones activas)
- En Render, configurar variables en el Dashboard, no en archivos

## 📦 Despliegue

El proyecto está configurado para desplegarse en **Render**. Ver `render.yaml` para la configuración de infraestructura.

### Pasos:
1. Conectar repositorio en Render Dashboard
2. Configurar variables de entorno (DATABASE_URL, SECRET_KEY, etc.)
3. Render detectará `render.yaml` automáticamente

## 📖 Documentación Adicional

- [Arquitectura del Sistema](ARQUITECTURA.md) - Documentación técnica detallada
- [API Docs](http://localhost:8000/api/docs/) - Swagger/OpenAPI (cuando el servidor está corriendo)

## 👥 Roles del Sistema

| Rol | Descripción |
|-----|-------------|
| `admin_sistema` | Administrador global |
| `farmacia` | Usuario de farmacia central |
| `centro` | Usuario de centro penitenciario |
| `vista` | Solo consulta (lectura) |

## 📝 Licencia

Este proyecto es software propietario para uso institucional.
