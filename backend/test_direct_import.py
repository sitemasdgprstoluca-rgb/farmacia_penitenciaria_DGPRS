"""
Script SIMPLIFICADO para probar importación de productos.
Este script hace EXACTAMENTE lo mismo que el test anterior, pero importa directamente.
"""
import os
import sys
import django
from pathlib import Path

# Setup Django
sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Ahora importamos después de django.setup()
from django.contrib.auth import get_user_model
from core.utils.excel_importer import importar_productos_desde_excel

User = get_user_model()

# Configuración
ARCHIVO_PLANTILLA = r"C:\Users\zarag\Downloads\REVISAR\Plantilla_Productos.xlsx"

def test_direct_import():
    """Prueba la importación directamente SIN pasar por la API."""
    
    print("=" * 70)
    print("TEST DIRECTO DE IMPORTACIÓN DE PRODUCTOS (SIN API)")
    print("=" * 70)
    
    # 1. Verificar que existe el archivo
    if not os.path.exists(ARCHIVO_PLANTILLA):
        print(f"\n❌ ERROR: No se encuentra el archivo: {ARCHIVO_PLANTILLA}")
        return
    
    print(f"\n✓ Archivo encontrado: {ARCHIVO_PLANTILLA}")
    file_size = os.path.getsize(ARCHIVO_PLANTILLA)
    print(f"  Tamaño: {file_size / 1024:.2f} KB")
    
    # 2. Obtener usuario de farmacia
    try:
        user = User.objects.filter(rol='farmacia').first()
        if not user:
            print("\n❌ ERROR: No hay usuario con rol 'farmacia'")
            return
        
        print(f"✓ Usuario farmacia: {user.email}")
    except Exception as e:
        print(f"\n❌ ERROR al buscar usuario: {e}")
        return
    
    # 3. Abrir archivo y ejecutar importación DIRECTA
    try:
        print(f"\n🔄 Importando productos directamente desde archivo...")
        
        with open(ARCHIVO_PLANTILLA, 'rb') as file:
            # Crear un objeto que simule el UploadedFile de Django
            from django.core.files.uploadedfile import InMemoryUploadedFile
            from io import BytesIO
            
            # Leer contenido completo
            content = file.read()
            file_obj = InMemoryUploadedFile(
                file=BytesIO(content),
                field_name='file',
                name=os.path.basename(ARCHIVO_PLANTILLA),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                size=len(content),
                charset=None
            )
            
            # Ejecutar importación
            resultado = importar_productos_desde_excel(file_obj, user)
            
            print(f"\n📊 RESULTADO:")
            print(f"   Exitosa: {resultado.get('exitosa', False)}")
            print(f"   Total procesados: {resultado.get('registros_totales', 0)}")
            print(f"   Exitosos: {resultado.get('registros_exitosos', 0)}")
            print(f"   Fallidos: {resultado.get('registros_fallidos', 0)}")
            
            if resultado.get('errores'):
                print(f"\n⚠️  ERRORES ENCONTRADOS ({len(resultado['errores'])}):")
                for i, err in enumerate(resultado['errores'][:10], 1):  # Mostrar primeros 10
                    print(f"   {i}. {err}")
                if len(resultado['errores']) > 10:
                    print(f"   ... y {len(resultado['errores']) - 10} más")
            
            resumen = resultado.get('resumen', {})
            if resumen:
                print(f"\n📋 RESUMEN:")
                print(f"   Creados: {resumen.get('creados', 0)}")
                print(f"   Actualizados: {resumen.get('actualizados', 0)}")
                print(f"   Omitidos: {resumen.get('omitidos', 0)}")
            
            if resultado.get('exitosa'):
                print(f"\n✅ IMPORTACIÓN EXITOSA!")
            else:
                print(f"\n❌ IMPORTACIÓN CON ERRORES")
                
    except Exception as e:
        print(f"\n❌ ERROR DURANTE IMPORTACIÓN:")
        print(f"   Tipo: {type(e).__name__}")
        print(f"   Mensaje: {str(e)}")
        import traceback
        print(f"\n   Traceback:")
        traceback.print_exc()
    
    print("\n" + "=" * 70)


if __name__ == '__main__':
    test_direct_import()
