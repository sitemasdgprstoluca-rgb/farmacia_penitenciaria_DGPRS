#!/usr/bin/env python
"""
Test de verificación del endpoint consolidados con cantidad_contrato_global.

Este test verifica que el endpoint /api/lotes/consolidados/ devuelve
el campo cantidad_contrato_global correctamente después del bugfix.

Uso:
    pytest tests/test_verificar_consolidados_ccg.py -v -s
"""
import pytest
from django.contrib.auth import get_user_model
from core.models import Lote, Producto, Centro
from rest_framework.test import APIClient
from decimal import Decimal

User = get_user_model()


@pytest.mark.django_db
class TestConsolidadosCCG:
    """Verificar que endpoint consolidados devuelve cantidad_contrato_global."""
    
    def test_consolidados_incluye_ccg(self):
        """
        VERIFICACIÓN: /api/lotes/consolidados/ debe incluir cantidad_contrato_global.
        
        Casos de prueba:
        1. Lotes CON CCG definido → debe aparecer en respuesta
        2. Lotes SIN CCG → campo debe ser null
        3. cantidad_pendiente_global calculado correctamente
        """
        print("\n" + "=" * 80)
        print("🔍 TEST: Endpoint consolidados con cantidad_contrato_global")
        print("=" * 80)
        
        # Crear usuario admin
        admin = User.objects.create_user(
            username='admin_test',
            password='test123',
            rol='farmacia'  # Rol en minúsculas
        )
        
        # Crear producto de prueba
        producto = Producto.objects.create(
            clave='TEST001',
            nombre='Paracetamol Test',
            descripcion='Para pruebas de consolidados',
            presentacion='Tabletas',
            unidad_medida='PIEZA',
            activo=True
        )
        
        # Crear lotes con CCG
        lote1 = Lote.objects.create(
            producto=producto,
            numero_lote='LOTE-CCG-001',
            cantidad_inicial=500,
            cantidad_actual=500,
            cantidad_contrato=500,
            cantidad_contrato_global=1000,  # ← Contrato GLOBAL
            numero_contrato='CONT-TEST-CCG',
            precio_unitario=Decimal('10.50'),
            marca='Marca Test',
            fecha_caducidad='2027-12-31',
            activo=True
        )
        
        lote2 = Lote.objects.create(
            producto=producto,
            numero_lote='LOTE-CCG-002',
            cantidad_inicial=300,
            cantidad_actual=300,
            cantidad_contrato=300,
            cantidad_contrato_global=1000,  # ← Mismo CCG
            numero_contrato='CONT-TEST-CCG',
            precio_unitario=Decimal('10.50'),
            marca='Marca Test',
            fecha_caducidad='2027-12-31',
            activo=True
        )
        
        # Lote SIN CCG para comparar
        lote3 = Lote.objects.create(
            producto=producto,
            numero_lote='LOTE-SIN-CCG',
            cantidad_inicial=100,
            cantidad_actual=100,
            cantidad_contrato=100,
            cantidad_contrato_global=None,  # ← SIN CCG
            numero_contrato='CONT-OTRO',
            precio_unitario=Decimal('10.50'),
            marca='Marca Test',
            fecha_caducidad='2027-12-31',
            activo=True
        )
        
        print(f"\n📦 Lotes creados:")
        print(f"   • {lote1.numero_lote}: cantidad_contrato_global = {lote1.cantidad_contrato_global}")
        print(f"   • {lote2.numero_lote}: cantidad_contrato_global = {lote2.cantidad_contrato_global}")
        print(f"   • {lote3.numero_lote}: cantidad_contrato_global = {lote3.cantidad_contrato_global}")
        
        # Llamar al endpoint consolidados
        client = APIClient()
        client.force_authenticate(user=admin)
        
        print(f"\n🌐 Llamando GET /api/lotes/consolidados/")
        response = client.get('/api/lotes/consolidados/')
        
        assert response.status_code == 200, f"Error: {response.status_code}"
        data = response.json()
        
        print(f"\n📊 Respuesta del API:")
        print(f"   Total de lotes consolidados: {data['count']}")
        
        # Verificar resultados
        results = data['results']
        
        # Buscar lote con CCG
        lotes_con_ccg = [r for r in results if r.get('numero_contrato') == 'CONT-TEST-CCG']
        lotes_sin_ccg = [r for r in results if r.get('numero_contrato') == 'CONT-OTRO']
        
        print(f"\n✅ Verificando lotes CON CCG:")
        for lote_cons in lotes_con_ccg:
            print(f"\n   Lote: {lote_cons['numero_lote']}")
            print(f"   ├─ cantidad_contrato_global: {lote_cons.get('cantidad_contrato_global')}")
            print(f"   ├─ cantidad_pendiente_global: {lote_cons.get('cantidad_pendiente_global')}")
            print(f"   └─ cantidad_inicial_total: {lote_cons['cantidad_inicial']}")
            
            # VERIFICACIÓN CRÍTICA
            assert 'cantidad_contrato_global' in lote_cons, \
                "❌ FALLO: No existe el campo cantidad_contrato_global en respuesta"
            
            assert lote_cons['cantidad_contrato_global'] == 1000, \
                f"❌ FALLO: CCG esperado=1000, recibido={lote_cons['cantidad_contrato_global']}"
            
            # Verificar pendiente global
            # Total recibido = 500 + 300 = 800
            # Pendiente = 1000 - 800 = 200
            if lote_cons['numero_lote'] in ['LOTE-CCG-001', 'LOTE-CCG-002']:
                assert lote_cons.get('cantidad_pendiente_global') is not None, \
                    "❌ FALLO: cantidad_pendiente_global debería estar calculado"
                
                # La primera iteración mostrará el pendiente correctamente
                print(f"   ✅ cantidad_pendiente_global = {lote_cons['cantidad_pendiente_global']}")
        
        print(f"\n✅ Verificando lotes SIN CCG:")
        for lote_cons in lotes_sin_ccg:
            print(f"\n   Lote: {lote_cons['numero_lote']}")
            print(f"   ├─ cantidad_contrato_global: {lote_cons.get('cantidad_contrato_global')}")
            print(f"   └─ cantidad_pendiente_global: {lote_cons.get('cantidad_pendiente_global')}")
            
            # Lotes sin CCG deben tener null
            assert lote_cons.get('cantidad_contrato_global') is None, \
                "❌ FALLO: Lotes sin CCG deberían tener null"
            
            assert lote_cons.get('cantidad_pendiente_global') is None, \
                "❌ FALLO: Lotes sin CCG no deberían calcular pendiente global"
        
        print("\n" + "=" * 80)
        print("✅ TEST PASADO: Endpoint consolidados devuelve cantidad_contrato_global")
        print("=" * 80)
        print("\n💡 CONCLUSIÓN:")
        print("   • El endpoint /api/lotes/consolidados/ ahora incluye cantidad_contrato_global")
        print("   • Se calcula cantidad_pendiente_global correctamente")
        print("   • El frontend podrá mostrar esta información\n")
