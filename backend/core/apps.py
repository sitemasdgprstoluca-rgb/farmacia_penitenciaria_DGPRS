from django.apps import AppConfig
import logging
import os
import threading

logger = logging.getLogger(__name__)


def _sincronizar_fechas_lotes_bg():
    """
    Sincroniza fecha_fabricacion de lotes usando parcialidades.
    Ejecuta en background para no bloquear el servidor.
    """
    try:
        from django.db import connection
        # Esperar a que la conexión esté lista
        connection.ensure_connection()
        
        from core.models import Lote, LoteParcialidad
        from django.db import transaction
        from django.utils import timezone
        
        # Buscar lotes sin fecha_fabricacion
        lotes_sin_fecha = Lote.objects.filter(
            fecha_fabricacion__isnull=True,
            activo=True
        ).count()
        
        if lotes_sin_fecha == 0:
            logger.info("[SYNC-FECHAS] Todos los lotes tienen fecha_fabricacion")
            return
        
        logger.info(f"[SYNC-FECHAS] Sincronizando {lotes_sin_fecha} lotes sin fecha...")
        
        actualizados = 0
        with transaction.atomic():
            for lote in Lote.objects.filter(fecha_fabricacion__isnull=True, activo=True):
                # Buscar primera parcialidad
                parcialidad = LoteParcialidad.objects.filter(
                    lote=lote
                ).order_by('fecha_entrega').first()
                
                if parcialidad and parcialidad.fecha_entrega:
                    lote.fecha_fabricacion = parcialidad.fecha_entrega
                else:
                    # Fallback a fecha actual
                    lote.fecha_fabricacion = timezone.now().date()
                
                lote.save(update_fields=['fecha_fabricacion'])
                actualizados += 1
        
        logger.info(f"[SYNC-FECHAS] ✓ {actualizados} lotes actualizados")
        
    except Exception as e:
        logger.warning(f"[SYNC-FECHAS] Error en sincronización: {e}")


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    label = 'core'
    verbose_name = 'Core del Sistema'

    def ready(self):
        # Importar signals al iniciar la app
        from . import signals  # noqa: F401
        
        # Auto-sincronizar fechas de lotes en background (no bloquea startup)
        # Solo se ejecuta una vez al iniciar el servidor
        if os.environ.get('RUN_MAIN') != 'true':  # Solo en el proceso principal
            sync_thread = threading.Thread(target=_sincronizar_fechas_lotes_bg, daemon=True)
            sync_thread.start()
        
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

