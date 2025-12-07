import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Producto, Centro, Lote, Movimiento
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from decimal import Decimal

User = get_user_model()

print("=" * 60)
print("🌱 POBLANDO BASE DE DATOS CON DATOS DE PRUEBA")
print("=" * 60)

# Crear usuario admin si no existe
print("\n👤 Creando usuario administrador...")
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print("✅ Usuario admin creado (username: admin, password: admin123)")
else:
    print("ℹ️  Usuario admin ya existe")

# Crear Centros Penitenciarios
print("\n🏢 Creando centros penitenciarios...")
centros_data = [
    {'clave': 'CP-001', 'nombre': 'Centro Penitenciario Norte', 'direccion': 'Av. Norte #123, Col. Centro', 'telefono': '555-1111'},
    {'clave': 'CP-002', 'nombre': 'Centro Penitenciario Sur', 'direccion': 'Av. Sur #456, Col. Reforma', 'telefono': '555-2222'},
    {'clave': 'CP-003', 'nombre': 'Centro Penitenciario Este', 'direccion': 'Av. Este #789, Col. Industrial', 'telefono': '555-3333'},
    {'clave': 'CP-004', 'nombre': 'Centro Penitenciario Oeste', 'direccion': 'Av. Oeste #321, Col. Moderna', 'telefono': '555-4444'},
    {'clave': 'CP-005', 'nombre': 'Centro Penitenciario Central', 'direccion': 'Calle Central #555, Centro Histórico', 'telefono': '555-5555'},
]

for centro_data in centros_data:
    centro, created = Centro.objects.get_or_create(
        clave=centro_data['clave'],
        defaults=centro_data
    )
    if created:
        print(f"✅ Centro creado: {centro.nombre}")
    else:
        print(f"ℹ️  Centro existente: {centro.nombre}")

# Crear Productos
print("\n💊 Creando productos...")
productos_data = [
    {'clave': 'MED-001', 'descripcion': 'Paracetamol 500mg', 'unidad_medida': 'TABLETA', 'precio_unitario': Decimal('2.50'), 'stock_minimo': 100},
    {'clave': 'MED-002', 'descripcion': 'Ibuprofeno 400mg', 'unidad_medida': 'CAPSULA', 'precio_unitario': Decimal('3.00'), 'stock_minimo': 80},
    {'clave': 'MED-003', 'descripcion': 'Amoxicilina 500mg', 'unidad_medida': 'CAPSULA', 'precio_unitario': Decimal('5.00'), 'stock_minimo': 60},
    {'clave': 'MED-004', 'descripcion': 'Omeprazol 20mg', 'unidad_medida': 'CAPSULA', 'precio_unitario': Decimal('4.50'), 'stock_minimo': 50},
    {'clave': 'MED-005', 'descripcion': 'Loratadina 10mg', 'unidad_medida': 'TABLETA', 'precio_unitario': Decimal('3.50'), 'stock_minimo': 40},
    {'clave': 'MED-006', 'descripcion': 'Metformina 850mg', 'unidad_medida': 'TABLETA', 'precio_unitario': Decimal('4.00'), 'stock_minimo': 70},
    {'clave': 'MED-007', 'descripcion': 'Atorvastatina 20mg', 'unidad_medida': 'TABLETA', 'precio_unitario': Decimal('6.50'), 'stock_minimo': 50},
    {'clave': 'MED-008', 'descripcion': 'Losartán 50mg', 'unidad_medida': 'TABLETA', 'precio_unitario': Decimal('5.50'), 'stock_minimo': 60},
    {'clave': 'MED-009', 'descripcion': 'Clonazepam 2mg', 'unidad_medida': 'TABLETA', 'precio_unitario': Decimal('7.00'), 'stock_minimo': 30},
    {'clave': 'MED-010', 'descripcion': 'Ranitidina 150mg', 'unidad_medida': 'TABLETA', 'precio_unitario': Decimal('3.80'), 'stock_minimo': 55},
]

for prod_data in productos_data:
    producto, created = Producto.objects.get_or_create(
        clave=prod_data['clave'],
        defaults=prod_data
    )
    if created:
        print(f"✅ Producto creado: {producto.descripcion}")
    else:
        print(f"ℹ️  Producto existente: {producto.descripcion}")

# Crear Lotes con diferentes estados de caducidad
print("\n📦 Creando lotes...")
productos = Producto.objects.all()
estados_caducidad = [
    ('VENCIDO', -10),
    ('CRITICO', 5),
    ('PROXIMO', 20),
    ('NORMAL', 180),
]

lote_counter = 1
centros = Centro.objects.all()
for i, producto in enumerate(productos):
    # Crear 2 lotes por producto con diferentes estados
    for j, (estado, dias) in enumerate(estados_caducidad[:2]):
        cantidad = 150 + (j * 100)
        centro = centros[i % len(centros)] if centros.exists() else None
        precio = round(float(producto.precio_unitario) * 0.7, 2)
        lote, created = Lote.objects.get_or_create(
            numero_lote=f'LOTE-2025-{lote_counter:03d}',
            producto=producto,
            defaults={
                'cantidad_inicial': cantidad,
                'cantidad_actual': cantidad,
                'fecha_caducidad': date.today() + timedelta(days=dias + (i * 10)),
                'marca': f'Laboratorio Farmacéutico {(i % 3) + 1}',
                'precio_unitario': Decimal(str(precio)),
                'centro': centro,
            }
        )
        if created:
            print(f"✅ Lote {estado}: {lote.numero_lote} - {producto.clave}")
        lote_counter += 1

# Crear algunos movimientos
print("\n📊 Creando movimientos de ejemplo...")
usuario = User.objects.first()
lotes = Lote.objects.filter(activo=True)  # Solo lotes activos

movimiento_counter = 0
for i, lote in enumerate(lotes):
    centro = lote.centro
    # Crear SALIDA (cantidad negativa)
    if lote.cantidad_actual > 50:
        Movimiento.objects.create(
            lote=lote,
            centro_origen=centro,
            tipo='salida',
            cantidad=-50,  # Negativo para salidas
            usuario=usuario,
            motivo='Salida a centro penitenciario'
        )
        movimiento_counter += 1
        print(f"✅ Salida creada para {lote.numero_lote}: -50 unidades")

print(f"\n✅ Total de movimientos creados: {movimiento_counter}")

print("\n" + "=" * 60)
print("✅ BASE DE DATOS POBLADA EXITOSAMENTE")
print("=" * 60)
print(f"\n📊 RESUMEN:")
print(f"  👤 Usuarios: {User.objects.count()}")
print(f"  🏢 Centros: {Centro.objects.count()}")
print(f"  💊 Productos: {Producto.objects.count()}")
print(f"  📦 Lotes: {Lote.objects.count()}")
print(f"  📋 Movimientos: {Movimiento.objects.count()}")
print("\n🔑 CREDENCIALES:")
print("  Usuario: admin")
print("  Password: admin123")
print("\n💡 PRUEBA LA TRAZABILIDAD:")
print("  - Por Producto: MED-001, MED-002, MED-003")
print("  - Por Lote: LOTE-2025-001, LOTE-2025-002")
print("=" * 60)
