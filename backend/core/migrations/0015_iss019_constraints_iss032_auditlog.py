# ISS-019: Constraint de cantidad no negativa
# ISS-032: Modelo AuditLog centralizado

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_iss018_indices_rendimiento'),
    ]

    operations = [
        # ISS-019: Agregar constraint CHECK para cantidad no negativa en Lote
        migrations.AddConstraint(
            model_name='lote',
            constraint=models.CheckConstraint(
                check=models.Q(cantidad_actual__gte=0),
                name='ck_lote_cantidad_no_negativa',
                violation_error_message='La cantidad actual no puede ser negativa'
            ),
        ),
        
        # ISS-019: Agregar constraint CHECK para cantidad_inicial
        migrations.AddConstraint(
            model_name='lote',
            constraint=models.CheckConstraint(
                check=models.Q(cantidad_inicial__gte=1),
                name='ck_lote_cantidad_inicial_positiva',
                violation_error_message='La cantidad inicial debe ser al menos 1'
            ),
        ),
        
        # ISS-019: Constraint para que cantidad_actual no exceda cantidad_inicial
        migrations.AddConstraint(
            model_name='lote',
            constraint=models.CheckConstraint(
                check=models.Q(cantidad_actual__lte=models.F('cantidad_inicial')),
                name='ck_lote_actual_no_excede_inicial',
                violation_error_message='La cantidad actual no puede exceder la cantidad inicial'
            ),
        ),
        
        # ISS-019: Constraint para cantidad en DetalleRequisicion
        migrations.AddConstraint(
            model_name='detallerequisicion',
            constraint=models.CheckConstraint(
                check=models.Q(cantidad_solicitada__gte=1),
                name='ck_detalle_cantidad_solicitada_positiva',
                violation_error_message='La cantidad solicitada debe ser al menos 1'
            ),
        ),
        
        # ISS-032: Crear modelo AuditLog
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(db_index=True)),
                ('action', models.CharField(
                    max_length=50,
                    db_index=True,
                    choices=[
                        ('create', 'Crear'),
                        ('read', 'Leer'),
                        ('update', 'Actualizar'),
                        ('delete', 'Eliminar'),
                        ('soft_delete', 'Eliminar (soft)'),
                        ('restore', 'Restaurar'),
                        ('login', 'Inicio de sesión'),
                        ('logout', 'Cierre de sesión'),
                        ('login_failed', 'Login fallido'),
                        ('password_change', 'Cambio de contraseña'),
                        ('permission_change', 'Cambio de permisos'),
                        ('export', 'Exportación'),
                        ('import', 'Importación'),
                        ('transition', 'Transición de estado'),
                        ('approval', 'Aprobación'),
                        ('rejection', 'Rechazo'),
                        ('transfer', 'Transferencia'),
                        ('adjustment', 'Ajuste'),
                        ('error', 'Error'),
                    ]
                )),
                ('severity', models.CharField(
                    max_length=20,
                    default='info',
                    choices=[
                        ('debug', 'Debug'),
                        ('info', 'Info'),
                        ('warning', 'Warning'),
                        ('error', 'Error'),
                        ('critical', 'Critical'),
                    ]
                )),
                ('usuario_id', models.IntegerField(null=True, blank=True, db_index=True)),
                ('modelo', models.CharField(max_length=100, db_index=True)),
                ('objeto_id', models.IntegerField(null=True, blank=True)),
                ('objeto_repr', models.CharField(max_length=200, blank=True)),
                ('descripcion', models.TextField()),
                ('datos_anteriores', models.JSONField(null=True, blank=True)),
                ('datos_nuevos', models.JSONField(null=True, blank=True)),
                ('ip_address', models.GenericIPAddressField(null=True, blank=True)),
                ('user_agent', models.CharField(max_length=200, blank=True)),
                ('request_id', models.CharField(max_length=100, null=True, blank=True)),
                ('duracion_ms', models.FloatField(null=True, blank=True)),
                ('metadata', models.JSONField(default=dict, blank=True)),
            ],
            options={
                'db_table': 'audit_logs',
                'ordering': ['-timestamp'],
                'indexes': [
                    models.Index(fields=['timestamp', 'action'], name='idx_audit_timestamp_action'),
                    models.Index(fields=['usuario_id', 'timestamp'], name='idx_audit_usuario_timestamp'),
                    models.Index(fields=['modelo', 'objeto_id'], name='idx_audit_modelo_objeto'),
                    models.Index(fields=['severity', 'timestamp'], name='idx_audit_severity'),
                ],
            },
        ),
    ]
