# -*- coding: utf-8 -*-
"""
ViewSet de Productos.

Gestión completa de productos farmacéuticos incluyendo:
- CRUD de productos
- Importación/exportación Excel
- Auditoría de cambios
- Toggle de estado activo/inactivo
"""
from rest_framework import status
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

from .base import (
    viewsets,
    Producto,
    ProductoSerializer,
    CustomPagination,
    is_farmacia_or_admin,
    get_user_centro,
    validar_archivo_excel,
    cargar_workbook_seguro,
    validar_filas_excel,
    UNIDADES_MEDIDA,
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
        # Usuarios CENTRO solo ven stock de SU centro (lo que farmacia les ha surtido)
        # Admin/Farmacia/Vista ven stock de farmacia central por defecto
        centro_param = self.request.query_params.get('centro')
        
        if not is_farmacia_or_admin(user) and not user.is_superuser:
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
            else:
                # Usuario sin centro asignado - stock = 0
                queryset = queryset.annotate(
                    stock_calculado=Coalesce(Sum('lotes__cantidad_actual', filter=Q(pk__isnull=True)), 0)
                )
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
        
        Columnas alineadas con schema real de productos:
        - #, Código Barras, Nombre, Categoría, Unidad, Stock Mínimo, Stock Actual, 
          Sustancia Activa, Presentación, Requiere Receta, Controlado, Lotes, Estado
        """
        try:
            productos = self.get_queryset()
            
            # Crear libro de Excel
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = 'Productos'
            
            # Encabezados alineados con schema de Supabase
            headers = ['#', 'Código Barras', 'Nombre', 'Categoría', 'Unidad Medida', 
                       'Stock Mínimo', 'Stock Actual', 'Sustancia Activa', 'Presentación',
                       'Concentración', 'Vía Admin', 'Requiere Receta', 'Controlado', 
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
                    for col in range(1, 16):
                        ws.cell(row=idx+1, column=col).fill = PatternFill(
                            start_color='FFF4E6', 
                            end_color='FFF4E6', 
                            fill_type='solid'
                        )
            
            # Ajustar anchos de columna
            ws.column_dimensions['A'].width = 6
            ws.column_dimensions['B'].width = 18
            ws.column_dimensions['C'].width = 40
            ws.column_dimensions['D'].width = 18
            ws.column_dimensions['E'].width = 14
            ws.column_dimensions['F'].width = 12
            ws.column_dimensions['G'].width = 12
            ws.column_dimensions['H'].width = 20
            ws.column_dimensions['I'].width = 14
            ws.column_dimensions['J'].width = 14
            ws.column_dimensions['K'].width = 14
            ws.column_dimensions['L'].width = 14
            ws.column_dimensions['M'].width = 12
            ws.column_dimensions['N'].width = 12
            ws.column_dimensions['O'].width = 10
            
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
        Importa productos desde un archivo Excel.
        
        Formato esperado:
        Fila 1: Encabezados (se ignora)
        Columnas: Clave | Nombre | Unidad | Stock Mínimo | Categoría | 
                  Sustancia Activa | Presentación | Concentración | Vía Admin |
                  Requiere Receta | Controlado | Estado
        
        Nota: Las primeras 4 columnas son requeridas, el resto son opcionales.
        
        Límites de seguridad:
        - Tamaño máximo: configurado en IMPORT_MAX_FILE_SIZE_MB (default 10MB)
        - Filas máximas: configurado en IMPORT_MAX_ROWS (default 5000)
        - Extensiones: .xlsx, .xls
        """
        file = request.FILES.get('file')
        
        # Validar archivo
        es_valido, error_msg = validar_archivo_excel(file)
        if not es_valido:
            return Response({
                'error': 'Archivo inválido',
                'mensaje': error_msg
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # ISS-001: Usar carga segura con límite real de bytes
            wb, error_carga = cargar_workbook_seguro(file)
            if wb is None:
                return Response({
                    'error': 'Error al procesar archivo',
                    'mensaje': error_carga
                }, status=status.HTTP_400_BAD_REQUEST)
            
            ws = wb.active
            
            # Validar número de filas
            filas_validas, error_filas, num_filas = validar_filas_excel(ws)
            if not filas_validas:
                wb.close()  # Liberar recursos en modo read_only
                return Response({
                    'error': 'Archivo demasiado grande',
                    'mensaje': error_filas
                }, status=status.HTTP_400_BAD_REQUEST)
            
            creados = 0
            actualizados = 0
            errores = []
            exitos = []
            
            # ISS-019: Envolver en transacción atómica para evitar estados parciales
            # Si hay errores críticos, se hace rollback automático
            with transaction.atomic():
                # Procesar cada fila (empezando desde la fila 2)
                # Formato esperado (columnas): Clave | Nombre | Unidad | Stock Min | Categoría | 
                #                              Sust Activa | Presentación | Concentración | Vía Admin | 
                #                              Req Receta | Controlado | Estado
                for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                    try:
                        # Extraer valores (asegurarse de tener al menos 12 columnas)
                        valores = list(row) + [None] * 12
                        clave = valores[0]
                        nombre = valores[1]
                        unidad_medida = valores[2]
                        stock_minimo = valores[3]
                        categoria = valores[4]
                        sustancia_activa = valores[5]
                        presentacion = valores[6]
                        concentracion = valores[7]
                        via_administracion = valores[8]
                        requiere_receta = valores[9]
                        es_controlado = valores[10]
                        estado = valores[11]
                        
                        # Validar campo requerido: clave y nombre
                        if not clave:
                            errores.append({'fila': row_idx, 'error': 'Clave es obligatoria'})
                            continue
                        if not nombre:
                            errores.append({'fila': row_idx, 'error': 'Nombre es obligatorio'})
                            continue
                        
                        # Validar unidad
                        unidad_limpia = str(unidad_medida).strip().upper() if unidad_medida else 'PIEZA'
                        if unidad_limpia not in dict(UNIDADES_MEDIDA):
                            errores.append({'fila': row_idx, 'error': f'Unidad no válida: {unidad_limpia}'})
                            continue

                        try:
                            stock_min = int(stock_minimo) if stock_minimo not in [None, ''] else 10
                            if stock_min < 0:
                                raise ValueError
                        except Exception:
                            errores.append({'fila': row_idx, 'error': 'Stock mínimo inválido'})
                            continue

                        # Parsear campos booleanos
                        def parse_bool(val):
                            if val is None:
                                return False
                            return str(val).lower() in ['sí', 'si', 'true', '1', 'yes', 's', 'x']

                        # Validar y normalizar categoría (usar constante centralizada)
                        from core.constants import CATEGORIAS_VALIDAS
                        categoria_limpia = str(categoria).strip().lower() if categoria else 'medicamento'
                        if categoria_limpia not in CATEGORIAS_VALIDAS:
                            categoria_limpia = 'medicamento'  # Default si no es válida

                        # Limpiar y preparar datos alineados con schema real
                        datos = {
                            'nombre': str(nombre).strip()[:500],
                            'unidad_medida': unidad_limpia,
                            'stock_minimo': stock_min,
                            'categoria': categoria_limpia,
                            'sustancia_activa': str(sustancia_activa).strip()[:200] if sustancia_activa else '',
                            'presentacion': str(presentacion).strip()[:200] if presentacion else '',
                            'concentracion': str(concentracion).strip()[:100] if concentracion else '',
                            'via_administracion': str(via_administracion).strip()[:50] if via_administracion else '',
                            'requiere_receta': parse_bool(requiere_receta),
                            'es_controlado': parse_bool(es_controlado),
                            'activo': str(estado).lower() in ['activo', 'sí', 'si', 'true', '1', 'yes', 's'] if estado else True
                        }
                        
                        # Crear o actualizar producto usando clave como identificador
                        clave_limpia = str(clave).strip()[:50].upper()  # También normalizar a mayúsculas
                        
                        producto, created = Producto.objects.update_or_create(
                            clave=clave_limpia,
                            defaults=datos
                        )
                        
                        if created:
                            creados += 1
                        else:
                            actualizados += 1
                        exitos.append({'fila': row_idx, 'producto_id': producto.id, 'clave': producto.clave})
                            
                    except Exception as e:
                        errores.append({'fila': row_idx, 'error': str(e)})
            # Fin del bloque transaction.atomic
            
            return Response({
                'mensaje': 'Importación completada',
                'resumen': {
                    'creados': creados,
                    'actualizados': actualizados,
                    'total_procesados': creados + actualizados,
                    'total_errores': len(errores)
                },
                'exitos': exitos,
                'errores': errores,
                'exito': len(errores) == 0
            }, status=status.HTTP_200_OK if len(errores) == 0 else status.HTTP_207_MULTI_STATUS)
            
        except Exception as e:
            # traceback removido por seguridad (ISS-008)
            return Response({
                'error': 'Error al procesar archivo',
                'mensaje': str(e),
                'sugerencia': 'Verifique que el archivo tenga el formato correcto: Clave, Nombre, Unidad, Stock Mínimo, Categoría, Sustancia Activa, Presentación, Concentración, Vía Admin, Requiere Receta, Controlado, Estado'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='plantilla')
    def plantilla_productos(self, request):
        """
        Descarga plantilla Excel para importación de productos.
        
        Columnas:
        - Clave (REQUERIDO, único) - Código identificador del producto
        - Nombre (REQUERIDO) - Nombre del medicamento o insumo
        - Unidad (opcional) - Unidad de medida (PIEZA, CAJA, FRASCO, SOBRE, AMPOLLETA, TABLETA, CAPSULA, ML, GR)
        - Stock Mínimo (opcional, default: 10) - Cantidad mínima de alerta
        - Categoría (opcional) - medicamento, material_curacion, insumo, equipo, otro
        - Sustancia Activa (opcional) - Principio activo
        - Presentación (opcional) - Forma farmacéutica
        - Concentración (opcional) - Dosis del principio activo
        - Vía Admin (opcional) - Vía de administración
        - Requiere Receta (opcional) - Sí/No
        - Controlado (opcional) - Sí/No
        - Estado (opcional, default: Activo) - Activo/Inactivo
        """
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Productos'
        
        # Headers que coinciden con importar_excel
        headers = [
            'Clave', 'Nombre', 'Unidad', 'Stock Mínimo', 'Categoría',
            'Sustancia Activa', 'Presentación', 'Concentración', 
            'Vía Admin', 'Requiere Receta', 'Controlado', 'Estado'
        ]
        ws.append(headers)
        
        # Filas de ejemplo (unidades en mayúsculas como las espera el sistema)
        ws.append([
            'MED001', 'Paracetamol 500mg', 'CAJA', 50, 'medicamento',
            'Paracetamol', 'Tableta', '500 mg',
            'oral', 'No', 'No', 'Activo'
        ])
        ws.append([
            'MED002', 'Ibuprofeno 400mg', 'FRASCO', 30, 'medicamento',
            'Ibuprofeno', 'Cápsula', '400 mg',
            'oral', 'No', 'No', 'Activo'
        ])
        ws.append([
            'INS001', 'Jeringa 10ml', 'PIEZA', 100, 'material_curacion',
            '', '', '',
            '', 'No', 'No', 'Activo'
        ])
        
        # Aplicar formato a headers
        header_font = Font(bold=True, color='FFFFFF')
        header_fill = PatternFill(start_color='9F2241', end_color='9F2241', fill_type='solid')
        for col in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col)
            cell.font = header_font
            cell.fill = header_fill
        
        # Ajustar ancho de columnas
        column_widths = {
            'A': 12,  # Clave
            'B': 35,  # Nombre
            'C': 12,  # Unidad
            'D': 14,  # Stock Mínimo
            'E': 18,  # Categoría
            'F': 20,  # Sustancia Activa
            'G': 15,  # Presentación
            'H': 15,  # Concentración
            'I': 12,  # Vía Admin
            'J': 15,  # Requiere Receta
            'K': 12,  # Controlado
            'L': 10,  # Estado
        }
        for col_letter, width in column_widths.items():
            ws.column_dimensions[col_letter].width = width
        
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=Plantilla_Productos.xlsx'
        wb.save(response)
        return response
