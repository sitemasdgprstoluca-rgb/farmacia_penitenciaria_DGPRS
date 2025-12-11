# Checklist de Seguridad para Producción

## Prerrequisitos Obligatorios

### 1. Variables de Entorno Críticas

```bash
# ⚠️ OBLIGATORIAS - Sin estas el servidor NO arranca
SECRET_KEY=<mínimo 50 caracteres, generar con: python -c "import secrets; print(secrets.token_urlsafe(64))">
DATABASE_URL=postgresql://...
ALLOWED_HOSTS=tu-dominio.com,tu-backend.onrender.com
CORS_ALLOWED_ORIGINS=https://tu-frontend.com
CSRF_TRUSTED_ORIGINS=https://tu-frontend.com,https://tu-backend.com
```

### 2. HTTPS y Cookies Seguras

```bash
# Configuración de producción (DEBUG=False las activa automáticamente)
ENFORCE_HTTPS=True
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
```

### 3. Rate Limiting

```bash
# Protección contra fuerza bruta
RATE_LIMIT_ENABLED=True
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
RATE_LIMIT_LOGIN_REQUESTS=5
RATE_LIMIT_LOGIN_WINDOW=300
```

### 4. Content Security Policy

```bash
CSP_ENABLED=True
CSP_DEFAULT_SRC='self'
CSP_SCRIPT_SRC='self'
CSP_FRAME_ANCESTORS='none'
```

---

## Verificación Automática

El sistema valida automáticamente al arrancar:

1. ✅ `SECRET_KEY` no vacía y mínimo 50 caracteres
2. ✅ `SECRET_KEY` no contiene "insecure" o "dev"
3. ✅ `DATABASE_URL` es PostgreSQL (no SQLite)
4. ✅ `ALLOWED_HOSTS` configurado (no wildcard `*`)
5. ✅ `CORS_ALLOWED_ORIGINS` configurado
6. ✅ `CSRF_TRUSTED_ORIGINS` configurado

### Errores que Bloquean el Arranque

```
❌ ERRORES CRÍTICOS DE SEGURIDAD (NO BYPASSEABLE)
==========================================================
  1. SECRET_KEY: CRÍTICO - Variable no configurada en producción.
```

---

## Headers de Seguridad Automáticos

### Siempre Activos
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Permissions-Policy: geolocation=(), microphone=(), camera=()`

### Con `CSP_ENABLED=True`
- `Content-Security-Policy: default-src 'self'; script-src 'self'; ...`

### Con `ENFORCE_HTTPS=True`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`

---

## Comandos de Verificación

```bash
# Verificar esquema de BD
python manage.py verify_schema --strict

# Verificar configuración de seguridad
python manage.py check --deploy

# Generar SQL de constraints
python manage.py verify_schema --sql
```

---

## Configuración en Render

### Variables de Entorno en Dashboard

| Variable | Valor |
|----------|-------|
| `SECRET_KEY` | (generar única) |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `tu-app.onrender.com` |
| `DATABASE_URL` | (desde Supabase) |
| `CORS_ALLOWED_ORIGINS` | `https://tu-frontend.onrender.com` |
| `CSRF_TRUSTED_ORIGINS` | `https://tu-frontend.onrender.com` |
| `ENFORCE_HTTPS` | `True` |
| `RENDER` | `True` (auto-detectado) |

### Build Command
```bash
./build.sh
```

### Start Command
```bash
gunicorn config.wsgi:application
```

---

## Checklist Pre-Despliegue

- [ ] SECRET_KEY única generada
- [ ] DATABASE_URL apunta a PostgreSQL de producción
- [ ] ALLOWED_HOSTS tiene solo dominios de producción
- [ ] CORS_ALLOWED_ORIGINS tiene URL del frontend
- [ ] CSRF_TRUSTED_ORIGINS configurado
- [ ] ENFORCE_HTTPS=True
- [ ] RATE_LIMIT_ENABLED=True
- [ ] CSP_ENABLED=True
- [ ] `python manage.py verify_schema --strict` pasa
- [ ] `python manage.py check --deploy` sin errores críticos
- [ ] Constraints de BD aplicados (ver SQL_MIGRATIONS.md)

---

## Referencia Rápida

### Generar SECRET_KEY
```python
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### Verificar Configuración Local
```bash
DEBUG=False python manage.py check --deploy
```

### Variables que NO deben estar en producción
```bash
DEBUG=True  # ❌ NUNCA
SKIP_SECURITY_VALIDATION=True  # ❌ Ignorada si DEBUG=False
ALLOWED_HOSTS=*  # ❌ Bloqueado
SECRET_KEY=django-insecure-...  # ❌ Bloqueado
```
