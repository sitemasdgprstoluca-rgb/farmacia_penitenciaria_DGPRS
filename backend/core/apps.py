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
        
        # ISS-001 FIX: Validación de esquema DESHABILITADA por defecto
        # La validación bloquea el inicio del servidor al conectarse a la BD
        # y causa timeouts en Render/producción (especialmente con Supabase).
        # 
        # Para habilitar manualmente: ENABLE_SCHEMA_VALIDATION=1
        # 
        # IMPORTANTE: No validar durante el inicio del servidor porque:
        # 1. Bloquea el binding del puerto (Render detecta "no open ports")
        # 2. Los timeouts de conexión a Supabase causan retrasos de ~4 minutos
        # 3. La validación debería ser un proceso separado, no parte del startup
        
        enable_validation = os.environ.get('ENABLE_SCHEMA_VALIDATION', '0') == '1'
        
        if enable_validation:
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

