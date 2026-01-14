# Generated manually to sync Producto model with existing migrations
# This migration is now a NO-OP since all fields already exist in the database
# The fields were added in previous migrations or directly in production

from django.db import migrations


class Migration(migrations.Migration):
    """
    Migration that does nothing - all Producto fields already exist.
    Previous migrations (0020_producto_imagen_requisicion_firmas and others) 
    already added these fields. This migration exists only to maintain
    migration history consistency.
    """

    dependencies = [
        ('core', '0025_fix_notificacion_fields'),
    ]

    operations = [
        # No operations needed - all fields already exist in database
        # Fields like 'imagen', 'nombre', 'categoria', etc. were added
        # in migrations 0002, 0020, and others
    ]
