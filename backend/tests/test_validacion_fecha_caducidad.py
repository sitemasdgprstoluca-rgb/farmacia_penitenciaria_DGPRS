"""
Test de validación de fechas de caducidad.
Verifica que el sistema rechace fechas de caducidad mayores a 8 años en el futuro.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from core.models import User, Centro, Producto, Lote
from core.serializers import LoteSerializer


class ValidacionFechaCaducidadTestCase(TestCase):
    """Pruebas de validación de fechas de caducidad"""
    
    def setUp(self):
        """Configuración inicial para las pruebas"""
        # Crear usuario administrador
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='admin123',
            first_name='Admin',
            last_name='Test'
        )
        
        # Crear centro de prueba
        self.centro = Centro.objects.create(
            nombre='Centro Prueba',
            activo=True
        )
        
        # Crear producto de prueba
        self.producto = Producto.objects.create(
            clave='PROD001',
            nombre='Producto Prueba',
            descripcion='Descripción de prueba',
            stock_minimo=10,
            activo=True
        )
        
        # Cliente API
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)
    
    def test_fecha_caducidad_valida_dentro_8_anios(self):
        """Test: Fecha de caducidad válida dentro de 8 años debe ser aceptada"""
        fecha_valida = date.today() + timedelta(days=7*365)  # 7 años
        
        data = {
            'producto': self.producto.id,
            'numero_lote': 'LOTE-TEST-001',
            'fecha_caducidad': fecha_valida.isoformat(),
            'cantidad_inicial': 100,
            'precio_unitario': 50.00,
            'centro': self.centro.id,
        }
        
        serializer = LoteSerializer(data=data)
        self.assertTrue(serializer.is_valid(), f"Errores: {serializer.errors}")
        lote = serializer.save()
        self.assertEqual(lote.fecha_caducidad, fecha_valida)
    
    def test_fecha_caducidad_invalida_mayor_8_anios(self):
        """Test: Fecha de caducidad mayor a 8 años debe ser rechazada"""
        fecha_invalida = date.today() + timedelta(days=9*365)  # 9 años
        
        data = {
            'producto': self.producto.id,
            'numero_lote': 'LOTE-TEST-002',
            'fecha_caducidad': fecha_invalida.isoformat(),
            'cantidad_inicial': 100,
            'precio_unitario': 50.00,
            'centro': self.centro.id,
        }
        
        serializer = LoteSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('fecha_caducidad', serializer.errors)
        error_msg = str(serializer.errors['fecha_caducidad'][0])
        self.assertIn('muy lejana', error_msg.lower())
        self.assertIn('8 años', error_msg.lower())
    
    def test_fecha_caducidad_invalida_anio_4013(self):
        """Test: Fecha con error de digitación (año 4013) debe ser rechazada"""
        fecha_invalida = date(4013, 9, 25)  # Error típico: 2013 -> 4013
        
        data = {
            'producto': self.producto.id,
            'numero_lote': 'LOTE-TEST-003',
            'fecha_caducidad': fecha_invalida.isoformat(),
            'cantidad_inicial': 100,
            'precio_unitario': 50.00,
            'centro': self.centro.id,
        }
        
        serializer = LoteSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('fecha_caducidad', serializer.errors)
    
    def test_fecha_caducidad_limite_exacto_8_anios(self):
        """Test: Fecha exactamente a 8 años debe ser aceptada"""
        fecha_limite = date.today() + timedelta(days=8*365)
        
        data = {
            'producto': self.producto.id,
            'numero_lote': 'LOTE-TEST-004',
            'fecha_caducidad': fecha_limite.isoformat(),
            'cantidad_inicial': 100,
            'precio_unitario': 50.00,
            'centro': self.centro.id,
        }
        
        serializer = LoteSerializer(data=data)
        self.assertTrue(serializer.is_valid(), f"Errores: {serializer.errors}")
    
    def test_api_crear_lote_fecha_invalida(self):
        """Test: API debe rechazar lote con fecha de caducidad inválida"""
        fecha_invalida = date.today() + timedelta(days=10*365)  # 10 años
        
        data = {
            'producto': self.producto.id,
            'numero_lote': 'LOTE-API-001',
            'fecha_caducidad': fecha_invalida.isoformat(),
            'cantidad_inicial': 100,
            'precio_unitario': 50.00,
            'centro': self.centro.id,
        }
        
        response = self.client.post('/api/lotes/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # El error puede estar en 'fecha_caducidad' directamente o en 'detalles'
        tiene_error = ('fecha_caducidad' in response.data or 
                      ('detalles' in response.data and 'fecha_caducidad' in response.data['detalles']))
        self.assertTrue(tiene_error, f"No se encontró error de fecha_caducidad en: {response.data}")
    
    def test_api_crear_lote_fecha_valida(self):
        """Test: API debe aceptar lote con fecha de caducidad válida"""
        fecha_valida = date.today() + timedelta(days=3*365)  # 3 años
        
        data = {
            'producto': self.producto.id,
            'numero_lote': 'LOTE-API-002',
            'fecha_caducidad': fecha_valida.isoformat(),
            'cantidad_inicial': 100,
            'precio_unitario': 50.00,
            'centro': self.centro.id,
        }
        
        response = self.client.post('/api/lotes/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['fecha_caducidad'], fecha_valida.isoformat())


@pytest.mark.django_db
class TestImportacionExcelFechasCaducidad:
    """Pruebas de importación Excel con validación de fechas"""
    
    @pytest.fixture(autouse=True)
    def setup(self, django_db_setup, django_db_blocker):
        """Configuración para cada prueba"""
        with django_db_blocker.unblock():
            # Crear usuario admin
            self.admin = User.objects.create_superuser(
                username='admin_import',
                email='admin_import@test.com',
                password='admin123',
                first_name='Admin',
                last_name='Import'
            )
            
            # Crear centro
            self.centro = Centro.objects.create(
                nombre='Centro Import',
                activo=True
            )
            
            # Crear producto
            self.producto = Producto.objects.create(
                clave='PROD-IMPORT',
                nombre='Producto Importación',
                descripcion='Para pruebas de importación',
                stock_minimo=10,
                activo=True
            )
    
    def test_importacion_rechaza_fecha_invalida(self):
        """Test: Importación debe rechazar fechas con error de digitación"""
        from core.utils.excel_importer import importar_lotes_desde_excel
        import openpyxl
        from io import BytesIO
        from datetime import date
        
        # Crear Excel con fecha inválida
        wb = openpyxl.Workbook()
        ws = wb.active
        
        # Headers
        ws.append(['Clave', 'Nombre Producto', 'Lote', 'Cantidad Inicial', 'Fecha Caducidad', 'Precio'])
        
        # Fila con fecha inválida (año 4013)
        ws.append(['PROD-IMPORT', 'Producto Importación', 'LOTE-ERR-001', 100, '25/09/4013', 50.00])
        
        # Guardar en BytesIO
        excel_file = BytesIO()
        wb.save(excel_file)
        excel_file.seek(0)
        excel_file.name = 'test_import.xlsx'
        
        # Importar
        resultado = importar_lotes_desde_excel(excel_file, self.admin, centro_id=self.centro.id)
        
        # Debug: Imprimir resultado
        print(f"\n=== RESULTADO DEBUG ===")
        print(f"Registros exitosos: {resultado['registros_exitosos']}")
        print(f"Registros fallidos: {resultado['registros_fallidos']}")
        print(f"Errores: {resultado['errores']}")
        
        # Verificar que fue rechazado (el resultado es un dict)
        assert resultado['registros_fallidos'] > 0
        assert resultado['registros_exitosos'] == 0
        assert len(resultado['errores']) > 0
        
        # Verificar mensaje de error
        error_encontrado = False
        for error in resultado['errores']:
            if 'muy lejana' in error['error'].lower() or '8 años' in error['error'].lower():
                error_encontrado = True
                break
        
        assert error_encontrado, f"No se encontró el mensaje de error esperado. Errores: {resultado['errores']}"
    
    def test_importacion_acepta_fecha_valida(self):
        """Test: Importación debe aceptar fechas válidas"""
        from core.utils.excel_importer import importar_lotes_desde_excel
        import openpyxl
        from io import BytesIO
        from datetime import date, timedelta
        
        # Crear Excel con fecha válida
        wb = openpyxl.Workbook()
        ws = wb.active
        
        # Headers
        ws.append(['Clave', 'Nombre Producto', 'Lote', 'Cantidad Inicial', 'Fecha Caducidad', 'Precio'])
        
        # Fila con fecha válida (3 años en el futuro)
        fecha_valida = date.today() + timedelta(days=3*365)
        ws.append(['PROD-IMPORT', 'Producto Importación', 'LOTE-OK-001', 100, fecha_valida, 50.00])
        
        # Guardar en BytesIO
        excel_file = BytesIO()
        wb.save(excel_file)
        excel_file.seek(0)
        excel_file.name = 'test_import_ok.xlsx'
        
        # Importar
        resultado = importar_lotes_desde_excel(excel_file, self.admin, centro_id=self.centro.id)
        
        # Verificar que fue aceptado (el resultado es un dict)
        assert resultado['registros_exitosos'] > 0
        assert resultado['registros_fallidos'] == 0
        
        # Verificar que el lote fue creado
        lote = Lote.objects.filter(numero_lote='LOTE-OK-001').first()
        assert lote is not None
        assert lote.fecha_caducidad == fecha_valida


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
