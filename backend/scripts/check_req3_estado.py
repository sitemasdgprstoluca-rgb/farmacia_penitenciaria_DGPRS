"""
Verificar el estado actual de la requisición 3
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Requisicion

req = Requisicion.objects.get(pk=3)
print(f"Estado: {req.estado}")
print(f"Fecha recolección límite: {req.fecha_recoleccion_limite if hasattr(req, 'fecha_recoleccion_limite') else 'Campo no existe'}")
print(f"Fecha autorización: {req.fecha_autorizacion if hasattr(req, 'fecha_autorizacion') else 'N/A'}")
print(f"Fecha autorización farmacia: {req.fecha_autorizacion_farmacia if hasattr(req, 'fecha_autorizacion_farmacia') else 'N/A'}")
