#!/usr/bin/env python
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.db import connection

cursor = connection.cursor()
cursor.execute("""
    SELECT pg_get_constraintdef(oid) 
    FROM pg_constraint 
    WHERE conname = 'valid_rol'
""")
result = cursor.fetchone()
print("Constraint actual en Supabase:")
print(result[0] if result else "No encontrado")
