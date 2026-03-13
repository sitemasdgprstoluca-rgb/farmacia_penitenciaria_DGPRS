#!/usr/bin/env python
"""
Script de verificación para la funcionalidad de Documentos Firmados en Dispensaciones
"""

import os
import sys

# Agregar el directorio del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

def verificar_modelo():
    """Verifica que el modelo Dispensacion tenga los campos correctos"""
    print("✓ Verificando modelo Dispensacion...")
    from core.models import Dispensacion
    
    campos_requeridos = [
        'documento_firmado_url',
        'documento_firmado_nombre',
        'documento_firmado_fecha',
        'documento_firmado_por',
        'documento_firmado_tamano'
    ]
    
    for campo in campos_requeridos:
        if hasattr(Dispensacion, campo):
            print(f"  ✓ Campo '{campo}' existe")
        else:
            print(f"  ✗ Campo '{campo}' NO existe")
            return False
    
    return True

def verificar_serializer():
    """Verifica que el serializer tenga los campos correctos"""
    print("\n✓ Verificando serializer DispensacionSerializer...")
    from core.serializers import DispensacionSerializer
    
    campos_esperados = [
        'documento_firmado_url',
        'documento_firmado_nombre',
        'documento_firmado_fecha',
        'documento_firmado_por',
        'documento_firmado_por_nombre',
        'documento_firmado_tamano',
        'tiene_documento_firmado'
    ]
    
    meta_fields = DispensacionSerializer.Meta.fields
    
    for campo in campos_esperados:
        if campo in meta_fields:
            print(f"  ✓ Campo '{campo}' en serializer")
        else:
            print(f"  ✗ Campo '{campo}' NO está en serializer")
            return False
    
    return True

def verificar_viewset():
    """Verifica que los endpoints estén definidos"""
    print("\n✓ Verificando endpoints en DispensacionViewSet...")
    from core.views import DispensacionViewSet
    
    endpoints_requeridos = [
        'subir_documento_firmado',
        'descargar_documento_firmado',
        'eliminar_documento_firmado'
    ]
    
    for endpoint in endpoints_requeridos:
        if hasattr(DispensacionViewSet, endpoint):
            print(f"  ✓ Endpoint '{endpoint}' existe")
        else:
            print(f"  ✗ Endpoint '{endpoint}' NO existe")
            return False
    
    return True

def verificar_storage_service():
    """Verifica que el StorageService tenga el método download_file"""
    print("\n✓ Verificando StorageService...")
    try:
        from inventario.services.storage_service import StorageService
        
        if hasattr(StorageService, 'download_file'):
            print("  ✓ Método 'download_file' existe")
        else:
            print("  ✗ Método 'download_file' NO existe")
            return False
        
        if hasattr(StorageService, 'upload_file'):
            print("  ✓ Método 'upload_file' existe")
        else:
            print("  ✗ Método 'upload_file' NO existe")
            return False
        
        if hasattr(StorageService, 'delete_file'):
            print("  ✓ Método 'delete_file' existe")
        else:
            print("  ✗ Método 'delete_file' NO existe")
            return False
        
        return True
    except ImportError as e:
        print(f"  ✗ Error importando StorageService: {e}")
        return False

def verificar_migracion_db():
    """Verifica que la migración se haya aplicado en la base de datos"""
    print("\n✓ Verificando migración en base de datos...")
    from django.db import connection
    
    try:
        with connection.cursor() as cursor:
            # Verificar que existan las columnas
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'dispensaciones' 
                AND column_name LIKE 'documento_firmado%'
                ORDER BY column_name;
            """)
            
            columnas = [row[0] for row in cursor.fetchall()]
            
            columnas_esperadas = [
                'documento_firmado_fecha',
                'documento_firmado_nombre',
                'documento_firmado_por_id',
                'documento_firmado_tamano',
                'documento_firmado_url'
            ]
            
            if set(columnas_esperadas).issubset(set(columnas)):
                print(f"  ✓ Todas las columnas existen en la BD: {', '.join(columnas)}")
                return True
            else:
                faltantes = set(columnas_esperadas) - set(columnas)
                print(f"  ✗ Faltan columnas en la BD: {', '.join(faltantes)}")
                return False
                
    except Exception as e:
        print(f"  ✗ Error verificando BD: {e}")
        return False

def verificar_supabase_config():
    """Verifica que Supabase esté configurado"""
    print("\n✓ Verificando configuración de Supabase...")
    from django.conf import settings
    
    if hasattr(settings, 'SUPABASE_URL') and settings.SUPABASE_URL:
        print(f"  ✓ SUPABASE_URL configurado")
    else:
        print("  ⚠ SUPABASE_URL no configurado")
    
    if hasattr(settings, 'SUPABASE_KEY') and settings.SUPABASE_KEY:
        print(f"  ✓ SUPABASE_KEY configurado")
    else:
        print("  ⚠ SUPABASE_KEY no configurado")
    
    # Intentar importar el paquete supabase
    try:
        import supabase
        print("  ✓ Paquete 'supabase' instalado")
    except ImportError:
        print("  ⚠ Paquete 'supabase' NO instalado (pip install supabase)")
    
    return True

def main():
    """Ejecuta todas las verificaciones"""
    print("=" * 70)
    print("VERIFICACIÓN: Documentos Firmados en Dispensaciones")
    print("=" * 70)
    
    resultados = []
    
    try:
        resultados.append(("Modelo", verificar_modelo()))
        resultados.append(("Serializer", verificar_serializer()))
        resultados.append(("ViewSet", verificar_viewset()))
        resultados.append(("StorageService", verificar_storage_service()))
        resultados.append(("Migración BD", verificar_migracion_db()))
        resultados.append(("Configuración Supabase", verificar_supabase_config()))
    except Exception as e:
        print(f"\n✗ Error durante la verificación: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Resumen
    print("\n" + "=" * 70)
    print("RESUMEN DE VERIFICACIÓN")
    print("=" * 70)
    
    total = len(resultados)
    exitosos = sum(1 for _, resultado in resultados if resultado)
    
    for nombre, resultado in resultados:
        estado = "✓ PASS" if resultado else "✗ FAIL"
        print(f"{nombre:.<40} {estado}")
    
    print("=" * 70)
    print(f"Total: {exitosos}/{total} verificaciones exitosas")
    
    if exitosos == total:
        print("\n✅ ¡TODAS LAS VERIFICACIONES PASARON!")
        print("\n📝 PRÓXIMOS PASOS:")
        print("   1. Crear bucket 'dispensaciones-firmadas' en Supabase Storage")
        print("   2. Configurar políticas de seguridad RLS")
        print("   3. Hacer deploy a producción")
        print("   4. Probar subir un documento PDF en la interfaz")
        return 0
    else:
        print("\n⚠ ALGUNAS VERIFICACIONES FALLARON")
        print("   Revisa los errores arriba y corrige los problemas.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
