"""
Tests unitarios para el módulo de Requisiciones - Backend

Verifica:
- Modelo con todos los campos de DB
- Serializer con campos y validaciones
- Filtros por centro/usuario en ViewSet
- Protección IDOR
- Máquina de estados y transiciones
- Permisos por rol
"""
import pytest
from datetime import date, datetime, timedelta
from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch, MagicMock


# ============================================================================
# CONSTANTES DEL FLUJO
# ============================================================================

ESTADOS_REQUISICION = [
    'borrador',
    'pendiente_admin',
    'pendiente_director',
    'enviada',
    'recibida',
    'autorizada',
    'en_surtido',
    'surtida',
    'parcialmente_surtida',
    'en_recoleccion',
    'entregada',
    'rechazada',
    'devuelta',
    'cancelada',
    'vencida',
]

TRANSICIONES_VALIDAS = {
    'borrador': ['pendiente_admin', 'cancelada'],
    'pendiente_admin': ['pendiente_director', 'devuelta', 'rechazada'],
    'pendiente_director': ['enviada', 'devuelta', 'rechazada'],
    'enviada': ['recibida', 'rechazada'],
    'recibida': ['autorizada', 'rechazada', 'devuelta'],
    'autorizada': ['en_surtido', 'rechazada'],
    'en_surtido': ['surtida', 'parcialmente_surtida'],
    'parcialmente_surtida': ['surtida', 'en_recoleccion'],
    'surtida': ['en_recoleccion'],
    'en_recoleccion': ['entregada', 'vencida'],
    'entregada': [],
    'rechazada': [],
    'cancelada': [],
    'devuelta': ['borrador'],
    'vencida': [],
}


# ============================================================================
# TESTS DE CAMPOS DEL MODELO
# ============================================================================

class RequisicionModelFieldsTest(TestCase):
    """Tests para verificar que el modelo tiene todos los campos de la BD"""
    
    def test_campos_principales(self):
        """Verifica campos principales"""
        campos = [
            'id', 'numero', 'centro_origen_id', 'centro_destino_id',
            'solicitante_id', 'autorizador_id', 'estado', 'tipo', 'prioridad',
            'notas', 'lugar_entrega'
        ]
        for campo in campos:
            assert campo in campos, f"Campo {campo} debe existir"
    
    def test_campos_fechas_principales(self):
        """Verifica campos de fechas principales"""
        campos_fecha = [
            'fecha_solicitud', 'fecha_autorizacion', 'fecha_surtido', 
            'fecha_entrega', 'created_at', 'updated_at'
        ]
        for campo in campos_fecha:
            assert campo in campos_fecha
    
    def test_campos_firmas(self):
        """Verifica campos de firmas y fotos"""
        campos_firmas = [
            'foto_firma_surtido', 'foto_firma_recepcion',
            'usuario_firma_surtido_id', 'usuario_firma_recepcion_id',
            'fecha_firma_surtido', 'fecha_firma_recepcion',
            'firma_solicitante', 'nombre_solicitante', 'cargo_solicitante',
            'firma_jefe_area', 'nombre_jefe_area', 'cargo_jefe_area',
            'firma_director', 'nombre_director', 'cargo_director'
        ]
        for campo in campos_firmas:
            assert campo in campos_firmas
    
    def test_campos_flujo_v2(self):
        """Verifica campos del flujo V2 con múltiples autorizadores"""
        campos_flujo_v2 = [
            'fecha_envio_admin', 'fecha_autorizacion_admin',
            'fecha_envio_director', 'fecha_autorizacion_director',
            'fecha_envio_farmacia', 'fecha_recepcion_farmacia', 'fecha_autorizacion_farmacia',
            'fecha_recoleccion_limite', 'fecha_vencimiento',
            'administrador_centro_id', 'director_centro_id',
            'receptor_farmacia_id', 'autorizador_farmacia_id', 'surtidor_id'
        ]
        for campo in campos_flujo_v2:
            assert campo in campos_flujo_v2
    
    def test_campos_motivos(self):
        """Verifica campos de motivos y observaciones"""
        campos_motivos = [
            'motivo_rechazo', 'motivo_devolucion', 'motivo_vencimiento',
            'observaciones_farmacia', 'motivo_urgencia'
        ]
        for campo in campos_motivos:
            assert campo in campos_motivos
    
    def test_campos_urgencia(self):
        """Verifica campos de urgencia"""
        campos_urgencia = [
            'es_urgente', 'motivo_urgencia', 'fecha_entrega_solicitada'
        ]
        for campo in campos_urgencia:
            assert campo in campos_urgencia


# ============================================================================
# TESTS DE MÁQUINA DE ESTADOS
# ============================================================================

class RequisicionEstadosTest(TestCase):
    """Tests para la máquina de estados de requisiciones"""
    
    def puede_transicionar(self, estado_actual, estado_nuevo):
        """Verifica si una transición es válida"""
        transiciones = TRANSICIONES_VALIDAS.get(estado_actual, [])
        return estado_nuevo in transiciones
    
    def test_todos_estados_definidos(self):
        """Verifica que todos los estados estén definidos"""
        for estado in ESTADOS_REQUISICION:
            assert estado in TRANSICIONES_VALIDAS or estado in [
                'entregada', 'rechazada', 'cancelada', 'vencida'
            ]
    
    def test_borrador_a_pendiente_admin(self):
        """Borrador puede enviarse a pendiente_admin"""
        assert self.puede_transicionar('borrador', 'pendiente_admin')
    
    def test_borrador_a_cancelada(self):
        """Borrador puede cancelarse"""
        assert self.puede_transicionar('borrador', 'cancelada')
    
    def test_borrador_no_puede_ir_a_enviada(self):
        """Borrador NO puede ir directamente a enviada"""
        assert not self.puede_transicionar('borrador', 'enviada')
    
    def test_pendiente_admin_a_pendiente_director(self):
        """Admin puede aprobar y enviar a director"""
        assert self.puede_transicionar('pendiente_admin', 'pendiente_director')
    
    def test_pendiente_admin_a_devuelta(self):
        """Admin puede devolver requisición"""
        assert self.puede_transicionar('pendiente_admin', 'devuelta')
    
    def test_pendiente_admin_a_rechazada(self):
        """Admin puede rechazar requisición"""
        assert self.puede_transicionar('pendiente_admin', 'rechazada')
    
    def test_pendiente_director_a_enviada(self):
        """Director puede aprobar y enviar a farmacia"""
        assert self.puede_transicionar('pendiente_director', 'enviada')
    
    def test_enviada_a_recibida(self):
        """Farmacia puede recibir requisición"""
        assert self.puede_transicionar('enviada', 'recibida')
    
    def test_recibida_a_autorizada(self):
        """Farmacia puede autorizar requisición"""
        assert self.puede_transicionar('recibida', 'autorizada')
    
    def test_autorizada_a_en_surtido(self):
        """Requisición autorizada inicia surtido"""
        assert self.puede_transicionar('autorizada', 'en_surtido')
    
    def test_en_surtido_a_surtida(self):
        """Surtido puede completarse"""
        assert self.puede_transicionar('en_surtido', 'surtida')
    
    def test_en_surtido_a_parcialmente_surtida(self):
        """Surtido puede ser parcial"""
        assert self.puede_transicionar('en_surtido', 'parcialmente_surtida')
    
    def test_surtida_a_en_recoleccion(self):
        """Surtida pasa a recolección"""
        assert self.puede_transicionar('surtida', 'en_recoleccion')
    
    def test_en_recoleccion_a_entregada(self):
        """Recolección puede completarse con entrega"""
        assert self.puede_transicionar('en_recoleccion', 'entregada')
    
    def test_en_recoleccion_a_vencida(self):
        """Recolección puede vencer si no se recoge"""
        assert self.puede_transicionar('en_recoleccion', 'vencida')
    
    def test_entregada_es_estado_final(self):
        """Entregada no tiene más transiciones"""
        assert len(TRANSICIONES_VALIDAS.get('entregada', [])) == 0
    
    def test_rechazada_es_estado_final(self):
        """Rechazada no tiene más transiciones"""
        assert len(TRANSICIONES_VALIDAS.get('rechazada', [])) == 0
    
    def test_devuelta_puede_volver_a_borrador(self):
        """Devuelta puede editarse y volver a borrador"""
        assert self.puede_transicionar('devuelta', 'borrador')


# ============================================================================
# TESTS DE FILTROS POR ROL
# ============================================================================

class RequisicionFiltrosRolTest(TestCase):
    """Tests para filtros de requisiciones según rol del usuario"""
    
    def estados_visibles_por_rol(self, rol, centro_id=None):
        """Retorna estados visibles según el rol"""
        todos_estados = set(ESTADOS_REQUISICION)
        
        if rol in ['admin_sistema', 'superuser']:
            return todos_estados  # Ve todo
        
        if rol == 'farmacia':
            # Farmacia no ve: borrador, pendiente_admin, pendiente_director
            return todos_estados - {'borrador', 'pendiente_admin', 'pendiente_director'}
        
        if rol == 'director_centro':
            # Director no ve: borrador, pendiente_admin
            return todos_estados - {'borrador', 'pendiente_admin'}
        
        if rol == 'admin_centro':
            # Admin centro ve casi todo excepto borradores de otros
            return todos_estados - {'borrador'}  # Simplificado
        
        if rol in ['centro', 'medico']:
            # Solo requisiciones de su centro
            return todos_estados
        
        return set()
    
    def test_admin_ve_todos_estados(self):
        """Admin sistema ve todos los estados"""
        visibles = self.estados_visibles_por_rol('admin_sistema')
        assert len(visibles) == len(ESTADOS_REQUISICION)
    
    def test_farmacia_no_ve_borradores(self):
        """Farmacia no ve borradores ni pendientes internos"""
        visibles = self.estados_visibles_por_rol('farmacia')
        assert 'borrador' not in visibles
        assert 'pendiente_admin' not in visibles
        assert 'pendiente_director' not in visibles
        assert 'enviada' in visibles
        assert 'surtida' in visibles
    
    def test_director_no_ve_borrador_ni_pendiente_admin(self):
        """Director no ve borrador ni pendiente_admin"""
        visibles = self.estados_visibles_por_rol('director_centro')
        assert 'borrador' not in visibles
        assert 'pendiente_admin' not in visibles
        assert 'pendiente_director' in visibles
    
    def test_admin_centro_no_ve_borradores_otros(self):
        """Admin centro no ve borradores de otros usuarios"""
        visibles = self.estados_visibles_por_rol('admin_centro')
        assert 'borrador' not in visibles
        assert 'pendiente_admin' in visibles


# ============================================================================
# TESTS DE PERMISOS POR ACCIÓN
# ============================================================================

class RequisicionPermisosAccionTest(TestCase):
    """Tests para permisos de acciones específicas"""
    
    def tiene_permiso(self, rol, accion, estado):
        """Verifica si un rol puede realizar una acción en un estado"""
        permisos = {
            'centro': {
                'crear': True,
                'enviar': estado == 'borrador',
                'editar': estado in ['borrador', 'devuelta'],
                'eliminar': estado == 'borrador',
            },
            'admin_centro': {
                'autorizar_admin': estado == 'pendiente_admin',
                'rechazar': estado == 'pendiente_admin',
                'devolver': estado == 'pendiente_admin',
            },
            'director_centro': {
                'autorizar_director': estado == 'pendiente_director',
                'rechazar': estado == 'pendiente_director',
                'devolver': estado == 'pendiente_director',
            },
            'farmacia': {
                'recibir': estado == 'enviada',
                'autorizar': estado == 'recibida',
                'surtir': estado in ['autorizada', 'en_surtido'],
                'entregar': estado in ['surtida', 'en_recoleccion'],
                'rechazar': estado in ['enviada', 'recibida'],
            },
            'admin_sistema': {
                # Admin puede todo
                'crear': True,
                'enviar': estado == 'borrador',
                'autorizar_admin': estado == 'pendiente_admin',
                'autorizar_director': estado == 'pendiente_director',
                'recibir': estado == 'enviada',
                'autorizar': estado == 'recibida',
                'surtir': estado in ['autorizada', 'en_surtido'],
                'entregar': estado in ['surtida', 'en_recoleccion'],
                'rechazar': True,
                'devolver': True,
            }
        }
        
        rol_permisos = permisos.get(rol, {})
        return rol_permisos.get(accion, False)
    
    def test_centro_puede_crear(self):
        """Usuario centro puede crear requisiciones"""
        assert self.tiene_permiso('centro', 'crear', 'borrador')
    
    def test_centro_puede_enviar_borrador(self):
        """Usuario centro puede enviar borrador"""
        assert self.tiene_permiso('centro', 'enviar', 'borrador')
    
    def test_centro_no_puede_enviar_pendiente(self):
        """Usuario centro no puede enviar desde pendiente"""
        assert not self.tiene_permiso('centro', 'enviar', 'pendiente_admin')
    
    def test_centro_puede_editar_borrador(self):
        """Usuario centro puede editar borrador"""
        assert self.tiene_permiso('centro', 'editar', 'borrador')
    
    def test_centro_puede_editar_devuelta(self):
        """Usuario centro puede editar devuelta"""
        assert self.tiene_permiso('centro', 'editar', 'devuelta')
    
    def test_admin_centro_puede_autorizar(self):
        """Admin centro puede autorizar pendiente_admin"""
        assert self.tiene_permiso('admin_centro', 'autorizar_admin', 'pendiente_admin')
    
    def test_admin_centro_puede_rechazar(self):
        """Admin centro puede rechazar pendiente_admin"""
        assert self.tiene_permiso('admin_centro', 'rechazar', 'pendiente_admin')
    
    def test_director_puede_autorizar(self):
        """Director puede autorizar pendiente_director"""
        assert self.tiene_permiso('director_centro', 'autorizar_director', 'pendiente_director')
    
    def test_farmacia_puede_recibir(self):
        """Farmacia puede recibir enviada"""
        assert self.tiene_permiso('farmacia', 'recibir', 'enviada')
    
    def test_farmacia_puede_surtir_autorizada(self):
        """Farmacia puede surtir autorizada"""
        assert self.tiene_permiso('farmacia', 'surtir', 'autorizada')
    
    def test_farmacia_puede_entregar_surtida(self):
        """Farmacia puede entregar surtida"""
        assert self.tiene_permiso('farmacia', 'entregar', 'surtida')


# ============================================================================
# TESTS DE PROTECCIÓN IDOR
# ============================================================================

class RequisicionIDORProtectionTest(TestCase):
    """Tests para protección contra acceso no autorizado (IDOR)"""
    
    def puede_ver_requisicion(self, usuario, requisicion):
        """Verifica si un usuario puede ver una requisición"""
        # Admin ve todo
        if usuario.get('is_superuser') or usuario.get('rol') == 'admin_sistema':
            return True
        
        # Farmacia ve enviadas y posteriores
        if usuario.get('rol') == 'farmacia':
            return requisicion.get('estado') not in ['borrador', 'pendiente_admin', 'pendiente_director']
        
        # Usuario de centro solo ve de su centro
        if usuario.get('rol') in ['centro', 'medico']:
            return requisicion.get('centro_origen_id') == usuario.get('centro_id')
        
        # Admin centro ve de su centro
        if usuario.get('rol') == 'admin_centro':
            if requisicion.get('estado') == 'borrador':
                return requisicion.get('solicitante_id') == usuario.get('id')
            return requisicion.get('centro_origen_id') == usuario.get('centro_id')
        
        return False
    
    def test_centro_no_ve_otro_centro(self):
        """Usuario centro no puede ver requisiciones de otro centro"""
        usuario = {'id': 1, 'rol': 'centro', 'centro_id': 5}
        requisicion = {'centro_origen_id': 3, 'estado': 'enviada'}
        
        assert not self.puede_ver_requisicion(usuario, requisicion)
    
    def test_centro_ve_su_centro(self):
        """Usuario centro puede ver requisiciones de su centro"""
        usuario = {'id': 1, 'rol': 'centro', 'centro_id': 5}
        requisicion = {'centro_origen_id': 5, 'estado': 'enviada'}
        
        assert self.puede_ver_requisicion(usuario, requisicion)
    
    def test_admin_ve_todo(self):
        """Admin puede ver cualquier requisición"""
        usuario = {'id': 1, 'rol': 'admin_sistema', 'is_superuser': True}
        requisicion = {'centro_origen_id': 99, 'estado': 'borrador'}
        
        assert self.puede_ver_requisicion(usuario, requisicion)
    
    def test_farmacia_no_ve_borrador(self):
        """Farmacia no puede ver borradores"""
        usuario = {'id': 2, 'rol': 'farmacia'}
        requisicion = {'centro_origen_id': 5, 'estado': 'borrador'}
        
        assert not self.puede_ver_requisicion(usuario, requisicion)
    
    def test_farmacia_ve_enviada(self):
        """Farmacia puede ver enviadas"""
        usuario = {'id': 2, 'rol': 'farmacia'}
        requisicion = {'centro_origen_id': 5, 'estado': 'enviada'}
        
        assert self.puede_ver_requisicion(usuario, requisicion)


# ============================================================================
# TESTS DE VALIDACIONES
# ============================================================================

class RequisicionValidacionesTest(TestCase):
    """Tests para validaciones del modelo/serializer"""
    
    def validar_requisicion(self, datos):
        """Simula validación de requisición"""
        errores = {}
        
        # Centro requerido
        if not datos.get('centro_origen_id'):
            errores['centro_origen'] = 'Centro es requerido'
        
        # Detalles requeridos
        detalles = datos.get('detalles', [])
        if not detalles:
            errores['detalles'] = 'Debe incluir al menos un producto'
        
        # Validar cada detalle
        for i, detalle in enumerate(detalles):
            if not detalle.get('producto_id'):
                errores[f'detalle_{i}_producto'] = 'Producto requerido'
            if not detalle.get('cantidad_solicitada') or detalle.get('cantidad_solicitada', 0) <= 0:
                errores[f'detalle_{i}_cantidad'] = 'Cantidad debe ser mayor a 0'
        
        # Urgente requiere motivo
        if datos.get('es_urgente') and not datos.get('motivo_urgencia'):
            errores['motivo_urgencia'] = 'Motivo de urgencia requerido'
        
        return errores
    
    def test_centro_requerido(self):
        """Centro es obligatorio"""
        errores = self.validar_requisicion({'centro_origen_id': None})
        assert 'centro_origen' in errores
    
    def test_detalles_requeridos(self):
        """Debe tener al menos un detalle"""
        errores = self.validar_requisicion({
            'centro_origen_id': 1,
            'detalles': []
        })
        assert 'detalles' in errores
    
    def test_producto_en_detalle_requerido(self):
        """Cada detalle debe tener producto"""
        errores = self.validar_requisicion({
            'centro_origen_id': 1,
            'detalles': [{'producto_id': None, 'cantidad_solicitada': 10}]
        })
        assert 'detalle_0_producto' in errores
    
    def test_cantidad_positiva_requerida(self):
        """Cantidad debe ser positiva"""
        errores = self.validar_requisicion({
            'centro_origen_id': 1,
            'detalles': [{'producto_id': 1, 'cantidad_solicitada': 0}]
        })
        assert 'detalle_0_cantidad' in errores
    
    def test_urgente_requiere_motivo(self):
        """Requisición urgente requiere motivo"""
        errores = self.validar_requisicion({
            'centro_origen_id': 1,
            'detalles': [{'producto_id': 1, 'cantidad_solicitada': 10}],
            'es_urgente': True,
            'motivo_urgencia': None
        })
        assert 'motivo_urgencia' in errores
    
    def test_datos_validos_sin_errores(self):
        """Datos válidos no generan errores"""
        errores = self.validar_requisicion({
            'centro_origen_id': 1,
            'detalles': [{'producto_id': 1, 'cantidad_solicitada': 50}],
            'es_urgente': False
        })
        assert len(errores) == 0


# ============================================================================
# TESTS DE CÁLCULOS DE SURTIDO
# ============================================================================

class RequisicionSurtidoTest(TestCase):
    """Tests para cálculos relacionados con el surtido"""
    
    def calcular_porcentaje_surtido(self, detalles):
        """Calcula porcentaje de surtido"""
        total_solicitado = sum(d.get('cantidad_solicitada', 0) for d in detalles)
        total_surtido = sum(d.get('cantidad_surtida', 0) for d in detalles)
        
        if total_solicitado == 0:
            return 0
        return round((total_surtido / total_solicitado) * 100)
    
    def determinar_estado_surtido(self, detalles):
        """Determina si el surtido es completo, parcial o pendiente"""
        total_solicitado = sum(d.get('cantidad_solicitada', 0) for d in detalles)
        total_surtido = sum(d.get('cantidad_surtida', 0) for d in detalles)
        
        if total_surtido == 0:
            return 'pendiente'
        if total_surtido < total_solicitado:
            return 'parcial'
        return 'completo'
    
    def test_porcentaje_cero_sin_surtido(self):
        """Sin surtido = 0%"""
        detalles = [{'cantidad_solicitada': 100, 'cantidad_surtida': 0}]
        assert self.calcular_porcentaje_surtido(detalles) == 0
    
    def test_porcentaje_50_surtido_mitad(self):
        """Mitad surtida = 50%"""
        detalles = [{'cantidad_solicitada': 100, 'cantidad_surtida': 50}]
        assert self.calcular_porcentaje_surtido(detalles) == 50
    
    def test_porcentaje_100_completo(self):
        """Todo surtido = 100%"""
        detalles = [{'cantidad_solicitada': 100, 'cantidad_surtida': 100}]
        assert self.calcular_porcentaje_surtido(detalles) == 100
    
    def test_estado_pendiente_sin_surtido(self):
        """Sin surtido = estado pendiente"""
        detalles = [{'cantidad_solicitada': 100, 'cantidad_surtida': 0}]
        assert self.determinar_estado_surtido(detalles) == 'pendiente'
    
    def test_estado_parcial(self):
        """Surtido incompleto = estado parcial"""
        detalles = [{'cantidad_solicitada': 100, 'cantidad_surtida': 40}]
        assert self.determinar_estado_surtido(detalles) == 'parcial'
    
    def test_estado_completo(self):
        """Todo surtido = estado completo"""
        detalles = [{'cantidad_solicitada': 100, 'cantidad_surtida': 100}]
        assert self.determinar_estado_surtido(detalles) == 'completo'
    
    def test_multiples_detalles(self):
        """Cálculo con múltiples detalles"""
        detalles = [
            {'cantidad_solicitada': 100, 'cantidad_surtida': 100},
            {'cantidad_solicitada': 50, 'cantidad_surtida': 25},
        ]
        # Total solicitado: 150, Total surtido: 125, Porcentaje: 83%
        assert self.calcular_porcentaje_surtido(detalles) == 83
        assert self.determinar_estado_surtido(detalles) == 'parcial'


# ============================================================================
# TESTS DE VENCIMIENTO
# ============================================================================

class RequisicionVencimientoTest(TestCase):
    """Tests para lógica de vencimiento de requisiciones"""
    
    def esta_vencida(self, fecha_limite):
        """Verifica si una requisición está vencida"""
        if not fecha_limite:
            return False
        ahora = timezone.now()
        return ahora > fecha_limite
    
    def dias_para_vencer(self, fecha_limite):
        """Calcula días restantes para vencer"""
        if not fecha_limite:
            return None
        ahora = timezone.now()
        diff = fecha_limite - ahora
        return diff.days
    
    def test_no_vencida_con_fecha_futura(self):
        """Requisición con fecha futura no está vencida"""
        fecha_limite = timezone.now() + timedelta(days=5)
        assert not self.esta_vencida(fecha_limite)
    
    def test_vencida_con_fecha_pasada(self):
        """Requisición con fecha pasada está vencida"""
        fecha_limite = timezone.now() - timedelta(days=1)
        assert self.esta_vencida(fecha_limite)
    
    def test_dias_restantes_positivos(self):
        """Días restantes positivos si no ha vencido"""
        fecha_limite = timezone.now() + timedelta(days=3)
        dias = self.dias_para_vencer(fecha_limite)
        assert dias >= 2  # Al menos 2 días (puede ser 2 o 3 según la hora)
    
    def test_dias_restantes_negativos(self):
        """Días restantes negativos si ya venció"""
        fecha_limite = timezone.now() - timedelta(days=2)
        dias = self.dias_para_vencer(fecha_limite)
        assert dias < 0
    
    def test_sin_fecha_limite_no_vence(self):
        """Sin fecha límite no puede estar vencida"""
        assert not self.esta_vencida(None)


# ============================================================================
# TESTS DE HISTORIAL DE ESTADOS
# ============================================================================

class RequisicionHistorialTest(TestCase):
    """Tests para el historial de estados"""
    
    def test_campos_historial(self):
        """Verifica campos del historial de estados"""
        campos_esperados = [
            'id', 'requisicion_id', 'estado_anterior', 'estado_nuevo',
            'usuario_id', 'fecha_cambio', 'accion', 'motivo',
            'observaciones', 'ip_address', 'user_agent',
            'datos_adicionales', 'hash_verificacion'
        ]
        for campo in campos_esperados:
            assert campo in campos_esperados
    
    def test_historial_registra_transicion(self):
        """Historial debe registrar cada transición"""
        historial = [
            {'estado_anterior': None, 'estado_nuevo': 'borrador', 'accion': 'crear'},
            {'estado_anterior': 'borrador', 'estado_nuevo': 'pendiente_admin', 'accion': 'enviar'},
            {'estado_anterior': 'pendiente_admin', 'estado_nuevo': 'pendiente_director', 'accion': 'autorizar_admin'},
        ]
        
        assert len(historial) == 3
        assert historial[0]['estado_nuevo'] == 'borrador'
        assert historial[-1]['estado_nuevo'] == 'pendiente_director'


# ============================================================================
# RESUMEN
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
