# Backend - Sistema de Farmacia Penitenciaria

Django REST Framework API para gestión de inventario farmacéutico en centros penitenciarios.

## 🚀 Inicio Rápido (Desarrollo Local)

### 1. Configurar Variables de Entorno

```bash
# Copiar archivo de ejemplo
cp .env.example .env

# El archivo .env ya incluye configuración para desarrollo:
# - DEBUG=True
# - SECRET_KEY con valor de desarrollo
# - SQLite como base de datos
# - CORS configurado para localhost:5173
```

**IMPORTANTE**: El archivo `.env` creado es solo para desarrollo local. Nunca lo subas al repositorio (ya está en `.gitignore`).

### 2. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 3. Aplicar Migraciones

```bash
python manage.py migrate
```

### 4. Crear Superusuario (Opcional)

```bash
python manage.py createsuperuser
```

O usar el script:
```bash
python crear_admin.py
```

### 5. Iniciar Servidor de Desarrollo

```bash
python manage.py runserver
```

El backend estará disponible en: `http://localhost:8000`

## 🧪 Ejecutar Tests

```bash
# Todos los tests
pytest

# Tests específicos
pytest core/tests/
pytest inventario/tests/

# Con cobertura
pytest --cov=core --cov=inventario
```

**Nota**: Los tests no requieren configurar `SECRET_KEY` manualmente. El sistema lo detecta automáticamente y usa SQLite en memoria.

## 🔐 Configuración de Producción

Para desplegar en producción (Render, AWS, etc.):

1. **Generar SECRET_KEY segura**:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(64))"
   ```

2. **Configurar variables de entorno** en tu plataforma:
   ```bash
   SECRET_KEY=<clave-generada-arriba>
   DEBUG=False
   ALLOWED_HOSTS=tu-dominio.com
   DATABASE_URL=postgresql://user:pass@host:5432/dbname
   ENFORCE_HTTPS=True
   ```

3. **Verificar configuración**:
   ```bash
   python manage.py check --deploy
   ```

## 📁 Estructura de Variables de Entorno

| Variable | Desarrollo | Producción | Descripción |
|----------|-----------|-----------|-------------|
| `SECRET_KEY` | `django-insecure-dev-key-...` | **REQUERIDO** | Clave secreta Django (min. 50 chars) |
| `DEBUG` | `True` | `False` | Modo depuración |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | `tu-dominio.com` | Hosts permitidos |
| `DATABASE_URL` | _(vacío = SQLite)_ | `postgresql://...` | URL de PostgreSQL |
| `ENFORCE_HTTPS` | `False` | `True` | Forzar HTTPS |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173` | `https://tu-frontend.com` | Orígenes CORS |

## 🔍 Validaciones de Seguridad

El backend incluye validaciones estrictas en producción (`DEBUG=False`):

- ✅ `SECRET_KEY` debe estar configurada y ser segura (min. 50 chars)
- ✅ `ALLOWED_HOSTS` debe estar configurado explícitamente (no `*`)
- ✅ `DATABASE_URL` debe ser PostgreSQL (no SQLite)
- ✅ `ENFORCE_HTTPS` debe ser `True`

Estas validaciones se **omiten automáticamente** para:
- Modo desarrollo (`DEBUG=True`)
- Tests con pytest (`pytest` detectado)
- Entornos CI (`CI=true`)
- Comandos offline (`migrate`, `collectstatic`, etc.)

## 🛠️ Comandos Útiles

```bash
# Verificar configuración
python manage.py check

# Verificar seguridad para producción
python manage.py check --deploy

# Ejecutar tests e2e
python tests_e2e.py

# Verificar integridad de base de datos
python verificar_integridad.py

# Verificar buenas prácticas
python verificar_buenas_practicas.py
```

## 📝 Notas Importantes

1. **SECRET_KEY en Desarrollo**: El archivo `.env.example` incluye una SECRET_KEY para desarrollo. Esto es seguro porque:
   - Está claramente marcada como "insecure-dev-key"
   - Solo funciona con `DEBUG=True`
   - Nunca debe usarse en producción

2. **Base de Datos en Desarrollo**: Por defecto usa SQLite (`db.sqlite3`). Para usar PostgreSQL en local, configura `DATABASE_URL` en `.env`.

3. **Tests Aislados**: Los tests siempre usan SQLite en memoria, independiente de la configuración en `.env`.

## 🔗 Recursos

- [Django Settings Documentation](https://docs.djangoproject.com/en/stable/ref/settings/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Deployment Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
