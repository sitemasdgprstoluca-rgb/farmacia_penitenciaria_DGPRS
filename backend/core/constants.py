"""
Constantes del sistema de Farmacia Penitenciaria
Centraliza valores mágicos y configuraciones

ISS-001/002/003 FIX (audit8): FUENTE ÚNICA DE VERDAD para estados y transiciones.
Todos los módulos (models.py, requisicion_service.py, state_machine.py) deben
importar estas constantes en lugar de definir sus propias copias.
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

# Categorías de productos válidas
CATEGORIAS_PRODUCTO = [
    ('medicamento', 'Medicamento'),
    ('material_curacion', 'Material de Curación'),
    ('insumo', 'Insumo'),
    ('equipo', 'Equipo'),
    ('otro', 'Otro'),
]

# Lista simple para validaciones
CATEGORIAS_VALIDAS = [c[0] for c in CATEGORIAS_PRODUCTO]

# Estados de lote
ESTADOS_LOTE = [
    ('disponible', 'Disponible'),
    ('agotado', 'Agotado'),
    ('vencido', 'Vencido'),
    ('bloqueado', 'Bloqueado'),
    ('retirado', 'Retirado'),
]

# ISS-001 FIX (audit11): Estados de lote que pueden contarse como stock disponible
# SOLO 'disponible' cuenta para cálculos de inventario surtible
# Lotes bloqueados, retirados, vencidos o agotados NO deben incluirse
ESTADOS_LOTE_DISPONIBLES = {'disponible'}
ESTADOS_LOTE_NO_DISPONIBLES = {'agotado', 'vencido', 'bloqueado', 'retirado'}

# Estados de requisición
# ISS-DB-002: Alineado con CHECK constraint de BD Supabase
# FLUJO V2: Estados jerárquicos con trazabilidad completa
ESTADOS_REQUISICION = [
    # Estados del flujo del centro
    ('borrador', 'Borrador'),                    # Médico creando la solicitud
    ('pendiente_admin', 'Pendiente Administrador'),  # Esperando autorización del Administrador del Centro
    ('pendiente_director', 'Pendiente Director'),    # Esperando autorización del Director del Centro
    
    # Estados del flujo de farmacia
    ('enviada', 'Enviada'),                      # Enviada a Farmacia Central
    ('en_revision', 'En Revisión'),              # Farmacia está revisando
    ('autorizada', 'Autorizada'),                # Farmacia autorizó y asignó fecha de recolección
    ('en_surtido', 'En Surtido'),                # En proceso de preparación
    ('surtida', 'Surtida'),                      # Lista para recolección
    ('entregada', 'Entregada'),                  # Entregada y confirmada
    
    # Estados finales negativos
    ('rechazada', 'Rechazada'),                  # Rechazada en cualquier punto del flujo
    ('vencida', 'Vencida'),                      # No se recolectó en la fecha límite
    ('cancelada', 'Cancelada'),                  # Cancelada por el solicitante
    ('devuelta', 'Devuelta'),                    # Devuelta al centro para corrección
    
    # Compatibilidad legacy
    ('parcial', 'Parcialmente Surtida'),         # Deprecated: usar en_surtido
]

# Grupos lógicos de estados de requisición para filtros y resúmenes
# FLUJO V2: Grupos actualizados con estados jerárquicos
REQUISICION_GRUPOS_ESTADO = {
    # Estados donde el Centro debe actuar
    'pendientes_centro': ['borrador', 'devuelta'],
    'pendientes_admin': ['pendiente_admin'],
    'pendientes_director': ['pendiente_director'],
    
    # Estados donde Farmacia debe actuar
    'pendientes_farmacia': ['enviada', 'en_revision'],
    'en_proceso': ['autorizada', 'en_surtido'],
    
    # Estados de espera
    'esperando_recoleccion': ['surtida'],
    
    # Estados finales positivos
    'completadas': ['entregada'],
    
    # Estados finales negativos
    'finalizadas_negativas': ['rechazada', 'cancelada', 'vencida'],
    
    # Compatibilidad legacy
    'pendientes': ['borrador', 'enviada', 'pendiente_admin', 'pendiente_director'],
    'surtidas': ['surtida'],
    'entregadas': ['entregada'],
    'rechazadas_canceladas': ['rechazada', 'cancelada', 'vencida'],
}

# Transiciones de estado válidas (para validación en backend)
# FLUJO V2: Definición de transiciones permitidas
# ISS-001 FIX (audit4): autorizada → en_surtido OBLIGATORIO (no saltar a surtida)
# ISS-002 FIX (audit4): cancelada con validación de movimientos pendientes
TRANSICIONES_REQUISICION = {
    'borrador': ['pendiente_admin', 'cancelada'],
    'pendiente_admin': ['pendiente_director', 'rechazada', 'devuelta', 'cancelada'],
    'pendiente_director': ['enviada', 'rechazada', 'devuelta', 'cancelada'],
    'enviada': ['en_revision', 'rechazada', 'cancelada'],  # ISS-001: Quitar autorizada directa
    'en_revision': ['autorizada', 'rechazada', 'devuelta', 'cancelada'],
    # ISS-001 FIX: autorizada SOLO puede ir a en_surtido, NO a surtida directamente
    'autorizada': ['en_surtido', 'cancelada'],
    'en_surtido': ['surtida', 'parcial', 'cancelada'],
    'parcial': ['en_surtido', 'surtida', 'cancelada'],
    # ISS-002 FIX: surtida NO puede cancelarse (ya hay movimientos de inventario)
    'surtida': ['entregada', 'vencida'],
    # Devolución: regresa a borrador para que médico corrija y reinicie ciclo completo
    'devuelta': ['borrador', 'cancelada'],
    # Estados finales - no pueden cambiar
    'entregada': [],
    'rechazada': [],
    'vencida': [],
    'cancelada': [],
}

# ISS-002 FIX (audit4): Estados que NO permiten cancelación por tener movimientos
ESTADOS_SIN_CANCELACION = ['surtida', 'entregada', 'parcial']

# ISS-001/002/003 FIX (audit8): Estados surtibles - FUENTE ÚNICA
# Solo estos estados permiten iniciar/continuar proceso de surtido
ESTADOS_SURTIBLES = ['autorizada', 'en_surtido']

# ISS-001/002/003 FIX (audit8): Estados terminales - FUENTE ÚNICA
# Estados que NO permiten ninguna transición posterior
ESTADOS_TERMINALES = ['entregada', 'rechazada', 'vencida', 'cancelada']

# ISS-001/002/003 FIX (audit8): Estados que requieren servicio transaccional
# Cambios a estos estados DEBEN pasar por RequisicionService, no modelo directo
ESTADOS_REQUIEREN_SERVICIO = ['en_surtido', 'surtida', 'parcial', 'entregada']

# ISS-003 FIX (audit4): Segregación de funciones - roles incompatibles
# Un usuario NO puede ejecutar dos acciones del mismo par en la misma requisición
SEGREGACION_FUNCIONES = {
    # (accion1, accion2): No pueden ser ejecutadas por el mismo usuario
    ('crear', 'autorizar_admin'): True,
    ('crear', 'autorizar_director'): True,
    ('crear', 'autorizar_farmacia'): True,
    ('autorizar_admin', 'autorizar_director'): True,
    ('autorizar_farmacia', 'surtir'): True,
}

# ISS-004 FIX (audit4): Estados que permiten edición completa
ESTADOS_EDITABLES = ['borrador', 'devuelta']

# ISS-001/002/003 FIX (audit8): Estados con edición limitada (solo notas/observaciones)
ESTADOS_EDICION_LIMITADA = ['pendiente_admin', 'pendiente_director', 'enviada', 'en_revision']

# ISS-001/002/003 FIX (audit8): Estados sin ninguna edición
ESTADOS_SIN_EDICION = ['autorizada', 'en_surtido', 'surtida', 'entregada', 
                       'rechazada', 'vencida', 'cancelada', 'parcial']

# ISS-004 FIX (audit4): Estados que requieren revalidación si se editan
ESTADOS_REVALIDAR_SI_EDITA = ['pendiente_admin', 'pendiente_director']

# ISS-001/002/003 FIX (audit8): Roles por transición - FUENTE ÚNICA
ROLES_POR_TRANSICION = {
    # Creación y envío - roles de centro
    ('borrador', 'pendiente_admin'): ['medico', 'centro', 'usuario_centro'],
    ('pendiente_admin', 'pendiente_director'): ['administrador_centro'],
    ('pendiente_director', 'enviada'): ['director_centro'],
    
    # Revisión y autorización - roles de farmacia
    ('enviada', 'en_revision'): ['farmacia', 'farmaceutico', 'admin_farmacia'],
    ('en_revision', 'autorizada'): ['farmacia', 'farmaceutico', 'admin_farmacia'],
    ('en_revision', 'rechazada'): ['farmacia', 'farmaceutico', 'admin_farmacia'],
    ('en_revision', 'devuelta'): ['farmacia', 'farmaceutico', 'admin_farmacia'],
    
    # Surtido - solo farmacia
    ('autorizada', 'en_surtido'): ['farmacia', 'farmaceutico', 'admin_farmacia'],
    ('en_surtido', 'surtida'): ['farmacia', 'farmaceutico', 'admin_farmacia'],
    ('en_surtido', 'parcial'): ['farmacia', 'farmaceutico', 'admin_farmacia'],
    
    # Recepción - solo centro destino
    ('surtida', 'entregada'): ['centro', 'usuario_centro', 'administrador_centro', 'director_centro', 'medico'],
    
    # Devolución - regresa a borrador
    ('devuelta', 'borrador'): ['medico', 'centro', 'usuario_centro'],
    
    # Cancelaciones - depende del estado
    ('borrador', 'cancelada'): ['medico', 'centro', 'usuario_centro', 'administrador_centro'],
    ('pendiente_admin', 'cancelada'): ['administrador_centro', 'director_centro'],
    ('pendiente_director', 'cancelada'): ['director_centro'],
    ('enviada', 'cancelada'): ['farmacia', 'admin_farmacia'],
    ('en_revision', 'cancelada'): ['farmacia', 'admin_farmacia'],
    ('autorizada', 'cancelada'): ['farmacia', 'admin_farmacia'],
    ('en_surtido', 'cancelada'): ['farmacia', 'admin_farmacia'],
    ('devuelta', 'cancelada'): ['medico', 'administrador_centro'],
    
    # Rechazos
    ('pendiente_admin', 'rechazada'): ['administrador_centro'],
    ('pendiente_director', 'rechazada'): ['director_centro'],
    ('enviada', 'rechazada'): ['farmacia', 'admin_farmacia'],
    
    # Devoluciones internas
    ('pendiente_admin', 'devuelta'): ['administrador_centro'],
    ('pendiente_director', 'devuelta'): ['director_centro'],
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
# NOTA: 'donacion' NO está aquí porque donaciones funciona como almacén SEPARADO
#       y no afecta el inventario principal ni genera movimientos auditados
TIPOS_MOVIMIENTO = [
    ('entrada', 'Entrada'),
    ('salida', 'Salida'),
    ('transferencia', 'Transferencia'),
    ('ajuste_positivo', 'Ajuste Positivo'),
    ('ajuste_negativo', 'Ajuste Negativo'),
    ('devolucion', 'Devolucion'),
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
# FLUJO V2: Roles específicos del centro para flujo jerárquico
ROLES_USUARIO = [
    # Roles de Farmacia Central
    ('admin', 'Administrador del Sistema'),       # Acceso total
    ('farmacia', 'Personal de Farmacia'),         # Recibe, autoriza, surte
    ('vista', 'Usuario Vista/Consultor'),         # Solo consulta
    
    # Roles de Centro Penitenciario (FLUJO V2)
    ('medico', 'Médico del Centro'),                    # Crea requisiciones
    ('administrador_centro', 'Administrador del Centro'), # Primera autorización
    ('director_centro', 'Director del Centro'),          # Segunda autorización
    ('centro', 'Usuario Centro (consulta)'),            # Solo consulta en centro
    
    # Compatibilidad con valores previos
    ('admin_sistema', 'Administrador del sistema (legacy)'),
    ('superusuario', 'Superusuario (legacy)'),
    ('admin_farmacia', 'Admin Farmacia (legacy)'),
    ('usuario_normal', 'Usuario Centro (legacy)'),
    ('usuario_vista', 'Usuario Vista (legacy)'),
]

# Mapeo de permisos del flujo por rol
# FLUJO V2: Qué puede hacer cada rol en el flujo de requisiciones
PERMISOS_FLUJO_REQUISICION = {
    'medico': {
        'puede_crear': True,
        'puede_enviar_admin': True,
        'puede_autorizar_admin': False,
        'puede_autorizar_director': False,
        'puede_recibir_farmacia': False,
        'puede_autorizar_farmacia': False,
        'puede_surtir': False,
        'puede_confirmar_entrega': True,
    },
    'administrador_centro': {
        'puede_crear': False,
        'puede_enviar_admin': False,
        'puede_autorizar_admin': True,
        'puede_autorizar_director': False,
        'puede_recibir_farmacia': False,
        'puede_autorizar_farmacia': False,
        'puede_surtir': False,
        'puede_confirmar_entrega': True,
    },
    'director_centro': {
        'puede_crear': False,
        'puede_enviar_admin': False,
        'puede_autorizar_admin': False,
        'puede_autorizar_director': True,
        'puede_recibir_farmacia': False,
        'puede_autorizar_farmacia': False,
        'puede_surtir': False,
        'puede_confirmar_entrega': True,
    },
    'farmacia': {
        'puede_crear': False,
        'puede_enviar_admin': False,
        'puede_autorizar_admin': False,
        'puede_autorizar_director': False,
        'puede_recibir_farmacia': True,
        'puede_autorizar_farmacia': True,
        # ISS-003 FIX: Farmacia autoriza O surte, pero NO ambos en misma requisición
        'puede_surtir': True,
        'puede_confirmar_entrega': False,
        # ISS-003 FIX (audit4): Segregación de funciones
        'segregacion_autorizar_surtir': True,  # Si autorizó, no puede surtir
    },
    'admin': {
        # ISS-003 FIX (audit4): Admin tiene capacidades pero con segregación
        'puede_crear': True,
        'puede_enviar_admin': True,
        'puede_autorizar_admin': True,
        'puede_autorizar_director': True,
        'puede_recibir_farmacia': True,
        'puede_autorizar_farmacia': True,
        'puede_surtir': True,
        'puede_confirmar_entrega': True,
        # ISS-003 FIX: Segregación incluso para admin
        'segregacion_autorizar_surtir': True,
        'segregacion_crear_autorizar': True,
    },
}

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
