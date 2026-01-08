# -*- coding: utf-8 -*-
"""
Módulo de ViewSet para Lotes.

Contiene LoteViewSet para gestionar el CRUD completo de lotes farmacéuticos,
incluyendo:
- Listado con filtros por producto, caducidad, stock y centro
- Exportación a PDF y Excel
- Importación masiva desde Excel
- Control de vencimientos y alertas
- Gestión de documentos asociados (facturas, contratos, remisiones)
- Trazabilidad y historial de movimientos

Refactorización audit34: Extraído del monolítico views.py (7654 líneas)
para mejorar mantenibilidad y organización del código.
"""
from datetime import datetime, date, timedelta
import logging
import uuid
import os
from io import BytesIO

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from rest_framework import viewsets, serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.utils import timezone

# Imports desde el módulo base
from .base import (
    # Clases base y utilidades
    CustomPagination,
    # Helpers de seguridad
    is_farmacia_or_admin,
    get_user_centro,
    # Validadores de archivos
    validar_archivo_excel,
    cargar_workbook_seguro,
    validar_filas_excel,
    validar_archivo_pdf,
    # Helper de movimientos
    registrar_movimiento_stock,
    # Constantes
    logger,
)

# Modelos
from core.models import Producto, Lote, Movimiento, Centro, LoteDocumento

# Serializers
from core.serializers import LoteSerializer, LoteDocumentoSerializer

# Permisos
from core.permissions import IsFarmaciaAdminOrReadOnly, IsFarmaciaRole, IsCentroRole


class LoteViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar lotes.
    
    Funcionalidades:
    - CRUD completo
    - Filtrado por producto
    - Filtrado por estado de caducidad
    - Busqueda por numero de lote
    - Validaciones de integridad
    """
    queryset = Lote.objects.select_related('producto').all()
    serializer_class = LoteSerializer
    permission_classes = [IsFarmaciaAdminOrReadOnly]
    pagination_class = CustomPagination

    def get_queryset(self):
        """
        Filtra lotes segun parametros.
        
        Parametros:
        - producto: ID del producto
        - activo: true/false
        - caducidad: vencido/critico/proximo/normal
        - search: busqueda por numero de lote
        - centro: ID del centro o 'central' para farmacia (solo admin/farmacia/vista)
        
        Seguridad: Usuarios de centro solo ven lotes de su centro.
        Admin/farmacia/vista ven todo por defecto, pueden filtrar con ?centro=.
        """
        queryset = Lote.objects.select_related('producto', 'centro').all()
        
        # SEGURIDAD: Filtrar por centro segun rol
        user = self.request.user
        
        # ISS-FIX: Usuarios de centro pueden ver lotes de farmacia central
        # cuando están creando requisiciones (para_requisicion=true)
        para_requisicion = self.request.query_params.get('para_requisicion', '').lower() == 'true'
        
        if not is_farmacia_or_admin(user):
            # Usuario de centro
            user_centro = get_user_centro(user)
            if not user_centro:
                return Lote.objects.none()
            
            if para_requisicion:
                # ISS-FIX: Para crear requisiciones, mostrar lotes de FARMACIA CENTRAL
                # porque las requisiciones se surten desde farmacia central
                queryset = queryset.filter(centro__isnull=True)
            else:
                # Por defecto: solo lotes de SU centro
                queryset = queryset.filter(centro=user_centro)
        else:
            # Admin/farmacia/vista: pueden filtrar por centro especifico
            centro_param = self.request.query_params.get('centro')
            if centro_param:
                if centro_param == 'central':
                    # Filtrar solo farmacia central (centro=NULL)
                    queryset = queryset.filter(centro__isnull=True)
                else:
                    queryset = queryset.filter(centro_id=centro_param)
        
        # Filtrar por producto
        producto = self.request.query_params.get('producto')
        if producto:
            queryset = queryset.filter(producto_id=producto)
        
        # Filtrar por activo (el campo real en la BD)
        activo = self.request.query_params.get('activo')
        if activo is not None:
            if activo.lower() in ['true', '1', 'si']:
                queryset = queryset.filter(activo=True)
            elif activo.lower() in ['false', '0', 'no']:
                queryset = queryset.filter(activo=False)
        
        # Busqueda por numero de lote, clave o nombre producto (ISS-003)
        search = self.request.query_params.get('search')
        if search and search.strip():
            search_term = search.strip()
            queryset = queryset.filter(
                Q(numero_lote__icontains=search_term) |
                Q(producto__clave__icontains=search_term) |
                Q(producto__nombre__icontains=search_term)
            )
        
        # Filtrar por estado de caducidad segun especificacion SIFP:
        # Normal: > 6 meses (180 dias)
        # Proximo: 3-6 meses (90-180 dias)
        # Critico: < 3 meses (90 dias)
        # Vencido: < 0 dias
        caducidad = self.request.query_params.get('caducidad')
        if caducidad:
            hoy = date.today()
            
            if caducidad == 'vencido':
                queryset = queryset.filter(fecha_caducidad__lt=hoy)
            elif caducidad == 'critico':
                # Menos de 3 meses (< 90 dias) pero no vencido
                queryset = queryset.filter(
                    fecha_caducidad__gte=hoy,
                    fecha_caducidad__lt=hoy + timedelta(days=90)
                )
            elif caducidad == 'proximo':
                # Entre 3 y 6 meses (90-180 dias)
                queryset = queryset.filter(
                    fecha_caducidad__gte=hoy + timedelta(days=90),
                    fecha_caducidad__lt=hoy + timedelta(days=180)
                )
            elif caducidad == 'normal':
                # Mas de 6 meses (> 180 dias)
                queryset = queryset.filter(fecha_caducidad__gte=hoy + timedelta(days=180))
        
        # Filtrar por stock minimo (para catalogo de requisiciones)
        stock_min = self.request.query_params.get('stock_min')
        if stock_min:
            try:
                queryset = queryset.filter(cantidad_actual__gte=int(stock_min))
            except (ValueError, TypeError):
                pass
        
        # Filtrar por existencia de stock (con_stock/sin_stock)
        con_stock = self.request.query_params.get('con_stock')
        if con_stock in ['con_stock', 'true', '1', True]:
            queryset = queryset.filter(cantidad_actual__gt=0)
        elif con_stock in ['sin_stock', 'false', '0', False]:
            queryset = queryset.filter(cantidad_actual=0)
        
        # Filtrar solo lotes disponibles (no vencidos) para el catalogo
        solo_disponibles = self.request.query_params.get('solo_disponibles')
        if solo_disponibles == 'true':
            queryset = queryset.filter(
                activo=True,
                fecha_caducidad__gt=date.today()
            )
        
        # ISS-FIX: Filtrar por rango de fechas (para exportación de trazabilidad)
        fecha_desde = self.request.query_params.get('fecha_desde')
        if fecha_desde:
            try:
                from datetime import datetime
                fecha_desde_dt = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__gte=fecha_desde_dt)
            except (ValueError, TypeError):
                pass
        
        fecha_hasta = self.request.query_params.get('fecha_hasta')
        if fecha_hasta:
            try:
                from datetime import datetime
                fecha_hasta_dt = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__lte=fecha_hasta_dt)
            except (ValueError, TypeError):
                pass
        
        return queryset.order_by('-created_at')
    
    def retrieve(self, request, *args, **kwargs):
        """
        Obtiene un lote específico por ID.
        
        ISS-FIX: Usuarios de centro pueden consultar lotes de farmacia central
        cuando están verificando stock para requisiciones (para_requisicion=true).
        Esto es necesario porque las requisiciones se surten desde farmacia central.
        """
        para_requisicion = request.query_params.get('para_requisicion', '').lower() == 'true'
        user = request.user
        
        # Si es para requisición y el usuario es de centro, buscar el lote sin filtro de centro
        if para_requisicion and not is_farmacia_or_admin(user):
            try:
                # Buscar el lote directamente (sin filtro de centro)
                lote = Lote.objects.select_related('producto', 'centro').get(pk=kwargs['pk'])
                
                # Solo permitir ver lotes de farmacia central (para requisiciones)
                if lote.centro is not None:
                    return Response(
                        {'error': 'Solo puede consultar lotes de farmacia central para requisiciones'},
                        status=status.HTTP_403_FORBIDDEN
                    )
                
                serializer = self.get_serializer(lote)
                return Response(serializer.data)
            except Lote.DoesNotExist:
                return Response(
                    {'error': 'Lote no encontrado'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Comportamiento normal: usa get_queryset() con filtros de seguridad
        return super().retrieve(request, *args, **kwargs)
    
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
                {'error': 'Error de validacion', 'detalles': e.detail}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            # traceback removido por seguridad (ISS-008)
            return Response(
                {'error': 'Error al crear lote', 'mensaje': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, *args, **kwargs):
        """Actualiza un lote existente.
        
        ISS-010 FIX: Validación explícita de permisos para evitar IDOR.
        Solo admin/farmacia pueden modificar lotes de farmacia central.
        Usuarios de centro solo pueden modificar lotes de SU centro.
        """
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            
            # ISS-010: Validar permisos de escritura sobre este lote específico
            user = request.user
            if not is_farmacia_or_admin(user):
                user_centro = get_user_centro(user)
                lote_centro = instance.centro
                
                # Si el lote es de farmacia central o de otro centro, denegar
                if lote_centro is None or (user_centro and lote_centro.pk != user_centro.pk):
                    logger.warning(
                        f"ISS-010: Intento de modificación no autorizada de lote. "
                        f"Usuario={user.username}, lote={instance.numero_lote}, "
                        f"lote_centro={lote_centro}, user_centro={user_centro}"
                    )
                    return Response(
                        {'error': 'No tiene permisos para modificar este lote'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            
            return Response(serializer.data)
        except serializers.ValidationError as e:
            return Response(
                {'error': 'Error de validacion', 'detalles': e.detail}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            # traceback removido por seguridad (ISS-008)
            return Response(
                {'error': 'Error al actualizar lote', 'mensaje': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, *args, **kwargs):
        """
        Elimina un lote.
        
        ISS-010 FIX: Validación explícita de permisos para evitar IDOR.
        
        Validaciones:
        - Permisos de escritura sobre el lote
        - No puede eliminarse si tiene movimientos asociados
        """
        instance = self.get_object()
        
        # ISS-010: Validar permisos de escritura sobre este lote específico
        user = request.user
        if not is_farmacia_or_admin(user):
            user_centro = get_user_centro(user)
            lote_centro = instance.centro
            
            # Si el lote es de farmacia central o de otro centro, denegar
            if lote_centro is None or (user_centro and lote_centro.pk != user_centro.pk):
                logger.warning(
                    f"ISS-010: Intento de eliminación no autorizada de lote. "
                    f"Usuario={user.username}, lote={instance.numero_lote}, "
                    f"lote_centro={lote_centro}, user_centro={user_centro}"
                )
                return Response(
                    {'error': 'No tiene permisos para eliminar este lote'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
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
            # traceback removido por seguridad (ISS-008)
            return Response({
                'error': 'Error al eliminar lote',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='consolidados')
    def consolidados(self, request):
        """
        TRAZABILIDAD: Obtiene lotes consolidados (únicos por numero_lote + producto).
        
        Los lotes que se distribuyen a múltiples centros se consolidan sumando
        las cantidades de todos los centros. Esto representa la trazabilidad real:
        un lote físico = un registro, aunque esté distribuido en varios centros.
        
        GET /api/lotes/consolidados/
        
        Parámetros opcionales:
        - search: Buscar por número de lote o clave/nombre de producto
        - producto: Filtrar por ID de producto
        - centro: ID del centro o 'central' para farmacia central
        - activo: true/false
        - page, page_size: Paginación
        
        Returns:
            Lista de lotes únicos con cantidad_total sumada de todos los centros
            y lista de centros donde está distribuido cada lote.
        """
        from collections import defaultdict
        
        # Obtener lotes con filtro opcional de centro
        # Optimización: usar only() para traer solo campos necesarios
        queryset = Lote.objects.select_related('producto', 'centro').only(
            'id', 'numero_lote', 'fecha_caducidad', 'fecha_fabricacion',
            'precio_unitario', 'marca', 'numero_contrato', 'ubicacion',
            'cantidad_inicial', 'cantidad_actual', 'activo',
            'producto__id', 'producto__clave', 'producto__nombre', 
            'producto__descripcion', 'producto__presentacion', 'producto__unidad_medida',
            'centro__id', 'centro__nombre'
        )
        
        # Determinar rol del usuario PRIMERO
        user = request.user
        es_admin_farmacia = is_farmacia_or_admin(user)
        
        # Verificar si hay búsqueda específica por número de lote
        search = request.query_params.get('search', '').strip()
        busqueda_especifica = bool(search and len(search) >= 3)
        
        # Filtrar por activo según rol:
        # - Farmacia/Admin: Ven TODOS los lotes (activos e inactivos) para trazabilidad completa
        # - Centro: Solo ven lotes activos
        activo_param = request.query_params.get('activo')
        if activo_param is not None:
            if activo_param.lower() in ['true', '1', 'activo']:
                queryset = queryset.filter(activo=True)
            elif activo_param.lower() in ['false', '0', 'inactivo']:
                queryset = queryset.filter(activo=False)
            # Si es vacío o 'todos', no filtrar por activo
        elif not es_admin_farmacia:
            # Usuarios de Centro: por defecto solo ver lotes activos
            queryset = queryset.filter(activo=True)
        # Farmacia/Admin sin filtro: ver TODOS los lotes (activos e inactivos) para trazabilidad
        
        # Filtrar por con_stock según rol del usuario:
        # - Farmacia/Admin: Por defecto ven TODOS los lotes (con y sin stock) para trazabilidad
        # - Centro: Por defecto solo ven lotes CON stock disponible
        
        con_stock_param = request.query_params.get('con_stock')
        if con_stock_param:
            if con_stock_param.lower() in ['con_stock', 'true', '1']:
                queryset = queryset.filter(cantidad_actual__gt=0)
            elif con_stock_param.lower() in ['sin_stock', 'false', '0']:
                queryset = queryset.filter(cantidad_actual=0)
        elif not es_admin_farmacia:
            # Usuarios de Centro: por defecto solo ver lotes con stock
            queryset = queryset.filter(cantidad_actual__gt=0)
        # Farmacia/Admin sin filtro: mostrar todos los lotes
        
        # Filtrar por centro si se especifica
        centro_param = request.query_params.get('centro')
        if centro_param:
            if centro_param == 'central':
                # Solo farmacia central (centro=NULL)
                queryset = queryset.filter(centro__isnull=True)
            elif centro_param != 'todos':
                # Centro específico por ID
                try:
                    queryset = queryset.filter(centro_id=int(centro_param))
                except (ValueError, TypeError):
                    pass
        
        # Aplicar filtros de búsqueda
        search = request.query_params.get('search')
        if search and search.strip():
            search_term = search.strip()
            queryset = queryset.filter(
                Q(numero_lote__icontains=search_term) |
                Q(producto__clave__icontains=search_term) |
                Q(producto__nombre__icontains=search_term)
            )
        
        producto = request.query_params.get('producto')
        if producto:
            queryset = queryset.filter(producto_id=producto)
        
        # Filtrar por estado de caducidad (mismo que en get_queryset)
        caducidad = request.query_params.get('caducidad')
        if caducidad:
            hoy = date.today()
            if caducidad == 'vencido':
                queryset = queryset.filter(fecha_caducidad__lt=hoy)
            elif caducidad == 'critico':
                queryset = queryset.filter(
                    fecha_caducidad__gte=hoy,
                    fecha_caducidad__lt=hoy + timedelta(days=90)
                )
            elif caducidad == 'proximo':
                queryset = queryset.filter(
                    fecha_caducidad__gte=hoy + timedelta(days=90),
                    fecha_caducidad__lt=hoy + timedelta(days=180)
                )
            elif caducidad == 'normal':
                queryset = queryset.filter(fecha_caducidad__gte=hoy + timedelta(days=180))
        
        queryset = queryset.order_by('producto__clave', 'numero_lote', 'fecha_caducidad')
        
        # Consolidar por (producto_id, numero_lote)
        lotes_consolidados = defaultdict(lambda: {
            'id': None,  # ID del primer lote encontrado (para referencia)
            'producto': None,
            'producto_id': None,
            'producto_clave': '',
            'producto_nombre': '',
            'producto_info': None,
            'numero_lote': '',
            'cantidad_total': 0,
            'cantidad_inicial_total': 0,
            'fecha_caducidad': None,
            'precio_unitario': 0,
            'marca': '-',
            'numero_contrato': None,
            'centros': [],
            'centros_detalle': [],  # Lista con nombre y cantidad por centro
            'activo': True,
            'dias_para_caducar': 999,
            'alerta_caducidad': 'normal',
        })
        
        hoy = date.today()
        
        for lote in queryset:
            key = (lote.producto_id, lote.numero_lote)
            cons = lotes_consolidados[key]
            
            if cons['id'] is None:
                cons['id'] = lote.id
                cons['producto'] = lote.producto_id
                cons['producto_id'] = lote.producto_id
                cons['producto_clave'] = lote.producto.clave
                cons['producto_nombre'] = lote.producto.nombre or lote.producto.descripcion or ''
                cons['producto_info'] = {
                    'presentacion': lote.producto.presentacion or '',
                    'unidad_medida': lote.producto.unidad_medida or 'PIEZA',
                }
                cons['numero_lote'] = lote.numero_lote
                cons['fecha_caducidad'] = lote.fecha_caducidad.isoformat() if lote.fecha_caducidad else None
                cons['precio_unitario'] = float(lote.precio_unitario or 0)
                cons['marca'] = lote.marca or '-'
                cons['numero_contrato'] = lote.numero_contrato
                
                # Calcular días para caducar y alerta
                if lote.fecha_caducidad:
                    dias = (lote.fecha_caducidad - hoy).days
                    cons['dias_para_caducar'] = dias
                    if dias < 0:
                        cons['alerta_caducidad'] = 'vencido'
                    elif dias < 90:
                        cons['alerta_caducidad'] = 'critico'
                    elif dias < 180:
                        cons['alerta_caducidad'] = 'proximo'
                    else:
                        cons['alerta_caducidad'] = 'normal'
            
            cons['cantidad_total'] += lote.cantidad_actual
            cons['cantidad_inicial_total'] += lote.cantidad_inicial
            
            # Registrar centro
            centro_nombre = lote.centro.nombre if lote.centro else 'Almacén Central'
            if centro_nombre not in cons['centros']:
                cons['centros'].append(centro_nombre)
            
            cons['centros_detalle'].append({
                'centro_id': lote.centro_id,
                'centro_nombre': centro_nombre,
                'cantidad': lote.cantidad_actual,
                'ubicacion': lote.ubicacion or '-',
            })
        
        # Convertir a lista y agregar campos calculados
        resultados = []
        for key, cons in lotes_consolidados.items():
            # Calcular porcentaje consumido
            if cons['cantidad_inicial_total'] > 0:
                porcentaje = round((1 - cons['cantidad_total'] / cons['cantidad_inicial_total']) * 100, 1)
            else:
                porcentaje = 0
            cons['porcentaje_consumido'] = porcentaje
            cons['cantidad_actual'] = cons['cantidad_total']  # Alias para compatibilidad
            cons['cantidad_inicial'] = cons['cantidad_inicial_total']
            cons['centro_nombre'] = ', '.join(cons['centros'][:2]) + ('...' if len(cons['centros']) > 2 else '')
            resultados.append(cons)
        
        # Ordenar por clave de producto y número de lote
        resultados.sort(key=lambda x: (x['producto_clave'], x['numero_lote']))
        
        # Paginación simple
        page_size = int(request.query_params.get('page_size', 25))
        page = int(request.query_params.get('page', 1))
        total = len(resultados)
        start = (page - 1) * page_size
        end = start + page_size
        
        return Response({
            'count': total,
            'total_pages': (total + page_size - 1) // page_size,
            'current_page': page,
            'results': resultados[start:end],
        })

    @action(detail=False, methods=['get'], url_path='diagnostico-centro')
    def diagnostico_centro(self, request):
        """
        ISS-FIX (lotes-centro): Endpoint de diagnóstico de lotes por centro.
        GET /api/lotes/diagnostico-centro/?producto_id={id}
        
        Solo accesible para admin/farmacia. Muestra distribución de lotes
        de un producto específico entre todos los centros.
        """
        # Solo admin/farmacia puede usar este endpoint
        if not is_farmacia_or_admin(request.user) and not request.user.is_superuser:
            return Response({
                'error': 'Este endpoint solo está disponible para administradores'
            }, status=status.HTTP_403_FORBIDDEN)
        
        producto_id = request.query_params.get('producto_id')
        if not producto_id:
            return Response({
                'error': 'Se requiere el parámetro producto_id'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            producto = Producto.objects.get(pk=producto_id)
        except Producto.DoesNotExist:
            return Response({
                'error': f'Producto con ID {producto_id} no encontrado'
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            # Obtener TODOS los lotes del producto (sin filtros de centro)
            todos_lotes = Lote.objects.filter(
                producto=producto
            ).select_related('centro').order_by('centro_id', 'numero_lote')
            
            # Agrupar por centro
            centros_info = {}
            for lote in todos_lotes:
                centro_key = lote.centro_id if lote.centro else 'central'
                centro_nombre = lote.centro.nombre if lote.centro else 'Farmacia Central'
                
                if centro_key not in centros_info:
                    centros_info[centro_key] = {
                        'centro_id': centro_key,
                        'centro_nombre': centro_nombre,
                        'lotes': [],
                        'total_stock': 0,
                        'total_lotes': 0,
                        'lotes_activos': 0,
                        'lotes_con_stock': 0,
                    }
                
                lote_info = {
                    'id': lote.id,
                    'numero_lote': lote.numero_lote,
                    'cantidad_inicial': lote.cantidad_inicial,
                    'cantidad_actual': lote.cantidad_actual,
                    'fecha_caducidad': lote.fecha_caducidad.isoformat() if lote.fecha_caducidad else None,
                    'activo': lote.activo,
                    'created_at': lote.created_at.isoformat() if hasattr(lote, 'created_at') and lote.created_at else None,
                }
                
                centros_info[centro_key]['lotes'].append(lote_info)
                centros_info[centro_key]['total_stock'] += lote.cantidad_actual
                centros_info[centro_key]['total_lotes'] += 1
                if lote.activo:
                    centros_info[centro_key]['lotes_activos'] += 1
                if lote.cantidad_actual > 0:
                    centros_info[centro_key]['lotes_con_stock'] += 1
            
            # Listar todos los centros del sistema para ver cuáles NO tienen lotes
            from core.models import Centro
            all_centros = list(Centro.objects.values('id', 'nombre'))
            centros_sin_lotes = [
                c for c in all_centros 
                if c['id'] not in centros_info and 'central' not in centros_info
            ]
            
            return Response({
                'producto': {
                    'id': producto.id,
                    'clave': producto.clave,
                    'nombre': producto.nombre,
                },
                'resumen_global': {
                    'total_lotes': todos_lotes.count(),
                    'total_stock_global': sum(l.cantidad_actual for l in todos_lotes),
                    'centros_con_lotes': len(centros_info),
                    'centros_sin_lotes': len(centros_sin_lotes),
                },
                'distribucion_por_centro': centros_info,
                'centros_sin_lotes': centros_sin_lotes,
            })
            
        except Exception as e:
            logger.error(f"Error en diagnostico_centro: {str(e)}", exc_info=True)
            return Response({
                'error': f'Error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='exportar-pdf')
    def exportar_pdf(self, request):
        """
        Genera PDF de inventario de lotes con filtros opcionales.
        
        Usa los mismos filtros que get_queryset para consistencia:
        - producto: ID del producto
        - activo: true/false
        - search: búsqueda en número de lote o producto
        - caducidad: vencido/critico/proximo/normal
        - con_stock: con_stock/sin_stock
        - centro: ID del centro o 'central'
        
        Respeta permisos de usuario:
        - Usuarios de centro solo ven lotes de su centro
        - Admin/Farmacia/Vista ven todo
        """
        from core.utils.pdf_reports import generar_reporte_lotes
        
        try:
            # Usar get_queryset que ya aplica filtros y permisos
            queryset = self.get_queryset()
            
            # Limitar a 500 lotes para PDF
            lotes = queryset[:500]
            
            # Preparar datos para el PDF
            lotes_data = []
            for lote in lotes:
                lotes_data.append({
                    'producto_clave': getattr(lote.producto, 'clave', '') if lote.producto else '',
                    'producto_nombre': getattr(lote.producto, 'nombre', '') if lote.producto else '',
                    'numero_lote': lote.numero_lote or '',
                    'fecha_fabricacion': lote.fecha_fabricacion.strftime('%Y-%m-%d') if lote.fecha_fabricacion else '',
                    'fecha_caducidad': lote.fecha_caducidad.strftime('%Y-%m-%d') if lote.fecha_caducidad else '',
                    'fecha_caducidad_raw': lote.fecha_caducidad,
                    'cantidad_inicial': lote.cantidad_inicial,
                    'cantidad_actual': lote.cantidad_actual,
                    'centro_nombre': getattr(lote.centro, 'nombre', 'Farmacia Central') if lote.centro else 'Farmacia Central',
                    'activo': lote.activo,
                })
            
            # Preparar filtros para mostrar en el PDF
            filtros = {}
            if request.query_params.get('producto'):
                try:
                    producto = Producto.objects.get(pk=request.query_params.get('producto'))
                    filtros['producto'] = f"{producto.clave} - {producto.nombre}"
                except Producto.DoesNotExist:
                    pass
            if request.query_params.get('centro'):
                centro_param = request.query_params.get('centro')
                if centro_param == 'central':
                    filtros['centro'] = 'Farmacia Central'
                else:
                    try:
                        centro = Centro.objects.get(pk=centro_param)
                        filtros['centro'] = centro.nombre
                    except Centro.DoesNotExist:
                        pass
            if request.query_params.get('caducidad'):
                filtros['caducidad'] = request.query_params.get('caducidad')
            if request.query_params.get('con_stock'):
                filtros['con_stock'] = request.query_params.get('con_stock')
            if request.query_params.get('activo'):
                filtros['activo'] = request.query_params.get('activo')
            if request.query_params.get('search'):
                filtros['busqueda'] = request.query_params.get('search')
            
            pdf_buffer = generar_reporte_lotes(lotes_data, filtros)
            
            response = HttpResponse(
                pdf_buffer.getvalue(),
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'attachment; filename="Inventario_Lotes_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
            
            return response
            
        except Exception as e:
            # traceback removido por seguridad (ISS-008)
            return Response({
                'error': 'Error al generar PDF de lotes',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='exportar-excel')
    def exportar_excel(self, request):
        """
        Exporta lotes aplicando los filtros de listado.
        Si el usuario tiene permisos globales, se exporta la vista CONSOLIDADA (agrupada por producto y lote)
        para coincidir con la visualización del frontend.

        Columnas basadas estrictamente en formulario "Editar Lote" + Cantidad Actual.
        """
        try:
            from collections import defaultdict
            
            # Reutilizar el queryset que ya aplica todos los filtros
            lotes = self.get_queryset()
            
            # ISS-FIX: Determinar si debemos consolidar
            user = request.user
            es_farmacia_admin = is_farmacia_or_admin(user)
            
            # Lógica de consolidación
            if es_farmacia_admin:
                lotes_map = defaultdict(lambda: {
                    'lote_obj': None,            # Objeto lote representativo
                    'cantidad_inicial': 0,
                    'cantidad_actual': 0,
                    'ubicaciones': set(),
                    'activo': False,
                    'found_main': False          # Flag para saber si ya encontramos el lote de farmacia central
                })
                
                for lote in lotes:
                    key = (lote.producto_id, lote.numero_lote)
                    item = lotes_map[key]
                    
                    # LOGICA CORREGIDA: Cantidad Inicial NO se suma.
                    # Se toma la del lote de Farmacia Central (origen) o el primero que se encuentre.
                    es_farmacia_central = (lote.centro is None)
                    
                    if item['lote_obj'] is None:
                        # Primer registro encontrado para este lote
                        item['lote_obj'] = lote
                        item['cantidad_inicial'] = lote.cantidad_inicial
                        item['found_main'] = es_farmacia_central
                    elif es_farmacia_central:
                        # Encontramos el registro maestro (Farmacia Central), este tiene la verdad histórica
                        item['lote_obj'] = lote
                        item['cantidad_inicial'] = lote.cantidad_inicial
                        item['found_main'] = True
                    # Si ya tenemos un lote y este no es el principal, ignoramos su cantidad_inicial
                    # para evitar sumar duplicados (transfrencias, etc).
                    
                    # La cantidad actual SI se suma (es el stock disperso total)
                    item['cantidad_actual'] += lote.cantidad_actual
                    
                    item['ubicaciones'].add(lote.ubicacion or '')
                    if lote.activo:
                        item['activo'] = True
                        
                lista_exportar = []
                for val in lotes_map.values():
                    lote_base = val['lote_obj']
                    lote_base.cantidad_inicial_total = val['cantidad_inicial']
                    lote_base.cantidad_actual_total = val['cantidad_actual']
                    lote_base.activo_consolidado = val['activo']
                    lista_exportar.append(lote_base)
            else:
                lista_exportar = list(lotes)
                for l in lista_exportar:
                    l.cantidad_inicial_total = l.cantidad_inicial
                    l.cantidad_actual_total = l.cantidad_actual
                    l.activo_consolidado = l.activo

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = 'Lotes'

            # Headers exactos
            headers = [
                'Producto', 'Presentación', 'Código de Lote', 'Fecha de Caducidad',
                'Cantidad Inicial', 'Cantidad Actual', 'Precio Unitario', 'Fecha de Fabricación',
                'Ubicación', 'Número de Contrato', 'Marca / Laboratorio', 'Lote activo'
            ]
            ws.append(headers)
            
            header_fill = PatternFill(start_color='632842', end_color='632842', fill_type='solid')
            header_font = Font(bold=True, color='FFFFFF', size=11)
            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center')

            for idx, lote in enumerate(lista_exportar, 1):
                if lote.producto:
                    nom_prod = f"{lote.producto.clave or ''} - {lote.producto.nombre}"
                    presentacion = lote.producto.presentacion or ''
                else:
                    nom_prod = 'Producto Desconocido'
                    presentacion = ''

                cant_inicial = getattr(lote, 'cantidad_inicial_total', lote.cantidad_inicial)
                cant_actual = getattr(lote, 'cantidad_actual_total', lote.cantidad_actual)
                activo_str = 'Sí' if getattr(lote, 'activo_consolidado', lote.activo) else 'No'
                
                # Para reporte consolidado, forzamos Almacén Central
                ubicacion_str = 'Almacén Central' if es_farmacia_admin else (lote.ubicacion or '')

                ws.append([
                    nom_prod,
                    presentacion,
                    lote.numero_lote or '',
                    lote.fecha_caducidad.strftime('%d/%m/%Y') if lote.fecha_caducidad else '',
                    cant_inicial,
                    cant_actual,
                    float(lote.precio_unitario) if lote.precio_unitario else 0.00,
                    lote.fecha_fabricacion.strftime('%d/%m/%Y') if lote.fecha_fabricacion else '',
                    ubicacion_str,
                    lote.numero_contrato or '',
                    lote.marca or '',
                    activo_str
                ])

            # Ajustar anchos de columna
            # Prod(40), Pres(25), Lote(15), Cadu(15), Ini(15), Act(15), Prec(15), Fab(15), Ubi(20), Cont(20), Mar(20), Act(12)
            column_widths = [40, 25, 15, 15, 15, 15, 15, 15, 20, 20, 20, 12]
            for col_idx, width in enumerate(column_widths, 1):
                ws.column_dimensions[get_column_letter(col_idx)].width = width

            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename=Lotes_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            wb.save(response)
            return response
        except Exception as exc:
            # traceback removido por seguridad (ISS-008)
            return Response({'error': 'Error al exportar lotes', 'mensaje': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='importar-excel')
    def importar_excel(self, request):
        """
        Importa lotes desde Excel usando el importador estandarizado.
        
        Soporta múltiples formatos de columnas:
        - Clave/ID/Nombre Producto (OBLIGATORIO)
        - Número Lote (OBLIGATORIO)
        - Cantidad Inicial (OBLIGATORIO)
        - Fecha Caducidad (OBLIGATORIO)
        - Fecha Fabricación (opcional)
        - Precio Unitario (opcional, default 0)
        - Número Contrato (opcional)
        - Marca (opcional)
        - Ubicación (opcional)
        - Centro (opcional - nombre del centro)
        - Activo (opcional, default Activo)
        
        Detecta automáticamente la fila de encabezados.
        Soporta archivos con encabezados en fila 1, 2 o 3.
        
        Límites de seguridad:
        - Tamaño máximo: 10MB
        - Extensiones: .xlsx, .xls
        """
        from core.utils.excel_importer import importar_lotes_desde_excel, crear_log_importacion
        
        file = request.FILES.get('file')
        
        # Validar archivo
        es_valido, error_msg = validar_archivo_excel(file)
        if not es_valido:
            return Response({
                'error': 'Archivo inválido',
                'mensaje': error_msg
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Obtener centro del usuario si aplica
            centro_id = None
            if hasattr(request.user, 'centro') and request.user.centro:
                centro_id = request.user.centro.id
            
            # Ejecutar importación
            resultado = importar_lotes_desde_excel(file, request.user, centro_id=centro_id)
            
            # Crear log de importación
            crear_log_importacion(
                usuario=request.user,
                tipo='Lote',
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
            logger.exception(f"Error en importación de lotes: {e}")
            return Response({
                'error': 'Error al procesar archivo',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='plantilla')
    def plantilla_lotes(self, request):
        """
        Descarga plantilla Excel actualizada para importación de lotes.
        
        Usa el generador estandarizado con el esquema real de la base de datos.
        """
        # HALLAZGO #5: Manejo robusto de errores en generación de plantilla
        try:
            from core.utils.excel_templates import generar_plantilla_lotes
            
            # Obtener centro del usuario si aplica
            user = request.user
            centro = None
            if not is_farmacia_or_admin(user):
                centro = get_user_centro(user)
            
            return generar_plantilla_lotes(centro=centro)
        except ImportError as exc:
            logger.error(f'Error al importar generador de plantilla: {exc}')
            return Response(
                {'error': 'Módulo de generación de plantillas no disponible'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as exc:
            logger.exception(f'Error al generar plantilla de lotes: {exc}')
            return Response(
                {'error': 'No se pudo generar la plantilla', 'mensaje': str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def por_vencer(self, request):
        """
        Obtiene lotes proximos a vencer.
        
        Parametros:
        - dias: numero de dias (default: 30)
        """
        try:
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
            # traceback removido por seguridad (ISS-008)
            return Response({
                'error': 'Error al obtener lotes por vencer',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='por-caducar')
    def por_caducar(self, request):
        """Alias compatible para el frontend: lotes proximos a vencer."""
        try:
            dias = int(request.query_params.get('dias', 90))
            hoy = date.today()
            fecha_limite = hoy + timedelta(days=dias)
            lotes = Lote.objects.select_related('producto').filter(
                cantidad_actual__gt=0,
                fecha_caducidad__gt=hoy,
                fecha_caducidad__lte=fecha_limite
            ).order_by('fecha_caducidad')

            page = self.paginate_queryset(lotes)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(lotes, many=True)
            return Response(serializer.data)
        except Exception as exc:
            # traceback removido por seguridad (ISS-008)
            return Response({'error': 'Error al obtener lotes por caducar', 'mensaje': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def vencidos(self, request):
        """Lotes con caducidad vencida y stock disponible."""
        try:
            hoy = date.today()
            lotes = Lote.objects.select_related('producto').filter(
                cantidad_actual__gt=0,
                fecha_caducidad__lt=hoy
            ).order_by('fecha_caducidad')

            page = self.paginate_queryset(lotes)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(lotes, many=True)
            return Response(serializer.data)
        except Exception as exc:
            # traceback removido por seguridad (ISS-008)
            return Response({'error': 'Error al obtener lotes vencidos', 'mensaje': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def historial(self, request, pk=None):
        """Obtiene el historial de movimientos de un lote"""
        try:
            lote = self.get_object()
            
            movimientos = Movimiento.objects.filter(lote=lote).select_related(
                'lote__producto'
            ).order_by('-fecha')
            
            total_entradas = movimientos.filter(tipo='entrada').aggregate(
                total=Sum('cantidad')
            )['total'] or 0
            
            total_salidas = movimientos.filter(tipo='salida').aggregate(
                total=Sum('cantidad')
            )['total'] or 0
            
            movimientos_data = []
            for mov in movimientos:
                movimientos_data.append({
                    'id': mov.id,
                    'tipo': mov.tipo,
                    'cantidad': mov.cantidad,
                    'fecha': mov.fecha,
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
            # traceback removido por seguridad (ISS-008)
            return Response({
                'error': 'Error al obtener historial',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def ajustar_stock(self, request, pk=None):
        """
        Ajusta stock del lote y crea movimiento asociado (entrada/salida/ajuste).
        """
        lote = self.get_object()
        tipo = request.data.get('tipo', 'ajuste')
        cantidad = request.data.get('cantidad')
        observaciones = request.data.get('observaciones', '')

        try:
            movimiento, lote_actualizado = registrar_movimiento_stock(
                lote=lote,
                tipo=tipo,
                cantidad=cantidad,
                usuario=request.user if request.user.is_authenticated else None,
                centro=None,
                requisicion=None,
                observaciones=observaciones
            )
            return Response({
                'mensaje': 'Stock ajustado correctamente',
                'lote': self.get_serializer(lote_actualizado).data,
                'movimiento_id': movimiento.id
            })
        except serializers.ValidationError as exc:
            return Response({'error': 'Error de validacion', 'detalles': exc.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            # traceback removido por seguridad (ISS-008)
            return Response({'error': 'Error al ajustar stock', 'mensaje': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], url_path='lotes-derivados')
    def lotes_derivados(self, request, pk=None):
        """
        Obtiene los lotes derivados de un lote de farmacia (vinculados a centros).
        
        Solo aplica para lotes de farmacia central (centro=NULL).
        Muestra todos los centros que tienen stock de este lote.
        """
        try:
            lote = self.get_object()
            
            # Verificar que es un lote de farmacia
            if lote.centro is not None:
                return Response({
                    'error': 'Solo los lotes de farmacia central tienen lotes derivados',
                    'lote_id': lote.id,
                    'centro': lote.centro.nombre if lote.centro else None
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Nota: En Supabase no hay lote_origen, se simplifica
            # Los lotes derivados se manejan diferente
            derivados = Lote.objects.none()
            
            # Calcular totales
            total_derivados = 0
            stock_total_centros = 0
            
            derivados_data = []
            # Código original removido - lote_origen no existe en Supabase
            
            return Response({
                'lote_farmacia': {
                    'id': lote.id,
                    'numero_lote': lote.numero_lote,
                    'producto_clave': lote.producto.clave,
                    'producto_nombre': lote.producto.nombre,
                    'cantidad_actual': lote.cantidad_actual,
                    'fecha_caducidad': lote.fecha_caducidad
                },
                'resumen': {
                    'total_centros_con_stock': total_derivados,
                    'stock_total_en_centros': stock_total_centros,
                    'stock_farmacia': lote.cantidad_actual,
                    'stock_total_sistema': lote.cantidad_actual + stock_total_centros
                },
                'lotes_derivados': derivados_data
            })
            
        except Exception as e:
            # traceback removido por seguridad (ISS-008)
            return Response({
                'error': 'Error al obtener lotes derivados',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], url_path='trazabilidad')
    def trazabilidad_lote(self, request, pk=None):
        """
        Obtiene la trazabilidad completa de un lote:
        - Si es lote de farmacia: muestra derivados en centros
        - Si es lote de centro: muestra origen en farmacia
        """
        try:
            lote = self.get_object()
            
            result = {
                'lote': {
                    'id': lote.id,
                    'numero_lote': lote.numero_lote,
                    'producto_clave': lote.producto.clave,
                    'producto_descripcion': lote.producto.descripcion,
                    'cantidad_actual': lote.cantidad_actual,
                    'fecha_caducidad': lote.fecha_caducidad,
                    'es_lote_farmacia': lote.centro is None,
                    'ubicacion': lote.centro.nombre if lote.centro else 'Farmacia Central'
                },
                'origen': None,
                'derivados': []
            }
            
            # En Supabase no hay lote_origen - trazabilidad simplificada
            # Los lotes de cada centro son independientes
            
            # Movimientos relacionados
            movimientos = Movimiento.objects.filter(
                lote=lote
            ).select_related('requisicion', 'usuario', 'centro_origen', 'centro_destino').order_by('-fecha')[:20]
            
            result['movimientos'] = [{
                'id': m.id,
                'tipo': m.tipo,
                'cantidad': m.cantidad,
                'fecha': m.fecha,
                'requisicion_folio': m.requisicion.folio if m.requisicion else None,
                'observaciones': m.observaciones
            } for m in movimientos]
            
            return Response(result)
            
        except Exception as e:
            # traceback removido por seguridad (ISS-008)
            return Response({
                'error': 'Error al obtener trazabilidad',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # =========================================================================
    # ACCIONES DE DOCUMENTOS (facturas, contratos, remisiones)
    # =========================================================================
    
    @action(detail=True, methods=['get'], url_path='documentos')
    def listar_documentos(self, request, pk=None):
        """
        Lista todos los documentos asociados a un lote.
        """
        try:
            lote = self.get_object()
            documentos = LoteDocumento.objects.filter(lote=lote).order_by('-created_at')
            serializer = LoteDocumentoSerializer(documentos, many=True)
            return Response({
                'lote_id': lote.id,
                'numero_lote': lote.numero_lote,
                'total_documentos': documentos.count(),
                'documentos': serializer.data
            })
        except Exception as e:
            return Response({
                'error': 'Error al obtener documentos',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='subir-documento')
    def subir_documento(self, request, pk=None):
        """
        Sube un documento (PDF) asociado al lote.
        
        Campos requeridos:
        - documento: archivo PDF (multipart)
        - tipo_documento: factura/contrato/remision/otro
        
        Campos opcionales:
        - numero_documento: número del documento
        - fecha_documento: fecha del documento (YYYY-MM-DD)
        - notas: notas adicionales
        """
        try:
            lote = self.get_object()
            
            # Validar permisos de escritura
            user = request.user
            if not is_farmacia_or_admin(user):
                user_centro = get_user_centro(user)
                lote_centro = lote.centro
                if lote_centro is None or (user_centro and lote_centro.pk != user_centro.pk):
                    return Response(
                        {'error': 'No tiene permisos para subir documentos a este lote'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # ISS-005 FIX (audit7): Validar archivo PDF con función centralizada
            archivo = request.FILES.get('documento')
            if not archivo:
                return Response(
                    {'error': 'Debe proporcionar un archivo'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Usar validador centralizado que verifica extensión, tamaño Y magic bytes
            es_valido, error_msg = validar_archivo_pdf(archivo)
            if not es_valido:
                return Response(
                    {'error': error_msg},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validar tipo de documento
            tipo_documento = request.data.get('tipo_documento', 'otro')
            tipos_validos = ['factura', 'contrato', 'remision', 'otro']
            if tipo_documento not in tipos_validos:
                return Response(
                    {'error': f'Tipo de documento inválido. Valores permitidos: {tipos_validos}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Generar path único para el archivo
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            unique_name = f"{tipo_documento}_{timestamp}_{uuid.uuid4().hex[:8]}.pdf"
            archivo_path = f"lotes/documentos/{lote.id}/{unique_name}"
            
            # Guardar nombre del archivo original
            nombre_archivo = getattr(archivo, 'name', unique_name)
            
            # ISS-001 FIX: Subir archivo al almacenamiento ANTES de crear registro
            from inventario.services.storage_service import get_storage_service, StorageError
            
            storage = get_storage_service()
            upload_result = storage.upload_file(
                file_content=archivo,
                file_path=archivo_path,
                content_type='application/pdf',
                metadata={
                    'lote_id': lote.id,
                    'tipo_documento': tipo_documento,
                    'uploaded_by': user.username if user.is_authenticated else 'anonymous'
                }
            )
            
            # ISS-001 FIX: Si falla la subida, NO crear registro (rollback)
            if not upload_result.get('success'):
                logger.error(
                    f"ISS-001: Fallo subida documento lote {lote.id}: {upload_result.get('error')}"
                )
                return Response({
                    'error': 'Error al guardar archivo en almacenamiento',
                    'detalle': upload_result.get('error', 'Error desconocido')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Parsear fecha si viene
            fecha_documento = None
            if request.data.get('fecha_documento'):
                try:
                    fecha_documento = datetime.strptime(
                        request.data.get('fecha_documento'), '%Y-%m-%d'
                    ).date()
                except ValueError:
                    pass
            
            # ISS-001 FIX: Solo crear registro si la subida fue exitosa
            try:
                documento = LoteDocumento.objects.create(
                    lote=lote,
                    tipo_documento=tipo_documento,
                    numero_documento=request.data.get('numero_documento', ''),
                    archivo=archivo_path,
                    nombre_archivo=nombre_archivo,
                    fecha_documento=fecha_documento,
                    notas=request.data.get('notas', ''),
                    created_by=user if user.is_authenticated else None
                )
            except Exception as db_error:
                # ISS-001 FIX: Si falla crear registro, eliminar archivo subido (rollback)
                logger.error(f"ISS-001: Error BD, revirtiendo subida: {db_error}")
                storage.delete_file(archivo_path)
                raise
            
            logger.info(
                f"ISS-001: Documento subido exitosamente - Lote: {lote.id}, "
                f"Path: {archivo_path}, Storage: {upload_result.get('storage')}"
            )
            
            serializer = LoteDocumentoSerializer(documento)
            return Response({
                'mensaje': 'Documento subido correctamente',
                'documento': serializer.data,
                'storage_info': {
                    'path': archivo_path,
                    'url': upload_result.get('url'),
                    'storage_type': upload_result.get('storage')
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'error': 'Error al subir documento',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['delete'], url_path='eliminar-documento/(?P<doc_id>[0-9]+)')
    def eliminar_documento(self, request, pk=None, doc_id=None):
        """
        Elimina un documento específico del lote.
        """
        try:
            lote = self.get_object()
            
            # Validar permisos de escritura
            user = request.user
            if not is_farmacia_or_admin(user):
                user_centro = get_user_centro(user)
                lote_centro = lote.centro
                if lote_centro is None or (user_centro and lote_centro.pk != user_centro.pk):
                    return Response(
                        {'error': 'No tiene permisos para eliminar documentos de este lote'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # Buscar documento
            try:
                documento = LoteDocumento.objects.get(id=doc_id, lote=lote)
            except LoteDocumento.DoesNotExist:
                return Response(
                    {'error': 'Documento no encontrado'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # ISS-002 FIX: Eliminar archivo del almacenamiento ANTES de borrar registro
            from inventario.services.storage_service import get_storage_service
            
            archivo_path = documento.archivo
            nombre = documento.nombre_archivo
            
            storage = get_storage_service()
            delete_result = storage.delete_file(archivo_path)
            
            # ISS-002 FIX: Registrar resultado de eliminación de storage
            if not delete_result.get('success'):
                logger.warning(
                    f"ISS-002: No se pudo eliminar archivo '{archivo_path}' del storage: "
                    f"{delete_result.get('error')}. Se eliminará el registro de BD igualmente."
                )
            else:
                logger.info(
                    f"ISS-002: Archivo eliminado de storage: {archivo_path}"
                )
            
            # Eliminar registro de BD
            documento.delete()
            
            logger.info(
                f"ISS-002: Documento eliminado - Lote: {lote.id}, "
                f"Archivo: {nombre}, Path: {archivo_path}"
            )
            
            return Response({
                'mensaje': 'Documento eliminado correctamente',
                'documento_eliminado': nombre,
                'storage_cleanup': delete_result.get('success', False)
            })
            
        except Exception as e:
            return Response({
                'error': 'Error al eliminar documento',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
