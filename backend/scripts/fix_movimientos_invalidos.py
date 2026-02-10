"""Fix movimientos con cantidad inválida."""
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Movimiento

print("🔍 Buscando movimientos con cantidad <= 0...")
movimientos_invalidos = Movimiento.objects.filter(cantidad__lte=0)

print(f"\nEncontrados: {movimientos_invalidos.count()} movimientos\n")

for m in movimientos_invalidos:
    print(f"ID: {m.id}")
    print(f"  Tipo: {m.tipo}")
    print(f"  Cantidad: {m.cantidad}")
    print(f"  Lote: {m.lote.numero_lote if m.lote else 'N/A'}")
    print(f"  Producto: {m.lote.producto.clave if m.lote and m.lote.producto else 'N/A'}")
    print(f"  Centro: {m.centro.nombre if m.centro else 'N/A'}")
    print(f"  Fecha: {m.fecha}")
    print(f"  Usuario: {m.usuario.username if m.usuario else 'N/A'}")
    print()

# Eliminar o corregir
if movimientos_invalidos.exists():
    respuesta = input("¿Deseas ELIMINAR estos movimientos inválidos? (s/n): ")
    if respuesta.lower() == 's':
        count = movimientos_invalidos.count()
        movimientos_invalidos.delete()
        print(f"✅ {count} movimientos eliminados")
    else:
        print("❌ No se eliminaron movimientos")
else:
    print("✅ No hay movimientos inválidos")
