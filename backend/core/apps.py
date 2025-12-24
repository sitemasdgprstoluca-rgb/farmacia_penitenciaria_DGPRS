from django.apps import AppConfig
import logging
import os

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    label = 'core'
    verbose_name = 'Core del Sistema'

    def ready(self):
        # Importar signals al iniciar la app
        from . import signals  # noqa: F401
        
        # ISS-001 FIX: Validar esquemas SOLO en producción y si está habilitado
        # Esto evita lentitud en desarrollo (~2s extra por cada inicio)
        import sys
        
        # Condiciones para SALTAR validación de esquema:
        # 1. Comandos de gestión (migrate, test, etc.)
        # 2. Modo DEBUG (desarrollo)
        # 3. Variable SKIP_SCHEMA_VALIDATION=1
        is_management_command = any(cmd in sys.argv for cmd in [
            'migrate', 'makemigrations', 'test', 'shell', 'dbshell',
            'collectstatic', 'check', 'runserver', 'showmigrations'
        ])
        skip_validation = os.environ.get('SKIP_SCHEMA_VALIDATION', '0') == '1'
        
        # Solo validar en producción (no DEBUG) y si no es comando de gestión
        from django.conf import settings
        should_validate = (
            not settings.DEBUG and 
            not is_management_command and 
            not skip_validation
        )
        
        if should_validate:
            try:
                from core.schema_validator import validate_unmanaged_schemas, check_transitions_constraint
                
                # Validar esquemas (solo warning, no bloquear inicio)
                results = validate_unmanaged_schemas(raise_on_error=False)
                check_transitions_constraint()
                
                total_errors = sum(len(e) for e in results.values())
                if total_errors:
                    logger.warning(
                        f"ISS-001: Validación de esquema completada con {total_errors} advertencia(s)."
                    )
                
                # ISS-005: Verificación adicional
                from core.schema_check import verificar_esquema_al_iniciar
                verificar_esquema_al_iniciar()
                    
            except Exception as e:
                logger.warning(f"ISS-001: No se pudo validar esquema: {e}")

