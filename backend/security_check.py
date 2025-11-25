"""Validaciones rapidas de seguridad previo a deployment."""
import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from django.conf import settings  # noqa: E402


def check_security():
    issues = []
    warnings = []

    if settings.DEBUG:
        issues.append("DEBUG=True en produccion")
    if len(settings.SECRET_KEY) < 32:
        issues.append("SECRET_KEY muy corta")
    if "*" in settings.ALLOWED_HOSTS:
        issues.append("ALLOWED_HOSTS contiene '*'")

    if not settings.SECURE_SSL_REDIRECT:
        warnings.append("SECURE_SSL_REDIRECT deshabilitado")
    if not settings.SESSION_COOKIE_SECURE:
        warnings.append("SESSION_COOKIE_SECURE deshabilitado")
    if not settings.CSRF_COOKIE_SECURE:
        warnings.append("CSRF_COOKIE_SECURE deshabilitado")

    db_password = settings.DATABASES['default'].get('PASSWORD')
    if not db_password or db_password.lower() == 'admin':
        issues.append("Password de base de datos insegura")

    if not getattr(settings, 'LOGGING', None):
        warnings.append("LOGGING no configurado")

    if not settings.EMAIL_HOST:
        warnings.append("EMAIL_HOST no configurado")

    print("\nSECURITY CHECK\n" + "=" * 40)
    if issues:
        print("Problemas criticos:")
        for issue in issues:
            print(f" - {issue}")
    else:
        print("Sin problemas criticos")

    if warnings:
        print("\nAdvertencias:")
        for warn in warnings:
            print(f" - {warn}")
    else:
        print("\nSin advertencias")

    return len(issues) == 0


if __name__ == "__main__":
    ok = check_security()
    sys.exit(0 if ok else 1)
