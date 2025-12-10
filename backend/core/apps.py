from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    label = 'core'
    verbose_name = 'Core del Sistema'

    def ready(self):
        # Importar signals al iniciar la app
        from . import signals  # noqa: F401
        
        # ISS-001 FIX (audit8): Validar esquemas de tablas unmanaged al iniciar
        # Solo ejecutar si no estamos en modo de migración o test
        import sys
        if 'migrate' not in sys.argv and 'makemigrations' not in sys.argv:
            try:
                from core.schema_validator import validate_unmanaged_schemas, check_transitions_constraint
                
                # Validar esquemas (solo warning, no bloquear inicio)
                results = validate_unmanaged_schemas(raise_on_error=False)
                
                # Verificar constraints de estados
                check_transitions_constraint()
                
                # Resumen
                total_errors = sum(len(e) for e in results.values())
                if total_errors:
                    logger.warning(
                        f"ISS-001: Validación de esquema completada con {total_errors} advertencia(s). "
                        "Ver logs para detalles."
                    )
                else:
                    logger.info("ISS-001: Validación de esquema completada sin errores.")
                    
            except Exception as e:
                # No bloquear inicio de la app por errores de validación
                logger.warning(f"ISS-001: No se pudo validar esquema: {e}")

