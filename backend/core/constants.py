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

# ISS-024 FIX (audit9): Lista de códigos válidos para validación rápida
UNIDADES_VALIDAS = {u[0] for u in UNIDADES_MEDIDA}

# ISS-024 FIX (audit9): Mapeo de alias comunes a valores normalizados
UNIDADES_ALIAS = {
    # Variaciones de texto libre a normalizar
    'pza': 'PIEZA',
    'pz': 'PIEZA',
    'pieza': 'PIEZA',
    'piezas': 'PIEZA',
    'caja': 'CAJA',
    'cajas': 'CAJA',
    'cj': 'CAJA',
    'frasco': 'FRASCO',
    'fco': 'FRASCO',
    'frascos': 'FRASCO',
    'sobre': 'SOBRE',
    'sobres': 'SOBRE',
    'sob': 'SOBRE',
    'ampolleta': 'AMPOLLETA',
    'amp': 'AMPOLLETA',
    'ampolletas': 'AMPOLLETA',
    'tableta': 'TABLETA',
    'tab': 'TABLETA',
    'tabl': 'TABLETA',
    'tabletas': 'TABLETA',
    'capsula': 'CAPSULA',
    'cap': 'CAPSULA',
    'caps': 'CAPSULA',
    'capsulas': 'CAPSULA',
    'ml': 'ML',
    'mililitro': 'ML',
    'mililitros': 'ML',
    'gr': 'GR',
    'g': 'GR',
    'gramo': 'GR',
    'gramos': 'GR',
}


class UnidadMedidaDesconocidaError(Exception):
    """
    ISS-AUDIT-004 FIX: Excepción para unidades de medida no reconocidas.
    
    Se lanza cuando normalizar_unidad_medida() encuentra una unidad que no puede mapear
    y strict=True. Esto permite detectar datos incorrectos durante importaciones
    en lugar de silenciosamente convertir todo a 'PIEZA'.
    """
    def __init__(self, valor_original, mensaje=None):
        self.valor_original = valor_original
        self.mensaje = mensaje or f"Unidad de medida no reconocida: '{valor_original}'"
        super().__init__(self.mensaje)


def normalizar_unidad_medida(valor, strict=False, log_warnings=True):
    """
    ISS-024 FIX (audit9): Normaliza una unidad de medida al código estándar.
    ISS-AUDIT-004 FIX: Modo strict para evitar conversión silenciosa a PIEZA.
    
    Maneja textos compuestos como:
    - "CAJA CON 7 OVULOS" -> "CAJA"
    - "FRASCO 120ML" -> "FRASCO"
    - "EN CAJA CON 20 GRAGEAS" -> "CAJA"
    - "GOTERO CON 15 MILILITROS" -> "FRASCO"
    - "BOLSA FLEX-OVAL, DE 500 MILILITROS" -> "PIEZA"
    - "ENVASE CON 120 MILILITROS" -> "FRASCO"
    
    Args:
        valor: Valor de unidad (puede ser código, nombre o alias)
        strict: Si True, lanza UnidadMedidaDesconocidaError en lugar de default a PIEZA
        log_warnings: Si True, registra advertencias para valores no reconocidos
        
    Returns:
        str: Código normalizado
        
    Raises:
        UnidadMedidaDesconocidaError: Si strict=True y la unidad no se reconoce
    """
    import logging
    logger = logging.getLogger(__name__)
    
    if not valor:
        if strict:
            raise UnidadMedidaDesconocidaError(
                valor,
                "Unidad de medida vacía o nula. Debe especificar una unidad válida."
            )
        return 'PIEZA'
    
    valor_upper = valor.upper().strip()
    valor_lower = valor.lower().strip()
    
    # Si ya es un código válido, retornarlo
    if valor_upper in UNIDADES_VALIDAS:
        return valor_upper
    
    # Buscar en alias
    if valor_lower in UNIDADES_ALIAS:
        return UNIDADES_ALIAS[valor_lower]
    
    # ISS-FIX: Intentar extraer unidad base de textos compuestos
    # Primero remover prefijos comunes
    texto_limpio = valor_upper
    prefijos_remover = ['EN ', 'CON ', 'DE ', 'POR ']
    for prefijo in prefijos_remover:
        if texto_limpio.startswith(prefijo):
            texto_limpio = texto_limpio[len(prefijo):]
    
    # Mapeo de palabras clave a unidades
    MAPEO_PALABRAS_CLAVE = {
        'CAJA': 'CAJA',
        'CAJAS': 'CAJA',
        'FRASCO': 'FRASCO',
        'FRASCOS': 'FRASCO',
        'GOTERO': 'FRASCO',  # Gotero es un tipo de frasco
        'ENVASE': 'FRASCO',  # Envase se mapea a frasco
        'BOTELLA': 'FRASCO',
        'SOBRE': 'SOBRE',
        'SOBRES': 'SOBRE',
        'AMPOLLETA': 'AMPOLLETA',
        'AMPOLLETAS': 'AMPOLLETA',
        'TABLETA': 'TABLETA',
        'TABLETAS': 'TABLETA',
        'GRAGEA': 'TABLETA',  # Gragea es similar a tableta
        'GRAGEAS': 'TABLETA',
        'COMPRIMIDO': 'TABLETA',
        'COMPRIMIDOS': 'TABLETA',
        'CAPSULA': 'CAPSULA',
        'CAPSULAS': 'CAPSULA',
        'PIEZA': 'PIEZA',
        'PIEZAS': 'PIEZA',
        'BOLSA': 'PIEZA',  # Bolsa se considera pieza
        'BOLSAS': 'PIEZA',
        'TUBO': 'PIEZA',
        'TUBOS': 'PIEZA',
        'JERINGA': 'PIEZA',
        'JERINGAS': 'PIEZA',
        'PARCHE': 'PIEZA',
        'PARCHES': 'PIEZA',
        'AMPULA': 'AMPOLLETA',
        'AMPULAS': 'AMPOLLETA',
        # ISS-AUDIT-004 FIX: Agregar más unidades comunes
        'KIT': 'PIEZA',
        'KITS': 'PIEZA',
        'PAQUETE': 'PIEZA',
        'PAQUETES': 'PIEZA',
        'UNIDAD': 'PIEZA',
        'UNIDADES': 'PIEZA',
        'VIAL': 'AMPOLLETA',
        'VIALES': 'AMPOLLETA',
        'LATA': 'PIEZA',
        'LATAS': 'PIEZA',
    }
    
    # Buscar palabras clave en el texto
    palabras = texto_limpio.replace(',', ' ').replace('-', ' ').split()
    for palabra in palabras:
        palabra_limpia = palabra.strip()
        if palabra_limpia in MAPEO_PALABRAS_CLAVE:
            return MAPEO_PALABRAS_CLAVE[palabra_limpia]
    
    # Buscar si alguna unidad válida está al inicio
    for unidad in UNIDADES_VALIDAS:
        if texto_limpio.startswith(unidad + ' ') or texto_limpio.startswith(unidad + '/'):
            return unidad
    
    # También buscar en alias con texto compuesto
    for alias, normalizado in UNIDADES_ALIAS.items():
        if valor_lower.startswith(alias + ' ') or valor_lower.startswith(alias + '/'):
            return normalizado
    
    # ISS-AUDIT-004 FIX: Si llegamos aquí, la unidad NO fue reconocida
    if strict:
        raise UnidadMedidaDesconocidaError(
            valor,
            f"Unidad de medida no reconocida: '{valor}'. "
            f"Unidades válidas: {', '.join(sorted(UNIDADES_VALIDAS))}. "
            f"Revise el dato o agregue un alias en UNIDADES_ALIAS si es una variante válida."
        )
    
    # ISS-AUDIT-004 FIX: Registrar advertencia para análisis posterior
    if log_warnings:
        logger.warning(
            f"ISS-AUDIT-004: Unidad de medida no reconocida '{valor}' convertida a 'PIEZA'. "
            f"Considere agregar un alias o revisar el dato de origen."
        )
    
    return 'PIEZA'


def normalizar_unidad_medida_strict(valor):
    """
    ISS-AUDIT-004 FIX: Versión estricta de normalizar_unidad_medida.
    
    Lanza UnidadMedidaDesconocidaError si la unidad no se reconoce.
    Usar en importaciones para detectar errores de datos.
    
    Args:
        valor: Valor de unidad a normalizar
        
    Returns:
        str: Código normalizado
        
    Raises:
        UnidadMedidaDesconocidaError: Si la unidad no se reconoce
    """
    return normalizar_unidad_medida(valor, strict=True, log_warnings=True)

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

# ISS-001 FIX (audit11): Estados de lote para cálculos de stock
# NOTA: La tabla 'lotes' en BD NO tiene campo 'estado'. 
# La disponibilidad se determina por: activo=True AND cantidad_actual>0 AND fecha_caducidad>=hoy
# Esta constante se mantiene por compatibilidad con código legacy que pueda referenciarla.
# ISS-004 FIX (audit14): Los filtros reales deben usar los campos existentes en BD.
ESTADOS_LOTE_DISPONIBLES = {'disponible'}  # DEPRECADO - usar filtros de BD reales
ESTADOS_LOTE_NO_DISPONIBLES = {'agotado', 'vencido', 'bloqueado', 'retirado'}  # DEPRECADO

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
# ALINEADO con FLUJO_REQUISICIONES_V2.md especificación
# ISS-TRANSICIONES FIX: Transiciones EXACTAS según trigger de Supabase
# validar_transicion_estado_requisicion() en la BD
TRANSICIONES_REQUISICION = {
    # Centro Penitenciario
    'borrador': ['pendiente_admin', 'cancelada'],
    'pendiente_admin': ['pendiente_director', 'rechazada', 'devuelta', 'cancelada'],
    'pendiente_director': ['enviada', 'rechazada', 'devuelta', 'cancelada'],
    
    # Farmacia Central - EXACTO según trigger Supabase
    'enviada': ['en_revision', 'rechazada', 'cancelada'],
    # ISS-TRIGGER-FIX: en_revision -> autorizada, rechazada, devuelta (NO parcial)
    # El estado 'parcial' es solo para SURTIDO parcial, no autorización
    'en_revision': ['autorizada', 'rechazada', 'devuelta'],
    # autorizada -> en_surtido, cancelada (según trigger)
    'autorizada': ['en_surtido', 'cancelada'],
    # en_surtido -> surtida, parcial, cancelada (según trigger)
    'en_surtido': ['surtida', 'parcial', 'cancelada'],
    # surtida -> entregada, vencida (según trigger)
    'surtida': ['entregada', 'vencida'],
    # parcial -> surtida, entregada, vencida (según trigger)
    'parcial': ['surtida', 'entregada', 'vencida'],
    
    # Devolución: regresa a pendiente_admin
    'devuelta': ['pendiente_admin', 'cancelada'],
    
    # Estados finales - no pueden cambiar
    'entregada': [],
    'rechazada': [],
    'vencida': [],
    'cancelada': [],
}

# ISS-TRIGGER-FIX: parcial es estado de SURTIDO parcial, no autorización parcial
# Se alcanza desde en_surtido, no desde en_revision
ESTADOS_SURTIDO_INTERNO = ['parcial']

# Transiciones extendidas que incluyen parcial (para validación interna de surtido)
TRANSICIONES_SURTIDO_EXTENDIDAS = {
    'en_surtido': ['surtida', 'parcial', 'cancelada'],
    'parcial': ['en_surtido', 'surtida', 'cancelada'],
}

# =============================================================================
# ISS-AUDIT-005 FIX: Estados cancelables - LISTA ESTÁTICA BASADA EN REGLAS DE NEGOCIO
# =============================================================================
# 
# ANTES (INSEGURO): ESTADOS_CANCELABLES se derivaba dinámicamente de TRANSICIONES_REQUISICION.
# PROBLEMA: Si alguien agregaba accidentalmente una transición 'surtida' -> 'cancelada'
# en TRANSICIONES_REQUISICION, automáticamente permitiría cancelar órdenes surtidas
# sin garantizar que exista lógica de reversión de inventario.
#
# AHORA (SEGURO): ESTADOS_CANCELABLES es una WHITELIST ESTÁTICA basada en:
# 1. Reglas de negocio: Solo estados SIN efectos de inventario irreversibles
# 2. Capacidad de reversión: Estados donde NO hay movimientos de stock confirmados
#
# REGLA FUNDAMENTAL: Una requisición solo puede cancelarse si:
# - NO ha generado movimientos de inventario (entradas/salidas)
# - NO ha afectado stock de lotes (físico o comprometido)
# - La cancelación es una operación administrativa sin efectos de inventario
#
# Para agregar un estado a esta lista, se DEBE verificar:
# 1. ¿El estado permite movimientos de inventario? Si sí, NO debe ser cancelable.
# 2. ¿Existe lógica de reversión implementada? Si no, NO debe ser cancelable.
# 3. ¿La cancelación desde este estado tiene sentido de negocio?
# =============================================================================

# ISS-AUDIT-005 FIX: Lista ESTÁTICA de estados cancelables
# Definida explícitamente según reglas de negocio, NO derivada de transiciones
ESTADOS_CANCELABLES_WHITELIST = frozenset([
    # Estados de creación/revisión (sin movimientos de inventario)
    'borrador',           # Requisición en creación, sin efectos
    'pendiente_admin',    # Esperando aprobación admin, sin efectos
    'pendiente_director', # Esperando aprobación director, sin efectos
    'enviada',            # Enviada a farmacia, sin efectos aún
    'devuelta',           # Devuelta para corrección, sin efectos
    
    # Estados de farmacia previos a surtido
    # NOTA: 'autorizada' permite cancelación porque el stock está RESERVADO
    # pero no MOVIDO físicamente. La cancelación libera la reserva.
    'autorizada',         # Autorizada pero no surtida, solo stock reservado
    
    # NOTA CRÍTICA: en_surtido PUEDE tener movimientos parciales
    # La cancelación desde en_surtido requiere REVERSIÓN de movimientos
    # Se incluye porque existe lógica de reversión implementada
    'en_surtido',         # En proceso, puede revertirse si hay lógica
])

# Estados que NUNCA pueden cancelarse por regla de negocio
# Incluye estados donde hay movimientos irreversibles o estados finales
ESTADOS_NO_CANCELABLES_WHITELIST = frozenset([
    # Estados con inventario ya movido (irreversible sin devolución formal)
    'surtida',            # Stock ya descontado de farmacia, entregado físicamente
    'parcial',            # Surtido parcial, hay movimientos confirmados
    
    # Estados finales - no pueden cambiar por definición
    'entregada',          # Completada exitosamente
    'rechazada',          # Rechazada, flujo terminado
    'vencida',            # Venció sin recolección, flujo terminado
    'cancelada',          # Ya cancelada
    
    # Estados intermedios sin transición a cancelada por diseño
    'en_revision',        # Solo puede ir a autorizada/rechazada/devuelta
])

# ISS-AUDIT-005 FIX: Mantener compatibilidad con código existente
ESTADOS_CANCELABLES = ESTADOS_CANCELABLES_WHITELIST
ESTADOS_SIN_CANCELACION = list(ESTADOS_NO_CANCELABLES_WHITELIST)

# ISS-AUDIT-005 FIX: DEPRECAR la función de cálculo dinámico
def _calcular_estados_cancelables():
    """
    DEPRECADO: Esta función ya NO debe usarse para determinar estados cancelables.
    
    Mantenida por compatibilidad pero ahora solo verifica consistencia
    entre la whitelist estática y las transiciones definidas.
    
    ISS-AUDIT-005: La fuente de verdad es ESTADOS_CANCELABLES_WHITELIST.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Calcular desde transiciones para verificar consistencia
    cancelables_transiciones = set()
    for estado, transiciones in TRANSICIONES_REQUISICION.items():
        if 'cancelada' in transiciones:
            cancelables_transiciones.add(estado)
    
    # Verificar consistencia
    diferencia = cancelables_transiciones.symmetric_difference(ESTADOS_CANCELABLES_WHITELIST)
    if diferencia:
        logger.warning(
            f"ISS-AUDIT-005 ADVERTENCIA: Inconsistencia detectada entre "
            f"TRANSICIONES_REQUISICION y ESTADOS_CANCELABLES_WHITELIST. "
            f"Estados en conflicto: {diferencia}. "
            f"Revisar reglas de negocio y actualizar whitelist si es necesario."
        )
    
    return ESTADOS_CANCELABLES_WHITELIST, ESTADOS_NO_CANCELABLES_WHITELIST

# Ejecutar verificación al importar módulo (solo en modo debug)
try:
    import os
    if os.environ.get('DJANGO_DEBUG', '').lower() == 'true':
        _calcular_estados_cancelables()
except Exception:
    pass  # Silenciar errores en importación

# =============================================================================
# ISS-005 FIX: CONSTANTES DE STOCK Y ESTADOS - FUENTE ÚNICA DE VERDAD
# =============================================================================
# Estas constantes definen qué estados afectan el cálculo de stock disponible.
# IMPORTANTE: Cualquier cambio aquí afecta:
# - RequisicionService.validar_stock_disponible()
# - RequisicionService._get_stock_comprometido_otras()
# - RequisicionContractValidator.validar_envio()
# - Reportes de inventario y stock
#
# Para agregar/modificar estados que comprometen stock:
# 1. Actualizar ESTADOS_COMPROMETIDOS
# 2. Actualizar TRANSICIONES_REQUISICION si es necesario
# 3. Verificar que las pruebas pasen
# =============================================================================

# ISS-001/002/003 FIX (audit8): Estados surtibles - FUENTE ÚNICA
# Solo estos estados permiten iniciar/continuar proceso de surtido
# ISS-PARCIAL FIX: Agregar 'parcial' - autorización parcial también puede surtirse
ESTADOS_SURTIBLES = ['autorizada', 'parcial', 'en_surtido']

# ISS-002 FIX (audit13): Estados que comprometen stock - FUENTE ÚNICA
# Requisiciones en estos estados tienen stock "reservado" pendiente de surtir
# Usado para calcular stock disponible real (evitar sobre-autorización)
# 
# Fórmula: stock_disponible = stock_farmacia - sum(autorizado - surtido) para estos estados
ESTADOS_COMPROMETIDOS = ['autorizada', 'en_surtido', 'parcial', 'surtida']

# ISS-005 FIX: Estados que permiten edición de detalles
# En estos estados el usuario puede modificar cantidades solicitadas
ESTADOS_EDITABLES = ['borrador', 'devuelta']

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
    # ISS-TRIGGER-FIX: El trigger de Supabase permite en_revision -> devuelta
    ('en_revision', 'devuelta'): ['farmacia', 'farmaceutico', 'admin_farmacia'],
    ('en_revision', 'rechazada'): ['farmacia', 'farmaceutico', 'admin_farmacia'],
    # NOTA: en_revision -> parcial NO está permitido por trigger Supabase
    # El estado 'parcial' es solo para SURTIDO parcial (en_surtido -> parcial)
    
    # Surtido - solo farmacia
    ('autorizada', 'en_surtido'): ['farmacia', 'farmaceutico', 'admin_farmacia'],
    ('en_surtido', 'surtida'): ['farmacia', 'farmaceutico', 'admin_farmacia'],
    ('en_surtido', 'parcial'): ['farmacia', 'farmaceutico', 'admin_farmacia'],
    
    # Recepción - solo centro destino
    ('surtida', 'entregada'): ['centro', 'usuario_centro', 'administrador_centro', 'director_centro', 'medico'],
    
    # Devolución: médico corrige y reenvía a pendiente_admin
    ('devuelta', 'pendiente_admin'): ['medico', 'centro', 'usuario_centro'],
    
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
    # ISS-PERFILES FIX: Agregar roles faltantes para completar matriz de permisos
    'centro': {
        # ISS-FIX: Usuario genérico de centro - NO puede autorizar
        # Los permisos de autorización son EXCLUSIVOS de administrador_centro y director_centro
        'puede_crear': False,
        'puede_enviar_admin': True,  # Puede enviar requisiciones de su centro
        'puede_autorizar_admin': False,  # SOLO administrador_centro
        'puede_autorizar_director': False,  # SOLO director_centro
        'puede_recibir_farmacia': False,
        'puede_autorizar_farmacia': False,
        'puede_surtir': False,
        'puede_confirmar_entrega': True,  # Puede confirmar recepción en su centro
    },
    'vista': {
        # Usuario de solo lectura - sin acciones
        'puede_crear': False,
        'puede_enviar_admin': False,
        'puede_autorizar_admin': False,
        'puede_autorizar_director': False,
        'puede_recibir_farmacia': False,
        'puede_autorizar_farmacia': False,
        'puede_surtir': False,
        'puede_confirmar_entrega': False,
    },
    # Aliases legacy
    'admin_sistema': {
        'puede_crear': True,
        'puede_enviar_admin': True,
        'puede_autorizar_admin': True,
        'puede_autorizar_director': True,
        'puede_recibir_farmacia': True,
        'puede_autorizar_farmacia': True,
        'puede_surtir': True,
        'puede_confirmar_entrega': True,
        'segregacion_autorizar_surtir': True,
        'segregacion_crear_autorizar': True,
    },
    'superusuario': {
        'puede_crear': True,
        'puede_enviar_admin': True,
        'puede_autorizar_admin': True,
        'puede_autorizar_director': True,
        'puede_recibir_farmacia': True,
        'puede_autorizar_farmacia': True,
        'puede_surtir': True,
        'puede_confirmar_entrega': True,
        'segregacion_autorizar_surtir': True,
        'segregacion_crear_autorizar': True,
    },
    'admin_farmacia': {
        'puede_crear': False,
        'puede_enviar_admin': False,
        'puede_autorizar_admin': False,
        'puede_autorizar_director': False,
        'puede_recibir_farmacia': True,
        'puede_autorizar_farmacia': True,
        'puede_surtir': True,
        'puede_confirmar_entrega': False,
        'segregacion_autorizar_surtir': True,
    },
    'usuario_centro': {
        'puede_crear': True,
        'puede_enviar_admin': True,
        'puede_autorizar_admin': False,
        'puede_autorizar_director': False,
        'puede_recibir_farmacia': False,
        'puede_autorizar_farmacia': False,
        'puede_surtir': False,
        'puede_confirmar_entrega': True,
    },
    'usuario_normal': {
        'puede_crear': True,
        'puede_enviar_admin': True,
        'puede_autorizar_admin': False,
        'puede_autorizar_director': False,
        'puede_recibir_farmacia': False,
        'puede_autorizar_farmacia': False,
        'puede_surtir': False,
        'puede_confirmar_entrega': True,
    },
    # =========================================================================
    # ALIASES DE ROLES - Variantes usadas en BD que mapean a permisos estándar
    # =========================================================================
    # ISS-ROL-FIX: Agregar alias 'admin_centro' que mapea a administrador_centro
    'admin_centro': {
        'puede_crear': False,
        'puede_enviar_admin': False,
        'puede_autorizar_admin': True,
        'puede_autorizar_director': False,
        'puede_recibir_farmacia': False,
        'puede_autorizar_farmacia': False,
        'puede_surtir': False,
        'puede_confirmar_entrega': True,
    },
    # ISS-ROL-FIX: Agregar alias 'director' que mapea a director_centro
    'director': {
        'puede_crear': False,
        'puede_enviar_admin': False,
        'puede_autorizar_admin': False,
        'puede_autorizar_director': True,
        'puede_recibir_farmacia': False,
        'puede_autorizar_farmacia': False,
        'puede_surtir': False,
        'puede_confirmar_entrega': True,
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
PAGINATION_MAX_PAGE_SIZE = 500  # ISS-FIX: Aumentado de 100 a 500 para mostrar todos los lotes en requisiciones

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
