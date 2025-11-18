# Importar todos los modelos desde core
from core.models import (
    User, Centro, Producto, Lote, Movimiento, 
    Requisicion, DetalleRequisicion, AuditoriaLog, ImportacionLog
)

__all__ = [
    'User', 'Centro', 'Producto', 'Lote', 'Movimiento',
    'Requisicion', 'DetalleRequisicion', 'AuditoriaLog', 'ImportacionLog'
]
