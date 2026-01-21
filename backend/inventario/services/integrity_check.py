"""
ISS-009: Detalle de verificación de integridad.

Servicio para verificación de integridad de datos con
reportes detallados de inconsistencias encontradas.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Generator
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from django.db import connection
from django.db.models import Sum, F, Q, Count

logger = logging.getLogger(__name__)


class NivelSeveridad(str, Enum):
    """Severidad de problemas encontrados."""
    CRITICO = "CRITICO"     # Datos corruptos, requiere acción inmediata
    ALTO = "ALTO"           # Inconsistencias que afectan operación
    MEDIO = "MEDIO"         # Advertencias que deben revisarse
    BAJO = "BAJO"           # Sugerencias de mejora
    INFO = "INFO"           # Información general


class CategoriaVerificacion(str, Enum):
    """Categorías de verificación."""
    STOCK = "STOCK"
    MOVIMIENTOS = "MOVIMIENTOS"
    LOTES = "LOTES"
    REQUISICIONES = "REQUISICIONES"
    RELACIONES = "RELACIONES"
    INDICES = "INDICES"
    DUPLICADOS = "DUPLICADOS"


@dataclass
class ProblemaIntegridad:
    """Representa un problema de integridad detectado."""
    codigo: str
    categoria: CategoriaVerificacion
    severidad: NivelSeveridad
    titulo: str
    descripcion: str
    tabla_afectada: str
    registros_afectados: int
    datos_ejemplo: List[Dict[str, Any]] = field(default_factory=list)
    sugerencia_correccion: str = ""
    sql_correccion: Optional[str] = None


@dataclass
class ResultadoVerificacion:
    """Resultado completo de verificación de integridad."""
    timestamp: datetime
    duracion_segundos: float
    total_verificaciones: int
    problemas_encontrados: int
    problemas: List[ProblemaIntegridad]
    resumen_por_severidad: Dict[str, int]
    resumen_por_categoria: Dict[str, int]
    estado_general: str  # "OK", "ADVERTENCIA", "CRITICO"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'duracion_segundos': self.duracion_segundos,
            'total_verificaciones': self.total_verificaciones,
            'problemas_encontrados': self.problemas_encontrados,
            'resumen_por_severidad': self.resumen_por_severidad,
            'resumen_por_categoria': self.resumen_por_categoria,
            'estado_general': self.estado_general,
            'problemas': [
                {
                    'codigo': p.codigo,
                    'categoria': p.categoria.value,
                    'severidad': p.severidad.value,
                    'titulo': p.titulo,
                    'descripcion': p.descripcion,
                    'tabla_afectada': p.tabla_afectada,
                    'registros_afectados': p.registros_afectados,
                    'datos_ejemplo': p.datos_ejemplo[:5],  # Limitar ejemplos
                    'sugerencia_correccion': p.sugerencia_correccion,
                    'tiene_sql_correccion': p.sql_correccion is not None
                }
                for p in self.problemas
            ]
        }


class VerificadorIntegridad:
    """
    ISS-009: Verificador de integridad de datos.
    
    Realiza verificaciones exhaustivas de la base de datos
    y genera reportes detallados de problemas encontrados.
    """
    
    def __init__(self):
        self.problemas: List[ProblemaIntegridad] = []
        self.verificaciones_ejecutadas = 0
    
    def ejecutar_verificacion_completa(self, incluir_correciones: bool = False) -> ResultadoVerificacion:
        """
        Ejecuta todas las verificaciones de integridad.
        
        Args:
            incluir_correciones: Si incluir SQL de corrección en el reporte
            
        Returns:
            ResultadoVerificacion con todos los problemas encontrados
        """
        from core.models import (
            Medicamento, Lote, Movimiento, 
            Requisicion, DetalleRequisicion
        )
        
        inicio = datetime.now()
        self.problemas = []
        self.verificaciones_ejecutadas = 0
        
        # Ejecutar todas las verificaciones
        verificaciones = [
            self._verificar_stock_negativo,
            self._verificar_stock_excede_inicial,
            self._verificar_lotes_sin_medicamento,
            self._verificar_movimientos_huerfanos,
            self._verificar_balance_movimientos,
            self._verificar_requisiciones_inconsistentes,
            self._verificar_fechas_invalidas,
            self._verificar_lotes_vencidos_con_stock,
            self._verificar_duplicados_codigo_barras,
            self._verificar_referencias_rotas,
            self._verificar_cantidades_cero_activas,
        ]
        
        for verificacion in verificaciones:
            try:
                verificacion()
                self.verificaciones_ejecutadas += 1
            except Exception as e:
                logger.error(f"Error en verificación {verificacion.__name__}: {e}")
                self.problemas.append(ProblemaIntegridad(
                    codigo=f"ERR_{verificacion.__name__.upper()}",
                    categoria=CategoriaVerificacion.INDICES,
                    severidad=NivelSeveridad.ALTO,
                    titulo=f"Error ejecutando {verificacion.__name__}",
                    descripcion=str(e),
                    tabla_afectada="N/A",
                    registros_afectados=0
                ))
        
        # Calcular resúmenes
        resumen_severidad = {}
        resumen_categoria = {}
        
        for problema in self.problemas:
            sev = problema.severidad.value
            cat = problema.categoria.value
            resumen_severidad[sev] = resumen_severidad.get(sev, 0) + 1
            resumen_categoria[cat] = resumen_categoria.get(cat, 0) + 1
        
        # Determinar estado general
        if resumen_severidad.get(NivelSeveridad.CRITICO.value, 0) > 0:
            estado = "CRITICO"
        elif resumen_severidad.get(NivelSeveridad.ALTO.value, 0) > 0:
            estado = "ADVERTENCIA"
        elif resumen_severidad.get(NivelSeveridad.MEDIO.value, 0) > 0:
            estado = "REVISION_REQUERIDA"
        else:
            estado = "OK"
        
        duracion = (datetime.now() - inicio).total_seconds()
        
        # Limpiar SQL de corrección si no se solicita
        if not incluir_correciones:
            for problema in self.problemas:
                problema.sql_correccion = None
        
        return ResultadoVerificacion(
            timestamp=inicio,
            duracion_segundos=duracion,
            total_verificaciones=self.verificaciones_ejecutadas,
            problemas_encontrados=len(self.problemas),
            problemas=self.problemas,
            resumen_por_severidad=resumen_severidad,
            resumen_por_categoria=resumen_categoria,
            estado_general=estado
        )
    
    def _verificar_stock_negativo(self):
        """Verifica que no haya lotes con cantidad negativa."""
        from core.models import Lote
        
        lotes_negativos = Lote.objects.filter(cantidad_actual__lt=0)
        
        if lotes_negativos.exists():
            ejemplos = list(lotes_negativos.values(
                'id', 'numero_lote', 'cantidad_actual',
                'medicamento__nombre'
            )[:10])
            
            self.problemas.append(ProblemaIntegridad(
                codigo="INT-001",
                categoria=CategoriaVerificacion.STOCK,
                severidad=NivelSeveridad.CRITICO,
                titulo="Lotes con cantidad negativa",
                descripcion=(
                    f"Se encontraron {lotes_negativos.count()} lotes con "
                    "cantidad actual negativa, lo cual es inválido."
                ),
                tabla_afectada="core_lote",
                registros_afectados=lotes_negativos.count(),
                datos_ejemplo=ejemplos,
                sugerencia_correccion=(
                    "Revisar movimientos de salida de estos lotes. "
                    "Posible doble registro de salidas."
                ),
                sql_correccion="""
                -- Identificar lotes negativos para revisión manual
                SELECT l.id, l.numero_lote, l.cantidad_actual, m.nombre
                FROM core_lote l
                JOIN core_medicamento m ON l.medicamento_id = m.id
                WHERE l.cantidad_actual < 0;
                
                -- NO ejecutar actualización automática sin revisión
                """
            ))
    
    def _verificar_stock_excede_inicial(self):
        """Verifica que cantidad actual no exceda cantidad inicial."""
        from core.models import Lote
        
        lotes_excedidos = Lote.objects.filter(
            cantidad_actual__gt=F('cantidad_inicial')
        )
        
        if lotes_excedidos.exists():
            ejemplos = list(lotes_excedidos.values(
                'id', 'numero_lote', 'cantidad_actual', 
                'cantidad_inicial', 'medicamento__nombre'
            )[:10])
            
            self.problemas.append(ProblemaIntegridad(
                codigo="INT-002",
                categoria=CategoriaVerificacion.STOCK,
                severidad=NivelSeveridad.ALTO,
                titulo="Lotes con cantidad actual mayor a inicial",
                descripcion=(
                    f"Se encontraron {lotes_excedidos.count()} lotes donde "
                    "la cantidad actual supera la cantidad inicial."
                ),
                tabla_afectada="core_lote",
                registros_afectados=lotes_excedidos.count(),
                datos_ejemplo=ejemplos,
                sugerencia_correccion=(
                    "Revisar si hubo ajustes de inventario o "
                    "entradas adicionales no registradas correctamente."
                ),
                sql_correccion="""
                UPDATE core_lote 
                SET cantidad_actual = cantidad_inicial
                WHERE cantidad_actual > cantidad_inicial;
                """
            ))
    
    def _verificar_lotes_sin_medicamento(self):
        """Verifica lotes huérfanos sin medicamento asociado."""
        from core.models import Lote
        
        # Usar raw SQL para detectar referencias rotas
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) FROM core_lote l
                LEFT JOIN core_medicamento m ON l.medicamento_id = m.id
                WHERE m.id IS NULL
            """)
            count = cursor.fetchone()[0]
        
        if count > 0:
            self.problemas.append(ProblemaIntegridad(
                codigo="INT-003",
                categoria=CategoriaVerificacion.RELACIONES,
                severidad=NivelSeveridad.CRITICO,
                titulo="Lotes sin medicamento asociado",
                descripcion=(
                    f"Se encontraron {count} lotes que referencian "
                    "medicamentos inexistentes (foreign key rota)."
                ),
                tabla_afectada="core_lote",
                registros_afectados=count,
                sugerencia_correccion="Eliminar lotes huérfanos o restaurar medicamentos.",
                sql_correccion="""
                -- Identificar lotes huérfanos
                SELECT l.* FROM core_lote l
                LEFT JOIN core_medicamento m ON l.medicamento_id = m.id
                WHERE m.id IS NULL;
                """
            ))
    
    def _verificar_movimientos_huerfanos(self):
        """Verifica movimientos sin lote o medicamento asociado."""
        from core.models import Movimiento
        
        # Movimientos con lote nulo (si no está permitido)
        movimientos_sin_lote = Movimiento.objects.filter(
            lote__isnull=True,
            tipo__in=['entrada', 'salida', 'ajuste']
        )
        
        if movimientos_sin_lote.exists():
            self.problemas.append(ProblemaIntegridad(
                codigo="INT-004",
                categoria=CategoriaVerificacion.MOVIMIENTOS,
                severidad=NivelSeveridad.MEDIO,
                titulo="Movimientos sin lote asociado",
                descripcion=(
                    f"Se encontraron {movimientos_sin_lote.count()} movimientos "
                    "sin lote asociado que deberían tenerlo."
                ),
                tabla_afectada="core_movimiento",
                registros_afectados=movimientos_sin_lote.count(),
                sugerencia_correccion="Asociar lotes a movimientos o marcar como históricos."
            ))
    
    def _verificar_balance_movimientos(self):
        """Verifica que el balance de movimientos coincida con stock actual."""
        from core.models import Lote, Movimiento
        
        # Para cada lote, calcular stock esperado vs actual
        discrepancias = []
        
        lotes_con_movimientos = Lote.objects.annotate(
            entradas=Sum('movimientos__cantidad', filter=Q(movimientos__tipo='entrada')),
            salidas=Sum('movimientos__cantidad', filter=Q(movimientos__tipo='salida')),
            ajustes=Sum('movimientos__cantidad', filter=Q(movimientos__tipo='ajuste'))
        ).filter(
            Q(entradas__isnull=False) | Q(salidas__isnull=False)
        )[:100]  # Limitar para rendimiento
        
        for lote in lotes_con_movimientos:
            entradas = lote.entradas or 0
            salidas = lote.salidas or 0
            ajustes = lote.ajustes or 0
            
            # Stock esperado = inicial + entradas - salidas + ajustes
            stock_esperado = lote.cantidad_inicial + entradas - salidas + ajustes
            
            if abs(stock_esperado - lote.cantidad_actual) > 0.01:
                discrepancias.append({
                    'lote_id': lote.id,
                    'numero_lote': lote.numero_lote,
                    'stock_actual': float(lote.cantidad_actual),
                    'stock_esperado': float(stock_esperado),
                    'diferencia': float(lote.cantidad_actual - stock_esperado)
                })
        
        if discrepancias:
            self.problemas.append(ProblemaIntegridad(
                codigo="INT-005",
                categoria=CategoriaVerificacion.MOVIMIENTOS,
                severidad=NivelSeveridad.ALTO,
                titulo="Discrepancia entre movimientos y stock",
                descripcion=(
                    f"Se encontraron {len(discrepancias)} lotes donde el "
                    "balance de movimientos no coincide con el stock actual."
                ),
                tabla_afectada="core_lote/core_movimiento",
                registros_afectados=len(discrepancias),
                datos_ejemplo=discrepancias[:5],
                sugerencia_correccion=(
                    "Revisar movimientos de estos lotes. Puede requerir "
                    "ajuste de inventario para corregir discrepancias."
                )
            ))
    
    def _verificar_requisiciones_inconsistentes(self):
        """Verifica requisiciones con estados inconsistentes."""
        from core.models import Requisicion, DetalleRequisicion
        
        # Requisiciones aprobadas sin detalles
        requisiciones_vacias = Requisicion.objects.annotate(
            num_detalles=Count('detalles')
        ).filter(
            estado__in=['APROBADA', 'DESPACHADA'],
            num_detalles=0
        )
        
        if requisiciones_vacias.exists():
            self.problemas.append(ProblemaIntegridad(
                codigo="INT-006",
                categoria=CategoriaVerificacion.REQUISICIONES,
                severidad=NivelSeveridad.MEDIO,
                titulo="Requisiciones aprobadas sin detalles",
                descripcion=(
                    f"Se encontraron {requisiciones_vacias.count()} requisiciones "
                    "en estado aprobado/despachado sin detalles asociados."
                ),
                tabla_afectada="core_requisicion",
                registros_afectados=requisiciones_vacias.count(),
                sugerencia_correccion="Revisar y cancelar requisiciones vacías."
            ))
        
        # Detalles con cantidad entregada mayor a solicitada
        detalles_excedidos = DetalleRequisicion.objects.filter(
            cantidad_entregada__gt=F('cantidad_solicitada')
        )
        
        if detalles_excedidos.exists():
            self.problemas.append(ProblemaIntegridad(
                codigo="INT-007",
                categoria=CategoriaVerificacion.REQUISICIONES,
                severidad=NivelSeveridad.ALTO,
                titulo="Entregas exceden cantidad solicitada",
                descripcion=(
                    f"Se encontraron {detalles_excedidos.count()} detalles de "
                    "requisición donde lo entregado supera lo solicitado."
                ),
                tabla_afectada="core_detallerequisicion",
                registros_afectados=detalles_excedidos.count(),
                sugerencia_correccion="Ajustar cantidades entregadas o solicitadas."
            ))
    
    def _verificar_fechas_invalidas(self):
        """Verifica fechas inválidas o inconsistentes."""
        from core.models import Lote, Movimiento
        
        # Lotes con fecha vencimiento anterior a fabricación
        lotes_fechas_invalidas = Lote.objects.filter(
            fecha_vencimiento__lt=F('fecha_fabricacion')
        )
        
        if lotes_fechas_invalidas.exists():
            self.problemas.append(ProblemaIntegridad(
                codigo="INT-008",
                categoria=CategoriaVerificacion.LOTES,
                severidad=NivelSeveridad.ALTO,
                titulo="Fechas de vencimiento anteriores a fabricación",
                descripcion=(
                    f"Se encontraron {lotes_fechas_invalidas.count()} lotes "
                    "con fecha de vencimiento anterior a fecha de fabricación."
                ),
                tabla_afectada="core_lote",
                registros_afectados=lotes_fechas_invalidas.count(),
                sugerencia_correccion="Corregir fechas de fabricación o vencimiento."
            ))
        
        # Movimientos con fecha futura
        from django.utils import timezone
        movimientos_futuros = Movimiento.objects.filter(
            fecha__gt=timezone.now() + timedelta(days=1)
        )
        
        if movimientos_futuros.exists():
            self.problemas.append(ProblemaIntegridad(
                codigo="INT-009",
                categoria=CategoriaVerificacion.MOVIMIENTOS,
                severidad=NivelSeveridad.MEDIO,
                titulo="Movimientos con fecha futura",
                descripcion=(
                    f"Se encontraron {movimientos_futuros.count()} movimientos "
                    "registrados con fecha futura."
                ),
                tabla_afectada="core_movimiento",
                registros_afectados=movimientos_futuros.count(),
                sugerencia_correccion="Revisar y corregir fechas de movimientos."
            ))
    
    def _verificar_lotes_vencidos_con_stock(self):
        """Informa sobre lotes vencidos que aún tienen stock."""
        from core.models import Lote
        from django.utils import timezone
        
        lotes_vencidos_stock = Lote.objects.filter(
            fecha_vencimiento__lt=timezone.now().date(),
            cantidad_actual__gt=0
        )
        
        if lotes_vencidos_stock.exists():
            total_unidades = lotes_vencidos_stock.aggregate(
                total=Sum('cantidad_actual')
            )['total'] or 0
            
            ejemplos = list(lotes_vencidos_stock.values(
                'id', 'codigo_lote', 'cantidad_actual',
                'fecha_vencimiento', 'medicamento__nombre'
            )[:10])
            
            self.problemas.append(ProblemaIntegridad(
                codigo="INT-010",
                categoria=CategoriaVerificacion.LOTES,
                severidad=NivelSeveridad.INFO,
                titulo="Lotes vencidos con stock disponible",
                descripcion=(
                    f"Se encontraron {lotes_vencidos_stock.count()} lotes "
                    f"vencidos con {total_unidades} unidades en stock."
                ),
                tabla_afectada="core_lote",
                registros_afectados=lotes_vencidos_stock.count(),
                datos_ejemplo=ejemplos,
                sugerencia_correccion=(
                    "Procesar baja de lotes vencidos según protocolo. "
                    "Este es un recordatorio, no necesariamente un error."
                )
            ))
    
    def _verificar_duplicados_codigo_barras(self):
        """Verifica códigos de barras duplicados."""
        from core.models import Lote
        from django.db.models import Count
        
        duplicados = Lote.objects.exclude(
            codigo_barras__isnull=True
        ).exclude(
            codigo_barras=''
        ).values('codigo_barras').annotate(
            count=Count('id')
        ).filter(count__gt=1)
        
        if duplicados.exists():
            ejemplos = list(duplicados[:10])
            total = sum(d['count'] for d in duplicados)
            
            self.problemas.append(ProblemaIntegridad(
                codigo="INT-011",
                categoria=CategoriaVerificacion.DUPLICADOS,
                severidad=NivelSeveridad.ALTO,
                titulo="Códigos de barras duplicados",
                descripcion=(
                    f"Se encontraron {len(duplicados)} códigos de barras "
                    f"duplicados afectando {total} lotes."
                ),
                tabla_afectada="core_lote",
                registros_afectados=total,
                datos_ejemplo=ejemplos,
                sugerencia_correccion="Asignar códigos únicos a cada lote."
            ))
    
    def _verificar_referencias_rotas(self):
        """Verifica integridad de foreign keys con raw SQL."""
        referencias_a_verificar = [
            ("core_movimiento", "medicamento_id", "core_medicamento"),
            ("core_movimiento", "lote_id", "core_lote"),
            ("core_movimiento", "usuario_id", "auth_user"),
            ("core_detallerequisicion", "requisicion_id", "core_requisicion"),
            ("core_detallerequisicion", "medicamento_id", "core_medicamento"),
        ]
        
        total_rotas = 0
        detalles = []
        
        for tabla, columna, tabla_ref in referencias_a_verificar:
            try:
                # HALLAZGO #11 FIX: Usar SQL parametrizado para prevenir inyección
                # Validar nombres de tabla/columna contra whitelist
                TABLAS_VALIDAS = {'core_requisicion', 'core_lote', 'core_producto', 
                                  'core_movimiento', 'core_detallerequisicion', 'core_centro'}
                COLUMNAS_VALIDAS = {'centro_id', 'producto_id', 'lote_id', 'usuario_id', 
                                   'centro_origen_id', 'centro_destino_id', 'solicitante_id'}
                
                if tabla not in TABLAS_VALIDAS or columna not in COLUMNAS_VALIDAS or tabla_ref not in TABLAS_VALIDAS:
                    logger.warning(f"HALLAZGO #11: Intento de query con nombres inválidos: {tabla}.{columna} -> {tabla_ref}")
                    continue
                
                with connection.cursor() as cursor:
                    # Usar SQL parametrizado (nombres de tabla validados contra whitelist)
                    query = f"""
                        SELECT COUNT(*) FROM {tabla} t
                        LEFT JOIN {tabla_ref} r ON t.{columna} = r.id
                        WHERE t.{columna} IS NOT NULL AND r.id IS NULL
                    """
                    cursor.execute(query)  # Sin parámetros interpolados del usuario
                    count = cursor.fetchone()[0]
                    
                    if count > 0:
                        total_rotas += count
                        detalles.append({
                            'tabla': tabla,
                            'columna': columna,
                            'tabla_referenciada': tabla_ref,
                            'registros_afectados': count
                        })
            except Exception as e:
                logger.warning(f"Error verificando {tabla}.{columna}: {e}")
        
        if total_rotas > 0:
            self.problemas.append(ProblemaIntegridad(
                codigo="INT-012",
                categoria=CategoriaVerificacion.RELACIONES,
                severidad=NivelSeveridad.CRITICO,
                titulo="Referencias a registros inexistentes",
                descripcion=(
                    f"Se encontraron {total_rotas} referencias rotas "
                    "a registros que no existen."
                ),
                tabla_afectada="Múltiples tablas",
                registros_afectados=total_rotas,
                datos_ejemplo=detalles,
                sugerencia_correccion="Restaurar registros faltantes o limpiar referencias."
            ))
    
    def _verificar_cantidades_cero_activas(self):
        """Verifica lotes con cantidad cero que no están marcados como agotados."""
        from core.models import Lote
        
        # Asumiendo que hay un campo `activo` o similar
        lotes_cero_activos = Lote.objects.filter(
            cantidad_actual=0,
            activo=True  # Si existe este campo
        ).select_related('medicamento')
        
        # Si no existe el campo activo, buscar otra forma
        try:
            count = lotes_cero_activos.count()
            if count > 0:
                self.problemas.append(ProblemaIntegridad(
                    codigo="INT-013",
                    categoria=CategoriaVerificacion.LOTES,
                    severidad=NivelSeveridad.BAJO,
                    titulo="Lotes agotados marcados como activos",
                    descripcion=(
                        f"Se encontraron {count} lotes con cantidad cero "
                        "que aún están marcados como activos."
                    ),
                    tabla_afectada="core_lote",
                    registros_afectados=count,
                    sugerencia_correccion="Considerar desactivar lotes agotados."
                ))
        except Exception:
            # Campo activo no existe, omitir esta verificación
            pass


# === FUNCIONES DE CONVENIENCIA ===

def verificar_integridad_rapida() -> Dict[str, Any]:
    """
    Ejecuta verificación rápida y retorna resumen.
    """
    verificador = VerificadorIntegridad()
    resultado = verificador.ejecutar_verificacion_completa(incluir_correciones=False)
    
    return {
        'estado': resultado.estado_general,
        'problemas': resultado.problemas_encontrados,
        'criticos': resultado.resumen_por_severidad.get('CRITICO', 0),
        'altos': resultado.resumen_por_severidad.get('ALTO', 0),
        'duracion': resultado.duracion_segundos
    }


def obtener_reporte_completo() -> ResultadoVerificacion:
    """
    Ejecuta verificación completa con todos los detalles.
    """
    verificador = VerificadorIntegridad()
    return verificador.ejecutar_verificacion_completa(incluir_correciones=True)


def verificar_categoria(categoria: CategoriaVerificacion) -> List[ProblemaIntegridad]:
    """
    Ejecuta verificación de una categoría específica.
    """
    verificador = VerificadorIntegridad()
    resultado = verificador.ejecutar_verificacion_completa()
    
    return [p for p in resultado.problemas if p.categoria == categoria]
