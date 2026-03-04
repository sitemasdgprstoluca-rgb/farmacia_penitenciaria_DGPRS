"""
inventario/utils/realtime.py
============================
Utilidad transversal para publicar eventos en tiempo real.

Arquitectura (segura y sin WebSockets propios):
    1. Después del commit de la transacción principal, se inserta una fila en la tabla
       `realtime_events` (solo metadatos, sin datos sensibles).
    2. Supabase Realtime detecta el INSERT y multicast la fila a todos los clientes
       suscritos al canal.
    3. Cada cliente reacciona haciendo un refetch a la API DRF normal (que aplica
       permisos/filtros). Nadie recibe datos que no le correspondan.

Seguridad:
    - La tabla realtime_events SOLO contiene: event_type, entity, entity_id, scope_id.
    - NO se almacena ni transmite información clínica, conteos de stock, nombres de
      medicamentos ni datos personales.
    - Las filas se auto-limpian cada 10 minutos para mantener la tabla pequeña.
    - Si la publicación falla (p.ej. tabla no existe), el error se logea como warning
      y NO interrumpe el flujo de la operación principal.

Uso:
    from inventario.utils.realtime import on_commit_publish

    # Dentro de una vista, después de modified/created/saved algún recurso:
    on_commit_publish('created', 'movimiento', movimiento.id, scope_id=centro_id)
    on_commit_publish('updated', 'requisicion', req.id)
    on_commit_publish('confirmed', 'movimiento', movimiento_id)
"""

import logging

from django.db import transaction, connections

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Core publish — se ejecuta DESPUÉS del commit (llamado desde on_commit_publish)
# ─────────────────────────────────────────────────────────────────────────────

def publish_event(event_type: str, entity: str, entity_id: int, scope_id: int | None = None) -> None:
    """
    Inserta una fila en realtime_events para que Supabase Realtime la emita.

    Siempre silencia excepciones para nunca romper el flujo principal.

    Args:
        event_type: 'created' | 'updated' | 'deleted' | 'confirmed' | 'cancelled' | 'surtido'
        entity:     'movimiento' | 'requisicion' | 'lote' | 'salida_masiva'
        entity_id:  ID del objeto afectado
        scope_id:   (opcional) ID del centro / almacén para filtrar suscripciones
    """
    try:
        with connections['default'].cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO realtime_events (event_type, entity, entity_id, scope_id)
                VALUES (%s, %s, %s, %s)
                """,
                [event_type, entity, int(entity_id), scope_id],
            )
            # Auto-cleanup: mantener la tabla liviana
            cursor.execute(
                "DELETE FROM realtime_events WHERE created_at < NOW() - INTERVAL '10 minutes'"
            )
    except Exception as exc:
        logger.warning(
            '[realtime] publish_event falló (no crítico) — '
            'entity=%s type=%s id=%s: %s',
            entity, event_type, entity_id, exc,
        )


# ─────────────────────────────────────────────────────────────────────────────
# on_commit_publish — API pública usada en las vistas
# ─────────────────────────────────────────────────────────────────────────────

def on_commit_publish(event_type: str, entity: str, entity_id: int, scope_id: int | None = None) -> None:
    """
    Programa la publicación del evento para DESPUÉS de que el commit actual tenga éxito.

    Si se llama fuera de una transacción atómica, Django ejecuta la callback de inmediato
    (autocommit). Si la transacción hace rollback, el evento NO se publica.

    Args:
        event_type: Tipo de evento ('created', 'updated', 'confirmed', 'cancelled', 'surtido', ...)
        entity:     Nombre de la entidad afectada ('movimiento', 'requisicion', 'lote', ...)
        entity_id:  ID numérico del objeto
        scope_id:   (opcional) ID del centro/almacén — permite al frontend filtrar por ámbito
    """
    # Capturar argumentos en closure para que el lambda no pierda la referencia
    _etype, _entity, _eid, _sid = event_type, entity, entity_id, scope_id
    transaction.on_commit(lambda: publish_event(_etype, _entity, _eid, _sid))
