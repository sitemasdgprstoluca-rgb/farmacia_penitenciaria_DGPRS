# -*- coding: utf-8 -*-
"""
ViewSet de Productos.

Gestión completa de productos farmacéuticos incluyendo:
- CRUD de productos
- Importación/exportación Excel
- Auditoría de cambios
- Toggle de estado activo/inactivo
"""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Q, Sum, F
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.utils import timezone
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
import logging

from core.models import Producto
from core.serializers import ProductoSerializer
from core.constants import UNIDADES_MEDIDA
from .base import (
    CustomPagination,
    is_farmacia_or_admin,
    get_user_centro,
    validar_archivo_excel,
    cargar_workbook_seguro,
    validar_filas_excel,
)

logger = logging.getLogger(__name__)


class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get_permissions(self):
        """
        Permisos personalizados por acción:
        - list, retrieve: IsAuthenticated
        - create, update, destroy, toggle_activo, importar_excel, exportar_excel, auditoria: IsFarmaciaRole
        """
        acciones_farmacia = [
            'create', 'update', 'partial_update', 'destroy', 
            'toggle_activo', 'importar_excel', 'exportar_excel', 'auditoria'
        ]
        if self.action in acciones_farmacia:
            from core.permissions import IsFarmaciaRole
            return [IsAuthenticated(), IsFarmaciaRole()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = Producto.objects.all()
        user = self.request.user
        
        # ISS-FIX: Determinar el centro para filtrar stock
        # Usuarios CENTRO solo ven productos con stock en SU centro (lo que farmacia les ha surtido)
        # Admin/Farmacia/Vista ven stock de farmacia central por defecto
        centro_param = self.request.query_params.get('centro')
        
        # ISS-FIX: Flag para determinar si el usuario es de centro
        es_usuario_centro = not is_farmacia_or_admin(user) and not user.is_superuser
        
        if es_usuario_centro:
            # Usuario de centro - filtrar stock solo por su centro
            user_centro = get_user_centro(user)
            if user_centro:
                # Anotar stock_calculado basado SOLO en lotes de su centro
                queryset = queryset.annotate(
                    stock_calculado=Coalesce(
                        Sum(
                            'lotes__cantidad_actual',
                            filter=Q(
                                lotes__activo=True,
                                lotes__cantidad_actual__gt=0,
                                lotes__centro=user_centro
                            )
                        ),
                        0
                    )
                )
                # ISS-FIX: Usuarios de centro SOLO ven productos con stock > 0 en su centro
                # Ya no ven todos los 76 productos con stock = 0
                queryset = queryset.filter(stock_calculado__gt=0)
            else:
                # Usuario sin centro asignado - no ve ningún producto
                queryset = queryset.annotate(
                    stock_calculado=Coalesce(Sum('lotes__cantidad_actual', filter=Q(pk__isnull=True)), 0)
                ).filter(stock_calculado__gt=0)  # Filtro imposible = 0 resultados
        else:
            # Admin/Farmacia/Vista - pueden ver stock global o por centro específico
            if centro_param:
                if centro_param == 'central':
                    # Solo stock de farmacia central (centro=NULL)
                    queryset = queryset.annotate(
                        stock_calculado=Coalesce(
                            Sum(
                                'lotes__cantidad_actual',
                                filter=Q(
                                    lotes__activo=True,
                                    lotes__cantidad_actual__gt=0,
                                    lotes__centro__isnull=True
                                )
                            ),
                            0
                        )
                    )
                else:
                    # Stock de un centro específico
                    queryset = queryset.annotate(
                        stock_calculado=Coalesce(
                            Sum(
                                'lotes__cantidad_actual',
                                filter=Q(
                                    lotes__activo=True,
                                    lotes__cantidad_actual__gt=0,
                                    lotes__centro_id=centro_param
                                )
                            ),
                            0
                        )
                    )
            else:
                # Por defecto: stock de farmacia central (donde está el inventario principal)
                queryset = queryset.annotate(
                    stock_calculado=Coalesce(
                        Sum(
                            'lotes__cantidad_actual',
                            filter=Q(
                                lotes__activo=True,
                                lotes__cantidad_actual__gt=0,
                                lotes__centro__isnull=True
                            )
                        ),
                        0
                    )
                )
        
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
                Q(nombre__icontains=search)
            )

        stock_status = self.request.query_params.get('stock_status')
        if stock_status:
            # ISS-FIX: Usar stock_calculado ya anotado (respeta el centro del usuario)
            # Ya no es necesario crear stock_total_calc separado
            status_val = stock_status.lower()
            if status_val == 'sin_stock':
                queryset = queryset.filter(stock_calculado__lte=0)
            elif status_val == 'critico':
                queryset = queryset.filter(
                    stock_calculado__gt=0,
                    stock_minimo__gt=0,
                    stock_calculado__lt=F('stock_minimo') * 0.5
                )
            elif status_val == 'bajo':
                queryset = queryset.filter(
                    Q(
                        stock_minimo__gt=0,
                        stock_calculado__gte=F('stock_minimo') * 0.5,
                        stock_calculado__lt=F('stock_minimo')
                    ) | Q(
                        stock_minimo__lte=0,
                        stock_calculado__gt=0,
                        stock_calculado__lt=25
                    )
                )
            elif status_val == 'normal':
                queryset = queryset.filter(
                    Q(
                        stock_minimo__gt=0,
                        stock_calculado__gte=F('stock_minimo'),
                        stock_calculado__lte=F('stock_minimo') * 2
                    ) | Q(
                        stock_minimo__lte=0,
                        stock_calculado__gte=25,
                        stock_calculado__lt=100
                    )
                )
            elif status_val == 'alto':
                queryset = queryset.filter(
                    Q(
                        stock_minimo__gt=0,
                        stock_calculado__gt=F('stock_minimo') * 2
                    ) | Q(
                        stock_minimo__lte=0,
                        stock_calculado__gte=100
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
            # traceback removido por seguridad (ISS-008)
            logger.error(f"Error al crear producto: {str(e)}", exc_info=True)
            return Response({'error': 'Error al crear producto. Verifique los datos ingresados.'}, status=status.HTTP_400_BAD_REQUEST)
    
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
            # traceback removido por seguridad (ISS-008)
            logger.error(f"Error al actualizar producto: {str(e)}", exc_info=True)
            return Response({'error': 'Error al actualizar producto. Verifique los datos ingresados.'}, status=status.HTTP_400_BAD_REQUEST)
    
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
            # traceback removido por seguridad (ISS-008)
            logger.error(f"Error al eliminar producto: {str(e)}", exc_info=True)
            return Response({'error': 'Error al eliminar producto'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], url_path='toggle-activo')
    def toggle_activo(self, request, pk=None):
        """
        Activa o desactiva un producto.
        POST /api/productos/{id}/toggle-activo/
        
        Reglas:
        - No se puede desactivar un producto con stock disponible > 0
        - Usa update() directo para evitar validación de otros campos
        """
        try:
            producto = self.get_object()
            nuevo_estado = not producto.activo
            
            # Si se va a desactivar, verificar que no tenga stock disponible
            if not nuevo_estado:  # Desactivando
                stock_disponible = producto.lotes.filter(
                    activo=True,
                    cantidad_actual__gt=0
                ).aggregate(total=Sum('cantidad_actual'))['total'] or 0
                
                if stock_disponible > 0:
                    return Response({
                        'error': 'No se puede desactivar el producto',
                        'razon': f'Tiene {stock_disponible} unidades en stock disponible',
                        'sugerencia': 'Transfiera o agote el inventario antes de desactivar'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Usar update() directo para evitar validación de otros campos
            Producto.objects.filter(pk=producto.pk).update(activo=nuevo_estado)
            
            estado = 'activado' if nuevo_estado else 'desactivado'
            return Response({
                'mensaje': f'Producto {estado} exitosamente',
                'activo': nuevo_estado,
                'id': producto.id
            }, status=status.HTTP_200_OK)
        except Producto.DoesNotExist:
            return Response({'error': 'Producto no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error en toggle_activo: {str(e)}", exc_info=True)
            return Response({'error': f'Error interno: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'], url_path='lotes')
    def lotes(self, request, pk=None):
        """
        Obtiene los lotes de un producto.
        GET /api/productos/{id}/lotes/
        
        Parámetros opcionales:
        - centro: ID del centro o 'central' para farmacia central
        - activo: 'true' para solo lotes activos
        - con_stock: 'true' para solo lotes con cantidad > 0
        """
        try:
            from core.models import Lote
            from core.serializers import LoteSerializer
            
            producto = self.get_object()
            user = request.user
            
            # Filtro base: lotes del producto
            lotes = Lote.objects.filter(producto=producto)
            
            # Filtro por centro
            centro_param = request.query_params.get('centro')
            if centro_param:
                if centro_param == 'central':
                    lotes = lotes.filter(centro__isnull=True)
                else:
                    lotes = lotes.filter(centro_id=centro_param)
            else:
                # Por defecto, usuarios de centro solo ven lotes de su centro
                if not is_farmacia_or_admin(user) and not user.is_superuser:
                    user_centro = get_user_centro(user)
                    if user_centro:
                        lotes = lotes.filter(centro=user_centro)
                    else:
                        # Usuario sin centro no ve ningún lote
                        lotes = Lote.objects.none()
                else:
                    # Farmacia/Admin ven lotes de farmacia central por defecto
                    lotes = lotes.filter(centro__isnull=True)
            
            # Filtro por activo
            activo_param = request.query_params.get('activo')
            if activo_param == 'true':
                lotes = lotes.filter(activo=True)
            elif activo_param == 'false':
                lotes = lotes.filter(activo=False)
            
            # Filtro por stock
            con_stock = request.query_params.get('con_stock')
            if con_stock == 'true':
                lotes = lotes.filter(cantidad_actual__gt=0)
            
            # Ordenar por fecha de caducidad
            lotes = lotes.order_by('fecha_caducidad')
            
            # Calcular totales
            total_lotes = lotes.count()
            total_stock = sum(l.cantidad_actual for l in lotes)
            
            # Serializar
            serializer = LoteSerializer(lotes, many=True)
            
            return Response({
                'producto_id': producto.id,
                'producto_nombre': producto.nombre,
                'producto_clave': producto.clave,
                'producto': {
                    'id': producto.id,
                    'clave': producto.clave,
                    'nombre': producto.nombre,
                    'unidad_medida': producto.unidad_medida,
                },
                'lotes': serializer.data,
                'total': total_lotes,
                'total_lotes': total_lotes,
                'total_stock': total_stock,
            })
            
        except Producto.DoesNotExist:
            return Response({'error': 'Producto no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error al obtener lotes del producto: {str(e)}", exc_info=True)
            return Response({'error': 'Error al obtener lotes'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'], url_path='auditoria')
    def auditoria(self, request, pk=None):
        """
        Obtiene el historial de cambios de un producto.
        GET /api/productos/{id}/auditoria/
        """
        try:
            from core.models import AuditoriaLogs
            producto = self.get_object()
            
            # Buscar logs de auditoría relacionados con este producto
            logs = AuditoriaLogs.objects.filter(
                Q(modelo='producto') | Q(modelo='core_producto') | Q(modelo='Producto'),
                objeto_id=str(producto.id)
            ).order_by('-timestamp')[:50]
            
            historial = []
            for log in logs:
                historial.append({
                    'id': log.id,
                    'fecha': log.timestamp.isoformat() if log.timestamp else None,
                    'usuario': log.usuario.get_full_name() or log.usuario.username if log.usuario else 'Sistema',
                    'accion': log.accion,
                    'cambios': log.datos_nuevos if log.datos_nuevos else None,
                    'ip': log.ip_address if log.ip_address else None,
                })
            
            return Response({
                'producto': {
                    'id': producto.id,
                    'clave': producto.clave,
                    'nombre': producto.nombre,
                },
                'historial': historial,
                'total': len(historial)
            })
        except Producto.DoesNotExist:
            return Response({'error': 'Producto no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error en auditoria: {str(e)}", exc_info=True)
            return Response({'error': 'Error al obtener auditoría'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'], url_path='exportar-excel')
    def exportar_excel(self, request):
        """
        Exporta todos los productos a un archivo Excel.
        
        Columnas alineadas con schema real de productos (incluye nombre_comercial):
        - #, Clave, Nombre, Nombre Comercial, Categoria, Unidad Medida, Stock Minimo, Stock Actual,
          Sustancia Activa, Presentacion, Concentracion, Via Admin, Requiere Receta, Controlado, 
          Lotes Activos, Estado
        """
        try:
            productos = self.get_queryset()
            
            # Crear libro de Excel
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = 'Productos'
            
            # Encabezados alineados con schema de Supabase (incluye nombre_comercial)
            headers = ['#', 'Clave', 'Nombre', 'Nombre Comercial', 'Categoria', 'Unidad Medida', 
                       'Stock Minimo', 'Stock Actual', 'Sustancia Activa', 'Presentacion',
                       'Concentracion', 'Via Admin', 'Requiere Receta', 'Controlado', 
                       'Lotes Activos', 'Estado']
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
                stock_actual = producto.lotes.filter(activo=True).aggregate(total=Sum('cantidad_actual'))['total'] or 0
                lotes_activos = producto.lotes.filter(activo=True, cantidad_actual__gt=0).count()
                
                ws.append([
                    idx,
                    producto.clave or '',
                    producto.nombre,
                    producto.nombre_comercial or '',
                    producto.categoria or '',
                    producto.unidad_medida,
                    producto.stock_minimo,
                    stock_actual,
                    producto.sustancia_activa or '',
                    producto.presentacion or '',
                    producto.concentracion or '',
                    producto.via_administracion or '',
                    'Sí' if producto.requiere_receta else 'No',
                    'Sí' if producto.es_controlado else 'No',
                    lotes_activos,
                    'Activo' if producto.activo else 'Inactivo'
                ])
                
                # Colorear fila si el stock está por debajo del mínimo
                if stock_actual < producto.stock_minimo:
                    for col in range(1, 17):
                        ws.cell(row=idx+1, column=col).fill = PatternFill(
                            start_color='FFF4E6', 
                            end_color='FFF4E6', 
                            fill_type='solid'
                        )
            
            # Ajustar anchos de columna
            ws.column_dimensions['A'].width = 6    # #
            ws.column_dimensions['B'].width = 18   # Clave
            ws.column_dimensions['C'].width = 40   # Nombre
            ws.column_dimensions['D'].width = 25   # Nombre Comercial
            ws.column_dimensions['E'].width = 18   # Categoria
            ws.column_dimensions['F'].width = 18   # Unidad Medida
            ws.column_dimensions['G'].width = 12   # Stock Minimo
            ws.column_dimensions['H'].width = 12   # Stock Actual
            ws.column_dimensions['I'].width = 20   # Sustancia Activa
            ws.column_dimensions['J'].width = 18   # Presentacion
            ws.column_dimensions['K'].width = 14   # Concentracion
            ws.column_dimensions['L'].width = 14   # Via Admin
            ws.column_dimensions['M'].width = 14   # Requiere Receta
            ws.column_dimensions['N'].width = 12   # Controlado
            ws.column_dimensions['O'].width = 12   # Lotes Activos
            ws.column_dimensions['P'].width = 10   # Estado
            
            # Generar respuesta
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename=Productos_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            wb.save(response)
            
            return response
            
        except Exception as e:
            # traceback removido por seguridad (ISS-008)
            return Response({
                'error': 'Error al exportar productos',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], url_path='importar-excel')
    def importar_excel(self, request):
        """
        Importa productos desde archivo Excel usando el importador actualizado.
        
        Usa core.utils.excel_importer que maneja el esquema real de la BD.
        Formato esperado alineado con la plantilla descargable.
        
        Límites de seguridad:
        - Tamaño máximo: 10MB
        - Filas máximas: 10,000
        - Extensiones: .xlsx
        """
        from core.utils.excel_importer import importar_productos_desde_excel, crear_log_importacion
        
        file = request.FILES.get('file')
        
        # Validar archivo
        es_valido, error_msg = validar_archivo_excel(file)
        if not es_valido:
            return Response({
                'error': 'Archivo inválido',
                'mensaje': error_msg
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Ejecutar importación
            resultado = importar_productos_desde_excel(file, request.user)
            
            # Crear log de importación
            crear_log_importacion(
                usuario=request.user,
                tipo='Producto',
                archivo_nombre=file.name,
                resultado_dict=resultado
            )
            
            # Determinar status code
            if resultado['exitosa']:
                status_code = status.HTTP_200_OK
            elif resultado['registros_exitosos'] > 0:
                status_code = status.HTTP_206_PARTIAL_CONTENT
            else:
                status_code = status.HTTP_400_BAD_REQUEST
            
            return Response(resultado, status=status_code)
            
        except Exception as e:
            logger.exception(f"Error en importación de productos: {e}")
            return Response({
                'error': 'Error al procesar archivo',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='plantilla')
    def plantilla_productos(self, request):
        """
        Descarga plantilla Excel actualizada para importación de productos.
        
        Usa el generador estandarizado con el esquema real de la base de datos.
        """
        # HALLAZGO #5: Manejo robusto de errores en generación de plantilla
        try:
            from core.utils.excel_templates import generar_plantilla_productos
            return generar_plantilla_productos()
        except ImportError as exc:
            logger.error(f'Error al importar generador de plantilla: {exc}')
            return Response(
                {'error': 'Módulo de generación de plantillas no disponible'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as exc:
            logger.exception(f'Error al generar plantilla de productos: {exc}')
            return Response(
                {'error': 'No se pudo generar la plantilla', 'mensaje': str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


