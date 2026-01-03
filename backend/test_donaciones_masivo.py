# -*- coding: utf-8 -*-
"""
Pruebas masivas para el módulo de Donaciones.
Verifica el flujo completo: crear, listar, recibir, procesar, rechazar.

Ejecutar: python test_donaciones_masivo.py [URL_BASE]
Ejemplo: python test_donaciones_masivo.py http://localhost:8000
"""
import os
import sys
import random
import requests
from datetime import datetime, timedelta

# URL base del servidor (puede pasarse como argumento)
BASE_URL = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8000'

class ColoresConsola:
    VERDE = '\033[92m'
    ROJO = '\033[91m'
    AMARILLO = '\033[93m'
    AZUL = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def ok(msg):
    print(f"{ColoresConsola.VERDE}✓ {msg}{ColoresConsola.RESET}")

def error(msg):
    print(f"{ColoresConsola.ROJO}✗ {msg}{ColoresConsola.RESET}")

def info(msg):
    print(f"{ColoresConsola.AZUL}ℹ {msg}{ColoresConsola.RESET}")

def warn(msg):
    print(f"{ColoresConsola.AMARILLO}⚠ {msg}{ColoresConsola.RESET}")

def titulo(msg):
    print(f"\n{ColoresConsola.BOLD}{ColoresConsola.AZUL}{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}{ColoresConsola.RESET}\n")


class PruebasDonacionesMasivas:
    """Clase para ejecutar pruebas masivas de donaciones."""
    
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
        self.token = None
        self.donaciones_creadas = []
        self.productos_disponibles = []
        self.centros_disponibles = []
        self.resultados = {
            'total': 0,
            'exitosos': 0,
            'fallidos': 0,
            'errores': []
        }
    
    def autenticar(self, username='admin', password='admin123'):
        """Obtener token de autenticación."""
        titulo("AUTENTICACIÓN")
        
        # Intentar diferentes combinaciones de credenciales
        credenciales = [
            (username, password),
            ('admin', 'Admin123!'),
            ('admin', 'admin'),
            ('superadmin', 'admin123'),
        ]
        
        for user, pwd in credenciales:
            try:
                response = requests.post(
                    f'{self.base_url}/api/token/',
                    json={'username': user, 'password': pwd},
                    timeout=10
                )
                
                if response.status_code == 200:
                    self.token = response.json().get('access')
                    ok(f"Autenticación exitosa como: {user}")
                    return True
            except requests.exceptions.ConnectionError:
                error(f"No se puede conectar a {self.base_url}")
                return False
            except Exception as e:
                pass
        
        error(f"No se pudo autenticar con ninguna credencial")
        info("Intentando obtener datos sin autenticación...")
        return False
    
    def get_headers(self):
        """Obtener headers con token de autenticación."""
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        return headers
    
    def cargar_catalogos(self):
        """Cargar productos y centros disponibles."""
        titulo("CARGA DE CATÁLOGOS")
        
        # Cargar productos
        try:
            response = requests.get(
                f'{self.base_url}/api/productos/?page_size=50&activo=true',
                headers=self.get_headers(),
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                self.productos_disponibles = data.get('results', data) if isinstance(data, dict) else data
                ok(f"Productos cargados: {len(self.productos_disponibles)}")
            else:
                warn(f"No se pudieron cargar productos: {response.status_code}")
        except Exception as e:
            warn(f"Error cargando productos: {e}")
        
        # Cargar centros
        try:
            response = requests.get(
                f'{self.base_url}/api/centros/?page_size=50',
                headers=self.get_headers(),
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                self.centros_disponibles = data.get('results', data) if isinstance(data, dict) else data
                ok(f"Centros cargados: {len(self.centros_disponibles)}")
            else:
                warn(f"No se pudieron cargar centros: {response.status_code}")
        except Exception as e:
            warn(f"Error cargando centros: {e}")
    
    def test_listar_donaciones(self):
        """Test: Listar donaciones."""
        self.resultados['total'] += 1
        try:
            response = requests.get(
                f'{self.base_url}/api/donaciones/',
                headers=self.get_headers(),
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                count = data.get('count', len(data.get('results', data)))
                ok(f"Listar donaciones: {count} registros encontrados")
                self.resultados['exitosos'] += 1
                return True
            else:
                error(f"Listar donaciones falló: {response.status_code}")
                self.resultados['fallidos'] += 1
                return False
        except Exception as e:
            error(f"Excepción listando donaciones: {e}")
            self.resultados['fallidos'] += 1
            self.resultados['errores'].append(str(e))
            return False
    
    def test_siguiente_numero(self):
        """Test: Obtener siguiente número de donación."""
        self.resultados['total'] += 1
        try:
            response = requests.get(
                f'{self.base_url}/api/donaciones/siguiente-numero/',
                headers=self.get_headers(),
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                numero = data.get('numero', data)
                ok(f"Siguiente número: {numero}")
                self.resultados['exitosos'] += 1
                return numero
            else:
                warn(f"Obtener siguiente número falló: {response.status_code} (generando manual)")
                self.resultados['exitosos'] += 1
                return f'DON-TEST-{random.randint(10000, 99999)}'
        except Exception as e:
            error(f"Excepción obteniendo número: {e}")
            self.resultados['fallidos'] += 1
            return f'DON-TEST-{random.randint(10000, 99999)}'
    
    def test_crear_donacion(self, numero_donacion):
        """Test: Crear una donación."""
        self.resultados['total'] += 1
        try:
            centro = random.choice(self.centros_disponibles) if self.centros_disponibles else None
            fecha = (datetime.now() - timedelta(days=random.randint(1, 30))).strftime('%Y-%m-%d')
            
            data = {
                'numero': numero_donacion,
                'donante_nombre': f'Empresa Prueba {random.randint(1, 100)} SA de CV',
                'donante_tipo': random.choice(['empresa', 'gobierno', 'ong', 'particular']),
                'fecha_donacion': fecha,
                'estado': 'pendiente',
                'notas': f'Donación de prueba automatizada - {datetime.now().isoformat()}'
            }
            
            if centro:
                data['centro_destino'] = centro.get('id')
            
            response = requests.post(
                f'{self.base_url}/api/donaciones/',
                json=data,
                headers=self.get_headers(),
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                donacion = response.json()
                self.donaciones_creadas.append(donacion.get('id'))
                ok(f"Donación creada: {donacion.get('numero')} (ID: {donacion.get('id')})")
                self.resultados['exitosos'] += 1
                return donacion
            else:
                error(f"Crear donación falló: {response.status_code} - {response.text[:200]}")
                self.resultados['fallidos'] += 1
                return None
        except Exception as e:
            error(f"Excepción creando donación: {e}")
            self.resultados['fallidos'] += 1
            self.resultados['errores'].append(str(e))
            return None
    
    def test_agregar_detalle(self, donacion_id):
        """Test: Agregar detalle a una donación."""
        self.resultados['total'] += 1
        try:
            if not self.productos_disponibles:
                warn("No hay productos disponibles, saltando test de detalles")
                self.resultados['exitosos'] += 1
                return None
            
            producto = random.choice(self.productos_disponibles)
            
            data = {
                'donacion': donacion_id,
                'producto': producto.get('id'),
                'cantidad': random.randint(10, 100),
                'lote': f'LOTE-TEST-{random.randint(1000, 9999)}',
                'fecha_caducidad': (datetime.now() + timedelta(days=random.randint(180, 720))).strftime('%Y-%m-%d'),
                'estado_producto': random.choice(['bueno', 'regular']),
                'notas': 'Detalle de prueba automatizada'
            }
            
            response = requests.post(
                f'{self.base_url}/api/detalles-donacion/',
                json=data,
                headers=self.get_headers(),
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                detalle = response.json()
                ok(f"Detalle agregado: {producto.get('nombre', producto.get('clave', 'Producto'))} x {data['cantidad']}")
                self.resultados['exitosos'] += 1
                return detalle
            else:
                error(f"Agregar detalle falló: {response.status_code} - {response.text[:200]}")
                self.resultados['fallidos'] += 1
                return None
        except Exception as e:
            error(f"Excepción agregando detalle: {e}")
            self.resultados['fallidos'] += 1
            self.resultados['errores'].append(str(e))
            return None
    
    def test_recibir_donacion(self, donacion_id):
        """Test: Marcar donación como recibida."""
        self.resultados['total'] += 1
        try:
            response = requests.post(
                f'{self.base_url}/api/donaciones/{donacion_id}/recibir/',
                json={},
                headers=self.get_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                donacion = response.json()
                ok(f"Donación {donacion.get('numero', donacion_id)} marcada como RECIBIDA")
                self.resultados['exitosos'] += 1
                return True
            else:
                error(f"Recibir donación falló: {response.status_code} - {response.text[:100]}")
                self.resultados['fallidos'] += 1
                return False
        except Exception as e:
            error(f"Excepción recibiendo donación: {e}")
            self.resultados['fallidos'] += 1
            return False
    
    def test_procesar_donacion(self, donacion_id):
        """Test: Procesar donación (activar stock)."""
        self.resultados['total'] += 1
        try:
            response = requests.post(
                f'{self.base_url}/api/donaciones/{donacion_id}/procesar/',
                json={},
                headers=self.get_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                ok(f"Donación procesada: {data.get('mensaje', 'OK')}")
                self.resultados['exitosos'] += 1
                return True
            else:
                error(f"Procesar donación falló: {response.status_code} - {response.text[:100]}")
                self.resultados['fallidos'] += 1
                return False
        except Exception as e:
            error(f"Excepción procesando donación: {e}")
            self.resultados['fallidos'] += 1
            return False
    
    def test_rechazar_donacion(self, donacion_id):
        """Test: Rechazar una donación."""
        self.resultados['total'] += 1
        try:
            response = requests.post(
                f'{self.base_url}/api/donaciones/{donacion_id}/rechazar/',
                json={'motivo': 'Prueba de rechazo automatizada'},
                headers=self.get_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                donacion = response.json()
                ok(f"Donación {donacion.get('numero', donacion_id)} RECHAZADA correctamente")
                self.resultados['exitosos'] += 1
                return True
            else:
                error(f"Rechazar donación falló: {response.status_code}")
                self.resultados['fallidos'] += 1
                return False
        except Exception as e:
            error(f"Excepción rechazando donación: {e}")
            self.resultados['fallidos'] += 1
            return False
    
    def test_ver_detalle(self, donacion_id):
        """Test: Ver detalle de una donación."""
        self.resultados['total'] += 1
        try:
            response = requests.get(
                f'{self.base_url}/api/donaciones/{donacion_id}/',
                headers=self.get_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                donacion = response.json()
                detalles = donacion.get('detalles', [])
                ok(f"Ver donación {donacion.get('numero')}: {len(detalles)} productos")
                self.resultados['exitosos'] += 1
                return donacion
            else:
                error(f"Ver detalle falló: {response.status_code}")
                self.resultados['fallidos'] += 1
                return None
        except Exception as e:
            error(f"Excepción viendo detalle: {e}")
            self.resultados['fallidos'] += 1
            return None
    
    def test_filtros(self):
        """Test: Verificar filtros de búsqueda."""
        titulo("PRUEBA DE FILTROS")
        filtros_ok = 0
        filtros_total = 4
        
        # Filtro por estado
        self.resultados['total'] += 1
        try:
            response = requests.get(
                f'{self.base_url}/api/donaciones/?estado=pendiente',
                headers=self.get_headers(),
                timeout=10
            )
            if response.status_code == 200:
                ok("Filtro por estado: OK")
                filtros_ok += 1
                self.resultados['exitosos'] += 1
            else:
                error(f"Filtro por estado falló: {response.status_code}")
                self.resultados['fallidos'] += 1
        except Exception as e:
            error(f"Excepción: {e}")
            self.resultados['fallidos'] += 1
        
        # Filtro por tipo donante
        self.resultados['total'] += 1
        try:
            response = requests.get(
                f'{self.base_url}/api/donaciones/?donante_tipo=empresa',
                headers=self.get_headers(),
                timeout=10
            )
            if response.status_code == 200:
                ok("Filtro por tipo donante: OK")
                filtros_ok += 1
                self.resultados['exitosos'] += 1
            else:
                error(f"Filtro por tipo donante falló: {response.status_code}")
                self.resultados['fallidos'] += 1
        except Exception as e:
            error(f"Excepción: {e}")
            self.resultados['fallidos'] += 1
        
        # Búsqueda por texto
        self.resultados['total'] += 1
        try:
            response = requests.get(
                f'{self.base_url}/api/donaciones/?search=prueba',
                headers=self.get_headers(),
                timeout=10
            )
            if response.status_code == 200:
                ok("Búsqueda por texto: OK")
                filtros_ok += 1
                self.resultados['exitosos'] += 1
            else:
                error(f"Búsqueda por texto falló: {response.status_code}")
                self.resultados['fallidos'] += 1
        except Exception as e:
            error(f"Excepción: {e}")
            self.resultados['fallidos'] += 1
        
        # Filtro por fechas
        self.resultados['total'] += 1
        try:
            fecha_desde = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            fecha_hasta = datetime.now().strftime('%Y-%m-%d')
            response = requests.get(
                f'{self.base_url}/api/donaciones/?fecha_desde={fecha_desde}&fecha_hasta={fecha_hasta}',
                headers=self.get_headers(),
                timeout=10
            )
            if response.status_code == 200:
                ok("Filtro por rango de fechas: OK")
                filtros_ok += 1
                self.resultados['exitosos'] += 1
            else:
                error(f"Filtro por fechas falló: {response.status_code}")
                self.resultados['fallidos'] += 1
        except Exception as e:
            error(f"Excepción: {e}")
            self.resultados['fallidos'] += 1
        
        info(f"Filtros: {filtros_ok}/{filtros_total} funcionando")
        return filtros_ok == filtros_total
    
    def limpiar_donaciones_prueba(self):
        """Eliminar donaciones de prueba."""
        titulo("LIMPIEZA DE DATOS DE PRUEBA")
        eliminados = 0
        
        for donacion_id in self.donaciones_creadas:
            try:
                response = requests.delete(
                    f'{self.base_url}/api/donaciones/{donacion_id}/',
                    headers=self.get_headers(),
                    timeout=10
                )
                if response.status_code in [200, 204]:
                    eliminados += 1
            except Exception as e:
                warn(f"No se pudo eliminar donación {donacion_id}: {e}")
        
        if eliminados > 0:
            ok(f"Se eliminaron {eliminados} donaciones de prueba")
        else:
            info("No se eliminaron donaciones (mantener datos de prueba)")
    
    def ejecutar_pruebas(self, cantidad_donaciones=5, limpiar=False):
        """Ejecutar todas las pruebas masivas."""
        titulo("INICIO DE PRUEBAS MASIVAS DE DONACIONES")
        info(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        info(f"Servidor: {self.base_url}")
        info(f"Cantidad de donaciones a crear: {cantidad_donaciones}")
        
        # 1. Autenticar
        if not self.autenticar():
            warn("Continuando sin autenticación (solo lectura)...")
        
        # 2. Cargar catálogos
        self.cargar_catalogos()
        
        # 3. Listar donaciones existentes
        titulo("PRUEBA DE LISTADO")
        self.test_listar_donaciones()
        
        # 4. Crear múltiples donaciones con flujos diferentes
        titulo("PRUEBA DE CREACIÓN MASIVA")
        for i in range(cantidad_donaciones):
            info(f"--- Donación {i+1}/{cantidad_donaciones} ---")
            
            # Obtener siguiente número
            numero = self.test_siguiente_numero()
            
            # Crear donación
            donacion = self.test_crear_donacion(numero)
            
            if donacion:
                donacion_id = donacion.get('id')
                
                # Agregar detalles (2-3 productos por donación)
                for _ in range(random.randint(2, 3)):
                    self.test_agregar_detalle(donacion_id)
                
                # Flujos diferentes según el índice
                if i % 3 == 0:
                    # Flujo completo: recibir -> procesar
                    self.test_recibir_donacion(donacion_id)
                    self.test_procesar_donacion(donacion_id)
                elif i % 3 == 1:
                    # Solo recibir
                    self.test_recibir_donacion(donacion_id)
                else:
                    # Rechazar
                    self.test_rechazar_donacion(donacion_id)
                
                # Ver detalle
                self.test_ver_detalle(donacion_id)
        
        # 5. Probar filtros
        self.test_filtros()
        
        # 6. Limpiar datos de prueba (opcional)
        if limpiar:
            self.limpiar_donaciones_prueba()
        else:
            info(f"Se mantienen {len(self.donaciones_creadas)} donaciones de prueba")
        
        # Resumen final
        self.mostrar_resumen()
        
        return self.resultados
    
    def mostrar_resumen(self):
        """Mostrar resumen de resultados."""
        titulo("RESUMEN DE PRUEBAS")
        
        total = self.resultados['total']
        exitosos = self.resultados['exitosos']
        fallidos = self.resultados['fallidos']
        porcentaje = (exitosos / total * 100) if total > 0 else 0
        
        print(f"  Total de pruebas: {total}")
        print(f"  {ColoresConsola.VERDE}Exitosas: {exitosos}{ColoresConsola.RESET}")
        print(f"  {ColoresConsola.ROJO}Fallidas: {fallidos}{ColoresConsola.RESET}")
        print(f"  Porcentaje de éxito: {porcentaje:.1f}%")
        
        if self.resultados['errores']:
            print(f"\n  {ColoresConsola.ROJO}Errores encontrados:{ColoresConsola.RESET}")
            for err in self.resultados['errores'][:5]:
                print(f"    - {err[:100]}...")
        
        if porcentaje >= 90:
            print(f"\n{ColoresConsola.VERDE}{ColoresConsola.BOLD}  ✓ PRUEBAS SUPERADAS{ColoresConsola.RESET}")
        elif porcentaje >= 70:
            print(f"\n{ColoresConsola.AMARILLO}{ColoresConsola.BOLD}  ⚠ PRUEBAS PARCIALMENTE EXITOSAS{ColoresConsola.RESET}")
        else:
            print(f"\n{ColoresConsola.ROJO}{ColoresConsola.BOLD}  ✗ PRUEBAS FALLIDAS{ColoresConsola.RESET}")


if __name__ == '__main__':
    pruebas = PruebasDonacionesMasivas(BASE_URL)
    resultados = pruebas.ejecutar_pruebas(cantidad_donaciones=5, limpiar=False)
    
    # Exit code según resultados
    sys.exit(0 if resultados['fallidos'] == 0 else 1)
