"""
ISS-017: Filtrado de reportes por permisos.
ISS-033: Optimización de queries N+1.

Sistema de reportes con filtrado por permisos de usuario
y optimización de consultas.
"""
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any, Callable
from functools import wraps

from django.db import models
from django.db.models import Q, Sum, Count, F, Prefetch
from django.db.models.functions import Coalesce, TruncDate, TruncMonth
from django.core.cache import cache

logger = logging.getLogger(__name__)


# =============================================================================
# ISS-033: Optimizador de Queries
# =============================================================================

class QueryOptimizer:
    """
    ISS-033: Optimizador de queries para evitar problemas N+1.
    
    Provee métodos para construir querysets optimizados con
    select_related y prefetch_related apropiados.
    """
    
    # Configuración de relaciones por modelo
    RELACIONES_SELECT = {
        'Requisicion': ['centro_destino', 'centro_origen', 'solicitante', 'autorizador', 'usuario_firma_recepcion'],
        'DetalleRequisicion': ['requisicion', 'producto', 'lote'],
        'Movimiento': ['lote', 'centro_origen', 'centro_destino', 'usuario', 'requisicion', 'lote__producto'],
        'Lote': ['producto', 'centro'],
        'Producto': [],
        'User': ['centro'],
    }
    
    RELACIONES_PREFETCH = {
        'Requisicion': ['detalles', 'detalles__producto', 'detalles__lote'],
        'Centro': ['requisiciones', 'lotes', 'usuarios'],
        'Producto': ['lotes'],
    }
    
    @classmethod
    def optimizar_queryset(
        cls,
        queryset,
        modelo: str,
        incluir_prefetch: bool = True,
        relaciones_extra: Optional[List[str]] = None
    ):
        """
        ISS-033: Optimiza un queryset aplicando select_related y prefetch_related.
        
        Args:
            queryset: QuerySet a optimizar
            modelo: Nombre del modelo
            incluir_prefetch: Si incluir prefetch_related
            relaciones_extra: Relaciones adicionales a incluir
        
        Returns:
            QuerySet optimizado
        """
        # Aplicar select_related
        select_rels = cls.RELACIONES_SELECT.get(modelo, [])
        if relaciones_extra:
            select_rels = list(set(select_rels + [r for r in relaciones_extra if '__' not in r or r.count('__') == 1]))
        
        if select_rels:
            queryset = queryset.select_related(*select_rels)
        
        # Aplicar prefetch_related
        if incluir_prefetch:
            prefetch_rels = cls.RELACIONES_PREFETCH.get(modelo, [])
            if prefetch_rels:
                queryset = queryset.prefetch_related(*prefetch_rels)
        
        return queryset
    
    @classmethod
    def requisiciones_optimizadas(cls, queryset=None):
        """
        ISS-033: Queryset optimizado para requisiciones.
        
        Returns:
            QuerySet optimizado
        """
        from core.models import Requisicion, DetalleRequisicion
        
        if queryset is None:
            queryset = Requisicion.objects.all()
        
        return queryset.select_related(
            'centro_destino',
            'centro_origen',
            'solicitante',
            'autorizador',
            'usuario_firma_recepcion'
        ).prefetch_related(
            Prefetch(
                'detalles',
                queryset=DetalleRequisicion.objects.select_related('producto', 'lote')
            )
        )
    
    @classmethod
    def movimientos_optimizados(cls, queryset=None):
        """
        ISS-033: Queryset optimizado para movimientos.
        
        Returns:
            QuerySet optimizado
        """
        from core.models import Movimiento
        
        if queryset is None:
            queryset = Movimiento.objects.all()
        
        return queryset.select_related(
            'lote',
            'lote__producto',
            'lote__centro',
            'centro',
            'usuario',
            'requisicion'
        )
    
    @classmethod
    def lotes_optimizados(cls, queryset=None):
        """
        ISS-033: Queryset optimizado para lotes.
        
        Returns:
            QuerySet optimizado
        """
        from core.models import Lote
        
        if queryset is None:
            queryset = Lote.objects.all()
        
        return queryset.select_related(
            'producto',
            'centro'
        )


# =============================================================================
# ISS-017: Filtrado de Reportes por Permisos
# =============================================================================

@dataclass
class FiltroReporte:
    """Configuración de filtros para un reporte."""
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    centro_id: Optional[int] = None
    producto_id: Optional[int] = None
    usuario_id: Optional[int] = None
    estado: Optional[str] = None
    tipo: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


class ReportPermissionFilter:
    """
    ISS-017: Filtrado de reportes basado en permisos de usuario.
    
    Aplica filtros automáticos según el rol del usuario:
    - Admin/Farmacia: Ve todos los datos
    - Centro: Solo datos de su centro
    - Vista: Solo lectura de datos permitidos
    """
    
    ROLES_ADMIN = {'admin', 'admin_sistema', 'superusuario', 'farmacia', 'admin_farmacia'}
    ROLES_VISTA = {'vista'}
    
    def __init__(self, usuario):
        """
        Inicializa el filtro con el usuario actual.
        
        Args:
            usuario: Usuario autenticado
        """
        self.usuario = usuario
        self.es_admin = self._es_admin()
        self.es_vista = self._es_vista()
        self.centro_usuario = getattr(usuario, 'centro_id', None)
    
    def _es_admin(self) -> bool:
        """Verifica si el usuario tiene rol admin."""
        if not self.usuario or not self.usuario.is_authenticated:
            return False
        if self.usuario.is_superuser:
            return True
        rol = (getattr(self.usuario, 'rol', '') or '').lower()
        return rol in self.ROLES_ADMIN
    
    def _es_vista(self) -> bool:
        """Verifica si el usuario tiene rol vista."""
        rol = (getattr(self.usuario, 'rol', '') or '').lower()
        return rol in self.ROLES_VISTA
    
    def aplicar_filtro_centro(self, queryset, campo_centro: str = 'centro'):
        """
        ISS-017: Aplica filtro de centro según permisos del usuario.
        
        Args:
            queryset: QuerySet a filtrar
            campo_centro: Nombre del campo de centro en el modelo
        
        Returns:
            QuerySet filtrado
        """
        # Admin y Vista ven todo
        if self.es_admin or self.es_vista:
            return queryset
        
        # Usuario de centro solo ve su centro
        if self.centro_usuario:
            filtro = {campo_centro: self.centro_usuario}
            return queryset.filter(**filtro)
        
        # Sin centro, ve solo sus propios registros si aplica
        return queryset.none()
    
    def filtrar_requisiciones(self, queryset=None, filtros: Optional[FiltroReporte] = None):
        """
        ISS-017: Filtra requisiciones según permisos.
        
        Args:
            queryset: QuerySet base (opcional)
            filtros: Filtros adicionales
        
        Returns:
            QuerySet filtrado y optimizado
        """
        from core.models import Requisicion
        
        if queryset is None:
            queryset = Requisicion.objects.all()
        
        # ISS-033: Optimizar queryset
        queryset = QueryOptimizer.requisiciones_optimizadas(queryset)
        
        # ISS-017: Aplicar filtro de centro
        queryset = self.aplicar_filtro_centro(queryset)
        
        # Aplicar filtros adicionales
        if filtros:
            if filtros.fecha_inicio:
                queryset = queryset.filter(fecha_solicitud__date__gte=filtros.fecha_inicio)
            if filtros.fecha_fin:
                queryset = queryset.filter(fecha_solicitud__date__lte=filtros.fecha_fin)
            if filtros.estado:
                queryset = queryset.filter(estado=filtros.estado)
            if filtros.producto_id:
                queryset = queryset.filter(detalles__producto_id=filtros.producto_id).distinct()
        
        return queryset
    
    def filtrar_movimientos(self, queryset=None, filtros: Optional[FiltroReporte] = None):
        """
        ISS-017: Filtra movimientos según permisos.
        
        Args:
            queryset: QuerySet base (opcional)
            filtros: Filtros adicionales
        
        Returns:
            QuerySet filtrado y optimizado
        """
        from core.models import Movimiento
        
        if queryset is None:
            queryset = Movimiento.objects.all()
        
        # ISS-033: Optimizar queryset
        queryset = QueryOptimizer.movimientos_optimizados(queryset)
        
        # ISS-017: Aplicar filtro de centro
        # Movimientos pueden estar en lote.centro o en campo centro
        if not self.es_admin and not self.es_vista and self.centro_usuario:
            queryset = queryset.filter(
                Q(centro_id=self.centro_usuario) | 
                Q(lote__centro_id=self.centro_usuario)
            )
        
        # Aplicar filtros adicionales
        if filtros:
            if filtros.fecha_inicio:
                queryset = queryset.filter(fecha__date__gte=filtros.fecha_inicio)
            if filtros.fecha_fin:
                queryset = queryset.filter(fecha__date__lte=filtros.fecha_fin)
            if filtros.tipo:
                queryset = queryset.filter(tipo=filtros.tipo)
            if filtros.producto_id:
                queryset = queryset.filter(lote__producto_id=filtros.producto_id)
            if filtros.centro_id:
                queryset = queryset.filter(
                    Q(centro_id=filtros.centro_id) | 
                    Q(lote__centro_id=filtros.centro_id)
                )
        
        return queryset
    
    def filtrar_lotes(self, queryset=None, filtros: Optional[FiltroReporte] = None):
        """
        ISS-017: Filtra lotes según permisos.
        
        Args:
            queryset: QuerySet base (opcional)
            filtros: Filtros adicionales
        
        Returns:
            QuerySet filtrado y optimizado
        """
        from core.models import Lote
        
        if queryset is None:
            queryset = Lote.objects.filter(activo=True)
        
        # ISS-033: Optimizar queryset
        queryset = QueryOptimizer.lotes_optimizados(queryset)
        
        # ISS-017: Aplicar filtro de centro
        if not self.es_admin and not self.es_vista and self.centro_usuario:
            # Usuario de centro ve lotes de su centro + farmacia central
            queryset = queryset.filter(
                Q(centro_id=self.centro_usuario) | Q(centro__isnull=True)
            )
        
        # Aplicar filtros adicionales
        if filtros:
            if filtros.producto_id:
                queryset = queryset.filter(producto_id=filtros.producto_id)
            if filtros.centro_id:
                queryset = queryset.filter(centro_id=filtros.centro_id)
        
        return queryset


# =============================================================================
# Generador de Reportes Optimizados
# =============================================================================

class ReportGenerator:
    """
    ISS-017, ISS-033: Generador de reportes optimizado con filtrado por permisos.
    """
    
    def __init__(self, usuario):
        """
        Inicializa el generador.
        
        Args:
            usuario: Usuario autenticado
        """
        self.usuario = usuario
        self.permission_filter = ReportPermissionFilter(usuario)
    
    def reporte_inventario_por_centro(
        self,
        centro_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        ISS-017, ISS-033: Genera reporte de inventario por centro.
        
        Args:
            centro_id: ID del centro específico (opcional)
        
        Returns:
            Dict con datos del reporte
        """
        from core.models import Lote, Centro
        
        filtros = FiltroReporte(centro_id=centro_id)
        lotes = self.permission_filter.filtrar_lotes(filtros=filtros)
        
        # Agrupar por centro y producto
        resumen = lotes.values(
            'centro__nombre',
            'producto__clave',
            'producto__descripcion'
        ).annotate(
            cantidad_total=Sum('cantidad_actual'),
            lotes_count=Count('id')
        ).order_by('centro__nombre', 'producto__descripcion')
        
        return {
            'tipo': 'inventario_por_centro',
            'fecha_generacion': datetime.now().isoformat(),
            'usuario': self.usuario.username,
            'filtros': filtros.to_dict(),
            'datos': list(resumen),
            'total_lotes': lotes.count(),
        }
    
    def reporte_movimientos_periodo(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        tipo: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        ISS-017, ISS-033: Genera reporte de movimientos por período.
        
        Args:
            fecha_inicio: Fecha de inicio
            fecha_fin: Fecha de fin
            tipo: Tipo de movimiento (opcional)
        
        Returns:
            Dict con datos del reporte
        """
        from core.models import Movimiento
        
        filtros = FiltroReporte(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            tipo=tipo
        )
        movimientos = self.permission_filter.filtrar_movimientos(filtros=filtros)
        
        # Resumen por tipo
        resumen_tipo = movimientos.values('tipo').annotate(
            cantidad_total=Sum('cantidad'),
            count=Count('id')
        )
        
        # Resumen por día
        resumen_diario = movimientos.annotate(
            dia=TruncDate('fecha')
        ).values('dia').annotate(
            entradas=Sum('cantidad', filter=Q(tipo='entrada')),
            salidas=Sum('cantidad', filter=Q(tipo='salida')),
            ajustes=Sum('cantidad', filter=Q(tipo='ajuste'))
        ).order_by('dia')
        
        return {
            'tipo': 'movimientos_periodo',
            'fecha_generacion': datetime.now().isoformat(),
            'usuario': self.usuario.username,
            'filtros': filtros.to_dict(),
            'resumen_tipo': list(resumen_tipo),
            'resumen_diario': list(resumen_diario),
            'total_movimientos': movimientos.count(),
        }
    
    def reporte_requisiciones_estado(
        self,
        fecha_inicio: Optional[date] = None,
        fecha_fin: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        ISS-017, ISS-033: Genera reporte de requisiciones por estado.
        
        Args:
            fecha_inicio: Fecha de inicio (opcional)
            fecha_fin: Fecha de fin (opcional)
        
        Returns:
            Dict con datos del reporte
        """
        from core.models import Requisicion
        
        filtros = FiltroReporte(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        requisiciones = self.permission_filter.filtrar_requisiciones(filtros=filtros)
        
        # Resumen por estado
        resumen_estado = requisiciones.values('estado').annotate(
            count=Count('id')
        ).order_by('estado')
        
        # Resumen por centro
        resumen_centro = requisiciones.values(
            'centro__nombre'
        ).annotate(
            count=Count('id'),
            pendientes=Count('id', filter=Q(estado__in=['borrador', 'enviada'])),
            completadas=Count('id', filter=Q(estado='recibida'))
        ).order_by('centro__nombre')
        
        return {
            'tipo': 'requisiciones_estado',
            'fecha_generacion': datetime.now().isoformat(),
            'usuario': self.usuario.username,
            'filtros': filtros.to_dict(),
            'resumen_estado': list(resumen_estado),
            'resumen_centro': list(resumen_centro),
            'total_requisiciones': requisiciones.count(),
        }


# =============================================================================
# Decoradores de optimización
# =============================================================================

def optimizar_query(modelo: str):
    """
    ISS-033: Decorador para optimizar queries automáticamente.
    
    Uso:
        @optimizar_query('Requisicion')
        def mi_vista(self, request):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            # Si es un queryset, optimizarlo
            if hasattr(result, 'query'):
                return QueryOptimizer.optimizar_queryset(result, modelo)
            return result
        return wrapper
    return decorator


def filtrar_por_permisos(campo_centro: str = 'centro'):
    """
    ISS-017: Decorador para filtrar por permisos automáticamente.
    
    Uso:
        @filtrar_por_permisos('centro')
        def get_queryset(self):
            return MiModelo.objects.all()
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            queryset = func(self, *args, **kwargs)
            
            # Obtener usuario del request
            request = getattr(self, 'request', None)
            if request and hasattr(request, 'user'):
                filter = ReportPermissionFilter(request.user)
                return filter.aplicar_filtro_centro(queryset, campo_centro)
            
            return queryset
        return wrapper
    return decorator
