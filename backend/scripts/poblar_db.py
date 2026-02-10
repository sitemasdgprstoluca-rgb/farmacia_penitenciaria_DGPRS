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
    {'nombre': 'Centro Penitenciario Norte', 'direccion': 'Av. Norte #123, Col. Centro', 'telefono': '555-1111'},
    {'nombre': 'Centro Penitenciario Sur', 'direccion': 'Av. Sur #456, Col. Reforma', 'telefono': '555-2222'},
    {'nombre': 'Centro Penitenciario Este', 'direccion': 'Av. Este #789, Col. Industrial', 'telefono': '555-3333'},
    {'nombre': 'Centro Penitenciario Oeste', 'direccion': 'Av. Oeste #321, Col. Moderna', 'telefono': '555-4444'},
    {'nombre': 'Centro Penitenciario Central', 'direccion': 'Calle Central #555, Centro Histórico', 'telefono': '555-5555'},
]

for centro_data in centros_data:
    centro, created = Centro.objects.get_or_create(
        nombre=centro_data['nombre'],
        defaults=centro_data
    )
    if created:
        print(f"✅ Centro creado: {centro.nombre}")
    else:
        print(f"ℹ️  Centro existente: {centro.nombre}")

# Crear Productos
print("\n💊 Creando productos...")
productos_data = [
    {'codigo_barras': 'MED-001', 'nombre': 'Paracetamol 500mg', 'descripcion': 'Tabletas analgésicas', 'unidad_medida': 'pieza', 'categoria': 'medicamento', 'stock_minimo': 100},
    {'codigo_barras': 'MED-002', 'nombre': 'Ibuprofeno 400mg', 'descripcion': 'Cápsulas antiinflamatorias', 'unidad_medida': 'pieza', 'categoria': 'medicamento', 'stock_minimo': 80},
    {'codigo_barras': 'MED-003', 'nombre': 'Amoxicilina 500mg', 'descripcion': 'Antibiótico de amplio espectro', 'unidad_medida': 'pieza', 'categoria': 'medicamento', 'stock_minimo': 60},
    {'codigo_barras': 'MED-004', 'nombre': 'Omeprazol 20mg', 'descripcion': 'Inhibidor de bomba de protones', 'unidad_medida': 'pieza', 'categoria': 'medicamento', 'stock_minimo': 50},
    {'codigo_barras': 'MED-005', 'nombre': 'Loratadina 10mg', 'descripcion': 'Antihistamínico', 'unidad_medida': 'pieza', 'categoria': 'medicamento', 'stock_minimo': 40},
    {'codigo_barras': 'MED-006', 'nombre': 'Metformina 850mg', 'descripcion': 'Antidiabético oral', 'unidad_medida': 'pieza', 'categoria': 'medicamento', 'stock_minimo': 70},
    {'codigo_barras': 'MED-007', 'nombre': 'Atorvastatina 20mg', 'descripcion': 'Reductor de colesterol', 'unidad_medida': 'pieza', 'categoria': 'medicamento', 'stock_minimo': 50},
    {'codigo_barras': 'MED-008', 'nombre': 'Losartán 50mg', 'descripcion': 'Antihipertensivo', 'unidad_medida': 'pieza', 'categoria': 'medicamento', 'stock_minimo': 60},
    {'codigo_barras': 'MED-009', 'nombre': 'Clonazepam 2mg', 'descripcion': 'Ansiolítico controlado', 'unidad_medida': 'pieza', 'categoria': 'medicamento', 'stock_minimo': 30, 'es_controlado': True, 'requiere_receta': True},
    {'codigo_barras': 'MED-010', 'nombre': 'Ranitidina 150mg', 'descripcion': 'Antiácido', 'unidad_medida': 'pieza', 'categoria': 'medicamento', 'stock_minimo': 55},
]

for prod_data in productos_data:
    producto, created = Producto.objects.get_or_create(
        codigo_barras=prod_data['codigo_barras'],
        defaults=prod_data
    )
    if created:
        print(f"✅ Producto creado: {producto.nombre}")
    else:
        print(f"ℹ️  Producto existente: {producto.nombre}")

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
precios_base = [Decimal('2.50'), Decimal('3.00'), Decimal('5.00'), Decimal('4.50'), Decimal('3.50'),
                Decimal('4.00'), Decimal('6.50'), Decimal('5.50'), Decimal('7.00'), Decimal('3.80')]

for i, producto in enumerate(productos):
    # Crear 2 lotes por producto con diferentes estados
    for j, (estado, dias) in enumerate(estados_caducidad[:2]):
        cantidad = 150 + (j * 100)
        centro = centros[i % len(centros)] if centros.exists() else None
        precio_base = precios_base[i % len(precios_base)]
        precio = round(float(precio_base) * 0.7, 2)
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
            print(f"✅ Lote {estado}: {lote.numero_lote} - {producto.codigo_barras or producto.nombre}")
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
            producto=lote.producto,
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
