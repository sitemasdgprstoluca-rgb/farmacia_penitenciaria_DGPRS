"""
Tests de seguridad y middlewares - audit23.

Cubre:
- Checklist de seguridad para producción
- SecurityHeadersMiddleware
- RateLimitMiddleware
- CurrentRequestMiddleware
- RedirectNonSuperuserFromAdminMiddleware
"""
import pytest
from django.test import TestCase, RequestFactory, override_settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from unittest.mock import MagicMock, patch


User = get_user_model()


class TestChecklistSeguridadProduccion(TestCase):
    """
    Checklist de variables de seguridad para producción.
    
    Verifica que settings.py tenga las configuraciones correctas
    para un despliegue seguro.
    """
    
    def test_https_obligatorio_en_produccion(self):
        """Verifica configuración HTTPS en settings."""
        from django.conf import settings
        
        # Estas variables deben existir en settings
        assert hasattr(settings, 'ENFORCE_HTTPS')
        assert hasattr(settings, 'SECURE_SSL_REDIRECT')
        assert hasattr(settings, 'SECURE_HSTS_SECONDS')
        
        # En DEBUG=False, deben estar habilitadas por defecto
        if not settings.DEBUG:
            assert settings.ENFORCE_HTTPS is True, \
                "ENFORCE_HTTPS debe ser True en producción"
            assert settings.SECURE_SSL_REDIRECT is True, \
                "SECURE_SSL_REDIRECT debe ser True en producción"
            assert settings.SECURE_HSTS_SECONDS >= 31536000, \
                "HSTS debe ser al menos 1 año (31536000 segundos)"
    
    def test_cookies_seguras_en_produccion(self):
        """Verifica configuración de cookies seguras."""
        from django.conf import settings
        
        assert hasattr(settings, 'SESSION_COOKIE_SECURE')
        assert hasattr(settings, 'CSRF_COOKIE_SECURE')
        assert hasattr(settings, 'SESSION_COOKIE_SAMESITE')
        assert hasattr(settings, 'CSRF_COOKIE_SAMESITE')
        
        # En producción deben ser seguras
        if not settings.DEBUG:
            assert settings.SESSION_COOKIE_SECURE is True
            assert settings.CSRF_COOKIE_SECURE is True
        
        # SameSite debe estar configurado
        assert settings.SESSION_COOKIE_SAMESITE in ('Strict', 'Lax')
        assert settings.CSRF_COOKIE_SAMESITE in ('Strict', 'Lax')
    
    def test_allowed_hosts_no_wildcard(self):
        """Verifica que ALLOWED_HOSTS no tenga wildcard en producción."""
        from django.conf import settings
        
        assert hasattr(settings, 'ALLOWED_HOSTS')
        
        if not settings.DEBUG:
            assert '*' not in settings.ALLOWED_HOSTS, \
                "ALLOWED_HOSTS no debe contener '*' en producción"
    
    def test_secret_key_segura(self):
        """Verifica que SECRET_KEY sea segura."""
        from django.conf import settings
        
        assert hasattr(settings, 'SECRET_KEY')
        assert settings.SECRET_KEY, "SECRET_KEY no puede estar vacía"
        
        # En producción debe ser larga y segura
        if not settings.DEBUG:
            assert len(settings.SECRET_KEY) >= 50, \
                "SECRET_KEY debe tener al menos 50 caracteres"
            assert 'insecure' not in settings.SECRET_KEY.lower(), \
                "SECRET_KEY no debe contener 'insecure'"
            assert 'dev' not in settings.SECRET_KEY.lower() or len(settings.SECRET_KEY) > 60, \
                "SECRET_KEY parece ser de desarrollo"
    
    def test_x_frame_options_deny(self):
        """Verifica X-Frame-Options para prevenir clickjacking."""
        from django.conf import settings
        
        assert hasattr(settings, 'X_FRAME_OPTIONS')
        assert settings.X_FRAME_OPTIONS in ('DENY', 'SAMEORIGIN'), \
            "X_FRAME_OPTIONS debe ser DENY o SAMEORIGIN"
    
    def test_content_type_nosniff(self):
        """Verifica X-Content-Type-Options."""
        from django.conf import settings
        
        assert hasattr(settings, 'SECURE_CONTENT_TYPE_NOSNIFF')
        assert settings.SECURE_CONTENT_TYPE_NOSNIFF is True
    
    def test_rate_limiting_configurado(self):
        """Verifica que rate limiting esté configurado."""
        from django.conf import settings
        
        assert hasattr(settings, 'RATE_LIMIT_ENABLED')
        assert hasattr(settings, 'RATE_LIMIT_REQUESTS')
        assert hasattr(settings, 'RATE_LIMIT_LOGIN_REQUESTS')
        
        # Límites razonables
        assert settings.RATE_LIMIT_REQUESTS > 0
        assert settings.RATE_LIMIT_LOGIN_REQUESTS > 0
        assert settings.RATE_LIMIT_LOGIN_REQUESTS < settings.RATE_LIMIT_REQUESTS
    
    def test_csp_configurado(self):
        """Verifica Content-Security-Policy."""
        from django.conf import settings
        
        assert hasattr(settings, 'CSP_ENABLED')
        assert hasattr(settings, 'CSP_DEFAULT_SRC')
        assert hasattr(settings, 'CSP_FRAME_ANCESTORS')
        
        # frame-ancestors debe ser restrictivo
        assert settings.CSP_FRAME_ANCESTORS in ("'none'", "'self'")


class TestSecurityHeadersMiddleware(TestCase):
    """Tests para SecurityHeadersMiddleware."""
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_middleware_agrega_csp_cuando_habilitado(self):
        """Verifica que CSP se agregue cuando está habilitado."""
        from core.middleware import SecurityHeadersMiddleware
        
        def get_response(request):
            return HttpResponse("OK")
        
        middleware = SecurityHeadersMiddleware(get_response)
        request = self.factory.get('/')
        
        with override_settings(CSP_ENABLED=True, CSP_DEFAULT_SRC="'self'"):
            response = middleware(request)
        
            assert 'Content-Security-Policy' in response
            assert "'self'" in response['Content-Security-Policy']
    
    def test_middleware_no_agrega_csp_cuando_deshabilitado(self):
        """Verifica que CSP no se agregue cuando está deshabilitado."""
        from core.middleware import SecurityHeadersMiddleware
        
        def get_response(request):
            return HttpResponse("OK")
        
        middleware = SecurityHeadersMiddleware(get_response)
        request = self.factory.get('/')
        
        with override_settings(CSP_ENABLED=False):
            response = middleware(request)
        
            assert 'Content-Security-Policy' not in response
    
    def test_middleware_agrega_permissions_policy(self):
        """Verifica que Permissions-Policy siempre se agregue."""
        from core.middleware import SecurityHeadersMiddleware
        
        def get_response(request):
            return HttpResponse("OK")
        
        middleware = SecurityHeadersMiddleware(get_response)
        request = self.factory.get('/')
        
        response = middleware(request)
        
        assert 'Permissions-Policy' in response
        assert 'geolocation=()' in response['Permissions-Policy']
        assert 'camera=()' in response['Permissions-Policy']


class TestRateLimitMiddleware(TestCase):
    """Tests para RateLimitMiddleware."""
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_middleware_permite_requests_normales(self):
        """Verifica que requests normales pasen."""
        from core.middleware import RateLimitMiddleware
        
        def get_response(request):
            return HttpResponse("OK")
        
        middleware = RateLimitMiddleware(get_response)
        request = self.factory.get('/api/test/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        with override_settings(RATE_LIMIT_ENABLED=True, RATE_LIMIT_REQUESTS=100):
            response = middleware(request)
        
            assert response.status_code == 200
    
    def test_middleware_deshabilitado_permite_todo(self):
        """Verifica que cuando está deshabilitado permite todo."""
        from core.middleware import RateLimitMiddleware
        
        def get_response(request):
            return HttpResponse("OK")
        
        middleware = RateLimitMiddleware(get_response)
        request = self.factory.get('/api/test/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        with override_settings(RATE_LIMIT_ENABLED=False):
            # Hacer muchas solicitudes
            for _ in range(200):
                response = middleware(request)
                assert response.status_code == 200
    
    def test_middleware_bloquea_exceso_requests(self):
        """Verifica bloqueo cuando se excede el límite."""
        from core.middleware import RateLimitMiddleware
        
        def get_response(request):
            return HttpResponse("OK")
        
        middleware = RateLimitMiddleware(get_response)
        
        with override_settings(
            RATE_LIMIT_ENABLED=True, 
            RATE_LIMIT_REQUESTS=3,
            RATE_LIMIT_WINDOW=60
        ):
            # Hacer más requests que el límite
            for i in range(5):
                request = self.factory.get('/api/test/')
                request.META['REMOTE_ADDR'] = '192.168.1.100'  # IP diferente
                response = middleware(request)
                
                if i >= 3:  # Después del límite
                    assert response.status_code == 429, \
                        f"Request {i+1} debió ser bloqueada (status: {response.status_code})"
    
    def test_middleware_extrae_ip_de_x_forwarded_for(self):
        """Verifica extracción de IP desde X-Forwarded-For."""
        from core.middleware import RateLimitMiddleware
        
        middleware = RateLimitMiddleware(lambda r: HttpResponse("OK"))
        
        request = self.factory.get('/api/test/')
        request.META['HTTP_X_FORWARDED_FOR'] = '203.0.113.195, 70.41.3.18, 150.172.238.178'
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        ip = middleware._get_client_ip(request)
        
        assert ip == '203.0.113.195', "Debe tomar la primera IP del X-Forwarded-For"
    
    def test_middleware_limite_especial_auth(self):
        """Verifica límite más estricto para endpoints de auth."""
        from core.middleware import RateLimitMiddleware
        
        def get_response(request):
            return HttpResponse("OK")
        
        middleware = RateLimitMiddleware(get_response)
        
        with override_settings(
            RATE_LIMIT_ENABLED=True,
            RATE_LIMIT_REQUESTS=100,
            RATE_LIMIT_LOGIN_REQUESTS=2,
            RATE_LIMIT_LOGIN_WINDOW=60
        ):
            # Endpoints de auth tienen límite más bajo
            for i in range(4):
                request = self.factory.post('/api/auth/token/')
                request.META['REMOTE_ADDR'] = '10.0.0.99'
                response = middleware(request)
                
                if i >= 2:
                    assert response.status_code == 429


class TestCurrentRequestMiddleware(TestCase):
    """Tests para CurrentRequestMiddleware."""
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_middleware_guarda_request_en_thread_local(self):
        """Verifica que el request se guarde en thread local."""
        from core.middleware import CurrentRequestMiddleware, get_current_request
        
        def get_response(request):
            # Verificar que el request está disponible dentro del ciclo
            current = get_current_request()
            assert current is request
            return HttpResponse("OK")
        
        middleware = CurrentRequestMiddleware(get_response)
        request = self.factory.get('/')
        
        middleware(request)
    
    def test_get_current_user_retorna_usuario(self):
        """Verifica que get_current_user retorne el usuario del request."""
        from core.middleware import CurrentRequestMiddleware, get_current_user, _thread_locals
        
        # Simular un request con usuario
        user = MagicMock()
        user.id = 1
        user.username = 'testuser'
        
        request = self.factory.get('/')
        request.user = user
        
        _thread_locals.request = request
        
        current_user = get_current_user()
        assert current_user is user


class TestRedirectNonSuperuserFromAdminMiddleware(TestCase):
    """Tests para RedirectNonSuperuserFromAdminMiddleware."""
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_superuser_accede_admin(self):
        """Superusuario puede acceder al admin."""
        from middleware import RedirectNonSuperuserFromAdminMiddleware
        
        def get_response(request):
            return HttpResponse("Admin OK")
        
        middleware = RedirectNonSuperuserFromAdminMiddleware(get_response)
        
        request = self.factory.get('/admin/')
        request.user = MagicMock(is_authenticated=True, is_superuser=True)
        
        response = middleware(request)
        
        assert response.status_code == 200
        assert response.content == b"Admin OK"
    
    def test_usuario_normal_redirigido_desde_admin(self):
        """Usuario normal es redirigido fuera del admin."""
        from middleware import RedirectNonSuperuserFromAdminMiddleware
        
        def get_response(request):
            return HttpResponse("Admin OK")
        
        middleware = RedirectNonSuperuserFromAdminMiddleware(get_response)
        
        request = self.factory.get('/admin/')
        request.user = MagicMock(is_authenticated=True, is_superuser=False)
        
        response = middleware(request)
        
        assert response.status_code == 302  # Redirect
    
    def test_usuario_normal_puede_logout(self):
        """Usuario normal puede acceder a /admin/logout/."""
        from middleware import RedirectNonSuperuserFromAdminMiddleware
        
        def get_response(request):
            return HttpResponse("Logout OK")
        
        middleware = RedirectNonSuperuserFromAdminMiddleware(get_response)
        
        request = self.factory.get('/admin/logout/')
        request.user = MagicMock(is_authenticated=True, is_superuser=False)
        
        response = middleware(request)
        
        assert response.status_code == 200
        assert response.content == b"Logout OK"
    
    def test_usuario_anonimo_pasa(self):
        """Usuario anónimo puede acceder (Django maneja el login)."""
        from middleware import RedirectNonSuperuserFromAdminMiddleware
        
        def get_response(request):
            return HttpResponse("Admin Login")
        
        middleware = RedirectNonSuperuserFromAdminMiddleware(get_response)
        
        request = self.factory.get('/admin/')
        request.user = MagicMock(is_authenticated=False, is_superuser=False)
        
        response = middleware(request)
        
        # Usuario anónimo pasa, Django mostrará el login
        assert response.status_code == 200


class TestEnvExampleCompleto(TestCase):
    """Verifica que .env.example tenga todas las variables necesarias."""
    
    def test_env_example_tiene_variables_seguridad(self):
        """Verifica variables de seguridad en .env.example."""
        import os
        from pathlib import Path
        
        base_dir = Path(__file__).parent.parent.parent
        env_example = base_dir / '.env.example'
        
        if not env_example.exists():
            self.skipTest(".env.example no encontrado en backend/")
        
        contenido = env_example.read_text()
        
        # Variables de seguridad que deben estar documentadas
        variables_requeridas = [
            'SECRET_KEY',
            'DEBUG',
            'ALLOWED_HOSTS',
            'ENFORCE_HTTPS',
            'SESSION_COOKIE_SECURE',
            'CSRF_COOKIE_SECURE',
            'CORS_ALLOWED_ORIGINS',
            'CSRF_TRUSTED_ORIGINS',
        ]
        
        for var in variables_requeridas:
            assert var in contenido, \
                f"Variable {var} debe estar documentada en .env.example"
    
    def test_env_example_tiene_ejemplos_produccion(self):
        """Verifica que haya ejemplos de producción."""
        import os
        from pathlib import Path
        
        base_dir = Path(__file__).parent.parent.parent
        env_example = base_dir / '.env.example'
        
        if not env_example.exists():
            self.skipTest(".env.example no encontrado")
        
        contenido = env_example.read_text()
        
        # Debe tener sección de producción
        assert 'PRODUCCIÓN' in contenido or 'produccion' in contenido.lower()
        assert 'SECURE_HSTS_SECONDS' in contenido
        assert 'onrender.com' in contenido or 'RENDER' in contenido
