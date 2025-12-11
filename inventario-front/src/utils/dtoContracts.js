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
 * ISS-002 FIX: Obtiene el stock de un producto con validación de contrato
 * 
 * @param {Object} producto - Objeto producto del API
 * @param {Object} options - Opciones
 * @param {boolean} options.strict - Si true, lanza error si falta campo canónico
 * @param {boolean} options.logWarnings - Si true, loguea advertencias de campos legacy
 * @returns {number} Stock del producto
 * @throws {Error} Si strict=true y no hay campo de stock válido
 */
export const getStockProducto = (producto, options = {}) => {
  const { strict = false, logWarnings = true } = options;
  
  if (!producto || typeof producto !== 'object') {
    if (strict) throw new Error('Producto inválido: debe ser un objeto');
    return 0;
  }

  // 1. Intentar campo canónico primero
  const stockCanonnico = producto[CAMPO_STOCK_CANONICO];
  if (typeof stockCanonnico === 'number' && !Number.isNaN(stockCanonnico)) {
    return stockCanonnico;
  }

  // 2. Buscar en campos legacy
  for (const campo of CAMPOS_STOCK_LEGACY) {
    const valor = producto[campo];
    if (typeof valor === 'number' && !Number.isNaN(valor)) {
      if (logWarnings && import.meta.env.DEV) {
        console.warn(
          `[DTO] Producto ${producto.id || producto.clave} usa campo legacy '${campo}' ` +
          `en lugar de '${CAMPO_STOCK_CANONICO}'. Actualizar backend.`
        );
      }
      return valor;
    }
  }

  // 3. Intentar parsear strings
  const candidatos = [
    producto[CAMPO_STOCK_CANONICO],
    ...CAMPOS_STOCK_LEGACY.map(c => producto[c])
  ].filter(v => v !== undefined && v !== null);

  for (const candidato of candidatos) {
    const parsed = Number(candidato);
    if (!Number.isNaN(parsed)) {
      if (logWarnings && import.meta.env.DEV) {
        console.warn(
          `[DTO] Producto ${producto.id || producto.clave} tiene stock como string. ` +
          `El API debería devolver número.`
        );
      }
      return parsed;
    }
  }

  // 4. Sin stock válido
  if (strict) {
    throw new Error(
      `Contrato violado: Producto ${producto.id || producto.clave} no tiene campo de stock válido. ` +
      `Esperado: '${CAMPO_STOCK_CANONICO}'`
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
 * @property {string} [fecha_fabricacion]
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
    proveedor: raw.proveedor || '',
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
 * Valida respuesta de lista paginada
 */
export const validarRespuestaPaginada = (response) => {
  if (Array.isArray(response)) {
    return { valido: true, data: response, count: response.length };
  }

  if (response && Array.isArray(response.results)) {
    return { 
      valido: true, 
      data: response.results, 
      count: response.count || response.results.length,
      next: response.next,
      previous: response.previous,
    };
  }

  if (response && Array.isArray(response.data)) {
    return {
      valido: true,
      data: response.data,
      count: response.total || response.count || response.data.length,
    };
  }

  return { valido: false, data: [], count: 0, error: 'Formato de respuesta no reconocido' };
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
