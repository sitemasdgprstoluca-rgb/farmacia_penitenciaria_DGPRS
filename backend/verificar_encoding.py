#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para verificar y corregir encoding de archivos críticos
"""
import os
import sys

def verificar_y_corregir_encoding(archivo):
    """Verifica y corrige el encoding de un archivo a UTF-8"""
    print(f"\n{'='*60}")
    print(f"Analizando: {archivo}")
    print('='*60)
    
    if not os.path.exists(archivo):
        print(f"❌ Archivo no encontrado: {archivo}")
        return False
    
    try:
        # Intentar leer como UTF-8
        with open(archivo, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        # Verificar si hay caracteres problemáticos
        problemas = []
        for i, linea in enumerate(contenido.split('\n'), 1):
            if '�' in linea or '\ufffd' in linea:
                problemas.append(f"  Línea {i}: {linea[:80]}")
        
        if problemas:
            print(f"⚠️  Encontrados {len(problemas)} problemas de encoding:")
            for p in problemas[:5]:  # Mostrar máximo 5
                print(p)
        else:
            print("✅ Encoding UTF-8 correcto, sin caracteres corruptos")
        
        # Estadísticas
        lineas = contenido.count('\n') + 1
        bytes_total = os.path.getsize(archivo)
        print(f"\n📊 Estadísticas:")
        print(f"  - Líneas: {lineas}")
        print(f"  - Tamaño: {bytes_total:,} bytes")
        print(f"  - Caracteres: {len(contenido):,}")
        
        return len(problemas) == 0
        
    except UnicodeDecodeError as e:
        print(f"❌ Error de decodificación UTF-8: {e}")
        print("   Intentando otros encodings...")
        
        # Intentar otros encodings comunes
        for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
            try:
                with open(archivo, 'r', encoding=encoding) as f:
                    contenido = f.read()
                print(f"✅ Archivo legible con {encoding}")
                
                # Reescribir como UTF-8
                backup = archivo + '.backup'
                os.rename(archivo, backup)
                
                with open(archivo, 'w', encoding='utf-8') as f:
                    f.write(contenido)
                
                print(f"✅ Convertido a UTF-8 (backup: {backup})")
                return True
            except:
                continue
        
        print("❌ No se pudo decodificar con ningún encoding conocido")
        return False
    
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False


def main():
    """Verificar archivos críticos del proyecto"""
    archivos_criticos = [
        'core/views.py',
        'PERMISOS.md',
        'core/utils/permission_helpers.py',
        'core/models.py',
        'core/serializers.py',
    ]
    
    print("🔍 VERIFICACIÓN DE ENCODING - FARMACIA PENITENCIARIA")
    print(f"Python: {sys.version}")
    print(f"Default encoding: {sys.getdefaultencoding()}")
    
    resultados = {}
    for archivo in archivos_criticos:
        if os.path.exists(archivo):
            resultados[archivo] = verificar_y_corregir_encoding(archivo)
        else:
            print(f"\n⚠️  Archivo no encontrado: {archivo}")
            resultados[archivo] = None
    
    # Resumen
    print(f"\n{'='*60}")
    print("📋 RESUMEN")
    print('='*60)
    
    for archivo, resultado in resultados.items():
        if resultado is True:
            estado = "✅ OK"
        elif resultado is False:
            estado = "❌ ERROR"
        else:
            estado = "⚠️  NO ENCONTRADO"
        print(f"{estado} - {archivo}")
    
    # Verificar migraciones
    print(f"\n{'='*60}")
    print("🗄️  VERIFICANDO MIGRACIONES")
    print('='*60)
    
    if os.path.exists('core/migrations'):
        migraciones = sorted([f for f in os.listdir('core/migrations') if f.endswith('.py') and f != '__init__.py'])
        print(f"Encontradas {len(migraciones)} migraciones:")
        for m in migraciones:
            print(f"  ✓ {m}")
    
    # Verificar tests
    print(f"\n{'='*60}")
    print("🧪 VERIFICANDO TESTS")
    print('='*60)
    
    if os.path.exists('core/tests'):
        tests = sorted([f for f in os.listdir('core/tests') if f.startswith('test_') and f.endswith('.py')])
        print(f"Encontrados {len(tests)} archivos de test:")
        for t in tests:
            print(f"  ✓ {t}")
    
    print(f"\n{'='*60}")
    print("✅ Verificación completada")
    print('='*60)


if __name__ == '__main__':
    main()
