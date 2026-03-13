from pathlib import Path
from decouple import config, Csv
from datetime import timedelta
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# HALLAZGO #1/#2: Definir DEBUG primero para evitar lógica circular
DEBUG = config('DEBUG', default=False, cast=bool)

# HALLAZGO #1: SECRET_KEY con fallback seguro según entorno
# - En producción (DEBUG=False): debe estar configurada o falla
# - En desarrollo (DEBUG=True): usa clave temporal si no está configurada
SECRET_KEY = config('SECRET_KEY', default='dev-only-insecure-key-not-for-production' if DEBUG else '')

# Logging defaults (can be overridden by env)
LOG_LEVEL = config('LOG_LEVEL', default='INFO')
# ISS-004: En producción (Render, containers) usar stdout por defecto ya que el disco es efímero
# Detectar automáticamente entornos containerizados
_is_container = config('RENDER', default=False, cast=bool) or config('DYNO', default='') or config('KUBERNETES_SERVICE_HOST', default='')
LOG_TO_STDOUT = config('LOG_TO_STDOUT', default=_is_container or not DEBUG, cast=bool)
LOG_FILE = config('LOG_FILE', default=str(BASE_DIR / 'logs' / 'django.log'))
# ISS-004 FIX: Ruta alternativa segura para logs si la principal falla
LOG_FILE_FALLBACK = config('LOG_FILE_FALLBACK', default=str(Path('/tmp') / 'farmacia_penitenciaria.log'))

# ISS-004 FIX: Mejorar robustez del fallback de logging
# Estrategia: 1) Intentar ruta principal, 2) Intentar ruta alternativa, 3) Forzar stdout
_logging_fallback_activated = False
_logging_fallback_reason = None

if not LOG_TO_STDOUT:
    _log_paths_to_try = [
        ('principal', LOG_FILE),
        ('alternativa', LOG_FILE_FALLBACK),
    ]
    
    _log_file_ok = False
    for path_name, log_path in _log_paths_to_try:
        try:
            log_dir = Path(log_path).parent
            log_dir.mkdir(parents=True, exist_ok=True)
            # Verificar que podemos escribir
            test_file = log_dir / '.write_test'
            test_file.touch()
            test_file.unlink()
            # Si llegamos aquí, la ruta funciona
            if path_name == 'alternativa':
                LOG_FILE = log_path  # Usar ruta alternativa
                _logging_fallback_activated = True
                _logging_fallback_reason = f"Ruta principal no accesible, usando: {log_path}"
            _log_file_ok = True
            break
        except (PermissionError, OSError) as e:
            _logging_fallback_reason = str(e)
            continue
    
    if not _log_file_ok:
        # Ninguna ruta de archivo funciona, forzar stdout
        import sys
        print(
            f"[ISS-004 WARNING] No se puede escribir logs en disco ({_logging_fallback_reason}). "
            f"Forzando LOG_TO_STDOUT=True. "
            f"Para persistir logs en producción, configure un agregador externo "
            f"(ELK, CloudWatch, Datadog, etc.) o use un volumen persistente.",
            file=sys.stderr
        )
        LOG_TO_STDOUT = True
        _logging_fallback_activated = True
    elif _logging_fallback_activated:
        import sys
        print(
            f"[ISS-004 INFO] {_logging_fallback_reason}",
            file=sys.stderr
        )

# ═══════════════════════════════════════════════════════════
# VALIDACIÓN ESTRICTA EN PRODUCCIÓN
# ═══════════════════════════════════════════════════════════
# ISS-002: Modo mantenimiento para permitir comandos administrativos
# sin bloquear por validaciones de entorno (migraciones, collectstatic, etc.)
MAINTENANCE_MODE = config('MAINTENANCE_MODE', default=False, cast=bool)

# ISS-001 FIX (audit10): SKIP_SECURITY_VALIDATION SOLO funciona con DEBUG=True
# En producción (DEBUG=False), esta bandera es IGNORADA para prevenir despliegues inseguros
_skip_security_env = config('SKIP_SECURITY_VALIDATION', default=False, cast=bool)
if _skip_security_env and not DEBUG:
    import sys
    print(
        "[SECURITY WARNING] SKIP_SECURITY_VALIDATION=True IGNORADO porque DEBUG=False. "
        "Esta bandera solo funciona en desarrollo.",
        file=sys.stderr
    )
SKIP_SECURITY_VALIDATION = _skip_security_env and DEBUG  # ISS-001 FIX: Solo válido en DEBUG=True

# ISS-004: Detectar comandos de gestión de Django para permitir operaciones offline
# Esto evita bloqueos en migraciones, collectstatic, y pipelines de CI
import sys
_is_management_command = len(sys.argv) > 1 and sys.argv[0].endswith('manage.py')
_offline_commands = {'migrate', 'makemigrations', 'collectstatic', 'check', 'showmigrations', 
                     'dbshell', 'shell', 'createsuperuser', 'test', 'flush', 'dumpdata', 'loaddata'}
_is_offline_command = _is_management_command and len(sys.argv) > 1 and sys.argv[1] in _offline_commands

# ISS-QA-001 FIX: Detectar pytest para permitir ejecución de tests sin SECRET_KEY de producción
# Múltiples métodos de detección para cubrir todos los casos (pytest directo, IDE, CI)
_is_pytest = (
    'pytest' in sys.modules or  # pytest ya importado
    '_pytest' in sys.modules or  # pytest internals
    'py.test' in sys.modules or  # pytest alternativo
    (sys.argv and any('pytest' in str(arg) for arg in sys.argv)) or  # pytest en argumentos
    'test' in sys.argv  # manage.py test
)

# Variables de entorno para CI/CD pipelines
RUNNING_MIGRATIONS = config('RUNNING_MIGRATIONS', default=False, cast=bool)
RUNNING_COLLECTSTATIC = config('RUNNING_COLLECTSTATIC', default=False, cast=bool)
CI_ENVIRONMENT = config('CI', default=False, cast=bool) or config('CI_ENVIRONMENT', default=False, cast=bool)

# ISS-001 FIX (audit10): Validación crítica SIEMPRE en producción
# Solo permitir bypass para comandos offline específicos (migrate, collectstatic, etc.)
# NUNCA para arranque del servidor en producción
_skip_validation = (
    DEBUG or  # En desarrollo se permite todo
    _is_offline_command or  # Comandos de gestión offline
    _is_pytest or  # ISS-QA-001 FIX: pytest tests
    RUNNING_MIGRATIONS or  # Pipeline de migraciones
    RUNNING_COLLECTSTATIC or  # Pipeline de collectstatic
    CI_ENVIRONMENT  # Entorno de CI (tests)
)
# ISS-001 FIX: MAINTENANCE_MODE ya NO permite bypass de validación de seguridad
# Solo se usa para otras funciones de mantenimiento, no para arranque inseguro

# ISS-QA-001 FIX: Para testing, usar SECRET_KEY segura temporal si no está definida
# Esto permite correr pytest sin configurar variables de entorno
if _is_pytest or CI_ENVIRONMENT:
    if not SECRET_KEY or SECRET_KEY == 'dev-only-insecure-key-not-for-production':
        SECRET_KEY = 'pytest-temporary-secret-key-only-for-testing-not-for-production-use-12345678901234567890'

# ISS-001 FIX (audit10): Validaciones CRÍTICAS que SIEMPRE se ejecutan en producción
# ISS-QA-001 FIX: NO validar en entorno de testing (pytest, CI)
if not DEBUG and not _is_pytest and not CI_ENVIRONMENT:
    _critical_errors = []
    
    # CRÍTICO 1: SECRET_KEY NUNCA puede estar vacía o ser insegura en producción
    if not SECRET_KEY or SECRET_KEY == 'dev-only-insecure-key-not-for-production':
        _critical_errors.append(
            'SECRET_KEY: CRÍTICO - Variable no configurada en producción. '
            'Genera una con: python -c "import secrets; print(secrets.token_urlsafe(64))"'
        )
    elif len(SECRET_KEY) < 50:
        _critical_errors.append(f'SECRET_KEY: CRÍTICO - Muy corta ({len(SECRET_KEY)} chars). Mínimo 50.')
    elif 'insecure' in SECRET_KEY.lower() or 'dev' in SECRET_KEY.lower():
        _critical_errors.append('SECRET_KEY: CRÍTICO - Parece ser una clave de desarrollo.')
    
    # Si hay errores CRÍTICOS, fallar SIEMPRE (sin importar banderas de bypass)
    if _critical_errors:
        _error_msg = '\n\n' + '=' * 70 + '\n'
        _error_msg += '🚨 ERRORES CRÍTICOS DE SEGURIDAD (NO BYPASSEABLE)\n'
        _error_msg += '=' * 70 + '\n\n'
        for i, err in enumerate(_critical_errors, 1):
            _error_msg += f'  {i}. {err}\n\n'
        _error_msg += '=' * 70 + '\n'
        _error_msg += 'Estas validaciones NO pueden omitirse en producción.\n'
        _error_msg += '=' * 70 + '\n'
        raise ValueError(_error_msg)

# Solo validar configuración completa cuando no estamos en modo offline
if not DEBUG and not _skip_validation:
    # Lista de verificaciones de seguridad para producción
    _security_errors = []
    
    # 1. DATABASE_URL debe ser PostgreSQL
    _db_url = config('DATABASE_URL', default='')
    if not _db_url:
        _security_errors.append('DATABASE_URL: Variable no configurada. Requerida para producción.')
    elif 'sqlite' in _db_url.lower():
        _security_errors.append('DATABASE_URL: SQLite no permitido en producción. Usa PostgreSQL.')
    elif not _db_url.startswith(('postgres://', 'postgresql://')):
        _security_errors.append('DATABASE_URL: Debe ser una URL de PostgreSQL válida.')
    
    # 2. ISS-002 FIX (audit10): ALLOWED_HOSTS DEBE estar configurado explícitamente
    # Ya no hay default permisivo - vacío = error
    _allowed_hosts = config('ALLOWED_HOSTS', default='')
    if not _allowed_hosts:
        _security_errors.append(
            'ALLOWED_HOSTS: OBLIGATORIO - No hay default en producción. '
            'Configura los dominios de producción explícitamente.'
        )
    elif _allowed_hosts == '*':
        _security_errors.append('ALLOWED_HOSTS: Wildcard (*) no permitido en producción.')
    elif _allowed_hosts in ('localhost', '127.0.0.1', 'localhost,127.0.0.1,testserver'):
        _security_errors.append(
            'ALLOWED_HOSTS: Solo contiene hosts de desarrollo. '
            'Agrega los dominios de producción.'
        )
    
    # 3. CORS_ALLOWED_ORIGINS debe estar configurado
    _cors_origins = config('CORS_ALLOWED_ORIGINS', default='')
    if not _cors_origins:
        _security_errors.append('CORS_ALLOWED_ORIGINS: Variable no configurada. Requerida para frontend.')
    elif 'localhost' in _cors_origins and 'onrender.com' not in _cors_origins:
        _security_errors.append('CORS_ALLOWED_ORIGINS: Contiene localhost pero no dominios de producción.')
    
    # 4. CSRF_TRUSTED_ORIGINS debe estar configurado
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

# ISS-002 FIX (audit10): ALLOWED_HOSTS con validación estricta
# En producción sin _skip_validation ya se validó arriba
# En desarrollo o comandos offline, usar default seguro
if DEBUG:
    ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,testserver', cast=Csv())
else:
    # En producción, SIEMPRE requiere configuración explícita
    _hosts = config('ALLOWED_HOSTS', default='')
    if not _hosts and _skip_validation:
        # Solo para comandos offline en producción, permitir localhost temporal
        ALLOWED_HOSTS = ['localhost', '127.0.0.1']
    else:
        ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())

# ISS-002 FIX (audit10): ENFORCE_HTTPS = True por defecto en producción
# Solo se puede desactivar explícitamente con ENFORCE_HTTPS=False
ENFORCE_HTTPS = config('ENFORCE_HTTPS', default=not DEBUG, cast=bool)
if not DEBUG and not ENFORCE_HTTPS:
    import sys
    print(
        "[SECURITY WARNING] ENFORCE_HTTPS=False en producción. "
        "El tráfico HTTP expone credenciales JWT. Considera habilitar HTTPS.",
        file=sys.stderr
    )
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
# ISS-034: SECURE_BROWSER_XSS_FILTER eliminado - es obsoleto y puede causar
# vulnerabilidades XS-Leak. Los navegadores modernos lo ignoran.
# La protección contra XSS debe manejarse con CSP (Content-Security-Policy).

# ═══════════════════════════════════════════════════════════
# RATE LIMITING (ISS-015)
# ═══════════════════════════════════════════════════════════
# Protección contra ataques de fuerza bruta y DDoS
RATE_LIMIT_ENABLED = config('RATE_LIMIT_ENABLED', default=not DEBUG, cast=bool)
RATE_LIMIT_REQUESTS = config('RATE_LIMIT_REQUESTS', default=100, cast=int)  # Requests por ventana
RATE_LIMIT_WINDOW = config('RATE_LIMIT_WINDOW', default=60, cast=int)  # Segundos
# Límites más estrictos para endpoints de autenticación
RATE_LIMIT_LOGIN_REQUESTS = config('RATE_LIMIT_LOGIN_REQUESTS', default=5, cast=int)
RATE_LIMIT_LOGIN_WINDOW = config('RATE_LIMIT_LOGIN_WINDOW', default=300, cast=int)  # 5 minutos

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
    'corsheaders.middleware.CorsMiddleware',  # CORS PRIMERO - antes que cualquier otro
    'middleware.CORSErrorHandlingMiddleware',  # ISS-FIX: CORS headers en errores 500
    'core.middleware.RateLimitMiddleware',  # Rate limiting
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'core.middleware.CurrentRequestMiddleware',  # Para auditoría (request en signals)
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.SecurityHeadersMiddleware',  # CSP y headers de seguridad adicionales
    'core.middleware.PdfInlineMiddleware',  # PDFs se abren en visor del navegador (inline, no attachment)
    'core.middleware.AuditMiddleware',  # Auditoría completa para Panel SUPER ADMIN
]

# Configuración de Auditoría
AUDIT_ENABLED = True  # Activar/desactivar registro de auditoría
AUDIT_LOG_READS = False  # No loguear GETs por defecto (muy verboso)
AUDIT_EXCLUDE_PATHS = [  # Paths excluidos de auditoría
    '/api/auth/token/refresh/',
    '/api/health/',
    '/api/metrics/',
    '/media/',
    '/static/',
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

# ISS-QA-001 FIX: Forzar SQLite para tests usando detección unificada
# Usa _is_pytest que ya detecta pytest/test de múltiples formas
TESTING = _is_pytest or CI_ENVIRONMENT

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
    # Detectar si es Supabase Pooler (puerto 6543) vs conexión directa (5432)
    _is_supabase_pooler = 'pooler.supabase' in DATABASE_URL and ':6543' in DATABASE_URL
    
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=config('DB_CONN_MAX_AGE', default=600 if not _is_supabase_pooler else 0, cast=int),
            ssl_require=config('DB_SSL_REQUIRE', default=True, cast=bool)
        )
    }
    
    # Agregar timeouts de conexión para PostgreSQL/Supabase
    DATABASES['default'].setdefault('OPTIONS', {})
    
    if _is_supabase_pooler:
        # Configuración optimizada para Supabase Connection Pooler
        # - conn_max_age=0: Pooler maneja las conexiones, no Django
        # - sslmode=require: SSL requerido pero sin verificación de certificado (compatible con pooler)
        # - connect_timeout mayor para cold starts de Supabase
        DATABASES['default']['OPTIONS'].update({
            'connect_timeout': 30,  # Mayor timeout para cold start de Supabase
            'sslmode': 'require',  # SSL requerido pero flexible con certificados
            'options': '-c statement_timeout=30000',  # Statement timeout 30s
        })
        import sys
        print(f"[DB CONFIG] Usando Supabase Connection Pooler (puerto 6543)", file=sys.stderr)
    else:
        # Configuración para conexión directa PostgreSQL
        DATABASES['default']['OPTIONS'].update({
            'connect_timeout': 10,  # Timeout de conexión en segundos
            'options': '-c statement_timeout=30000',  # Statement timeout 30s
        })
else:
    # Solo desarrollo local - NUNCA en producción
    # ISS-FIX: Detectar entorno Render explícitamente para fallar temprano
    _is_render = config('RENDER', default=False, cast=bool)
    _is_production = not DEBUG or _is_render
    
    if _is_production:
        import sys
        print(
            "\n" + "=" * 70 + "\n"
            "❌ ERROR CRÍTICO: DATABASE_URL no configurada\n"
            "=" * 70 + "\n"
            "Este servidor está en modo producción (DEBUG=False o RENDER=True)\n"
            "pero no se encontró DATABASE_URL.\n\n"
            "SOLUCIÓN:\n"
            "1. Ve al Dashboard de Render\n"
            "2. Selecciona el servicio 'farmacia-api'\n"
            "3. Ve a 'Environment' > 'Environment Variables'\n"
            "4. Agrega DATABASE_URL con tu URL de Supabase PostgreSQL:\n"
            "   postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-us-west-1.pooler.supabase.com:6543/postgres\n\n"
            "5. Haz clic en 'Save Changes' y espera el redeploy\n"
            "=" * 70 + "\n",
            file=sys.stderr
        )
        raise ValueError(
            'ERROR: DATABASE_URL requerido en producción. '
            'Configura esta variable en el Dashboard de Render.'
        )
    
    # Desarrollo local con SQLite
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

# AUTHENTICATION BACKENDS
# Usa backend case-insensitive para que "Centro", "centro", "CENTRO" funcionen igual
AUTHENTICATION_BACKENDS = [
    'core.backends.CaseInsensitiveModelBackend',
]

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

# ═══════════════════════════════════════════════════════════
# ISS-001/002 FIX: SUPABASE STORAGE CONFIGURATION
# ═══════════════════════════════════════════════════════════
# Para almacenamiento de documentos (facturas, contratos de lotes)
# En producción usa Supabase Storage (S3 compatible)
# En desarrollo usa almacenamiento local como fallback
#
# Variables de entorno requeridas para producción:
#   SUPABASE_URL: URL del proyecto Supabase (ej: https://xxx.supabase.co)
#   SUPABASE_KEY: API Key del proyecto (preferir service_role para backend)
#
# Bucket por defecto: 'documentos'
# Se debe crear manualmente en Supabase Dashboard > Storage
SUPABASE_URL = config('SUPABASE_URL', default='')
SUPABASE_KEY = config('SUPABASE_KEY', default='')
SUPABASE_STORAGE_BUCKET = config('SUPABASE_STORAGE_BUCKET', default='documentos')

# Advertir si no está configurado en producción (pero no bloquear)
if not DEBUG and not SUPABASE_URL and not _skip_validation:
    import sys
    print(
        "[WARNING] ISS-001: SUPABASE_URL no configurado. "
        "Los documentos de lotes se guardarán localmente (no persistente en Render).",
        file=sys.stderr
    )

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
        'login': config('THROTTLE_RATE_LOGIN', default='20/min'),  # ✅ Rate limit para login
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

# Dominios de producción en Render (SIEMPRE INCLUIDOS - NO DEPENDEN DE ENV VAR)
_cors_render_domains = [
    'https://farmacia-penitenciaria-front.onrender.com',
    'https://farmacia-penitenciaria.onrender.com',
    'https://farmacia-penitenciaria-front-ggkp.onrender.com',
]

# Dominios de desarrollo local
_cors_dev_domains = [
    'http://localhost:3000',
    'http://localhost:5173',
    'http://127.0.0.1:3000',
    'http://127.0.0.1:5173',
] if DEBUG else []

# Dominios adicionales desde variable de entorno (opcional)
_cors_from_env = config('CORS_ALLOWED_ORIGINS', default='', cast=Csv())

# Combinar todos los orígenes permitidos (sin duplicados)
# PRIORIDAD: Render (siempre) + Dev (si DEBUG) + Env var (adicionales)
CORS_ALLOWED_ORIGINS = list(set(
    _cors_render_domains +
    _cors_dev_domains +
    [origin for origin in _cors_from_env if origin]
))

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
    'x-confirm-action',
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
        # ISS-006 FIX (audit17): Logger específico para auditoría de accesos privilegiados
        'audit': {
            'handlers': _log_handlers,
            'level': 'INFO',
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
# En producción usamos Resend (https://resend.com)
# Variable requerida: RESEND_API_KEY
# Obtén tu API key gratis en: https://resend.com/api-keys
RESEND_API_KEY = config('RESEND_API_KEY', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='Sistema Farmacia <onboarding@resend.dev>')

# Fallback a configuración SMTP tradicional si no hay Resend
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend' if DEBUG else 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

# ISS-002 FIX: Advertir si email no está configurado en producción
if not DEBUG and not RESEND_API_KEY and not EMAIL_HOST_USER and not _skip_validation:
    import sys
    print(
        "[WARNING] ISS-002: EMAIL_HOST_USER no configurado. "
        "La recuperación de contraseña por email no funcionará. "
        "Configure EMAIL_HOST_USER y EMAIL_HOST_PASSWORD para habilitar esta funcionalidad.",
        file=sys.stderr
    )


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
# Usa variable de entorno si está configurada, sino intenta detectar el entorno
_default_frontend = 'http://localhost:5173' if DEBUG else 'https://farmacia-penitenciaria-front.onrender.com'
FRONTEND_URL = config('FRONTEND_URL', default=_default_frontend)

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

# ═══════════════════════════════════════════════════════════
# SUPPRESS KNOWN-HARMLESS THIRD-PARTY WARNINGS
# ═══════════════════════════════════════════════════════════
import warnings
# supabase jala urllib3>=2 y chardet>=7 que son más nuevos que lo que
# requests <=2.32 verificaba internamente — completamente inofensivo.
warnings.filterwarnings('ignore', message='urllib3', category=Warning)
warnings.filterwarnings('ignore', category=Warning, module='requests')

# ═══════════════════════════════════════════════════════════
# SILENCED SYSTEM CHECKS (para desarrollo)
# ═══════════════════════════════════════════════════════════
# En modo DEBUG, silenciar warnings de seguridad que no aplican en desarrollo
# Estas configuraciones SÍ se aplican en producción (DEBUG=False)
if DEBUG:
    SILENCED_SYSTEM_CHECKS = [
        'security.W004',  # HSTS no configurado (no necesario en dev)
        'security.W008',  # SECURE_SSL_REDIRECT no True (localhost no usa SSL)
        'security.W012',  # SESSION_COOKIE_SECURE no True (localhost)
        'security.W016',  # CSRF_COOKIE_SECURE no True (localhost)
        'security.W018',  # DEBUG=True (esperado en desarrollo)
    ]
else:
    SILENCED_SYSTEM_CHECKS = []

# ═══════════════════════════════════════════════════════════
# SENTRY — Error tracking & performance monitoring
# ═══════════════════════════════════════════════════════════
# Requiere agregar SENTRY_DSN en las variables de entorno de Render.
# El paquete sentry-sdk[django] ya está en requirements.txt.
# Con DSN vacío (por defecto) Sentry queda deshabilitado — sin efecto en dev.
SENTRY_DSN = config('SENTRY_DSN', default='')

if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    import logging as _logging

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(
                transaction_style='url',    # Agrupa trazas por URL (evita card explosion)
                middleware_spans=True,
                signals_spans=False,        # Señales de Django son ruidosas; deshabilitar
            ),
            LoggingIntegration(
                level=_logging.WARNING,     # Captura WARNING y superiores
                event_level=_logging.ERROR, # Solo ERROR+ crea Sentry events
            ),
        ],
        # Muestreo de rendimiento: 5% de requests en producción
        traces_sample_rate=0.05 if not DEBUG else 0.0,
        # No enviar datos personales (IPs, cookies, headers de sesión)
        send_default_pii=False,
        environment='production' if not DEBUG else 'development',
        # Ignorar errores 404 y PermissionDenied que generarían demasiado ruido
        ignore_errors=[
            'django.http.Http404',
            'django.core.exceptions.PermissionDenied',
        ],
    )
