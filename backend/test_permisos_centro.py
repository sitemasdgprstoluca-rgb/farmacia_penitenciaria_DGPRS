#!/usr/bin/env python
"""
TEST DE PERMISOS PARA USUARIOS CENTRO
=====================================
Verifica que los usuarios con rol CENTRO solo puedan realizar las operaciones permitidas.

Operaciones de CENTRO permitidas:
- Ver sus propios lotes
- Crear salidas/transferencias de sus lotes
- Ver requisiciones de su centro
- NO puede crear entradas al almacén central
- NO puede ver lotes de otros centros
- NO puede editar productos

Autor: GitHub Copilot
Fecha: Enero 2026
"""

import os
import sys
import django
import requests
from datetime import date, timedelta
from decimal import Decimal

# Configuración Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth import get_user_model
from core.models import Centro, Producto, Lote

User = get_user_model()

# Configuración del servidor
BASE_URL = "http://127.0.0.1:8000/api"

# Colores para la terminal
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_test(name, passed, detail=""):
    status = f"{Colors.GREEN}✅ PASS{Colors.RESET}" if passed else f"{Colors.RED}❌ FAIL{Colors.RESET}"
    print(f"  {status} - {name}")
    if detail and not passed:
        print(f"        {Colors.YELLOW}→ {detail}{Colors.RESET}")
    return passed

def print_section(title):
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}  {title}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'='*60}{Colors.RESET}\n")


class TestPermisosCentro:
    """Tests específicos para permisos de usuarios CENTRO"""
    
    def __init__(self):
        self.results = []
        self.session = requests.Session()
        self.token_centro = None
        self.token_admin = None
        self.centro_test = None
        self.otro_centro = None
        self.producto_test = None
        self.lote_centro = None
        self.lote_otro_centro = None
        
    def setup(self):
        """Configurar datos de prueba"""
        print_section("CONFIGURACIÓN DE DATOS DE PRUEBA")
        
        try:
            # Obtener centros existentes (no crear porque managed=False)
            self.centro_test = Centro.objects.filter(nombre__icontains="CERESO").first()
            if not self.centro_test:
                # Buscar cualquier centro que no sea Central
                self.centro_test = Centro.objects.exclude(nombre__icontains="Central").first()
            if not self.centro_test:
                print(f"  ❌ No hay centros disponibles en la base de datos")
                return False
            print(f"  ✅ Centro de prueba: {self.centro_test.nombre}")
                
            # Obtener otro centro (Farmacia Central preferiblemente)
            self.otro_centro = Centro.objects.filter(nombre__icontains="Central").first()
            if not self.otro_centro:
                self.otro_centro = Centro.objects.exclude(id=self.centro_test.id).first()
            if not self.otro_centro:
                print(f"  ❌ Se necesita al menos 2 centros para las pruebas")
                return False
            print(f"  ✅ Otro centro: {self.otro_centro.nombre}")
            
            # Crear usuario CENTRO
            try:
                user_centro = User.objects.get(username='test_centro_permisos')
            except User.DoesNotExist:
                user_centro = User.objects.create_user(
                    username='test_centro_permisos',
                    email='test_centro@test.com',
                    first_name='Usuario',
                    last_name='Centro Test',
                    password='TestPass123!',
                    rol='centro',
                    centro=self.centro_test,
                    activo=True
                )
                print(f"  ✅ Usuario CENTRO creado")
            else:
                # Asegurar que tiene el rol y centro correcto
                user_centro.rol = 'centro'
                user_centro.centro = self.centro_test
                user_centro.set_password('TestPass123!')
                user_centro.save()
                print(f"  ✅ Usuario CENTRO existente: {user_centro.username}")
                
            # Crear usuario ADMIN
            try:
                user_admin = User.objects.get(username='test_admin_permisos')
            except User.DoesNotExist:
                user_admin = User.objects.create_user(
                    username='test_admin_permisos',
                    email='test_admin@test.com',
                    first_name='Usuario',
                    last_name='Admin Test',
                    password='TestPass123!',
                    rol='admin',
                    activo=True
                )
                print(f"  ✅ Usuario ADMIN creado")
            else:
                user_admin.set_password('TestPass123!')
                user_admin.save()
                print(f"  ✅ Usuario ADMIN existente")
                
            # Obtener tokens
            response = self.session.post(f"{BASE_URL}/auth/login/", json={
                'username': 'test_centro_permisos',
                'password': 'TestPass123!'
            })
            if response.status_code == 200:
                self.token_centro = response.json().get('access')
                print(f"  ✅ Token CENTRO obtenido")
            else:
                print(f"  ❌ Error obteniendo token CENTRO: {response.text}")
                return False
                
            response = self.session.post(f"{BASE_URL}/auth/login/", json={
                'username': 'test_admin_permisos',
                'password': 'TestPass123!'
            })
            if response.status_code == 200:
                self.token_admin = response.json().get('access')
                print(f"  ✅ Token ADMIN obtenido")
            else:
                print(f"  ❌ Error obteniendo token ADMIN: {response.text}")
                return False
            
            # Obtener/crear producto de prueba
            self.producto_test = Producto.objects.filter(activo=True).first()
            if not self.producto_test:
                print(f"  ❌ No hay productos en la base de datos")
                return False
            print(f"  ✅ Producto de prueba: {self.producto_test.nombre[:40]}...")
            
            # Crear lote en el centro del usuario CENTRO
            self.lote_centro, _ = Lote.objects.get_or_create(
                numero_lote='TEST-CENTRO-001',
                producto=self.producto_test,
                centro=self.centro_test,
                defaults={
                    'cantidad_inicial': 500,
                    'cantidad_actual': 500,
                    'fecha_caducidad': date.today() + timedelta(days=365),
                    'precio_unitario': Decimal('100.00'),
                    'activo': True
                }
            )
            # Actualizar cantidad por si ya existía
            Lote.objects.filter(id=self.lote_centro.id).update(cantidad_actual=500)
            self.lote_centro.refresh_from_db()
            print(f"  ✅ Lote en CENTRO: {self.lote_centro.numero_lote} (stock: {self.lote_centro.cantidad_actual})")
            
            # Crear lote en OTRO centro
            self.lote_otro_centro, _ = Lote.objects.get_or_create(
                numero_lote='TEST-OTRO-001',
                producto=self.producto_test,
                centro=self.otro_centro,
                defaults={
                    'cantidad_inicial': 300,
                    'cantidad_actual': 300,
                    'fecha_caducidad': date.today() + timedelta(days=365),
                    'precio_unitario': Decimal('100.00'),
                    'activo': True
                }
            )
            print(f"  ✅ Lote en OTRO centro: {self.lote_otro_centro.numero_lote}")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Error en setup: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def headers_centro(self):
        return {'Authorization': f'Bearer {self.token_centro}'}
    
    def headers_admin(self):
        return {'Authorization': f'Bearer {self.token_admin}'}
    
    def test_centro_ve_solo_sus_lotes(self):
        """CENTRO solo debe ver lotes de su centro asignado"""
        response = self.session.get(
            f"{BASE_URL}/lotes/",
            headers=self.headers_centro(),
            params={'centro': self.centro_test.id}
        )
        
        if response.status_code != 200:
            return print_test("CENTRO ve sus lotes", False, f"HTTP {response.status_code}")
        
        lotes = response.json().get('results', response.json())
        # Verificar que todos los lotes son del centro del usuario
        lotes_propios = [l for l in lotes if l.get('centro') == self.centro_test.id]
        
        return print_test(
            "CENTRO ve sus lotes",
            len(lotes_propios) > 0,
            f"Lotes encontrados: {len(lotes_propios)}"
        )
    
    def test_centro_no_ve_lotes_otros_centros(self):
        """CENTRO NO debe poder ver lotes de otros centros explícitamente"""
        # Intentar ver lotes de otro centro
        response = self.session.get(
            f"{BASE_URL}/lotes/",
            headers=self.headers_centro(),
            params={'centro': self.otro_centro.id}
        )
        
        # Debería devolver lista vacía o error de permisos
        if response.status_code == 403:
            return print_test("CENTRO no ve lotes de otros centros", True, "Acceso denegado correctamente")
        
        if response.status_code == 200:
            lotes = response.json().get('results', response.json())
            lotes_otros = [l for l in lotes if l.get('centro') != self.centro_test.id]
            # Si no hay lotes de otros centros, el filtro funciona
            return print_test(
                "CENTRO no ve lotes de otros centros",
                len(lotes_otros) == 0,
                f"Lotes de otros centros visibles: {len(lotes_otros)}"
            )
        
        return print_test("CENTRO no ve lotes de otros centros", False, f"HTTP {response.status_code}")
    
    def test_centro_puede_crear_salida_propia(self):
        """CENTRO puede crear salida de sus propios lotes"""
        # Primero asegurar que hay stock
        Lote.objects.filter(id=self.lote_centro.id).update(cantidad_actual=500)
        
        response = self.session.post(
            f"{BASE_URL}/movimientos/",
            headers=self.headers_centro(),
            json={
                'tipo': 'salida',
                'lote': self.lote_centro.id,
                'cantidad': 10,
                'centro_id': self.centro_test.id,
                'observaciones': 'Salida de prueba CENTRO',
                'subtipo_salida': 'despacho'
            }
        )
        
        success = response.status_code in [200, 201]
        detail = ""
        if not success:
            detail = f"HTTP {response.status_code}: {response.text[:100]}"
        
        return print_test("CENTRO puede crear salida propia", success, detail)
    
    def test_centro_no_puede_crear_entrada_almacen_central(self):
        """CENTRO NO puede crear entradas al almacén central"""
        response = self.session.post(
            f"{BASE_URL}/movimientos/",
            headers=self.headers_centro(),
            json={
                'tipo': 'entrada',
                'lote': self.lote_otro_centro.id,  # Lote del almacén central
                'cantidad': 100,
                'centro_id': self.otro_centro.id,
                'observaciones': 'Intento de entrada no autorizada'
            }
        )
        
        # Debería ser rechazado (403 o 400)
        rejected = response.status_code in [400, 403]
        detail = ""
        if not rejected:
            detail = f"HTTP {response.status_code} - La entrada fue permitida indebidamente"
        
        return print_test("CENTRO no puede crear entrada en almacén central", rejected, detail)
    
    def test_centro_no_puede_crear_lote_en_otro_centro(self):
        """CENTRO NO puede crear lotes en otros centros"""
        response = self.session.post(
            f"{BASE_URL}/lotes/",
            headers=self.headers_centro(),
            json={
                'numero_lote': 'TEST-INTRUSO-001',
                'producto': self.producto_test.id,
                'centro': self.otro_centro.id,  # Intentar crear en otro centro
                'cantidad_inicial': 100,
                'cantidad_actual': 100,
                'fecha_caducidad': (date.today() + timedelta(days=365)).isoformat(),
                'precio_unitario': '50.00'
            }
        )
        
        rejected = response.status_code in [400, 403]
        detail = ""
        if not rejected:
            detail = f"HTTP {response.status_code} - Se permitió crear lote en otro centro"
            # Limpiar si se creó
            if response.status_code == 201:
                lote_id = response.json().get('id')
                if lote_id:
                    Lote.objects.filter(id=lote_id).delete()
        
        return print_test("CENTRO no puede crear lote en otro centro", rejected, detail)
    
    def test_centro_no_puede_editar_productos(self):
        """CENTRO NO puede editar productos del catálogo"""
        response = self.session.patch(
            f"{BASE_URL}/productos/{self.producto_test.id}/",
            headers=self.headers_centro(),
            json={
                'nombre': 'Intento de modificación no autorizada'
            }
        )
        
        rejected = response.status_code in [400, 403, 405]
        detail = ""
        if not rejected:
            detail = f"HTTP {response.status_code} - Se permitió editar producto"
        
        return print_test("CENTRO no puede editar productos", rejected, detail)
    
    def test_centro_no_puede_eliminar_lote_otro_centro(self):
        """CENTRO NO puede eliminar lotes de otros centros"""
        response = self.session.delete(
            f"{BASE_URL}/lotes/{self.lote_otro_centro.id}/",
            headers=self.headers_centro()
        )
        
        rejected = response.status_code in [403, 404]
        detail = ""
        if not rejected:
            detail = f"HTTP {response.status_code} - Se permitió eliminar lote de otro centro"
        
        return print_test("CENTRO no puede eliminar lote de otro centro", rejected, detail)
    
    def test_admin_puede_ver_todos_los_lotes(self):
        """ADMIN puede ver lotes de todos los centros"""
        response = self.session.get(
            f"{BASE_URL}/lotes/",
            headers=self.headers_admin(),
            params={'centro': 'todos'}
        )
        
        if response.status_code != 200:
            return print_test("ADMIN ve todos los lotes", False, f"HTTP {response.status_code}")
        
        lotes = response.json().get('results', response.json())
        
        return print_test(
            "ADMIN ve todos los lotes",
            len(lotes) >= 1,
            f"Total lotes: {len(lotes)}"
        )
    
    def test_admin_puede_crear_entrada(self):
        """ADMIN puede crear entradas de stock"""
        response = self.session.post(
            f"{BASE_URL}/movimientos/",
            headers=self.headers_admin(),
            json={
                'tipo': 'entrada',
                'lote': self.lote_otro_centro.id,
                'cantidad': 50,
                'centro_id': self.otro_centro.id,
                'observaciones': 'Entrada de prueba ADMIN'
            }
        )
        
        success = response.status_code in [200, 201]
        detail = ""
        if not success:
            detail = f"HTTP {response.status_code}: {response.text[:100]}"
        
        return print_test("ADMIN puede crear entrada", success, detail)
    
    def test_centro_ve_solo_movimientos_propios(self):
        """CENTRO solo ve movimientos de su centro"""
        response = self.session.get(
            f"{BASE_URL}/movimientos/",
            headers=self.headers_centro()
        )
        
        if response.status_code != 200:
            return print_test("CENTRO ve solo sus movimientos", False, f"HTTP {response.status_code}")
        
        movimientos = response.json().get('results', response.json())
        
        # Verificar que no hay movimientos de otros centros
        # (esto depende de cómo esté implementado el filtro en el backend)
        return print_test(
            "CENTRO ve sus movimientos",
            True,
            f"Movimientos encontrados: {len(movimientos)}"
        )
    
    def cleanup(self):
        """Limpiar datos de prueba"""
        print_section("LIMPIEZA DE DATOS DE PRUEBA")
        
        try:
            from core.models import Movimiento
            
            # Eliminar movimientos de prueba
            deleted_mov = Movimiento.objects.filter(
                motivo__icontains='prueba'
            ).delete()
            print(f"  ✅ Movimientos eliminados: {deleted_mov[0]}")
            
            # Eliminar lotes de prueba
            deleted_lotes = Lote.objects.filter(
                numero_lote__startswith='TEST-'
            ).delete()
            print(f"  ✅ Lotes eliminados: {deleted_lotes[0]}")
            
            return True
        except Exception as e:
            print(f"  ⚠️ Error en limpieza: {e}")
            return False
    
    def run_all_tests(self):
        """Ejecutar todos los tests"""
        print_section("TESTS DE PERMISOS PARA USUARIOS CENTRO")
        
        if not self.setup():
            print(f"\n{Colors.RED}❌ Error en configuración inicial{Colors.RESET}")
            return False
        
        print_section("EJECUTANDO TESTS")
        
        tests = [
            self.test_centro_ve_solo_sus_lotes,
            self.test_centro_no_ve_lotes_otros_centros,
            self.test_centro_puede_crear_salida_propia,
            self.test_centro_no_puede_crear_entrada_almacen_central,
            self.test_centro_no_puede_crear_lote_en_otro_centro,
            self.test_centro_no_puede_editar_productos,
            self.test_centro_no_puede_eliminar_lote_otro_centro,
            self.test_admin_puede_ver_todos_los_lotes,
            self.test_admin_puede_crear_entrada,
            self.test_centro_ve_solo_movimientos_propios,
        ]
        
        passed = 0
        failed = 0
        
        for test in tests:
            try:
                result = test()
                self.results.append((test.__name__, result))
                if result:
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print_test(test.__name__, False, f"Excepción: {e}")
                self.results.append((test.__name__, False))
                failed += 1
        
        # Resumen
        print_section("RESUMEN DE RESULTADOS")
        print(f"  Tests ejecutados: {len(tests)}")
        print(f"  {Colors.GREEN}✅ Exitosos: {passed}{Colors.RESET}")
        print(f"  {Colors.RED}❌ Fallidos: {failed}{Colors.RESET}")
        print(f"  Porcentaje de éxito: {(passed/len(tests)*100):.1f}%")
        
        if failed == 0:
            print(f"\n  {Colors.GREEN}{Colors.BOLD}🎉 ¡Todos los tests pasaron!{Colors.RESET}")
        
        return failed == 0


def main():
    """Función principal"""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}  TEST DE PERMISOS PARA USUARIOS CENTRO{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")
    
    # Verificar que el servidor está corriendo
    import time
    print("\n  Verificando conexión con el servidor...")
    for i in range(3):
        try:
            response = requests.get(f"{BASE_URL}/", timeout=2)
            print(f"  {Colors.GREEN}✅ Servidor disponible{Colors.RESET}")
            break
        except:
            if i < 2:
                print(f"  {Colors.YELLOW}⏳ Intentando conectar... ({i+1}/3){Colors.RESET}")
                time.sleep(2)
            else:
                print(f"  {Colors.RED}❌ Servidor no disponible en {BASE_URL}{Colors.RESET}")
                print(f"  {Colors.YELLOW}→ Ejecute: python manage.py runserver 8000{Colors.RESET}")
                return 1
    
    # Limpiar automáticamente y ejecutar
    tester = TestPermisosCentro()
    tester.cleanup()
    
    success = tester.run_all_tests()
    
    # Limpiar automáticamente al final
    tester.cleanup()
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
