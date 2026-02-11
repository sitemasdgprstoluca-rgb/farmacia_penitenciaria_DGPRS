"""
Módulo para salida masiva de inventario - Solo Farmacia
Permite agregar múltiples productos/lotes a una lista y procesarlos de una vez
con generación de hoja de entrega para firma.

FLUJO DE TRANSFERENCIAS A CENTROS PENITENCIARIOS:
================================================

FASE ACTUAL - Transferencia CON retención en centro:
    1. Farmacia hace salida masiva con auto_confirmar=True (default)
    2. Stock se descuenta INMEDIATAMENTE del lote de Farmacia Central
    3. Se CREA lote espejo en centro destino con la cantidad transferida
    4. El inventario PERMANECE en el centro destino para gestión manual
    5. El centro puede registrar salidas (dispensación, consumo, etc.) manualmente
    6. Movimientos: SALIDA en Central + ENTRADA en Centro (sin dispensación automática)

GESTIÓN EN CENTRO:
    1. El centro verá su lote con el stock recibido
    2. Deberán registrar SALIDAS para justificar consumo:
       - Salida por receta (dispensación a pacientes)
       - Consumo interno
       - Merma/caducidad
    3. Si hay diferencias inexplicables → AJUSTE con justificación obligatoria

AUDITORÍA:
    - Todo movimiento tiene usuario, fecha y motivo
    - Ajustes negativos requieren justificación ≥10 caracteres (ISS-003)
    - Trazabilidad completa: Farmacia Central → Centro → Consumo final
    - Hoja de entrega firmada como respaldo físico

NOTA: Las salidas masivas desde Farmacia Central (centro_id=NULL en lotes)
hacia centros penitenciarios se registran como tipo 'salida' con subtipo_salida='transferencia'
y crean un lote espejo en el centro destino con tipo 'entrada'.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from django.http import HttpResponse
import logging
import uuid

from core.models import Lote, Movimiento, Centro, Producto
from core.permissions import IsFarmaciaRole, IsCentroRole

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsFarmaciaRole])
def salida_masiva(request):
    """
    Procesa una salida masiva de inventario para un centro destino.
    Solo disponible para usuarios con rol Farmacia.
    
    FLUJO SIMPLIFICADO (centros aún sin acceso al sistema):
    - Por defecto auto_confirmar=true → Stock se descuenta inmediatamente
    - Se crea lote espejo en centro destino con movimiento de ENTRADA
    - Se genera hoja de entrega para firma física
    - Historial completo queda registrado
    
    Body esperado:
    {
        "centro_destino_id": 1,
        "observaciones": "Entrega programada",
        "auto_confirmar": true,  // Default: true - descuenta stock inmediatamente
        "items": [
            {"lote_id": 123, "cantidad": 10},
            {"lote_id": 456, "cantidad": 5},
            ...
        ]
    }
    
    Returns:
        - 201: Salida procesada exitosamente con ID de grupo y lista de movimientos
        - 400: Error de validación
        - 403: Sin permisos
    """
    try:
        centro_destino_id = request.data.get('centro_destino_id')
        observaciones = request.data.get('observaciones', '')
        items = request.data.get('items', [])
        # Por defecto auto-confirmar (centros no tienen acceso aún)
        auto_confirmar = request.data.get('auto_confirmar', True)
        # Fecha de salida física (puede diferir de la fecha de procesamiento en el sistema)
        fecha_salida_raw = request.data.get('fecha_salida', None)
        fecha_salida = None
        if fecha_salida_raw:
            from django.utils.dateparse import parse_datetime, parse_date
            from datetime import datetime as dt
            if isinstance(fecha_salida_raw, str):
                fecha_salida = parse_datetime(fecha_salida_raw)
                if not fecha_salida:
                    fecha_parsed = parse_date(fecha_salida_raw)
                    if fecha_parsed:
                        fecha_salida = timezone.make_aware(dt.combine(fecha_parsed, dt.min.time()))
                # Asegurar que siempre sea timezone-aware para evitar comparaciones naive vs aware
                if fecha_salida and timezone.is_naive(fecha_salida):
                    fecha_salida = timezone.make_aware(fecha_salida)
        
        # MOV-FECHA: Validar que fecha_salida no sea futura
        if fecha_salida and fecha_salida > timezone.now():
            return Response({
                'error': True,
                'message': 'La fecha de salida no puede ser una fecha futura.'
            }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        
        # Validaciones básicas
        if not centro_destino_id:
            return Response({
                'error': True,
                'message': 'Debe seleccionar un centro destino'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not items or len(items) == 0:
            return Response({
                'error': True,
                'message': 'Debe agregar al menos un producto a la lista'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verificar centro destino existe
        try:
            centro_destino = Centro.objects.get(pk=centro_destino_id)
        except Centro.DoesNotExist:
            return Response({
                'error': True,
                'message': 'Centro destino no encontrado'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validar items antes de procesar
        errores = []
        items_validos = []
        
        # =====================================================================
        # PERF-FIX: Batch-fetch lotes y stock reservado para evitar N+1 queries
        # Antes: 2 queries por item (get + stock_reservado) = 2N queries
        # Ahora: 2 queries totales para todos los items
        # =====================================================================
        lote_ids = []
        cantidades_por_idx = {}
        for idx, item in enumerate(items, 1):
            lote_id = item.get('lote_id')
            cantidad = item.get('cantidad', 0)
            
            if not lote_id:
                errores.append(f'Item {idx}: Falta ID de lote')
                continue
            if not cantidad or cantidad <= 0:
                errores.append(f'Item {idx}: Cantidad debe ser mayor a 0')
                continue
            
            lote_ids.append(lote_id)
            cantidades_por_idx[lote_id] = cantidades_por_idx.get(lote_id, [])
            cantidades_por_idx[lote_id].append((idx, int(cantidad)))
        
        # Batch-fetch todos los lotes en 1 query
        lotes_map = {}
        if lote_ids:
            lotes_qs = Lote.objects.select_related('producto').filter(pk__in=lote_ids)
            lotes_map = {l.pk: l for l in lotes_qs}
        
        # Batch-calculate stock reservado para todos los lotes en 1 query
        reservado_map = _calcular_stock_reservado_batch(list(lotes_map.values())) if lotes_map else {}
        
        # Validar cada item usando los datos pre-cargados
        for item_raw in items:
            lote_id = item_raw.get('lote_id')
            cantidad = item_raw.get('cantidad', 0)
            if not lote_id or not cantidad or cantidad <= 0:
                continue  # Ya reportado arriba
            
            idx_list = cantidades_por_idx.get(lote_id, [])
            if not idx_list:
                continue
            idx, cantidad_int = idx_list.pop(0)
            
            lote = lotes_map.get(lote_id)
            if not lote:
                errores.append(f'Item {idx}: Lote con ID {lote_id} no encontrado')
                continue
            
            stock_reservado = reservado_map.get(lote.pk, 0)
            stock_disponible = lote.cantidad_actual - stock_reservado
            
            if stock_disponible < cantidad_int:
                errores.append(
                    f'Item {idx}: Stock insuficiente en lote {lote.numero_lote}. '
                    f'Disponible real: {stock_disponible} (total: {lote.cantidad_actual}, reservado: {stock_reservado}), '
                    f'Solicitado: {cantidad_int}'
                )
                continue
            
            items_validos.append({
                'lote': lote,
                'cantidad': cantidad_int
            })
        
        if errores:
            return Response({
                'error': True,
                'message': 'Errores de validación',
                'errores': errores
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Generar ID de grupo para esta salida masiva 
        # ISS-SEC: Formato único SAL-MMDD-HHMM-CentroID-UUID para evitar colisiones
        now = timezone.now()
        timestamp = now.strftime('%m%d-%H%M')
        unique_suffix = uuid.uuid4().hex[:6].upper()
        grupo_salida = f'SAL-{timestamp}-{centro_destino.id}-{unique_suffix}'
        
        movimientos_creados = []
        estado_tag = '[CONFIRMADO]' if auto_confirmar else '[PENDIENTE]'
        
        with transaction.atomic():
            # =====================================================================
            # PERF-FIX: Batch lock todos los lotes en 1 query + batch stock reservado
            # Antes: (select_for_update + stock_reservado + full_clean) * N = ~5N queries
            # Ahora: 2 queries batch + 1 INSERT por item = 2 + N queries
            # =====================================================================
            lote_pks_validos = [item['lote'].pk for item in items_validos]
            lotes_locked_qs = Lote.objects.select_for_update().select_related('producto').filter(pk__in=lote_pks_validos)
            lotes_locked_map = {l.pk: l for l in lotes_locked_qs}
            
            # Re-calcular stock reservado dentro de la transacción (con locks)
            if not auto_confirmar:
                reservado_locked = _calcular_stock_reservado_batch(list(lotes_locked_map.values()))
            else:
                reservado_locked = {}
            
            for item in items_validos:
                lote = item['lote']
                cantidad = item['cantidad']
                
                lote_locked = lotes_locked_map.get(lote.pk)
                if not lote_locked:
                    raise Exception(f'Lote {lote.pk} no encontrado al procesar')
                
                # Re-validar stock disponible (usando datos batch)
                if not auto_confirmar:
                    stock_reservado = reservado_locked.get(lote_locked.pk, 0)
                    stock_disponible = lote_locked.cantidad_actual - stock_reservado
                else:
                    stock_disponible = lote_locked.cantidad_actual
                
                if stock_disponible < cantidad:
                    raise Exception(
                        f'Stock insuficiente en lote {lote_locked.numero_lote}. '
                        f'Disponible: {stock_disponible}, Solicitado: {cantidad}'
                    )
                
                stock_anterior = lote_locked.cantidad_actual
                
                # Si auto_confirmar: descontar stock inmediatamente
                if auto_confirmar:
                    nuevo_stock = stock_anterior - cantidad
                    lote_locked.cantidad_actual = nuevo_stock
                    
                    # Marcar como inactivo si se agotó el stock
                    if nuevo_stock == 0:
                        lote_locked.activo = False
                        lote_locked.save(update_fields=['cantidad_actual', 'activo', 'updated_at'])
                    else:
                        lote_locked.save(update_fields=['cantidad_actual', 'updated_at'])
                    
                    # ============= Crear lote en centro destino =============
                    lote_destino, lote_creado = Lote.objects.get_or_create(
                        numero_lote=lote_locked.numero_lote,
                        producto=lote_locked.producto,
                        centro=centro_destino,
                        defaults={
                            'cantidad_inicial': cantidad,
                            'cantidad_actual': cantidad,
                            'fecha_caducidad': lote_locked.fecha_caducidad,
                            'fecha_fabricacion': lote_locked.fecha_fabricacion,
                            'precio_unitario': lote_locked.precio_unitario,
                            'marca': lote_locked.marca,
                            'numero_contrato': lote_locked.numero_contrato,
                            'ubicacion': lote_locked.ubicacion,
                            'activo': True
                        }
                    )
                    
                    if not lote_creado:
                        # Lote ya existe, sumar cantidad
                        lote_destino.cantidad_actual += cantidad
                        lote_destino.cantidad_inicial += cantidad
                        lote_destino.activo = True
                        lote_destino.save(update_fields=['cantidad_actual', 'cantidad_inicial', 'activo', 'updated_at'])
                    
                    # Crear movimiento de ENTRADA en centro destino
                    # HALLAZGO #1 FIX: Ya actualizamos stock manualmente, usar skip_stock_update
                    motivo_entrada = f'[CONFIRMADO][{grupo_salida}] Entrada por transferencia desde Almacén Central'
                    mov_entrada = Movimiento(
                        tipo='entrada',
                        producto=lote_destino.producto,
                        lote=lote_destino,
                        centro_origen=None,  # Viene de Farmacia Central
                        centro_destino=centro_destino,
                        cantidad=cantidad,
                        motivo=motivo_entrada,
                        usuario=request.user,
                        subtipo_salida=None,
                        referencia=grupo_salida
                    )
                    mov_entrada.save(skip_stock_update=True, skip_validation=True)
                    
                    # ===============================================================
                    # ISS-FLUJO-FIX: El inventario permanece en el centro destino
                    # para que ellos gestionen las salidas manualmente.
                    # NO se crea dispensación automática.
                    # El stock del lote destino mantiene la cantidad transferida
                    # hasta que el centro registre sus propios movimientos.
                    # ===============================================================
                
                # Crear movimiento de SALIDA desde Farmacia Central
                motivo_completo = f'{estado_tag}[{grupo_salida}] {observaciones}'.strip()
                
                movimiento = Movimiento(
                    tipo='salida',
                    producto=lote_locked.producto,
                    lote=lote_locked,
                    centro_origen=None,  # NULL = Farmacia Central
                    centro_destino=centro_destino,
                    cantidad=cantidad,
                    motivo=motivo_completo,
                    usuario=request.user,
                    subtipo_salida='transferencia',
                    referencia=grupo_salida,
                    fecha_salida=fecha_salida
                )
                movimiento._stock_pre_movimiento = stock_anterior
                # HALLAZGO #1 FIX: Ya actualizamos stock arriba, usar skip_stock_update
                # PERF-FIX: skip_validation — ya validamos en la vista
                movimiento.save(skip_stock_update=True, skip_validation=True)
                
                # ISS-FECHA FIX: Si tiene fecha_salida, actualizar el campo 'fecha'
                # para que coincida (auto_now_add siempre pone now())
                if fecha_salida:
                    Movimiento.objects.filter(pk=movimiento.pk).update(fecha=fecha_salida)
                
                movimientos_creados.append({
                    'id': movimiento.id,
                    'lote_id': lote_locked.id,
                    'numero_lote': lote_locked.numero_lote,
                    'producto_clave': lote_locked.producto.clave,
                    'producto_nombre': lote_locked.producto.nombre,
                    'cantidad': cantidad,
                    'stock_anterior': stock_anterior,
                    'stock_actual': lote_locked.cantidad_actual,
                    'confirmado': auto_confirmar
                })
        
        estado_mensaje = 'CONFIRMADA (stock descontado)' if auto_confirmar else 'PENDIENTE (requiere confirmación)'
        logger.info(
            f'Salida masiva {grupo_salida} {estado_mensaje} por {request.user.username}: '
            f'{len(movimientos_creados)} items a centro {centro_destino.nombre}'
        )
        
        return Response({
            'success': True,
            'message': f'Salida procesada exitosamente. {len(movimientos_creados)} productos {"entregados" if auto_confirmar else "pendientes de confirmar"}.',
            'grupo_salida': grupo_salida,
            'confirmado': auto_confirmar,
            'centro_destino': {
                'id': centro_destino.id,
                'nombre': centro_destino.nombre
            },
            'total_items': len(movimientos_creados),
            'movimientos': movimientos_creados
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f'Error en salida masiva: {str(e)}')
        return Response({
            'error': True,
            'message': f'Error al procesar salida: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _calcular_stock_reservado(lote):
    """
    Calcula el stock reservado por movimientos PENDIENTES en un lote.
    
    ISS-FIX FLUJO CORRECTO: Stock reservado = suma de cantidades de
    movimientos de salida que están [PENDIENTE] (aún no confirmados).
    
    Args:
        lote: Instancia del Lote
    
    Returns:
        int: Cantidad total reservada por movimientos pendientes
    """
    from django.db.models import Sum
    
    reservado = Movimiento.objects.filter(
        lote=lote,
        tipo='salida',
        motivo__contains='[PENDIENTE]'
    ).aggregate(total=Sum('cantidad'))['total'] or 0
    
    return reservado


def _calcular_stock_reservado_batch(lotes):
    """
    PERF-FIX: Calcula stock reservado para MÚLTIPLES lotes en 1 sola query.
    
    Antes: N queries individuales (1 por lote).
    Ahora: 1 query con GROUP BY lote_id.
    
    Args:
        lotes: Lista de instancias Lote
    
    Returns:
        dict: {lote_id: cantidad_reservada}
    """
    from django.db.models import Sum
    
    if not lotes:
        return {}
    
    lote_ids = [l.pk for l in lotes]
    
    reservados = Movimiento.objects.filter(
        lote_id__in=lote_ids,
        tipo='salida',
        motivo__contains='[PENDIENTE]'
    ).values('lote_id').annotate(
        total=Sum('cantidad')
    )
    
    return {r['lote_id']: r['total'] or 0 for r in reservados}


def _es_movimiento_pendiente(movimiento):
    """Verifica si un movimiento está en estado PENDIENTE."""
    return '[PENDIENTE]' in (movimiento.motivo or '')


def _es_movimiento_confirmado(movimiento):
    """Verifica si un movimiento está en estado CONFIRMADO."""
    return '[CONFIRMADO]' in (movimiento.motivo or '')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hoja_entrega_pdf(request, grupo_salida):
    """
    Genera PDF de hoja de entrega para una salida masiva.
    
    Permisos:
        - Farmacia/Admin: Pueden descargar cualquier hoja de entrega
        - Centro: Solo pueden descargar hojas de entregas destinadas a su centro
    
    Args:
        grupo_salida: ID del grupo de salida (ej: SAL-20251217120000-1)
    
    Query params:
        finalizado: si es 'true', genera comprobante con sello ENTREGADO en lugar de firmas
    
    Returns:
        PDF con hoja de entrega para firma o comprobante de entrega
    """
    try:
        from core.utils.pdf_generator import generar_hoja_entrega
        
        user = request.user
        rol = (getattr(user, 'rol_efectivo', None) or getattr(user, 'rol', '') or '').lower()
        
        # Normalizar aliases de roles
        ROLE_ALIASES = {
            'administrador_centro': 'centro',
            'director_centro': 'centro',
            'medico': 'centro',
        }
        rol_normalizado = ROLE_ALIASES.get(rol, rol)
        
        finalizado = request.query_params.get('finalizado', 'false').lower() == 'true'
        
        # ISS-FIX: Buscar solo movimientos de SALIDA de este grupo
        # El PDF de hoja de entrega muestra lo que SE ENVÍA al centro
        # (las salidas de Farmacia Central, NO las entradas al centro destino)
        movimientos = Movimiento.objects.filter(
            motivo__contains=f'[{grupo_salida}]',
            tipo='salida'  # Solo salidas - lo que se envía
        ).select_related(
            'lote', 'lote__producto', 'centro_destino', 'usuario'
        ).order_by('id')
        
        if not movimientos.exists():
            return Response({
                'error': True,
                'message': 'No se encontraron movimientos para este grupo de salida'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Obtener datos del grupo
        primer_mov = movimientos.first()
        centro_destino = primer_mov.centro_destino
        
        # Validar permisos según rol
        if rol_normalizado == 'centro':
            # Usuarios de centro solo pueden ver entregas a su propio centro
            user_centro_id = getattr(user, 'centro_id', None)
            if not user_centro_id or (centro_destino and centro_destino.id != user_centro_id):
                return Response({
                    'error': True,
                    'message': 'No tienes permisos para ver esta hoja de entrega'
                }, status=status.HTTP_403_FORBIDDEN)
        elif rol_normalizado not in ['admin', 'farmacia', 'vista']:
            return Response({
                'error': True,
                'message': 'No tienes permisos para esta acción'
            }, status=status.HTTP_403_FORBIDDEN)
        
        usuario = primer_mov.usuario
        # Priorizar fecha_salida (fecha real de salida física) sobre fecha del sistema
        fecha = primer_mov.fecha_salida or primer_mov.fecha
        
        # Extraer observaciones (quitar el prefijo del grupo)
        observaciones_raw = primer_mov.motivo or ''
        observaciones = observaciones_raw.replace(f'[{grupo_salida}]', '').strip()
        
        # Preparar datos para el PDF
        datos_entrega = {
            'grupo_salida': grupo_salida,
            'centro_destino': centro_destino.nombre if centro_destino else 'N/A',
            'fecha': fecha,
            'usuario': usuario.get_full_name() if usuario else 'N/A',
            'observaciones': observaciones,
            'items': []
        }
        
        for mov in movimientos:
            producto = mov.lote.producto if mov.lote else None
            datos_entrega['items'].append({
                'clave': producto.clave if producto else 'N/A',
                'descripcion': producto.nombre if producto else 'N/A',
                'presentacion': producto.presentacion or producto.unidad_medida if producto else 'N/A',
                'lote': mov.lote.numero_lote if mov.lote else 'N/A',
                'caducidad': mov.lote.fecha_caducidad.strftime('%d/%m/%Y') if mov.lote and mov.lote.fecha_caducidad else 'N/A',
                'cantidad': mov.cantidad,
                'unidad': producto.unidad_medida if producto else 'UND'
            })
        
        # Generar PDF
        pdf_buffer = generar_hoja_entrega(datos_entrega, finalizado=finalizado)
        
        response = HttpResponse(
            pdf_buffer.getvalue(),
            content_type='application/pdf'
        )
        folio_safe = grupo_salida.replace('/', '-')
        nombre_archivo = f"Comprobante_Entrega_{folio_safe}.pdf" if finalizado else f"Hoja_Entrega_{folio_safe}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
        
        return response
        
    except Exception as e:
        logger.error(f'Error generando hoja de entrega: {str(e)}')
        return Response({
            'error': True,
            'message': f'Error al generar PDF: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsFarmaciaRole])
def confirmar_entrega(request, grupo_salida):
    """
    Confirma la entrega física de una salida masiva.
    
    ISS-FIX FLUJO CORRECTO: AQUÍ es donde se descuenta el stock de los lotes.
    Cambia [PENDIENTE] por [CONFIRMADO] en el motivo.
    
    Permisos:
        - Solo usuarios con rol farmacia o admin pueden confirmar entregas
    
    Args:
        grupo_salida: ID del grupo de salida (ej: SAL-1229-0917-1)
    
    Returns:
        - 200: Entrega confirmada exitosamente
        - 404: Grupo de salida no encontrado
        - 400: Ya estaba confirmado o no hay stock suficiente
        - 403: Sin permisos suficientes
    """
    try:
        # Buscar movimientos de este grupo
        movimientos = Movimiento.objects.filter(
            motivo__contains=f'[{grupo_salida}]'
        ).select_related('lote')
        
        if not movimientos.exists():
            return Response({
                'error': True,
                'message': 'No se encontraron movimientos para este grupo de salida'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Verificar si ya está confirmado
        primer_mov = movimientos.first()
        if _es_movimiento_confirmado(primer_mov):
            return Response({
                'error': True,
                'message': 'Esta entrega ya fue confirmada anteriormente'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verificar que esté pendiente
        if not _es_movimiento_pendiente(primer_mov):
            return Response({
                'error': True,
                'message': 'Esta salida no está en estado pendiente'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        items_confirmados = []
        
        # ISS-FIX FLUJO CORRECTO: Descontar stock, crear lote destino y marcar como confirmados
        with transaction.atomic():
            for mov in movimientos:
                if mov.lote and _es_movimiento_pendiente(mov):
                    # Bloquear lote para actualización atómica
                    lote_locked = Lote.objects.select_for_update().get(pk=mov.lote.pk)
                    
                    stock_anterior = lote_locked.cantidad_actual
                    cantidad = mov.cantidad
                    nuevo_stock = stock_anterior - cantidad
                    
                    # Validar stock suficiente
                    if nuevo_stock < 0:
                        raise Exception(
                            f'Stock insuficiente en lote {lote_locked.numero_lote}. '
                            f'Disponible: {stock_anterior}, Requerido: {cantidad}'
                        )
                    
                    # Actualizar stock del lote origen (Farmacia Central)
                    lote_locked.cantidad_actual = nuevo_stock
                    
                    # Marcar como inactivo si se agotó el stock
                    if nuevo_stock == 0:
                        lote_locked.activo = False
                        lote_locked.save(update_fields=['cantidad_actual', 'activo', 'updated_at'])
                    else:
                        lote_locked.save(update_fields=['cantidad_actual', 'updated_at'])
                    
                    # ===============================================================
                    # ISS-FIX CRÍTICO: Crear/actualizar lote en centro destino
                    # ===============================================================
                    centro_destino = mov.centro_destino
                    if centro_destino:
                        # Buscar si ya existe un lote con mismo numero_lote en el centro destino
                        lote_destino, created = Lote.objects.get_or_create(
                            numero_lote=lote_locked.numero_lote,
                            producto=lote_locked.producto,
                            centro=centro_destino,
                            defaults={
                                'cantidad_inicial': cantidad,
                                'cantidad_actual': cantidad,
                                'fecha_caducidad': lote_locked.fecha_caducidad,
                                'fecha_fabricacion': lote_locked.fecha_fabricacion,
                                'precio_unitario': lote_locked.precio_unitario,
                                'marca': lote_locked.marca,
                                'numero_contrato': lote_locked.numero_contrato,
                                'ubicacion': lote_locked.ubicacion,
                                'activo': True
                            }
                        )
                        
                        if not created:
                            # Lote ya existe, sumar cantidad
                            lote_destino.cantidad_actual += cantidad
                            lote_destino.cantidad_inicial += cantidad
                            lote_destino.activo = True
                            lote_destino.save(update_fields=['cantidad_actual', 'cantidad_inicial', 'activo', 'updated_at'])
                        
                        # Crear movimiento de ENTRADA en centro destino
                        # FIX: Usar Movimiento() + save(skip_stock_update=True) en lugar de
                        # Movimiento.objects.create() — ya actualizamos stock manualmente arriba,
                        # sin skip_stock_update el save() llamaría aplicar_movimiento_a_lote()
                        # y DUPLICARÍA la cantidad en el lote destino.
                        motivo_entrada = f'[CONFIRMADO][{grupo_salida}] Entrada por transferencia desde Almacén Central'
                        mov_entrada = Movimiento(
                            tipo='entrada',
                            producto=lote_destino.producto,
                            lote=lote_destino,
                            centro_origen=None,  # Viene de Farmacia Central
                            centro_destino=centro_destino,
                            cantidad=cantidad,
                            motivo=motivo_entrada,
                            usuario=request.user,
                            subtipo_salida=None,
                            referencia=grupo_salida
                        )
                        mov_entrada.save(skip_stock_update=True, skip_validation=True)
                        
                        # ===============================================================
                        # ISS-FLUJO-FIX: El inventario permanece en el centro destino
                        # para que ellos gestionen las salidas manualmente.
                        # NO se crea dispensación automática.
                        # ===============================================================
                    
                    # Cambiar estado de [PENDIENTE] a [CONFIRMADO]
                    nuevo_motivo = (mov.motivo or '').replace('[PENDIENTE]', '[CONFIRMADO]')
                    mov.motivo = nuevo_motivo
                    mov.save(update_fields=['motivo'])
                    
                    items_confirmados.append({
                        'lote_id': lote_locked.id,
                        'numero_lote': lote_locked.numero_lote,
                        'producto_clave': lote_locked.producto.clave if lote_locked.producto else 'N/A',
                        'producto_nombre': lote_locked.producto.nombre if lote_locked.producto else 'Sin nombre',
                        'cantidad': cantidad,
                        'stock_anterior': stock_anterior,
                        'stock_actual': nuevo_stock,
                        'centro_destino': centro_destino.nombre if centro_destino else None,
                        'lote_destino_creado': created if centro_destino else None
                    })
        
        logger.info(
            f'Entrega {grupo_salida} CONFIRMADA por {request.user.username}: '
            f'{len(items_confirmados)} items, stock descontado'
        )
        
        return Response({
            'success': True,
            'message': f'Entrega confirmada exitosamente. {len(items_confirmados)} productos descontados del inventario.',
            'grupo_salida': grupo_salida,
            'items_confirmados': items_confirmados
        })
        
    except Exception as e:
        logger.error(f'Error confirmando entrega: {str(e)}')
        return Response({
            'error': True,
            'message': f'Error al confirmar entrega: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def estado_entrega(request, grupo_salida):
    """
    Consulta el estado de una entrega (pendiente, confirmada, etc).
    
    Permisos:
        - Farmacia/Admin: Pueden consultar cualquier entrega
        - Centro: Solo pueden consultar entregas destinadas a su centro
    
    Args:
        grupo_salida: ID del grupo de salida
    
    Returns:
        - confirmada: boolean
        - fecha_confirmacion: datetime si está confirmada
        - 403: Sin permisos para ver esta entrega
    """
    try:
        user = request.user
        rol = (getattr(user, 'rol_efectivo', None) or getattr(user, 'rol', '') or '').lower()
        
        # Normalizar aliases de roles
        ROLE_ALIASES = {
            'administrador_centro': 'centro',
            'director_centro': 'centro',
            'medico': 'centro',
        }
        rol_normalizado = ROLE_ALIASES.get(rol, rol)
        
        movimientos = Movimiento.objects.filter(
            motivo__contains=f'[{grupo_salida}]'
        ).select_related('centro_destino')
        
        if not movimientos.exists():
            return Response({
                'error': True,
                'message': 'Grupo de salida no encontrado'
            }, status=status.HTTP_404_NOT_FOUND)
        
        primer_mov = movimientos.first()
        centro_destino = primer_mov.centro_destino
        
        # Validar permisos según rol
        if rol_normalizado == 'centro':
            # Usuarios de centro solo pueden ver entregas a su propio centro
            user_centro_id = getattr(user, 'centro_id', None)
            if not user_centro_id or (centro_destino and centro_destino.id != user_centro_id):
                return Response({
                    'error': True,
                    'message': 'No tienes permisos para ver esta entrega'
                }, status=status.HTTP_403_FORBIDDEN)
        elif rol_normalizado not in ['admin', 'farmacia', 'vista']:
            return Response({
                'error': True,
                'message': 'No tienes permisos para esta acción'
            }, status=status.HTTP_403_FORBIDDEN)
        
        confirmada = _es_movimiento_confirmado(primer_mov)
        pendiente = _es_movimiento_pendiente(primer_mov)
        
        return Response({
            'grupo_salida': grupo_salida,
            'pendiente': pendiente,
            'confirmada': confirmada,
            'total_items': movimientos.count(),
            'centro_destino': centro_destino.nombre if centro_destino else None
        })
        
    except Exception as e:
        logger.error(f'Error consultando estado de entrega: {str(e)}')
        return Response({
            'error': True,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsFarmaciaRole])
def cancelar_salida(request, grupo_salida):
    """
    Cancela una salida masiva PENDIENTE.
    
    ISS-FIX FLUJO CORRECTO: Como el stock NO se descuenta hasta confirmar,
    cancelar solo elimina los movimientos (no hay stock que devolver).
    Solo se pueden cancelar salidas que están en estado [PENDIENTE].
    
    Args:
        grupo_salida: ID del grupo de salida (ej: SAL-0102-1530-1)
    
    Returns:
        - 200: Salida cancelada exitosamente
        - 400: Ya está confirmada o no está pendiente
        - 404: Grupo de salida no encontrado
    """
    try:
        # Buscar movimientos de este grupo
        movimientos = Movimiento.objects.filter(
            motivo__contains=f'[{grupo_salida}]'
        ).select_related('lote')
        
        if not movimientos.exists():
            return Response({
                'error': True,
                'message': 'No se encontraron movimientos para este grupo de salida'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Verificar estados
        primer_mov = movimientos.first()
        if _es_movimiento_confirmado(primer_mov):
            return Response({
                'error': True,
                'message': 'No se puede cancelar una entrega que ya fue confirmada'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not _es_movimiento_pendiente(primer_mov):
            return Response({
                'error': True,
                'message': 'Esta salida no está en estado pendiente'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        items_cancelados = []
        
        # ISS-FIX FLUJO CORRECTO: Solo eliminar movimientos
        # NO hay stock que devolver porque nunca se descontó
        with transaction.atomic():
            for mov in movimientos:
                items_cancelados.append({
                    'lote_id': mov.lote.id if mov.lote else None,
                    'numero_lote': mov.lote.numero_lote if mov.lote else 'N/A',
                    'cantidad_cancelada': mov.cantidad,
                })
                # Eliminar el movimiento
                mov.delete()
        
        logger.info(
            f'Salida masiva {grupo_salida} CANCELADA por {request.user.username}: '
            f'{len(items_cancelados)} movimientos eliminados (stock no afectado)'
        )
        
        return Response({
            'success': True,
            'message': f'Salida cancelada. {len(items_cancelados)} movimientos eliminados.',
            'grupo_salida': grupo_salida,
            'items_cancelados': items_cancelados
        })
    
    except Exception as e:
        logger.error(f'Error cancelando salida masiva {grupo_salida}: {str(e)}')
        return Response({
            'error': True,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsFarmaciaRole])
def lotes_disponibles_farmacia(request):
    """
    Lista lotes con stock disponible en Farmacia Central (centro=NULL).
    Optimizado para el selector de salida masiva.
    
    Query params:
        - search: Buscar por clave o nombre de producto, o número de lote
        - page_size: Items por página (default 50)
    """
    try:
        search = request.query_params.get('search', '').strip()
        page_size = int(request.query_params.get('page_size', 50))
        
        # Lotes de Farmacia Central (centro=NULL) con stock
        queryset = Lote.objects.filter(
            centro__isnull=True,
            activo=True,
            cantidad_actual__gt=0
        ).select_related('producto').order_by('producto__nombre', 'fecha_caducidad')
        
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(producto__clave__icontains=search) |
                Q(producto__nombre__icontains=search) |
                Q(numero_lote__icontains=search)
            )
        
        # Limitar resultados
        lotes = queryset[:page_size]
        
        data = []
        for lote in lotes:
            data.append({
                'id': lote.id,
                'numero_lote': lote.numero_lote,
                'producto_id': lote.producto_id,
                'producto_clave': lote.producto.clave,
                'producto_nombre': lote.producto.nombre,
                'presentacion': lote.producto.presentacion or '',
                'unidad_medida': lote.producto.unidad_medida,
                'cantidad_disponible': lote.cantidad_actual,
                'fecha_caducidad': lote.fecha_caducidad.strftime('%Y-%m-%d') if lote.fecha_caducidad else None,
                'dias_para_caducar': (lote.fecha_caducidad - timezone.now().date()).days if lote.fecha_caducidad else None
            })
        
        return Response({
            'count': queryset.count(),
            'results': data
        })
        
    except Exception as e:
        logger.error(f'Error listando lotes disponibles: {str(e)}')
        return Response({
            'error': True,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
