from pathlib import Path
from decouple import config, Csv
from datetime import timedelta
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY - definir DEBUG primero para usarlo en logging
SECRET_KEY = config('SECRET_KEY', default='' if not config('DEBUG', default=False, cast=bool) else 'dev-only-insecure-key-not-for-production')
DEBUG = config('DEBUG', default=False, cast=bool)

# Logging defaults (can be overridden by env)
LOG_LEVEL = config('LOG_LEVEL', default='INFO')
# ISS-004: En producción (Render, containers) usar stdout por defecto ya que el disco es efímero
# Detectar automáticamente entornos containerizados
_is_container = config('RENDER', default=False, cast=bool) or config('DYNO', default='') or config('KUBERNETES_SERVICE_HOST', default='')
LOG_TO_STDOUT = config('LOG_TO_STDOUT', default=_is_container or not DEBUG, cast=bool)
LOG_FILE = config('LOG_FILE', default=str(BASE_DIR / 'logs' / 'django.log'))

# ISS-004: Solo crear directorio de logs si no usamos stdout y manejamos errores
if not LOG_TO_STDOUT:
    try:
        Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError) as e:
        # Si no podemos crear el directorio, forzar stdout
        import sys
        print(f"[WARNING] No se puede crear directorio de logs ({e}), usando stdout", file=sys.stderr)
        LOG_TO_STDOUT = True

# ═══════════════════════════════════════════════════════════
# VALIDACIÓN ESTRICTA EN PRODUCCIÓN
# ═══════════════════════════════════════════════════════════
# ISS-002: Modo mantenimiento para permitir comandos administrativos
# sin bloquear por validaciones de entorno (migraciones, collectstatic, etc.)
MAINTENANCE_MODE = config('MAINTENANCE_MODE', default=False, cast=bool)
SKIP_SECURITY_VALIDATION = config('SKIP_SECURITY_VALIDATION', default=False, cast=bool)

# ISS-004: Detectar comandos de gestión de Django para permitir operaciones offline
# Esto evita bloqueos en migraciones, collectstatic, y pipelines de CI
import sys
_is_management_command = len(sys.argv) > 1 and sys.argv[0].endswith('manage.py')
_offline_commands = {'migrate', 'makemigrations', 'collectstatic', 'check', 'showmigrations', 
                     'dbshell', 'shell', 'createsuperuser', 'test', 'flush', 'dumpdata', 'loaddata'}
_is_offline_command = _is_management_command and len(sys.argv) > 1 and sys.argv[1] in _offline_commands

# Variables de entorno para CI/CD pipelines
RUNNING_MIGRATIONS = config('RUNNING_MIGRATIONS', default=False, cast=bool)
RUNNING_COLLECTSTATIC = config('RUNNING_COLLECTSTATIC', default=False, cast=bool)
CI_ENVIRONMENT = config('CI', default=False, cast=bool) or config('CI_ENVIRONMENT', default=False, cast=bool)

# Determinar si debemos saltar validación
_skip_validation = (
    MAINTENANCE_MODE or 
    SKIP_SECURITY_VALIDATION or 
    _is_offline_command or 
    RUNNING_MIGRATIONS or 
    RUNNING_COLLECTSTATIC or
    CI_ENVIRONMENT
)

# Solo validar en producción Y cuando no estamos en modo mantenimiento/offline
if not DEBUG and not _skip_validation:
    # Lista de verificaciones de seguridad para producción
    _security_errors = []
    
    # 1. SECRET_KEY debe ser segura
    if not SECRET_KEY or SECRET_KEY == 'dev-only-insecure-key-not-for-production':
        _security_errors.append('SECRET_KEY: Variable no configurada. Genera una con: python -c "import secrets; print(secrets.token_urlsafe(64))"')
    elif len(SECRET_KEY) < 50:
        _security_errors.append(f'SECRET_KEY: Muy corta ({len(SECRET_KEY)} chars). Mínimo 50 caracteres.')
    elif 'insecure' in SECRET_KEY.lower() or 'dev' in SECRET_KEY.lower():
        _security_errors.append('SECRET_KEY: Parece ser una clave de desarrollo. Usa una clave segura.')
    
    # 2. DATABASE_URL debe ser PostgreSQL
    _db_url = config('DATABASE_URL', default='')
    if not _db_url:
        _security_errors.append('DATABASE_URL: Variable no configurada. Requerida para producción.')
    elif 'sqlite' in _db_url.lower():
        _security_errors.append('DATABASE_URL: SQLite no permitido en producción. Usa PostgreSQL.')
    elif not _db_url.startswith(('postgres://', 'postgresql://')):
        _security_errors.append('DATABASE_URL: Debe ser una URL de PostgreSQL válida.')
    
    # 3. ALLOWED_HOSTS debe estar configurado
    _allowed_hosts = config('ALLOWED_HOSTS', default='')
    if not _allowed_hosts or _allowed_hosts in ('localhost', '127.0.0.1', '*'):
        _security_errors.append('ALLOWED_HOSTS: Configura los dominios de producción (no localhost ni *).')
    
    # 4. CORS_ALLOWED_ORIGINS debe estar configurado
    _cors_origins = config('CORS_ALLOWED_ORIGINS', default='')
    if not _cors_origins:
        _security_errors.append('CORS_ALLOWED_ORIGINS: Variable no configurada. Requerida para frontend.')
    elif 'localhost' in _cors_origins and 'onrender.com' not in _cors_origins:
        _security_errors.append('CORS_ALLOWED_ORIGINS: Contiene localhost pero no dominios de producción.')
    
    # 5. CSRF_TRUSTED_ORIGINS debe estar configurado
    _csrf_origins = config('CSRF_TRUSTED_ORIGINS', default='')
    if not _csrf_origins:
        _security_errors.append('CSRF_TRUSTED_ORIGINS: Variable no configurada. Requerida para protección CSRF.')
    
    # Si hay errores, mostrarlos todos juntos y fallar
    if _security_errors:
        _error_msg = '\n\n' + '=' * 70 + '\n'
        _error_msg += '❌ ERRORES DE CONFIGURACIÓN DE PRODUCCIÓN\n'
        _error_msg += '=' * 70 + '\n\n'
        for i, err in enumerate(_security_errors, 1):
            _error_msg += f'  {i}. {err}\n\n'
        _error_msg += '=' * 70 + '\n'
        _error_msg += 'Configura las variables de entorno antes de desplegar.\n'
        _error_msg += '=' * 70 + '\n'
        raise ValueError(_error_msg)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())
# Hardened security toggles (enable in producción)
ENFORCE_HTTPS = config('ENFORCE_HTTPS', default=not DEBUG, cast=bool)
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=ENFORCE_HTTPS, cast=bool)
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000 if ENFORCE_HTTPS else 0, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=ENFORCE_HTTPS, cast=bool)
SECURE_HSTS_PRELOAD = config('SECURE_HSTS_PRELOAD', default=ENFORCE_HTTPS, cast=bool)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=ENFORCE_HTTPS, cast=bool)
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=ENFORCE_HTTPS, cast=bool)
CSRF_COOKIE_SAMESITE = config('CSRF_COOKIE_SAMESITE', default='Lax')
SESSION_COOKIE_SAMESITE = config('SESSION_COOKIE_SAMESITE', default='Lax')
SECURE_REFERRER_POLICY = config('SECURE_REFERRER_POLICY', default='same-origin')

# ═══════════════════════════════════════════════════════════
# CONTENT SECURITY POLICY (CSP) & ADDITIONAL HEADERS
# ═══════════════════════════════════════════════════════════
# X-Frame-Options: Ya manejado por XFrameOptionsMiddleware (DENY por defecto)
X_FRAME_OPTIONS = 'DENY'

# Content-Security-Policy: Configurable vía variable de entorno
# Ejemplo restrictivo para producción (ajustar según necesidades del frontend):
# default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self' https://api.tudominio.com
CSP_ENABLED = config('CSP_ENABLED', default=not DEBUG, cast=bool)
CSP_DEFAULT_SRC = config('CSP_DEFAULT_SRC', default="'self'")
CSP_SCRIPT_SRC = config('CSP_SCRIPT_SRC', default="'self'")
CSP_STYLE_SRC = config('CSP_STYLE_SRC', default="'self' 'unsafe-inline'")  # unsafe-inline para Tailwind
CSP_IMG_SRC = config('CSP_IMG_SRC', default="'self' data: blob:")
CSP_FONT_SRC = config('CSP_FONT_SRC', default="'self'")
CSP_CONNECT_SRC = config('CSP_CONNECT_SRC', default="'self'")
CSP_FRAME_ANCESTORS = config('CSP_FRAME_ANCESTORS', default="'none'")

# Secure browser features
SECURE_CONTENT_TYPE_NOSNIFF = True  # X-Content-Type-Options: nosniff
SECURE_BROWSER_XSS_FILTER = True    # X-XSS-Protection (legacy pero útil)

# INSTALLED APPS
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',  # ✅ AGREGADO: Soporte para blacklist de tokens
    'corsheaders',
    'drf_spectacular',
    'django_filters',
    
    # Local apps
    'core',
    'inventario',
    # 'farmacia' - ELIMINADO: App legacy sin uso, funcionalidad migrada a core/inventario
]

# MIDDLEWARE
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # CORS antes de CommonMiddleware
    'core.middleware.CurrentRequestMiddleware',  # Para auditoría (request en signals)
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.SecurityHeadersMiddleware',  # CSP y headers de seguridad adicionales
]


ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Python 3.14 compatibility: Disable template debugging during tests
import sys
if 'test' in sys.argv:
    TEMPLATES[0]['OPTIONS']['debug'] = False
    # Disable template rendering capture to avoid Python 3.14 copy() bug
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
    }

WSGI_APPLICATION = 'config.wsgi.application'

# DATABASE
DATABASE_URL = config('DATABASE_URL', default=None)

# Forzar SQLite para tests (ignora DATABASE_URL)
import sys
TESTING = 'test' in sys.argv or 'pytest' in sys.modules

if TESTING:
    # Tests siempre usan SQLite en memoria para velocidad y aislamiento
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }
    # Desactivar password hashers lentos para acelerar tests
    PASSWORD_HASHERS = [
        'django.contrib.auth.hashers.MD5PasswordHasher',
    ]
elif DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=config('DB_CONN_MAX_AGE', default=600, cast=int),
            ssl_require=ENFORCE_HTTPS
        )
    }
else:
    # Solo desarrollo local - NUNCA en producción
    if not DEBUG:
        raise ValueError('ERROR: DATABASE_URL requerido en producción')
    DATABASES = {
        'default': {
            'ENGINE': config('DB_ENGINE', default='django.db.backends.sqlite3'),
            'NAME': config('DB_NAME', default=str(BASE_DIR / 'db.sqlite3')),
            'USER': config('DB_USER', default=''),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default=''),
            'PORT': config('DB_PORT', default=''),
            'OPTIONS': {
                'timeout': 30,  # Timeout en segundos para SQLite
            },
        }
    }

# CUSTOM USER MODEL
AUTH_USER_MODEL = 'core.User'

# PASSWORD VALIDATION
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# INTERNATIONALIZATION
LANGUAGE_CODE = 'es-mx'
TIME_ZONE = 'America/Mexico_City'
USE_I18N = True
USE_TZ = True

# STATIC FILES
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',  # Incluye backend/static/ en collectstatic (fondo_institucional.png, etc.)
]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ═══════════════════════════════════════════════════════════
# REST FRAMEWORK CONFIGURATION
# ═══════════════════════════════════════════════════════════
REST_FRAMEWORK = {
    # ISS-001: Solo JWT para API - SessionAuthentication removida para evitar
    # vulnerabilidades CSRF (csrf_exempt ya no es necesario en ViewSets)
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'core.exceptions.custom_exception_handler',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': config('THROTTLE_RATE_ANON', default='200/hour'),
        'user': config('THROTTLE_RATE_USER', default='1000/hour'),
        'import': config('THROTTLE_RATE_IMPORT', default='50/day'),
        'login': config('THROTTLE_RATE_LOGIN', default='5/min'),  # ✅ Rate limit para login
        'password_change': config('THROTTLE_RATE_PASSWORD_CHANGE', default='3/min'),  # ✅ Rate limit para cambio de password
    },
}

# ═══════════════════════════════════════════════════════════
# DESACTIVAR THROTTLING EN TESTS
# ═══════════════════════════════════════════════════════════
if TESTING:
    REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []
    REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
        'anon': None,
        'user': None,
        'import': None,
        'login': None,
        'password_change': None,
    }

# ═══════════════════════════════════════════════════════════
# SIMPLE JWT CONFIGURATION
# ═══════════════════════════════════════════════════════════
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=config('JWT_ACCESS_TOKEN_LIFETIME_HOURS', default=1, cast=int)),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=config('JWT_REFRESH_TOKEN_LIFETIME_DAYS', default=7, cast=int)),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

# ═══════════════════════════════════════════════════════════
# SEGURIDAD DE TOKENS JWT - ESTRATEGIA Y CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════
# 
# DECISIÓN DE ARQUITECTURA: TOKENS EN LOCALSTORAGE
# =========================================================
# Se decidió usar localStorage para tokens JWT por las siguientes razones:
#
# VENTAJAS:
# - Simplicidad de implementación en SPA (React)
# - Sin problemas de CORS con cookies
# - Persistencia entre pestañas del navegador
# - Compatible con cualquier backend (portabilidad)
#
# RIESGOS DOCUMENTADOS:
# - Vulnerable a ataques XSS (si hay código malicioso inyectado,
#   puede leer tokens de localStorage)
# - Los tokens son accesibles desde JavaScript
#
# MITIGACIONES IMPLEMENTADAS:
# 1. Tokens de corta duración (1 hora por defecto) - reduce ventana de ataque
# 2. Refresh tokens con rotación automática y blacklist - limita reutilización
# 3. HTTPS forzado en producción - previene MITM
# 4. CSP headers para mitigar XSS - limita scripts externos
# 5. Rate limiting en endpoints de autenticación - previene fuerza bruta
# 6. Validación estricta de inputs en frontend y backend
# 7. Escapado de HTML en todas las respuestas (DRF por defecto)
# 8. Auditoría de acciones sensibles (trazabilidad)
#
# NIVEL DE RIESGO: BAJO-MEDIO
# Para una aplicación interna de farmacia penitenciaria con usuarios
# controlados, el riesgo es aceptable con las mitigaciones implementadas.
#
# ALTERNATIVA (COOKIES HTTPONLY):
# =========================================================
# PARA MIGRAR A COOKIES HTTPONLY (si se requiere mayor seguridad):
# 1. Instalar: djangorestframework-simplejwt[cookies]
# 2. Descomentar las líneas JWT_AUTH_COOKIE_* abajo
# 3. Actualizar frontend para no enviar Authorization header
# 4. Ajustar CORS para credentials
# 5. Implementar CSRF protection para requests de mutación
#
# JWT_AUTH_COOKIE = 'access_token'
# JWT_AUTH_REFRESH_COOKIE = 'refresh_token'
# JWT_AUTH_COOKIE_SECURE = not DEBUG  # Solo HTTPS en producción
# JWT_AUTH_COOKIE_HTTP_ONLY = True    # Inaccesible desde JavaScript
# JWT_AUTH_COOKIE_SAMESITE = 'Lax'    # Protección CSRF básica
# JWT_AUTH_COOKIE_PATH = '/'

# Ocultar refresh token del payload en producción (solo usar HttpOnly cookie)
JWT_HIDE_REFRESH_FROM_PAYLOAD = config('JWT_HIDE_REFRESH_FROM_PAYLOAD', default=not DEBUG, cast=bool)

# Límites para importaciones Excel
# Default más conservador para producción; puede ajustarse vía env.
IMPORT_MAX_FILE_SIZE_MB = config('IMPORT_MAX_FILE_SIZE_MB', default=5, cast=int)
IMPORT_MAX_ROWS = config('IMPORT_MAX_ROWS', default=2000, cast=int)
IMPORT_ALLOWED_EXTENSIONS = ['.xlsx', '.xls']
#
# ═══════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════
# CORS CONFIGURATION
# ═══════════════════════════════════════════════════════════
# Lee los orígenes permitidos desde una única variable de entorno
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='', cast=Csv())
CORS_ALLOW_CREDENTIALS = True  # IMPORTANTE: Permite envío de cookies cross-origin
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]
# Exponer headers necesarios al frontend
CORS_EXPOSE_HEADERS = [
    'content-disposition',
    'content-type',
]

# ═══════════════════════════════════════════════════════════
# DRF SPECTACULAR (Swagger/OpenAPI)
# ═══════════════════════════════════════════════════════════
SPECTACULAR_SETTINGS = {
    'TITLE': 'API Sistema de Farmacia Penitenciaria',
    'DESCRIPTION': 'Sistema de Control de Abasto de Medicamentos',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# ═══════════════════════════════════════════════════════════
# LOGGING CONFIGURATION
# ═══════════════════════════════════════════════════════════

# Formateador JSON personalizado para producción
class JsonFormatter:
    """Formateador JSON para logs estructurados en producción"""
    def format(self, record):
        import json
        from datetime import datetime
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
        }
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        if record.exc_info:
            import traceback
            log_data['exception'] = ''.join(traceback.format_exception(*record.exc_info))
        return json.dumps(log_data, ensure_ascii=False)

# Elegir formateadores según entorno
# En producción con LOG_TO_STDOUT=True, solo usamos console handler (Render, Heroku, etc.)
_log_handlers = ['console'] if LOG_TO_STDOUT else ['console', 'file']

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} {message}',
            'style': '{',
        },
        'json': {
            '()': 'config.settings.JsonFormatter',
        } if not DEBUG else {
            'format': '[{levelname}] {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json' if not DEBUG else 'verbose',
            'level': LOG_LEVEL,
        },
        **({
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'json' if not DEBUG else 'verbose',
                'filename': LOG_FILE,
                'maxBytes': 10 * 1024 * 1024,  # 10MB
                'backupCount': 5,
                'encoding': 'utf-8',
            },
        } if not LOG_TO_STDOUT else {}),
    },
    'root': {
        'handlers': _log_handlers,
        'level': LOG_LEVEL,
    },
    'loggers': {
        'django': {
            'handlers': _log_handlers,
            'level': 'INFO',  # No loguear cada query SQL
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'WARNING',  # Solo errores de DB, no cada query
            'propagate': False,
        },
        'core': {
            'handlers': _log_handlers,
            'level': 'INFO' if DEBUG else LOG_LEVEL,
        },
        'inventario': {
            'handlers': _log_handlers,
            'level': 'INFO',
        },
        'django.security': {
            'handlers': _log_handlers,
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# ═══════════════════════════════════════════════════════════
# CSRF CONFIGURATION (para frontend)
# ═══════════════════════════════════════════════════════════
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())

CSRF_COOKIE_NAME = 'csrftoken'
CSRF_HEADER_NAME = 'HTTP_X_CSRFTOKEN'
CSRF_COOKIE_HTTPONLY = False  # Permitir acceso desde JS

# Session configuration
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 86400  # 24 horas

# ═══════════════════════════════════════════════════════════
# EMAIL CONFIGURATION (para recuperación de contraseña)
# ═══════════════════════════════════════════════════════════
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend' if DEBUG else 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='Sistema Farmacia <noreply@farmacia.gob.mx>')

# ═══════════════════════════════════════════════════════════
# CAPTCHA (reCAPTCHA v2/v3)
# ═══════════════════════════════════════════════════════════
# 
# DECISIÓN DE ARQUITECTURA:
# reCAPTCHA está disponible pero DESHABILITADO por defecto.
# Para habilitarlo en producción:
# 1. Obtener claves en: https://www.google.com/recaptcha/admin
# 2. Configurar variables de entorno:
#    - RECAPTCHA_ENABLED=true
#    - RECAPTCHA_SITE_KEY=tu_clave_sitio
#    - RECAPTCHA_SECRET_KEY=tu_clave_secreta
#
# ENDPOINTS PROTEGIDOS (cuando está habilitado):
# - Login (/api/token/) - Ya implementado
# - Password reset (/api/usuarios/reset-password/) - Pendiente de implementar
#
# NOTA: Si se habilita, el frontend debe incluir el widget de reCAPTCHA
# y enviar el token en el campo 'recaptcha_token' del body.
#
RECAPTCHA_ENABLED = config('RECAPTCHA_ENABLED', default=False, cast=bool)
RECAPTCHA_SECRET_KEY = config('RECAPTCHA_SECRET_KEY', default='')
RECAPTCHA_SITE_KEY = config('RECAPTCHA_SITE_KEY', default='')
RECAPTCHA_SCORE_THRESHOLD = config('RECAPTCHA_SCORE_THRESHOLD', default=0.5, cast=float)  # Para v3

# URL del frontend (para enlaces en emails de recuperación de contraseña)
FRONTEND_URL = config('FRONTEND_URL', default='http://localhost:5173')

# ═══════════════════════════════════════════════════════════
# CACHE CONFIGURATION (para optimizar dashboard y reportes)
# ═══════════════════════════════════════════════════════════
# Render.com usa REDIS_URL automáticamente al crear un servicio Redis
# También soporta CACHE_URL como fallback para otros proveedores
REDIS_URL = config('REDIS_URL', default=config('CACHE_URL', default=''))

if REDIS_URL:
    # Configuración de Redis para producción (Render.com)
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                # Usar hiredis para mejor rendimiento (ya está en requirements.txt)
                'PARSER_CLASS': 'redis.connection.HiredisParser',
                # Timeout de conexión para evitar bloqueos
                'SOCKET_CONNECT_TIMEOUT': 5,
                'SOCKET_TIMEOUT': 5,
                # Reintentos automáticos en caso de fallo
                'CONNECTION_POOL_KWARGS': {
                    'max_connections': 50,
                    'retry_on_timeout': True,
                },
                # Ignorar excepciones para que la app no falle si Redis está caído
                'IGNORE_EXCEPTIONS': True,
            },
            'KEY_PREFIX': 'farmacia',
            'TIMEOUT': 300,  # 5 minutos por defecto
        }
    }
    # Usar Redis también para las sesiones (mejor rendimiento)
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'
else:
    # Cache local en memoria para desarrollo
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
            'TIMEOUT': 300,
            'OPTIONS': {
                'MAX_ENTRIES': 1000
            }
        }
    }

# Tiempos de cache (en segundos)
CACHE_TTL_DASHBOARD = config('CACHE_TTL_DASHBOARD', default=60, cast=int)  # 1 minuto
CACHE_TTL_ESTADISTICAS = config('CACHE_TTL_ESTADISTICAS', default=300, cast=int)  # 5 minutos
CACHE_TTL_REPORTES = config('CACHE_TTL_REPORTES', default=600, cast=int)  # 10 minutos
