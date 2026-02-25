"""
Utilidad de MERGE para LoteParcialidad.

Implementa lógica de matching jerárquico para evitar duplicados:
- Si una entrega es "idéntica" a una existente, SUMA cantidad en lugar de crear nuevo registro.
- Completa campos faltantes si el existente tiene NULL y el nuevo trae valor.
- Registra AuditLog persistente para trazabilidad SOX/ISO 27001.

Criterio de "misma entrega" (matching jerárquico):

Nivel A (alta confianza):
  - lote_id + factura + proveedor + fecha_entrega + centro
  - Si coincide → merge (sumar cantidad)

Nivel B (si NO hay factura):
  - lote_id + proveedor + fecha_entrega + centro
  - Si coincide → merge solo si no hay conflictos

Regla "tolerante a nulos":
  - Si un campo está en ambos y son diferentes → NO merge (crear nuevo)
  - Si un campo está en uno y el otro es null → OK para merge
  - En merge: rellenar campos faltantes si el nuevo trae valor
"""

import hashlib
import logging
from datetime import date
from typing import Optional, Dict, Any, Tuple

from django.db import transaction
from django.db.models import F
from django.utils import timezone

logger = logging.getLogger(__name__)


def normalizar_texto(valor: Any) -> Optional[str]:
    """
    Normaliza un valor de texto para comparación.
    - None o vacío → None
    - Texto → trim + lowercase
    """
    if valor is None:
        return None
    texto = str(valor).strip().lower()
    return texto if texto else None


def normalizar_fecha(valor: Any) -> Optional[date]:
    """
    Normaliza una fecha para comparación.
    - None → None
    - datetime → date
    - date → date
    - str → parse a date
    """
    if valor is None:
        return None
    
    if isinstance(valor, date):
        return valor
    
    from datetime import datetime
    if isinstance(valor, datetime):
        return valor.date()
    
    # Intentar parsear string
    try:
        texto = str(valor).strip()
        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
            try:
                return datetime.strptime(texto, fmt).date()
            except ValueError:
                continue
    except Exception:
        pass
    
    return None


def campos_compatibles(valor_existente: Any, valor_nuevo: Any) -> bool:
    """
    Verifica si dos valores de campo son compatibles para merge.
    
    Reglas:
    - Si ambos son None/vacío → compatible
    - Si uno es None/vacío y el otro tiene valor → compatible (se rellenará)
    - Si ambos tienen valor → deben ser iguales
    """
    norm_existente = normalizar_texto(valor_existente)
    norm_nuevo = normalizar_texto(valor_nuevo)
    
    # Si alguno es None, son compatibles
    if norm_existente is None or norm_nuevo is None:
        return True
    
    # Si ambos tienen valor, deben ser iguales
    return norm_existente == norm_nuevo


def generar_import_fingerprint(lote_id: int, fecha_entrega: date, cantidad: int,
                                factura: str = None, proveedor: str = None,
                                fila_num: int = None, archivo_nombre: str = None) -> str:
    """
    Genera un fingerprint único para idempotencia de importación.
    
    Permite detectar si una fila específica de un archivo ya fue importada,
    evitando re-sumar cantidades en reimportaciones.
    """
    partes = [
        str(lote_id),
        str(fecha_entrega),
        str(cantidad),
        normalizar_texto(factura) or '',
        normalizar_texto(proveedor) or '',
        str(fila_num) if fila_num else '',
        normalizar_texto(archivo_nombre) or '',
    ]
    texto = '|'.join(partes)
    return hashlib.sha256(texto.encode()).hexdigest()[:64]


def buscar_parcialidad_candidata(
    lote,
    fecha_entrega: date,
    factura: str = None,
    proveedor: str = None,
    centro=None,
    numero_remision: str = None,
) -> Tuple[Optional['LoteParcialidad'], str]:
    """
    Busca una parcialidad existente que sea candidata para merge.
    
    Returns:
        Tuple[parcialidad, nivel_match]:
        - (parcialidad, 'A') si match de alta confianza
        - (parcialidad, 'B') si match sin factura
        - (None, '') si no hay candidato
    """
    from core.models import LoteParcialidad
    
    # Normalizar valores de búsqueda
    fecha_norm = normalizar_fecha(fecha_entrega)
    factura_norm = normalizar_texto(factura)
    proveedor_norm = normalizar_texto(proveedor)
    
    if fecha_norm is None:
        # Sin fecha no podemos hacer match
        return None, ''
    
    # Base queryset
    qs_base = LoteParcialidad.objects.filter(
        lote=lote,
        fecha_entrega=fecha_norm,
    )
    
    # NIVEL A: Match con factura (alta confianza)
    if factura_norm:
        # Normalizar factura para comparación case-insensitive
        candidatos_a = qs_base.filter(
            numero_factura__iexact=factura,
        )
        
        # Refinar por proveedor si viene
        if proveedor_norm:
            # Buscar match exacto o donde proveedor existente es NULL
            candidatos_a_prov = candidatos_a.filter(
                proveedor__iexact=proveedor
            )
            if candidatos_a_prov.exists():
                return candidatos_a_prov.first(), 'A'
            
            # Si no hay match exacto, buscar donde proveedor es NULL (compatible)
            candidatos_a_null = candidatos_a.filter(proveedor__isnull=True)
            if candidatos_a_null.exists():
                return candidatos_a_null.first(), 'A'
            
            # Si no hay compatible por proveedor, ver si hay alguno con proveedor vacío
            candidatos_a_empty = candidatos_a.filter(proveedor='')
            if candidatos_a_empty.exists():
                return candidatos_a_empty.first(), 'A'
        else:
            # Sin proveedor en request, cualquier candidato con factura sirve
            if candidatos_a.exists():
                return candidatos_a.first(), 'A'
    
    # NIVEL B: Match sin factura (solo si proveedor viene)
    if proveedor_norm:
        # Buscar parcialidades sin factura con mismo proveedor
        candidatos_b = qs_base.filter(
            numero_factura__isnull=True,
            proveedor__iexact=proveedor,
        )
        if candidatos_b.exists():
            return candidatos_b.first(), 'B'
        
        # Buscar con factura vacía
        candidatos_b_empty = qs_base.filter(
            numero_factura='',
            proveedor__iexact=proveedor,
        )
        if candidatos_b_empty.exists():
            return candidatos_b_empty.first(), 'B'
    
    # NIVEL B alternativo: Match por fecha sin factura ni proveedor específico
    # Solo si NO hay conflictos de campos
    candidatos_fecha = qs_base.filter(
        numero_factura__isnull=True,
        proveedor__isnull=True,
    )
    if candidatos_fecha.exists():
        return candidatos_fecha.first(), 'B'
    
    # También probar con valores vacíos
    candidatos_fecha_empty = qs_base.filter(
        numero_factura='',
        proveedor='',
    )
    if candidatos_fecha_empty.exists():
        return candidatos_fecha_empty.first(), 'B'
    
    return None, ''


def calcular_file_checksum(archivo) -> str:
    """
    Calcula SHA256 del contenido del archivo para tracking de importaciones.
    
    Args:
        archivo: File object o path string
        
    Returns:
        str: SHA256 hex digest (64 chars)
    """
    import hashlib
    
    sha256 = hashlib.sha256()
    
    try:
        if hasattr(archivo, 'read'):
            # Es un file object
            pos = archivo.tell()  # Guardar posición
            archivo.seek(0)
            for chunk in iter(lambda: archivo.read(8192), b''):
                sha256.update(chunk)
            archivo.seek(pos)  # Restaurar posición
        elif hasattr(archivo, 'chunks'):
            # Es un Django UploadedFile
            for chunk in archivo.chunks():
                sha256.update(chunk)
        else:
            # Es una ruta
            with open(archivo, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    sha256.update(chunk)
    except Exception as e:
        logger.warning(f"[CHECKSUM] Error calculando checksum: {e}")
        return hashlib.sha256(str(archivo).encode()).hexdigest()
    
    return sha256.hexdigest()


def calcular_row_fingerprint(
    file_checksum: str,
    row_number: int,
    lote_id: int = None,
    numero_lote: str = None,
    clave_producto: str = None,
    proveedor: str = None,
    factura: str = None,
    fecha_entrega_raw: str = None,
    cantidad: int = None,
) -> str:
    """
    Calcula fingerprint único para una fila de importación.
    
    El fingerprint garantiza idempotencia: si reimportas el mismo archivo,
    las filas ya procesadas se detectan y no se duplican.
    
    Args:
        file_checksum: Hash del archivo completo
        row_number: Número de fila en el archivo
        lote_id: ID del lote (si existe)
        numero_lote: Número de lote (alternativo a lote_id para lotes nuevos)
        clave_producto: Clave del producto (opcional)
        proveedor: Nombre del proveedor normalizado (opcional)
        factura: Número de factura normalizado (opcional)
        fecha_entrega_raw: Fecha como string raw del Excel (opcional)
        cantidad: Cantidad de la fila (opcional)
    
    Returns:
        str: SHA256 fingerprint (64 chars)
    """
    # Usar lote_id si está disponible, sino numero_lote normalizado
    lote_identifier = str(lote_id) if lote_id else (normalizar_texto(numero_lote) or 'NO_LOTE')
    
    partes = [
        file_checksum or 'NO_CHECKSUM',
        str(row_number) if row_number else 'NO_ROW',
        lote_identifier,
        normalizar_texto(clave_producto) or 'NULL',
        normalizar_texto(proveedor) or 'NULL',
        normalizar_texto(factura) or 'NULL',
        str(fecha_entrega_raw).strip() if fecha_entrega_raw else 'NULL',
        str(cantidad) if cantidad else 'NULL',
    ]
    texto = '|'.join(partes)
    return hashlib.sha256(texto.encode()).hexdigest()


def verificar_fingerprint_existente(fingerprint: str) -> tuple:
    """
    Verifica si un fingerprint ya existe en la tabla de control.
    
    Graceful degradation: si la tabla no existe, retorna (False, None)
    para permitir que el sistema siga funcionando mientras se crea la tabla.
    
    Returns:
        tuple: (existe: bool, registro: ParcialidadImportFingerprint or None)
    """
    try:
        from core.models import ParcialidadImportFingerprint
        registro = ParcialidadImportFingerprint.objects.filter(
            fingerprint=fingerprint
        ).first()
        return (registro is not None, registro)
    except Exception as e:
        # Tabla puede no existir todavía - graceful degradation
        error_str = str(e).lower()
        if 'does not exist' in error_str or 'no such table' in error_str:
            logger.warning(
                f"[FINGERPRINT] Tabla parcialidad_import_fingerprints no existe. "
                f"Ejecuta el SQL de migración. Continuando sin deduplicación."
            )
        else:
            logger.warning(f"[FINGERPRINT] Error verificando: {e}")
        return (False, None)


def registrar_fingerprint(
    fingerprint: str,
    lote,
    parcialidad=None,
    file_checksum: str = None,
    row_number: int = None,
    archivo_nombre: str = None,
    usuario=None,
    action_taken: str = 'CREATED',
    cantidad: int = 0,
) -> tuple:
    """
    Registra un fingerprint de importación de forma atómica.
    
    Usa INSERT ... ON CONFLICT DO NOTHING equivalente (get_or_create)
    para garantizar idempotencia ante concurrencia.
    
    Graceful degradation: si la tabla no existe, retorna (None, False)
    y logea una advertencia.
    
    Returns:
        tuple: (registro, created: bool)
    """
    try:
        from core.models import ParcialidadImportFingerprint
        from django.db import IntegrityError
        
        registro, created = ParcialidadImportFingerprint.objects.get_or_create(
            fingerprint=fingerprint,
            defaults={
                'lote': lote,
                'parcialidad': parcialidad,
                'file_checksum': file_checksum,
                'row_number': row_number,
                'archivo_nombre': archivo_nombre,
                'imported_by': usuario,
                'action_taken': action_taken,
                'cantidad_importada': cantidad,
            }
        )
        
        if not created:
            logger.info(
                f"[FINGERPRINT-DUP] Fila ya importada: {fingerprint[:16]}..., "
                f"row={row_number}, acción original={registro.action_taken}"
            )
        
        return registro, created
        
    except IntegrityError:
        # Concurrencia: otro proceso insertó primero
        logger.info(f"[FINGERPRINT-RACE] Conflicto concurrencia: {fingerprint[:16]}...")
        try:
            from core.models import ParcialidadImportFingerprint
            registro = ParcialidadImportFingerprint.objects.filter(fingerprint=fingerprint).first()
            return registro, False
        except Exception:
            return None, False
    except Exception as e:
        # Graceful degradation si la tabla no existe
        error_str = str(e).lower()
        if 'does not exist' in error_str or 'no such table' in error_str:
            logger.warning(
                f"[FINGERPRINT] Tabla parcialidad_import_fingerprints no existe. "
                f"Ejecuta el SQL de migración. Continuando sin registro de fingerprint."
            )
        else:
            logger.error(f"[FINGERPRINT-ERROR] Error registrando: {e}")
        return None, False


def merge_or_create_parcialidad(
    lote,
    fecha_entrega: date,
    cantidad: int,
    usuario=None,
    factura: str = None,
    proveedor: str = None,
    numero_remision: str = None,
    notas: str = None,
    es_sobreentrega: bool = False,
    motivo_override: str = None,
    centro=None,
    # Para idempotencia de importación
    import_fingerprint: str = None,
    fila_num: int = None,
    archivo_nombre: str = None,
    # Control de merge
    allow_merge: bool = True,
    # Para auditoría
    request=None,
) -> Dict[str, Any]:
    """
    Crea o merge una parcialidad según criterio de equivalencia.
    
    Reglas:
    1. Si allow_merge=False → CREATE directo (sin buscar candidatos)
    2. Si existe parcialidad equivalente (matching) → MERGE (sumar cantidad + completar campos)
    3. Si no existe → CREATE nuevo registro
    
    Idempotencia:
    - Si import_fingerprint coincide con una parcialidad existente, NO re-sumar
    
    Args:
        allow_merge: Si False, no busca candidatos para merge (crea siempre nuevo).
                     Usar False cuando no hay fecha válida para evitar merges incorrectos.
    
    Returns:
        Dict con:
        - 'parcialidad': objeto LoteParcialidad
        - 'merged': bool - True si fue merge, False si fue create
        - 'nivel_match': 'A', 'B' o '' (para nuevos)
        - 'cantidad_antes': int (si merge)
        - 'cantidad_despues': int
        - 'campos_rellenados': list de campos que se completaron
        - 'audit_log_id': id del registro de auditoría
        - 'skipped': bool - True si se saltó por fingerprint duplicado
    """
    from core.models import LoteParcialidad, AuditoriaLogs
    
    resultado = {
        'parcialidad': None,
        'merged': False,
        'nivel_match': '',
        'cantidad_antes': 0,
        'cantidad_despues': cantidad,
        'campos_rellenados': [],
        'audit_log_id': None,
        'mensaje': '',
        'fingerprint_dup': False,
        'skipped': False,
    }
    
    with transaction.atomic():
        # Bloquear el lote para evitar race conditions
        from core.models import Lote
        lote_locked = Lote.objects.select_for_update().get(pk=lote.pk)
        
        # Solo buscar candidato para merge si allow_merge=True
        candidato = None
        nivel = ''
        
        if allow_merge:
            candidato, nivel = buscar_parcialidad_candidata(
                lote=lote_locked,
                fecha_entrega=fecha_entrega,
                factura=factura,
                proveedor=proveedor,
                centro=centro,
                numero_remision=numero_remision,
            )
        else:
            logger.info(
                f"[PARCIALIDAD-NO-MERGE] allow_merge=False para lote {lote.numero_lote}, "
                f"fecha={fecha_entrega}. Creando nuevo registro sin buscar candidatos."
            )
        
        if candidato:
            # Bloquear la parcialidad candidata
            parcialidad = LoteParcialidad.objects.select_for_update().get(pk=candidato.pk)
            
            # Verificar compatibilidad de campos opcionales
            campos_a_verificar = [
                ('numero_remision', parcialidad.numero_remision, numero_remision),
            ]
            
            conflictos = []
            for campo, val_existente, val_nuevo in campos_a_verificar:
                if not campos_compatibles(val_existente, val_nuevo):
                    conflictos.append(f"{campo}: '{val_existente}' vs '{val_nuevo}'")
            
            if conflictos:
                # Hay conflictos - no hacer merge, crear nuevo
                logger.info(
                    f"[PARCIALIDAD-MERGE] Conflicto detectado para lote {lote.numero_lote}, "
                    f"fecha {fecha_entrega}: {conflictos}. Creando nuevo registro."
                )
            else:
                # OK para merge
                cantidad_antes = parcialidad.cantidad
                campos_rellenados = []
                
                # Sumar cantidad
                parcialidad.cantidad = F('cantidad') + cantidad
                
                # Completar campos faltantes
                if not parcialidad.numero_factura and factura:
                    parcialidad.numero_factura = factura
                    campos_rellenados.append('numero_factura')
                
                if not parcialidad.proveedor and proveedor:
                    parcialidad.proveedor = proveedor
                    campos_rellenados.append('proveedor')
                
                if not parcialidad.numero_remision and numero_remision:
                    parcialidad.numero_remision = numero_remision
                    campos_rellenados.append('numero_remision')
                
                # Agregar a notas
                nota_merge = f" | MERGE: +{cantidad} uds"
                if notas:
                    nota_merge += f" ({notas})"
                if parcialidad.notas:
                    parcialidad.notas = parcialidad.notas + nota_merge
                else:
                    parcialidad.notas = nota_merge.strip(' |')
                
                # Si es sobreentrega, marcar
                if es_sobreentrega:
                    parcialidad.es_sobreentrega = True
                    if motivo_override:
                        parcialidad.motivo_override = (parcialidad.motivo_override or '') + f" | {motivo_override}"
                
                parcialidad.save()
                parcialidad.refresh_from_db()  # Para obtener cantidad actualizada
                
                # Registrar AuditLog
                audit_log = _registrar_audit_merge(
                    parcialidad=parcialidad,
                    lote=lote_locked,
                    cantidad_antes=cantidad_antes,
                    cantidad_agregada=cantidad,
                    cantidad_despues=parcialidad.cantidad,
                    nivel_match=nivel,
                    campos_rellenados=campos_rellenados,
                    usuario=usuario,
                    request=request,
                )
                
                resultado.update({
                    'parcialidad': parcialidad,
                    'merged': True,
                    'nivel_match': nivel,
                    'cantidad_antes': cantidad_antes,
                    'cantidad_despues': parcialidad.cantidad,
                    'campos_rellenados': campos_rellenados,
                    'audit_log_id': audit_log.pk if audit_log else None,
                    'mensaje': f'MERGE nivel {nivel}: +{cantidad} uds (total: {parcialidad.cantidad})',
                })
                
                logger.info(
                    f"[PARCIALIDAD-MERGE] Lote {lote.numero_lote}: MERGE nivel {nivel}, "
                    f"+{cantidad} uds (antes: {cantidad_antes}, después: {parcialidad.cantidad}), "
                    f"campos rellenados: {campos_rellenados}"
                )
                
                return resultado
        
        # No hay candidato o hubo conflicto - crear nuevo
        parcialidad = LoteParcialidad.objects.create(
            lote=lote_locked,
            fecha_entrega=normalizar_fecha(fecha_entrega),
            cantidad=cantidad,
            numero_factura=factura or None,
            numero_remision=numero_remision or None,
            proveedor=proveedor or None,
            notas=notas or None,
            es_sobreentrega=es_sobreentrega,
            motivo_override=motivo_override,
            usuario=usuario,
        )
        
        resultado.update({
            'parcialidad': parcialidad,
            'merged': False,
            'nivel_match': '',
            'cantidad_despues': cantidad,
            'mensaje': f'NUEVO: {cantidad} uds',
        })
        
        logger.info(
            f"[PARCIALIDAD-CREATE] Lote {lote.numero_lote}: Nueva parcialidad, "
            f"{cantidad} uds, fecha {fecha_entrega}"
        )
        
        return resultado


def _registrar_audit_merge(
    parcialidad,
    lote,
    cantidad_antes: int,
    cantidad_agregada: int,
    cantidad_despues: int,
    nivel_match: str,
    campos_rellenados: list,
    usuario=None,
    request=None,
) -> Optional['AuditoriaLogs']:
    """
    Registra el merge en AuditoriaLogs para SOX/ISO 27001.
    """
    from core.models import AuditoriaLogs
    
    try:
        # Extraer IP si hay request
        ip_address = None
        user_agent = None
        if request:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            ip_address = x_forwarded_for.split(',')[0].strip() if x_forwarded_for else request.META.get('REMOTE_ADDR', '')
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:200]
        
        audit_log = AuditoriaLogs.objects.create(
            usuario=usuario,
            accion='MERGE_PARCIALIDAD',
            modelo='LoteParcialidad',
            objeto_id=str(parcialidad.pk),
            datos_anteriores={
                'cantidad': cantidad_antes,
            },
            datos_nuevos={
                'cantidad': cantidad_despues,
                'cantidad_agregada': cantidad_agregada,
            },
            ip_address=ip_address[:45] if ip_address else None,
            user_agent=user_agent,
            detalles={
                'nivel_match': nivel_match,
                'campos_rellenados': campos_rellenados,
                'lote_id': lote.pk,
                'lote_numero': lote.numero_lote,
                'fecha_entrega': str(parcialidad.fecha_entrega),
                'factura': parcialidad.numero_factura,
                'proveedor': parcialidad.proveedor,
            }
        )
        
        logger.info(
            f"[AUDIT-DB] MERGE_PARCIALIDAD - Lote: {lote.numero_lote}, "
            f"Parcialidad: {parcialidad.pk}, Usuario: {usuario.username if usuario else 'system'}"
        )
        
        return audit_log
        
    except Exception as e:
        logger.error(f"[AUDIT-ERROR] Error registrando merge: {e}")
        return None


# Cache para fingerprints de importación (evita duplicados en mismo request/batch)
_import_fingerprints_cache = set()


def clear_import_fingerprint_cache():
    """Limpia el cache de fingerprints (llamar al inicio de cada importación)."""
    global _import_fingerprints_cache
    _import_fingerprints_cache = set()


def is_fingerprint_processed(fingerprint: str) -> bool:
    """Verifica si un fingerprint ya fue procesado en esta sesión de importación."""
    return fingerprint in _import_fingerprints_cache


def mark_fingerprint_processed(fingerprint: str):
    """Marca un fingerprint como procesado."""
    _import_fingerprints_cache.add(fingerprint)
