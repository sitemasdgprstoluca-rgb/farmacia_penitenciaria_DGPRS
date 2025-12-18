# -*- coding: utf-8 -*-
"""
Módulo MovimientoViewSet para gestión de movimientos de inventario.

Contiene el ViewSet para operaciones CRUD sobre movimientos de stock,
incluyendo exportación a PDF/Excel y trazabilidad de productos y lotes.

Refactorización audit34: Extraído del monolítico views.py (7654 líneas)
para mejorar mantenibilidad y separación de responsabilidades.
"""
import logging
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone

from rest_framework import viewsets, mixins, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from core.models import Producto, Lote, Movimiento, Centro
from core.serializers import MovimientoSerializer
# ISS-MEDICO FIX: Usar IsCentroCanManageInventory para excluir médico
from core.permissions import IsFarmaciaRole, IsCentroRole, IsCentroCanManageInventory, RoleHelper

from .base import (
    CustomPagination,
    is_farmacia_or_admin,
    get_user_centro,
    registrar_movimiento_stock,
    CentroPermissionMixin,
)

logger = logging.getLogger(__name__)


class MovimientoViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet
):
    """
    ViewSet para gestionar movimientos de inventario.
    
    PERMISOS:
    - Admin/Farmacia: acceso completo a todos los movimientos
    - Centro (administrador_centro, director_centro): puede VER y CREAR movimientos
    - Medico: NO puede crear movimientos (ISS-MEDICO FIX)
    - Vista: solo lectura
    
    FILTROS (alineados con exportacin):
    - tipo: entrada/salida/ajuste
    - centro: ID del centro
    - producto: ID del producto
    - lote: ID del lote
    - fecha_inicio: YYYY-MM-DD
    - fecha_fin: YYYY-MM-DD
    - search: bsqueda en observaciones, nmero de lote, producto
    
    Esto permite auditora completa de consumos en cada centro.
    """
    queryset = Movimiento.objects.select_related('lote__producto', 'centro_origen', 'centro_destino', 'usuario').all()
    serializer_class = MovimientoSerializer
    # ISS-MEDICO FIX: Usar permiso que excluye médico de operaciones de escritura
    permission_classes = [IsCentroCanManageInventory]
    pagination_class = CustomPagination
    http_method_names = ['get', 'post', 'head', 'options']

    def _get_producto_display(self, mov):
        """Helper para obtener display de producto de forma segura."""
        if not mov.lote or not mov.lote.producto:
            return 'N/A'
        producto = mov.lote.producto
        nombre = producto.nombre or producto.descripcion or ''
        return f"{producto.clave} - {nombre[:40]}"

    def get_queryset(self):
        """
        Filtra movimientos segun parametros.
        
        Parametros (alineados con exportacin):
        - tipo: entrada/salida/ajuste
        - centro: ID del centro (solo admin/farmacia/vista)
        - producto: ID del producto
        - lote: ID del lote
        - fecha_inicio: fecha mnima (YYYY-MM-DD)
        - fecha_fin: fecha mxima (YYYY-MM-DD)
        - search: bsqueda en observaciones, lote, producto
        
        Seguridad: Usuarios de centro solo ven movimientos de su centro.
        Admin/farmacia/vista ven todo por defecto, pueden filtrar con ?centro=.
        """
        queryset = Movimiento.objects.select_related('lote__producto', 'centro_origen', 'centro_destino', 'usuario')
        
        # SEGURIDAD: Filtrar por centro segun rol
        user = self.request.user
        if not is_farmacia_or_admin(user):
            # Usuario de centro: forzado a su centro
            user_centro = get_user_centro(user)
            if user_centro:
                queryset = queryset.filter(lote__centro=user_centro)
            else:
                return Movimiento.objects.none()
        else:
            # Admin/farmacia/vista: pueden filtrar por centro especifico
            centro_param = self.request.query_params.get('centro')
            if centro_param:
                queryset = queryset.filter(lote__centro_id=centro_param)
        
        # Filtro por tipo
        tipo = self.request.query_params.get('tipo')
        if tipo:
            queryset = queryset.filter(tipo=tipo.lower())
        
        # Filtro por producto
        producto = self.request.query_params.get('producto')
        if producto:
            queryset = queryset.filter(lote__producto_id=producto)
        
        # Filtro por lote (acepta ID numérico o número de lote como texto)
        lote = self.request.query_params.get('lote')
        if lote:
            if lote.isdigit():
                # Si es un número, buscar por ID
                queryset = queryset.filter(lote_id=lote)
            else:
                # Si es texto, buscar por número de lote (coincidencia parcial)
                queryset = queryset.filter(lote__numero_lote__icontains=lote)
        
        # Filtro por subtipo de salida (receta, consumo_interno, merma, etc.)
        subtipo_salida = self.request.query_params.get('subtipo_salida')
        if subtipo_salida:
            queryset = queryset.filter(subtipo_salida__iexact=subtipo_salida)
        
        # Filtro por rango de fechas
        fecha_inicio = self.request.query_params.get('fecha_inicio')
        if fecha_inicio:
            queryset = queryset.filter(fecha__date__gte=fecha_inicio)
        
        fecha_fin = self.request.query_params.get('fecha_fin')
        if fecha_fin:
            queryset = queryset.filter(fecha__date__lte=fecha_fin)
        
        # Busqueda en motivo, lote y producto
        search = self.request.query_params.get('search')
        if search and search.strip():
            search_term = search.strip()
            queryset = queryset.filter(
                Q(motivo__icontains=search_term) |
                Q(lote__numero_lote__icontains=search_term) |
                Q(lote__producto__clave__icontains=search_term) |
                Q(lote__producto__descripcion__icontains=search_term) |
                Q(numero_expediente__icontains=search_term)
            )
        
        return queryset.order_by('-fecha')

    def perform_create(self, serializer):
        """
        Crea un movimiento validando permisos por centro.
        
        SEGURIDAD:
        - Admin/farmacia: pueden crear cualquier movimiento en cualquier lote
        - Usuario de centro (administrador/director): pueden crear movimientos en lotes de su centro
          y solo ciertos tipos: 'salida' (consumo), 'ajuste' (inventario físico)
        - Médico: NO puede crear movimientos (ISS-MEDICO FIX)
        - Usuario de centro NO puede crear 'entrada' (solo vía surtido de requisición)
        """
        user = self.request.user
        
        # ISS-MEDICO FIX: Bloquear explícitamente a médicos
        if RoleHelper.is_medico(user):
            raise serializers.ValidationError({
                'detail': 'Los médicos no tienen permiso para crear movimientos de inventario. Use requisiciones para solicitar medicamentos.'
            })
        
        lote = serializer.validated_data.get('lote')
        tipo = serializer.validated_data.get('tipo', '').lower()
        
        # Validar que usuario de centro solo opere con sus lotes
        if not is_farmacia_or_admin(user):
            user_centro = get_user_centro(user)
            
            # Validar que el lote pertenece al centro del usuario
            if lote and lote.centro != user_centro:
                raise serializers.ValidationError({
                    'lote': 'Solo puedes registrar movimientos en lotes de tu centro'
                })
            
            # Validar tipos de movimiento permitidos para centros
            # Centros pueden: salida (consumo), ajuste (inventario fsico)
            # Centros NO pueden: entrada (solo va surtido automtico)
            tipos_permitidos_centro = ['salida', 'ajuste']
            if tipo not in tipos_permitidos_centro:
                raise serializers.ValidationError({
                    'tipo': f'Los centros solo pueden registrar: {", ".join(tipos_permitidos_centro)}. Las entradas se generan automticamente al surtir requisiciones.'
                })
        
        # MEJORA FLUJO 5: Extraer campos de trazabilidad
        subtipo_salida = serializer.validated_data.get('subtipo_salida')
        numero_expediente = serializer.validated_data.get('numero_expediente')
        
        movimiento, _ = registrar_movimiento_stock(
            lote=lote,
            tipo=serializer.validated_data.get('tipo'),
            cantidad=serializer.validated_data.get('cantidad'),
            usuario=user,
            centro=serializer.validated_data.get('centro') or (lote.centro if lote else None),
            requisicion=serializer.validated_data.get('requisicion'),
            # FIX: El serializer mapea 'observaciones' del frontend a 'motivo' via to_internal_value
            observaciones=serializer.validated_data.get('motivo', ''),
            subtipo_salida=subtipo_salida,
            numero_expediente=numero_expediente
        )
        # Dejar instancia lista para serializer.data
        serializer.instance = movimiento

    @action(detail=False, methods=['get'], url_path='trazabilidad-pdf')
    def trazabilidad_pdf(self, request):
        """
        Genera PDF de trazabilidad de un producto.
        Parmetros: ?producto_clave=XXX
        
        SEGURIDAD: Filtra por centro del usuario si no es admin/farmacia.
        """
        from core.utils.pdf_reports import generar_reporte_trazabilidad
        
        # SEGURIDAD: Verificar permisos y determinar filtro de centro
        user = request.user
        filtrar_por_centro = not is_farmacia_or_admin(user)
        user_centro = get_user_centro(user) if filtrar_por_centro else None
        
        clave = request.query_params.get('producto_clave')
        if not clave:
            return Response({'error': 'Se requiere producto_clave'}, status=status.HTTP_400_BAD_REQUEST)
        
        producto = Producto.objects.filter(
            Q(clave__iexact=clave) | Q(descripcion__iexact=clave)
        ).first()
        if not producto:
            return Response({'error': 'Producto no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            # Obtener movimientos del producto
            movimientos = Movimiento.objects.filter(
                lote__producto=producto
            ).select_related('lote', 'centro_origen', 'centro_destino', 'usuario')
            
            # Aplicar filtro de centro si corresponde
            if filtrar_por_centro and user_centro:
                movimientos = movimientos.filter(
                    Q(centro_origen=user_centro) | Q(centro_destino=user_centro) | Q(lote__centro=user_centro)
                )
            
            movimientos = movimientos.order_by('-fecha')[:100]
            
            trazabilidad_data = []
            for mov in movimientos:
                trazabilidad_data.append({
                    'fecha': mov.fecha.strftime('%d/%m/%Y %H:%M') if mov.fecha else 'N/A',
                    'tipo': mov.tipo.upper(),
                    'lote': mov.lote.numero_lote if mov.lote else 'N/A',
                    'cantidad': mov.cantidad,
                    'centro': mov.centro_destino.nombre if mov.centro_destino else (mov.centro_origen.nombre if mov.centro_origen else 'Farmacia Central'),
                    'usuario': mov.usuario.get_full_name() if mov.usuario else 'Sistema',
                    'observaciones': mov.motivo or ''
                })
            
            # Obtener primer lote para info de contrato y precio
            lote_principal = Lote.objects.filter(producto=producto, activo=True).order_by('-cantidad_actual').first()
            
            producto_info = {
                'clave': producto.clave,
                'descripcion': producto.nombre,  # Usar nombre como descripción principal
                'unidad_medida': producto.unidad_medida,
                'stock_actual': producto.get_stock_actual() if hasattr(producto, 'get_stock_actual') else 0,
                'stock_minimo': producto.stock_minimo,
                'precio_unitario': lote_principal.precio_unitario if lote_principal else 0,
                'numero_contrato': lote_principal.numero_contrato if lote_principal else 'N/A',
            }
            
            pdf_buffer = generar_reporte_trazabilidad(trazabilidad_data, producto_info=producto_info)
            
            response = HttpResponse(
                pdf_buffer.getvalue(),
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'attachment; filename="Trazabilidad_{clave}_{timezone.now().strftime("%Y%m%d")}.pdf"'
            
            return response
            
        except Exception as e:
            # traceback removido por seguridad (ISS-008)
            return Response({
                'error': 'Error al generar PDF de trazabilidad',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='trazabilidad-lote-pdf')
    def trazabilidad_lote_pdf(self, request):
        """
        Genera PDF de trazabilidad de un lote especfico.
        Parmetros: ?numero_lote=XXX
        
        SEGURIDAD: Solo admin/farmacia pueden acceder.
        """
        from core.utils.pdf_reports import generar_reporte_trazabilidad
        
        # SEGURIDAD: Solo admin/farmacia pueden exportar trazabilidad de lotes
        if not is_farmacia_or_admin(request.user):
            return Response({'error': 'Solo administradores y farmacia pueden exportar trazabilidad de lotes'}, status=status.HTTP_403_FORBIDDEN)
        
        numero_lote = request.query_params.get('numero_lote')
        lote_id = request.query_params.get('lote_id')
        
        if not numero_lote and not lote_id:
            return Response({'error': 'Se requiere numero_lote o lote_id'}, status=status.HTTP_400_BAD_REQUEST)
        
        # ISS-FIX: Preferir lote_id para evitar ambigüedad con lotes duplicados en diferentes centros
        if lote_id:
            lote = Lote.objects.filter(id=lote_id).select_related('producto', 'centro').first()
        else:
            lote = Lote.objects.filter(numero_lote__iexact=numero_lote).select_related('producto', 'centro').first()
        
        if not lote:
            return Response({'error': 'Lote no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            # Obtener movimientos del lote
            movimientos = Movimiento.objects.filter(
                lote=lote
            ).select_related('lote', 'centro_origen', 'centro_destino', 'usuario').order_by('-fecha')[:100]
            
            trazabilidad_data = []
            for mov in movimientos:
                trazabilidad_data.append({
                    'fecha': mov.fecha.strftime('%d/%m/%Y %H:%M') if mov.fecha else 'N/A',
                    'tipo': mov.tipo.upper(),
                    'lote': mov.lote.numero_lote if mov.lote else 'N/A',
                    'cantidad': mov.cantidad,
                    'centro': mov.centro_destino.nombre if mov.centro_destino else (mov.centro_origen.nombre if mov.centro_origen else 'Farmacia Central'),
                    'usuario': mov.usuario.get_full_name() if mov.usuario else 'Sistema',
                    'observaciones': mov.motivo or ''
                })
            
            # ISS-FIX: Usar nombre como fallback para descripcion, manejar None correctamente
            descripcion_producto = 'N/A'
            if lote.producto:
                descripcion_producto = lote.producto.nombre or lote.producto.descripcion or 'N/A'
            
            producto_info = {
                'clave': lote.producto.clave if lote.producto else 'N/A',
                'descripcion': descripcion_producto,
                'unidad_medida': lote.producto.unidad_medida if lote.producto else 'N/A',
                'stock_actual': lote.cantidad_actual,
                'stock_minimo': lote.producto.stock_minimo if lote.producto else 0,
                'numero_lote': lote.numero_lote,
                'fecha_caducidad': lote.fecha_caducidad.strftime('%d/%m/%Y') if lote.fecha_caducidad else 'N/A',
                'proveedor': lote.marca or 'No especificado',
                'numero_contrato': lote.numero_contrato if lote.numero_contrato else 'N/A',
                'precio_unitario': float(lote.precio_unitario) if lote.precio_unitario else 0,
            }
            
            pdf_buffer = generar_reporte_trazabilidad(trazabilidad_data, producto_info=producto_info)
            
            response = HttpResponse(
                pdf_buffer.getvalue(),
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'attachment; filename="Trazabilidad_Lote_{numero_lote}_{timezone.now().strftime("%Y%m%d")}.pdf"'
            
            return response
            
        except Exception as e:
            # traceback removido por seguridad (ISS-008)
            return Response({
                'error': 'Error al generar PDF de trazabilidad del lote',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='exportar-pdf')
    def exportar_pdf(self, request):
        """
        Genera PDF de movimientos con filtros opcionales.
        Filtros soportados: tipo, fecha_inicio, fecha_fin, producto, centro, lote, subtipo_salida, search
        """
        from core.utils.pdf_reports import generar_reporte_movimientos
        
        try:
            # Aplicar filtros (get_queryset ya aplica filtros base, aquí se duplican por consistencia explícita)
            queryset = self.get_queryset()
            
            tipo = request.query_params.get('tipo')
            if tipo:
                queryset = queryset.filter(tipo=tipo.lower())
            
            fecha_inicio = request.query_params.get('fecha_inicio')
            if fecha_inicio:
                queryset = queryset.filter(fecha__gte=fecha_inicio)
            
            fecha_fin = request.query_params.get('fecha_fin')
            if fecha_fin:
                queryset = queryset.filter(fecha__lte=fecha_fin)
            
            # FIX: Agregar filtros faltantes para consistencia total
            producto = request.query_params.get('producto')
            if producto:
                queryset = queryset.filter(lote__producto_id=producto)
            
            centro = request.query_params.get('centro')
            if centro:
                queryset = queryset.filter(Q(centro_origen_id=centro) | Q(centro_destino_id=centro) | Q(lote__centro_id=centro))
            
            lote = request.query_params.get('lote')
            if lote:
                if lote.isdigit():
                    queryset = queryset.filter(lote_id=lote)
                else:
                    queryset = queryset.filter(lote__numero_lote__icontains=lote)
            
            subtipo_salida = request.query_params.get('subtipo_salida')
            if subtipo_salida:
                queryset = queryset.filter(subtipo_salida__iexact=subtipo_salida)
            
            search = request.query_params.get('search')
            if search:
                queryset = queryset.filter(
                    Q(lote__numero_lote__icontains=search) |
                    Q(lote__producto__nombre__icontains=search) |
                    Q(lote__producto__descripcion__icontains=search) |
                    Q(motivo__icontains=search) |
                    Q(numero_expediente__icontains=search)
                )
            
            movimientos = queryset[:200]  # Limitar para PDF
            
            # Agrupar movimientos por referencia/transacción para PDF
            transacciones = {}
            total_entradas = 0
            total_salidas = 0
            
            for mov in movimientos:
                amount = abs(mov.cantidad) if mov.tipo == 'salida' else mov.cantidad
                ref = mov.referencia or f"MOV-{mov.id}"
                
                if ref not in transacciones:
                    transacciones[ref] = {
                        'referencia': ref,
                        'fecha': mov.fecha.strftime('%d/%m/%Y %H:%M') if mov.fecha else 'N/A',
                        'tipo': mov.tipo.upper(),
                        'centro_origen': mov.centro_origen.nombre if mov.centro_origen else 'Farmacia Central',
                        'centro_destino': mov.centro_destino.nombre if mov.centro_destino else 'Farmacia Central',
                        'total_productos': 0,
                        'total_cantidad': 0,
                        'detalles': []
                    }
                
                transacciones[ref]['detalles'].append({
                    'producto': self._get_producto_display(mov),
                    'lote': mov.lote.numero_lote if mov.lote else 'N/A',
                    'cantidad': amount
                })
                transacciones[ref]['total_productos'] += 1
                transacciones[ref]['total_cantidad'] += amount
                
                if mov.tipo == 'entrada':
                    total_entradas += amount
                else:
                    total_salidas += amount
            
            movimientos_data = list(transacciones.values())
            resumen_data = {
                'total_transacciones': len(movimientos_data),
                'total_movimientos': sum(t['total_productos'] for t in movimientos_data),
                'total_entradas': total_entradas,
                'total_salidas': total_salidas,
                'diferencia': total_entradas - total_salidas
            }
            
            pdf_buffer = generar_reporte_movimientos(movimientos_data, resumen=resumen_data)
            
            response = HttpResponse(
                pdf_buffer.getvalue(),
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'attachment; filename="Movimientos_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
            
            return response
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Error generando PDF de movimientos: {str(e)}', exc_info=True)
            return Response({
                'error': 'Error al generar PDF de movimientos',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='exportar-excel')
    def exportar_excel(self, request):
        """
        Genera Excel de movimientos con filtros opcionales.
        Filtros soportados: tipo, fecha_inicio, fecha_fin, producto, centro, lote, subtipo_salida, search
        """
        try:
            # Aplicar filtros (get_queryset ya aplica filtros base, aquí se duplican por consistencia explícita)
            queryset = self.get_queryset()
            
            tipo = request.query_params.get('tipo')
            if tipo:
                queryset = queryset.filter(tipo=tipo.lower())
            
            fecha_inicio = request.query_params.get('fecha_inicio')
            if fecha_inicio:
                queryset = queryset.filter(fecha__gte=fecha_inicio)
            
            fecha_fin = request.query_params.get('fecha_fin')
            if fecha_fin:
                queryset = queryset.filter(fecha__lte=fecha_fin)
            
            producto = request.query_params.get('producto')
            if producto:
                queryset = queryset.filter(lote__producto_id=producto)
            
            centro = request.query_params.get('centro')
            if centro:
                queryset = queryset.filter(Q(centro_origen_id=centro) | Q(centro_destino_id=centro) | Q(lote__centro_id=centro))
            
            # FIX: Agregar filtros faltantes para consistencia total
            lote = request.query_params.get('lote')
            if lote:
                if lote.isdigit():
                    queryset = queryset.filter(lote_id=lote)
                else:
                    queryset = queryset.filter(lote__numero_lote__icontains=lote)
            
            subtipo_salida = request.query_params.get('subtipo_salida')
            if subtipo_salida:
                queryset = queryset.filter(subtipo_salida__iexact=subtipo_salida)
            
            search = request.query_params.get('search')
            if search:
                queryset = queryset.filter(
                    Q(lote__numero_lote__icontains=search) |
                    Q(lote__producto__nombre__icontains=search) |
                    Q(lote__producto__descripcion__icontains=search) |
                    Q(motivo__icontains=search) |
                    Q(numero_expediente__icontains=search)
                )
            
            movimientos = queryset[:1000]  # Limitar para Excel
            
            # Crear libro de Excel
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = 'Movimientos'
            
            # Título - Con columnas de centro origen y destino
            ws.merge_cells('A1:J1')
            ws['A1'] = 'REPORTE DE MOVIMIENTOS'
            ws['A1'].font = Font(bold=True, size=14, color='632842')
            ws['A1'].alignment = Alignment(horizontal='center')
            
            # Fecha
            ws.merge_cells('A2:J2')
            ws['A2'] = f'Generado el {timezone.now().strftime("%d/%m/%Y %H:%M")}'
            ws['A2'].alignment = Alignment(horizontal='center')
            
            # Encabezados - Con Centro Origen y Centro Destino
            headers = ['#', 'Fecha', 'Tipo', 'Producto', 'Lote', 'Cantidad', 'Centro Origen', 'Centro Destino', 'Usuario', 'Observaciones']
            ws.append([])
            ws.append(headers)
            
            header_fill = PatternFill(start_color='632842', end_color='632842', fill_type='solid')
            header_font = Font(bold=True, color='FFFFFF')
            for cell in ws[4]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center')
            
            # Datos - Con centro origen y destino separados
            for idx, mov in enumerate(movimientos, 1):
                # ISS-FIX: Usar nombre o descripcion, manejar None correctamente
                producto_nombre = ''
                if mov.lote and mov.lote.producto:
                    producto_nombre = (mov.lote.producto.nombre or mov.lote.producto.descripcion or '')[:50]
                ws.append([
                    idx,
                    mov.fecha.strftime('%d/%m/%Y %H:%M') if mov.fecha else 'N/A',
                    mov.tipo.upper(),
                    producto_nombre or 'N/A',
                    mov.lote.numero_lote if mov.lote else 'N/A',
                    mov.cantidad,
                    mov.centro_origen.nombre if mov.centro_origen else 'Farmacia Central',
                    mov.centro_destino.nombre if mov.centro_destino else 'Farmacia Central',
                    mov.usuario.get_full_name() or mov.usuario.username if mov.usuario else 'Sistema',
                    (mov.motivo or '')[:100],
                ])
            
            # Ajustar anchos - actualizado para 10 columnas
            column_widths = [8, 18, 12, 45, 15, 10, 22, 22, 20, 30]
            for i, width in enumerate(column_widths, 1):
                ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = width
            
            # Respuesta
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="Movimientos_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
            wb.save(response)
            return response
            
        except Exception as e:
            # traceback removido por seguridad (ISS-008)
            return Response({
                'error': 'Error al generar Excel de movimientos',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
