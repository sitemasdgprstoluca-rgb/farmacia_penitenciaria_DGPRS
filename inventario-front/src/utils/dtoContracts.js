/**
 * ISS-002 FIX: Contratos DTO para sincronización frontend-backend
 * 
 * Define los shapes esperados de las respuestas del API y proporciona
 * funciones de normalización para garantizar consistencia.
 * 
 * IMPORTANTE: Este archivo es la fuente única de verdad para los contratos
 * entre frontend y backend. Cualquier cambio en el API debe reflejarse aquí.
 */

// ============================================================================
// ISS-001 FIX: CONFIGURACIÓN GLOBAL DE CONTRATOS
// ============================================================================

const isDev = import.meta.env.DEV || import.meta.env.MODE === 'development';

/**
 * ISS-003 FIX (audit32): Modo estricto ACTIVADO en producción
 * Los campos legacy generan errores bloqueantes, no solo warnings
 */
const CONFIG = {
  // ISS-003 FIX: En producción, strictMode está ACTIVO por defecto
  strictModeEnabled: !isDev || import.meta.env.VITE_STRICT_CONTRACTS === 'true',
  // Endpoints que SIEMPRE requieren validación estricta
  strictModeEndpoints: ['productos', 'lotes', 'requisiciones', 'movimientos'],
  // Habilitar logging de violaciones (siempre en dev, configurable en prod)
  logViolations: isDev || import.meta.env.VITE_LOG_CONTRACT_VIOLATIONS === 'true',
  // Máximo de violaciones antes de alertar/bloquear
  maxViolationsBeforeAlert: 3,
  // ISS-003 FIX: Bloquear operaciones cuando hay violaciones críticas
  blockOnCriticalViolation: !isDev,
  // Callbacks para notificar a la UI de violaciones
  onViolation: null,
  onCriticalViolation: null,
};

/**
 * ISS-003 FIX: Configurar callbacks de violación para la UI
 */
export const setContractViolationHandler = (handler) => {
  CONFIG.onViolation = handler;
};

export const setCriticalViolationHandler = (handler) => {
  CONFIG.onCriticalViolation = handler;
};

/**
 * ISS-003 FIX: Verificar si modo estricto está activo para un endpoint
 */
export const isStrictModeActive = (endpoint = null) => {
  if (!CONFIG.strictModeEnabled) return false;
  if (!endpoint) return CONFIG.strictModeEnabled;
  return CONFIG.strictModeEndpoints.includes(endpoint);
};

/**
 * ISS-001 FIX: Métricas de violaciones de contrato
 * Rastrea campos legacy y discrepancias para monitoreo
 */
const contractMetrics = {
  violations: [],
  legacyFieldUsage: new Map(),
  paginationDiscrepancies: 0,
  criticalViolations: 0,
  lastViolation: null,
  blocked: false,
  
  recordViolation(type, details, isCritical = false) {
    const entry = {
      type,
      details,
      isCritical,
      timestamp: new Date().toISOString(),
    };
    this.violations.push(entry);
    this.lastViolation = entry;
    
    if (isCritical) {
      this.criticalViolations++;
      // ISS-003 FIX: Notificar violación crítica a la UI
      if (CONFIG.onCriticalViolation) {
        CONFIG.onCriticalViolation(entry);
      }
      // Bloquear si está configurado
      if (CONFIG.blockOnCriticalViolation && this.criticalViolations >= CONFIG.maxViolationsBeforeAlert) {
        this.blocked = true;
        console.error(
          `[DTO CONTRACT] ❌ BLOQUEADO: ${this.criticalViolations} violaciones críticas. ` +
          `Operaciones de escritura deshabilitadas hasta resolver.`
        );
      }
    }
    
    // Notificar a la UI
    if (CONFIG.onViolation) {
      CONFIG.onViolation(entry);
    }
    
    // Mantener solo últimas 100 violaciones
    if (this.violations.length > 100) {
      this.violations.shift();
    }
    
    // Alertar si hay demasiadas violaciones
    if (this.violations.length >= CONFIG.maxViolationsBeforeAlert && CONFIG.logViolations) {
      console.warn(
        `[DTO CONTRACT] ⚠️ ${this.violations.length} violaciones de contrato detectadas. ` +
        `Revisar alineación backend-frontend.`
      );
    }
  },
  
  recordLegacyField(campo, endpoint = 'unknown') {
    const key = `${endpoint}:${campo}`;
    const count = (this.legacyFieldUsage.get(key) || 0) + 1;
    this.legacyFieldUsage.set(key, count);
    
    // ISS-003 FIX: En modo estricto, campos legacy son violaciones críticas
    const isCritical = isStrictModeActive(endpoint);
    this.recordViolation('legacy_field', { campo, endpoint, count }, isCritical);
  },
  
  recordPaginationDiscrepancy(format, endpoint = 'unknown') {
    this.paginationDiscrepancies++;
    const isCritical = isStrictModeActive(endpoint);
    this.recordViolation('pagination_format', { format, endpoint }, isCritical);
  },
  
  getMetrics() {
    return {
      totalViolations: this.violations.length,
      criticalViolations: this.criticalViolations,
      legacyFieldUsage: Object.fromEntries(this.legacyFieldUsage),
      paginationDiscrepancies: this.paginationDiscrepancies,
      lastViolation: this.lastViolation,
      blocked: this.blocked,
      strictModeEnabled: CONFIG.strictModeEnabled,
    };
  },
  
  isBlocked() {
    return this.blocked;
  },
  
  reset() {
    this.violations = [];
    this.legacyFieldUsage.clear();
    this.paginationDiscrepancies = 0;
    this.criticalViolations = 0;
    this.lastViolation = null;
    this.blocked = false;
  },
  
  // ISS-003 FIX: Desbloquear manualmente (para admin)
  unblock() {
    this.blocked = false;
    this.criticalViolations = 0;
  },
  
  // ISS-003 FIX (audit32): Bloquear manualmente con razón
  block(reason = 'manual') {
    this.blocked = true;
    this.recordViolation('manual_block', { reason }, true);
    console.error(`[DTO CONTRACT] ❌ BLOQUEADO: ${reason}`);
  },
};

// Exportar métricas para monitoreo externo
export const getContractMetrics = () => ({
  ...contractMetrics.getMetrics(),
  // ISS-003 FIX (audit32): Exponer métodos de control para tests y admin
  isBlocked: () => contractMetrics.isBlocked(),
  block: (reason) => contractMetrics.block(reason),
  unblock: () => contractMetrics.unblock(),
});
export const resetContractMetrics = () => contractMetrics.reset();
export const isContractBlocked = () => contractMetrics.isBlocked();
export const unblockContract = () => contractMetrics.unblock();

// ============================================================================
// PRODUCTO DTO
// ============================================================================

/**
 * Shape esperado de un producto desde el API
 * @typedef {Object} ProductoDTO
 * @property {number} id - ID único
 * @property {string} clave - Código/clave del producto
 * @property {string} nombre - Nombre del producto
 * @property {string} [descripcion] - Descripción opcional
 * @property {string} unidad_medida - Unidad de medida (PIEZA, CAJA, etc.)
 * @property {string} categoria - Categoría del producto
 * @property {number} stock_minimo - Stock mínimo para alertas
 * @property {number} stock_actual - Stock actual calculado
 * @property {string} [sustancia_activa] - Sustancia activa
 * @property {string} [presentacion] - Presentación
 * @property {string} [concentracion] - Concentración
 * @property {string} [via_administracion] - Vía de administración
 * @property {boolean} requiere_receta - Si requiere receta
 * @property {boolean} es_controlado - Si es medicamento controlado
 * @property {boolean} activo - Si está activo
 * @property {string} [imagen] - URL de imagen
 * @property {string} created_at - Fecha de creación
 * @property {string} updated_at - Fecha de actualización
 */

/**
 * Campo canónico para stock en el backend
 * El backend DEBE devolver este campo. Si no existe, es un error de contrato.
 */
const CAMPO_STOCK_CANONICO = 'stock_actual';

/**
 * Campos legacy que podrían existir por compatibilidad
 * Se usan como fallback pero se loguea advertencia
 */
const CAMPOS_STOCK_LEGACY = [
  'stock_total',
  'inventario_total', 
  'inventario',
  'existencias',
  'stock_disponible',
  'cantidad_disponible',
  'cantidad_total',
  'stock'
];

/**
 * ISS-001/002/003 FIX: Obtiene el stock de un producto con validación de contrato
 * 
 * ISS-003 (audit32): En producción, modo estricto está ACTIVO por defecto
 * Los campos legacy generan errores y se registran como violaciones críticas
 * 
 * @param {Object} producto - Objeto producto del API
 * @param {Object} options - Opciones
 * @param {boolean} options.strict - Si true, lanza error si falta campo canónico (default: auto)
 * @param {boolean} options.logWarnings - Si true, loguea advertencias de campos legacy
 * @param {string} options.endpoint - Nombre del endpoint para métricas
 * @param {boolean} options.alertOnLegacy - Mostrar alerta visible al usuario cuando usa campos legacy
 * @returns {number} Stock del producto
 * @throws {Error} Si strict=true y no hay campo de stock válido
 */
export const getStockProducto = (producto, options = {}) => {
  const { 
    // ISS-003 FIX: Modo estricto AUTOMÁTICO en producción para productos
    strict = isStrictModeActive(options.endpoint || 'productos'), 
    logWarnings = true, 
    endpoint = 'productos',
    alertOnLegacy = isStrictModeActive(options.endpoint || 'productos'),
  } = options;
  
  // ISS-003 FIX: Verificar si está bloqueado por violaciones críticas
  if (contractMetrics.isBlocked() && strict) {
    throw new Error(
      `[CONTRACT BLOCKED] Operaciones bloqueadas por violaciones de contrato. ` +
      `Contacte al administrador para revisar la alineación backend-frontend.`
    );
  }
  
  if (!producto || typeof producto !== 'object') {
    if (strict) throw new Error('Producto inválido: debe ser un objeto');
    return 0;
  }

  const productoId = producto.id || producto.clave || 'desconocido';

  // 1. Intentar campo canónico primero - ÚNICO ACEPTADO EN MODO ESTRICTO
  const stockCanonnico = producto[CAMPO_STOCK_CANONICO];
  if (typeof stockCanonnico === 'number' && !Number.isNaN(stockCanonnico)) {
    return stockCanonnico;
  }
  
  // ISS-003 FIX: Si estamos en modo estricto y no hay campo canónico, es error crítico
  if (strict && stockCanonnico === undefined) {
    contractMetrics.recordViolation('missing_canonical_field', { 
      productoId, 
      campo: CAMPO_STOCK_CANONICO,
      endpoint 
    }, true); // Marcar como crítico
    
    throw new Error(
      `[CONTRACT ERROR] Producto ${productoId}: falta campo canónico '${CAMPO_STOCK_CANONICO}'. ` +
      `Backend debe incluir este campo. Endpoint: ${endpoint}`
    );
  }

  // 2. Buscar en campos legacy - REGISTRAR VIOLACIÓN (crítica en strict mode)
  for (const campo of CAMPOS_STOCK_LEGACY) {
    const valor = producto[campo];
    if (typeof valor === 'number' && !Number.isNaN(valor)) {
      // ISS-003 FIX: Registrar uso de campo legacy como violación (crítica si strict)
      contractMetrics.recordLegacyField(campo, endpoint);
      
      if (logWarnings && CONFIG.logViolations) {
        console.warn(
          `[DTO CONTRACT] ⚠️ Producto ${productoId} usa campo legacy '${campo}' ` +
          `en lugar de '${CAMPO_STOCK_CANONICO}'. Endpoint: ${endpoint}. Actualizar backend.`
        );
      }
      
      // ISS-003 FIX: En modo estricto, NO aceptar campos legacy
      if (strict) {
        throw new Error(
          `[CONTRACT ERROR] Producto ${productoId}: usando campo legacy '${campo}' ` +
          `en lugar del canónico '${CAMPO_STOCK_CANONICO}'. ` +
          `Backend debe enviar el campo correcto. Endpoint: ${endpoint}`
        );
      }
      
      // ISS-001: Alerta visible si está habilitada (para endpoints críticos)
      if (alertOnLegacy && !isDev) {
        console.error(
          `[STOCK CONTRACT] Producto ${productoId}: usando campo legacy '${campo}'. ` +
          `Esto puede causar inconsistencias de inventario.`
        );
      }
      
      return valor;
    }
  }

  // 3. Intentar parsear strings - TAMBIÉN ES VIOLACIÓN
  const candidatos = [
    producto[CAMPO_STOCK_CANONICO],
    ...CAMPOS_STOCK_LEGACY.map(c => producto[c])
  ].filter(v => v !== undefined && v !== null);

  for (const candidato of candidatos) {
    const parsed = Number(candidato);
    if (!Number.isNaN(parsed)) {
      // ISS-003 FIX: Tipo incorrecto es violación crítica en strict mode
      const isCritical = isStrictModeActive(endpoint);
      contractMetrics.recordViolation('string_as_number', { 
        productoId, 
        campo: 'stock', 
        endpoint 
      }, isCritical);
      
      if (strict) {
        throw new Error(
          `[CONTRACT ERROR] Producto ${productoId}: stock es string ('${candidato}') ` +
          `en lugar de number. Backend debe enviar tipo correcto. Endpoint: ${endpoint}`
        );
      }
      
      if (logWarnings && CONFIG.logViolations) {
        console.warn(
          `[DTO CONTRACT] ⚠️ Producto ${productoId} tiene stock como string. ` +
          `El API debería devolver número. Endpoint: ${endpoint}`
        );
      }
      return parsed;
    }
  }

  // 4. Sin stock válido
  if (strict) {
    const error = new Error(
      `Contrato violado: Producto ${productoId} no tiene campo de stock válido. ` +
      `Esperado: '${CAMPO_STOCK_CANONICO}'. Endpoint: ${endpoint}`
    );
    error.name = 'ContractViolationError';
    error.productoId = productoId;
    error.endpoint = endpoint;
    throw error;
  }

  // ISS-001: Registrar ausencia de stock (solo si no es strict)
  contractMetrics.recordViolation('missing_stock', { productoId, endpoint }, false);
  
  if (logWarnings && CONFIG.logViolations) {
    console.warn(
      `[DTO CONTRACT] ⚠️ Producto ${productoId} sin campo de stock válido. ` +
      `Retornando 0. Endpoint: ${endpoint}`
    );
  }

  return 0;
};

/**
 * ISS-002 FIX: Normaliza un producto del API al shape esperado
 * 
 * @param {Object} raw - Producto crudo del API
 * @returns {ProductoDTO} Producto normalizado
 */
export const normalizarProducto = (raw) => {
  if (!raw || typeof raw !== 'object') {
    throw new Error('normalizarProducto: input debe ser un objeto');
  }

  return {
    id: raw.id,
    clave: raw.clave || raw.codigo_barras || raw.codigo || '',
    nombre: raw.nombre || '',
    descripcion: raw.descripcion || '',
    unidad_medida: (raw.unidad_medida || 'PIEZA').toUpperCase(),
    categoria: raw.categoria || 'medicamento',
    stock_minimo: Number(raw.stock_minimo) || 0,
    stock_actual: getStockProducto(raw, { strict: false, logWarnings: false }),
    sustancia_activa: raw.sustancia_activa || '',
    presentacion: raw.presentacion || '',
    concentracion: raw.concentracion || '',
    via_administracion: raw.via_administracion || '',
    requiere_receta: Boolean(raw.requiere_receta),
    es_controlado: Boolean(raw.es_controlado),
    activo: raw.activo !== false, // default true
    imagen: raw.imagen || null,
    created_at: raw.created_at || null,
    updated_at: raw.updated_at || null,
  };
};

/**
 * Formatea el stock para mostrar en UI
 * @param {Object} producto - Producto
 * @returns {string} Stock formateado
 */
export const formatStock = (producto) => {
  const stock = getStockProducto(producto);
  return stock.toLocaleString('es-MX');
};

// ============================================================================
// LOTE DTO
// ============================================================================

/**
 * @typedef {Object} LoteDTO
 * @property {number} id
 * @property {number} producto_id
 * @property {string} numero_lote
 * @property {number} cantidad_inicial
 * @property {number} cantidad_actual
 * @property {string} fecha_caducidad
 * @property {string} [fecha_fabricacion] - Representa fecha de recepción del lote
 * @property {string} estado - calculado: disponible, agotado, vencido, por_vencer
 * @property {boolean} activo
 */

/**
 * Normaliza un lote del API
 * @param {Object} raw - Lote crudo
 * @returns {LoteDTO}
 */
export const normalizarLote = (raw) => {
  if (!raw) return null;
  
  return {
    id: raw.id,
    producto_id: raw.producto_id || raw.producto,
    numero_lote: raw.numero_lote || raw.lote || '',
    cantidad_inicial: Number(raw.cantidad_inicial) || 0,
    cantidad_actual: Number(raw.cantidad_actual) || 0,
    fecha_caducidad: raw.fecha_caducidad || null,
    fecha_fabricacion: raw.fecha_fabricacion || null,
    estado: raw.estado || calcularEstadoLote(raw),
    activo: raw.activo !== false,
    marca: raw.marca || '',
    precio_unitario: Number(raw.precio_unitario) || 0,
  };
};

/**
 * Calcula el estado de un lote basado en sus propiedades
 */
const calcularEstadoLote = (lote) => {
  if (!lote.activo) return 'inactivo';
  if (lote.cantidad_actual <= 0) return 'agotado';
  
  if (lote.fecha_caducidad) {
    const hoy = new Date();
    const caducidad = new Date(lote.fecha_caducidad);
    const diasParaVencer = Math.ceil((caducidad - hoy) / (1000 * 60 * 60 * 24));
    
    if (diasParaVencer <= 0) return 'vencido';
    if (diasParaVencer <= 90) return 'por_vencer';
  }
  
  return 'disponible';
};

// ============================================================================
// REQUISICION DTO
// ============================================================================

/**
 * Estados válidos de requisición
 */
export const ESTADOS_REQUISICION = {
  BORRADOR: 'borrador',
  PENDIENTE: 'pendiente',
  APROBADA: 'aprobada',
  EN_PROCESO: 'en_proceso',
  SURTIDA_PARCIAL: 'surtida_parcial',
  SURTIDA: 'surtida',
  RECHAZADA: 'rechazada',
  CANCELADA: 'cancelada',
};

/**
 * @typedef {Object} RequisicionDTO
 * @property {number} id
 * @property {string} folio
 * @property {string} estado
 * @property {string} fecha_creacion
 * @property {string} [fecha_aprobacion]
 * @property {string} [fecha_surtido]
 * @property {number} solicitante_id
 * @property {string} solicitante_nombre
 * @property {number} [aprobador_id]
 * @property {string} [lugar_entrega]
 * @property {string} [observaciones]
 * @property {Array} detalles
 */

/**
 * Normaliza una requisición del API
 * @param {Object} raw - Requisición cruda
 * @returns {RequisicionDTO}
 */
export const normalizarRequisicion = (raw) => {
  if (!raw) return null;

  return {
    id: raw.id,
    folio: raw.folio || '',
    estado: raw.estado || ESTADOS_REQUISICION.BORRADOR,
    fecha_creacion: raw.fecha_creacion || raw.created_at || null,
    fecha_aprobacion: raw.fecha_aprobacion || null,
    fecha_surtido: raw.fecha_surtido || null,
    solicitante_id: raw.solicitante_id || raw.solicitante?.id || null,
    solicitante_nombre: raw.solicitante_nombre || raw.solicitante?.nombre || 
                        raw.solicitante?.username || '',
    aprobador_id: raw.aprobador_id || raw.aprobador?.id || null,
    aprobador_nombre: raw.aprobador_nombre || raw.aprobador?.nombre ||
                      raw.aprobador?.username || '',
    lugar_entrega: raw.lugar_entrega || '',
    observaciones: raw.observaciones || '',
    detalles: (raw.detalles || []).map(normalizarDetalleRequisicion),
    centro_id: raw.centro_id || raw.centro?.id || null,
    centro_nombre: raw.centro_nombre || raw.centro?.nombre || '',
  };
};

/**
 * Normaliza un detalle de requisición
 */
export const normalizarDetalleRequisicion = (raw) => {
  if (!raw) return null;

  return {
    id: raw.id,
    producto_id: raw.producto_id || raw.producto?.id || null,
    producto_clave: raw.producto_clave || raw.producto?.clave || '',
    producto_nombre: raw.producto_nombre || raw.producto?.nombre || '',
    cantidad_solicitada: Number(raw.cantidad_solicitada) || 0,
    cantidad_aprobada: Number(raw.cantidad_aprobada) || null,
    cantidad_surtida: Number(raw.cantidad_surtida) || 0,
    unidad_medida: raw.unidad_medida || raw.producto?.unidad_medida || 'PIEZA',
    observaciones: raw.observaciones || '',
  };
};

// ============================================================================
// MOVIMIENTO DTO
// ============================================================================

/**
 * Tipos de movimiento válidos
 */
export const TIPOS_MOVIMIENTO = {
  ENTRADA: 'entrada',
  SALIDA: 'salida',
  AJUSTE: 'ajuste',
  TRANSFERENCIA: 'transferencia',
  MERMA: 'merma',
  DEVOLUCION: 'devolucion',
};

/**
 * @typedef {Object} MovimientoDTO
 * @property {number} id
 * @property {string} tipo
 * @property {number} cantidad
 * @property {number} lote_id
 * @property {number} producto_id
 * @property {string} fecha
 * @property {string} [referencia]
 * @property {string} [observaciones]
 */

export const normalizarMovimiento = (raw) => {
  if (!raw) return null;

  return {
    id: raw.id,
    tipo: raw.tipo || TIPOS_MOVIMIENTO.ENTRADA,
    cantidad: Number(raw.cantidad) || 0,
    lote_id: raw.lote_id || raw.lote?.id || null,
    producto_id: raw.producto_id || raw.producto?.id || null,
    fecha: raw.fecha || raw.created_at || null,
    referencia: raw.referencia || '',
    observaciones: raw.observaciones || '',
    usuario_id: raw.usuario_id || raw.usuario?.id || null,
    usuario_nombre: raw.usuario_nombre || raw.usuario?.username || '',
  };
};

// ============================================================================
// VALIDADORES DE CONTRATO
// ============================================================================

/**
 * Valida que un objeto tenga los campos requeridos
 * @param {Object} obj - Objeto a validar
 * @param {string[]} camposRequeridos - Lista de campos requeridos
 * @param {string} entidad - Nombre de la entidad para mensajes
 * @returns {{ valido: boolean, errores: string[] }}
 */
export const validarContrato = (obj, camposRequeridos, entidad = 'Objeto') => {
  const errores = [];

  if (!obj || typeof obj !== 'object') {
    return { valido: false, errores: [`${entidad} debe ser un objeto`] };
  }

  for (const campo of camposRequeridos) {
    if (obj[campo] === undefined || obj[campo] === null) {
      errores.push(`${entidad}: campo '${campo}' es requerido`);
    }
  }

  return { valido: errores.length === 0, errores };
};

/**
 * Campos requeridos por entidad
 */
export const CAMPOS_REQUERIDOS = {
  producto: ['id', 'clave', 'nombre'],
  lote: ['id', 'numero_lote', 'producto_id'],
  requisicion: ['id', 'folio', 'estado'],
  movimiento: ['id', 'tipo', 'cantidad'],
};

/**
 * ISS-003 FIX (audit32): Valida respuesta de lista paginada con registro de discrepancias
 * 
 * FORMATO CANÓNICO ESPERADO (DRF):
 * { results: [...], count: N, next: url|null, previous: url|null }
 * 
 * ISS-003: En producción, modo estricto está ACTIVO AUTOMÁTICAMENTE
 * para endpoints críticos (productos, lotes, requisiciones)
 * 
 * @param {Object|Array} response - Respuesta del API
 * @param {Object} options - Opciones
 * @param {string} options.endpoint - Nombre del endpoint para métricas
 * @param {boolean} options.strict - Si true, rechaza formatos no canónicos (default: auto)
 * @returns {{ valido: boolean, data: Array, count: number, warning?: string }}
 */
export const validarRespuestaPaginada = (response, options = {}) => {
  // ISS-003 FIX: Modo estricto AUTOMÁTICO en producción para endpoints críticos
  const { 
    endpoint = 'unknown', 
    strict = isStrictModeActive(endpoint),
  } = options;
  
  // ISS-003 FIX: Verificar bloqueo por violaciones críticas
  if (contractMetrics.isBlocked() && strict) {
    return {
      valido: false,
      data: [],
      count: 0,
      error: '[CONTRACT BLOCKED] Operaciones bloqueadas por violaciones críticas de contrato.',
      format: 'blocked',
    };
  }
  
  // ISS-003: Formato canónico DRF - el único válido en modo estricto
  if (response && Array.isArray(response.results)) {
    return { 
      valido: true, 
      data: response.results, 
      count: response.count ?? response.results.length,
      next: response.next ?? null,
      previous: response.previous ?? null,
      format: 'canonical',
    };
  }
  
  // ISS-003: Array plano - FORMATO LEGACY
  if (Array.isArray(response)) {
    contractMetrics.recordPaginationDiscrepancy('array_plain', endpoint);
    
    if (CONFIG.logViolations) {
      console.warn(
        `[DTO CONTRACT] ⚠️ Endpoint ${endpoint} devuelve array plano en lugar de ` +
        `formato paginado {results, count}. Sin información de paginación disponible.`
      );
    }
    
    if (strict) {
      return { 
        valido: false, 
        data: response, 
        count: response.length,
        error: 'Formato no canónico: array plano sin paginación',
        format: 'array_plain',
      };
    }
    
    return { 
      valido: true, 
      data: response, 
      count: response.length,
      warning: 'Array plano - sin información de paginación',
      format: 'array_plain',
    };
  }

  // ISS-003: Formato {data: [...]} - FORMATO ALTERNATIVO (algunos backends)
  if (response && Array.isArray(response.data)) {
    contractMetrics.recordPaginationDiscrepancy('data_wrapper', endpoint);
    
    if (CONFIG.logViolations) {
      console.warn(
        `[DTO CONTRACT] ⚠️ Endpoint ${endpoint} usa formato {data: [...]} en lugar de ` +
        `{results: [...]}. Considerar estandarizar al formato DRF.`
      );
    }
    
    if (strict) {
      return {
        valido: false,
        data: response.data,
        count: response.total || response.count || response.data.length,
        error: 'Formato no canónico: wrapper data en lugar de results',
        format: 'data_wrapper',
      };
    }
    
    return {
      valido: true,
      data: response.data,
      count: response.total || response.count || response.data.length,
      warning: 'Formato alternativo {data} - considerar migrar a {results}',
      format: 'data_wrapper',
    };
  }

  // ISS-003: Formato no reconocido - SIEMPRE es error
  contractMetrics.recordViolation('unknown_pagination_format', { 
    endpoint, 
    responseType: typeof response,
    hasResults: response?.results !== undefined,
    hasData: response?.data !== undefined,
  });
  
  if (CONFIG.logViolations) {
    console.error(
      `[DTO CONTRACT] ❌ Endpoint ${endpoint} devolvió formato de paginación no reconocido. ` +
      `Tipo: ${typeof response}. Esperado: {results: [...], count: N}`
    );
  }

  return { 
    valido: false, 
    data: [], 
    count: 0, 
    error: `Formato de respuesta no reconocido para endpoint ${endpoint}`,
    format: 'unknown',
  };
};

export default {
  // Productos
  getStockProducto,
  normalizarProducto,
  formatStock,
  // Lotes
  normalizarLote,
  // Requisiciones
  normalizarRequisicion,
  normalizarDetalleRequisicion,
  ESTADOS_REQUISICION,
  // Movimientos
  normalizarMovimiento,
  TIPOS_MOVIMIENTO,
  // Validadores
  validarContrato,
  validarRespuestaPaginada,
  CAMPOS_REQUERIDOS,
};
