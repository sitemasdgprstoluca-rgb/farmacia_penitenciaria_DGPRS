"""
ISS-001/ISS-004 FIX: Helpers centralizados para consultas de lotes.

Este módulo proporciona métodos seguros para consultar lotes sin usar
el campo 'estado' que es una propiedad calculada (NO existe en BD).

IMPORTANTE: La tabla 'lotes' en BD NO tiene campo 'estado'.
La disponibilidad se determina por: activo=True AND cantidad_actual>0 AND fecha_caducidad>=hoy

USO:
    from core.lote_helpers import LoteQueryHelper
    
    # Obtener queryset de lotes disponibles
    lotes = LoteQueryHelper.get_lotes_disponibles(producto=producto)
    
    # Validar stock para surtido
    errores = LoteQueryHelper.validar_stock_surtido(producto, cantidad, centro=None)

Ver también: docs/SQL_MIGRATIONS.md, ISS-001 en ARQUITECTURA.md
"""
from django.db.models import Sum, Q, QuerySet
from django.utils import timezone
from datetime import timedelta
from typing import Optional, List, Dict, Any, Union
import logging

logger = logging.getLogger(__name__)


class LoteQueryHelper:
    """
    ISS-001/ISS-004 FIX: Helper centralizado para consultas seguras de lotes.
    
    NUNCA usa 'estado' como campo de filtro (es propiedad calculada).
    Usa los campos reales de BD: activo, cantidad_actual, fecha_caducidad.
    """
    
    # Días de anticipación para alertas de vencimiento próximo
    DIAS_ALERTA_VENCIMIENTO = 30
    DIAS_ALERTA_CRITICA = 90
    
    @staticmethod
    def get_lotes_disponibles(
        producto=None,
        centro=None,
        solo_farmacia_central: bool = False,
        incluir_proximos_vencer: bool = True,
        ordenar_fefo: bool = True,
        cantidad_minima: int = 0,
    ) -> QuerySet:
        """
        ISS-001 FIX: Retorna QuerySet de lotes disponibles para surtido.
        
        FILTROS APLICADOS (equivalente a estado='disponible'):
        - activo=True
        - cantidad_actual > cantidad_minima
        - fecha_caducidad >= hoy
        
        Args:
            producto: Producto específico (opcional, puede ser ID o instancia)
            centro: Centro específico (opcional, puede ser ID o instancia)
            solo_farmacia_central: Si True, solo lotes sin centro (farmacia central)
            incluir_proximos_vencer: Si True, incluye lotes próximos a vencer
            ordenar_fefo: Si True, ordena por fecha de caducidad (FEFO)
            cantidad_minima: Cantidad mínima requerida en el lote
            
        Returns:
            QuerySet de Lote filtrado
        """
        from core.models import Lote
        
        hoy = timezone.now().date()
        
        filtros = {
            'activo': True,
            'cantidad_actual__gt': cantidad_minima,
            'fecha_caducidad__gte': hoy,
        }
        
        # Filtrar por producto
        if producto:
            producto_id = producto.id if hasattr(producto, 'id') else producto
            filtros['producto_id'] = producto_id
        
        # Filtrar por centro
        if solo_farmacia_central:
            filtros['centro__isnull'] = True
        elif centro:
            centro_id = centro.id if hasattr(centro, 'id') else centro
            filtros['centro_id'] = centro_id
        
        queryset = Lote.objects.filter(**filtros)
        
        if ordenar_fefo:
            queryset = queryset.order_by('fecha_caducidad', '-cantidad_actual')
        
        return queryset
    
    @staticmethod
    def get_stock_disponible(
        producto,
        centro=None,
        solo_farmacia_central: bool = False,
    ) -> int:
        """
        ISS-001 FIX: Calcula stock total disponible para un producto.
        
        Args:
            producto: Producto (ID o instancia)
            centro: Centro específico (opcional)
            solo_farmacia_central: Si True, solo cuenta farmacia central
            
        Returns:
            int: Cantidad total disponible
        """
        lotes = LoteQueryHelper.get_lotes_disponibles(
            producto=producto,
            centro=centro,
            solo_farmacia_central=solo_farmacia_central,
        )
        
        return lotes.aggregate(total=Sum('cantidad_actual'))['total'] or 0
    
    @staticmethod
    def validar_stock_surtido(
        producto,
        cantidad_requerida: int,
        centro=None,
        solo_farmacia_central: bool = True,
    ) -> Dict[str, Any]:
        """
        ISS-001 FIX: Valida si hay stock suficiente para surtir una cantidad.
        
        Args:
            producto: Producto a validar
            cantidad_requerida: Cantidad que se necesita surtir
            centro: Centro específico (opcional)
            solo_farmacia_central: Si True, solo valida farmacia central
            
        Returns:
            dict: {
                'valido': bool,
                'stock_disponible': int,
                'faltante': int,
                'lotes': list de dicts con info de lotes,
                'errores': list de strings,
                'advertencias': list de strings
            }
        """
        lotes = LoteQueryHelper.get_lotes_disponibles(
            producto=producto,
            centro=centro,
            solo_farmacia_central=solo_farmacia_central,
        )
        
        stock_disponible = lotes.aggregate(total=Sum('cantidad_actual'))['total'] or 0
        hoy = timezone.now().date()
        limite_vencimiento = hoy + timedelta(days=LoteQueryHelper.DIAS_ALERTA_VENCIMIENTO)
        
        # Construir lista de lotes con info
        lotes_info = []
        for lote in lotes.values('id', 'numero_lote', 'cantidad_actual', 'fecha_caducidad'):
            lotes_info.append({
                'id': lote['id'],
                'numero_lote': lote['numero_lote'],
                'cantidad_actual': lote['cantidad_actual'],
                'fecha_caducidad': lote['fecha_caducidad'],
                'proximo_vencer': lote['fecha_caducidad'] < limite_vencimiento if lote['fecha_caducidad'] else False,
            })
        
        errores = []
        advertencias = []
        faltante = max(0, cantidad_requerida - stock_disponible)
        
        # Validar stock suficiente
        if stock_disponible < cantidad_requerida:
            producto_nombre = producto.nombre if hasattr(producto, 'nombre') else str(producto)
            producto_clave = producto.clave if hasattr(producto, 'clave') else ''
            
            lotes_str = ", ".join([
                f"{l['numero_lote']}:{l['cantidad_actual']}" for l in lotes_info[:5]
            ]) or "(ninguno)"
            
            errores.append(
                f"Stock insuficiente para '{producto_clave}' ({producto_nombre}): "
                f"requerido {cantidad_requerida}, disponible {stock_disponible}. "
                f"Lotes: {lotes_str}"
            )
        
        # Advertencia de lotes próximos a vencer
        lotes_proximos = [l for l in lotes_info if l.get('proximo_vencer')]
        if lotes_proximos and not errores:
            advertencias.append(
                f"Hay {len(lotes_proximos)} lote(s) próximos a vencer en menos de "
                f"{LoteQueryHelper.DIAS_ALERTA_VENCIMIENTO} días"
            )
        
        return {
            'valido': len(errores) == 0,
            'stock_disponible': stock_disponible,
            'faltante': faltante,
            'lotes': lotes_info,
            'errores': errores,
            'advertencias': advertencias,
        }
    
    @staticmethod
    def seleccionar_lotes_fefo(
        producto,
        cantidad_requerida: int,
        centro=None,
        solo_farmacia_central: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        ISS-001 FIX: Selecciona lotes usando FEFO (First Expired, First Out).
        
        Retorna lista de lotes a usar con las cantidades a tomar de cada uno.
        
        Args:
            producto: Producto a surtir
            cantidad_requerida: Cantidad total a surtir
            centro: Centro específico (opcional)
            solo_farmacia_central: Si True, solo usa farmacia central
            
        Returns:
            list: Lista de dicts {lote_id, numero_lote, cantidad_a_usar, ...}
        """
        lotes = LoteQueryHelper.get_lotes_disponibles(
            producto=producto,
            centro=centro,
            solo_farmacia_central=solo_farmacia_central,
            ordenar_fefo=True,
        )
        
        seleccion = []
        cantidad_pendiente = cantidad_requerida
        
        for lote in lotes:
            if cantidad_pendiente <= 0:
                break
            
            cantidad_a_usar = min(lote.cantidad_actual, cantidad_pendiente)
            
            seleccion.append({
                'lote_id': lote.id,
                'numero_lote': lote.numero_lote,
                'cantidad_disponible': lote.cantidad_actual,
                'cantidad_a_usar': cantidad_a_usar,
                'fecha_caducidad': lote.fecha_caducidad,
            })
            
            cantidad_pendiente -= cantidad_a_usar
        
        return seleccion
    
    @staticmethod
    def get_lotes_por_vencer(
        dias: int = 90,
        producto=None,
        centro=None,
        solo_farmacia_central: bool = False,
    ) -> QuerySet:
        """
        ISS-004 FIX: Retorna lotes que vencen en los próximos X días.
        
        Args:
            dias: Número de días hacia adelante para buscar
            producto: Filtrar por producto específico
            centro: Filtrar por centro específico
            solo_farmacia_central: Si True, solo farmacia central
            
        Returns:
            QuerySet de lotes próximos a vencer
        """
        from core.models import Lote
        
        hoy = timezone.now().date()
        limite = hoy + timedelta(days=dias)
        
        filtros = {
            'activo': True,
            'cantidad_actual__gt': 0,
            'fecha_caducidad__gte': hoy,
            'fecha_caducidad__lte': limite,
        }
        
        if producto:
            producto_id = producto.id if hasattr(producto, 'id') else producto
            filtros['producto_id'] = producto_id
        
        if solo_farmacia_central:
            filtros['centro__isnull'] = True
        elif centro:
            centro_id = centro.id if hasattr(centro, 'id') else centro
            filtros['centro_id'] = centro_id
        
        return Lote.objects.filter(**filtros).order_by('fecha_caducidad')
    
    @staticmethod
    def get_lotes_vencidos(
        producto=None,
        centro=None,
        solo_activos: bool = True,
    ) -> QuerySet:
        """
        ISS-004 FIX: Retorna lotes ya vencidos.
        
        Args:
            producto: Filtrar por producto específico
            centro: Filtrar por centro específico
            solo_activos: Si True, solo lotes activos (para procesar)
            
        Returns:
            QuerySet de lotes vencidos
        """
        from core.models import Lote
        
        hoy = timezone.now().date()
        
        filtros = {
            'fecha_caducidad__lt': hoy,
        }
        
        if solo_activos:
            filtros['activo'] = True
        
        if producto:
            producto_id = producto.id if hasattr(producto, 'id') else producto
            filtros['producto_id'] = producto_id
        
        if centro:
            centro_id = centro.id if hasattr(centro, 'id') else centro
            filtros['centro_id'] = centro_id
        
        return Lote.objects.filter(**filtros).order_by('fecha_caducidad')


class ContratoValidator:
    """
    ISS-003 FIX: Validador estricto de contratos para entradas de lotes.
    
    Convierte advertencias en errores bloqueantes para operaciones críticas.
    """
    
    # Porcentaje máximo de excedente permitido sobre cantidad contratada
    PORCENTAJE_EXCEDENTE_MAX = 10
    
    # Días mínimos de vigencia requeridos para caducidad
    DIAS_MINIMOS_CADUCIDAD = 180
    
    @staticmethod
    def validar_entrada_contrato(
        lote,
        cantidad_a_ingresar: int,
        contrato=None,
        es_entrada_formal: bool = True,
        strict: bool = True,
    ) -> Dict[str, Any]:
        """
        ISS-003 FIX: Valida reglas de contrato para entrada de lotes.
        
        Args:
            lote: Instancia de Lote a validar
            cantidad_a_ingresar: Cantidad que se pretende ingresar
            contrato: Objeto contrato si existe (opcional)
            es_entrada_formal: Si True, exige número de contrato
            strict: Si True, convierte advertencias críticas en errores
            
        Returns:
            dict: {
                'valido': bool,
                'errores': list,
                'advertencias': list,
                'bloqueante': bool (True si hay errores que deben bloquear)
            }
        """
        errores = []
        advertencias = []
        
        # 1. Validar número de contrato obligatorio
        if es_entrada_formal and not lote.numero_contrato:
            msg = 'El lote debe tener número de contrato para entradas formales.'
            if strict:
                errores.append(msg)
            else:
                advertencias.append(msg)
        
        # 2. Validar vigencia de caducidad
        if lote.fecha_caducidad:
            hoy = timezone.now().date()
            dias_vigencia = (lote.fecha_caducidad - hoy).days
            
            if dias_vigencia < 0:
                errores.append(
                    f'El lote está vencido (caducidad: {lote.fecha_caducidad}).'
                )
            elif dias_vigencia < ContratoValidator.DIAS_MINIMOS_CADUCIDAD:
                msg = (
                    f'El lote tiene menos de {ContratoValidator.DIAS_MINIMOS_CADUCIDAD} días '
                    f'de vigencia (caduca: {lote.fecha_caducidad}, días restantes: {dias_vigencia}).'
                )
                if strict:
                    errores.append(msg)
                else:
                    advertencias.append(msg)
        
        # 3. Validar excedente sobre cantidad inicial
        if cantidad_a_ingresar and lote.cantidad_inicial:
            cantidad_proyectada = (lote.cantidad_actual or 0) + cantidad_a_ingresar
            limite_max = lote.cantidad_inicial * (1 + ContratoValidator.PORCENTAJE_EXCEDENTE_MAX / 100)
            
            if cantidad_proyectada > limite_max:
                msg = (
                    f'La cantidad resultante ({cantidad_proyectada}) excede el '
                    f'{ContratoValidator.PORCENTAJE_EXCEDENTE_MAX}% del límite inicial '
                    f'({lote.cantidad_inicial}).'
                )
                if strict:
                    errores.append(msg)
                else:
                    advertencias.append(msg)
        
        # 4. Validar contrato específico si se proporciona
        if contrato:
            # Validar fecha de vigencia del contrato
            if hasattr(contrato, 'fecha_fin') and contrato.fecha_fin:
                hoy = timezone.now().date()
                if contrato.fecha_fin < hoy:
                    errores.append(
                        f'El contrato {contrato} ha expirado (fin: {contrato.fecha_fin}).'
                    )
            
            # Validar cantidad máxima del contrato
            if hasattr(contrato, 'cantidad_maxima') and contrato.cantidad_maxima:
                if cantidad_a_ingresar > contrato.cantidad_maxima:
                    errores.append(
                        f'La cantidad ({cantidad_a_ingresar}) excede el máximo del contrato '
                        f'({contrato.cantidad_maxima}).'
                    )
        
        return {
            'valido': len(errores) == 0,
            'errores': errores,
            'advertencias': advertencias,
            'bloqueante': len(errores) > 0,
        }
    
    @staticmethod
    def validar_lote_para_surtido(
        lote,
        cantidad_a_surtir: int,
    ) -> Dict[str, Any]:
        """
        ISS-003 FIX: Valida si un lote puede usarse para surtir.
        
        Args:
            lote: Instancia de Lote
            cantidad_a_surtir: Cantidad que se pretende surtir
            
        Returns:
            dict: {valido, errores, advertencias}
        """
        errores = []
        advertencias = []
        
        # Verificar que el lote esté activo
        if not lote.activo:
            errores.append(f'El lote {lote.numero_lote} está inactivo.')
        
        # Verificar que no esté vencido
        if lote.esta_vencido():
            errores.append(
                f'El lote {lote.numero_lote} está vencido (caducidad: {lote.fecha_caducidad}).'
            )
        
        # Verificar stock suficiente
        if lote.cantidad_actual < cantidad_a_surtir:
            errores.append(
                f'El lote {lote.numero_lote} no tiene stock suficiente: '
                f'disponible {lote.cantidad_actual}, requerido {cantidad_a_surtir}.'
            )
        
        # Advertencia si está próximo a vencer
        if lote.fecha_caducidad:
            hoy = timezone.now().date()
            dias_restantes = (lote.fecha_caducidad - hoy).days
            if 0 < dias_restantes < 30:
                advertencias.append(
                    f'El lote {lote.numero_lote} vence en {dias_restantes} días.'
                )
        
        return {
            'valido': len(errores) == 0,
            'errores': errores,
            'advertencias': advertencias,
        }
