#!/usr/bin/env python
"""Listar usuarios disponibles."""
import sqlite3

DB = 'db.sqlite3'
conn = sqlite3.connect(DB)
cursor = conn.cursor()

cursor.execute("""
    SELECT id, username, email, is_superuser, is_staff, is_active 
    FROM usuarios 
    ORDER BY is_superuser DESC, username
""")

print("Usuarios en la base de datos:")
print("-" * 80)
print(f"{'ID':<5} {'Usuario':<20} {'Email':<30} {'Super':<7} {'Staff':<7} {'Activo'}")
print("-" * 80)

for row in cursor.fetchall():
    user_id, username, email, is_super, is_staff, is_active = row
    print(f"{user_id:<5} {username:<20} {email:<30} {'Sí' if is_super else 'No':<7} {'Sí' if is_staff else 'No':<7} {'Sí' if is_active else 'No'}")

print("-" * 80)
print(f"\nTotal usuarios: {cursor.rowcount}")

conn.close()
