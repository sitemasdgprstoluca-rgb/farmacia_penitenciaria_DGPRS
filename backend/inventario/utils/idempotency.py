"""
Utilidad de idempotencia transversal para todos los endpoints de escritura.

USO:
----
    from inventario.utils.idempotency import idempotent_action

    @idempotent_action('mi_endpoint')
    def mi_vista(request):
        ...
        return Response(data, status=201)

    # O como función utilitaria (para class-based views):
    from inventario.utils.idempotency import check_idempotency, save_idempotency

    hit, cached = check_idempotency(request)
    if hit:
        return cached

    # ... procesar ...
    save_idempotency(request, 'endpoint', request_id, response_data, 201)

PROTOCOLO:
----------
- El frontend envía `client_request_id` (UUID v4) en el body o como header
  `X-Idempotency-Key` de cada request de escritura.
- Si la clave ya existe → devuelve la respuesta cacheada (evita duplicados).
- Si no existe → procesa normalmente y cachea el resultado.
- Estado 'processing' se guarda antes del procesamiento para detectar
  operaciones largas concurrentes.
- TTL: 24 horas (limpieza vía pg_cron o tarea periódica).
"""

import hashlib
import json
import logging
import functools

from rest_framework.response import Response
from rest_framework import status as drf_status

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
STATUS_PROCESSING = 'processing'
STATUS_SUCCESS    = 'success'
STATUS_FAILED     = 'failed'

IDEMPOTENCY_HEADER = 'HTTP_X_IDEMPOTENCY_KEY'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_key(request) -> str | None:
    """
    Extrae el client_request_id del body o del header X-Idempotency-Key.
    Retorna None si no se envió.
    """
    # 1. Body (JSON)
    key = None
    try:
        key = request.data.get('client_request_id')
    except Exception:
        pass

    # 2. Header (X-Idempotency-Key) — útil para PUT/PATCH/DELETE sin body JSON
    if not key:
        key = request.META.get(IDEMPOTENCY_HEADER)

    return key or None


def _payload_hash(request) -> str:
    """SHA-256 del body para detectar retries con payload distinto."""
    try:
        raw = json.dumps(request.data, sort_keys=True, default=str)
    except Exception:
        raw = str(request.data)
    return hashlib.sha256(raw.encode()).hexdigest()


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def check_idempotency(request, endpoint: str = '') -> tuple[bool, Response | None]:
    """
    Verifica si la request ya fue procesada.

    Returns:
        (True,  Response)  → Hit:   devolver inmediatamente.
        (False, None)      → Miss:  procesar normalmente.
        (True,  Response(409)) → Conflicto: operación en curso.
    """
    from core.models import IdempotencyKey  # import tardío para evitar circular

    key = _get_key(request)
    if not key:
        return False, None

    try:
        existing = IdempotencyKey.objects.filter(key=key).first()
    except Exception as exc:
        logger.warning(f'[Idempotency] Error al consultar clave {key}: {exc}')
        return False, None

    if not existing:
        return False, None

    if existing.status == STATUS_PROCESSING:
        logger.info(f'[Idempotency] CONFLICT key={key} endpoint={endpoint} '
                    f'user={request.user.username}')
        return True, Response(
            {'error': True, 'message': 'Operación en curso. Inténtalo de nuevo en unos segundos.'},
            status=drf_status.HTTP_409_CONFLICT
        )

    logger.info(f'[Idempotency] HIT key={key} endpoint={endpoint} '
                f'user={request.user.username} status={existing.status}')
    return True, Response(existing.response_data, status=existing.response_status)


def save_idempotency(
    request,
    endpoint: str,
    key: str,
    response_data: dict,
    response_status: int = 201,
    op_status: str = STATUS_SUCCESS,
) -> None:
    """
    Persiste el resultado de la operación en IdempotencyKey.
    Usa get_or_create para ser thread-safe (constraint UNIQUE en DB).
    """
    from core.models import IdempotencyKey  # import tardío

    try:
        obj, created = IdempotencyKey.objects.get_or_create(
            key=key,
            defaults={
                'endpoint': endpoint,
                'user': request.user,
                'payload_hash': _payload_hash(request),
                'status': op_status,
                'response_data': response_data,
                'response_status': response_status,
            }
        )
        if not created and obj.status == STATUS_PROCESSING:
            # Actualizar el registro 'processing' con el resultado final
            obj.status = op_status
            obj.response_data = response_data
            obj.response_status = response_status
            obj.save(update_fields=['status', 'response_data', 'response_status'])
        logger.debug(f'[Idempotency] SAVED key={key} endpoint={endpoint} '
                     f'created={created} status={op_status}')
    except Exception as exc:
        # No propagar — la operación ya se completó; solo loggear
        logger.warning(f'[Idempotency] No se pudo guardar clave {key}: {exc}')


def mark_processing(request, endpoint: str, key: str) -> None:
    """
    Marca la operación como 'processing' antes de iniciar trabajo pesado.
    Permite detectar concurrencia (dos requests con la misma clave al mismo tiempo).
    """
    from core.models import IdempotencyKey

    try:
        IdempotencyKey.objects.get_or_create(
            key=key,
            defaults={
                'endpoint': endpoint,
                'user': request.user,
                'payload_hash': _payload_hash(request),
                'status': STATUS_PROCESSING,
                'response_data': {},
                'response_status': 202,
            }
        )
    except Exception as exc:
        logger.warning(f'[Idempotency] No se pudo marcar processing clave {key}: {exc}')


# ---------------------------------------------------------------------------
# Decorador para function-based views
# ---------------------------------------------------------------------------

def idempotent_action(endpoint: str):
    """
    Decorador para views que modifiquen estado.

    Uso:
        @api_view(['POST'])
        @idempotent_action('salida_masiva')
        def mi_vista(request):
            ...
            return Response(data, status=201)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            hit, cached = check_idempotency(request, endpoint)
            if hit:
                return cached

            # Obtener key para guardar después
            key = _get_key(request)

            response = func(request, *args, **kwargs)

            # Solo guardar respuestas exitosas (2xx) para idempotencia
            if key and 200 <= response.status_code < 300:
                resp_data = getattr(response, 'data', {})
                if hasattr(resp_data, 'items'):
                    resp_data = dict(resp_data)
                save_idempotency(request, endpoint, key, resp_data, response.status_code)

            return response
        return wrapper
    return decorator
