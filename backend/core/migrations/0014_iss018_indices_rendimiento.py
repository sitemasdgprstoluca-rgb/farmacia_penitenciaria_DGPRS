"""
ISS-018: Índices de base de datos optimizados.

Migración para agregar índices que mejoran el rendimiento
de consultas frecuentes.
"""
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    ISS-018: Migración para añadir índices de rendimiento.
    
    Índices añadidos:
    - Requisiciones: estado, centro+estado, fecha
    - Movimientos: tipo, lote+tipo, fecha, centro+fecha
    - Lotes: producto, centro, fecha_caducidad, estado+cantidad
    - Productos: clave, activo, stock_minimo
    """
    
    dependencies = [
        ('core', '0013_tema_global'),
    ]
    
    operations = [
        # =========================================
        # ÍNDICES PARA REQUISICIONES
        # =========================================
        
        # Búsqueda por estado (muy frecuente en listados)
        migrations.AddIndex(
            model_name='requisicion',
            index=models.Index(
                fields=['estado', '-fecha_solicitud'],
                name='idx_req_estado_fecha'
            ),
        ),
        
        # Búsqueda por centro y estado (filtro común)
        migrations.AddIndex(
            model_name='requisicion',
            index=models.Index(
                fields=['centro', 'estado', '-fecha_solicitud'],
                name='idx_req_centro_estado'
            ),
        ),
        
        # Búsqueda por usuario que solicita
        migrations.AddIndex(
            model_name='requisicion',
            index=models.Index(
                fields=['usuario_solicita', '-fecha_solicitud'],
                name='idx_req_usuario_fecha'
            ),
        ),
        
        # =========================================
        # ÍNDICES PARA MOVIMIENTOS
        # =========================================
        
        # Búsqueda por tipo y fecha (reportes)
        migrations.AddIndex(
            model_name='movimiento',
            index=models.Index(
                fields=['tipo', '-fecha'],
                name='idx_mov_tipo_fecha'
            ),
        ),
        
        # Búsqueda por lote (trazabilidad)
        migrations.AddIndex(
            model_name='movimiento',
            index=models.Index(
                fields=['lote', '-fecha'],
                name='idx_mov_lote_fecha'
            ),
        ),
        
        # Búsqueda por requisición (surtido)
        migrations.AddIndex(
            model_name='movimiento',
            index=models.Index(
                fields=['requisicion', '-fecha'],
                name='idx_mov_req_fecha'
            ),
        ),
        
        # Búsqueda por usuario (auditoría)
        migrations.AddIndex(
            model_name='movimiento',
            index=models.Index(
                fields=['usuario', '-fecha'],
                name='idx_mov_usuario_fecha'
            ),
        ),
        
        # =========================================
        # ÍNDICES PARA LOTES
        # =========================================
        
        # Lotes por caducidad (alertas)
        migrations.AddIndex(
            model_name='lote',
            index=models.Index(
                fields=['fecha_caducidad', 'estado'],
                name='idx_lote_caducidad_estado'
            ),
        ),
        
        # Lotes disponibles por producto (búsqueda de stock)
        migrations.AddIndex(
            model_name='lote',
            index=models.Index(
                fields=['producto', 'estado', 'cantidad_actual'],
                name='idx_lote_prod_stock'
            ),
        ),
        
        # Lotes por centro (filtro frecuente)
        migrations.AddIndex(
            model_name='lote',
            index=models.Index(
                fields=['centro', 'estado', '-fecha_caducidad'],
                name='idx_lote_centro_estado'
            ),
        ),
        
        # =========================================
        # ÍNDICES PARA PRODUCTOS
        # =========================================
        
        # Productos activos (filtro común)
        migrations.AddIndex(
            model_name='producto',
            index=models.Index(
                fields=['activo', 'descripcion'],
                name='idx_prod_activo_desc'
            ),
        ),
        
        # Productos bajo stock (alertas)
        migrations.AddIndex(
            model_name='producto',
            index=models.Index(
                fields=['stock_minimo', 'activo'],
                name='idx_prod_stock_min'
            ),
        ),
        
        # =========================================
        # ÍNDICES PARA DETALLES REQUISICIÓN
        # =========================================
        
        # Detalles por producto (reportes)
        migrations.AddIndex(
            model_name='detallerequisicion',
            index=models.Index(
                fields=['producto', 'requisicion'],
                name='idx_det_prod_req'
            ),
        ),
    ]
