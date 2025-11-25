"""
ViewSets para la API REST del sistema de farmacia penitenciaria
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from datetime import date, timedelta
from io import BytesIO
import openpyxl
import logging

from core.models import (
    User, Centro, Producto, Lote, Requisicion, DetalleRequisicion,
    Movimiento, AuditoriaLog, ImportacionLog, Notificacion, UserProfile
)
from core.serializers import (
    UserSerializer, CentroSerializer, UserMeSerializer,
    ProductoSerializer, LoteSerializer, RequisicionSerializer,
    DetalleRequisicionSerializer, MovimientoSerializer,
    AuditoriaLogSerializer, ImportacionLogSerializer, NotificacionSerializer
)
from core.permissions import (
    IsFarmaciaRole, IsCentroUser, CanAuthorizeRequisicion, CanViewNotifications, CanViewProfile
)

logger = logging.getLogger(__name__)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 1000


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet para gestion de usuarios"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['username', 'date_joined']
    ordering = ['-date_joined']

    def get_serializer_class(self):
        if self.action in ['me', 'me_change_password']:
            return UserMeSerializer
        return super().get_serializer_class()

    def get_permissions(self):
        perms = super().get_permissions()
        if self.action in ['me', 'me_change_password']:
            perms.append(CanViewProfile())
        return perms

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return User.objects.all()
        return User.objects.filter(id=user.id)

    @action(detail=False, methods=['get', 'patch'], url_path='me')
    def me(self, request):
        """GET/PATCH /api/usuarios/me/ - Perfil del usuario autenticado"""
        UserProfile.objects.get_or_create(user=request.user)
        
        if request.method == 'PATCH':
            serializer = UserMeSerializer(request.user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        else:
            serializer = UserMeSerializer(request.user)
            return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='me/change-password')
    def me_change_password(self, request):
        """POST /api/usuarios/me/change-password/"""
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')

        if not all([old_password, new_password, confirm_password]):
            return Response({'error': 'Debe proporcionar old_password, new_password y confirm_password'}, status=status.HTTP_400_BAD_REQUEST)

        if new_password != confirm_password:
            return Response({'error': 'Las contraseñas nuevas no coinciden'}, status=status.HTTP_400_BAD_REQUEST)

        if not user.check_password(old_password):
            logger.warning("Intento de cambio de contraseña fallido para %s: contraseña actual incorrecta", user.username)
            return Response({'error': 'Contraseña actual incorrecta'}, status=status.HTTP_400_BAD_REQUEST)

        if len(new_password) < 8:
            return Response({'error': 'La nueva contraseña debe tener al menos 8 caracteres'}, status=status.HTTP_400_BAD_REQUEST)

        if old_password == new_password:
            return Response({'error': 'La nueva contraseña debe ser diferente a la anterior'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        logger.info("Contraseña actualizada para usuario %s", user.username)
        return Response({'message': 'Contraseña actualizada exitosamente'})


# NOTA: ProductoViewSet, LoteViewSet, RequisicionViewSet y CentroViewSet
# están en inventario/views.py para evitar duplicación.
# Importar desde allí si es necesario.


class DetalleRequisicionViewSet(viewsets.ModelViewSet):
    """ViewSet para detalles de requisiciones"""
    queryset = DetalleRequisicion.objects.all()
    serializer_class = DetalleRequisicionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination


class AuditoriaLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para registros de auditoria (solo lectura)"""
    queryset = AuditoriaLog.objects.all()
    serializer_class = AuditoriaLogSerializer
    permission_classes = [IsAuthenticated, IsFarmaciaRole]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['modelo', 'usuario__username', 'accion']
    ordering_fields = ['fecha_creacion']
    ordering = ['-fecha_creacion']


class ImportacionLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para registros de importacion (solo lectura)"""
    queryset = ImportacionLog.objects.all()
    serializer_class = ImportacionLogSerializer
    permission_classes = [IsAuthenticated, IsFarmaciaRole]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['modelo', 'usuario__username', 'estado']
    ordering_fields = ['fecha_creacion']
    ordering = ['-fecha_creacion']


class NotificacionViewSet(viewsets.ModelViewSet):
    """ViewSet para notificaciones del usuario"""
    serializer_class = NotificacionSerializer
    permission_classes = [IsAuthenticated, CanViewNotifications]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['fecha_creacion']
    ordering = ['-fecha_creacion']

    def get_queryset(self):
        queryset = Notificacion.objects.filter(usuario=self.request.user)
        tipo = self.request.query_params.get('tipo')
        if tipo:
            queryset = queryset.filter(tipo=tipo)

        leida = self.request.query_params.get('leida')
        if leida in ['true', 'false']:
            queryset = queryset.filter(leida=leida == 'true')

        fecha_desde = self.request.query_params.get('desde')
        fecha_hasta = self.request.query_params.get('hasta')
        try:
            if fecha_desde:
                queryset = queryset.filter(fecha_creacion__date__gte=fecha_desde)
            if fecha_hasta:
                queryset = queryset.filter(fecha_creacion__date__lte=fecha_hasta)
        except Exception:
            pass

        return queryset

    @action(detail=True, methods=['post'])
    def marcar_leida(self, request, pk=None):
        """POST /api/notificaciones/{id}/marcar_leida/"""
        notificacion = self.get_object()
        notificacion.leida = True
        notificacion.save()
        return Response({'leida': True})

    @action(detail=False, methods=['get'])
    def no_leidas_count(self, request):
        """GET /api/notificaciones/no_leidas_count/"""
        count = self.get_queryset().filter(leida=False).count()
        return Response({'no_leidas': count})


class ReportesViewSet(viewsets.ViewSet):
    """ViewSet para reportes del sistema"""
    permission_classes = [IsAuthenticated, IsFarmaciaRole]

    @method_decorator(cache_page(60 * 5))  # Cache 5 minutos
    @action(detail=False, methods=['get'])
    def inventario(self, request):
        """GET /api/reportes/inventario/?formato=excel|pdf|json"""
        from django.http import FileResponse
        from core.utils.pdf_reports import generar_reporte_inventario
        
        formato = request.query_params.get('formato', 'json')

        queryset = Producto.objects.select_related('created_by').prefetch_related('lotes')

        datos = []
        for producto in queryset:
            stock_actual = producto.get_stock_actual()
            datos.append({
                'id': producto.id,
                'clave': producto.clave,
                'descripcion': producto.descripcion,
                'stock_actual': stock_actual,
                'stock_minimo': producto.stock_minimo,
                'nivel_stock': producto.get_nivel_stock(),
                'precio_unitario': float(producto.precio_unitario),
                'valor_inventario': float(stock_actual * producto.precio_unitario),
                'lotes_activos': producto.lotes.filter(estado='disponible').count()
            })

        resumen = {
            'total_productos': len(datos),
            'productos_sin_stock': sum(1 for d in datos if d['stock_actual'] == 0),
            'productos_stock_critico': sum(1 for d in datos if d['nivel_stock'] == 'critico'),
            'valor_total_inventario': sum(d['valor_inventario'] for d in datos)
        }

        if formato == 'pdf':
            pdf_buffer = generar_reporte_inventario(datos)
            return FileResponse(
                pdf_buffer,
                content_type='application/pdf',
                as_attachment=True,
                filename=f'reporte_inventario_{timezone.now().strftime("%Y%m%d")}.pdf'
            )

        if formato == 'excel':
            workbook = openpyxl.Workbook()
            sheet = workbook.active
            sheet.title = 'Inventario'

            headers = ['Clave', 'Descripcion', 'Stock Actual', 'Stock Minimo', 'Nivel', 'Precio Unitario', 'Valor Total']
            sheet.append(headers)

            for d in datos:
                sheet.append([
                    d['clave'],
                    d['descripcion'],
                    d['stock_actual'],
                    d['stock_minimo'],
                    d['nivel_stock'],
                    d['precio_unitario'],
                    d['valor_inventario']
                ])

            for row in sheet.iter_rows(min_row=1, max_row=len(datos) + 1):
                for cell in row:
                    cell.alignment = openpyxl.styles.Alignment(horizontal='center')

            buffer = BytesIO()
            workbook.save(buffer)
            buffer.seek(0)

            return FileResponse(
                buffer,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                filename='reporte_inventario.xlsx'
            )

        return Response({
            'reporte': 'inventario',
            'fecha_generacion': timezone.now().isoformat(),
            'datos': datos,
            'resumen': resumen
        })

    @method_decorator(cache_page(60 * 5))  # Cache 5 minutos
    @action(detail=False, methods=['get'])
    def caducidades(self, request):
        """GET /api/reportes/caducidades/?dias=30&formato=json|pdf"""
        from django.http import FileResponse
        from core.utils.pdf_reports import generar_reporte_caducidades
        
        dias = int(request.query_params.get('dias', 30))
        formato = request.query_params.get('formato', 'json')
        fecha_limite = date.today() + timedelta(days=dias)

        lotes = Lote.objects.filter(
            fecha_caducidad__lte=fecha_limite,
            estado__in=['disponible', 'critico', 'proximo'],
            deleted_at__isnull=True
        ).select_related('producto').order_by('fecha_caducidad')

        datos = []
        for lote in lotes:
            dias_restantes = lote.dias_para_caducar()
            datos.append({
                'id': lote.id,
                'producto_clave': lote.producto.clave,
                'producto_descripcion': lote.producto.descripcion,
                'numero_lote': lote.numero_lote,
                'fecha_caducidad': lote.fecha_caducidad.isoformat(),
                'dias_restantes': dias_restantes,
                'alerta': lote.alerta_caducidad(),
                'cantidad_actual': lote.cantidad_actual,
                'proveedor': lote.proveedor
            })

        resumen = {
            'total_lotes_proximos': len(datos),
            'lotes_vencidos': sum(1 for d in datos if d['alerta'] == 'vencido'),
            'lotes_criticos': sum(1 for d in datos if d['alerta'] == 'critico'),
            'lotes_proximos': sum(1 for d in datos if d['alerta'] == 'proximo')
        }

        if formato == 'pdf':
            pdf_buffer = generar_reporte_caducidades(datos, dias=dias)
            return FileResponse(
                pdf_buffer,
                content_type='application/pdf',
                as_attachment=True,
                filename=f'reporte_caducidades_{timezone.now().strftime("%Y%m%d")}.pdf'
            )

        return Response({
            'reporte': 'caducidades',
            'fecha_generacion': timezone.now().isoformat(),
            'datos': datos,
            'resumen': resumen
        })

    @method_decorator(cache_page(60 * 10))  # Cache 10 minutos
    @action(detail=False, methods=['get'])
    def requisiciones(self, request):
        """GET /api/reportes/requisiciones/?formato=json|pdf"""
        from django.http import FileResponse
        from core.utils.pdf_reports import generar_reporte_requisiciones
        
        formato = request.query_params.get('formato', 'json')
        estado = request.query_params.get('estado')
        fecha_inicio = request.query_params.get('fecha_inicio')
        fecha_fin = request.query_params.get('fecha_fin')

        queryset = Requisicion.objects.select_related(
            'centro', 'usuario_solicita', 'usuario_autoriza'
        ).prefetch_related('detalles')

        filtros = {}
        if estado:
            queryset = queryset.filter(estado=estado)
            filtros['estado'] = estado

        if fecha_inicio:
            queryset = queryset.filter(fecha_solicitud__gte=fecha_inicio)
            filtros['fecha_inicio'] = fecha_inicio

        if fecha_fin:
            queryset = queryset.filter(fecha_solicitud__lte=fecha_fin)
            filtros['fecha_fin'] = fecha_fin

        datos = []
        for req in queryset:
            datos.append({
                'id': req.id,
                'folio': req.folio,
                'centro_nombre': req.centro.nombre,
                'estado': req.estado,
                'fecha_solicitud': req.fecha_solicitud.isoformat(),
                'total_items': req.detalles.count(),
                'usuario_solicita': req.usuario_solicita.username
            })

        if formato == 'pdf':
            pdf_buffer = generar_reporte_requisiciones(datos, filtros=filtros)
            return FileResponse(
                pdf_buffer,
                content_type='application/pdf',
                as_attachment=True,
                filename=f'reporte_requisiciones_{timezone.now().strftime("%Y%m%d")}.pdf'
            )

        return Response({
            'reporte': 'requisiciones',
            'fecha_generacion': timezone.now().isoformat(),
            'datos': datos
        })


# ============================================
# AUTENTICACION JWT
# ============================================

class CustomTokenObtainPairView(TokenObtainPairView):
    """
    View personalizado para login que retorna tokens + datos del usuario.
    Usa CustomTokenObtainPairSerializer de serializers_jwt.py
    """
    from core.serializers_jwt import CustomTokenObtainPairSerializer
    serializer_class = CustomTokenObtainPairSerializer


class LogoutView(APIView):
    """Endpoint para logout (blacklist del refresh token)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                # Si no se envía refresh, solo confirmamos logout
                # (el access token expirará naturalmente)
                return Response({"message": "Logout exitoso (access token invalidado)"}, status=status.HTTP_200_OK)
            
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Logout exitoso (refresh blacklisted)"}, status=status.HTTP_200_OK)
        except Exception as e:
            # Si el refresh ya expiró o es inválido, igual consideramos logout exitoso
            return Response({"message": "Logout completado (refresh inválido/expirado)", "detail": str(e)}, status=status.HTTP_200_OK)


class DevAutoLoginView(APIView):
    """
    SOLO DESARROLLO: Autologin sin credenciales.
    DEBE deshabilitarse en produccion.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username', 'admin')
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response(
                {'error': f'Usuario {username} no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )

        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        })

# NOTA: UserProfileView eliminada - usar /api/usuarios/me/ del UserViewSet
# class UserProfileView eliminada (código muerto, duplicaba funcionalidad)







