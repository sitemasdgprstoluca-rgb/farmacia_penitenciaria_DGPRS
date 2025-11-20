from rest_framework import viewsets, status, filters, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from django_filters.rest_framework import DjangoFilterBackend
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum, Count, F, Prefetch
from django.db import transaction
from django.utils import timezone
from datetime import timedelta, date
import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, PatternFill, Alignment
from django.http import HttpResponse
import io
import logging

from .models import (
    User, Centro, Producto, Lote, Requisicion, 
    DetalleRequisicion, Movimiento, ImportacionLog, AuditoriaLog
)
from .serializers import (
    UserSerializer, CentroSerializer, ProductoSerializer,
    LoteSerializer, RequisicionSerializer, MovimientoSerializer,
    AuditoriaLogSerializer, ImportacionLogSerializer, DetalleRequisicionSerializer
)
from .permissions import (
    IsFarmaciaAdmin, IsFarmaciaAdminOrReadOnly,
    IsCentroUser, CanAuthorizeRequisicion, IsSuperuserOnly
)
from .constants import *
from .utils.pdf_generator import generar_hoja_recoleccion

logger = logging.getLogger(__name__)


class ImportacionLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Historial de importaciones masivas."""
    queryset = ImportacionLog.objects.select_related('usuario').all()
    serializer_class = ImportacionLogSerializer
    permission_classes = [IsFarmaciaAdmin]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields = ['archivo_nombre', 'usuario__username', 'modelo']
    filterset_fields = ['modelo', 'estado']
    ordering_fields = ['fecha_importacion', 'total_registros']
    ordering = ['-fecha_importacion']


class AuditoriaLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Logs de auditoría del sistema."""
    queryset = AuditoriaLog.objects.select_related('usuario').all()
    serializer_class = AuditoriaLogSerializer
    permission_classes = [IsFarmaciaAdmin]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields = ['usuario__username', 'modelo', 'accion', 'objeto_repr']
    filterset_fields = ['modelo', 'accion']
    ordering_fields = ['fecha']
    ordering = ['-fecha']


class DetalleRequisicionViewSet(viewsets.ModelViewSet):
    """Gestión granular de los renglones de una requisición."""
    queryset = DetalleRequisicion.objects.select_related('requisicion', 'producto').all()
    serializer_class = DetalleRequisicionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['requisicion', 'producto']


class CustomPagination(PageNumberPagination):
    """
    Paginación personalizada con 25 items por página
    Permite override via query param ?page_size=X
    """
    page_size = PAGINATION_DEFAULT_PAGE_SIZE
    page_size_query_param = 'page_size'
    max_page_size = PAGINATION_MAX_PAGE_SIZE


class ProductoViewSet(viewsets.ModelViewSet):
    """
    ViewSet completo para gestión de productos
    
    Endpoints:
    - GET /api/productos/ - Listar productos con filtros
    - POST /api/productos/ - Crear producto (solo FARMACIA_ADMIN)
    - GET /api/productos/{id}/ - Detalle de producto
    - PUT/PATCH /api/productos/{id}/ - Actualizar producto (solo FARMACIA_ADMIN)
    - DELETE /api/productos/{id}/ - Soft delete producto (solo FARMACIA_ADMIN)
    - GET /api/productos/nuevos/ - Productos recientes
    - GET /api/productos/exportar_excel/ - Exportar a Excel
    - POST /api/productos/importar_excel/ - Importar desde Excel
    - GET /api/productos/bajo_stock/ - Productos con stock bajo
    - GET /api/productos/estadisticas/ - Estadísticas generales
    
    Filtros disponibles:
    - ?search=TEXTO - Busca en clave y descripción
    - ?activo=true/false - Estado del producto
    - ?unidad_medida=PIEZA - Tipo de unidad
    - ?precio_min=10&precio_max=100 - Rango de precios
    - ?stock_status=critico|bajo|normal|alto - Nivel de stock
    - ?ordering=clave,-precio_unitario - Ordenamiento
    """
    serializer_class = ProductoSerializer
    permission_classes = [IsFarmaciaAdminOrReadOnly]
    pagination_class = CustomPagination
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields = ['clave', 'descripcion']
    filterset_fields = ['activo', 'unidad_medida']
    ordering_fields = ['clave', 'descripcion', 'precio_unitario', 'created_at']
    ordering = ['clave']

    def get_queryset(self):
        """
        Optimiza queryset con select_related y prefetch_related
        Aplica filtros personalizados
        """
        queryset = Producto.objects.select_related('created_by').prefetch_related(
            Prefetch(
                'lotes',
                queryset=Lote.objects.filter(estado='disponible'),
                to_attr='lotes_disponibles'
            )
        )
        
        # Filtro por rango de precios
        precio_min = self.request.query_params.get('precio_min')
        precio_max = self.request.query_params.get('precio_max')
        
        if precio_min:
            try:
                queryset = queryset.filter(precio_unitario__gte=float(precio_min))
            except ValueError:
                logger.warning(f"Precio mínimo inválido: {precio_min}")
        
        if precio_max:
            try:
                queryset = queryset.filter(precio_unitario__lte=float(precio_max))
            except ValueError:
                logger.warning(f"Precio máximo inválido: {precio_max}")
        
        # Filtro por nivel de stock
        stock_status = self.request.query_params.get('stock_status')
        if stock_status in ['critico', 'bajo', 'normal', 'alto']:
            # Filtro aplicado en el serializer por complejidad
            queryset = queryset.annotate(
                stock_calculado=Sum('lotes__cantidad_actual', filter=Q(lotes__estado='disponible'))
            )
        
        return queryset

    def perform_create(self, serializer):
        """Registra usuario que crea el producto"""
        serializer.save(created_by=self.request.user)
        logger.info(
            f"Producto {serializer.instance.clave} creado por "
            f"{self.request.user.username}"
        )

    def perform_destroy(self, instance):
        """
        Soft delete: marca producto como inactivo en lugar de eliminar
        Protege integridad referencial con lotes y requisiciones
        """
        # Verificar si tiene lotes activos
        if instance.lotes.filter(cantidad_actual__gt=0).exists():
            return Response(
                {'error': 'No se puede eliminar producto con lotes activos'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar requisiciones pendientes
        if DetalleRequisicion.objects.filter(
            producto=instance,
            requisicion__estado__in=['borrador', 'enviada', 'autorizada']
        ).exists():
            return Response(
                {'error': 'No se puede eliminar producto con requisiciones pendientes'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Soft delete
        instance.activo = False
        instance.save()
        logger.warning(f"Producto {instance.clave} desactivado por {self.request.user.username}")

    @action(detail=False, methods=['get'])
    def nuevos(self, request):
        """
        Retorna productos creados recientemente
        Query param: ?dias=30 (default: 7 días)
        """
        dias = int(request.query_params.get('dias', 7))
        fecha_limite = timezone.now() - timedelta(days=dias)
        
        productos = self.get_queryset().filter(
            created_at__gte=fecha_limite
        ).order_by('-created_at')
        
        page = self.paginate_queryset(productos)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(productos, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def bajo_stock(self, request):
        """
        Retorna productos con stock por debajo del mínimo
        """
        productos_bajo_stock = []
        
        for producto in self.get_queryset().filter(activo=True):
            stock_actual = producto.get_stock_actual()
            nivel = producto.get_nivel_stock()
            
            if nivel in ['critico', 'bajo']:
                productos_bajo_stock.append({
                    'id': producto.id,
                    'clave': producto.clave,
                    'descripcion': producto.descripcion,
                    'stock_actual': stock_actual,
                    'stock_minimo': producto.stock_minimo,
                    'nivel_stock': nivel,
                    'diferencia': producto.stock_minimo - stock_actual
                })
        
        return Response(productos_bajo_stock)

    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """
        Retorna estadísticas generales de productos
        """
        queryset = self.get_queryset().filter(activo=True)
        
        stats = {
            'total_productos': queryset.count(),
            'por_unidad': {},
            'valor_total_inventario': 0,
            'productos_sin_stock': 0,
            'productos_bajo_stock': 0,
        }
        
        # Estadísticas por unidad
        for unidad, _ in UNIDADES_MEDIDA:
            stats['por_unidad'][unidad] = queryset.filter(unidad_medida=unidad).count()
        
        # Calcular valores
        for producto in queryset:
            stock_actual = producto.get_stock_actual()
            stats['valor_total_inventario'] += float(stock_actual * producto.precio_unitario)
            
            if stock_actual == 0:
                stats['productos_sin_stock'] += 1
            elif stock_actual < producto.stock_minimo:
                stats['productos_bajo_stock'] += 1
        
        return Response(stats)

    @action(detail=False, methods=['get'])
    def exportar_excel(self, request):
        """
        Exporta productos a Excel con formato profesional
        Respeta filtros activos en la consulta
        """
        try:
            # Aplicar filtros del request
            queryset = self.filter_queryset(self.get_queryset())
            
            # Crear workbook
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Productos"
            
            # Estilos
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            header_font = Font(color="FFFFFF", bold=True)
            header_alignment = Alignment(horizontal="center", vertical="center")
            
            # Headers
            headers = [
                'ID', 'Clave', 'Descripción', 'Unidad de Medida', 
                'Precio Unitario', 'Stock Mínimo', 'Stock Actual',
                'Nivel Stock', 'Valor Inventario', 'Lotes Activos', 'Estado'
            ]
            
            for col_num, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col_num, value=header)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = header_alignment
            
            # Datos
            for row_num, producto in enumerate(queryset, start=2):
                stock_actual = producto.get_stock_actual()
                nivel_stock = producto.get_nivel_stock()
                valor_inventario = float(stock_actual * producto.precio_unitario)
                lotes_activos = producto.lotes.filter(estado='disponible').count()
                
                ws.cell(row=row_num, column=1, value=producto.id)
                ws.cell(row=row_num, column=2, value=producto.clave)
                ws.cell(row=row_num, column=3, value=producto.descripcion)
                ws.cell(row=row_num, column=4, value=producto.get_unidad_medida_display())
                ws.cell(row=row_num, column=5, value=float(producto.precio_unitario))
                ws.cell(row=row_num, column=6, value=producto.stock_minimo)
                ws.cell(row=row_num, column=7, value=stock_actual)
                ws.cell(row=row_num, column=8, value=nivel_stock.upper())
                ws.cell(row=row_num, column=9, value=valor_inventario)
                ws.cell(row=row_num, column=10, value=lotes_activos)
                ws.cell(row=row_num, column=11, value='Activo' if producto.activo else 'Inactivo')
            
            # Ajustar ancho de columnas
            for col in range(1, len(headers) + 1):
                ws.column_dimensions[get_column_letter(col)].width = 15
            
            # Agregar metadatos
            ws_meta = wb.create_sheet("Información")
            ws_meta['A1'] = "Fecha de Exportación:"
            ws_meta['B1'] = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            ws_meta['A2'] = "Usuario:"
            ws_meta['B2'] = request.user.username
            ws_meta['A3'] = "Total Productos:"
            ws_meta['B3'] = queryset.count()
            
            # Guardar en memoria
            output = io.BytesIO()
            wb.save(output)
            output.seek(0)
            
            # Respuesta HTTP
            filename = f"productos_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            response = HttpResponse(
                output.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename={filename}'
            
            logger.info(f"Exportación Excel realizada por {request.user.username}: {queryset.count()} productos")
            return response
        except Exception as e:
            logger.error(f"Error en exportación Excel: {str(e)}")
            return Response(
                {'error': f'Error al exportar: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CustomTokenObtainPairView(TokenObtainPairView):
    """Permite exponer el endpoint de autenticación esperado por los tests."""
    pass


class UserProfileView(APIView):
    """Vista de perfil de usuario autenticado."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class LogoutView(APIView):
    """Endpoint para logout."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        return Response({'message': 'Logout exitoso'})


class LoteViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de lotes con todas las funcionalidades
    
    Endpoints:
    - GET /api/lotes/ - Listar lotes con filtros avanzados
    - POST /api/lotes/ - Crear lote (solo FARMACIA_ADMIN)
    - GET /api/lotes/{id}/ - Detalle de lote
    - PUT/PATCH /api/lotes/{id}/ - Actualizar lote
    - DELETE /api/lotes/{id}/ - Soft delete lote
    - GET /api/lotes/por_caducar/ - Lotes próximos a caducar
    - GET /api/lotes/vencidos/ - Lotes vencidos
    - POST /api/lotes/{id}/ajustar_stock/ - Ajustar cantidad
    - GET /api/lotes/exportar_excel/ - Exportar a Excel
    - POST /api/lotes/importar-excel/ - Importar desde Excel
    
    Filtros disponibles:
    - ?producto=1 - Por producto ID
    - ?search=LOT123 - Búsqueda en número lote, producto
    - ?caducidad=critico|proximo|vencido|normal - Por estado de caducidad
    - ?con_stock=true - Solo con existencias
    - ?activo=true - Por estado activo
    - ?desde=2025-01-01&hasta=2025-12-31 - Por rango de fechas
    """
    serializer_class = LoteSerializer
    permission_classes = [IsFarmaciaAdminOrReadOnly]
    pagination_class = CustomPagination
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields = ['numero_lote', 'producto__clave', 'producto__descripcion', 'proveedor']
    filterset_fields = ['estado', 'producto']
    ordering_fields = ['fecha_caducidad', 'fecha_entrada', 'cantidad_actual', 'numero_lote']
    ordering = ['-fecha_entrada']

    def get_queryset(self):
        """
        Optimiza queryset y aplica filtros personalizados
        """
        queryset = Lote.objects.select_related('producto', 'created_by').filter(
            deleted_at__isnull=True  # Solo lotes activos
        )
        
        # Filtro: con stock
        con_stock = self.request.query_params.get('con_stock')
        if con_stock is not None:
            if con_stock.lower() == 'true':
                queryset = queryset.filter(cantidad_actual__gt=0)
        
        # Filtro: activo
        activo = self.request.query_params.get('activo')
        if activo is not None:
            queryset = queryset.filter(activo=activo.lower() == 'true')
        
        # Filtro: por caducidad
        caducidad = self.request.query_params.get('caducidad')
        if caducidad:
            hoy = date.today()
            en7 = hoy + timedelta(days=7)
            en30 = hoy + timedelta(days=30)
            
            if caducidad == 'vencido':
                queryset = queryset.filter(fecha_caducidad__lt=hoy)
            elif caducidad == 'critico':
                queryset = queryset.filter(fecha_caducidad__gte=hoy, fecha_caducidad__lte=en7)
            elif caducidad == 'proximo':
                queryset = queryset.filter(fecha_caducidad__gt=en7, fecha_caducidad__lte=en30)
            elif caducidad == 'normal':
                queryset = queryset.filter(fecha_caducidad__gt=en30)
        
        # Filtro: rango de fechas de entrada
        desde = self.request.query_params.get('desde')
        hasta = self.request.query_params.get('hasta')
        
        if desde:
            try:
                queryset = queryset.filter(fecha_entrada__gte=desde)
            except ValidationError:
                pass
        
        if hasta:
            try:
                queryset = queryset.filter(fecha_entrada__lte=hasta)
            except ValidationError:
                pass
        
        return queryset

    def perform_create(self, serializer):
        """Registra usuario que crea el lote"""
        serializer.save(created_by=self.request.user)
        logger.info(
            f"Lote {serializer.instance.numero_lote} creado por "
            f"{self.request.user.username}"
        )

    def perform_destroy(self, instance):
        """
        Soft delete: marca como eliminado sin borrar
        Valida que no haya movimientos recientes
        """
        # Verificar movimientos recientes (últimos 30 días)
        movimientos_recientes = instance.movimientos.filter(
            fecha__gte=timezone.now() - timedelta(days=30)
        )
        
        if movimientos_recientes.exists():
            return Response(
                {
                    'error': 'No se puede eliminar lote con movimientos recientes',
                    'movimientos': movimientos_recientes.count()
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        instance.soft_delete()
        logger.warning(f"Lote {instance.numero_lote} eliminado por {self.request.user.username}")

    @action(detail=False, methods=['get'])
    def por_caducar(self, request):
        """
        Retorna lotes próximos a caducar
        Query param: ?dias=90 (default)
        """
        dias = int(request.query_params.get('dias', DIAS_ALERTA_CADUCIDAD))
        fecha_limite = date.today() + timedelta(days=dias)
        
        lotes = self.get_queryset().filter(
            estado='disponible',
            fecha_caducidad__lte=fecha_limite,
            fecha_caducidad__gt=date.today()
        ).order_by('fecha_caducidad')
        
        page = self.paginate_queryset(lotes)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(lotes, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def vencidos(self, request):
        """Retorna lotes vencidos"""
        lotes = self.get_queryset().filter(
            Q(estado='vencido') | Q(fecha_caducidad__lt=date.today())
        ).order_by('-fecha_caducidad')
        
        page = self.paginate_queryset(lotes)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(lotes, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def ajustar_stock(self, request, pk=None):
        """
        Ajusta stock de un lote (entrada/salida/ajuste)
        Body: { "tipo": "ajuste", "cantidad": 10, "observaciones": "..." }
        """
        lote = self.get_object()
        
        tipo = request.data.get('tipo', 'ajuste')
        cantidad = request.data.get('cantidad')
        observaciones = request.data.get('observaciones', '')
        
        if not cantidad:
            return Response(
                {'error': 'Cantidad requerida'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            cantidad = int(cantidad)
        except ValueError:
            return Response(
                {'error': 'Cantidad debe ser un número entero'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar disponibilidad para salidas
        if tipo == 'salida' and abs(cantidad) > lote.cantidad_actual:
            return Response(
                {'error': f'Stock insuficiente. Disponible: {lote.cantidad_actual}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Crear movimiento
        try:
            movimiento = Movimiento.objects.create(
                tipo=tipo,
                lote=lote,
                cantidad=cantidad if tipo == 'entrada' else -abs(cantidad),
                usuario=request.user,
                observaciones=observaciones
            )
            
            return Response({
                'mensaje': 'Stock ajustado correctamente',
                'lote': self.get_serializer(lote).data,
                'movimiento_id': movimiento.id
            })
            
        except Exception as e:
            logger.error(f"Error al ajustar stock: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def exportar_excel(self, request):
        """
        Exporta lotes a Excel con filtros aplicables
        
        Parámetros:
        ?producto=1&caducidad=vencido&desde=2025-01-01&hasta=2025-12-31
        
        Retorna: archivo .xlsx
        """
        try:
            # Aplicar filtros del request
            queryset = self.filter_queryset(self.get_queryset())
            
            # Crear workbook
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Lotes"
            
            # Estilos
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            header_font = Font(color="FFFFFF", bold=True)
            header_alignment = Alignment(horizontal="center", vertical="center")
            
            # Estilos por estado
            fill_vencido = PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid")
            fill_critico = PatternFill(start_color="FFA500", end_color="FFA500", fill_type="solid")
            fill_proximo = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
            fill_normal = PatternFill(start_color="00FF00", end_color="00FF00", fill_type="solid")
            
            # Headers
            headers = [
                'ID', 'Producto (Clave)', 'Descripción', 'Número Lote', 
                'Fecha Caducidad', 'Días para Vencer', 'Estado Caducidad',
                'Cantidad Inicial', 'Cantidad Actual', '% Consumido',
                'Precio Compra', 'Proveedor', 'Factura', 'Fecha Entrada', 'Estado'
            ]
            
            for col_num, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col_num, value=header)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = header_alignment
            
            # Datos
            for row_num, lote in enumerate(queryset, start=2):
                dias = lote.dias_para_caducar()
                alerta = lote.alerta_caducidad()
                porcentaje = round(((lote.cantidad_inicial - lote.cantidad_actual) / lote.cantidad_inicial) * 100, 2) if lote.cantidad_inicial > 0 else 0
                
                ws.cell(row=row_num, column=1, value=lote.id)
                ws.cell(row=row_num, column=2, value=lote.producto.clave)
                ws.cell(row=row_num, column=3, value=lote.producto.descripcion)
                ws.cell(row=row_num, column=4, value=lote.numero_lote)
                ws.cell(row=row_num, column=5, value=lote.fecha_caducidad.strftime('%Y-%m-%d'))
                ws.cell(row=row_num, column=6, value=dias)
                
                # Aplicar color según estado
                estado_cell = ws.cell(row=row_num, column=7, value=alerta.upper())
                if alerta == 'vencido':
                    estado_cell.fill = fill_vencido
                elif alerta == 'critico':
                    estado_cell.fill = fill_critico
                elif alerta == 'proximo':
                    estado_cell.fill = fill_proximo
                else:
                    estado_cell.fill = fill_normal
                
                ws.cell(row=row_num, column=8, value=lote.cantidad_inicial)
                ws.cell(row=row_num, column=9, value=lote.cantidad_actual)
                ws.cell(row=row_num, column=10, value=porcentaje)
                ws.cell(row=row_num, column=11, value=float(lote.precio_compra) if lote.precio_compra else 0)
                ws.cell(row=row_num, column=12, value=lote.proveedor)
                ws.cell(row=row_num, column=13, value=lote.factura)
                ws.cell(row=row_num, column=14, value=lote.fecha_entrada.strftime('%Y-%m-%d'))
                ws.cell(row=row_num, column=15, value='Activo' if lote.activo else 'Inactivo')
            
            # Ajustar ancho de columnas
            for col in range(1, len(headers) + 1):
                ws.column_dimensions[get_column_letter(col)].width = 15
            
            # Agregar metadatos
            ws_meta = wb.create_sheet("Información")
            ws_meta['A1'] = "Fecha de Exportación:"
            ws_meta['B1'] = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            ws_meta['A2'] = "Usuario:"
            ws_meta['B2'] = request.user.username
            ws_meta['A3'] = "Total Lotes:"
            ws_meta['B3'] = queryset.count()
            ws_meta['A4'] = "Filtros Aplicados:"
            ws_meta['B4'] = str(request.query_params.dict())
            
            # Guardar en memoria
            output = io.BytesIO()
            wb.save(output)
            output.seek(0)
            
            # Respuesta HTTP
            filename = f"lotes_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            response = HttpResponse(
                output.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename={filename}'
            
            logger.info(f"Exportación Excel de lotes realizada por {request.user.username}: {queryset.count()} registros")
            return response
            
        except Exception as e:
            logger.error(f"Error en exportación Excel de lotes: {str(e)}")
            return Response(
                {'error': f'Error al exportar: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='importar_excel')
    def importar_excel(self, request):
        """
        Importar lotes desde archivo Excel
        
        Formato esperado (Fila 1 = Headers):
        - Producto (Clave o ID)
        - Número Lote
        - Fecha Caducidad (YYYY-MM-DD)
        - Cantidad Inicial (Existencias)
        - Precio Compra (opcional)
        - Proveedor (opcional)
        - Factura (opcional)
        
        Validaciones:
        - Producto MUST exist
        - Número Lote: 3-50 chars, único por producto
        - Caducidad: formato fecha, no pasada
        - Cantidad: integer >= 1
        - Precio: decimal >= 0
        
        Retorna:
        {
          "creados": 5,
          "actualizados": 3,
          "errores": [{"fila": 2, "error": "..."}],
          "mensaje": "Importación completada"
        }
        """
        file = request.FILES.get('file')
        if not file:
            return Response(
                {'error': 'No se proporcionó archivo'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar extensión
        file_ext = file.name.split('.')[-1].lower()
        if f'.{file_ext}' not in IMPORT_ALLOWED_EXTENSIONS:
            return Response(
                {'error': f'Formato no permitido. Use: {", ".join(IMPORT_ALLOWED_EXTENSIONS)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar tamaño
        if file.size > IMPORT_MAX_FILE_SIZE:
            return Response(
                {'error': f'Archivo muy grande. Máximo: {IMPORT_MAX_FILE_SIZE / 1024 / 1024}MB'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            wb = openpyxl.load_workbook(file)
            ws = wb.active
            
            # Detectar headers
            headers = [cell.value for cell in ws[1]]
            headers_map = self._mapear_headers(headers)
            
            if not headers_map.get('producto') or not headers_map.get('numero_lote'):
                return Response(
                    {'error': 'Headers requeridos: Producto, Número Lote, Fecha Caducidad, Cantidad'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            resultados = {
                'creados': 0,
                'actualizados': 0,
                'errores': []
            }
            
            # Transacción atómica
            with transaction.atomic():
                for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                    if row_num > IMPORT_MAX_ROWS:
                        resultados['errores'].append({
                            'fila': row_num,
                            'error': f'Límite de filas excedido ({IMPORT_MAX_ROWS})'
                        })
                        break
                    
                    # Saltar filas vacías
                    if not any(row):
                        continue
                    
                    try:
                        # Extraer datos
                        datos = self._extraer_datos_fila_lote(row, headers_map)
                        
                        # Buscar producto
                        producto = self._buscar_producto(datos.get('producto'))
                        if not producto:
                            resultados['errores'].append({
                                'fila': row_num,
                                'error': f'Producto no encontrado: {datos.get("producto")}'
                            })
                            continue
                        
                        # Validar campos requeridos
                        if not datos.get('numero_lote'):
                            resultados['errores'].append({
                                'fila': row_num,
                                'error': 'Número de lote requerido'
                            })
                            continue
                        
                        if not datos.get('fecha_caducidad'):
                            resultados['errores'].append({
                                'fila': row_num,
                                'error': 'Fecha de caducidad requerida'
                            })
                            continue
                        
                        # Update or Create
                        lote, creado = Lote.objects.update_or_create(
                            producto=producto,
                            numero_lote=datos['numero_lote'].upper().strip(),
                            defaults={
                                'fecha_caducidad': datos['fecha_caducidad'],
                                'cantidad_inicial': datos.get('cantidad_inicial', 0),
                                'cantidad_actual': datos.get('cantidad_inicial', 0),  # Inicializar igual
                                'precio_compra': datos.get('precio_compra'),
                                'proveedor': datos.get('proveedor', ''),
                                'factura': datos.get('factura', ''),
                                'created_by': request.user if creado else None
                            }
                        )
                        
                        if creado:
                            resultados['creados'] += 1
                        else:
                            resultados['actualizados'] += 1
                            
                    except ValidationError as e:
                        resultados['errores'].append({
                            'fila': row_num,
                            'error': str(e)
                        })
                    except Exception as e:
                        resultados['errores'].append({
                            'fila': row_num,
                            'error': f'Error inesperado: {str(e)}'
                        })
                
                # Si hay más errores que éxitos, rollback
                if len(resultados['errores']) > resultados['creados'] + resultados['actualizados']:
                    transaction.set_rollback(True)
                    return Response(
                        {'error': 'Demasiados errores. Importación cancelada.', 'detalles': resultados},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Registrar importación en log
            total_procesado = resultados['creados'] + resultados['actualizados']
            errores_total = len(resultados['errores'])
            estado = 'exitosa' if errores_total == 0 else ('parcial' if total_procesado else 'fallida')
            ImportacionLog.objects.create(
                usuario=request.user,
                archivo_nombre=file.name,
                modelo='Lote',
                total_registros=total_procesado + errores_total,
                registros_exitosos=total_procesado,
                registros_fallidos=errores_total,
                estado=estado,
                resultado_procesamiento=resultados
            )
            
            logger.info(
                f"Importación de lotes completada por {request.user.username}: "
                f"{resultados['creados']} creados, {resultados['actualizados']} actualizados, "
                f"{len(resultados['errores'])} errores"
            )
            
            resultados['mensaje'] = 'Importación completada'
            return Response(resultados, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error en importación de lotes: {str(e)}")
            return Response(
                {'error': f'Error al procesar archivo: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _mapear_headers(self, headers):
        """Mapea headers del Excel a campos del modelo Lote"""
        mapping = {}
        
        headers_normalizados = {
            'producto': ['producto', 'clave', 'clave producto', 'id producto'],
            'numero_lote': ['numero lote', 'número lote', 'lote', 'codigo lote', 'código lote'],
            'fecha_caducidad': ['fecha caducidad', 'caducidad', 'vencimiento', 'expiration'],
            'cantidad_inicial': ['cantidad', 'existencias', 'cantidad inicial', 'stock'],
            'precio_compra': ['precio', 'precio compra', 'costo'],
            'proveedor': ['proveedor', 'supplier'],
            'factura': ['factura', 'invoice', 'numero factura']
        }
        
        for idx, header in enumerate(headers):
            if not header:
                continue
            
            header_lower = str(header).lower().strip()
            
            for campo, variantes in headers_normalizados.items():
                if header_lower in variantes:
                    mapping[campo] = idx
                    break
        
        return mapping
    
    def _extraer_datos_fila_lote(self, row, headers_map):
        """Extrae y valida datos de una fila de lotes"""
        from datetime import datetime
        
        datos = {}
        
        # Producto (clave o ID)
        if 'producto' in headers_map:
            datos['producto'] = str(row[headers_map['producto']]) if row[headers_map['producto']] else None
        
        # Número lote
        if 'numero_lote' in headers_map:
            datos['numero_lote'] = str(row[headers_map['numero_lote']]) if row[headers_map['numero_lote']] else None
        
        # Fecha caducidad
        if 'fecha_caducidad' in headers_map:
            fecha_val = row[headers_map['fecha_caducidad']]
            if isinstance(fecha_val, datetime):
                datos['fecha_caducidad'] = fecha_val.date()
            elif isinstance(fecha_val, str):
                try:
                    datos['fecha_caducidad'] = datetime.strptime(fecha_val, '%Y-%m-%d').date()
                except:
                    datos['fecha_caducidad'] = None
            else:
                datos['fecha_caducidad'] = None
        
        # Cantidad
        if 'cantidad_inicial' in headers_map:
            try:
                datos['cantidad_inicial'] = int(row[headers_map['cantidad_inicial']]) if row[headers_map['cantidad_inicial']] else 0
            except (ValueError, TypeError):
                datos['cantidad_inicial'] = 0
        
        # Precio
        if 'precio_compra' in headers_map:
            try:
                datos['precio_compra'] = float(row[headers_map['precio_compra']]) if row[headers_map['precio_compra']] else None
            except (ValueError, TypeError):
                datos['precio_compra'] = None
        
        # Proveedor
        if 'proveedor' in headers_map:
            datos['proveedor'] = str(row[headers_map['proveedor']]) if row[headers_map['proveedor']] else ''
        
        # Factura
        if 'factura' in headers_map:
            datos['factura'] = str(row[headers_map['factura']]) if row[headers_map['factura']] else ''
        
        return datos
    
    def _buscar_producto(self, valor):
        """Busca producto por clave o ID"""
        if not valor:
            return None
        
        # Intentar por ID
        try:
            return Producto.objects.get(id=int(valor))
        except (ValueError, Producto.DoesNotExist):
            pass
        
        # Intentar por clave
        try:
            return Producto.objects.get(clave__iexact=str(valor).strip())
        except Producto.DoesNotExist:
            return None

class UserViewSet(viewsets.ModelViewSet):
    """
    CRUD de Usuarios con permisos y validaciones
    
    Endpoints:
    - GET /api/usuarios/ - Listar usuarios
    - POST /api/usuarios/ - Crear usuario (solo SUPERUSUARIO)
    - GET /api/usuarios/{id}/ - Detalle de usuario
    - PUT/PATCH /api/usuarios/{id}/ - Actualizar usuario
    - DELETE /api/usuarios/{id}/ - Desactivar usuario
    - POST /api/usuarios/{id}/cambiar_password/ - Cambiar contraseña
    
    Filtros:
    - ?search=TEXTO - Busca en username, email, nombre
    - ?rol=admin_farmacia - Filtro por rol
    - ?activo=true - Filtro por estado
    - ?centro=1 - Filtro por centro
    
    Permisos:
    - Lectura: Usuarios autenticados (solo su perfil)
    - Escritura: Solo SUPERUSUARIO
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    filterset_fields = ['rol', 'activo', 'centro']
    ordering_fields = ['username', 'date_joined']
    ordering = ['-date_joined']
    
    def get_queryset(self):
        """
        Optimiza queryset y filtra por permisos
        ✅ MEJORADO: Implementa búsqueda
        """
        queryset = User.objects.select_related('centro').all()
        
        # Usuarios normales solo ven su propio perfil
        if self.request.user.rol not in ['superusuario', 'admin_farmacia']:
            queryset = queryset.filter(id=self.request.user.id)
        
        # ✅ AGREGADO: Búsqueda manual adicional
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )
        
        return queryset
    
    def get_permissions(self):
        """Permisos dinámicos según acción"""
        if self.action in ['create', 'destroy']:
            # Solo superusuario puede crear/eliminar
            return [IsFarmaciaAdmin()]
        elif self.action in ['update', 'partial_update']:
            # Usuarios pueden actualizar su perfil, admin puede todos
            return [IsAuthenticated()]
        else:
            return [IsAuthenticated()]
    
    def perform_destroy(self, instance):
        """Soft delete: desactiva usuario en lugar de eliminar"""
        instance.activo = False
        instance.save()
        logger.warning(f"Usuario {instance.username} desactivado por {self.request.user.username}")
    
    @action(detail=True, methods=['post'])
    def cambiar_password(self, request, pk=None):
        """
        Cambia contraseña de usuario
        Body: { "old_password": "...", "new_password": "..." }
        """
        user = self.get_object()
        
        # Validar permisos: solo el propio usuario o superusuario
        if request.user.id != user.id and request.user.rol != 'superusuario':
            return Response(
                {'error': 'No tiene permisos para cambiar esta contraseña'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        
        if not new_password:
            return Response(
                {'error': 'Nueva contraseña requerida'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Si no es superusuario, validar contraseña actual
        if request.user.rol != 'superusuario':
            if not old_password:
                return Response(
                    {'error': 'Contraseña actual requerida'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not user.check_password(old_password):
                return Response(
                    {'error': 'Contraseña actual incorrecta'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Validar nueva contraseña
        serializer = self.get_serializer(data={'password': new_password}, partial=True)
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as e:
            return Response(
                {'error': e.detail.get('password', ['Error de validación'])[0]},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Cambiar contraseña
        user.set_password(new_password)
        user.save()
        
        logger.info(f"Contraseña cambiada para usuario {user.username}")
        return Response({'mensaje': 'Contraseña actualizada correctamente'})


class RequisicionViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de requisiciones con flujo completo y permisos jerárquicos
    
    ✅ MEJORADO CON SISTEMA DE PERMISOS COMPLETO
    """
    serializer_class = RequisicionSerializer
    permission_classes = [IsCentroUser]
    pagination_class = CustomPagination
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields = ['folio', 'centro__nombre', 'observaciones']
    filterset_fields = ['estado', 'centro']
    ordering_fields = ['fecha_solicitud', 'folio']
    ordering = ['-fecha_solicitud']

    def get_queryset(self):
        """
        Optimiza queryset y filtra según permisos del usuario
        - SUPERUSUARIO y FARMACIA_ADMIN: Ven TODAS
        - CENTRO_USER: Solo sus requisiciones
        - VISTA_USER: Ven todas (solo lectura)
        """
        user = self.request.user
        queryset = Requisicion.objects.select_related(
            'centro', 'usuario_solicita', 'usuario_autoriza'
        ).prefetch_related('detalles__producto')
        
        # SUPERUSUARIO: acceso total
        if user.is_superuser:
            return queryset
        
        # FARMACIA_ADMIN: ve todas
        if user.groups.filter(name='FARMACIA_ADMIN').exists():
            return queryset
        
        # CENTRO_USER: solo sus requisiciones
        if user.groups.filter(name='CENTRO_USER').exists():
            # Buscar centro del usuario (primero en profile, luego en user)
            centro = None
            if hasattr(user, 'profile') and user.profile.centro:
                centro = user.profile.centro
            elif user.centro:
                centro = user.centro
            
            if centro:
                return queryset.filter(centro=centro)
            else:
                return queryset.none()
        
        # VISTA_USER: ve todas (solo lectura)
        if user.groups.filter(name='VISTA_USER').exists():
            return queryset
        
        return queryset.none()
    
    def get_permissions(self):
        """Permisos dinámicos según acción"""
        if self.action in ['autorizar', 'rechazar', 'surtir']:
            return [CanAuthorizeRequisicion()]
        elif self.action == 'hoja_recoleccion':
            return [IsAuthenticated()]
        return super().get_permissions()

    @action(detail=True, methods=['post'])
    def enviar(self, request, pk=None):
        """
        Cambia estado de BORRADOR a ENVIADA
        Solo el usuario del centro puede enviar su requisición
        """
        requisicion = self.get_object()
        
        # Validar estado
        if requisicion.estado != 'borrador':
            return Response(
                {'error': f'Solo se pueden enviar requisiciones en BORRADOR. Estado actual: {requisicion.estado}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar que tenga productos
        if not requisicion.detalles.exists():
            return Response(
                {'error': 'La requisición debe tener al menos un producto'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar permiso (solo el centro propietario)
        user_centro = getattr(request.user.profile, 'centro', None) if hasattr(request.user, 'profile') else request.user.centro
        if requisicion.centro != user_centro and not request.user.is_superuser:
            return Response(
                {'error': 'No tiene permiso para enviar esta requisición'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Cambiar estado
        requisicion.estado = 'enviada'
        requisicion.save()
        
        logger.info(f"Requisición {requisicion.folio} enviada por {request.user.username}")
        
        # TODO: Enviar notificación a FARMACIA_ADMIN
        
        return Response(self.get_serializer(requisicion).data)

    @action(detail=True, methods=['post'])
    def autorizar(self, request, pk=None):
        """
        Autoriza requisición (ENVIADA → AUTORIZADA)
        Solo FARMACIA_ADMIN y SUPERUSUARIO
        
        Body opcional: { "detalles": [{"id": 1, "cantidad_autorizada": 50}] }
        """
        requisicion = self.get_object()
        
        # Validar estado
        if requisicion.estado not in ['enviada', 'parcial']:
            return Response(
                {'error': f'No se puede autorizar una requisición en estado {requisicion.estado}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar stock disponible
        for detalle in requisicion.detalles.all():
            stock_disponible = detalle.producto.get_stock_actual()
            cantidad_a_autorizar = detalle.cantidad_solicitada
            
            if stock_disponible < cantidad_a_autorizar:
                return Response(
                    {
                        'error': f'Stock insuficiente para {detalle.producto.clave}',
                        'producto': detalle.producto.clave,
                        'solicitado': cantidad_a_autorizar,
                        'disponible': stock_disponible
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Actualizar cantidades autorizadas (si se proporcionan)
        detalles_data = request.data.get('detalles', [])
        parcial = False
        
        with transaction.atomic():
            for detalle_data in detalles_data:
                detalle = DetalleRequisicion.objects.get(
                    id=detalle_data['id'],
                    requisicion=requisicion
                )
                cantidad_autorizada = detalle_data.get(
                    'cantidad_autorizada',
                    detalle.cantidad_solicitada
                )
                
                if cantidad_autorizada > detalle.cantidad_solicitada:
                    return Response(
                        {'error': 'Cantidad autorizada no puede exceder solicitada'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                detalle.cantidad_autorizada = cantidad_autorizada
                detalle.save()
                
                if cantidad_autorizada < detalle.cantidad_solicitada:
                    parcial = True
            
            # Actualizar requisición
            requisicion.estado = 'parcial' if parcial else 'autorizada'
            requisicion.usuario_autoriza = request.user
            requisicion.fecha_autorizacion = timezone.now()
            requisicion.save()
        
        logger.info(
            f"Requisición {requisicion.folio} autorizada "
            f"{'parcialmente' if parcial else 'totalmente'} por {request.user.username}"
        )
        
        # TODO: Enviar notificación al centro
        
        return Response(self.get_serializer(requisicion).data)

    @action(detail=True, methods=['post'])
    def rechazar(self, request, pk=None):
        """
        Rechaza requisición (ENVIADA → RECHAZADA)
        Solo FARMACIA_ADMIN y SUPERUSUARIO
        
        Body: { "motivo": "..." }
        """
        requisicion = self.get_object()
        
        # Validar estado
        if requisicion.estado != 'enviada':
            return Response(
                {'error': f'No se puede rechazar una requisición en estado {requisicion.estado}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        motivo = request.data.get('motivo', '')
        
        if not motivo:
            return Response(
                {'error': 'El motivo de rechazo es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Rechazar requisición
        requisicion.estado = 'rechazada'
        requisicion.motivo_rechazo = motivo
        requisicion.usuario_autoriza = request.user
        requisicion.fecha_autorizacion = timezone.now()
        requisicion.save()
        
        logger.warning(f"Requisición {requisicion.folio} rechazada por {request.user.username}: {motivo}")
        
        # TODO: Enviar notificación al centro
        
        return Response(self.get_serializer(requisicion).data)

    @action(detail=True, methods=['post'])
    def surtir(self, request, pk=None):
        """
        Surte requisición autorizada (AUTORIZADA → SURTIDA)
        Descuenta de lotes con FIFO (primero en caducar)
        Solo FARMACIA_ADMIN y SUPERUSUARIO
        """
        requisicion = self.get_object()
        
        # Validar estado
        if requisicion.estado != 'autorizada':
            return Response(
                {'error': f'Solo se pueden surtir requisiciones AUTORIZADAS. Estado actual: {requisicion.estado}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        errores = []
        
        with transaction.atomic():
            for detalle in requisicion.detalles.all():
                cantidad_pendiente = detalle.cantidad_autorizada - detalle.cantidad_surtida
                
                if cantidad_pendiente > 0:
                    # Obtener lotes disponibles ordenados por caducidad (FIFO)
                    lotes = Lote.objects.filter(
                        producto=detalle.producto,
                        estado='disponible',
                        cantidad_actual__gt=0,
                        deleted_at__isnull=True
                    ).order_by('fecha_caducidad')
                    
                    cantidad_total_disponible = sum(l.cantidad_actual for l in lotes)
                    
                    if cantidad_total_disponible < cantidad_pendiente:
                        errores.append({
                            'producto': detalle.producto.clave,
                            'solicitado': cantidad_pendiente,
                            'disponible': cantidad_total_disponible
                        })
                        continue
                    
                    # Surtir de lotes (FIFO)
                    for lote in lotes:
                        if cantidad_pendiente == 0:
                            break
                        
                        cantidad_a_surtir = min(cantidad_pendiente, lote.cantidad_actual)
                        
                        # Crear movimiento de salida
                        Movimiento.objects.create(
                            tipo='requisicion',
                            lote=lote,
                            centro=requisicion.centro,
                            cantidad=-cantidad_a_surtir,
                            usuario=request.user,
                            requisicion=requisicion,
                            observaciones=f'Surtido de requisición {requisicion.folio}'
                        )
                        
                        detalle.cantidad_surtida += cantidad_a_surtir
                        cantidad_pendiente -= cantidad_a_surtir
                
                detalle.save()
            
            if errores:
                transaction.set_rollback(True)
                return Response(
                    {'error': 'Stock insuficiente', 'detalles': errores},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Marcar como surtida
            requisicion.estado = 'surtida'
            requisicion.save()
        
        logger.info(f"Requisición {requisicion.folio} surtida por {request.user.username}")
        
        # TODO: Enviar notificación al centro
        
        return Response(self.get_serializer(requisicion).data)

    @action(detail=True, methods=['get'], url_path='hoja-recoleccion')
    def hoja_recoleccion(self, request, pk=None):
        """
        Genera PDF con hoja de recolección
        
        Permisos:
        - SUPERUSUARIO: Siempre puede
        - FARMACIA_ADMIN: Siempre puede
        - CENTRO_USER: Solo si es su requisición Y está AUTORIZADA
        - VISTA_USER: No puede
        """
        requisicion = self.get_object()
        
        # Validar estado
        if requisicion.estado not in ['autorizada', 'surtida']:
            return Response(
                {'error': f'Solo requisiciones AUTORIZADAS o SURTIDAS tienen hoja de recolección. Estado actual: {requisicion.estado}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar permiso
        user = request.user
        user_centro = getattr(user.profile, 'centro', None) if hasattr(user, 'profile') else user.centro
        
        puede_descargar = (
            user.is_superuser or
            user.groups.filter(name='FARMACIA_ADMIN').exists() or
            (user.groups.filter(name='CENTRO_USER').exists() and requisicion.centro == user_centro)
        )
        
        if not puede_descargar:
            return Response(
                {'error': 'No tiene permiso para cancelar esta requisición'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Generar PDF
        try:
            pdf_buffer = generar_hoja_recoleccion(requisicion)
            
            response = HttpResponse(pdf_buffer, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="Hoja_Recoleccion_{requisicion.folio}.pdf"'
            
            logger.info(f"Hoja de recolección generada para {requisicion.folio} por {user.username}")
            
            return response
            
        except Exception as e:
            logger.error(f"Error al generar hoja de recolección: {str(e)}")
            return Response(
                {'error': f'Error al generar PDF: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        """
        Cancela requisición
        Solo el creador o SUPERUSUARIO/FARMACIA_ADMIN pueden cancelar
        No se puede cancelar si ya está SURTIDA
        """
        requisicion = self.get_object()
        
        # Validar estado
        if requisicion.estado in ['surtida', 'cancelada']:
            return Response(
                {'error': f'No se puede cancelar una requisición {requisicion.estado}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar permiso
        user = request.user
        user_centro = getattr(user.profile, 'centro', None) if hasattr(user, 'profile') else user.centro
        
        puede_cancelar = (
            user.is_superuser or
            user.groups.filter(name='FARMACIA_ADMIN').exists() or
            requisicion.centro == user_centro
        )
        
        if not puede_cancelar:
            return Response(
                {'error': 'No tiene permiso para cancelar esta requisición'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Cancelar
        requisicion.estado = 'cancelada'
        requisicion.save()
        
        logger.info(f"Requisición {requisicion.folio} cancelada por {user.username}")
        
        return Response(self.get_serializer(requisicion).data)

class AuditoriaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet de solo lectura para consultar logs de auditoría
    Solo SUPERUSUARIO y FARMACIA_ADMIN
    """
    queryset = AuditoriaLog.objects.select_related('usuario').all()
    serializer_class = AuditoriaLogSerializer
    permission_classes = [IsFarmaciaAdmin]
    pagination_class = CustomPagination
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields = ['usuario__username', 'accion', 'modelo', 'objeto_repr']
    filterset_fields = ['modelo', 'accion', 'usuario']
    ordering_fields = ['fecha']
    ordering = ['-fecha']
    
    def get_queryset(self):
        """Filtra por rango de fechas si se proporciona"""
        queryset = super().get_queryset()
        
        fecha_inicio = self.request.query_params.get('fecha_inicio')
        fecha_fin = self.request.query_params.get('fecha_fin')
        
        if fecha_inicio:
            try:
                queryset = queryset.filter(fecha__gte=fecha_inicio)
            except:
                pass
        
        if fecha_fin:
            try:
                queryset = queryset.filter(fecha__lte=fecha_fin)
            except:
                pass
        
        return queryset

