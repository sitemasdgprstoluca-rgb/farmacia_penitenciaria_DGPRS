"""
ISS-020: Validación de stock al crear/editar requisición.
ISS-024: Validación de inventario por centro en salidas.
ISS-026: Reconciliación de inventario.

Servicios de validación e integridad de inventario.
"""
import logging
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum, Q, F, Count
from django.utils import timezone

logger = logging.getLogger(__name__)


@dataclass
class StockValidationResult:
    """Resultado de validación de stock."""
    is_valid: bool
    producto_clave: str
    cantidad_requerida: int
    cantidad_disponible: int
    deficit: int = 0
    mensaje: str = ""
    ubicacion: str = "farmacia"  # 'farmacia' o nombre del centro
    

@dataclass  
class ReconciliacionResult:
    """Resultado de reconciliación de inventario."""
    lote_id: int
    numero_lote: str
    producto_clave: str
    stock_sistema: int
    stock_calculado: int
    diferencia: int
    estado: str  # 'ok', 'discrepancia', 'critico'
    movimientos_count: int


class StockValidationError(Exception):
    """Error de validación de stock."""
    def __init__(self, message: str, errores: List[StockValidationResult] = None):
        super().__init__(message)
        self.message = message
        self.errores = errores or []


class StockValidationService:
    """
    ISS-020: Servicio de validación de stock.
    
    Valida disponibilidad de stock antes de operaciones:
    - Crear/editar requisiciones
    - Surtir requisiciones  
    - Movimientos de salida
    """
    
    def __init__(self, centro=None):
        """
        Args:
            centro: Centro para el cual validar (None = farmacia central)
        """
        self.centro = centro
    
    def validar_stock_producto(
        self, 
        producto, 
        cantidad_requerida: int,
        excluir_lote_id: int = None
    ) -> StockValidationResult:
        """
        ISS-020: Valida stock disponible para un producto.
        
        Args:
            producto: Instancia de Producto
            cantidad_requerida: Cantidad que se necesita
            excluir_lote_id: ID de lote a excluir del cálculo
            
        Returns:
            StockValidationResult con el resultado
        """
        from core.models import Lote
        
        # Construir filtro de lotes disponibles
        filtro = Q(
            producto=producto,
            activo=True,
            cantidad_actual__gt=0
        )
        
        # Si hay centro, buscar en farmacia central + ese centro
        if self.centro:
            filtro &= (Q(centro__isnull=True) | Q(centro=self.centro))
        else:
            # Solo farmacia central
            filtro &= Q(centro__isnull=True)
        
        queryset = Lote.objects.filter(filtro)
        
        if excluir_lote_id:
            queryset = queryset.exclude(pk=excluir_lote_id)
        
        disponible = queryset.aggregate(total=Sum('cantidad_actual'))['total'] or 0
        
        ubicacion = self.centro.nombre if self.centro else "Farmacia Central"
        
        return StockValidationResult(
            is_valid=disponible >= cantidad_requerida,
            producto_clave=producto.clave,
            cantidad_requerida=cantidad_requerida,
            cantidad_disponible=disponible,
            deficit=max(0, cantidad_requerida - disponible),
            mensaje="" if disponible >= cantidad_requerida else (
                f"Stock insuficiente: {producto.clave} - "
                f"Requerido: {cantidad_requerida}, Disponible: {disponible}"
            ),
            ubicacion=ubicacion
        )
    
    def validar_requisicion(self, requisicion, solo_autorizados: bool = False) -> List[StockValidationResult]:
        """
        ISS-020: Valida stock para todos los items de una requisición.
        
        Args:
            requisicion: Instancia de Requisicion
            solo_autorizados: Si True, solo valida cantidades autorizadas
            
        Returns:
            Lista de StockValidationResult (errores)
        """
        self.centro = requisicion.centro
        errores = []
        
        for detalle in requisicion.detalles.select_related('producto'):
            if solo_autorizados:
                cantidad = detalle.cantidad_autorizada or 0
            else:
                cantidad = detalle.cantidad_solicitada
            
            # Restar lo ya surtido
            cantidad -= (detalle.cantidad_surtida or 0)
            
            if cantidad <= 0:
                continue
            
            resultado = self.validar_stock_producto(detalle.producto, cantidad)
            
            if not resultado.is_valid:
                errores.append(resultado)
        
        return errores
    
    def validar_detalles_requisicion(self, detalles_data: List[Dict]) -> List[StockValidationResult]:
        """
        ISS-020: Valida stock para detalles antes de crear requisición.
        
        Args:
            detalles_data: Lista de diccionarios con 'producto' y 'cantidad_solicitada'
            
        Returns:
            Lista de errores de validación
        """
        from core.models import Producto
        
        errores = []
        
        # Agrupar cantidades por producto (por si hay duplicados)
        productos_cantidades = {}
        for detalle in detalles_data:
            producto = detalle.get('producto')
            cantidad = detalle.get('cantidad_solicitada', 0)
            
            if isinstance(producto, int):
                producto = Producto.objects.get(pk=producto)
            
            if producto.pk in productos_cantidades:
                productos_cantidades[producto.pk]['cantidad'] += cantidad
            else:
                productos_cantidades[producto.pk] = {
                    'producto': producto,
                    'cantidad': cantidad
                }
        
        # Validar cada producto
        for data in productos_cantidades.values():
            resultado = self.validar_stock_producto(
                data['producto'], 
                data['cantidad']
            )
            if not resultado.is_valid:
                errores.append(resultado)
        
        return errores


class CentroInventoryValidator:
    """
    ISS-024: Validación de inventario por centro.
    
    Asegura que:
    - Los centros solo pueden operar con su propio inventario
    - Las salidas de un centro no afectan inventario de otros
    - La farmacia central puede operar globalmente
    """
    
    def __init__(self, usuario):
        """
        Args:
            usuario: Usuario que realiza la operación
        """
        self.usuario = usuario
        self.centro_usuario = getattr(usuario, 'centro', None)
        self.es_admin_o_farmacia = self._verificar_rol_privilegiado()
    
    def _verificar_rol_privilegiado(self) -> bool:
        """Verifica si el usuario tiene rol privilegiado."""
        if not self.usuario or not self.usuario.is_authenticated:
            return False
        if self.usuario.is_superuser:
            return True
        
        rol = (getattr(self.usuario, 'rol', '') or '').lower()
        return rol in ['admin', 'admin_sistema', 'farmacia', 'admin_farmacia', 'farmaceutico']
    
    def validar_acceso_lote(self, lote) -> Tuple[bool, str]:
        """
        ISS-024: Valida que el usuario puede acceder al lote.
        
        Args:
            lote: Instancia de Lote
            
        Returns:
            Tuple (es_valido, mensaje_error)
        """
        # Admins/Farmacia pueden acceder a todo
        if self.es_admin_o_farmacia:
            return True, ""
        
        # Usuario sin centro no puede operar
        if not self.centro_usuario:
            return False, "Usuario sin centro asignado no puede operar sobre lotes"
        
        lote_centro = getattr(lote, 'centro', None)
        
        # Lote de farmacia central (centro=None) - usuarios de centro NO pueden
        if lote_centro is None:
            return False, "No tiene permiso para operar sobre lotes de farmacia central"
        
        # Lote de otro centro
        if lote_centro.pk != self.centro_usuario.pk:
            return False, f"No tiene permiso para operar sobre lotes del centro {lote_centro.nombre}"
        
        return True, ""
    
    def validar_salida_lote(self, lote, cantidad: int) -> Tuple[bool, str]:
        """
        ISS-024: Valida una operación de salida de stock.
        
        Args:
            lote: Instancia de Lote
            cantidad: Cantidad a retirar
            
        Returns:
            Tuple (es_valido, mensaje_error)
        """
        # Primero validar acceso
        acceso_ok, error = self.validar_acceso_lote(lote)
        if not acceso_ok:
            return False, error
        
        # Validar stock suficiente
        if cantidad > lote.cantidad_actual:
            return False, f"Stock insuficiente: disponible {lote.cantidad_actual}, solicitado {cantidad}"
        
        # Validar estado del lote
        if lote.estado != 'disponible':
            return False, f"El lote no está disponible (estado: {lote.estado})"
        
        # Validar que no esté vencido (alerta_caducidad retorna 'vencido' si ya caducó)
        if lote.alerta_caducidad() == 'vencido':
            return False, "No se puede operar con lotes vencidos"
        
        return True, ""
    
    def get_lotes_disponibles_usuario(self, producto=None) -> 'QuerySet':
        """
        ISS-024: Retorna lotes accesibles para el usuario.
        
        Args:
            producto: Filtrar por producto (opcional)
            
        Returns:
            QuerySet de lotes accesibles
        """
        from core.models import Lote
        
        filtro = Q(
            activo=True,
            cantidad_actual__gt=0
        )
        
        if producto:
            filtro &= Q(producto=producto)
        
        # Filtrar por centro según rol
        if self.es_admin_o_farmacia:
            # Acceso global
            pass
        elif self.centro_usuario:
            # Solo su centro
            filtro &= Q(centro=self.centro_usuario)
        else:
            # Sin centro = sin acceso
            return Lote.objects.none()
        
        return Lote.objects.filter(filtro).select_related('producto', 'centro')


class InventoryReconciliationService:
    """
    ISS-026: Servicio de reconciliación de inventario.
    
    Detecta y reporta discrepancias entre:
    - Stock registrado en lotes vs calculado por movimientos
    - Inventario físico vs sistema (cuando se proporcione)
    """
    
    def __init__(self):
        self.tolerancia_porcentaje = 0.01  # 1% de tolerancia
    
    def reconciliar_lote(self, lote) -> ReconciliacionResult:
        """
        ISS-026: Reconcilia un lote individual.
        
        Calcula:
        - Stock según movimientos: cantidad_inicial + sum(movimientos)
        - Compara con cantidad_actual registrada
        
        Args:
            lote: Instancia de Lote
            
        Returns:
            ReconciliacionResult
        """
        from core.models import Movimiento
        
        # Stock actual en sistema
        stock_sistema = lote.cantidad_actual
        
        # Sumar todos los movimientos del lote
        movimientos = Movimiento.objects.filter(lote=lote)
        
        total_entradas = movimientos.filter(
            tipo='entrada'
        ).aggregate(total=Sum('cantidad'))['total'] or 0
        
        total_salidas = movimientos.filter(
            tipo='salida'
        ).aggregate(total=Sum('cantidad'))['total'] or 0
        
        # El campo cantidad de salida ya es negativo, así que sumamos todo
        movimientos_neto = total_entradas + total_salidas  # salidas son negativas
        
        # Stock calculado = inicial + movimientos netos
        # Pero en este sistema, la cantidad_inicial ya incluye la primera entrada
        # y los movimientos registran los cambios posteriores
        stock_calculado = lote.cantidad_inicial + movimientos_neto
        
        # Para lotes nuevos sin movimientos, el stock calculado = inicial
        if movimientos.count() == 0:
            stock_calculado = lote.cantidad_inicial
        
        diferencia = stock_sistema - stock_calculado
        abs_diferencia = abs(diferencia)
        
        # Determinar estado
        if diferencia == 0:
            estado = 'ok'
        elif abs_diferencia <= max(1, stock_sistema * self.tolerancia_porcentaje):
            estado = 'discrepancia'  # Dentro de tolerancia pero hay diferencia
        else:
            estado = 'critico'  # Fuera de tolerancia
        
        return ReconciliacionResult(
            lote_id=lote.pk,
            numero_lote=lote.numero_lote,
            producto_clave=lote.producto.clave,
            stock_sistema=stock_sistema,
            stock_calculado=stock_calculado,
            diferencia=diferencia,
            estado=estado,
            movimientos_count=movimientos.count()
        )
    
    def reconciliar_centro(self, centro=None) -> List[ReconciliacionResult]:
        """
        ISS-026: Reconcilia todos los lotes de un centro.
        
        Args:
            centro: Centro a reconciliar (None = farmacia central)
            
        Returns:
            Lista de ReconciliacionResult
        """
        from core.models import Lote
        
        if centro:
            lotes = Lote.objects.filter(centro=centro, activo=True)
        else:
            lotes = Lote.objects.filter(centro__isnull=True, activo=True)
        
        resultados = []
        for lote in lotes.select_related('producto'):
            resultado = self.reconciliar_lote(lote)
            resultados.append(resultado)
        
        return resultados
    
    def reconciliar_global(self, solo_discrepancias: bool = True) -> Dict[str, Any]:
        """
        ISS-026: Reconciliación global de todo el inventario.
        
        Args:
            solo_discrepancias: Si True, solo retorna lotes con problemas
            
        Returns:
            Dict con resumen y detalles
        """
        from core.models import Lote, Centro
        
        resultados_totales = []
        
        # Farmacia central
        resultados_totales.extend(self.reconciliar_centro(None))
        
        # Todos los centros
        for centro in Centro.objects.filter(activo=True):
            resultados_totales.extend(self.reconciliar_centro(centro))
        
        # Filtrar si solo queremos discrepancias
        if solo_discrepancias:
            resultados_filtrados = [r for r in resultados_totales if r.estado != 'ok']
        else:
            resultados_filtrados = resultados_totales
        
        # Calcular resumen
        total_lotes = len(resultados_totales)
        lotes_ok = sum(1 for r in resultados_totales if r.estado == 'ok')
        lotes_discrepancia = sum(1 for r in resultados_totales if r.estado == 'discrepancia')
        lotes_critico = sum(1 for r in resultados_totales if r.estado == 'critico')
        
        return {
            'fecha_reconciliacion': timezone.now().isoformat(),
            'resumen': {
                'total_lotes': total_lotes,
                'lotes_ok': lotes_ok,
                'lotes_discrepancia': lotes_discrepancia,
                'lotes_critico': lotes_critico,
                'porcentaje_integridad': round(lotes_ok / total_lotes * 100, 2) if total_lotes > 0 else 100
            },
            'detalles': [
                {
                    'lote_id': r.lote_id,
                    'numero_lote': r.numero_lote,
                    'producto': r.producto_clave,
                    'stock_sistema': r.stock_sistema,
                    'stock_calculado': r.stock_calculado,
                    'diferencia': r.diferencia,
                    'estado': r.estado,
                    'movimientos': r.movimientos_count
                }
                for r in resultados_filtrados
            ]
        }
    
    @transaction.atomic
    def corregir_discrepancia(self, lote, nuevo_stock: int, motivo: str, usuario) -> bool:
        """
        ISS-026: Corrige una discrepancia de stock.
        
        Crea un movimiento de ajuste para igualar el stock.
        
        Args:
            lote: Lote a corregir
            nuevo_stock: Stock correcto
            motivo: Motivo del ajuste
            usuario: Usuario que realiza el ajuste
            
        Returns:
            bool: True si se corrigió
        """
        from core.models import Movimiento, Lote as LoteModel
        
        diferencia = nuevo_stock - lote.cantidad_actual
        
        if diferencia == 0:
            return False
        
        # Bloquear lote
        lote_locked = LoteModel.objects.select_for_update().get(pk=lote.pk)
        stock_anterior = lote_locked.cantidad_actual
        
        # Crear movimiento de ajuste
        movimiento = Movimiento(
            tipo='ajuste',
            producto=lote_locked.producto,  # Campo requerido en BD
            lote=lote_locked,
            centro_origen=lote_locked.centro,
            cantidad=diferencia,
            usuario=usuario,
            motivo=f"ISS-026 Reconciliación: {motivo}. Stock anterior: {stock_anterior}"
        )
        movimiento._stock_pre_movimiento = stock_anterior
        # HALLAZGO #1 FIX: Actualización de stock se hace manualmente abajo
        movimiento.save(skip_stock_update=True)
        
        # Actualizar stock
        lote_locked.cantidad_actual = nuevo_stock
        if nuevo_stock == 0:
            lote_locked.activo = False
        elif not lote_locked.activo and nuevo_stock > 0:
            lote_locked.activo = True
        lote_locked.save(update_fields=['cantidad_actual', 'activo', 'updated_at'])
        
        logger.info(
            f"ISS-026: Discrepancia corregida en lote {lote.numero_lote}. "
            f"Stock: {stock_anterior} → {nuevo_stock} (diferencia: {diferencia})"
        )
        
        return True


# =============================================================================
# Funciones de conveniencia
# =============================================================================

def validar_stock_para_requisicion(requisicion, solo_autorizados: bool = False) -> List[Dict]:
    """
    Valida stock para una requisición.
    
    ISS-FIX: Las requisiciones se surten desde FARMACIA CENTRAL, por lo que
    la validación de stock debe ser contra centro=None (farmacia central).
    No usamos requisicion.centro porque es alias de centro_destino.
    
    Returns:
        Lista de errores (vacía si válido)
    """
    # ISS-FIX: Siempre validar contra farmacia central (None) porque
    # las requisiciones se surten desde ahí, independientemente del centro_origen
    validator = StockValidationService(None)
    errores = validator.validar_requisicion(requisicion, solo_autorizados)
    
    return [
        {
            'producto': e.producto_clave,
            'requerido': e.cantidad_requerida,
            'disponible': e.cantidad_disponible,
            'deficit': e.deficit,
            'mensaje': e.mensaje
        }
        for e in errores
    ]


def validar_acceso_lote_usuario(usuario, lote) -> Tuple[bool, str]:
    """
    Valida que un usuario puede acceder a un lote.
    
    Returns:
        Tuple (es_valido, mensaje_error)
    """
    validator = CentroInventoryValidator(usuario)
    return validator.validar_acceso_lote(lote)


def reconciliar_inventario(centro=None, global_: bool = False, solo_discrepancias: bool = True) -> Dict:
    """
    Ejecuta reconciliación de inventario.
    
    Args:
        centro: Centro específico (None = farmacia central)
        global_: Si True, reconcilia todo el sistema
        solo_discrepancias: Si True, solo retorna problemas
        
    Returns:
        Dict con resultados
    """
    service = InventoryReconciliationService()
    
    if global_:
        return service.reconciliar_global(solo_discrepancias)
    
    resultados = service.reconciliar_centro(centro)
    
    if solo_discrepancias:
        resultados = [r for r in resultados if r.estado != 'ok']
    
    return {
        'centro': centro.nombre if centro else 'Farmacia Central',
        'total_lotes': len(resultados),
        'detalles': [
            {
                'lote_id': r.lote_id,
                'numero_lote': r.numero_lote,
                'producto': r.producto_clave,
                'stock_sistema': r.stock_sistema,
                'stock_calculado': r.stock_calculado,
                'diferencia': r.diferencia,
                'estado': r.estado
            }
            for r in resultados
        ]
    }


# =============================================================================
# ISS-021 FIX (audit9): Funciones centralizadas de cálculo de stock
# =============================================================================

def calcular_stock_producto(producto, centro=None, solo_vigentes=True, incluir_comprometido=False):
    """
    ISS-021 FIX (audit9): Función centralizada para calcular stock de un producto.
    
    USAR ESTA FUNCIÓN en lugar de queries inline para evitar duplicación
    y garantizar consistencia en el cálculo de stock.
    
    Args:
        producto: Instancia de Producto o ID
        centro: Centro para filtrar (None = farmacia central)
        solo_vigentes: Si True, excluye lotes vencidos
        incluir_comprometido: Si True, resta stock comprometido por requisiciones
        
    Returns:
        dict: {
            'stock_total': int,
            'stock_disponible': int,  # stock_total - comprometido
            'stock_comprometido': int,
            'lotes_count': int,
            'lotes_vigentes': int,
            'lotes_vencidos': int,
            'detalle_lotes': list
        }
    """
    from django.db.models import Sum, Q, Value
    from django.db.models.functions import Coalesce
    from django.utils import timezone
    from core.models import Lote, Producto, DetalleRequisicion
    from core.constants import ESTADOS_COMPROMETIDOS
    
    hoy = timezone.now().date()
    
    # Normalizar producto
    if isinstance(producto, int):
        producto = Producto.objects.get(pk=producto)
    
    # Construir filtro base
    filtro = Q(producto=producto, activo=True, cantidad_actual__gt=0)
    
    # Filtrar por centro
    if centro is None:
        filtro &= Q(centro__isnull=True)  # Farmacia central
    else:
        filtro &= Q(centro=centro)
    
    # Query de lotes
    lotes_query = Lote.objects.filter(filtro)
    
    # Separar vigentes y vencidos
    lotes_vigentes_query = lotes_query.filter(fecha_caducidad__gte=hoy)
    lotes_vencidos_query = lotes_query.filter(fecha_caducidad__lt=hoy)
    
    lotes_vigentes_count = lotes_vigentes_query.count()
    lotes_vencidos_count = lotes_vencidos_query.count()
    
    # Calcular stock según parámetros
    if solo_vigentes:
        stock_total = lotes_vigentes_query.aggregate(
            total=Coalesce(Sum('cantidad_actual'), Value(0))
        )['total']
    else:
        stock_total = lotes_query.aggregate(
            total=Coalesce(Sum('cantidad_actual'), Value(0))
        )['total']
    
    # Calcular comprometido
    stock_comprometido = 0
    if incluir_comprometido:
        resultado_comprometido = DetalleRequisicion.objects.filter(
            requisicion__estado__in=ESTADOS_COMPROMETIDOS,
            producto=producto
        ).aggregate(
            total_autorizado=Coalesce(Sum('cantidad_autorizada'), Value(0)),
            total_surtido=Coalesce(Sum('cantidad_surtida'), Value(0))
        )
        stock_comprometido = max(0, 
            resultado_comprometido['total_autorizado'] - resultado_comprometido['total_surtido']
        )
    
    stock_disponible = stock_total - stock_comprometido
    
    # Detalle de lotes (opcional, para debugging)
    detalle_lotes = []
    for lote in lotes_query.select_related('producto')[:10]:  # Limitar a 10
        detalle_lotes.append({
            'id': lote.pk,
            'numero_lote': lote.numero_lote,
            'cantidad': lote.cantidad_actual,
            'fecha_caducidad': str(lote.fecha_caducidad),
            'vigente': lote.fecha_caducidad >= hoy,
        })
    
    return {
        'stock_total': stock_total,
        'stock_disponible': max(0, stock_disponible),
        'stock_comprometido': stock_comprometido,
        'lotes_count': lotes_vigentes_count + lotes_vencidos_count,
        'lotes_vigentes': lotes_vigentes_count,
        'lotes_vencidos': lotes_vencidos_count,
        'detalle_lotes': detalle_lotes,
    }


def calcular_stock_batch(producto_ids, centro=None, solo_vigentes=True, incluir_comprometido=False):
    """
    ISS-021 FIX (audit9): Calcula stock para múltiples productos en una operación eficiente.
    
    Optimizado para evitar N+1 queries usando agregaciones batch.
    
    Args:
        producto_ids: Lista de IDs de productos
        centro: Centro para filtrar (None = farmacia central)
        solo_vigentes: Si True, excluye lotes vencidos
        incluir_comprometido: Si True, resta stock comprometido
        
    Returns:
        dict: {producto_id: stock_info, ...}
    """
    from django.db.models import Sum, Q, Value
    from django.db.models.functions import Coalesce
    from django.utils import timezone
    from core.models import Lote, DetalleRequisicion
    from core.constants import ESTADOS_COMPROMETIDOS
    
    hoy = timezone.now().date()
    
    # Filtro base para todos los productos
    filtro = Q(producto_id__in=producto_ids, activo=True, cantidad_actual__gt=0)
    
    if centro is None:
        filtro &= Q(centro__isnull=True)
    else:
        filtro &= Q(centro=centro)
    
    if solo_vigentes:
        filtro &= Q(fecha_caducidad__gte=hoy)
    
    # Query batch de stock por producto
    stock_por_producto = {
        item['producto_id']: item['total']
        for item in Lote.objects.filter(filtro).values('producto_id').annotate(
            total=Coalesce(Sum('cantidad_actual'), Value(0))
        )
    }
    
    # Query batch de comprometido
    comprometido_por_producto = {}
    if incluir_comprometido:
        resultado = DetalleRequisicion.objects.filter(
            requisicion__estado__in=ESTADOS_COMPROMETIDOS,
            producto_id__in=producto_ids
        ).values('producto_id').annotate(
            total_autorizado=Coalesce(Sum('cantidad_autorizada'), Value(0)),
            total_surtido=Coalesce(Sum('cantidad_surtida'), Value(0))
        )
        comprometido_por_producto = {
            item['producto_id']: max(0, item['total_autorizado'] - item['total_surtido'])
            for item in resultado
        }
    
    # Construir resultado
    result = {}
    for pid in producto_ids:
        stock_total = stock_por_producto.get(pid, 0)
        stock_comprometido = comprometido_por_producto.get(pid, 0)
        result[pid] = {
            'stock_total': stock_total,
            'stock_disponible': max(0, stock_total - stock_comprometido),
            'stock_comprometido': stock_comprometido,
        }
    
    return result
