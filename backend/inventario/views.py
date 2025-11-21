from rest_framework import viewsets, status, serializers, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import HttpResponse
from django.db.models import Q, Sum, Count, F
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import Group  # ← AGREGAR ESTE IMPORT
from datetime import datetime, timedelta
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
import traceback
import random
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from core.models import Producto, Lote, Movimiento, Centro, Requisicion, DetalleRequisicion
from .serializers import (
    ProductoSerializer, LoteSerializer, MovimientoSerializer, 
    CentroSerializer, RequisicionSerializer, DetalleRequisicionSerializer
)

from django.contrib.auth import get_user_model
from core.permissions import (
    IsAdminRole, IsFarmaciaRole, IsCentroRole, IsVistaRole,
    IsFarmaciaAdminOrReadOnly, CanAuthorizeRequisicion
)

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    grupos = serializers.SerializerMethodField()
    rol = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_superuser', 'grupos', 'rol', 'date_joined']
        read_only_fields = ['id', 'date_joined']

    def get_grupos(self, obj):
        return [g.name for g in obj.groups.all()]

    def get_rol(self, obj):
        if obj.is_superuser:
            return 'SUPERUSER'
        grupos = obj.groups.all()
        if grupos.exists():
            return grupos.first().name
        return 'USUARIO'

@method_decorator(csrf_exempt, name='dispatch')
class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar usuarios.
    
    Funcionalidades:
    - CRUD completo
    - Asignación de roles
    - Asignación de centros
    - Activación/Desactivación
    - Cambio de contraseñas
    - Filtrado por rol y estado
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        """Filtra usuarios según parámetros"""
        queryset = User.objects.all()
        
        # Filtro por estado activo
        activo = self.request.query_params.get('activo')
        if activo == 'true':
            queryset = queryset.filter(is_active=True)
        elif activo == 'false':
            queryset = queryset.filter(is_active=False)
        
        # Filtro por rol
        rol = self.request.query_params.get('rol')
        if rol:
            if rol == 'SUPERUSER':
                queryset = queryset.filter(is_superuser=True)
            else:
                queryset = queryset.filter(groups__name=rol)
        
        # Búsqueda por nombre o username
        search = self.request.query_params.get('search')
        if search and search.strip():
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )
        
        return queryset.order_by('-date_joined')
    
    def create(self, request, *args, **kwargs):
        """Crea un nuevo usuario"""
        try:
            print("=" * 50)
            print("📥 CREAR USUARIO - Datos recibidos:")
            print(f"   Body: {request.data}")
            print("=" * 50)
            
            # Validar datos requeridos
            if not request.data.get('username'):
                return Response({
                    'error': 'El nombre de usuario es requerido'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not request.data.get('password'):
                return Response({
                    'error': 'La contraseña es requerida'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Crear usuario
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            
            # Asignar rol si se especificó
            rol = request.data.get('rol')
            if rol and rol != 'USUARIO':
                if rol == 'SUPERUSER':
                    user.is_superuser = True
                    user.is_staff = True
                    user.save()
                else:
                    # Asignar a grupo
                    grupo, created = Group.objects.get_or_create(name=rol)
                    user.groups.add(grupo)
            
            print(f"✅ Usuario creado: {user.username}")
            
            return Response({
                'mensaje': 'Usuario creado exitosamente',
                'usuario': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
            
        except serializers.ValidationError as e:
            print(f"❌ Error de validación: {e.detail}")
            return Response({
                'error': 'Error de validación',
                'detalles': e.detail
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            print(f"❌ Error inesperado: {str(e)}")
            traceback.print_exc()
            return Response({
                'error': 'Error al crear usuario',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def update(self, request, *args, **kwargs):
        """Actualiza un usuario existente"""
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            
            print("=" * 50)
            print(f"📝 ACTUALIZAR USUARIO: {instance.username}")
            print(f"   Datos: {request.data}")
            print("=" * 50)
            
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            
            # Actualizar rol si cambió
            rol = request.data.get('rol')
            if rol:
                # Limpiar grupos actuales
                user.groups.clear()
                user.is_superuser = False
                user.is_staff = False
                
                if rol == 'SUPERUSER':
                    user.is_superuser = True
                    user.is_staff = True
                elif rol != 'USUARIO':
                    grupo, created = Group.objects.get_or_create(name=rol)
                    user.groups.add(grupo)
                
                user.save()
            
            print(f"✅ Usuario actualizado: {user.username}")
            
            return Response({
                'mensaje': 'Usuario actualizado exitosamente',
                'usuario': UserSerializer(user).data
            })
            
        except serializers.ValidationError as e:
            print(f"❌ Error de validación: {e.detail}")
            return Response({
                'error': 'Error de validación',
                'detalles': e.detail
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            traceback.print_exc()
            return Response({
                'error': 'Error al actualizar usuario',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def destroy(self, request, *args, **kwargs):
        """Elimina un usuario"""
        instance = self.get_object()
        
        try:
            # Validar que no sea el último superusuario
            if instance.is_superuser:
                total_superusers = User.objects.filter(is_superuser=True).count()
                if total_superusers <= 1:
                    return Response({
                        'error': 'No se puede eliminar el último superusuario',
                        'sugerencia': 'Debe haber al menos un superusuario en el sistema'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            username_eliminado = instance.username
            instance.delete()
            
            print(f"✅ Usuario eliminado: {username_eliminado}")
            
            return Response({
                'mensaje': 'Usuario eliminado exitosamente',
                'usuario_eliminado': username_eliminado
            }, status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            print(f"❌ Error al eliminar: {str(e)}")
            traceback.print_exc()
            return Response({
                'error': 'Error al eliminar usuario',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def cambiar_password(self, request, pk=None):
        """Cambia la contraseña de un usuario"""
        try:
            user = self.get_object()
            new_password = request.data.get('password')
            
            if not new_password:
                return Response({
                    'error': 'La contraseña es requerida'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if len(new_password) < 6:
                return Response({
                    'error': 'La contraseña debe tener al menos 6 caracteres'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            user.set_password(new_password)
            user.save()
            
            return Response({
                'mensaje': 'Contraseña actualizada exitosamente'
            })
            
        except Exception as e:
            traceback.print_exc()
            return Response({
                'error': 'Error al cambiar contraseña',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Activa/Desactiva un usuario"""
        try:
            user = self.get_object()
            user.is_active = not user.is_active
            user.save()
            
            estado = 'activado' if user.is_active else 'desactivado'
            
            return Response({
                'mensaje': f'Usuario {estado} exitosamente',
                'is_active': user.is_active
            })
            
        except Exception as e:
            traceback.print_exc()
            return Response({
                'error': 'Error al cambiar estado del usuario',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer
    permission_classes = [IsFarmaciaAdminOrReadOnly]

    def get_queryset(self):
        queryset = Producto.objects.all()
        
        activo = self.request.query_params.get('activo')
        if activo == 'true':
            queryset = queryset.filter(activo=True)
        elif activo == 'false':
            queryset = queryset.filter(activo=False)
        
        unidad = self.request.query_params.get('unidad_medida')
        if unidad and unidad != '':
            queryset = queryset.filter(unidad_medida=unidad)
        
        search = self.request.query_params.get('search')
        if search and search.strip():
            queryset = queryset.filter(
                Q(clave__icontains=search) | 
                Q(descripcion__icontains=search)
            )

        stock_status = self.request.query_params.get('stock_status')
        if stock_status:
            queryset = queryset.annotate(
                stock_total_calc=Coalesce(
                    Sum(
                        'lotes__cantidad_actual',
                        filter=Q(
                            lotes__deleted_at__isnull=True,
                            lotes__cantidad_actual__gt=0
                        )
                    ),
                    0.0
                )
            )
            status_val = stock_status.lower()
            if status_val == 'sin_stock':
                queryset = queryset.filter(stock_total_calc__lte=0)
            elif status_val == 'critico':
                queryset = queryset.filter(
                    stock_total_calc__gt=0,
                    stock_minimo__gt=0,
                    stock_total_calc__lt=F('stock_minimo') * 0.5
                )
            elif status_val == 'bajo':
                queryset = queryset.filter(
                    Q(
                        stock_minimo__gt=0,
                        stock_total_calc__gte=F('stock_minimo') * 0.5,
                        stock_total_calc__lt=F('stock_minimo')
                    ) | Q(
                        stock_minimo__lte=0,
                        stock_total_calc__gt=0,
                        stock_total_calc__lt=25
                    )
                )
            elif status_val == 'normal':
                queryset = queryset.filter(
                    Q(
                        stock_minimo__gt=0,
                        stock_total_calc__gte=F('stock_minimo'),
                        stock_total_calc__lte=F('stock_minimo') * 2
                    ) | Q(
                        stock_minimo__lte=0,
                        stock_total_calc__gte=25,
                        stock_total_calc__lt=100
                    )
                )
            elif status_val == 'alto':
                queryset = queryset.filter(
                    Q(
                        stock_minimo__gt=0,
                        stock_total_calc__gt=F('stock_minimo') * 2
                    ) | Q(
                        stock_minimo__lte=0,
                        stock_total_calc__gte=100
                    )
                )
        
        return queryset.order_by('-created_at')
    
    def create(self, request, *args, **kwargs):
        """
        Crea un nuevo producto.
        
        Validaciones:
        - Clave única
        - Campos requeridos
        - Formato correcto
        """
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            
            headers = self.get_success_headers(serializer.data)
            return Response(
                serializer.data, 
                status=status.HTTP_201_CREATED, 
                headers=headers
            )
        except Exception as e:
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def update(self, request, *args, **kwargs):
        """
        Actualiza un producto existente.
        
        Validaciones:
        - Clave única (si se modifica)
        - Datos válidos
        """
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            
            return Response(serializer.data)
        except Exception as e:
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, *args, **kwargs):
        """
        Elimina un producto.
        
        Validaciones:
        - No puede eliminarse si tiene lotes asociados
        - Confirmación de eliminación
        """
        instance = self.get_object()
        
        try:
            if instance.lotes.exists():
                return Response({
                    'error': 'No se puede eliminar el producto',
                    'razon': 'Tiene lotes asociados',
                    'sugerencia': 'Elimine primero los lotes o marque el producto como inactivo'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            instance.delete()
            return Response({'mensaje': 'Producto eliminado exitosamente'}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def exportar_excel(self, request):
        """
        Exporta todos los productos a un archivo Excel.
        
        Columnas:
        - #, Clave, Descripción, Unidad, Precio, Stock Mínimo, Stock Actual, Lotes, Estado
        """
        try:
            productos = self.get_queryset()
            
            # Crear libro de Excel
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = 'Productos'
            
            # Encabezados
            headers = ['#', 'Clave', 'Descripción', 'Unidad Medida', 'Precio Unitario', 'Stock Mínimo', 'Stock Actual', 'Lotes Activos', 'Estado']
            ws.append(headers)
            
            # Estilo de encabezados
            header_fill = PatternFill(start_color='632842', end_color='632842', fill_type='solid')
            header_font = Font(bold=True, color='FFFFFF', size=12)
            
            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Datos de productos
            for idx, producto in enumerate(productos, start=1):
                stock_actual = producto.lotes.filter(estado='disponible').aggregate(total=Sum('cantidad_actual'))['total'] or 0
                lotes_activos = producto.lotes.filter(estado='disponible', cantidad_actual__gt=0).count()
                
                ws.append([
                    idx,
                    producto.clave,
                    producto.descripcion,
                    producto.unidad_medida,
                    float(producto.precio_unitario) if producto.precio_unitario else 0,
                    producto.stock_minimo,
                    stock_actual,
                    lotes_activos,
                    'Activo' if producto.activo else 'Inactivo'
                ])
                
                # Colorear fila si el stock está por debajo del mínimo
                if stock_actual < producto.stock_minimo:
                    for col in range(1, 10):
                        ws.cell(row=idx+1, column=col).fill = PatternFill(
                            start_color='FFF4E6', 
                            end_color='FFF4E6', 
                            fill_type='solid'
                        )
            
            # Ajustar anchos de columna
            ws.column_dimensions['A'].width = 8
            ws.column_dimensions['B'].width = 15
            ws.column_dimensions['C'].width = 50
            ws.column_dimensions['D'].width = 15
            ws.column_dimensions['E'].width = 15
            ws.column_dimensions['F'].width = 15
            ws.column_dimensions['G'].width = 15
            ws.column_dimensions['H'].width = 15
            ws.column_dimensions['I'].width = 12
            
            # Generar respuesta
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename=Productos_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            wb.save(response)
            
            return response
            
        except Exception as e:
            traceback.print_exc()
            return Response({
                'error': 'Error al exportar productos',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def importar_excel(self, request):
        """
        Importa productos desde un archivo Excel.
        
        Formato esperado:
        Fila 1: Encabezados (se ignora)
        Columnas: Clave | Descripción | Unidad | Precio | Stock Mínimo | Estado
        """
        file = request.FILES.get('file')
        
        if not file:
            return Response({
                'error': 'No se recibió archivo',
                'mensaje': 'Debe seleccionar un archivo Excel (.xlsx)'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            wb = openpyxl.load_workbook(file)
            ws = wb.active
            
            creados = 0
            actualizados = 0
            errores = []
            
            # Procesar cada fila (empezando desde la fila 2)
            for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                try:
                    # Extraer valores (asegurarse de tener al menos 6 columnas)
                    valores = list(row) + [None] * 6
                    clave = valores[0]
                    descripcion = valores[1]
                    unidad_medida = valores[2]
                    precio_unitario = valores[3]
                    stock_minimo = valores[4]
                    estado = valores[5]
                    
                    # Validar campos requeridos
                    if not clave or not descripcion:
                        errores.append(f'Fila {row_idx}: Clave y descripción son obligatorios')
                        continue
                    
                    # Limpiar y preparar datos
                    datos = {
                        'descripcion': str(descripcion).strip(),
                        'unidad_medida': str(unidad_medida).strip().upper() if unidad_medida else 'PIEZA',
                        'precio_unitario': float(precio_unitario) if precio_unitario and str(precio_unitario).replace('.','').isdigit() else 0.0,
                        'stock_minimo': int(stock_minimo) if stock_minimo and str(stock_minimo).isdigit() else 10,
                        'activo': str(estado).lower() in ['activo', 'sí', 'si', 'true', '1', 'yes'] if estado else True
                    }
                    
                    # Crear o actualizar producto
                    producto, created = Producto.objects.update_or_create(
                        clave=str(clave).upper().strip(),
                        defaults=datos
                    )
                    
                    if created:
                        creados += 1
                    else:
                        actualizados += 1
                        
                except Exception as e:
                    errores.append(f'Fila {row_idx}: {str(e)}')
            
            return Response({
                'mensaje': 'Importación completada',
                'resumen': {
                    'creados': creados,
                    'actualizados': actualizados,
                    'total_procesados': creados + actualizados,
                    'total_errores': len(errores)
                },
                'errores': errores[:10] if errores else [],
                'tiene_mas_errores': len(errores) > 10,
                'exito': len(errores) == 0
            }, status=status.HTTP_200_OK if len(errores) == 0 else status.HTTP_207_MULTI_STATUS)
            
        except Exception as e:
            traceback.print_exc()
            return Response({
                'error': 'Error al procesar archivo',
                'mensaje': str(e),
                'sugerencia': 'Verifique que el archivo tenga el formato correcto: Clave, Descripción, Unidad, Precio, Stock Mínimo, Estado'
            }, status=status.HTTP_400_BAD_REQUEST)

@method_decorator(csrf_exempt, name='dispatch')
class CentroViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar centros penitenciarios.
    
    Funcionalidades:
    - CRUD completo
    - Búsqueda por clave, nombre y dirección
    - Filtrado por estado activo/inactivo
    - Exportar a Excel con formato profesional
    - Importar desde Excel con validaciones
    - Obtener requisiciones por centro
    """
    queryset = Centro.objects.all()
    serializer_class = CentroSerializer
    permission_classes = [IsFarmaciaAdminOrReadOnly]

    def get_queryset(self):
        """Filtra centros según parámetros"""
        queryset = Centro.objects.all()
        
        # Filtro por búsqueda
        search = self.request.query_params.get('search')
        if search and search.strip():
            queryset = queryset.filter(
                Q(clave__icontains=search) | 
                Q(nombre__icontains=search) | 
                Q(direccion__icontains=search)
            )
        
        # Filtro por estado activo
        activo = self.request.query_params.get('activo')
        if activo == 'true':
            queryset = queryset.filter(activo=True)
        elif activo == 'false':
            queryset = queryset.filter(activo=False)
        
        return queryset.order_by('-created_at')
    
    def create(self, request, *args, **kwargs):
        """Crea un nuevo centro"""
        try:
            print("=" * 50)
            print("📥 CREAR CENTRO - Datos recibidos:")
            print(f"   Body: {request.data}")
            print(f"   Headers: {dict(request.headers)}")
            print("=" * 50)
            
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            centro = serializer.save()
            
            print(f"✅ Centro creado: {centro.clave} - {centro.nombre}")
            
            return Response({
                'mensaje': 'Centro creado exitosamente',
                'centro': CentroSerializer(centro).data
            }, status=status.HTTP_201_CREATED)
            
        except serializers.ValidationError as e:
            print(f"❌ Error de validación: {e.detail}")
            return Response({
                'error': 'Error de validación',
                'detalles': e.detail
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            print(f"❌ Error inesperado: {str(e)}")
            traceback.print_exc()
            return Response({
                'error': 'Error al crear centro',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        """Actualiza un centro existente"""
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            
            return Response({
                'mensaje': 'Centro actualizado exitosamente',
                'centro': serializer.data
            })
        except serializers.ValidationError as e:
            return Response(
                {'error': 'Error de validación', 'detalles': e.detail},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            traceback.print_exc()
            return Response(
                {'error': 'Error al actualizar centro', 'mensaje': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, *args, **kwargs):
        """
        Elimina un centro.
        
        Validaciones:
        - No puede eliminarse si tiene requisiciones asociadas
        - No puede eliminarse si tiene usuarios asignados
        """
        instance = self.get_object()
        
        try:
            # Verificar requisiciones
            if hasattr(instance, 'requisiciones') and instance.requisiciones.exists():
                total_requisiciones = instance.requisiciones.count()
                requisiciones_activas = instance.requisiciones.exclude(
                    estado__in=['CANCELADA', 'SURTIDA']
                ).count()
                
                return Response({
                    'error': 'No se puede eliminar el centro',
                    'razon': 'Tiene requisiciones asociadas',
                    'total_requisiciones': total_requisiciones,
                    'requisiciones_activas': requisiciones_activas,
                    'sugerencia': 'Marque el centro como inactivo en lugar de eliminarlo'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Verificar usuarios asignados
            if hasattr(instance, 'usuarios') and instance.usuarios.exists():
                total_usuarios = instance.usuarios.count()
                
                return Response({
                    'error': 'No se puede eliminar el centro',
                    'razon': 'Tiene usuarios asignados',
                    'total_usuarios': total_usuarios,
                    'sugerencia': 'Reasigne los usuarios a otro centro o marque el centro como inactivo'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Si no tiene relaciones, se puede eliminar
            clave_eliminada = instance.clave
            nombre_eliminado = instance.nombre
            instance.delete()
            
            return Response({
                'mensaje': 'Centro eliminado exitosamente',
                'centro_eliminado': f"{clave_eliminada} - {nombre_eliminado}"
            }, status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            traceback.print_exc()
            return Response({
                'error': 'Error al eliminar centro',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def exportar_excel(self, request):
        """
        Exporta todos los centros a Excel con formato profesional.
        
        Columnas:
        - #, Clave, Nombre, Dirección, Teléfono, Total Requisiciones, Estado
        """
        try:
            centros = self.get_queryset()
            
            # Crear libro de Excel
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = 'Centros Penitenciarios'
            
            # Título del reporte
            ws.merge_cells('A1:G1')
            titulo_cell = ws['A1']
            titulo_cell.value = 'REPORTE DE CENTROS PENITENCIARIOS'
            titulo_cell.font = Font(bold=True, size=14, color='632842')
            titulo_cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Fecha de generación
            ws.merge_cells('A2:G2')
            fecha_cell = ws['A2']
            fecha_cell.value = f'Generado el {timezone.now().strftime("%d/%m/%Y %H:%M")}'

            fecha_cell.font = Font(size=10, italic=True)
            fecha_cell.alignment = Alignment(horizontal='center')
            
            # Espacio
            ws.append([])
            
            # Encabezados
            headers = ['#', 'Clave', 'Nombre', 'Dirección', 'Teléfono', 'Total Requisiciones', 'Estado']
            ws.append(headers)
            
            # Estilo de encabezados
            header_fill = PatternFill(start_color='632842', end_color='632842', fill_type='solid')
            header_font = Font(bold=True, color='FFFFFF', size=11)
            header_alignment = Alignment(horizontal='center', vertical='center')
            
            for col_num, cell in enumerate(ws[4], 1):
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = header_alignment
            
            # Datos de centros
            for idx, centro in enumerate(centros, start=1):
                # Calcular total de requisiciones si existe la relación
                total_requisiciones = 0
                if hasattr(centro, 'requisiciones'):
                    total_requisiciones = centro.requisiciones.count()
                
                ws.append([
                    idx,
                    centro.clave,
                    centro.nombre,
                    centro.direccion or 'Sin dirección',
                    centro.telefono or 'Sin teléfono',
                    total_requisiciones,
                    'Activo' if centro.activo else 'Inactivo'
                ])
                
                # Estilo para filas
                row_num = idx + 4
                for cell in ws[row_num]:
                    cell.alignment = Alignment(vertical='center')
                    
                # Colorear estado
                estado_cell = ws.cell(row=row_num, column=7)
                if centro.activo:
                    estado_cell.fill = PatternFill(start_color='D4EDDA', end_color='D4EDDA', fill_type='solid')
                    estado_cell.font = Font(color='155724', bold=True)
                else:
                    estado_cell.fill = PatternFill(start_color='F8D7DA', end_color='F8D7DA', fill_type='solid')
                    estado_cell.font = Font(color='721C24', bold=True)
            
            # Ajustar anchos de columna
            ws.column_dimensions['A'].width = 8
            ws.column_dimensions['B'].width = 20
            ws.column_dimensions['C'].width = 50
            ws.column_dimensions['D'].width = 40
            ws.column_dimensions['E'].width = 15
            ws.column_dimensions['F'].width = 20
            ws.column_dimensions['G'].width = 12
            
            # Agregar bordes
            from openpyxl.styles import Border, Side
            thin_border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
            
            for row in ws.iter_rows(min_row=4, max_row=ws.max_row, min_col=1, max_col=7):
                for cell in row:
                    cell.border = thin_border
            
            # Resumen al final
            ws.append([])
            resumen_row = ws.max_row + 1
            ws.merge_cells(f'A{resumen_row}:C{resumen_row}')
            resumen_cell = ws[f'A{resumen_row}']
            resumen_cell.value = f'TOTAL DE CENTROS: {centros.count()}'
            resumen_cell.font = Font(bold=True, size=11)
            resumen_cell.alignment = Alignment(horizontal='left')
            
            # Generar respuesta
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename=Centros_Penitenciarios_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            wb.save(response)
            
            return response
            
        except Exception as e:
            traceback.print_exc()
            return Response({
                'error': 'Error al exportar centros',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def importar_excel(self, request):
        """
        Importa centros desde Excel.
        
        Formato esperado:
        - Clave (requerido)
        - Nombre (requerido)
        - Dirección (opcional)
        - Teléfono (opcional)
        - Estado (Activo/Inactivo)
        """
        file = request.FILES.get('file')
        
        if not file:
            return Response({
                'error': 'No se recibió archivo',
                'mensaje': 'Debe enviar un archivo Excel (.xlsx)'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            wb = openpyxl.load_workbook(file)
            ws = wb.active
            
            creados = 0
            actualizados = 0
            errores = []
            
            # Procesar filas
            for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                try:
                    # Extraer datos
                    clave, nombre, direccion, telefono, estado = row[:5]
                    
                    # Validar requeridos
                    if not clave or not nombre:
                        errores.append(f'Fila {row_idx}: Clave y nombre son requeridos')
                        continue
                    
                    # Preparar datos
                    datos = {
                        'nombre': str(nombre).strip(),
                        'direccion': str(direccion).strip() if direccion else '',
                        'telefono': str(telefono).strip() if telefono else '',
                        'activo': str(estado).lower() in ['activo', 'sí', 'si', 'true', '1'] if estado else True
                    }
                    
                    # Crear o actualizar
                    centro, created = Centro.objects.update_or_create(
                        clave=str(clave).upper().strip(),
                        defaults=datos
                    )
                    
                    if created:
                        creados += 1
                    else:
                        actualizados += 1
                        
                except Exception as e:
                    errores.append(f'Fila {row_idx}: {str(e)}')
            
            return Response({
                'mensaje': 'Importación completada',
                'resumen': {
                    'creados': creados,
                    'actualizados': actualizados,
                    'total_procesados': creados + actualizados,
                    'errores_encontrados': len(errores)
                },
                'errores': errores[:10] if errores else [],  # Máximo 10 errores
                'tiene_mas_errores': len(errores) > 10,
                'exito': len(errores) == 0
            }, status=status.HTTP_200_OK if len(errores) == 0 else status.HTTP_207_MULTI_STATUS)
            
        except Exception as e:
            traceback.print_exc()
            return Response({
                'error': 'Error al procesar el archivo',
                'mensaje': str(e),
                'sugerencia': 'Verifique que el archivo tenga el formato correcto (Clave, Nombre, Dirección, Teléfono, Estado)'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def requisiciones(self, request, pk=None):
        """Obtiene todas las requisiciones de un centro"""
        try:
            centro = self.get_object()
            
            if not hasattr(centro, 'requisiciones'):
                return Response({
                    'centro': {
                        'id': centro.id,
                        'clave': centro.clave,
                        'nombre': centro.nombre
                    },
                    'requisiciones': [],
                    'total': 0,
                    'mensaje': 'No hay requisiciones disponibles'
                })
            
            requisiciones = centro.requisiciones.all().order_by('-fecha_solicitud')
            
            # Agrupar por estado
            por_estado = {}
            for req in requisiciones:
                estado = req.estado
                if estado not in por_estado:
                    por_estado[estado] = 0
                por_estado[estado] += 1
            
            requisiciones_data = []
            for req in requisiciones:
                requisiciones_data.append({
                    'id': req.id,
                    'folio': req.folio,
                    'estado': req.estado,
                    'fecha_solicitud': req.fecha_solicitud,
                    'total_items': req.items.count() if hasattr(req, 'items') else 0
                })
            
            return Response({
                'centro': {
                    'id': centro.id,
                    'clave': centro.clave,
                    'nombre': centro.nombre
                },
                'estadisticas': {
                    'total': requisiciones.count(),
                    'por_estado': por_estado
                },
                'requisiciones': requisiciones_data
            })
            
        except Exception as e:
            traceback.print_exc()
            return Response({
                'error': 'Error al obtener requisiciones',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class LoteViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar lotes.
    
    Funcionalidades:
    - CRUD completo
    - Filtrado por producto
    - Filtrado por estado de caducidad
    - Búsqueda por número de lote
    - Validaciones de integridad
    """
    queryset = Lote.objects.select_related('producto').all()
    serializer_class = LoteSerializer
    permission_classes = [IsFarmaciaAdminOrReadOnly]

    def get_queryset(self):
        """
        Filtra lotes según parámetros.
        
        Parámetros:
        - producto: ID del producto
        - activo: true/false
        - caducidad: vencido/critico/proximo/normal
        - search: búsqueda por número de lote
        """
        queryset = Lote.objects.select_related('producto').all()
        
        # Filtrar por producto
        producto = self.request.query_params.get('producto')
        if producto:
            queryset = queryset.filter(producto_id=producto)
        
        # Filtrar por estado activo
        activo = self.request.query_params.get('activo')
        if activo == 'true':
            queryset = queryset.filter(activo=True)
        elif activo == 'false':
            queryset = queryset.filter(activo=False)
        
        # Búsqueda por número de lote
        search = self.request.query_params.get('search')
        if search and search.strip():
            queryset = queryset.filter(numero_lote__icontains=search)
        
        # Filtrar por estado de caducidad
        caducidad = self.request.query_params.get('caducidad')
        if caducidad:
            from datetime import date, timedelta
            hoy = date.today()
            
            if caducidad == 'vencido':
                queryset = queryset.filter(fecha_caducidad__lt=hoy)
            elif caducidad == 'critico':
                queryset = queryset.filter(
                    fecha_caducidad__gte=hoy,
                    fecha_caducidad__lte=hoy + timedelta(days=7)
                )
            elif caducidad == 'proximo':
                queryset = queryset.filter(
                    fecha_caducidad__gt=hoy + timedelta(days=7),
                    fecha_caducidad__lte=hoy + timedelta(days=30)
                )
            elif caducidad == 'normal':
                queryset = queryset.filter(fecha_caducidad__gt=hoy + timedelta(days=30))
        
        return queryset.order_by('-created_at')
    
    def create(self, request, *args, **kwargs):
        """Crea un nuevo lote con validaciones"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            
            headers = self.get_success_headers(serializer.data)
            return Response(
                serializer.data, 
                status=status.HTTP_201_CREATED, 
                headers=headers
            )
        except serializers.ValidationError as e:
            return Response(
                {'error': 'Error de validación', 'detalles': e.detail}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            traceback.print_exc()
            return Response(
                {'error': 'Error al crear lote', 'mensaje': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, *args, **kwargs):
        """Actualiza un lote existente"""
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            
            return Response(serializer.data)
        except serializers.ValidationError as e:
            return Response(
                {'error': 'Error de validación', 'detalles': e.detail}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            traceback.print_exc()
            return Response(
                {'error': 'Error al actualizar lote', 'mensaje': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, *args, **kwargs):
        """
        Elimina un lote.
        
        Validaciones:
        - No puede eliminarse si tiene movimientos asociados
        """
        instance = self.get_object()
        
        try:
            # Verificar si tiene movimientos
            if Movimiento.objects.filter(lote=instance).exists():
                total_movimientos = Movimiento.objects.filter(lote=instance).count()
                
                return Response({
                    'error': 'No se puede eliminar el lote',
                    'razon': 'Tiene movimientos asociados',
                    'total_movimientos': total_movimientos,
                    'sugerencia': 'Marque el lote como inactivo en lugar de eliminarlo'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Si no tiene movimientos, se puede eliminar
            numero_lote = instance.numero_lote
            producto_clave = instance.producto.clave
            instance.delete()
            
            return Response({
                'mensaje': 'Lote eliminado exitosamente',
                'lote_eliminado': numero_lote,
                'producto': producto_clave
            }, status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            traceback.print_exc()
            return Response({
                'error': 'Error al eliminar lote',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def por_vencer(self, request):
        """
        Obtiene lotes próximos a vencer.
        
        Parámetros:
        - dias: número de días (default: 30)
        """
        try:
            from datetime import date, timedelta
            
            dias = int(request.query_params.get('dias', 30))
            fecha_limite = date.today() + timedelta(days=dias)
            
            lotes = Lote.objects.select_related('producto').filter(
                activo=True,
                cantidad_actual__gt=0,
                fecha_caducidad__lte=fecha_limite
            ).order_by('fecha_caducidad')
            
            serializer = self.get_serializer(lotes, many=True)
            
            return Response({
                'total': lotes.count(),
                'dias_configurados': dias,
                'fecha_limite': fecha_limite,
                'lotes': serializer.data
            })
            
        except Exception as e:
            traceback.print_exc()
            return Response({
                'error': 'Error al obtener lotes por vencer',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def historial(self, request, pk=None):
        """Obtiene el historial de movimientos de un lote"""
        try:
            lote = self.get_object()
            
            movimientos = Movimiento.objects.filter(lote=lote).select_related(
                'producto'
            ).order_by('-fecha_movimiento')
            
            from django.db.models import Sum
            
            total_entradas = movimientos.filter(tipo_movimiento='ENTRADA').aggregate(
                total=Sum('cantidad')
            )['total'] or 0
            
            total_salidas = movimientos.filter(tipo_movimiento='SALIDA').aggregate(
                total=Sum('cantidad')
            )['total'] or 0
            
            movimientos_data = []
            for mov in movimientos:
                movimientos_data.append({
                    'id': mov.id,
                    'tipo': mov.tipo_movimiento,
                    'cantidad': mov.cantidad,
                    'fecha': mov.fecha_movimiento,
                    'observaciones': mov.observaciones or ''
                })
            
            return Response({
                'lote': {
                    'id': lote.id,
                    'numero_lote': lote.numero_lote,
                    'producto': lote.producto.clave,
                    'cantidad_actual': lote.cantidad_actual
                },
                'estadisticas': {
                    'total_entradas': total_entradas,
                    'total_salidas': total_salidas,
                    'diferencia': total_entradas - total_salidas
                },
                'movimientos': movimientos_data,
                'total_movimientos': len(movimientos_data)
            })
            
        except Exception as e:
            traceback.print_exc()
            return Response({
                'error': 'Error al obtener historial',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class MovimientoViewSet(viewsets.ModelViewSet):
    queryset = Movimiento.objects.select_related('producto', 'lote').all()
    serializer_class = MovimientoSerializer
    permission_classes = [IsFarmaciaRole]

    def get_queryset(self):
        queryset = Movimiento.objects.select_related('producto', 'lote').all()
        tipo = self.request.query_params.get('tipo')
        if tipo:
            queryset = queryset.filter(tipo_movimiento=tipo)
        return queryset.order_by('-fecha_movimiento')

@method_decorator(csrf_exempt, name='dispatch')
class RequisicionViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar requisiciones.
    
    Funcionalidades:
    - CRUD completo
    - Flujo de estados (BORRADOR → ENVIADA → AUTORIZADA → SURTIDA)
    - Gestión de items
    - Filtrado por estado y centro
    - Acciones de autorización, rechazo y cancelación
    """
    queryset = Requisicion.objects.select_related('centro', 'solicitante', 'autorizado_por').prefetch_related('items').all()
    serializer_class = RequisicionSerializer
    permission_classes = [IsCentroRole]

    def get_queryset(self):
        """Filtra requisiciones según parámetros"""
        queryset = Requisicion.objects.select_related('centro', 'solicitante', 'autorizado_por').prefetch_related('items').all()
        
        # Restricción por rol
        if _has_role := getattr(self.request, 'user', None):
            if not _has_role.is_superuser and getattr(_has_role, 'rol', '') not in ['admin_sistema', 'farmacia', 'admin_farmacia', 'superusuario']:
                user_centro = getattr(_has_role, 'centro', None) or getattr(getattr(_has_role, 'profile', None), 'centro', None)
                if user_centro:
                    queryset = queryset.filter(centro=user_centro)
                else:
                    queryset = queryset.none()
        
        # Filtro por estado
        estado = self.request.query_params.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado)
        
        # Filtro por centro
        centro = self.request.query_params.get('centro')
        if centro:
            queryset = queryset.filter(centro_id=centro)
        
        # Búsqueda por folio
        search = self.request.query_params.get('search')
        if search and search.strip():
            queryset = queryset.filter(folio__icontains=search)
        
        return queryset.order_by('-created_at')
    
    def create(self, request, *args, **kwargs):
        """Crea una nueva requisición"""
        try:
            print("=" * 50)
            print("📥 CREAR REQUISICIÓN - Datos recibidos:")
            print(f"   Body: {request.data}")
            print("=" * 50)
            
            # Generar folio automático
            fecha = timezone.now()
            folio = f"REQ-{fecha.strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
            
            # Verificar que el folio sea único
            while Requisicion.objects.filter(folio=folio).exists():
                folio = f"REQ-{fecha.strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
            
            # Preparar datos
            data = request.data.copy()
            data['folio'] = folio
            data['estado'] = 'enviada'
            
            # Ajustar usuario y centro solicitante por rol
            solicitante = request.user if request.user.is_authenticated else None
            if solicitante:
                data['usuario_solicita'] = getattr(solicitante, 'id', None)
                user_centro = getattr(solicitante, 'centro', None) or getattr(getattr(solicitante, 'profile', None), 'centro', None)
                if user_centro:
                    data['centro'] = user_centro.id
            if not data.get('usuario_solicita'):
                return Response({'error': 'Solicitante requerido'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Crear requisición
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            requisicion = serializer.save()
            
            # Crear items
            items_data = request.data.get('items', [])
            items_creados = 0
            
            for item_data in items_data:
                if not item_data.get('producto') or not item_data.get('cantidad_solicitada'):
                    continue
                
                DetalleRequisicion.objects.create(
                    requisicion=requisicion,
                    producto_id=item_data['producto'],
                    cantidad_solicitada=item_data['cantidad_solicitada'],
                    observaciones=item_data.get('observaciones', '')
                )
                items_creados += 1
            
            print(f"✅ Requisición creada: {requisicion.folio} con {items_creados} items")
            
            return Response({
                'mensaje': 'Requisición creada exitosamente',
                'requisicion': RequisicionSerializer(requisicion).data,
                'items_creados': items_creados
            }, status=status.HTTP_201_CREATED)
            
        except serializers.ValidationError as e:
            print(f"❌ Error de validación: {e.detail}")
            return Response({
                'error': 'Error de validación',
                'detalles': e.detail
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            print(f"❌ Error inesperado: {str(e)}")
            traceback.print_exc()
            return Response({
                'error': 'Error al crear requisición',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def update(self, request, *args, **kwargs):
        """Actualiza una requisición (solo si está en BORRADOR)"""
        try:
            requisicion = self.get_object()
            
            if requisicion.estado != 'BORRADOR':
                return Response({
                    'error': 'Solo se pueden editar requisiciones en estado BORRADOR',
                    'estado_actual': requisicion.estado
                }, status=status.HTTP_400_BAD_REQUEST)
            
            partial = kwargs.pop('partial', False)
            serializer = self.get_serializer(requisicion, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            requisicion = serializer.save()
            
            # Actualizar items si se proporcionaron
            items_data = request.data.get('items')
            if items_data is not None:
                # Eliminar items actuales
                requisicion.items.all().delete()
                
                # Crear nuevos items
                for item_data in items_data:
                    if not item_data.get('producto') or not item_data.get('cantidad_solicitada'):
                        continue
                    
                    DetalleRequisicion.objects.create(
                        requisicion=requisicion,
                        producto_id=item_data['producto'],
                        cantidad_solicitada=item_data['cantidad_solicitada'],
                        observaciones=item_data.get('observaciones', '')
                    )
            
            return Response({
                'mensaje': 'Requisición actualizada exitosamente',
                'requisicion': RequisicionSerializer(requisicion).data
            })
            
        except Exception as e:
            traceback.print_exc()
            return Response({
                'error': 'Error al actualizar requisición',
                'mensaje': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, *args, **kwargs):
        """Elimina una requisición (solo si está en BORRADOR)"""
        requisicion = self.get_object()
        
        try:
            if requisicion.estado != 'BORRADOR':
                return Response({
                    'error': 'Solo se pueden eliminar requisiciones en estado BORRADOR',
                    'estado_actual': requisicion.estado,
                    'sugerencia': 'Use la acción de cancelar en su lugar'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            folio = requisicion.folio
            requisicion.delete()
            
            return Response({
                'mensaje': 'Requisición eliminada exitosamente',
                'folio_eliminado': folio
            }, status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            traceback.print_exc()
            return Response({
                'error': 'Error al eliminar requisición',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def enviar(self, request, pk=None):
        """Envía una requisición (BORRADOR → ENVIADA)"""
        try:
            requisicion = self.get_object()
            
            if requisicion.estado != 'BORRADOR':
                return Response({
                    'error': 'Solo se pueden enviar requisiciones en estado BORRADOR',
                    'estado_actual': requisicion.estado
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not requisicion.items.exists():
                return Response({
                    'error': 'La requisición debe tener al menos un producto'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            requisicion.estado = 'ENVIADA'
            requisicion.save()
            
            print(f"✅ Requisición enviada: {requisicion.folio}")
            
            return Response({
                'mensaje': 'Requisición enviada exitosamente',
                'requisicion': RequisicionSerializer(requisicion).data
            })
            
        except Exception as e:
            traceback.print_exc()
            return Response({
                'error': 'Error al enviar requisición',
                'mensaje': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def autorizar(self, request, pk=None):
        """Autoriza una requisición (ENVIADA → AUTORIZADA)"""
        try:
            requisicion = self.get_object()
            
            if requisicion.estado != 'ENVIADA':
                return Response({
                    'error': 'Solo se pueden autorizar requisiciones en estado ENVIADA',
                    'estado_actual': requisicion.estado
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Obtener usuario que autoriza
            from django.contrib.auth import get_user_model
            User = get_user_model()
            autorizado_por = User.objects.first()  # En producción: request.user
            
            requisicion.estado = 'AUTORIZADA'
            requisicion.fecha_autorizacion = timezone.now()
            requisicion.autorizado_por = autorizado_por
            requisicion.save()
            
            # Actualizar cantidades autorizadas de items
            items_data = request.data.get('items', [])
            for item_data in items_data:
                item_id = item_data.get('id')
                cantidad_autorizada = item_data.get('cantidad_autorizada')
                
                if item_id and cantidad_autorizada is not None:
                    try:
                        item = requisicion.items.get(id=item_id)
                        item.cantidad_autorizada = cantidad_autorizada
                        item.save()
                    except DetalleRequisicion.DoesNotExist:
                        continue
            
            print(f"✅ Requisición autorizada: {requisicion.folio}")
            
            return Response({
                'mensaje': 'Requisición autorizada exitosamente',
                'requisicion': RequisicionSerializer(requisicion).data
            })
            
        except Exception as e:
            traceback.print_exc()
            return Response({
                'error': 'Error al autorizar requisición',
                'mensaje': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def rechazar(self, request, pk=None):
        """Rechaza una requisición (ENVIADA → RECHAZADA)"""
        try:
            requisicion = self.get_object()
            
            if requisicion.estado != 'ENVIADA':
                return Response({
                    'error': 'Solo se pueden rechazar requisiciones en estado ENVIADA',
                    'estado_actual': requisicion.estado
                }, status=status.HTTP_400_BAD_REQUEST)
            
            motivo = request.data.get('observaciones', '')
            if not motivo.strip():
                return Response({
                    'error': 'Debe proporcionar un motivo de rechazo'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            requisicion.estado = 'RECHAZADA'
            requisicion.observaciones = motivo
            requisicion.save()
            
            print(f"✅ Requisición rechazada: {requisicion.folio}")
            
            return Response({
                'mensaje': 'Requisición rechazada',
                'requisicion': RequisicionSerializer(requisicion).data
            })
            
        except Exception as e:
            traceback.print_exc()
            return Response({
                'error': 'Error al rechazar requisición',
                'mensaje': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        """Cancela una requisición"""
        try:
            requisicion = self.get_object()
            
            if requisicion.estado in ['SURTIDA', 'CANCELADA']:
                return Response({
                    'error': f'No se puede cancelar una requisición en estado {requisicion.estado}',
                    'estado_actual': requisicion.estado
                }, status=status.HTTP_400_BAD_REQUEST)
            
            motivo = request.data.get('observaciones', '')
            
            requisicion.estado = 'CANCELADA'
            if motivo:
                requisicion.observaciones = motivo
            requisicion.save()
            
            print(f"✅ Requisición cancelada: {requisicion.folio}")
            
            return Response({
                'mensaje': 'Requisición cancelada exitosamente',
                'requisicion': RequisicionSerializer(requisicion).data
            })
            
        except Exception as e:
            traceback.print_exc()
            return Response({
                'error': 'Error al cancelar requisición',
                'mensaje': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """Obtiene estadísticas de requisiciones"""
        try:
            total = Requisicion.objects.count()
            
            por_estado = {}
            for estado, _ in Requisicion.ESTADO_CHOICES:
                count = Requisicion.objects.filter(estado=estado).count()
                por_estado[estado] = count
            
            por_centro = []
            centros = Centro.objects.annotate(
                total_requisiciones=Count('requisiciones')
            ).filter(total_requisiciones__gt=0).order_by('-total_requisiciones')[:10]
            
            for centro in centros:
                por_centro.append({
                    'centro': centro.nombre,
                    'total': centro.total_requisiciones
                })
            
            return Response({
                'total': total,
                'por_estado': por_estado,
                'top_centros': por_centro
            })
            
        except Exception as e:
            traceback.print_exc()
            return Response({
                'error': 'Error al obtener estadísticas',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_resumen(request):
    try:
        total_productos = Producto.objects.filter(activo=True).count()
        lotes_disponibles = Lote.objects.filter(
            estado='disponible',
            deleted_at__isnull=True
        )
        stock_total = lotes_disponibles.aggregate(
            total=Sum('cantidad_actual')
        )['total'] or 0
        lotes_activos = lotes_disponibles.filter(
            cantidad_actual__gt=0
        ).count()
        movimiento_fields = {field.name for field in Movimiento._meta.get_fields()}
        fecha_field = 'fecha_movimiento' if 'fecha_movimiento' in movimiento_fields else 'fecha'
        tipo_field = 'tipo_movimiento' if 'tipo_movimiento' in movimiento_fields else 'tipo'
        inicio_mes = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        movimientos_queryset = Movimiento.objects.all()
        if 'activo' in movimiento_fields:
            movimientos_queryset = movimientos_queryset.filter(activo=True)
        if 'deleted_at' in movimiento_fields:
            movimientos_queryset = movimientos_queryset.filter(deleted_at__isnull=True)
        movimientos_mes = movimientos_queryset.filter(
            **{f"{fecha_field}__gte": inicio_mes}
        ).count()
        
        ultimos_movimientos = movimientos_queryset.select_related('producto', 'lote').order_by(f'-{fecha_field}')[:10]
        
        movimientos_data = []
        for mov in ultimos_movimientos:
            producto_rel = getattr(mov, 'producto', None)
            lote_rel = getattr(mov, 'lote', None)
            if producto_rel is None or lote_rel is None:
                continue
            fecha_valor = getattr(mov, fecha_field, None)
            movimientos_data.append({
                'id': mov.id,
                'tipo_movimiento': getattr(mov, tipo_field, ''),
                'producto__descripcion': getattr(producto_rel, 'descripcion', 'N/A'),
                'producto__clave': getattr(producto_rel, 'clave', 'N/A'),
                'lote__codigo_lote': getattr(lote_rel, 'numero_lote', 'N/A'),
                'cantidad': mov.cantidad,
                'fecha_movimiento': fecha_valor.isoformat() if fecha_valor else None,
                'observaciones': getattr(mov, 'observaciones', '') or ''
            })
        
        return Response({
            'kpi': {
                'total_productos': total_productos,
                'stock_total': stock_total,
                'lotes_activos': lotes_activos,
                'movimientos_mes': movimientos_mes
            },
            'ultimos_movimientos': movimientos_data
        })
    except Exception as e:
        traceback.print_exc()
        return Response({
            'kpi': {'total_productos': 0, 'stock_total': 0, 'lotes_activos': 0, 'movimientos_mes': 0},
            'ultimos_movimientos': []
        }, status=status.HTTP_200_OK)

@api_view(['GET'])
def trazabilidad_producto(request, clave):
    """
    Trazabilidad completa de un producto por su clave.
    """
    try:
        print("=" * 50)
        print(f"🔍 TRAZABILIDAD PRODUCTO: {clave}")
        print("=" * 50)
        
        # Buscar producto (case-insensitive)
        producto = Producto.objects.filter(clave__iexact=clave).first()
        
        if not producto:
            return Response({
                'error': 'Producto no encontrado',
                'clave_buscada': clave
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Obtener lotes del producto
        lotes = Lote.objects.filter(producto=producto).order_by('-created_at')
        
        lotes_data = []
        for lote in lotes:
            # Calcular días para caducar
            from datetime import date
            dias_caducidad = (lote.fecha_caducidad - date.today()).days if lote.fecha_caducidad else None
            
            # Estado de caducidad
            if dias_caducidad is None:
                estado_caducidad = 'DESCONOCIDO'
            elif dias_caducidad < 0:
                estado_caducidad = 'VENCIDO'
            elif dias_caducidad <= 7:
                estado_caducidad = 'CRITICO'
            elif dias_caducidad <= 30:
                estado_caducidad = 'PROXIMO'
            else:
                estado_caducidad = 'NORMAL'
            
            # Movimientos del lote
            movimientos_lote = Movimiento.objects.filter(lote=lote)
            total_entradas = movimientos_lote.filter(tipo_movimiento='ENTRADA').aggregate(total=Sum('cantidad'))['total'] or 0
            total_salidas = movimientos_lote.filter(tipo_movimiento='SALIDA').aggregate(total=Sum('cantidad'))['total'] or 0
            
            lotes_data.append({
                'id': lote.id,
                'numero_lote': lote.numero_lote,
                'fecha_caducidad': lote.fecha_caducidad.isoformat() if lote.fecha_caducidad else None,
                'dias_para_caducar': dias_caducidad,
                'estado_caducidad': estado_caducidad,
                'cantidad_actual': lote.cantidad_actual,
                'cantidad_inicial': total_entradas,
                'total_entradas': total_entradas,
                'total_salidas': total_salidas,
                'proveedor': lote.proveedor or 'N/A',
                'precio_compra': str(lote.precio_compra) if lote.precio_compra else None,
                'activo': lote.activo,
                'created_at': lote.created_at.isoformat()
            })
        
        # Movimientos del producto (últimos 100)
        movimientos = Movimiento.objects.filter(
            producto=producto
        ).select_related('lote', 'producto').order_by('-fecha_movimiento')[:100]
        
        movimientos_data = []
        for mov in movimientos:
            movimientos_data.append({
                'id': mov.id,
                'tipo_movimiento': mov.tipo_movimiento,
                'tipo': mov.tipo_movimiento,  # Alias para compatibilidad
                'lote': mov.lote.numero_lote if mov.lote else 'N/A',
                'cantidad': mov.cantidad,
                'fecha_movimiento': mov.fecha_movimiento.isoformat(),
                'observaciones': mov.observaciones or ''
            })
        
        # Estadísticas generales
        stock_total = lotes.filter(activo=True).aggregate(total=Sum('cantidad_actual'))['total'] or 0
        lotes_activos = lotes.filter(activo=True, cantidad_actual__gt=0).count()
        total_lotes = lotes.count()
        
        total_entradas = Movimiento.objects.filter(
            producto=producto, 
            tipo_movimiento='ENTRADA'
        ).aggregate(total=Sum('cantidad'))['total'] or 0
        
        total_salidas = Movimiento.objects.filter(
            producto=producto, 
            tipo_movimiento='SALIDA'
        ).aggregate(total=Sum('cantidad'))['total'] or 0
        
        # Lotes próximos a vencer
        from datetime import date, timedelta
        fecha_limite = date.today() + timedelta(days=30)
        lotes_proximos_vencer = lotes.filter(
            activo=True,
            cantidad_actual__gt=0,
            fecha_caducidad__lte=fecha_limite,
            fecha_caducidad__gte=date.today()
        ).count()
        
        # Lotes vencidos
        lotes_vencidos = lotes.filter(
            activo=True,
            cantidad_actual__gt=0,
            fecha_caducidad__lt=date.today()
        ).count()
        
        # Alertas
        alertas = []
        if stock_total < producto.stock_minimo:
            alertas.append({
                'tipo': 'STOCK_BAJO',
                'mensaje': f'Stock actual ({stock_total}) por debajo del mínimo ({producto.stock_minimo})',
                'nivel': 'CRITICO'
            })
        
        if lotes_vencidos > 0:
            alertas.append({
                'tipo': 'LOTES_VENCIDOS',
                'mensaje': f'{lotes_vencidos} lote(s) vencido(s) con stock',
                'nivel': 'CRITICO'
            })
        
        if lotes_proximos_vencer > 0:
            alertas.append({
                'tipo': 'PROXIMOS_VENCER',
                'mensaje': f'{lotes_proximos_vencer} lote(s) próximo(s) a vencer (30 días)',
                'nivel': 'ADVERTENCIA'
            })
        
        print(f"✅ Trazabilidad generada para {producto.clave}")
        print(f"   Movimientos encontrados: {len(movimientos_data)}")
        
        return Response({
            'producto': {
                'id': producto.id,
                'clave': producto.clave,
                'descripcion': producto.descripcion,
                'unidad_medida': producto.unidad_medida,
                'stock_minimo': producto.stock_minimo,
                'precio_unitario': str(producto.precio_unitario) if producto.precio_unitario else None,
                'activo': producto.activo
            },
            'estadisticas': {
                'stock_total': stock_total,
                'total_lotes': total_lotes,
                'lotes_activos': lotes_activos,
                'total_entradas': total_entradas,
                'total_salidas': total_salidas,
                'diferencia': total_entradas - total_salidas,
                'lotes_proximos_vencer': lotes_proximos_vencer,
                'lotes_vencidos': lotes_vencidos,
                'bajo_minimo': stock_total < producto.stock_minimo
            },
            'lotes': lotes_data,
            'movimientos': movimientos_data,
            'total_movimientos': Movimiento.objects.filter(producto=producto).count(),
            'alertas': alertas
        })
        
    except Exception as e:
        print(f"❌ Error en trazabilidad producto: {str(e)}")
        traceback.print_exc()
        return Response({
            'error': 'Error al obtener trazabilidad del producto',
            'mensaje': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def trazabilidad_lote(request, codigo):
    """
    Trazabilidad completa de un lote por su código.
    
    Retorna:
    - Información del lote y producto
    - Estadísticas de movimientos
    - Historial completo con saldos
    - Estado de caducidad
    """
    try:
        print("=" * 50)
        print(f"🔍 TRAZABILIDAD LOTE: {codigo}")
        print("=" * 50)
        
        # Buscar lote (case-insensitive)
        lote = Lote.objects.select_related('producto').filter(
            numero_lote__iexact=codigo
        ).first()
        
        if not lote:
            return Response({
                'error': 'Lote no encontrado',
                'codigo_buscado': codigo
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Movimientos del lote ordenados cronológicamente
        movimientos = Movimiento.objects.filter(
            lote=lote
        ).select_related('producto').order_by('fecha_movimiento')
        
        # Construir historial con saldos
        historial = []
        saldo = 0
        
        for mov in movimientos:
            if mov.tipo_movimiento == 'ENTRADA':
                saldo += mov.cantidad
            else:
                saldo -= mov.cantidad
            
            historial.append({
                'id': mov.id,
                'fecha': mov.fecha_movimiento.isoformat(),
                'tipo': mov.tipo_movimiento,
                'cantidad': mov.cantidad,
                'saldo': saldo,
                'observaciones': mov.observaciones or ''
            })
        
        # Estadísticas
        total_entradas = movimientos.filter(tipo_movimiento='ENTRADA').aggregate(
            total=Sum('cantidad')
        )['total'] or 0
        
        total_salidas = movimientos.filter(tipo_movimiento='SALIDA').aggregate(
            total=Sum('cantidad')
        )['total'] or 0
        
        # Calcular días para caducar
        from datetime import date
        dias_caducidad = (lote.fecha_caducidad - date.today()).days if lote.fecha_caducidad else None
        
        # Estado de caducidad
        if dias_caducidad is None:
            estado_caducidad = 'DESCONOCIDO'
        elif dias_caducidad < 0:
            estado_caducidad = 'VENCIDO'
        elif dias_caducidad <= 7:
            estado_caducidad = 'CRITICO'
        elif dias_caducidad <= 30:
            estado_caducidad = 'PROXIMO'
        else:
            estado_caducidad = 'NORMAL'
        
        # Alertas
        alertas = []
        if dias_caducidad is not None:
            if dias_caducidad < 0:
                alertas.append({
                    'tipo': 'VENCIDO',
                    'mensaje': f'Este lote está vencido desde hace {abs(dias_caducidad)} días',
                    'nivel': 'CRITICO'
                })
            elif dias_caducidad <= 7:
                alertas.append({
                    'tipo': 'CRITICO',
                    'mensaje': f'Este lote caduca en {dias_caducidad} días',
                    'nivel': 'CRITICO'
                })
            elif dias_caducidad <= 30:
                alertas.append({
                    'tipo': 'PROXIMO',
                    'mensaje': f'Este lote caduca en {dias_caducidad} días',
                    'nivel': 'ADVERTENCIA'
                })
        
        if saldo != lote.cantidad_actual:
            alertas.append({
                'tipo': 'INCONSISTENCIA',
                'mensaje': f'Inconsistencia: Saldo calculado ({saldo}) difiere del stock actual ({lote.cantidad_actual})',
                'nivel': 'ADVERTENCIA'
            })
        
        print(f"✅ Trazabilidad generada para lote {lote.numero_lote}")
        
        return Response({
            'lote': {
                'id': lote.id,
                'numero_lote': lote.numero_lote,
                'fecha_caducidad': lote.fecha_caducidad.isoformat() if lote.fecha_caducidad else None,
                'dias_para_caducar': dias_caducidad,
                'estado_caducidad': estado_caducidad,
                'cantidad_actual': lote.cantidad_actual,
                'precio_compra': str(lote.precio_compra) if lote.precio_compra else None,
                'proveedor': lote.proveedor or 'N/A',
                'activo': lote.activo,
                'created_at': lote.created_at.isoformat()
            },
            'producto': {
                'id': lote.producto.id,
                'clave': lote.producto.clave,
                'descripcion': lote.producto.descripcion,
                'unidad_medida': lote.producto.unidad_medida
            },
            'estadisticas': {
                'cantidad_inicial': total_entradas,
                'total_entradas': total_entradas,
                'total_salidas': total_salidas,
                'cantidad_actual': lote.cantidad_actual,
                'saldo_calculado': saldo,
                'diferencia': total_entradas - total_salidas,
                'consistente': saldo == lote.cantidad_actual
            },
            'historial': historial,
            'total_movimientos': movimientos.count(),
            'alertas': alertas
        })
        
    except Exception as e:
        print(f"❌ Error en trazabilidad lote: {str(e)}")
        traceback.print_exc()
        return Response({
            'error': 'Error al obtener trazabilidad del lote',
            'mensaje': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def reporte_inventario(request):
    """
    Genera reporte de inventario actual en PDF.
    
    Incluye:
    - Listado completo de productos activos
    - Stock actual por producto
    - Lotes activos
    - Productos con stock bajo mínimo destacados
    """
    try:
        print("=" * 50)
        print("📄 GENERANDO REPORTE DE INVENTARIO PDF")
        print("=" * 50)
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Título
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#632842'),
            spaceAfter=30,
            alignment=1
        )
        title = Paragraph("REPORTE DE INVENTARIO ACTUAL", title_style)
        elements.append(title)
        
        # Fecha y hora
        fecha_style = ParagraphStyle(
            'FechaStyle',
            parent=styles['Normal'],
            fontSize=10,
            alignment=1,
            spaceAfter=20
        )
        fecha = Paragraph(
            f"Generado el {timezone.now().strftime('%d/%m/%Y %H:%M:%S')}",
            fecha_style
        )
        elements.append(fecha)
        elements.append(Spacer(1, 0.3*inch))
        
        # Datos del reporte
        productos = Producto.objects.filter(activo=True).order_by('clave')
        
        data = [['#', 'Clave', 'Descripción', 'Stock', 'Lotes']]
        
        total_productos = 0
        
        data = [['#', 'Clave', 'Descripción', 'Stock', 'Lotes']]
        
        total_productos = 0
        total_stock = 0
        productos_bajo_minimo = 0
        
        for idx, producto in enumerate(productos, 1):
            stock_total = producto.lotes.filter(estado='disponible').aggregate(
                total=Sum('cantidad_actual')
            )['total'] or 0
            
            lotes_activos = producto.lotes.filter(
                estado='disponible', 
                cantidad_actual__gt=0
            ).count()
            
            data.append([
                str(idx),
                producto.clave,
                producto.descripcion[:50] + '...' if len(producto.descripcion) > 50 else producto.descripcion,
                str(stock_total),
                str(lotes_activos)
            ])
            
            total_productos += 1
            total_stock += stock_total
            
            if stock_total < producto.stock_minimo:
                productos_bajo_minimo += 1
        
        # Crear tabla
        table = Table(data, colWidths=[0.5*inch, 1.2*inch, 3.5*inch, 1*inch, 1*inch])
        table.setStyle(TableStyle([
            # Encabezado
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#632842')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            # Contenido
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.beige]),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Resumen
        resumen_data = [
            ['Total de Productos:', str(total_productos)],
            ['Stock Total:', str(total_stock)],
            ['Productos Bajo Mínimo:', str(productos_bajo_minimo)]
        ]
        
        resumen_table = Table(resumen_data, colWidths=[3*inch, 2*inch])
        resumen_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F0F0F0')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(resumen_table)
        
        # Construir PDF
        doc.build(elements)
        
        buffer.seek(0)
        response = HttpResponse(buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename=Inventario_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        
        print(f"✅ Reporte PDF generado: {total_productos} productos")
        
        return response
        
    except Exception as e:
        print(f"❌ Error generando reporte: {str(e)}")
        traceback.print_exc()
        return Response({
            'error': 'Error al generar reporte',
            'mensaje': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def reporte_movimientos(request):
    """
    Genera reporte de movimientos con filtros.
    
    Parámetros:
    - fecha_inicio: Fecha inicial (YYYY-MM-DD)
    - fecha_fin: Fecha final (YYYY-MM-DD)
    - tipo: ENTRADA o SALIDA
    - formato: excel o pdf
    """
    try:
        print("=" * 50)
        print("📊 GENERANDO REPORTE DE MOVIMIENTOS")
        print(f"   Parámetros: {dict(request.query_params)}")
        print("=" * 50)
        
        # Obtener parámetros
        fecha_inicio = request.query_params.get('fecha_inicio')
        fecha_fin = request.query_params.get('fecha_fin')
        tipo = request.query_params.get('tipo')
        formato = request.query_params.get('formato', 'excel')
        
        # Filtrar movimientos
        movimientos = Movimiento.objects.select_related('producto', 'lote').all()
        
        if fecha_inicio:
            movimientos = movimientos.filter(fecha_movimiento__gte=fecha_inicio)
        if fecha_fin:
            movimientos = movimientos.filter(fecha_movimiento__lte=fecha_fin)
        if tipo and tipo in ['ENTRADA', 'SALIDA']:
            movimientos = movimientos.filter(tipo_movimiento=tipo)
        
        movimientos = movimientos.order_by('-fecha_movimiento')
        
        if formato == 'excel':
            # Generar Excel
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = 'Movimientos'
            
            # Título
            ws.merge_cells('A1:G1')
            titulo_cell = ws['A1']
            titulo_cell.value = 'REPORTE DE MOVIMIENTOS'
            titulo_cell.font = Font(bold=True, size=14, color='632842')
            titulo_cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Filtros aplicados
            filtros_text = []
            if fecha_inicio:
                filtros_text.append(f'Desde: {fecha_inicio}')
            if fecha_fin:
                filtros_text.append(f'Hasta: {fecha_fin}')
            if tipo:
                filtros_text.append(f'Tipo: {tipo}')
            
            ws.merge_cells('A2:G2')
            filtros_cell = ws['A2']
            filtros_cell.value = ' | '.join(filtros_text) if filtros_text else 'Sin filtros'
            filtros_cell.font = Font(size=10, italic=True)
            filtros_cell.alignment = Alignment(horizontal='center')
            
            ws.append([])  # Línea en blanco
            
            # Encabezados
            headers = ['#', 'Fecha', 'Tipo', 'Producto', 'Lote', 'Cantidad', 'Observaciones']
            ws.append(headers)
            
            # Estilo encabezados
            header_fill = PatternFill(start_color='632842', end_color='632842', fill_type='solid')
            header_font = Font(bold=True, color='FFFFFF', size=11)
            
            for cell in ws[4]:  # Fila 4 tiene los encabezados
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Datos
            total_entradas = 0
            total_salidas = 0
            
            for idx, mov in enumerate(movimientos, 1):
                ws.append([
                    idx,
                    mov.fecha_movimiento.strftime('%d/%m/%Y %H:%M'),
                    mov.tipo_movimiento,
                    f"{mov.producto.clave} - {mov.producto.descripcion[:40]}",
                    mov.lote.numero_lote if mov.lote else 'N/A',
                    mov.cantidad,
                    mov.observaciones or ''
                ])
                
                if mov.tipo_movimiento == 'ENTRADA':
                    total_entradas += mov.cantidad
                else:
                    total_salidas += mov.cantidad
                
                # Colorear por tipo
                row_num = idx + 4
                tipo_cell = ws.cell(row=row_num, column=3)
                if mov.tipo_movimiento == 'ENTRADA':
                    tipo_cell.fill = PatternFill(start_color='D4EDDA', end_color='D4EDDA', fill_type='solid')
                    tipo_cell.font = Font(color='155724', bold=True)
                else:
                    tipo_cell.fill = PatternFill(start_color='F8D7DA', end_color='F8D7DA', fill_type='solid')
                    tipo_cell.font = Font(color='721C24', bold=True)
            
            # Resumen
            ws.append([])
            resumen_row = ws.max_row + 1
            ws[f'D{resumen_row}'] = 'TOTAL ENTRADAS:'
            ws[f'D{resumen_row}'].font = Font(bold=True)
            ws[f'F{resumen_row}'] = total_entradas
            ws[f'F{resumen_row}'].font = Font(bold=True, color='155724')
            
            ws[f'D{resumen_row + 1}'] = 'TOTAL SALIDAS:'
            ws[f'D{resumen_row + 1}'].font = Font(bold=True)
            ws[f'F{resumen_row + 1}'] = total_salidas
            ws[f'F{resumen_row + 1}'].font = Font(bold=True, color='721C24');
            
            ws[f'D{resumen_row + 2}'] = 'DIFERENCIA:'
            ws[f'D{resumen_row + 2}'].font = Font(bold=True)
            ws[f'F{resumen_row + 2}'] = total_entradas - total_salidas
            ws[f'F{resumen_row + 2}'].font = Font(bold=True)
            
            # Ajustar anchos
            ws.column_dimensions['A'].width = 8
            ws.column_dimensions['B'].width = 18
            ws.column_dimensions['C'].width = 12
            ws.column_dimensions['D'].width = 50
            ws.column_dimensions['E'].width = 20
            ws.column_dimensions['F'].width = 12
            ws.column_dimensions['G'].width = 30
            
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename=Movimientos_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            wb.save(response)
            
            print(f"✅ Reporte Excel generado: {movimientos.count()} movimientos")
            
            return response
            
        else:
            return Response({
                'error': 'Formato no soportado',
                'formatos_disponibles': ['excel']
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        print(f"❌ Error generando reporte: {str(e)}")
        traceback.print_exc()
        return Response({
            'error': 'Error al generar reporte de movimientos',
            'mensaje': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def reporte_caducidades(request):
    """
    Genera reporte de lotes próximos a caducar en Excel.
    
    Parámetros:
    - dias: Número de días de anticipación (default: 30)
    """
    try:
        print("=" * 50)
        print("⚠️ GENERANDO REPORTE DE CADUCIDADES")
        print("=" * 50)
        
        dias = int(request.query_params.get('dias', 30))
        
        from datetime import date, timedelta
        fecha_limite = date.today() + timedelta(days=dias)
        
        # Obtener lotes próximos a vencer
        lotes = Lote.objects.filter(
            activo=True,
            cantidad_actual__gt=0,
            fecha_caducidad__lte=fecha_limite
        ).select_related('producto').order_by('fecha_caducidad')
        
        # Generar Excel
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Caducidades'
        
        # Título
        ws.merge_cells('A1:G1')
        titulo_cell = ws['A1']
        titulo_cell.value = f'REPORTE DE LOTES PRÓXIMOS A CADUCAR ({dias} DÍAS)'
        titulo_cell.font = Font(bold=True, size=14, color='632842')
        titulo_cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Fecha generación
        ws.merge_cells('A2:G2')
        fecha_cell = ws['A2']
        fecha_cell.value = f'Generado el {timezone.now().strftime("%d/%m/%Y %H:%M")}'
        fecha_cell.font = Font(size=10, italic=True)
        fecha_cell.alignment = Alignment(horizontal='center')
        
        ws.append([])  # Línea en blanco
        
        # Encabezados
        headers = ['#', 'Producto', 'Lote', 'Caducidad', 'Días Restantes', 'Stock', 'Estado']
        ws.append(headers)
        
        # Estilo encabezados
        header_fill = PatternFill(start_color='632842', end_color='632842', fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF', size=11)
        
        for cell in ws[4]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Datos
        vencidos = 0
        criticos = 0
        proximos = 0
        
        for idx, lote in enumerate(lotes, 1):
            dias_restantes = (lote.fecha_caducidad - date.today()).days
            
            if dias_restantes < 0:
                estado = 'VENCIDO'
                vencidos += 1
            elif dias_restantes <= 7:
                estado = 'CRÍTICO'
                criticos += 1
            else:
                estado = 'PRÓXIMO'
                proximos += 1
            
            ws.append([
                idx,
                f"{lote.producto.clave} - {lote.producto.descripcion[:40]}",
                lote.numero_lote,
                lote.fecha_caducidad.strftime('%d/%m/%Y'),
                dias_restantes,
                lote.cantidad_actual,
                estado
            ])
            
            # Colorear según estado
            row_num = idx + 4
            estado_cell = ws.cell(row=row_num, column=7)
            
            if dias_restantes < 0:
                estado_cell.fill = PatternFill(start_color='FF0000', end_color='FF0000', fill_type='solid')
                estado_cell.font = Font(color='FFFFFF', bold=True)
            elif dias_restantes <= 7:
                estado_cell.fill = PatternFill(start_color='FFA500', end_color='FFA500', fill_type='solid')
                estado_cell.font = Font(color='FFFFFF', bold=True)
            else:
                estado_cell.fill = PatternFill(start_color='FFFF00', end_color='FFFF00', fill_type='solid')
                estado_cell.font = Font(bold=True)
        
        # Resumen
        ws.append([])
        resumen_row = ws.max_row + 1
        ws[f'B{resumen_row}'] = 'RESUMEN:'
        ws[f'B{resumen_row}'].font = Font(bold=True, size=12)
        
        ws[f'B{resumen_row + 1}'] = 'Vencidos:'
        ws[f'C{resumen_row + 1}'] = vencidos
        ws[f'C{resumen_row + 1}'].fill = PatternFill(start_color='FF0000', end_color='FF0000', fill_type='solid')
        ws[f'C{resumen_row + 1}'].font = Font(color='FFFFFF', bold=True)
        
        ws[f'B{resumen_row + 2}'] = 'Críticos (≤7 días):'
        ws[f'C{resumen_row + 2}'] = criticos
        ws[f'C{resumen_row + 2}'].fill = PatternFill(start_color='FFA500', end_color='FFA500', fill_type='solid')
        ws[f'C{resumen_row + 2}'].font = Font(color='FFFFFF', bold=True)
        
        ws[f'B{resumen_row + 3}'] = f'Próximos (≤{dias} días):'
        ws[f'C{resumen_row + 3}'] = proximos
        ws[f'C{resumen_row + 3}'].fill = PatternFill(start_color='FFFF00', end_color='FFFF00', fill_type='solid')
        ws[f'C{resumen_row + 3}'].font = Font(bold=True)
        
        # Ajustar anchos
        ws.column_dimensions['A'].width = 8
        ws.column_dimensions['B'].width = 50
        ws.column_dimensions['C'].width = 20
        ws.column_dimensions['D'].width = 15
        ws.column_dimensions['E'].width = 15
        ws.column_dimensions['F'].width = 12
        ws.column_dimensions['G'].width = 12
        
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename=Caducidades_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        wb.save(response)
        
        print(f"✅ Reporte de caducidades generado: {lotes.count()} lotes")
        
        return response
        
    except Exception as e:
        print(f"❌ Error generando reporte: {str(e)}")
        traceback.print_exc()
        return Response({
            'error': 'Error al generar reporte de caducidades',
            'mensaje': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def reportes_precarga(request):
    """
    Obtiene datos para precargar formularios de reportes.
    
    Retorna:
    - Lista de productos activos
    - Lista de centros activos
    - Tipos de movimiento disponibles
    """
    try:
        productos = Producto.objects.filter(activo=True).values(
            'id', 'clave', 'descripcion'
        ).order_by('clave')
        
        centros = Centro.objects.filter(activo=True).values(
            'id', 'clave', 'nombre'
        ).order_by('clave')
        
        return Response({
            'productos': list(productos),
            'centros': list(centros),
            'tipos_movimiento': ['ENTRADA', 'SALIDA']
        })
        
    except Exception as e:
        traceback.print_exc()
        return Response({
            'error': 'Error al obtener datos de precarga',
            'mensaje': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
