"""
Módulo para salida masiva de inventario - Solo Farmacia
Permite agregar múltiples productos/lotes a una lista y procesarlos de una vez
con generación de hoja de entrega para firma.

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

from core.models import Lote, Movimiento, Centro, Producto
from core.permissions import IsFarmaciaRole

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsFarmaciaRole])
def salida_masiva(request):
    """
    Procesa una salida masiva de inventario para un centro destino.
    Solo disponible para usuarios con rol Farmacia.
    
    Body esperado:
    {
        "centro_destino_id": 1,
        "observaciones": "Entrega programada",
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
        
        for idx, item in enumerate(items, 1):
            lote_id = item.get('lote_id')
            cantidad = item.get('cantidad', 0)
            
            if not lote_id:
                errores.append(f'Item {idx}: Falta ID de lote')
                continue
            
            if not cantidad or cantidad <= 0:
                errores.append(f'Item {idx}: Cantidad debe ser mayor a 0')
                continue
            
            try:
                lote = Lote.objects.select_related('producto').get(pk=lote_id)
                
                # Verificar stock disponible
                if lote.cantidad_actual < cantidad:
                    errores.append(
                        f'Item {idx}: Stock insuficiente en lote {lote.numero_lote}. '
                        f'Disponible: {lote.cantidad_actual}, Solicitado: {cantidad}'
                    )
                    continue
                
                items_validos.append({
                    'lote': lote,
                    'cantidad': int(cantidad)
                })
                
            except Lote.DoesNotExist:
                errores.append(f'Item {idx}: Lote con ID {lote_id} no encontrado')
        
        if errores:
            return Response({
                'error': True,
                'message': 'Errores de validación',
                'errores': errores
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Generar ID de grupo para esta salida masiva (formato corto: SAL-MMDD-HHMM-CentroID)
        now = timezone.now()
        timestamp = now.strftime('%m%d-%H%M')
        grupo_salida = f'SAL-{timestamp}-{centro_destino.id}'
        
        movimientos_creados = []
        
        with transaction.atomic():
            for item in items_validos:
                lote = item['lote']
                cantidad = item['cantidad']
                
                # Bloquear lote para actualización atómica
                lote_locked = Lote.objects.select_for_update().get(pk=lote.pk)
                
                # Re-validar stock con el lote bloqueado
                if lote_locked.cantidad_actual < cantidad:
                    raise Exception(
                        f'Stock insuficiente en lote {lote_locked.numero_lote}. '
                        f'Disponible: {lote_locked.cantidad_actual}, Solicitado: {cantidad}'
                    )
                
                stock_anterior = lote_locked.cantidad_actual
                nuevo_stock = stock_anterior - cantidad
                
                # Actualizar stock del lote origen (Farmacia Central)
                lote_locked.cantidad_actual = nuevo_stock
                
                # Marcar como inactivo si se agotó el stock
                if nuevo_stock == 0:
                    lote_locked.activo = False
                    lote_locked.save(update_fields=['cantidad_actual', 'activo', 'updated_at'])
                else:
                    lote_locked.save(update_fields=['cantidad_actual', 'updated_at'])
                
                # Crear movimiento de SALIDA desde Farmacia Central
                # Nota: centro_origen=NULL indica Farmacia Central
                motivo_completo = f'[{grupo_salida}] {observaciones}'.strip()
                
                movimiento = Movimiento(
                    tipo='salida',
                    producto=lote_locked.producto,
                    lote=lote_locked,
                    centro_origen=None,  # NULL = Farmacia Central
                    centro_destino=centro_destino,
                    cantidad=cantidad,  # Cantidad positiva, se registra como salida
                    motivo=motivo_completo,
                    usuario=request.user,
                    subtipo_salida='transferencia',
                    referencia=grupo_salida
                )
                # Bypass validación de stock ya que ya actualizamos el lote
                movimiento._stock_pre_movimiento = stock_anterior
                movimiento.save()
                
                movimientos_creados.append({
                    'id': movimiento.id,
                    'lote_id': lote_locked.id,
                    'numero_lote': lote_locked.numero_lote,
                    'producto_clave': lote_locked.producto.clave,
                    'producto_nombre': lote_locked.producto.nombre,
                    'cantidad': cantidad,
                    'stock_anterior': stock_anterior,
                    'stock_actual': nuevo_stock
                })
        
        logger.info(
            f'Salida masiva {grupo_salida} procesada por {request.user.username}: '
            f'{len(movimientos_creados)} items a centro {centro_destino.nombre}'
        )
        
        return Response({
            'success': True,
            'message': f'Salida procesada exitosamente. {len(movimientos_creados)} productos entregados.',
            'grupo_salida': grupo_salida,
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


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsFarmaciaRole])
def hoja_entrega_pdf(request, grupo_salida):
    """
    Genera PDF de hoja de entrega para una salida masiva.
    
    Args:
        grupo_salida: ID del grupo de salida (ej: SAL-20251217120000-1)
    
    Query params:
        finalizado: si es 'true', genera comprobante con sello ENTREGADO en lugar de firmas
    
    Returns:
        PDF con hoja de entrega para firma o comprobante de entrega
    """
    try:
        from core.utils.pdf_generator import generar_hoja_entrega
        
        finalizado = request.query_params.get('finalizado', 'false').lower() == 'true'
        
        # Buscar movimientos de este grupo
        movimientos = Movimiento.objects.filter(
            motivo__contains=f'[{grupo_salida}]'
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
        usuario = primer_mov.usuario
        fecha = primer_mov.fecha
        
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
            datos_entrega['items'].append({
                'clave': mov.lote.producto.clave if mov.lote and mov.lote.producto else 'N/A',
                'descripcion': mov.lote.producto.nombre if mov.lote and mov.lote.producto else 'N/A',
                'lote': mov.lote.numero_lote if mov.lote else 'N/A',
                'caducidad': mov.lote.fecha_caducidad.strftime('%d/%m/%Y') if mov.lote and mov.lote.fecha_caducidad else 'N/A',
                'cantidad': mov.cantidad,
                'unidad': mov.lote.producto.unidad_medida if mov.lote and mov.lote.producto else 'UND'
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
