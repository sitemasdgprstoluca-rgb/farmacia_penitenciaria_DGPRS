#!/usr/bin/env python
"""Script para verificar y reparar la base de datos."""
import sqlite3
import os

DB_PATH = 'db.sqlite3'

def check_tables():
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] No existe {DB_PATH}")
        return False
    
    conn = sqlite3.connect(DB_PATH, timeout=10)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cursor.fetchall()]
    
    print(f"Tablas encontradas ({len(tables)}):")
    for t in sorted(tables):
        print(f"  - {t}")
    
    # Verificar tabla principal
    if 'core_user' in tables:
        cursor.execute("SELECT COUNT(*) FROM core_user")
        count = cursor.fetchone()[0]
        print(f"\n[OK] core_user existe con {count} usuarios")
    else:
        print("\n[ERROR] core_user NO existe!")
    
    # Verificar migraciones
    if 'django_migrations' in tables:
        cursor.execute("SELECT app, name FROM django_migrations ORDER BY id")
        migs = cursor.fetchall()
        print(f"\nMigraciones registradas ({len(migs)}):")
        for app, name in migs:
            print(f"  [{app}] {name}")
    
    conn.close()
    return 'core_user' in tables

if __name__ == '__main__':
    check_tables()
