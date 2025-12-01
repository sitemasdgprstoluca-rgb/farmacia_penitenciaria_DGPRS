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

### Frontend
```bash
cd inventario-front
npm test
```

## 🔐 Variables de Entorno

### Backend (`.env`)
```env
SECRET_KEY=tu-clave-secreta
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173
CSRF_TRUSTED_ORIGINS=http://localhost:5173
```

### Frontend (`.env`)
```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api/
```

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
