"""
Constantes del sistema de Farmacia Penitenciaria
Centraliza valores mágicos y configuraciones
"""

# Unidades de medida disponibles
UNIDADES_MEDIDA = [
    ('PIEZA', 'Pieza'),
    ('CAJA', 'Caja'),
    ('FRASCO', 'Frasco'),
    ('SOBRE', 'Sobre'),
    ('AMPOLLETA', 'Ampolleta'),
    ('TABLETA', 'Tableta'),
    ('CAPSULA', 'Cápsula'),
    ('ML', 'Mililitro'),
    ('GR', 'Gramo'),
]

# Estados de lote
ESTADOS_LOTE = [
    ('disponible', 'Disponible'),
    ('agotado', 'Agotado'),
    ('vencido', 'Vencido'),
    ('bloqueado', 'Bloqueado'),
    ('retirado', 'Retirado'),
]

# Estados de requisición
# ISS-DB-002: Alineado con CHECK constraint de BD Supabase
# BD permite: borrador, enviada, autorizada, rechazada, en_surtido, surtida, parcial, cancelada, entregada
ESTADOS_REQUISICION = [
    ('borrador', 'Borrador'),
    ('enviada', 'Enviada'),              # Requisición enviada para autorización
    ('autorizada', 'Autorizada'),        # Completamente autorizada
    ('rechazada', 'Rechazada'),
    ('en_surtido', 'En Surtido'),        # En proceso de surtido
    ('surtida', 'Surtida'),              # Completamente surtida
    ('parcial', 'Parcialmente Surtida'), # Surtida parcialmente
    ('entregada', 'Entregada'),          # Entregada al centro
    ('cancelada', 'Cancelada'),
]

# Grupos lógicos de estados de requisición para filtros y resúmenes
# ISS-DB-002: Alineado con BD Supabase
REQUISICION_GRUPOS_ESTADO = {
    'pendientes': ['borrador', 'enviada'],
    'en_proceso': ['autorizada', 'en_surtido', 'parcial'],
    'surtidas': ['surtida'],
    'entregadas': ['entregada'],
    'rechazadas_canceladas': ['rechazada', 'cancelada'],
}

# Permisos extra (asignados vía grupos) que pueden complementar al rol base
EXTRA_PERMISSIONS = [
    'CAN_VIEW_GLOBAL_REPORTS',
    'CAN_MANAGE_CENTROS',
    'CAN_MANAGE_USERS',
    'CAN_VIEW_ALL_REQUISICIONES',
    'VER_NOTIFICACIONES',
    'VER_PERFIL',
]

# Tipos de movimiento
# ISS-DB-001: Alineado con CHECK constraint valid_tipo_movimiento de BD Supabase
# BD permite: entrada, salida, transferencia, ajuste_positivo, ajuste_negativo, devolucion, merma, caducidad
TIPOS_MOVIMIENTO = [
    ('entrada', 'Entrada'),
    ('salida', 'Salida'),
    ('transferencia', 'Transferencia'),
    ('ajuste_positivo', 'Ajuste Positivo'),
    ('ajuste_negativo', 'Ajuste Negativo'),
    ('devolucion', 'Devolución'),
    ('merma', 'Merma'),
    ('caducidad', 'Caducidad'),
]

# Helper: Mapeo de tipo genérico a tipo BD según signo de cantidad
def get_tipo_ajuste_bd(cantidad):
    """Devuelve 'ajuste_positivo' o 'ajuste_negativo' según el signo de la cantidad."""
    return 'ajuste_positivo' if cantidad > 0 else 'ajuste_negativo'

# Tipos que restan stock (para validaciones)
TIPOS_RESTA_STOCK = ['salida', 'ajuste_negativo', 'merma', 'caducidad']
TIPOS_SUMA_STOCK = ['entrada', 'ajuste_positivo', 'devolucion']

# Roles de usuario
ROLES_USUARIO = [
    ('admin_sistema', 'Administrador del sistema'),
    ('farmacia', 'Usuario Farmacia'),
    ('centro', 'Usuario Centro/Unidad'),
    ('vista', 'Usuario Vista/Consultor'),
    # Compatibilidad con valores previos
    ('superusuario', 'Superusuario (legacy)'),
    ('admin_farmacia', 'Admin Farmacia (legacy)'),
    ('usuario_normal', 'Usuario Centro (legacy)'),
    ('usuario_vista', 'Usuario Vista (legacy)'),
]

# Niveles de stock
NIVELES_STOCK = {
    'critico': 0.25,  # 0-25% del mínimo
    'bajo': 0.75,     # 25-75% del mínimo
    'normal': 1.5,    # 75-150% del mínimo
    'alto': float('inf')  # >150% del mínimo
}

# Configuración de paginación
PAGINATION_DEFAULT_PAGE_SIZE = 25
PAGINATION_MAX_PAGE_SIZE = 100

# Configuración de importación
IMPORT_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
IMPORT_ALLOWED_EXTENSIONS = ['.xlsx', '.xls']
IMPORT_MAX_ROWS = 10000

# Configuración de exportación
EXPORT_FORMATS = ['excel', 'csv', 'pdf']
EXPORT_MAX_ROWS = 50000

# Días para considerar medicamento por caducar
DIAS_ALERTA_CADUCIDAD = 90

# Validaciones de producto
PRODUCTO_CLAVE_MIN_LENGTH = 2
PRODUCTO_CLAVE_MAX_LENGTH = 50
PRODUCTO_DESCRIPCION_MIN_LENGTH = 5
PRODUCTO_DESCRIPCION_MAX_LENGTH = 300
PRODUCTO_PRECIO_MAX_DIGITS = 10
PRODUCTO_PRECIO_DECIMAL_PLACES = 2

# Validaciones de lote
LOTE_NUMERO_MIN_LENGTH = 2
LOTE_NUMERO_MAX_LENGTH = 100

# ============================================================================
# CATÁLOGO DE ACCIONES DE AUDITORÍA (normalizadas)
# ============================================================================
ACCIONES_AUDITORIA = [
    # Acciones CRUD genéricas
    ('crear', 'Crear'),
    ('actualizar', 'Actualizar'),
    ('eliminar', 'Eliminar'),
    
    # Acciones de Requisiciones (ISS-DB-002: nombres alineados con BD)
    ('cambiar_estado_pendiente', 'Enviar requisición'),
    ('cambiar_estado_autorizada', 'Autorizar requisición'),
    ('cambiar_estado_en_proceso', 'Requisición en proceso'),
    ('cambiar_estado_rechazada', 'Rechazar requisición'),
    ('cambiar_estado_surtida', 'Surtir requisición'),
    ('cambiar_estado_entregada', 'Entregar requisición'),
    ('cambiar_estado_cancelada', 'Cancelar requisición'),
    
    # Acciones de Movimientos
    ('movimiento_entrada', 'Entrada de inventario'),
    ('movimiento_salida', 'Salida de inventario'),
    ('movimiento_ajuste', 'Ajuste de inventario'),
    ('movimiento_requisicion', 'Movimiento por requisición'),
    
    # Acciones de Usuarios y Perfil
    ('cambiar_password', 'Cambiar contraseña'),
    ('cambiar_password_fallido', 'Intento fallido de cambio de contraseña'),
    ('actualizar_perfil', 'Actualizar perfil'),
    ('importar_usuarios', 'Importar usuarios'),
    
    # Acciones de Lotes
    ('ajustar_stock', 'Ajustar stock de lote'),
    ('marcar_vencido', 'Marcar lote como vencido'),
    
    # Acciones de Sistema
    ('login', 'Inicio de sesión'),
    ('logout', 'Cierre de sesión'),
    ('exportar', 'Exportar datos'),
    ('importar', 'Importar datos'),
]

# Modelos auditados
MODELOS_AUDITADOS = [
    'Producto',
    'Lote',
    'Movimiento',
    'Requisicion',
    'Centro',
    'Usuario',
]
