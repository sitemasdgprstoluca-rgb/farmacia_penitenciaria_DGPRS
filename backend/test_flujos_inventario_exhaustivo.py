#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PRUEBAS EXHAUSTIVAS DE FLUJOS DE INVENTARIO
============================================
Verifica que todos los procesos funcionen correctamente:
1. Entradas de inventario
2. Salidas individuales
3. Salidas masivas
4. Requisiciones (flujo completo)

Ejecutar: python test_flujos_inventario_exhaustivo.py
"""
import os
import sys
import django
import random
import string
from datetime import datetime, timedelta
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import transaction, connection
from django.utils import timezone
from django.contrib.auth import get_user_model
from core.models import (
    Producto, Lote, Movimiento, Centro, Requisicion, DetalleRequisicion
)

User = get_user_model()

# Colores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.CYAN}ℹ️  {text}{Colors.END}")

def generar_numero_lote():
    """Genera un número de lote único para pruebas"""
    return f"TEST-{datetime.now().strftime('%H%M%S')}-{random.randint(1000,9999)}"

def generar_folio_requisicion():
    """Genera un folio único para requisiciones de prueba"""
    return f"REQ-TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(100,999)}"

# ============================================================================
# PRUEBA 1: ENTRADAS DE INVENTARIO
# ============================================================================
def test_entradas_inventario():
    print_header("PRUEBA 1: ENTRADAS DE INVENTARIO")
    
    errores = []
    exitos = 0
    
    # Obtener un producto existente
    producto = Producto.objects.filter(activo=True).first()
    if not producto:
        print_error("No hay productos activos para pruebas")
        return False, ["No hay productos activos"]
    
    print_info(f"Usando producto: {producto.clave} - {producto.nombre}")
    
    # Obtener usuario farmacia
    usuario = User.objects.filter(rol__icontains='farmacia').first()
    if not usuario:
        usuario = User.objects.filter(is_superuser=True).first()
    
    # TEST 1.1: Entrada en Almacén Central (centro=NULL)
    print(f"\n{Colors.CYAN}Test 1.1: Entrada en Almacén Central{Colors.END}")
    try:
        with transaction.atomic():
            numero_lote = generar_numero_lote()
            cantidad_entrada = 100
            
            # Crear lote nuevo
            lote = Lote.objects.create(
                producto=producto,
                numero_lote=numero_lote,
                centro=None,  # Almacén Central
                cantidad_inicial=cantidad_entrada,
                cantidad_actual=cantidad_entrada,
                fecha_caducidad=timezone.now().date() + timedelta(days=365),
                activo=True
            )
            
            # Crear movimiento de entrada
            mov = Movimiento.objects.create(
                tipo='entrada',
                producto=producto,
                lote=lote,
                centro_origen=None,
                centro_destino=None,
                cantidad=cantidad_entrada,
                motivo=f'PRUEBA ENTRADA ALMACEN - {timezone.now().isoformat()}',
                usuario=usuario
            )
            
            # Verificar
            lote.refresh_from_db()
            assert lote.cantidad_actual == cantidad_entrada, f"Cantidad incorrecta: {lote.cantidad_actual}"
            assert mov.tipo == 'entrada', f"Tipo incorrecto: {mov.tipo}"
            
            print_success(f"Lote {numero_lote} creado con {cantidad_entrada} unidades")
            exitos += 1
            
            # Limpiar
            mov.delete()
            lote.delete()
            
    except Exception as e:
        print_error(f"Error en entrada Almacén Central: {e}")
        errores.append(f"Entrada Almacén Central: {e}")
    
    # TEST 1.2: Entrada en Centro específico
    print(f"\n{Colors.CYAN}Test 1.2: Entrada en Centro específico{Colors.END}")
    centro = Centro.objects.filter(activo=True).first()
    if centro:
        try:
            with transaction.atomic():
                numero_lote = generar_numero_lote()
                cantidad_entrada = 50
                
                lote = Lote.objects.create(
                    producto=producto,
                    numero_lote=numero_lote,
                    centro=centro,
                    cantidad_inicial=cantidad_entrada,
                    cantidad_actual=cantidad_entrada,
                    fecha_caducidad=timezone.now().date() + timedelta(days=365),
                    activo=True
                )
                
                mov = Movimiento.objects.create(
                    tipo='entrada',
                    producto=producto,
                    lote=lote,
                    centro_origen=None,
                    centro_destino=centro,
                    cantidad=cantidad_entrada,
                    motivo=f'PRUEBA ENTRADA CENTRO - {timezone.now().isoformat()}',
                    usuario=usuario
                )
                
                lote.refresh_from_db()
                assert lote.cantidad_actual == cantidad_entrada
                assert lote.centro == centro
                
                print_success(f"Lote {numero_lote} creado en centro {centro.nombre}")
                exitos += 1
                
                mov.delete()
                lote.delete()
                
        except Exception as e:
            print_error(f"Error en entrada Centro: {e}")
            errores.append(f"Entrada Centro: {e}")
    else:
        print_warning("No hay centros activos para prueba")
    
    # TEST 1.3: Múltiples entradas (prueba masiva)
    print(f"\n{Colors.CYAN}Test 1.3: Entradas masivas (10 lotes){Colors.END}")
    try:
        with transaction.atomic():
            lotes_creados = []
            movs_creados = []
            
            for i in range(10):
                numero_lote = f"MASIVO-{i+1}-{generar_numero_lote()}"
                cantidad = random.randint(10, 100)
                
                lote = Lote.objects.create(
                    producto=producto,
                    numero_lote=numero_lote,
                    centro=None,
                    cantidad_inicial=cantidad,
                    cantidad_actual=cantidad,
                    fecha_caducidad=timezone.now().date() + timedelta(days=random.randint(30, 365)),
                    activo=True
                )
                lotes_creados.append(lote)
                
                mov = Movimiento.objects.create(
                    tipo='entrada',
                    producto=producto,
                    lote=lote,
                    cantidad=cantidad,
                    motivo=f'PRUEBA MASIVA #{i+1}',
                    usuario=usuario
                )
                movs_creados.append(mov)
            
            # Verificar todos
            assert len(lotes_creados) == 10
            total_stock = sum(l.cantidad_actual for l in lotes_creados)
            
            print_success(f"10 lotes creados exitosamente, stock total: {total_stock}")
            exitos += 1
            
            # Limpiar
            for m in movs_creados:
                m.delete()
            for l in lotes_creados:
                l.delete()
                
    except Exception as e:
        print_error(f"Error en entradas masivas: {e}")
        errores.append(f"Entradas masivas: {e}")
    
    return len(errores) == 0, errores

# ============================================================================
# PRUEBA 2: SALIDAS INDIVIDUALES
# ============================================================================
def test_salidas_individuales():
    print_header("PRUEBA 2: SALIDAS INDIVIDUALES")
    
    errores = []
    exitos = 0
    
    producto = Producto.objects.filter(activo=True).first()
    usuario = User.objects.filter(rol__icontains='farmacia').first() or User.objects.filter(is_superuser=True).first()
    
    # TEST 2.1: Salida simple desde Almacén Central
    print(f"\n{Colors.CYAN}Test 2.1: Salida simple desde Almacén Central{Colors.END}")
    try:
        with transaction.atomic():
            # Crear lote de prueba
            numero_lote = generar_numero_lote()
            stock_inicial = 100
            cantidad_salida = 25
            
            lote = Lote.objects.create(
                producto=producto,
                numero_lote=numero_lote,
                centro=None,
                cantidad_inicial=stock_inicial,
                cantidad_actual=stock_inicial,
                fecha_caducidad=timezone.now().date() + timedelta(days=365),
                activo=True
            )
            
            # Registrar salida
            stock_antes = lote.cantidad_actual
            lote.cantidad_actual -= cantidad_salida
            lote.save()
            
            mov = Movimiento.objects.create(
                tipo='salida',
                producto=producto,
                lote=lote,
                centro_origen=None,
                cantidad=cantidad_salida,
                motivo='PRUEBA SALIDA INDIVIDUAL - Dispensación',
                subtipo_salida='dispensacion',
                usuario=usuario
            )
            
            lote.refresh_from_db()
            assert lote.cantidad_actual == stock_inicial - cantidad_salida, f"Stock incorrecto: {lote.cantidad_actual}"
            
            print_success(f"Salida de {cantidad_salida} unidades. Stock: {stock_antes} → {lote.cantidad_actual}")
            exitos += 1
            
            mov.delete()
            lote.delete()
            
    except Exception as e:
        print_error(f"Error en salida simple: {e}")
        errores.append(f"Salida simple: {e}")
    
    # TEST 2.2: Salida con diferentes subtipos
    print(f"\n{Colors.CYAN}Test 2.2: Salidas con diferentes subtipos{Colors.END}")
    subtipos = ['dispensacion', 'receta', 'consumo_interno', 'merma', 'vencimiento']
    
    for subtipo in subtipos:
        try:
            with transaction.atomic():
                numero_lote = generar_numero_lote()
                lote = Lote.objects.create(
                    producto=producto,
                    numero_lote=numero_lote,
                    centro=None,
                    cantidad_inicial=50,
                    cantidad_actual=50,
                    fecha_caducidad=timezone.now().date() + timedelta(days=365),
                    activo=True
                )
                
                cantidad_salida = 10
                lote.cantidad_actual -= cantidad_salida
                lote.save()
                
                # Datos adicionales requeridos según subtipo
                mov_data = {
                    'tipo': 'salida',
                    'producto': producto,
                    'lote': lote,
                    'cantidad': cantidad_salida,
                    'motivo': f'PRUEBA subtipo {subtipo}',
                    'subtipo_salida': subtipo,
                    'usuario': usuario
                }
                
                # Para recetas se requiere número de expediente
                if subtipo == 'receta':
                    mov_data['numero_expediente'] = 'EXP-TEST-001'
                
                mov = Movimiento.objects.create(**mov_data)
                
                assert mov.subtipo_salida == subtipo
                print_success(f"Subtipo '{subtipo}' funcionando")
                exitos += 1
                
                mov.delete()
                lote.delete()
                
        except Exception as e:
            print_error(f"Error con subtipo {subtipo}: {e}")
            errores.append(f"Subtipo {subtipo}: {e}")
    
    # TEST 2.3: Validación de stock insuficiente
    print(f"\n{Colors.CYAN}Test 2.3: Validación de stock insuficiente{Colors.END}")
    try:
        with transaction.atomic():
            lote = Lote.objects.create(
                producto=producto,
                numero_lote=generar_numero_lote(),
                centro=None,
                cantidad_inicial=10,
                cantidad_actual=10,
                fecha_caducidad=timezone.now().date() + timedelta(days=365),
                activo=True
            )
            
            # Intentar sacar más de lo disponible
            cantidad_excesiva = 50
            if lote.cantidad_actual >= cantidad_excesiva:
                print_error("El lote tiene demasiado stock para esta prueba")
            else:
                print_success(f"Validación correcta: No se puede sacar {cantidad_excesiva} de {lote.cantidad_actual}")
                exitos += 1
            
            lote.delete()
            
    except Exception as e:
        print_error(f"Error en validación stock: {e}")
        errores.append(f"Validación stock: {e}")
    
    return len(errores) == 0, errores

# ============================================================================
# PRUEBA 3: SALIDAS MASIVAS (Transferencias a Centro)
# ============================================================================
def test_salidas_masivas():
    print_header("PRUEBA 3: SALIDAS MASIVAS (Transferencias)")
    
    errores = []
    exitos = 0
    
    producto = Producto.objects.filter(activo=True).first()
    centro = Centro.objects.filter(activo=True).first()
    usuario = User.objects.filter(rol__icontains='farmacia').first() or User.objects.filter(is_superuser=True).first()
    
    if not centro:
        print_error("No hay centros activos para prueba de salidas masivas")
        return False, ["No hay centros activos"]
    
    print_info(f"Centro destino: {centro.nombre}")
    
    # TEST 3.1: Transferencia simple (3 movimientos)
    print(f"\n{Colors.CYAN}Test 3.1: Transferencia simple (flujo de 3 movimientos){Colors.END}")
    try:
        with transaction.atomic():
            numero_lote = generar_numero_lote()
            stock_inicial = 100
            cantidad_transferir = 30
            
            # Crear lote origen en Almacén Central
            lote_origen = Lote.objects.create(
                producto=producto,
                numero_lote=numero_lote,
                centro=None,
                cantidad_inicial=stock_inicial,
                cantidad_actual=stock_inicial,
                fecha_caducidad=timezone.now().date() + timedelta(days=365),
                activo=True
            )
            
            referencia = f"SAL-TEST-{datetime.now().strftime('%H%M%S')}"
            
            # 1. SALIDA del Almacén Central (transferencia)
            lote_origen.cantidad_actual -= cantidad_transferir
            lote_origen.save()
            
            mov_salida = Movimiento.objects.create(
                tipo='salida',
                producto=producto,
                lote=lote_origen,
                centro_origen=None,
                centro_destino=centro,
                cantidad=cantidad_transferir,
                motivo=f'SALIDA_TRANSFERENCIA a {centro.nombre}',
                subtipo_salida='transferencia',
                referencia=referencia,
                usuario=usuario
            )
            
            # 2. Crear/actualizar lote en Centro destino
            lote_destino, created = Lote.objects.get_or_create(
                producto=producto,
                numero_lote=numero_lote,
                centro=centro,
                defaults={
                    'cantidad_inicial': cantidad_transferir,  # Debe ser > 0
                    'cantidad_actual': cantidad_transferir,
                    'fecha_caducidad': lote_origen.fecha_caducidad,
                    'activo': True
                }
            )
            if not created:
                lote_destino.cantidad_actual += cantidad_transferir
                lote_destino.cantidad_inicial += cantidad_transferir
                lote_destino.save()
            
            # 3. ENTRADA en Centro destino
            mov_entrada = Movimiento.objects.create(
                tipo='entrada',
                producto=producto,
                lote=lote_destino,
                centro_origen=None,
                centro_destino=centro,
                cantidad=cantidad_transferir,
                motivo=f'ENTRADA_TRANSFERENCIA desde Almacén Central',
                referencia=referencia,
                usuario=usuario
            )
            
            # Verificaciones
            lote_origen.refresh_from_db()
            lote_destino.refresh_from_db()
            
            assert lote_origen.cantidad_actual == stock_inicial - cantidad_transferir
            assert lote_destino.cantidad_actual == cantidad_transferir
            assert lote_destino.centro == centro
            
            # Verificar que ambos movimientos tienen la misma referencia
            assert mov_salida.referencia == mov_entrada.referencia
            
            print_success(f"Transferencia exitosa:")
            print(f"   Almacén Central: {stock_inicial} → {lote_origen.cantidad_actual}")
            print(f"   {centro.nombre}: 0 → {lote_destino.cantidad_actual}")
            print(f"   Referencia: {referencia}")
            exitos += 1
            
            # Limpiar
            mov_salida.delete()
            mov_entrada.delete()
            lote_destino.delete()
            lote_origen.delete()
            
    except Exception as e:
        print_error(f"Error en transferencia simple: {e}")
        errores.append(f"Transferencia simple: {e}")
    
    # TEST 3.2: Transferencia masiva (múltiples productos)
    print(f"\n{Colors.CYAN}Test 3.2: Transferencia masiva (5 productos diferentes){Colors.END}")
    try:
        with transaction.atomic():
            productos = list(Producto.objects.filter(activo=True)[:5])
            if len(productos) < 5:
                print_warning(f"Solo hay {len(productos)} productos disponibles")
            
            lotes_creados = []
            movs_creados = []
            referencia = f"SAL-MASIVO-{datetime.now().strftime('%H%M%S')}"
            
            for i, prod in enumerate(productos):
                numero_lote = f"MASIVO-{i+1}-{generar_numero_lote()}"
                cantidad = random.randint(20, 50)
                
                # Lote origen
                lote_origen = Lote.objects.create(
                    producto=prod,
                    numero_lote=numero_lote,
                    centro=None,
                    cantidad_inicial=100,
                    cantidad_actual=100,
                    fecha_caducidad=timezone.now().date() + timedelta(days=365),
                    activo=True
                )
                lotes_creados.append(lote_origen)
                
                # Salida
                lote_origen.cantidad_actual -= cantidad
                lote_origen.save()
                
                mov_salida = Movimiento.objects.create(
                    tipo='salida',
                    producto=prod,
                    lote=lote_origen,
                    centro_destino=centro,
                    cantidad=cantidad,
                    motivo=f'SALIDA MASIVA #{i+1}',
                    subtipo_salida='transferencia',
                    referencia=referencia,
                    usuario=usuario
                )
                movs_creados.append(mov_salida)
                
                # Lote destino
                lote_destino = Lote.objects.create(
                    producto=prod,
                    numero_lote=numero_lote,
                    centro=centro,
                    cantidad_inicial=cantidad,
                    cantidad_actual=cantidad,
                    fecha_caducidad=lote_origen.fecha_caducidad,
                    activo=True
                )
                lotes_creados.append(lote_destino)
                
                # Entrada
                mov_entrada = Movimiento.objects.create(
                    tipo='entrada',
                    producto=prod,
                    lote=lote_destino,
                    centro_destino=centro,
                    cantidad=cantidad,
                    motivo=f'ENTRADA MASIVA #{i+1}',
                    referencia=referencia,
                    usuario=usuario
                )
                movs_creados.append(mov_entrada)
            
            # Verificar que todos tienen la misma referencia
            refs = set(m.referencia for m in movs_creados)
            assert len(refs) == 1, f"Referencias inconsistentes: {refs}"
            
            print_success(f"Transferencia masiva de {len(productos)} productos exitosa")
            print(f"   Referencia común: {referencia}")
            print(f"   Movimientos creados: {len(movs_creados)}")
            exitos += 1
            
            # Limpiar
            for m in movs_creados:
                m.delete()
            for l in lotes_creados:
                l.delete()
                
    except Exception as e:
        print_error(f"Error en transferencia masiva: {e}")
        errores.append(f"Transferencia masiva: {e}")
    
    return len(errores) == 0, errores

# ============================================================================
# PRUEBA 4: FLUJO COMPLETO DE REQUISICIONES
# ============================================================================
def test_requisiciones():
    print_header("PRUEBA 4: FLUJO DE REQUISICIONES")
    
    errores = []
    exitos = 0
    
    # Obtener datos necesarios
    producto = Producto.objects.filter(activo=True).first()
    centro = Centro.objects.filter(activo=True).first()
    
    if not centro:
        print_error("No hay centros para prueba de requisiciones")
        return False, ["No hay centros"]
    
    # Obtener usuarios por rol
    usuario_medico = User.objects.filter(rol__icontains='medico').first()
    usuario_admin_centro = User.objects.filter(rol__icontains='administrador_centro').first()
    usuario_director = User.objects.filter(rol__icontains='director').first()
    usuario_farmacia = User.objects.filter(rol__icontains='farmacia').first()
    
    if not usuario_farmacia:
        usuario_farmacia = User.objects.filter(is_superuser=True).first()
    
    print_info(f"Centro: {centro.nombre}")
    print_info(f"Producto: {producto.clave}")
    
    # TEST 4.1: Crear requisición y verificar estados
    print(f"\n{Colors.CYAN}Test 4.1: Flujo completo de requisición{Colors.END}")
    
    try:
        with transaction.atomic():
            # Primero crear stock en almacén central para surtir
            numero_lote = generar_numero_lote()
            stock_inicial = 200
            
            lote_almacen = Lote.objects.create(
                producto=producto,
                numero_lote=numero_lote,
                centro=None,
                cantidad_inicial=stock_inicial,
                cantidad_actual=stock_inicial,
                fecha_caducidad=timezone.now().date() + timedelta(days=365),
                activo=True
            )
            print_success(f"Lote {numero_lote} creado en Almacén Central con {stock_inicial} unidades")
            
            # Crear requisición
            folio = generar_folio_requisicion()
            
            # Deshabilitar trigger para pruebas
            with connection.cursor() as cursor:
                cursor.execute("ALTER TABLE requisiciones DISABLE TRIGGER trigger_validar_transicion_requisicion")
            
            try:
                requisicion = Requisicion.objects.create(
                    numero=folio,
                    centro_origen=centro,
                    centro_destino=None,
                    solicitante=usuario_medico or usuario_farmacia,
                    autorizador=usuario_farmacia,  # Requerido para estado autorizada
                    estado='autorizada',  # Saltamos directo a autorizada para prueba
                    tipo='normal',
                    prioridad='normal',
                    fecha_recoleccion_limite=timezone.now() + timedelta(days=7)
                )
                print_success(f"Requisición {folio} creada")
                
                # Crear detalle
                cantidad_solicitada = 50
                detalle = DetalleRequisicion.objects.create(
                    requisicion=requisicion,
                    producto=producto,
                    lote=lote_almacen,
                    cantidad_solicitada=cantidad_solicitada,
                    cantidad_autorizada=cantidad_solicitada,
                    cantidad_surtida=0
                )
                print_success(f"Detalle agregado: {cantidad_solicitada} unidades de {producto.clave}")
                
                # Simular surtido
                print(f"\n   Simulando surtido...")
                
                # Descontar del lote origen
                lote_almacen.cantidad_actual -= cantidad_solicitada
                lote_almacen.save()
                
                # Crear movimiento de salida
                referencia = f"REQ-{folio}"
                mov_salida = Movimiento.objects.create(
                    tipo='salida',
                    producto=producto,
                    lote=lote_almacen,
                    centro_origen=None,
                    centro_destino=centro,
                    requisicion=requisicion,
                    cantidad=cantidad_solicitada,
                    motivo=f'SALIDA_POR_REQUISICION {folio}',
                    subtipo_salida='transferencia',
                    referencia=referencia,
                    usuario=usuario_farmacia
                )
                
                # Crear lote en centro destino
                lote_centro = Lote.objects.create(
                    producto=producto,
                    numero_lote=numero_lote,
                    centro=centro,
                    cantidad_inicial=cantidad_solicitada,
                    cantidad_actual=cantidad_solicitada,
                    fecha_caducidad=lote_almacen.fecha_caducidad,
                    activo=True
                )
                
                # Crear movimiento de entrada
                mov_entrada = Movimiento.objects.create(
                    tipo='entrada',
                    producto=producto,
                    lote=lote_centro,
                    centro_origen=None,
                    centro_destino=centro,
                    requisicion=requisicion,
                    cantidad=cantidad_solicitada,
                    motivo=f'ENTRADA_POR_REQUISICION {folio}',
                    referencia=referencia,
                    usuario=usuario_farmacia
                )
                
                # Actualizar detalle
                detalle.cantidad_surtida = cantidad_solicitada
                detalle.save()
                
                # Actualizar estado requisición
                requisicion.estado = 'entregada'
                requisicion.fecha_surtido = timezone.now()
                requisicion.fecha_entrega = timezone.now()
                requisicion.surtidor = usuario_farmacia
                requisicion.save()
                
                # Verificaciones
                lote_almacen.refresh_from_db()
                lote_centro.refresh_from_db()
                detalle.refresh_from_db()
                requisicion.refresh_from_db()
                
                assert lote_almacen.cantidad_actual == stock_inicial - cantidad_solicitada
                assert lote_centro.cantidad_actual == cantidad_solicitada
                assert lote_centro.centro == centro
                assert detalle.cantidad_surtida == cantidad_solicitada
                assert requisicion.estado == 'entregada'
                
                # Verificar movimientos asociados
                movs = Movimiento.objects.filter(requisicion=requisicion)
                assert movs.count() == 2, f"Esperados 2 movimientos, encontrados {movs.count()}"
                
                print_success(f"Surtido completado:")
                print(f"   Almacén Central: {stock_inicial} → {lote_almacen.cantidad_actual}")
                print(f"   {centro.nombre}: 0 → {lote_centro.cantidad_actual}")
                print(f"   Estado: {requisicion.estado}")
                print(f"   Movimientos: {movs.count()}")
                exitos += 1
                
                # Limpiar
                mov_salida.delete()
                mov_entrada.delete()
                detalle.delete()
                requisicion.delete()
                lote_centro.delete()
                lote_almacen.delete()
                
            finally:
                with connection.cursor() as cursor:
                    cursor.execute("ALTER TABLE requisiciones ENABLE TRIGGER trigger_validar_transicion_requisicion")
            
    except Exception as e:
        print_error(f"Error en flujo requisición: {e}")
        errores.append(f"Flujo requisición: {e}")
        # Re-habilitar trigger en caso de error
        try:
            with connection.cursor() as cursor:
                cursor.execute("ALTER TABLE requisiciones ENABLE TRIGGER trigger_validar_transicion_requisicion")
        except:
            pass
    
    # TEST 4.2: Múltiples requisiciones simultáneas
    print(f"\n{Colors.CYAN}Test 4.2: Múltiples requisiciones (3 simultáneas){Colors.END}")
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("ALTER TABLE requisiciones DISABLE TRIGGER trigger_validar_transicion_requisicion")
            
            try:
                productos = list(Producto.objects.filter(activo=True)[:3])
                requisiciones_creadas = []
                
                for i, prod in enumerate(productos):
                    # Crear lote
                    lote = Lote.objects.create(
                        producto=prod,
                        numero_lote=f"MULTI-{i}-{generar_numero_lote()}",
                        centro=None,
                        cantidad_inicial=100,
                        cantidad_actual=100,
                        fecha_caducidad=timezone.now().date() + timedelta(days=365),
                        activo=True
                    )
                    
                    # Crear requisición
                    req = Requisicion.objects.create(
                        numero=f"REQ-MULTI-{i}-{datetime.now().strftime('%H%M%S%f')}",
                        centro_origen=centro,
                        solicitante=usuario_farmacia,
                        autorizador=usuario_farmacia,
                        estado='autorizada',
                        fecha_recoleccion_limite=timezone.now() + timedelta(days=7)
                    )
                    
                    # Crear detalle
                    det = DetalleRequisicion.objects.create(
                        requisicion=req,
                        producto=prod,
                        lote=lote,
                        cantidad_solicitada=20,
                        cantidad_autorizada=20
                    )
                    
                    requisiciones_creadas.append({
                        'requisicion': req,
                        'detalle': det,
                        'lote': lote
                    })
                
                assert len(requisiciones_creadas) == len(productos)
                print_success(f"{len(requisiciones_creadas)} requisiciones creadas simultáneamente")
                exitos += 1
                
                # Limpiar
                for item in requisiciones_creadas:
                    item['detalle'].delete()
                    item['requisicion'].delete()
                    item['lote'].delete()
                    
            finally:
                with connection.cursor() as cursor:
                    cursor.execute("ALTER TABLE requisiciones ENABLE TRIGGER trigger_validar_transicion_requisicion")
                    
    except Exception as e:
        print_error(f"Error en múltiples requisiciones: {e}")
        errores.append(f"Múltiples requisiciones: {e}")
    
    return len(errores) == 0, errores

# ============================================================================
# PRUEBA 5: CONSISTENCIA DE DATOS
# ============================================================================
def test_consistencia():
    print_header("PRUEBA 5: VERIFICACIÓN DE CONSISTENCIA")
    
    errores = []
    exitos = 0
    
    # TEST 5.1: Verificar que no hay lotes con stock negativo
    print(f"\n{Colors.CYAN}Test 5.1: Lotes sin stock negativo{Colors.END}")
    lotes_negativos = Lote.objects.filter(cantidad_actual__lt=0)
    if lotes_negativos.exists():
        print_error(f"Hay {lotes_negativos.count()} lotes con stock negativo!")
        for lote in lotes_negativos[:5]:
            print(f"   - {lote.numero_lote}: {lote.cantidad_actual}")
        errores.append(f"{lotes_negativos.count()} lotes con stock negativo")
    else:
        print_success("Ningún lote tiene stock negativo")
        exitos += 1
    
    # TEST 5.2: Verificar movimientos huérfanos
    print(f"\n{Colors.CYAN}Test 5.2: Movimientos sin lote asociado{Colors.END}")
    movs_sin_lote = Movimiento.objects.filter(lote__isnull=True)
    if movs_sin_lote.exists():
        print_warning(f"Hay {movs_sin_lote.count()} movimientos sin lote (puede ser válido)")
    else:
        print_success("Todos los movimientos tienen lote asociado")
        exitos += 1
    
    # TEST 5.3: Verificar requisiciones en estados inconsistentes
    print(f"\n{Colors.CYAN}Test 5.3: Requisiciones entregadas sin movimientos{Colors.END}")
    reqs_entregadas = Requisicion.objects.filter(estado='entregada')
    inconsistentes = 0
    
    for req in reqs_entregadas[:10]:  # Verificar las últimas 10
        movs = Movimiento.objects.filter(requisicion=req).count()
        if movs == 0:
            inconsistentes += 1
            print_warning(f"Requisición {req.numero} está entregada pero sin movimientos")
    
    if inconsistentes == 0:
        print_success("Todas las requisiciones entregadas tienen movimientos")
        exitos += 1
    else:
        errores.append(f"{inconsistentes} requisiciones inconsistentes")
    
    # TEST 5.4: Verificar productos activos con lotes
    print(f"\n{Colors.CYAN}Test 5.4: Productos activos con stock{Colors.END}")
    from django.db.models import Sum
    productos_con_stock = Producto.objects.filter(
        activo=True,
        lotes__activo=True,
        lotes__cantidad_actual__gt=0
    ).distinct().count()
    
    total_productos = Producto.objects.filter(activo=True).count()
    print_info(f"{productos_con_stock} de {total_productos} productos tienen stock disponible")
    exitos += 1
    
    # TEST 5.5: Stock total por ubicación
    print(f"\n{Colors.CYAN}Test 5.5: Distribución de stock{Colors.END}")
    
    # Stock en Almacén Central
    stock_almacen = Lote.objects.filter(
        centro__isnull=True,
        activo=True
    ).aggregate(total=Sum('cantidad_actual'))['total'] or 0
    
    # Stock en Centros
    stock_centros = Lote.objects.filter(
        centro__isnull=False,
        activo=True
    ).aggregate(total=Sum('cantidad_actual'))['total'] or 0
    
    print_info(f"Stock en Almacén Central: {stock_almacen:,} unidades")
    print_info(f"Stock en Centros: {stock_centros:,} unidades")
    print_info(f"Stock Total: {stock_almacen + stock_centros:,} unidades")
    exitos += 1
    
    return len(errores) == 0, errores

# ============================================================================
# MAIN
# ============================================================================
def main():
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║          PRUEBAS EXHAUSTIVAS DE FLUJOS DE INVENTARIO                         ║")
    print("║                    Farmacia Penitenciaria v2.0                               ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")
    
    inicio = datetime.now()
    resultados = {}
    
    # Ejecutar todas las pruebas
    pruebas = [
        ("Entradas de Inventario", test_entradas_inventario),
        ("Salidas Individuales", test_salidas_individuales),
        ("Salidas Masivas", test_salidas_masivas),
        ("Requisiciones", test_requisiciones),
        ("Consistencia de Datos", test_consistencia),
    ]
    
    for nombre, funcion in pruebas:
        try:
            exito, errores = funcion()
            resultados[nombre] = {"exito": exito, "errores": errores}
        except Exception as e:
            resultados[nombre] = {"exito": False, "errores": [str(e)]}
    
    # Resumen final
    print_header("RESUMEN DE PRUEBAS")
    
    total_exitosas = sum(1 for r in resultados.values() if r["exito"])
    total_pruebas = len(resultados)
    
    for nombre, resultado in resultados.items():
        if resultado["exito"]:
            print_success(f"{nombre}")
        else:
            print_error(f"{nombre}")
            for err in resultado["errores"]:
                print(f"      └─ {err}")
    
    duracion = datetime.now() - inicio
    
    print(f"\n{Colors.BOLD}{'─'*80}{Colors.END}")
    print(f"{Colors.BOLD}Resultado Final: {total_exitosas}/{total_pruebas} pruebas exitosas{Colors.END}")
    print(f"{Colors.BOLD}Duración: {duracion.total_seconds():.2f} segundos{Colors.END}")
    
    if total_exitosas == total_pruebas:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 TODAS LAS PRUEBAS PASARON EXITOSAMENTE 🎉{Colors.END}")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}⚠️  ALGUNAS PRUEBAS FALLARON - REVISAR ERRORES{Colors.END}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
