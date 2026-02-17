"""
Tests de Escenarios Reales de Negocio - Validación Dual de Contratos
Simula situaciones reales del almacén farmacéutico penitenciario
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from core.models import Lote, Producto, Centro
from inventario.views_legacy import registrar_movimiento_stock
from core.serializers import LoteSerializer
from rest_framework.exceptions import ValidationError

User = get_user_model()


@pytest.fixture
def setup_escenario_real(db):
    """Setup de un escenario real con centros, productos y usuarios"""
    # Centro penitenciario
    centro = Centro.objects.create(
        nombre="Centro Penitenciario Federal #1",
        direccion="Av. Principal #100",
        telefono="555-1234",
        email="cpf1@ssp.gob.mx",
        activo=True
    )
    
    # Productos comunes
    paracetamol = Producto.objects.create(
        id=615,
        clave="615",
        nombre="PARACETAMOL",
        presentacion="500 MG",
        activo=True
    )
    
    amoxicilina = Producto.objects.create(
        id=720,
        clave="720",
        nombre="AMOXICILINA",
        presentacion="500 MG",
        activo=True
    )
    
    ibuprofeno = Producto.objects.create(
        id=850,
        clave="850",
        nombre="IBUPROFENO",
        presentacion="400 MG",
        activo=True
    )
    
    # Usuario admin
    admin = User.objects.create_user(
        username='admin_farmacia',
        email='admin@farmacia.gob.mx',
        password='test123',
        is_staff=True,
        is_superuser=True
    )
    
    return {
        'centro': centro,
        'productos': {
            'paracetamol': paracetamol,
            'amoxicilina': amoxicilina,
            'ibuprofeno': ibuprofeno,
        },
        'admin': admin
    }


@pytest.mark.django_db
class TestEscenarioContratoUnicoCompleto:
    """
    Escenario 1: Contrato con entrega única completa
    Situación: El proveedor entrega el 100% del contrato en un solo lote
    """
    
    def test_entrega_unica_500_unidades(self, setup_escenario_real):
        """
        Contrato: 500 unidades de Paracetamol
        Entrega: 1 lote con 500 unidades
        Esperado: Todo correcto, sin alertas
        """
        config = setup_escenario_real
        
        # Crear lote con entrega completa
        lote_data = {
            'producto': config['productos']['paracetamol'].id,
            'numero_lote': 'LOT-2025-PAR-001',
            'centro': config['centro'].id,
            'fecha_caducidad': '2027-12-31',
            'cantidad_inicial': 500,
            'precio_unitario': '12.50',
            'numero_contrato': 'SSA-2025-CONT-001',
            'cantidad_contrato': 500,  # Límite del lote
            'cantidad_contrato_global': 500,  # Total contratado
            'activo': True,
        }
        
        serializer = LoteSerializer(data=lote_data)
        assert serializer.is_valid(), f"Errores: {serializer.errors}"
        
        # No debe haber alerta
        assert not hasattr(serializer, '_alerta_contrato_global'), \
            "No debe haber alerta en entrega exacta"
        
        lote = serializer.save()
        
        # Verificar cantidades
        assert lote.cantidad_inicial == 500
        assert lote.cantidad_actual == 500
        assert lote.cantidad_contrato == 500
        assert lote.cantidad_contrato_global == 500


@pytest.mark.django_db
class TestEscenarioEntregasParciales:
    """
    Escenario 2: Contrato con entregas parciales múltiples
    Situación: El proveedor entrega en varios lotes hasta completar el contrato
    """
    
    def test_tres_entregas_parciales_completan_contrato(self, setup_escenario_real):
        """
        Contrato: 1000 unidades de Amoxicilina
        Entrega 1: 400 unidades
        Entrega 2: 350 unidades
        Entrega 3: 250 unidades
        Total: 1000 (completo)
        """
        config = setup_escenario_real
        producto = config['productos']['amoxicilina']
        centro = config['centro']
        
        # Primera entrega parcial
        lote1 = Lote.objects.create(
            producto=producto,
            numero_lote='LOT-AMX-2025-001',
            centro=centro,
            fecha_caducidad=date(2027, 6, 30),
            cantidad_inicial=400,
            cantidad_actual=400,
            precio_unitario=Decimal('15.00'),
            numero_contrato='SSA-2025-AMX-001',
            cantidad_contrato=400,  # Límite de ESTE lote
            cantidad_contrato_global=1000,  # Total contratado
            activo=True,
        )
        
        # Segunda entrega parcial
        lote2_data = {
            'producto': producto.id,
            'numero_lote': 'LOT-AMX-2025-002',
            'centro': centro.id,
            'fecha_caducidad': '2027-08-31',
            'cantidad_inicial': 350,
            'precio_unitario': '15.00',
            'numero_contrato': 'SSA-2025-AMX-001',
            'cantidad_contrato': 350,
            # CCG se hereda automáticamente
            'activo': True,
        }
        
        serializer2 = LoteSerializer(data=lote2_data)
        assert serializer2.is_valid()
        lote2 = serializer2.save()
        
        # Verificar herencia de CCG
        assert lote2.cantidad_contrato_global == 1000
        
        # Tercera entrega (completa exacto)
        lote3_data = {
            'producto': producto.id,
            'numero_lote': 'LOT-AMX-2025-003',
            'centro': centro.id,
            'fecha_caducidad': '2027-10-31',
            'cantidad_inicial': 250,
            'precio_unitario': '15.00',
            'numero_contrato': 'SSA-2025-AMX-001',
            'cantidad_contrato': 250,
            'activo': True,
        }
        
        serializer3 = LoteSerializer(data=lote3_data)
        assert serializer3.is_valid()
        
        # No debe haber alerta (suma exacta a 1000)
        assert not hasattr(serializer3, '_alerta_contrato_global')
        
        lote3 = serializer3.save()
        
        # Verificar total recibido
        from django.db.models import Sum
        total_recibido = Lote.objects.filter(
            producto=producto,
            numero_contrato__iexact='SSA-2025-AMX-001',
            activo=True
        ).aggregate(total=Sum('cantidad_inicial'))['total']
        
        assert total_recibido == 1000, "Debe sumar exactamente 1000 unidades"


@pytest.mark.django_db
class TestEscenarioEntradaAdicional:
    """
    Escenario 3: Entrada adicional a un lote existente
    Situación: El lote recibe más producto (reabastecimiento)
    """
    
    def test_entrada_adicional_dentro_limites(self, setup_escenario_real):
        """
        Lote inicial: 200/300 (contrato lote)
        Entrada: +50 unidades
        Resultado: 250/300 ✅
        """
        config = setup_escenario_real
        producto = config['productos']['ibuprofeno']
        
        # Crear lote con espacio disponible
        lote = Lote.objects.create(
            producto=producto,
            numero_lote='LOT-IBU-2025-001',
            centro=config['centro'],
            fecha_caducidad=date(2027, 12, 31),
            cantidad_inicial=200,
            cantidad_actual=200,
            precio_unitario=Decimal('8.50'),
            numero_contrato='SSA-2025-IBU-001',
            cantidad_contrato=300,  # Límite del lote
            cantidad_contrato_global=1000,  # Límite global
            activo=True,
        )
        
        # Registrar entrada adicional
        _, lote_actualizado = registrar_movimiento_stock(
            lote=lote,
            tipo='entrada',
            cantidad=50,
            usuario=config['admin'],
            observaciones='Reabastecimiento autorizado',
            skip_centro_check=True,
        )
        
        # Verificar actualización
        assert lote_actualizado.cantidad_inicial == 250
        assert lote_actualizado.cantidad_actual == 250
    
    def test_entrada_excede_contrato_lote_bloqueada(self, setup_escenario_real):
        """
        Lote inicial: 280/300 (contrato lote)
        Entrada: +50 unidades
        Resultado: ERROR (excedería 330 > 300)
        """
        config = setup_escenario_real
        producto = config['productos']['ibuprofeno']
        
        # Crear lote casi completo
        lote = Lote.objects.create(
            producto=producto,
            numero_lote='LOT-IBU-2025-002',
            centro=config['centro'],
            fecha_caducidad=date(2027, 12, 31),
            cantidad_inicial=280,
            cantidad_actual=280,
            precio_unitario=Decimal('8.50'),
            numero_contrato='SSA-2025-IBU-002',
            cantidad_contrato=300,
            cantidad_contrato_global=1000,
            activo=True,
        )
        
        # Intentar entrada que excede
        with pytest.raises(ValidationError) as exc_info:
            registrar_movimiento_stock(
                lote=lote,
                tipo='entrada',
                cantidad=50,  # 280 + 50 = 330 > 300 ❌
                usuario=config['admin'],
                observaciones='Intento de exceso',
                skip_centro_check=True,
            )
        
        error_msg = str(exc_info.value).lower()
        assert 'excede el contrato' in error_msg and 'lote' in error_msg


@pytest.mark.django_db
class TestEscenarioExcesoGlobal:
    """
    Escenario 4: Exceso en contrato global (permitido con alerta)
    Situación: La suma de lotes excede el CCG pero cada lote está dentro de su límite
    """
    
    def test_multiples_lotes_exceden_global(self, setup_escenario_real):
        """
        CCG: 500 unidades
        Lote 1: 300/400 (dentro de su límite)
        Lote 2: 250/350 (dentro de su límite)
        Total: 550 > 500 ⚠️ (alerta pero permite)
        """
        config = setup_escenario_real
        producto = config['productos']['paracetamol']
        
        # Primer lote
        lote1 = Lote.objects.create(
            producto=producto,
            numero_lote='LOT-PAR-2025-010',
            centro=config['centro'],
            fecha_caducidad=date(2027, 12, 31),
            cantidad_inicial=300,
            cantidad_actual=300,
            precio_unitario=Decimal('12.00'),
            numero_contrato='SSA-2025-PAR-010',
            cantidad_contrato=400,
            cantidad_contrato_global=500,  # Límite global
            activo=True,
        )
        
        # Segundo lote que excede el global
        lote2_data = {
            'producto': producto.id,
            'numero_lote': 'LOT-PAR-2025-011',
            'centro': config['centro'].id,
            'fecha_caducidad': '2027-12-31',
            'cantidad_inicial': 250,  # 300 + 250 = 550 > 500
            'precio_unitario': '12.00',
            'numero_contrato': 'SSA-2025-PAR-010',
            'cantidad_contrato': 350,  # Dentro de SU límite
            'cantidad_contrato_global': 500,
            'activo': True,
        }
        
        serializer = LoteSerializer(data=lote2_data)
        assert serializer.is_valid()
        
        # Debe generar ALERTA pero permitir
        assert hasattr(serializer, '_alerta_contrato_global'), \
            "Debe generar alerta al exceder CCG"
        
        assert '50 unidades' in serializer._alerta_contrato_global, \
            "Debe indicar excedente de 50 unidades"
        
        # Permite crear el lote
        lote2 = serializer.save()
        assert lote2.cantidad_inicial == 250


@pytest.mark.django_db
class TestEscenarioSalidas:
    """
    Escenario 5: Salidas NO afectan validaciones de contrato
    Situación: Las salidas reducen cantidad_actual pero NO cantidad_inicial
    """
    
    def test_salida_reduce_actual_no_inicial(self, setup_escenario_real):
        """
        Lote: 500 inicial, 500 actual
        Salida: 200 unidades
        Resultado: 500 inicial, 300 actual
        """
        config = setup_escenario_real
        producto = config['productos']['amoxicilina']
        
        lote = Lote.objects.create(
            producto=producto,
            numero_lote='LOT-AMX-2025-050',
            centro=config['centro'],
            fecha_caducidad=date(2027, 12, 31),
            cantidad_inicial=500,
            cantidad_actual=500,
            precio_unitario=Decimal('15.00'),
            numero_contrato='SSA-2025-AMX-050',
            cantidad_contrato=500,
            cantidad_contrato_global=1000,
            activo=True,
        )
        
        # Registrar salida
        _, lote_actualizado = registrar_movimiento_stock(
            lote=lote,
            tipo='salida',
            cantidad=200,
            usuario=config['admin'],
            observaciones='Despacho a centro penitenciario',
            skip_centro_check=True,
        )
        
        # Verificar: inicial NO cambia, actual sí
        assert lote_actualizado.cantidad_inicial == 500, \
            "Salida NO debe afectar cantidad_inicial"
        assert lote_actualizado.cantidad_actual == 300, \
            "Salida debe reducir cantidad_actual"


@pytest.mark.django_db
class TestEscenarioMultiplesProvedores:
    """
    Escenario 6: Mismo producto con diferentes contratos
    Situación: Se tiene el mismo producto con contratos distintos
    """
    
    def test_contratos_diferentes_no_se_mezclan(self, setup_escenario_real):
        """
        Producto: Paracetamol
        Contrato A: 500 unidades
        Contrato B: 300 unidades
        Deben validarse independientemente
        """
        config = setup_escenario_real
        producto = config['productos']['paracetamol']
        
        # Contrato A
        lote_a1 = Lote.objects.create(
            producto=producto,
            numero_lote='LOT-PAR-CONT-A-001',
            centro=config['centro'],
            fecha_caducidad=date(2027, 12, 31),
            cantidad_inicial=300,
            cantidad_actual=300,
            precio_unitario=Decimal('12.00'),
            numero_contrato='SSA-2025-PROV-A',
            cantidad_contrato=300,
            cantidad_contrato_global=500,
            activo=True,
        )
        
        # Contrato B (diferente)
        lote_b1_data = {
            'producto': producto.id,
            'numero_lote': 'LOT-PAR-CONT-B-001',
            'centro': config['centro'].id,
            'fecha_caducidad': '2027-12-31',
            'cantidad_inicial': 250,
            'precio_unitario': '11.50',
            'numero_contrato': 'SSA-2025-PROV-B',  # Diferente contrato
            'cantidad_contrato': 250,
            'cantidad_contrato_global': 300,  # Diferente CCG
            'activo': True,
        }
        
        serializer_b = LoteSerializer(data=lote_b1_data)
        assert serializer_b.is_valid()
        
        # NO debe considerar lotes del contrato A
        assert not hasattr(serializer_b, '_alerta_contrato_global')
        
        lote_b1 = serializer_b.save()
        
        # Verificar independencia
        from django.db.models import Sum
        
        total_contrato_a = Lote.objects.filter(
            producto=producto,
            numero_contrato__iexact='SSA-2025-PROV-A',
            activo=True
        ).aggregate(total=Sum('cantidad_inicial'))['total']
        
        total_contrato_b = Lote.objects.filter(
            producto=producto,
            numero_contrato__iexact='SSA-2025-PROV-B',
            activo=True
        ).aggregate(total=Sum('cantidad_inicial'))['total']
        
        assert total_contrato_a == 300, "Contrato A debe tener 300"
        assert total_contrato_b == 250, "Contrato B debe tener 250"


# Resumen de escenarios cubiertos
"""
✅ Escenario 1: Entrega única completa (500/500)
✅ Escenario 2: Entregas parciales múltiples (400+350+250=1000)
✅ Escenario 3: Entrada adicional dentro de límites (200→250/300)
✅ Escenario 4: Entrada adicional excede lote (bloqueada)
✅ Escenario 5: Múltiples lotes exceden global (alerta permitida)
✅ Escenario 6: Salidas NO afectan inicial
✅ Escenario 7: Contratos diferentes independientes
"""
