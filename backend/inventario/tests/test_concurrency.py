"""
ISS-028: Tests de concurrencia.

Suite de tests para validar el comportamiento del sistema
bajo condiciones de alta concurrencia.

NOTA: SQLite tiene limitaciones para SELECT FOR UPDATE y locks concurrentes.
Estos tests están diseñados para PostgreSQL en producción.
En SQLite (desarrollo), algunos tests se adaptan o se saltan apropiadamente.
"""
import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch
import unittest

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.db import transaction, IntegrityError, connection

from core.models import (
    Centro, Producto, Lote, Requisicion, DetalleRequisicion, Movimiento
)
from inventario.services import FolioGenerator

User = get_user_model()
logger = logging.getLogger(__name__)


def is_sqlite():
    """Verifica si se está usando SQLite."""
    return connection.vendor == 'sqlite'


def skip_on_sqlite(reason="SQLite no soporta esta funcionalidad concurrente"):
    """Decorador para saltar tests en SQLite."""
    return unittest.skipIf(is_sqlite(), reason)


class FolioConcurrencyTests(TransactionTestCase):
    """ISS-028: Tests de concurrencia para generación de folios."""
    
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin_folio',
            email='admin@folio.test',
            password='Admin@123'
        )
        self.centro = Centro.objects.create(
            clave='CTR-FOL',
            nombre='Centro Folio Test',
            direccion='Dir',
            telefono='555-0001',
            activo=True
        )
    
    @skip_on_sqlite("SQLite bloquea la tabla completa, causando errores de concurrencia")
    def test_folios_unicos_concurrentes(self):
        """ISS-028: Múltiples threads generando folios deben ser únicos (PostgreSQL only)."""
        NUM_THREADS = 10
        FOLIOS_POR_THREAD = 5
        
        folios_generados = []
        errores = []
        lock = threading.Lock()
        
        def generar_folios(thread_id):
            """Función que ejecuta cada thread."""
            thread_folios = []
            for i in range(FOLIOS_POR_THREAD):
                try:
                    # Crear requisición que genera folio automáticamente
                    with transaction.atomic():
                        req = Requisicion.objects.create(
                            centro=self.centro,
                            usuario_solicita=self.admin,
                            estado='borrador'
                        )
                        thread_folios.append(req.folio)
                except Exception as e:
                    with lock:
                        errores.append(f"Thread {thread_id}: {str(e)}")
            
            with lock:
                folios_generados.extend(thread_folios)
        
        # Ejecutar threads en paralelo
        threads = []
        for i in range(NUM_THREADS):
            t = threading.Thread(target=generar_folios, args=(i,))
            threads.append(t)
        
        # Iniciar todos al mismo tiempo
        for t in threads:
            t.start()
        
        # Esperar a que terminen
        for t in threads:
            t.join()
        
        # Verificar resultados
        self.assertEqual(len(errores), 0, f"Errores durante generación: {errores}")
        
        total_esperado = NUM_THREADS * FOLIOS_POR_THREAD
        self.assertEqual(len(folios_generados), total_esperado)
        
        # Todos los folios deben ser únicos
        folios_unicos = set(folios_generados)
        self.assertEqual(
            len(folios_unicos), 
            total_esperado,
            f"Folios duplicados detectados: {len(folios_generados) - len(folios_unicos)}"
        )
    
    def test_folios_unicos_secuencial(self):
        """ISS-028: Folios generados secuencialmente deben ser únicos."""
        NUM_FOLIOS = 10
        folios = []
        
        for _ in range(NUM_FOLIOS):
            req = Requisicion.objects.create(
                centro=self.centro,
                usuario_solicita=self.admin,
                estado='borrador'
            )
            folios.append(req.folio)
        
        # Verificar que todos sean únicos
        self.assertEqual(len(folios), len(set(folios)))
        
        # Verificar formato correcto
        for folio in folios:
            self.assertTrue(folio.startswith('REQ-'))
    
    def test_folio_generator_atomico(self):
        """ISS-028: FolioGenerator debe generar folios únicos secuencialmente."""
        NUM_FOLIOS = 10
        
        folios = []
        generator = FolioGenerator('requisicion')
        
        for _ in range(NUM_FOLIOS):
            folio = generator.generar(
                modelo_class=Requisicion,
                campo_folio='folio',
                centro_codigo=self.centro.clave
            )
            folios.append(folio)
        
        # Verificar unicidad
        self.assertEqual(len(folios), len(set(folios)))
        
        # Verificar secuencia (los números deben ser consecutivos)
        numeros = []
        for folio in folios:
            # Extraer el número secuencial del folio
            partes = folio.split('-')
            numeros.append(int(partes[-1]))
        
        # Deben ser consecutivos
        numeros_ordenados = sorted(numeros)
        for i in range(1, len(numeros_ordenados)):
            self.assertEqual(numeros_ordenados[i], numeros_ordenados[i-1] + 1)


class StockConcurrencyTests(TransactionTestCase):
    """ISS-028: Tests de concurrencia para operaciones de stock."""
    
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin_stock_conc',
            email='admin@stock.test',
            password='Admin@123'
        )
        self.centro = Centro.objects.create(
            clave='CTR-STC',
            nombre='Centro Stock Test',
            direccion='Dir',
            telefono='555-0002',
            activo=True
        )
        self.producto = Producto.objects.create(
            clave='PROD-STC-001',
            descripcion='Producto Stock Test',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('10.00'),
            stock_minimo=10,
            activo=True
        )
        self.lote = Lote.objects.create(
            producto=self.producto,
            centro=None,
            numero_lote='LOTE-STC-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
    
    def test_descuento_stock_concurrente(self):
        """ISS-028: Múltiples threads descontando stock no deben causar sobregiro."""
        NUM_THREADS = 10
        CANTIDAD_POR_THREAD = 10  # Total: 100, exactamente el stock
        
        errores = []
        exitos = []
        lock = threading.Lock()
        
        def descontar_stock(thread_id):
            """Intenta descontar stock."""
            try:
                with transaction.atomic():
                    # Bloquear el lote para actualización
                    lote = Lote.objects.select_for_update().get(pk=self.lote.pk)
                    
                    if lote.cantidad_actual >= CANTIDAD_POR_THREAD:
                        lote.cantidad_actual -= CANTIDAD_POR_THREAD
                        lote.save()
                        
                        # Registrar movimiento
                        Movimiento.objects.create(
                            tipo='salida',
                            lote=lote,
                            cantidad=-CANTIDAD_POR_THREAD,
                            usuario=self.admin,
                            observaciones=f'Thread {thread_id}'
                        )
                        
                        with lock:
                            exitos.append(thread_id)
                    else:
                        with lock:
                            errores.append(f"Thread {thread_id}: Stock insuficiente")
            except Exception as e:
                with lock:
                    errores.append(f"Thread {thread_id}: {str(e)}")
        
        # Ejecutar threads
        threads = []
        for i in range(NUM_THREADS):
            t = threading.Thread(target=descontar_stock, args=(i,))
            threads.append(t)
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # Verificar resultados
        self.lote.refresh_from_db()
        
        # Stock final debe ser >= 0
        self.assertGreaterEqual(
            self.lote.cantidad_actual, 
            0,
            "Stock negativo detectado (sobregiro)"
        )
        
        # La suma de éxitos * cantidad debe coincidir con lo descontado
        stock_descontado = 100 - self.lote.cantidad_actual
        self.assertEqual(
            stock_descontado,
            len(exitos) * CANTIDAD_POR_THREAD,
            "Inconsistencia entre éxitos y stock descontado"
        )
    
    def test_entrada_salida_simultanea(self):
        """ISS-028: Entradas y salidas simultáneas deben mantener consistencia."""
        NUM_OPERACIONES = 20
        
        operaciones_completadas = {'entradas': 0, 'salidas': 0}
        lock = threading.Lock()
        
        def hacer_entrada():
            try:
                with transaction.atomic():
                    lote = Lote.objects.select_for_update().get(pk=self.lote.pk)
                    lote.cantidad_actual += 5
                    lote.save()
                    
                    Movimiento.objects.create(
                        tipo='entrada',
                        lote=lote,
                        cantidad=5,
                        usuario=self.admin
                    )
                    
                    with lock:
                        operaciones_completadas['entradas'] += 1
            except Exception as e:
                logger.error(f"Error en entrada: {e}")
        
        def hacer_salida():
            try:
                with transaction.atomic():
                    lote = Lote.objects.select_for_update().get(pk=self.lote.pk)
                    
                    if lote.cantidad_actual >= 5:
                        lote.cantidad_actual -= 5
                        lote.save()
                        
                        Movimiento.objects.create(
                            tipo='salida',
                            lote=lote,
                            cantidad=-5,
                            usuario=self.admin
                        )
                        
                        with lock:
                            operaciones_completadas['salidas'] += 1
            except Exception as e:
                logger.error(f"Error en salida: {e}")
        
        # Mezclar operaciones
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i in range(NUM_OPERACIONES):
                if i % 2 == 0:
                    futures.append(executor.submit(hacer_entrada))
                else:
                    futures.append(executor.submit(hacer_salida))
            
            for future in as_completed(futures):
                future.result()
        
        # Verificar consistencia
        self.lote.refresh_from_db()
        
        stock_esperado = 100 + (operaciones_completadas['entradas'] * 5) - (operaciones_completadas['salidas'] * 5)
        
        self.assertEqual(
            self.lote.cantidad_actual,
            stock_esperado,
            f"Stock inconsistente. Esperado: {stock_esperado}, Actual: {self.lote.cantidad_actual}"
        )


class RequisicionConcurrencyTests(TransactionTestCase):
    """ISS-028: Tests de concurrencia para requisiciones."""
    
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin_req_conc',
            email='admin@req.test',
            password='Admin@123'
        )
        self.centro = Centro.objects.create(
            clave='CTR-REQ',
            nombre='Centro Requisicion Test',
            direccion='Dir',
            telefono='555-0003',
            activo=True
        )
        self.producto = Producto.objects.create(
            clave='PROD-REQ-001',
            descripcion='Producto Requisicion Test',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('10.00'),
            stock_minimo=5,
            activo=True
        )
        self.lote = Lote.objects.create(
            producto=self.producto,
            centro=None,
            numero_lote='LOTE-REQ-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=50,
            cantidad_actual=50,
            estado='disponible'
        )
    
    def test_requisicion_estado_transicion(self):
        """ISS-028: Validar transiciones de estado de requisición."""
        # Crear requisición en borrador
        req = Requisicion.objects.create(
            centro=self.centro,
            usuario_solicita=self.admin,
            estado='borrador'
        )
        
        # Transición válida: borrador -> enviada
        req.estado = 'enviada'
        req.save()
        req.refresh_from_db()
        self.assertEqual(req.estado, 'enviada')
        
        # Transición válida: enviada -> autorizada
        req.estado = 'autorizada'
        req.save()
        req.refresh_from_db()
        self.assertEqual(req.estado, 'autorizada')
    
    @skip_on_sqlite("SQLite no soporta locks concurrentes para este test")
    def test_surtido_doble_bloqueado(self):
        """ISS-028: Intentar surtir la misma requisición dos veces debe fallar (PostgreSQL only)."""
        from inventario.services import RequisicionService
        
        # Crear requisición autorizada
        req = Requisicion.objects.create(
            centro=self.centro,
            usuario_solicita=self.admin,
            estado='autorizada'
        )
        DetalleRequisicion.objects.create(
            requisicion=req,
            producto=self.producto,
            cantidad_solicitada=10,
            cantidad_autorizada=10
        )
        
        resultados = {'exitos': 0, 'fallos': 0}
        lock = threading.Lock()
        
        def intentar_surtir():
            try:
                service = RequisicionService(req, self.admin)
                service.surtir()
                with lock:
                    resultados['exitos'] += 1
            except Exception as e:
                with lock:
                    resultados['fallos'] += 1
                logger.info(f"Surtido bloqueado: {e}")
        
        # Dos threads intentando surtir al mismo tiempo
        threads = [threading.Thread(target=intentar_surtir) for _ in range(2)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Solo uno debe tener éxito
        self.assertEqual(resultados['exitos'], 1)
        self.assertEqual(resultados['fallos'], 1)
        
        # Verificar stock final
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.cantidad_actual, 40)  # 50 - 10


class DatabaseLockTests(TransactionTestCase):
    """ISS-028: Tests de bloqueo de base de datos."""
    
    def setUp(self):
        self.centro = Centro.objects.create(
            clave='CTR-LOCK',
            nombre='Centro Lock Test',
            direccion='Dir',
            telefono='555-0004',
            activo=True
        )
    
    def test_transaction_atomicity(self):
        """ISS-028: Las transacciones atómicas deben ser consistentes."""
        # Test que funciona en SQLite y PostgreSQL
        original_nombre = self.centro.nombre
        
        try:
            with transaction.atomic():
                self.centro.nombre = 'Nombre Temporal'
                self.centro.save()
                # Forzar un error
                raise ValueError("Error simulado")
        except ValueError:
            pass
        
        # El nombre debe ser el original (rollback)
        self.centro.refresh_from_db()
        self.assertEqual(self.centro.nombre, original_nombre)
    
    def test_transaction_commit(self):
        """ISS-028: Las transacciones exitosas deben persistir."""
        nuevo_nombre = 'Nombre Actualizado'
        
        with transaction.atomic():
            self.centro.nombre = nuevo_nombre
            self.centro.save()
        
        # El cambio debe persistir
        self.centro.refresh_from_db()
        self.assertEqual(self.centro.nombre, nuevo_nombre)
    
    @skip_on_sqlite("SQLite bloquea tablas completas, no filas individuales")
    def test_select_for_update_blocks(self):
        """ISS-028: SELECT FOR UPDATE debe bloquear otras transacciones (PostgreSQL only)."""
        barrier = threading.Barrier(2)
        results = {'thread1': None, 'thread2': None}
        
        def thread1_func():
            try:
                with transaction.atomic():
                    # Bloquear el centro
                    centro = Centro.objects.select_for_update().get(pk=self.centro.pk)
                    barrier.wait()  # Sincronizar con thread2
                    time.sleep(0.5)  # Mantener bloqueo
                    centro.nombre = 'Modificado por Thread 1'
                    centro.save()
                    results['thread1'] = 'success'
            except Exception as e:
                results['thread1'] = f'error: {e}'
        
        def thread2_func():
            try:
                barrier.wait()  # Esperar a que thread1 tenga el bloqueo
                time.sleep(0.1)  # Pequeña espera
                
                with transaction.atomic():
                    # Esto debería esperar hasta que thread1 libere
                    centro = Centro.objects.select_for_update(nowait=False).get(pk=self.centro.pk)
                    centro.nombre = 'Modificado por Thread 2'
                    centro.save()
                    results['thread2'] = 'success'
            except Exception as e:
                results['thread2'] = f'error: {e}'
        
        t1 = threading.Thread(target=thread1_func)
        t2 = threading.Thread(target=thread2_func)
        
        t1.start()
        t2.start()
        
        t1.join(timeout=5)
        t2.join(timeout=5)
        
        # Ambos deberían completarse sin error
        self.assertEqual(results['thread1'], 'success')
        self.assertEqual(results['thread2'], 'success')
        
        # El nombre final depende de qué thread terminó último
        self.centro.refresh_from_db()
        self.assertIn(self.centro.nombre, ['Modificado por Thread 1', 'Modificado por Thread 2'])
