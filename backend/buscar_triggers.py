#!/usr/bin/env python
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection
with connection.cursor() as c:
    c.execute("SELECT trigger_name FROM information_schema.triggers WHERE event_object_table='requisiciones'")
    print("Triggers encontrados:")
    for r in c.fetchall():
        print(f"  - {r[0]}")
