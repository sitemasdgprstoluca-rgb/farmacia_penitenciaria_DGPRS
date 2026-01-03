# Generated manually - Fix notificaciones table to match Supabase schema

from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Añade campos faltantes al modelo Notificacion para que coincida con
    la tabla real en Supabase. Esta migración es necesaria para que los
    tests unitarios funcionen correctamente.
    
    Campos añadidos:
    - datos: JSONField para datos adicionales (requisicion_id, etc.)
    - url: CharField para enlaces a recursos relacionados
    - created_at: DateTimeField (reemplaza fecha_creacion)
    
    También:
    - Renombra fecha_creacion -> created_at para consistencia con el modelo
    - Elimina índices que usan fecha_creacion (se recrearán con created_at)
    - Elimina campo requisicion (el modelo actual no lo tiene)
    """

    dependencies = [
        ('core', '0024_fix_admin_permissions'),
    ]

    operations = [
        # Primero eliminar los índices existentes que usan fecha_creacion
        migrations.RemoveIndex(
            model_name='notificacion',
            name='idx_notif_user_read',
        ),
        migrations.RemoveIndex(
            model_name='notificacion',
            name='idx_notif_user_date',
        ),
        # Añadir campo 'datos' (JSONField)
        migrations.AddField(
            model_name='notificacion',
            name='datos',
            field=models.JSONField(blank=True, null=True),
        ),
        # Añadir campo 'url' 
        migrations.AddField(
            model_name='notificacion',
            name='url',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        # Renombrar fecha_creacion -> created_at para consistencia
        migrations.RenameField(
            model_name='notificacion',
            old_name='fecha_creacion',
            new_name='created_at',
        ),
        # Eliminar campo requisicion (el modelo actual no lo tiene)
        migrations.RemoveField(
            model_name='notificacion',
            name='requisicion',
        ),
        # Recrear índices con el nuevo nombre de campo
        migrations.AddIndex(
            model_name='notificacion',
            index=models.Index(fields=['usuario', 'leida', '-created_at'], name='idx_notif_user_read'),
        ),
        migrations.AddIndex(
            model_name='notificacion',
            index=models.Index(fields=['usuario', '-created_at'], name='idx_notif_user_date'),
        ),
    ]

