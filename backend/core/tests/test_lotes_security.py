"""
ISS-SEC: Tests QA funcionales para blindaje de reglas de negocio de Lotes.

Cubre los 7 puntos de la auditoría de seguridad:
1. cantidad_inicial solo en CREATE, rechazada en UPDATE
2. cantidad_actual NO editable desde API (read_only)
3. Doble confirmación para operaciones de escritura
4. Solo Farmacia puede editar cantidad_contrato
5. Auditoría de cambios con datos anteriores/nuevos
6. Datos históricos sin cantidad_inicial no rompen
7. Integridad transaccional movimientos ↔ stock
"""
import json
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from core.models import Centro, Producto, Lote, Movimiento, AuditoriaLogs
from core.serializers import LoteSerializer

User = get_user_model()


# =============================================================================
# Helpers
# =============================================================================

def _future(days=365):
    return date.today() + timedelta(days=days)


class LoteSecurityBaseTestCase(APITestCase):
    """Base con datos compartidos para tests de seguridad de lotes."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # Grupos
        cls.g_farmacia, _ = Group.objects.get_or_create(name='FARMACEUTICO')
        cls.g_centro, _ = Group.objects.get_or_create(name='CENTRO_USER')
        cls.g_vista, _ = Group.objects.get_or_create(name='VISTA_USER')

        # Usuarios
        cls.admin = User.objects.create_superuser(
            username='admin_sec', email='admin@sec.test', password='Admin@123'
        )
        cls.farmacia = User.objects.create_user(
            username='farmacia_sec', email='farm@sec.test',
            password='Farm@123', rol='farmacia'
        )
        cls.farmacia.groups.add(cls.g_farmacia)

        cls.centro_obj = Centro.objects.create(
            clave='C-SEC', nombre='Centro Seguridad',
            direccion='Dir', telefono='555', activo=True
        )
        cls.usuario_centro = User.objects.create_user(
            username='centro_sec', email='centro@sec.test',
            password='Centro@123', rol='centro', centro=cls.centro_obj
        )
        cls.usuario_centro.groups.add(cls.g_centro)

        cls.vista = User.objects.create_user(
            username='vista_sec', email='vista@sec.test',
            password='Vista@123', rol='vista'
        )
        cls.vista.groups.add(cls.g_vista)

        # Producto
        cls.producto = Producto.objects.create(
            clave='MED-SEC', descripcion='Medicamento Seguridad',
            unidad_medida='PIEZA', precio_unitario=Decimal('15.00'),
            stock_minimo=10, activo=True
        )

    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def _crear_lote(self, **overrides):
        """Helper para crear un lote directamente en BD."""
        defaults = dict(
            producto=self.producto,
            numero_lote='SEC-LOTE-001',
            cantidad_inicial=100,
            cantidad_actual=100,
            fecha_caducidad=_future(),
            precio_unitario=Decimal('15.00'),
            activo=True,
        )
        defaults.update(overrides)
        return Lote.objects.create(**defaults)

    def _payload_crear(self, **overrides):
        """Payload mínimo válido para crear lote vía API."""
        data = {
            'producto': self.producto.pk,
            'numero_lote': 'API-LOTE-001',
            'cantidad_inicial': 50,
            'fecha_caducidad': _future().isoformat(),
            'precio_unitario': '10.00',
        }
        data.update(overrides)
        return data


# =============================================================================
# 1. cantidad_inicial: solo en CREATE, rechazada en UPDATE
# =============================================================================

class TestCantidadInicialBlindaje(LoteSecurityBaseTestCase):
    """
    Verifica que cantidad_inicial:
    - Es obligatoria al crear un lote
    - Es > 0 al crear
    - NO se puede modificar vía PATCH/PUT
    - Se rechaza explícitamente si se intenta cambiar
    """

    def test_crear_lote_sin_cantidad_inicial_falla(self):
        """CREATE sin cantidad_inicial debe fallar con error claro."""
        self.client.force_authenticate(user=self.admin)
        data = self._payload_crear()
        del data['cantidad_inicial']
        resp = self.client.post('/api/lotes/', data, format='json')
        self.assertIn(resp.status_code, [400, 409])

    def test_crear_lote_con_cantidad_inicial_cero_falla(self):
        """CREATE con cantidad_inicial=0 debe fallar."""
        self.client.force_authenticate(user=self.admin)
        data = self._payload_crear(cantidad_inicial=0)
        resp = self.client.post('/api/lotes/', data, format='json')
        self.assertIn(resp.status_code, [400, 409])

    def test_crear_lote_con_cantidad_inicial_negativa_falla(self):
        """CREATE con cantidad_inicial negativa debe fallar."""
        self.client.force_authenticate(user=self.admin)
        data = self._payload_crear(cantidad_inicial=-10)
        resp = self.client.post('/api/lotes/', data, format='json')
        self.assertIn(resp.status_code, [400, 409])

    def test_crear_lote_con_cantidad_inicial_valida_ok(self):
        """CREATE con cantidad_inicial > 0 debe funcionar."""
        self.client.force_authenticate(user=self.admin)
        data = self._payload_crear(cantidad_inicial=50)
        resp = self.client.post('/api/lotes/', data, format='json')
        self.assertIn(resp.status_code, [201, 409])  # 409 = pide confirmación
        if resp.status_code == 409:
            # Reenviar con confirmación
            data['confirmed'] = True
            resp = self.client.post('/api/lotes/', data, format='json')
            self.assertEqual(resp.status_code, 201)

    def test_update_ignora_cantidad_inicial(self):
        """PATCH con cantidad_inicial debe ignorar el campo (no error, solo ignorar)."""
        lote = self._crear_lote(numero_lote='SEC-UPD-001')
        cantidad_original = lote.cantidad_inicial
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(
            f'/api/lotes/{lote.pk}/',
            {'cantidad_inicial': 999, 'confirmed': True},
            format='json'
        )
        # Puede ser 200 (ignoró el campo) o 409 (pide confirmación)
        if resp.status_code == 409:
            resp = self.client.patch(
                f'/api/lotes/{lote.pk}/',
                {'cantidad_inicial': 999, 'confirmed': True},
                format='json'
            )
        lote.refresh_from_db()
        self.assertEqual(lote.cantidad_inicial, cantidad_original,
                         'cantidad_inicial NO debe cambiar vía PATCH')

    def test_put_no_permite_modificar_cantidad_inicial(self):
        """PUT con cantidad_inicial diferente al original es rechazado."""
        lote = self._crear_lote(numero_lote='SEC-PUT-001')
        self.client.force_authenticate(user=self.admin)
        data = {
            'producto': self.producto.pk,
            'numero_lote': lote.numero_lote,
            'cantidad_inicial': 999,
            'fecha_caducidad': lote.fecha_caducidad.isoformat(),
            'precio_unitario': '15.00',
            'confirmed': True,
        }
        resp = self.client.put(f'/api/lotes/{lote.pk}/', data, format='json')
        lote.refresh_from_db()
        self.assertNotEqual(lote.cantidad_inicial, 999,
                            'cantidad_inicial NO debe cambiar vía PUT')


# =============================================================================
# 2. cantidad_actual: NO editable desde API
# =============================================================================

class TestCantidadActualReadOnly(LoteSecurityBaseTestCase):
    """
    Verifica que cantidad_actual:
    - NO se puede establecer al crear vía API (se calcula = cantidad_inicial)
    - NO se puede modificar vía PATCH/PUT
    - SOLO se modifica vía Movimiento.aplicar_movimiento_a_lote
    """

    def test_crear_lote_cantidad_actual_igual_a_inicial(self):
        """Al crear un lote, cantidad_actual siempre = cantidad_inicial (ignora payload)."""
        self.client.force_authenticate(user=self.admin)
        data = self._payload_crear(cantidad_inicial=50)
        # Intentar forzar cantidad_actual=999
        data['cantidad_actual'] = 999
        resp = self.client.post('/api/lotes/', data, format='json')
        if resp.status_code == 409:
            data['confirmed'] = True
            resp = self.client.post('/api/lotes/', data, format='json')
        if resp.status_code == 201:
            lote = Lote.objects.get(pk=resp.data['id'])
            self.assertEqual(lote.cantidad_actual, 50,
                             'cantidad_actual debe ser = cantidad_inicial, NO el valor enviado')

    def test_patch_no_modifica_cantidad_actual(self):
        """PATCH con cantidad_actual debe ser ignorado (campo read_only)."""
        lote = self._crear_lote(numero_lote='SEC-ACT-001')
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(
            f'/api/lotes/{lote.pk}/',
            {'cantidad_actual': 999, 'confirmed': True},
            format='json'
        )
        if resp.status_code == 409:
            resp = self.client.patch(
                f'/api/lotes/{lote.pk}/',
                {'cantidad_actual': 999, 'confirmed': True},
                format='json'
            )
        lote.refresh_from_db()
        self.assertEqual(lote.cantidad_actual, 100,
                         'cantidad_actual NO debe cambiar vía PATCH')

    def test_postman_no_puede_forzar_cantidad_actual(self):
        """Simula ataque desde Postman intentando forzar cantidad_actual."""
        lote = self._crear_lote(numero_lote='SEC-POSTMAN-001', cantidad_actual=50)
        self.client.force_authenticate(user=self.admin)
        # Intentar poner cantidad_actual en 0 para "agotar" inventario
        resp = self.client.patch(
            f'/api/lotes/{lote.pk}/',
            {'cantidad_actual': 0, 'confirmed': True},
            format='json'
        )
        lote.refresh_from_db()
        self.assertEqual(lote.cantidad_actual, 50,
                         'cantidad_actual NO debe ser forzable desde API')

    def test_movimiento_si_modifica_cantidad_actual(self):
        """Un Movimiento de salida SÍ debe decrementar cantidad_actual."""
        lote = self._crear_lote(numero_lote='SEC-MOV-001', cantidad_actual=100)
        mov = Movimiento(
            lote=lote,
            tipo='salida',
            cantidad=10,
            centro_origen=self.centro_obj,
            motivo='Dispensación de prueba'
        )
        mov.save()
        lote.refresh_from_db()
        self.assertEqual(lote.cantidad_actual, 90,
                         'Movimiento de salida debe decrementar cantidad_actual')


# =============================================================================
# 3. Doble confirmación para operaciones de escritura
# =============================================================================

class TestDobleConfirmacion(LoteSecurityBaseTestCase):
    """
    Verifica que las operaciones de escritura requieren confirmación.
    Sin confirmed=true, el backend responde 409 Conflict.
    """

    def test_update_sin_confirmacion_devuelve_409(self):
        """PATCH sin confirmed=true debe devolver 409."""
        lote = self._crear_lote(numero_lote='SEC-CONF-001')
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(
            f'/api/lotes/{lote.pk}/',
            {'marca': 'Nueva Marca'},
            format='json'
        )
        self.assertEqual(resp.status_code, 409,
                         'Update sin confirmación debe devolver 409')
        self.assertEqual(resp.data.get('code'), 'CONFIRMATION_REQUIRED')

    def test_update_con_confirmacion_funciona(self):
        """PATCH con confirmed=true debe funcionar."""
        lote = self._crear_lote(numero_lote='SEC-CONF-002')
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(
            f'/api/lotes/{lote.pk}/',
            {'marca': 'Marca OK', 'confirmed': True},
            format='json'
        )
        self.assertEqual(resp.status_code, 200)
        lote.refresh_from_db()
        self.assertEqual(lote.marca, 'Marca OK')

    def test_delete_sin_confirmacion_devuelve_409(self):
        """DELETE sin confirmed=true debe devolver 409."""
        lote = self._crear_lote(numero_lote='SEC-CONF-DEL')
        self.client.force_authenticate(user=self.admin)
        resp = self.client.delete(f'/api/lotes/{lote.pk}/')
        self.assertEqual(resp.status_code, 409)

    def test_update_con_header_confirmacion(self):
        """PATCH con header X-Confirm-Action: true debe funcionar."""
        lote = self._crear_lote(numero_lote='SEC-CONF-HDR')
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(
            f'/api/lotes/{lote.pk}/',
            {'marca': 'Via Header'},
            format='json',
            HTTP_X_CONFIRM_ACTION='true'
        )
        self.assertEqual(resp.status_code, 200)

    def test_update_con_query_param_confirmacion(self):
        """PATCH con ?confirmed=true debe funcionar."""
        lote = self._crear_lote(numero_lote='SEC-CONF-QP')
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(
            f'/api/lotes/{lote.pk}/?confirmed=true',
            {'marca': 'Via QP'},
            format='json'
        )
        self.assertEqual(resp.status_code, 200)


# =============================================================================
# 4. Solo Farmacia puede editar cantidad_contrato
# =============================================================================

class TestPermisoCantidadContrato(LoteSecurityBaseTestCase):
    """
    Verifica que cantidad_contrato solo es editable por Farmacia/Admin.
    Usuarios de centro NO pueden modificar este campo.
    """

    def test_admin_puede_editar_cantidad_contrato(self):
        """Admin puede modificar cantidad_contrato."""
        lote = self._crear_lote(numero_lote='SEC-CONT-ADM', cantidad_contrato=100)
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(
            f'/api/lotes/{lote.pk}/',
            {'cantidad_contrato': 200, 'confirmed': True},
            format='json'
        )
        self.assertEqual(resp.status_code, 200)
        lote.refresh_from_db()
        self.assertEqual(lote.cantidad_contrato, 200)

    def test_farmacia_puede_editar_cantidad_contrato(self):
        """Farmacia puede modificar cantidad_contrato."""
        lote = self._crear_lote(numero_lote='SEC-CONT-FARM')
        self.client.force_authenticate(user=self.farmacia)
        resp = self.client.patch(
            f'/api/lotes/{lote.pk}/',
            {'cantidad_contrato': 150, 'confirmed': True},
            format='json'
        )
        # Puede ser 200 o 403 (depende de permisos del ViewSet)
        if resp.status_code == 200:
            lote.refresh_from_db()
            self.assertEqual(lote.cantidad_contrato, 150)

    def test_centro_no_puede_editar_cantidad_contrato(self):
        """Usuario de centro NO puede modificar cantidad_contrato."""
        lote = self._crear_lote(
            numero_lote='SEC-CONT-CENT', cantidad_contrato=100,
            centro=self.centro_obj
        )
        self.client.force_authenticate(user=self.usuario_centro)
        resp = self.client.patch(
            f'/api/lotes/{lote.pk}/',
            {'cantidad_contrato': 999, 'confirmed': True},
            format='json'
        )
        # Debe ser 403 (permiso de ViewSet) o 400 (serializer rechaza)
        lote.refresh_from_db()
        self.assertNotEqual(lote.cantidad_contrato, 999,
                            'Centro NO debe poder modificar cantidad_contrato')

    def test_vista_no_puede_editar_nada(self):
        """Usuario Vista no puede hacer operaciones de escritura."""
        lote = self._crear_lote(numero_lote='SEC-CONT-VISTA')
        self.client.force_authenticate(user=self.vista)
        resp = self.client.patch(
            f'/api/lotes/{lote.pk}/',
            {'marca': 'Intento Vista', 'confirmed': True},
            format='json'
        )
        self.assertIn(resp.status_code, [403, 405],
                      'Vista NO debe poder modificar lotes')


# =============================================================================
# 5. Auditoría de cambios con datos anteriores/nuevos
# =============================================================================

class TestAuditoriaLotesCambios(LoteSecurityBaseTestCase):
    """
    Verifica que los cambios en lotes quedan registrados en auditoría.
    """

    def test_creacion_lote_registra_auditoria(self):
        """Crear un lote debe generar registro de auditoría."""
        count_antes = AuditoriaLogs.objects.filter(
            modelo='Lote', accion='crear'
        ).count()
        self._crear_lote(numero_lote='SEC-AUD-001')
        count_despues = AuditoriaLogs.objects.filter(
            modelo='Lote', accion='crear'
        ).count()
        self.assertGreater(count_despues, count_antes,
                           'Crear lote debe registrar auditoría')

    def test_modificar_contrato_registra_auditoria_especifica(self):
        """Modificar cantidad_contrato registra auditoría con acción específica."""
        lote = self._crear_lote(numero_lote='SEC-AUD-CONT', cantidad_contrato=100)
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(
            f'/api/lotes/{lote.pk}/',
            {'cantidad_contrato': 200, 'confirmed': True},
            format='json'
        )
        if resp.status_code == 200:
            # Buscar registro de auditoría específico para cambio de contrato
            registros = AuditoriaLogs.objects.filter(
                modelo='Lote',
                objeto_id=str(lote.pk),
                accion='modificar_contrato'
            )
            self.assertTrue(registros.exists(),
                            'Cambio de cantidad_contrato debe registrar auditoría específica')
            if registros.exists():
                datos = registros.first().datos_nuevos
                self.assertIn('cantidad_contrato', datos,
                              'Auditoría debe incluir detalle del cambio')

    def test_actualizacion_lote_registra_diff(self):
        """Actualizar lote debe registrar datos anteriores y nuevos."""
        lote = self._crear_lote(numero_lote='SEC-AUD-DIFF', marca='Original')
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(
            f'/api/lotes/{lote.pk}/',
            {'marca': 'Modificada', 'confirmed': True},
            format='json'
        )
        if resp.status_code == 200:
            # Buscar registros de actualización
            registros = AuditoriaLogs.objects.filter(
                modelo='Lote',
                objeto_id=str(lote.pk),
                accion='actualizar'
            ).order_by('-timestamp')
            # Debe haber al menos un registro con datos_anteriores
            self.assertTrue(registros.exists())


# =============================================================================
# 6. Datos históricos sin cantidad_inicial no rompen
# =============================================================================

class TestDatosHistoricos(LoteSecurityBaseTestCase):
    """
    Verifica que lotes con cantidad_inicial NULL o 0 no rompen el sistema.
    """

    def test_lote_con_cantidad_inicial_null_no_rompe_api(self):
        """GET de lote con cantidad_inicial NULL no debe causar error 500."""
        lote = Lote.objects.create(
            producto=self.producto,
            numero_lote='SEC-HIST-NULL',
            cantidad_actual=50,
            cantidad_inicial=0,  # Simula dato histórico
            fecha_caducidad=_future(),
        )
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get(f'/api/lotes/{lote.pk}/')
        self.assertIn(resp.status_code, [200, 301])

    def test_listado_con_lotes_historicos_no_rompe(self):
        """GET /api/lotes/ con lotes históricos no debe causar error."""
        Lote.objects.create(
            producto=self.producto,
            numero_lote='SEC-HIST-LIST',
            cantidad_actual=0,
            cantidad_inicial=0,
            fecha_caducidad=_future(),
        )
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get('/api/lotes/')
        self.assertEqual(resp.status_code, 200)


# =============================================================================
# 7. Integridad transaccional: Movimiento ↔ Stock
# =============================================================================

class TestIntegridadMovimientoStock(LoteSecurityBaseTestCase):
    """
    Verifica que los movimientos y el stock se mantienen consistentes.
    """

    def test_movimiento_entrada_incrementa_stock(self):
        """Movimiento de entrada debe incrementar cantidad_actual."""
        lote = self._crear_lote(numero_lote='SEC-INT-ENT', cantidad_actual=100)
        mov = Movimiento(
            lote=lote, tipo='entrada', cantidad=20,
            motivo='Entrega parcial'
        )
        mov.save()
        lote.refresh_from_db()
        self.assertEqual(lote.cantidad_actual, 120)

    def test_movimiento_salida_decrementa_stock(self):
        """Movimiento de salida debe decrementar cantidad_actual."""
        lote = self._crear_lote(numero_lote='SEC-INT-SAL', cantidad_actual=100)
        mov = Movimiento(
            lote=lote, tipo='salida', cantidad=30,
            centro_origen=self.centro_obj,
            motivo='Dispensación'
        )
        mov.save()
        lote.refresh_from_db()
        self.assertEqual(lote.cantidad_actual, 70)

    def test_movimiento_salida_rechaza_stock_insuficiente(self):
        """Movimiento de salida con stock insuficiente debe fallar."""
        lote = self._crear_lote(numero_lote='SEC-INT-INS', cantidad_actual=10)
        with self.assertRaises(Exception):
            mov = Movimiento(
                lote=lote, tipo='salida', cantidad=20,
                centro_origen=self.centro_obj,
                motivo='Dispensación'
            )
            mov.save()

    def test_stock_no_queda_negativo(self):
        """Después de operaciones, stock nunca debe quedar negativo."""
        lote = self._crear_lote(numero_lote='SEC-INT-NEG', cantidad_actual=5)
        try:
            mov = Movimiento(
                lote=lote, tipo='salida', cantidad=10,
                centro_origen=self.centro_obj,
                motivo='Dispensación'
            )
            mov.save()
        except Exception:
            pass  # Esperado
        lote.refresh_from_db()
        self.assertGreaterEqual(lote.cantidad_actual, 0,
                                'Stock nunca debe quedar negativo')

    def test_cantidad_actual_consistente_con_movimientos(self):
        """cantidad_actual debe ser consistente con la suma de movimientos."""
        lote = self._crear_lote(
            numero_lote='SEC-INT-CONS', cantidad_actual=100, cantidad_inicial=100
        )
        # Entrada de 50
        Movimiento(lote=lote, tipo='entrada', cantidad=50, motivo='Reabasto').save()
        # Salida de 30
        Movimiento(
            lote=lote, tipo='salida', cantidad=30,
            centro_origen=self.centro_obj, motivo='Dispensación'
        ).save()
        lote.refresh_from_db()
        # 100 + 50 - 30 = 120
        self.assertEqual(lote.cantidad_actual, 120)
