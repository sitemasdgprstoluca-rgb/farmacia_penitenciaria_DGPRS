#!/usr/bin/env python
"""
Script de verificación manual del módulo de Productos
Ejecutar: python verificar_productos.py
"""
import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Producto, User
from core.serializers import ProductoSerializer
from decimal import Decimal
import json

def print_header(texto):
    print(f"\n{'='*60}")
    print(f"  {texto}")
    print(f"{'='*60}\n")

def print_success(texto):
    print(f"✅ {texto}")

def print_error(texto):
    print(f"❌ {texto}")

def print_info(texto):
    print(f"ℹ️  {texto}")

def verificar_modelo():
    """Verifica el modelo Producto"""
    print_header("VERIFICACIÓN DEL MODELO PRODUCTO")
    
    # 1. Verificar normalización de clave
    print_info("Test 1: Normalización de clave a mayúsculas")
    try:
        producto = Producto(
            clave="prod-001",
            descripcion="Producto de prueba para normalización",
            unidad_medida="PIEZA",
            precio_unitario=Decimal("10.50"),
            stock_minimo=5
        )
        producto.clean()
        assert producto.clave == "PROD-001", "Clave no normalizada"
        print_success("Clave normalizada correctamente a mayúsculas")
    except Exception as e:
        print_error(f"Fallo en normalización: {e}")
    
    # 2. Verificar validación de clave única
    print_info("\nTest 2: Validación de clave única")
    Producto.objects.filter(clave="TEST-UNICO").delete()
    try:
        prod1 = Producto.objects.create(
            clave="TEST-UNICO",
            descripcion="Primer producto con clave única",
            unidad_medida="PIEZA",
            precio_unitario=Decimal("5.00"),
            stock_minimo=10
        )
        print_success(f"Producto creado: {prod1.clave}")
        
        # Intentar crear duplicado
        try:
            prod2 = Producto(
                clave="test-unico",  # Minúsculas, pero debería detectar duplicado
                descripcion="Segundo producto duplicado",
                unidad_medida="CAJA",
                precio_unitario=Decimal("8.00"),
                stock_minimo=5
            )
            prod2.save()
            print_error("Permitió crear clave duplicada (ERROR)")
        except Exception:
            print_success("Bloqueó correctamente clave duplicada")
        
        prod1.delete()
    except Exception as e:
        print_error(f"Error en test de unicidad: {e}")
    
    # 3. Verificar validación de precio positivo
    print_info("\nTest 3: Validación de precio > 0")
    try:
        producto_invalido = Producto(
            clave="PRECIO-NEG",
            descripcion="Producto con precio negativo",
            unidad_medida="FRASCO",
            precio_unitario=Decimal("-5.00"),
            stock_minimo=10
        )
        producto_invalido.save()
        print_error("Permitió precio negativo (ERROR)")
    except Exception:
        print_success("Bloqueó correctamente precio negativo")
    
    # 4. Verificar validación de stock_minimo >= 0
    print_info("\nTest 4: Validación de stock_minimo >= 0")
    try:
        producto_invalido = Producto(
            clave="STOCK-NEG",
            descripcion="Producto con stock mínimo negativo",
            unidad_medida="TABLETA",
            precio_unitario=Decimal("2.50"),
            stock_minimo=-5
        )
        producto_invalido.save()
        print_error("Permitió stock_minimo negativo (ERROR)")
    except Exception:
        print_success("Bloqueó correctamente stock_minimo negativo")
    
    # 5. Verificar validación de unidad de medida
    print_info("\nTest 5: Validación de unidad de medida")
    try:
        producto_invalido = Producto(
            clave="UNIDAD-INV",
            descripcion="Producto con unidad inválida",
            unidad_medida="KILOGRAMOS",  # No está en UNIDADES_MEDIDA
            precio_unitario=Decimal("15.00"),
            stock_minimo=10
        )
        producto_invalido.clean()
        print_error("Permitió unidad de medida inválida (ERROR)")
    except Exception:
        print_success("Bloqueó correctamente unidad de medida inválida")

def verificar_serializer():
    """Verifica el serializer ProductoSerializer"""
    print_header("VERIFICACIÓN DEL SERIALIZER")
    
    # 1. Crear producto válido
    print_info("Test 1: Crear producto válido")
    data = {
        "clave": "aspirin-500",
        "descripcion": "Aspirina 500mg tabletas",
        "unidad_medida": "TABLETA",
        "precio_unitario": "12.50",
        "stock_minimo": 100
    }
    serializer = ProductoSerializer(data=data)
    if serializer.is_valid():
        producto = serializer.save()
        print_success(f"Producto creado: {producto.clave} - {producto.descripcion}")
        
        # Verificar campos calculados
        print_info(f"  Stock actual: {producto.get_stock_actual()}")
        print_info(f"  Nivel stock: {producto.get_nivel_stock()}")
        
        producto.delete()
    else:
        print_error(f"Errores de validación: {serializer.errors}")
    
    # 2. Validar descripción mínima
    print_info("\nTest 2: Validar descripción mínima (5 caracteres)")
    data_invalido = {
        "clave": "TEST",
        "descripcion": "Med",  # Menos de 5 caracteres
        "unidad_medida": "PIEZA",
        "precio_unitario": "10.00",
        "stock_minimo": 5
    }
    serializer = ProductoSerializer(data=data_invalido)
    if not serializer.is_valid():
        print_success(f"Bloqueó descripción corta: {serializer.errors.get('descripcion', [''])[0]}")
    else:
        print_error("Permitió descripción menor a 5 caracteres (ERROR)")
    
    # 3. Validar precio cero
    print_info("\nTest 3: Validar precio > 0")
    data_invalido = {
        "clave": "PRECIO-CERO",
        "descripcion": "Producto sin precio",
        "unidad_medida": "CAJA",
        "precio_unitario": "0",
        "stock_minimo": 10
    }
    serializer = ProductoSerializer(data=data_invalido)
    if not serializer.is_valid():
        print_success(f"Bloqueó precio cero: {serializer.errors.get('precio_unitario', [''])[0]}")
    else:
        print_error("Permitió precio = 0 (ERROR)")
    
    # 4. Validar clave normalización
    print_info("\nTest 4: Normalización de clave en serializer")
    data = {
        "clave": "ibuprofeno-400",  # Minúsculas
        "descripcion": "Ibuprofeno 400mg capsulas",
        "unidad_medida": "capsula",  # Minúsculas
        "precio_unitario": "8.75",
        "stock_minimo": 200
    }
    serializer = ProductoSerializer(data=data)
    if serializer.is_valid():
        producto = serializer.save()
        assert producto.clave == "IBUPROFENO-400", "Clave no normalizada"
        assert producto.unidad_medida == "CAPSULA", "Unidad no normalizada"
        print_success(f"Normalizó correctamente: {producto.clave} | {producto.unidad_medida}")
        producto.delete()
    else:
        print_error(f"Errores: {serializer.errors}")

def verificar_integracion():
    """Verifica integración con lotes y stock"""
    print_header("VERIFICACIÓN DE INTEGRACIÓN")
    
    from core.models import Lote
    from datetime import date, timedelta
    
    # Crear producto de prueba
    Producto.objects.filter(clave="INT-TEST").delete()
    producto = Producto.objects.create(
        clave="INT-TEST",
        descripcion="Producto para pruebas de integración",
        unidad_medida="FRASCO",
        precio_unitario=Decimal("25.00"),
        stock_minimo=50
    )
    print_success(f"Producto creado: {producto.clave}")
    
    # Crear lotes
    print_info("\nCreando lotes asociados...")
    lote1 = Lote.objects.create(
        producto=producto,
        numero_lote="LOTE-001",
        fecha_caducidad=date.today() + timedelta(days=365),
        cantidad_inicial=100,
        cantidad_actual=100,
        estado='disponible'
    )
    print_success(f"Lote 1: {lote1.numero_lote} - {lote1.cantidad_actual} unidades")
    
    lote2 = Lote.objects.create(
        producto=producto,
        numero_lote="LOTE-002",
        fecha_caducidad=date.today() + timedelta(days=180),
        cantidad_inicial=75,
        cantidad_actual=75,
        estado='disponible'
    )
    print_success(f"Lote 2: {lote2.numero_lote} - {lote2.cantidad_actual} unidades")
    
    # Verificar stock calculado
    stock_total = producto.get_stock_actual()
    expected = lote1.cantidad_actual + lote2.cantidad_actual
    print_info(f"\nStock calculado: {stock_total} (esperado: {expected})")
    assert stock_total == expected, f"Stock incorrecto: {stock_total} != {expected}"
    print_success("Cálculo de stock correcto")
    
    # Verificar nivel de stock
    nivel = producto.get_nivel_stock()
    print_info(f"Nivel de stock: {nivel} (stock: {stock_total}, mínimo: {producto.stock_minimo})")
    
    # Limpiar
    lote1.delete()
    lote2.delete()
    producto.delete()
    print_success("\nLimpieza completada")

def verificar_permisos():
    """Verifica configuración de permisos"""
    print_header("VERIFICACIÓN DE PERMISOS")
    
    from core.permissions import IsFarmaciaRole, IsCentroRole
    from django.contrib.auth.models import AnonymousUser
    from rest_framework.test import APIRequestFactory
    
    factory = APIRequestFactory()
    
    # Crear usuarios de prueba
    print_info("Creando usuarios de prueba...")
    
    User.objects.filter(username__in=['farmacia_test', 'centro_test', 'vista_test']).delete()
    
    user_farmacia = User.objects.create_user(
        username='farmacia_test',
        password='test123',
        rol='farmacia'
    )
    print_success(f"Usuario farmacia: {user_farmacia.username} (rol: {user_farmacia.rol})")
    
    user_centro = User.objects.create_user(
        username='centro_test',
        password='test123',
        rol='centro'
    )
    print_success(f"Usuario centro: {user_centro.username} (rol: {user_centro.rol})")
    
    user_vista = User.objects.create_user(
        username='vista_test',
        password='test123',
        rol='vista'
    )
    print_success(f"Usuario vista: {user_vista.username} (rol: {user_vista.rol})")
    
    # Test IsFarmaciaRole
    print_info("\nTest IsFarmaciaRole:")
    request = factory.get('/')
    request.user = user_farmacia
    if IsFarmaciaRole().has_permission(request, None):
        print_success("  ✓ Farmacia tiene permiso")
    else:
        print_error("  ✗ Farmacia NO tiene permiso (ERROR)")
    
    request.user = user_centro
    if not IsFarmaciaRole().has_permission(request, None):
        print_success("  ✓ Centro NO tiene permiso (correcto)")
    else:
        print_error("  ✗ Centro tiene permiso (ERROR)")
    
    # Test IsCentroRole
    print_info("\nTest IsCentroRole:")
    request.user = user_centro
    if IsCentroRole().has_permission(request, None):
        print_success("  ✓ Centro tiene permiso")
    else:
        print_error("  ✗ Centro NO tiene permiso (ERROR)")
    
    request.user = user_vista
    if not IsCentroRole().has_permission(request, None):
        print_success("  ✓ Vista NO tiene permiso (correcto)")
    else:
        print_error("  ✗ Vista tiene permiso (ERROR)")
    
    # Limpiar
    user_farmacia.delete()
    user_centro.delete()
    user_vista.delete()
    print_success("\nLimpieza completada")

def main():
    print_header("VERIFICACIÓN COMPLETA DEL MÓDULO DE PRODUCTOS")
    print_info("Ejecutando verificaciones...\n")
    
    try:
        verificar_modelo()
        verificar_serializer()
        verificar_integracion()
        verificar_permisos()
        
        print_header("RESUMEN")
        print_success("Todas las verificaciones completadas")
        print_info("Revise los resultados arriba para confirmar que todo funciona correctamente")
        
    except Exception as e:
        print_error(f"\nError fatal durante verificación: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
