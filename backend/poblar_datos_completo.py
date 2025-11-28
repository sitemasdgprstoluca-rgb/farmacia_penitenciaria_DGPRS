"""
Script para poblar la base de datos con datos de prueba completos
Ejecutar: python manage.py shell < poblar_datos_completo.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.utils import timezone
from datetime import timedelta
from core.models import User, Centro, Producto, Lote, Movimiento, Requisicion, DetalleRequisicion
import random

print("🔄 Iniciando población de datos de prueba...")

# 1. Crear movimientos para los últimos 6 meses
print("\n📊 Creando movimientos históricos (últimos 6 meses)...")
movimientos_creados = 0

for i in range(180):  # 180 días = 6 meses
    fecha = timezone.now() - timedelta(days=i)
    
    # Crear entre 1 y 5 movimientos por día
    for j in range(random.randint(1, 5)):
        try:
            lote = Lote.objects.filter(estado='disponible').order_by('?').first()
            if not lote:
                continue
                
            tipo = random.choice(['entrada', 'salida'])
            cantidad = random.randint(10, 100)
            usuario = User.objects.filter(is_active=True).order_by('?').first()
            
            if not usuario:
                continue
            
            Movimiento.objects.create(
                tipo=tipo,
                producto=lote.producto,
                lote=lote,
                cantidad=cantidad,
                fecha=fecha,
                usuario=usuario,
                observaciones=f'Movimiento de prueba generado automáticamente'
            )
            movimientos_creados += 1
        except Exception as e:
            print(f"⚠️  Error creando movimiento: {e}")
            continue

print(f"✅ {movimientos_creados} movimientos creados")

# 2. Crear requisiciones en diferentes estados
print("\n📝 Creando requisiciones en diferentes estados...")
requisiciones_creadas = 0

estados = ['borrador', 'enviada', 'autorizada', 'rechazada', 'surtida']
centros = list(Centro.objects.filter(activo=True))
usuarios = list(User.objects.filter(is_active=True))

if not centros or not usuarios:
    print("⚠️  No hay centros o usuarios disponibles")
else:
    for estado in estados:
        # Crear entre 5 y 15 requisiciones por estado
        cantidad = random.randint(5, 15)
        
        for i in range(cantidad):
            try:
                centro = random.choice(centros)
                usuario = random.choice(usuarios)
                dias_atras = random.randint(1, 180)
                fecha = timezone.now() - timedelta(days=dias_atras)
                
                req = Requisicion.objects.create(
                    centro=centro,
                    usuario_solicita=usuario,
                    estado=estado,
                    fecha_solicitud=fecha,
                    observaciones=f'Requisición de prueba en estado {estado}'
                )
                
                # Agregar detalles a la requisición
                productos = list(Producto.objects.filter(activo=True).order_by('?')[:random.randint(3, 8)])
                for producto in productos:
                    DetalleRequisicion.objects.create(
                        requisicion=req,
                        producto=producto,
                        cantidad_solicitada=random.randint(10, 100),
                        cantidad_autorizada=random.randint(5, 100) if estado in ['autorizada', 'surtida'] else 0
                    )
                
                # Si está autorizada o rechazada, asignar usuario autorizador
                if estado in ['autorizada', 'rechazada', 'surtida']:
                    req.usuario_autoriza = random.choice([u for u in usuarios if u.is_staff])
                    req.fecha_autorizacion = fecha + timedelta(hours=random.randint(2, 48))
                    if estado == 'rechazada':
                        req.motivo_rechazo = 'Falta de stock / Requisición de prueba rechazada'
                    req.save()
                
                requisiciones_creadas += 1
            except Exception as e:
                print(f"⚠️  Error creando requisición: {e}")
                continue
    
    print(f"✅ {requisiciones_creadas} requisiciones creadas")

# 3. Estadísticas finales
print("\n" + "="*60)
print("📊 RESUMEN DE DATOS GENERADOS")
print("="*60)
print(f"Productos: {Producto.objects.count()}")
print(f"Lotes: {Lote.objects.filter(deleted_at__isnull=True).count()}")
print(f"Centros: {Centro.objects.filter(activo=True).count()}")
print(f"Usuarios: {User.objects.filter(is_active=True).count()}")
print(f"Movimientos: {Movimiento.objects.count()}")
print(f"Requisiciones: {Requisicion.objects.count()}")
print("\nRequisiciones por estado:")
for estado in estados:
    count = Requisicion.objects.filter(estado=estado).count()
    print(f"  - {estado.capitalize()}: {count}")
print("="*60)
print("✅ ¡Datos de prueba generados exitosamente!")
print("\n💡 Ahora puedes:")
print("   1. Ver el Dashboard con gráficas pobladas")
print("   2. Explorar Auditoría con logs de acciones")
print("   3. Generar reportes con datos reales")
print("   4. Probar Trazabilidad con productos existentes")
