#!/usr/bin/env python
import os
import sys
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

print("=" * 60)
print("🚀 INICIANDO SISTEMA DE FARMACIA")
print("=" * 60)

# 1. Verificar si existe db.sqlite3
db_path = BASE_DIR / 'db.sqlite3'

if not db_path.exists():
    print("\n⚠️  Base de datos no encontrada")
    print("💡 Ejecutando fix_migrations.py...")
    result = subprocess.run([sys.executable, 'fix_migrations.py'])
    if result.returncode != 0:
        print("\n❌ Error al inicializar, saliendo...")
        sys.exit(1)
else:
    print(f"\n✅ Base de datos encontrada: {db_path}")
    
    # Verificar si tiene tablas
    import sqlite3
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table';")
        table_count = cursor.fetchone()[0]
        conn.close()
        
        if table_count < 5:
            print(f"⚠️  Base de datos con solo {table_count} tablas")
            print("💡 Ejecutando fix_migrations.py...")
            result = subprocess.run([sys.executable, 'fix_migrations.py'])
            if result.returncode != 0:
                print("\n❌ Error al inicializar, saliendo...")
                sys.exit(1)
        else:
            print(f"✅ Base de datos operativa con {table_count} tablas")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Ejecutando fix_migrations.py...")
        subprocess.run([sys.executable, 'fix_migrations.py'])

# 2. Iniciar servidor
print("\n" + "=" * 60)
print("🌐 INICIANDO SERVIDOR EN http://localhost:8000")
print("=" * 60)
print("\n🔑 Credenciales por defecto:")
print("   Usuario: admin")
print("   Password: admin123")
print("\n" + "=" * 60)

subprocess.run([sys.executable, 'manage.py', 'runserver', '8000'])
