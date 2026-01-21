/**
 * ISS-004 FIX: Validadores por flujo de negocio
 * 
 * Centraliza validaciones específicas para cada flujo:
 * - Creación/edición de productos
 * - Flujo de requisiciones (transiciones de estado)
 * - Validación de stock para surtido
 * - Permisos por rol y estado
 * 
 * IMPORTANTE: Este archivo debe mantenerse sincronizado con las reglas
 * del backend en core/constants.py y core/validators.py
 */

import { getStockProducto, getContractMetrics } from './dtoContracts';
// ISS-SEC FIX: Importar desde el objeto requisicionesValidacion exportado
import { requisicionesValidacion } from '../services/api';
const { esTransicionValida: esTransicionValidaV2, TRANSICIONES_V2 } = requisicionesValidacion;

// ============================================================================
// CONFIGURACIÓN
// ============================================================================

const isDev = import.meta.env.DEV || import.meta.env.MODE === 'development';

/**
 * Métricas de validación para monitoreo
 */
const validationMetrics = {
  validations: 0,
  failures: 0,
  stockInsufficient: 0,
  invalidTransitions: 0,
  lastFailure: null,
  
  record(type, success, details = null) {
    this.validations++;
    if (!success) {
      this.failures++;
      this.lastFailure = { type, details, timestamp: new Date().toISOString() };
      
      if (type === 'stock') this.stockInsufficient++;
      if (type === 'transition') this.invalidTransitions++;
    }
  },
  
  getMetrics() {
    return { ...this, successRate: this.validations > 0 ? ((this.validations - this.failures) / this.validations * 100).toFixed(1) : 100 };
  },
  
  reset() {
    this.validations = 0;
    this.failures = 0;
    this.stockInsufficient = 0;
    this.invalidTransitions = 0;
    this.lastFailure = null;
  },
};

export const getValidationMetrics = () => validationMetrics.getMetrics();
export const resetValidationMetrics = () => validationMetrics.reset();

// ============================================================================
// FLUJO: CREACIÓN/EDICIÓN DE PRODUCTOS
// ============================================================================

/**
 * Reglas de validación para productos
 * Sincronizadas con backend/inventario/serializers.py
 */
export const PRODUCTO_RULES = {
  clave: {
    required: true,
    minLength: 3,
    maxLength: 50,
    pattern: /^[A-Za-z0-9\-_]+$/,
    patternMessage: 'Solo letras, números, guiones y guiones bajos',
  },
  nombre: {
    required: true,
    minLength: 3,
    maxLength: 500,
  },
  descripcion: {
    required: false,
    maxLength: 1000,
  },
  unidad_medida: {
    required: true,
    // Valores válidos se obtienen del catálogo
  },
  categoria: {
    required: true,
    validValues: ['medicamento', 'material_curacion', 'insumo', 'equipo_medico', 'otro'],
  },
  stock_minimo: {
    required: true,
    type: 'integer',
    min: 0,
    max: 999999,
  },
  presentacion: {
    required: false,
    maxLength: 200,
  },
  sustancia_activa: {
    required: false,
    maxLength: 200,
  },
  concentracion: {
    required: false,
    maxLength: 100,
  },
};

/**
 * ISS-004 FIX: Valida un producto para creación
 * @param {Object} producto - Datos del producto
 * @param {Object} options - Opciones
 * @param {Array} options.unidadesValidas - Unidades de medida válidas del catálogo
 * @param {boolean} options.strict - Modo estricto (falla en warnings)
 * @returns {{ valido: boolean, errores: Object, warnings: Array }}
 */
export const validarProductoCreacion = (producto, options = {}) => {
  const { unidadesValidas = null, strict = false } = options;
  const errores = {};
  const warnings = [];
  
  // Validar clave
  const claveRules = PRODUCTO_RULES.clave;
  if (claveRules.required && !producto.clave?.trim()) {
    errores.clave = 'La clave es obligatoria';
  } else if (producto.clave) {
    if (producto.clave.length < claveRules.minLength) {
      errores.clave = `La clave debe tener al menos ${claveRules.minLength} caracteres`;
    } else if (producto.clave.length > claveRules.maxLength) {
      errores.clave = `La clave no puede exceder ${claveRules.maxLength} caracteres`;
    } else if (!claveRules.pattern.test(producto.clave)) {
      errores.clave = claveRules.patternMessage;
    }
  }
  
  // Validar nombre
  const nombreRules = PRODUCTO_RULES.nombre;
  if (nombreRules.required && !producto.nombre?.trim()) {
    errores.nombre = 'El nombre es obligatorio';
  } else if (producto.nombre) {
    if (producto.nombre.length < nombreRules.minLength) {
      errores.nombre = `El nombre debe tener al menos ${nombreRules.minLength} caracteres`;
    } else if (producto.nombre.length > nombreRules.maxLength) {
      errores.nombre = `El nombre no puede exceder ${nombreRules.maxLength} caracteres`;
    }
  }
  
  // Validar unidad_medida
  if (PRODUCTO_RULES.unidad_medida.required && !producto.unidad_medida?.trim()) {
    errores.unidad_medida = 'La unidad de medida es obligatoria';
  } else if (unidadesValidas && producto.unidad_medida) {
    // ISS-002 FIX: Validar contra catálogo del servidor
    if (!unidadesValidas.includes(producto.unidad_medida.toUpperCase())) {
      errores.unidad_medida = `Unidad no válida. Opciones: ${unidadesValidas.slice(0, 5).join(', ')}...`;
    }
  }
  
  // Validar categoría
  const catRules = PRODUCTO_RULES.categoria;
  if (catRules.required && !producto.categoria?.trim()) {
    errores.categoria = 'La categoría es obligatoria';
  } else if (producto.categoria && !catRules.validValues.includes(producto.categoria)) {
    errores.categoria = `Categoría no válida. Opciones: ${catRules.validValues.join(', ')}`;
  }
  
  // Validar stock_minimo
  const stockRules = PRODUCTO_RULES.stock_minimo;
  if (stockRules.required && (producto.stock_minimo === undefined || producto.stock_minimo === '')) {
    errores.stock_minimo = 'El stock mínimo es obligatorio';
  } else if (producto.stock_minimo !== undefined && producto.stock_minimo !== '') {
    const stockMin = Number(producto.stock_minimo);
    if (isNaN(stockMin)) {
      errores.stock_minimo = 'El stock mínimo debe ser un número';
    } else if (!Number.isInteger(stockMin)) {
      errores.stock_minimo = 'El stock mínimo debe ser un número entero';
    } else if (stockMin < stockRules.min) {
      errores.stock_minimo = `El stock mínimo no puede ser negativo`;
    } else if (stockMin > stockRules.max) {
      errores.stock_minimo = `El stock mínimo no puede exceder ${stockRules.max}`;
    }
  }
  
  // Warnings (no bloquean pero se muestran)
  if (!producto.descripcion?.trim()) {
    warnings.push('Se recomienda agregar una descripción para mejor identificación');
  }
  if (!producto.presentacion?.trim()) {
    warnings.push('Se recomienda especificar la presentación del producto');
  }
  
  const valido = Object.keys(errores).length === 0 && (!strict || warnings.length === 0);
  validationMetrics.record('producto_creacion', valido, valido ? null : errores);
  
  return {
    valido,
    errores,
    warnings,
    primerError: Object.values(errores)[0] || null,
  };
};

/**
 * ISS-004 FIX: Valida un producto para edición
 * Similar a creación pero permite campos parciales
 */
export const validarProductoEdicion = (producto, productoOriginal, options = {}) => {
  const { unidadesValidas = null } = options;
  const errores = {};
  const warnings = [];
  
  // Para edición, solo validar campos que cambiaron
  const camposModificados = {};
  for (const key of Object.keys(producto)) {
    if (producto[key] !== productoOriginal?.[key]) {
      camposModificados[key] = producto[key];
    }
  }
  
  // Validar clave si cambió
  if ('clave' in camposModificados) {
    const claveRules = PRODUCTO_RULES.clave;
    if (!producto.clave?.trim()) {
      errores.clave = 'La clave no puede quedar vacía';
    } else if (producto.clave.length < claveRules.minLength) {
      errores.clave = `La clave debe tener al menos ${claveRules.minLength} caracteres`;
    } else if (!claveRules.pattern.test(producto.clave)) {
      errores.clave = claveRules.patternMessage;
    }
  }
  
  // Validar nombre si cambió
  if ('nombre' in camposModificados && !producto.nombre?.trim()) {
    errores.nombre = 'El nombre no puede quedar vacío';
  }
  
  // Validar unidad_medida si cambió
  if ('unidad_medida' in camposModificados) {
    if (!producto.unidad_medida?.trim()) {
      errores.unidad_medida = 'La unidad de medida no puede quedar vacía';
    } else if (unidadesValidas && !unidadesValidas.includes(producto.unidad_medida.toUpperCase())) {
      errores.unidad_medida = 'Unidad no válida según catálogo del servidor';
    }
  }
  
  // Validar stock_minimo si cambió
  if ('stock_minimo' in camposModificados) {
    const stockMin = Number(producto.stock_minimo);
    if (isNaN(stockMin) || stockMin < 0) {
      errores.stock_minimo = 'El stock mínimo debe ser un número no negativo';
    }
  }
  
  // Warning si se está desactivando producto con stock
  if ('activo' in camposModificados && !producto.activo) {
    const stockActual = getStockProducto(productoOriginal);
    if (stockActual > 0) {
      warnings.push(`Este producto tiene ${stockActual} unidades en stock. Desactivarlo no afecta el inventario pero lo oculta de búsquedas.`);
    }
  }
  
  const valido = Object.keys(errores).length === 0;
  validationMetrics.record('producto_edicion', valido, valido ? null : errores);
  
  return {
    valido,
    errores,
    warnings,
    camposModificados: Object.keys(camposModificados),
  };
};

// ============================================================================
// FLUJO: REQUISICIONES
// ============================================================================

/**
 * Estados del flujo V2 de requisiciones
 */
export const ESTADOS_FLUJO_V2 = {
  BORRADOR: 'borrador',
  PENDIENTE_ADMIN: 'pendiente_admin',
  PENDIENTE_DIRECTOR: 'pendiente_director',
  ENVIADA: 'enviada',
  EN_REVISION: 'en_revision',
  AUTORIZADA: 'autorizada',
  EN_SURTIDO: 'en_surtido',
  SURTIDA: 'surtida',
  ENTREGADA: 'entregada',
  RECHAZADA: 'rechazada',
  VENCIDA: 'vencida',
  CANCELADA: 'cancelada',
  DEVUELTA: 'devuelta',
};

/**
 * Roles y sus acciones permitidas por estado
 */
export const ACCIONES_POR_ROL = {
  ADMIN: {
    borrador: ['enviar', 'editar', 'eliminar'],
    pendiente_admin: ['aprobar', 'rechazar', 'devolver'],
    pendiente_director: ['ver'],
    enviada: ['aprobar', 'rechazar', 'devolver'],
    en_revision: ['aprobar', 'rechazar'],
    autorizada: ['surtir', 'cancelar'],
    en_surtido: ['completar_surtido', 'cancelar'],
    surtida: ['entregar', 'cancelar'],
    entregada: ['ver'],
    rechazada: ['ver', 'reabrir'],
    cancelada: ['ver'],
    devuelta: ['ver', 'editar', 'reenviar'],
  },
  FARMACIA: {
    borrador: ['enviar', 'editar', 'eliminar'],
    pendiente_admin: ['ver'],
    enviada: ['ver'],
    autorizada: ['surtir'],
    en_surtido: ['completar_surtido'],
    surtida: ['entregar'],
    entregada: ['ver'],
  },
  CENTRO: {
    borrador: ['enviar', 'editar', 'eliminar'],
    pendiente_admin: ['ver', 'cancelar'],
    enviada: ['ver', 'cancelar'],
    autorizada: ['ver'],
    en_surtido: ['ver'],
    surtida: ['confirmar_recepcion'],
    entregada: ['ver'],
    rechazada: ['ver', 'editar_y_reenviar'],
    devuelta: ['editar', 'reenviar', 'cancelar'],
  },
  VISTA: {
    // Solo lectura en todos los estados
    borrador: ['ver'],
    pendiente_admin: ['ver'],
    enviada: ['ver'],
    autorizada: ['ver'],
    surtida: ['ver'],
    entregada: ['ver'],
  },
};

/**
 * ISS-004 FIX: Valida una requisición antes de enviar
 * @param {Object} requisicion - Datos de la requisición
 * @param {Object} options - Opciones
 * @returns {{ valido: boolean, errores: Object, warnings: Array }}
 */
export const validarRequisicionEnvio = (requisicion, options = {}) => {
  const { verificarStock = true, productos = [] } = options;
  const errores = {};
  const warnings = [];
  
  // Validar que tenga detalles
  if (!requisicion.detalles?.length) {
    errores.detalles = 'La requisición debe tener al menos un producto';
  } else {
    // Validar cada detalle
    for (let i = 0; i < requisicion.detalles.length; i++) {
      const detalle = requisicion.detalles[i];
      
      if (!detalle.producto_id) {
        errores[`detalle_${i}_producto`] = `Línea ${i + 1}: debe seleccionar un producto`;
      }
      
      const cantidad = Number(detalle.cantidad_solicitada);
      if (isNaN(cantidad) || cantidad <= 0) {
        errores[`detalle_${i}_cantidad`] = `Línea ${i + 1}: la cantidad debe ser mayor a 0`;
      }
      
      // ISS-001 FIX: Verificar stock si está habilitado
      if (verificarStock && detalle.producto_id) {
        const producto = productos.find(p => p.id === detalle.producto_id);
        if (producto) {
          const stockDisponible = getStockProducto(producto, { 
            endpoint: 'validarRequisicionEnvio',
            strict: false 
          });
          
          if (stockDisponible < cantidad) {
            warnings.push(
              `Línea ${i + 1} (${producto.clave || producto.nombre}): ` +
              `Stock disponible (${stockDisponible}) menor que solicitado (${cantidad})`
            );
          }
        }
      }
    }
    
    // Validar duplicados
    const productosIds = requisicion.detalles.map(d => d.producto_id).filter(Boolean);
    const duplicados = productosIds.filter((id, idx) => productosIds.indexOf(id) !== idx);
    if (duplicados.length > 0) {
      errores.duplicados = 'Hay productos duplicados en la requisición';
    }
  }
  
  // Validar lugar de entrega
  if (!requisicion.lugar_entrega?.trim()) {
    errores.lugar_entrega = 'El lugar de entrega es obligatorio';
  }
  
  const valido = Object.keys(errores).length === 0;
  validationMetrics.record('requisicion_envio', valido, valido ? null : errores);
  
  return {
    valido,
    errores,
    warnings,
  };
};

/**
 * ISS-004 FIX: Valida transición de estado de requisición
 * @param {string} estadoActual - Estado actual
 * @param {string} nuevoEstado - Estado destino
 * @param {string} rol - Rol del usuario
 * @returns {{ valido: boolean, error: string|null, accionRequerida: string|null }}
 */
export const validarTransicionRequisicion = (estadoActual, nuevoEstado, rol) => {
  // ISS-SEC FIX: Mapear estado destino a acción correspondiente ANTES de validar
  // esTransicionValidaV2 espera una ACCIÓN, no un estado destino
  const MAPA_ESTADO_A_ACCION = {
    'pendiente_admin': 'enviar',
    'pendiente_director': 'autorizarAdmin',
    'enviada': 'autorizarDirector',
    'en_revision': 'recibirFarmacia',
    'autorizada': 'autorizarFarmacia',
    'en_surtido': 'surtir',
    'surtida': 'surtir',
    'entregada': 'confirmarEntrega',
    'recibida': 'marcarRecibida',
    'rechazada': 'rechazar',
    'cancelada': 'cancelar',
    'devuelta': 'devolver',
  };
  
  const accionRequerida = MAPA_ESTADO_A_ACCION[nuevoEstado?.toLowerCase()];
  
  // ISS-SEC FIX: Si no hay acción mapeada, la transición no es válida
  if (!accionRequerida) {
    validationMetrics.record('transition', false, { estadoActual, nuevoEstado, rol, error: 'estado_destino_desconocido' });
    return {
      valido: false,
      error: `Estado destino "${nuevoEstado}" no es válido`,
      accionRequerida: null,
    };
  }
  
  // ISS-SEC FIX: Validar usando la ACCIÓN, no el estado destino
  const transicionValida = esTransicionValidaV2(estadoActual, accionRequerida);
  
  if (!transicionValida) {
    validationMetrics.record('transition', false, { estadoActual, nuevoEstado, rol, accionRequerida });
    return {
      valido: false,
      error: `No se puede ejecutar "${accionRequerida}" desde estado "${estadoActual}"`,
      accionRequerida,
    };
  }
  
  // Verificar permisos del rol
  const accionesPermitidas = ACCIONES_POR_ROL[rol?.toUpperCase()]?.[estadoActual] || [];
  
  if (accionRequerida && !accionesPermitidas.includes(accionRequerida)) {
    validationMetrics.record('transition', false, { estadoActual, nuevoEstado, rol, accionRequerida });
    return {
      valido: false,
      error: `El rol ${rol} no puede realizar la acción "${accionRequerida}" en estado "${estadoActual}"`,
      accionRequerida,
    };
  }
  
  validationMetrics.record('transition', true);
  return {
    valido: true,
    error: null,
    accionRequerida,
  };
};

/**
 * ISS-004 FIX: Valida datos para surtido de requisición
 * @param {Object} requisicion - Requisición a surtir
 * @param {Array} surtido - Datos de surtido [{detalle_id, cantidad, lote_id}]
 * @param {Array} lotes - Lotes disponibles
 * @returns {{ valido: boolean, errores: Array, detallesSurtido: Array }}
 */
export const validarSurtidoRequisicion = (requisicion, surtido, lotes) => {
  const errores = [];
  const detallesSurtido = [];
  
  if (!requisicion?.detalles?.length) {
    errores.push('La requisición no tiene detalles para surtir');
    return { valido: false, errores, detallesSurtido };
  }
  
  for (const item of surtido) {
    const detalle = requisicion.detalles.find(d => d.id === item.detalle_id);
    if (!detalle) {
      errores.push(`Detalle ${item.detalle_id} no encontrado en la requisición`);
      continue;
    }
    
    const cantidadSurtir = Number(item.cantidad);
    if (isNaN(cantidadSurtir) || cantidadSurtir <= 0) {
      errores.push(`${detalle.producto_nombre || 'Producto'}: cantidad a surtir inválida`);
      continue;
    }
    
    // Verificar que no se surta más de lo aprobado
    const cantidadPendiente = (detalle.cantidad_aprobada ?? detalle.cantidad_solicitada) - (detalle.cantidad_surtida || 0);
    if (cantidadSurtir > cantidadPendiente) {
      errores.push(
        `${detalle.producto_nombre || 'Producto'}: cantidad a surtir (${cantidadSurtir}) ` +
        `excede pendiente (${cantidadPendiente})`
      );
      continue;
    }
    
    // Verificar lote
    if (item.lote_id) {
      const lote = lotes.find(l => l.id === item.lote_id);
      if (!lote) {
        errores.push(`${detalle.producto_nombre || 'Producto'}: lote no encontrado`);
        continue;
      }
      
      if (lote.cantidad_actual < cantidadSurtir) {
        errores.push(
          `${detalle.producto_nombre || 'Producto'}: lote ${lote.numero_lote} tiene ` +
          `stock insuficiente (${lote.cantidad_actual} < ${cantidadSurtir})`
        );
        validationMetrics.record('stock', false, { lote: lote.numero_lote, requerido: cantidadSurtir, disponible: lote.cantidad_actual });
        continue;
      }
      
      // Verificar caducidad
      if (lote.fecha_caducidad) {
        const caducidad = new Date(lote.fecha_caducidad);
        const hoy = new Date();
        if (caducidad < hoy) {
          errores.push(`${detalle.producto_nombre || 'Producto'}: lote ${lote.numero_lote} está vencido`);
          continue;
        }
      }
    }
    
    detallesSurtido.push({
      detalle_id: item.detalle_id,
      producto_id: detalle.producto_id,
      cantidad: cantidadSurtir,
      lote_id: item.lote_id,
    });
  }
  
  const valido = errores.length === 0 && detallesSurtido.length > 0;
  validationMetrics.record('surtido', valido, valido ? null : errores);
  
  return { valido, errores, detallesSurtido };
};

// ============================================================================
// FLUJO: LOTES
// ============================================================================

/**
 * ISS-004 FIX: Valida un lote para creación
 */
export const validarLoteCreacion = (lote, options = {}) => {
  const { productosDisponibles = [] } = options;
  const errores = {};
  
  // Número de lote obligatorio
  if (!lote.numero_lote?.trim()) {
    errores.numero_lote = 'El número de lote es obligatorio';
  } else if (!/^[A-Za-z0-9\-]+$/.test(lote.numero_lote)) {
    errores.numero_lote = 'El número de lote solo puede contener letras, números y guiones';
  }
  
  // Producto obligatorio
  if (!lote.producto_id) {
    errores.producto_id = 'Debe seleccionar un producto';
  } else if (productosDisponibles.length && !productosDisponibles.find(p => p.id === lote.producto_id)) {
    errores.producto_id = 'Producto no válido';
  }
  
  // Cantidad inicial
  const cantidad = Number(lote.cantidad_inicial);
  if (isNaN(cantidad) || cantidad <= 0) {
    errores.cantidad_inicial = 'La cantidad inicial debe ser mayor a 0';
  } else if (!Number.isInteger(cantidad)) {
    errores.cantidad_inicial = 'La cantidad debe ser un número entero';
  }
  
  // Fecha de caducidad
  if (!lote.fecha_caducidad) {
    errores.fecha_caducidad = 'La fecha de caducidad es obligatoria';
  } else {
    const caducidad = new Date(lote.fecha_caducidad);
    const hoy = new Date();
    if (caducidad < hoy) {
      errores.fecha_caducidad = 'La fecha de caducidad no puede ser pasada';
    }
  }
  
  const valido = Object.keys(errores).length === 0;
  return { valido, errores };
};

// ============================================================================
// UTILIDADES DE EXPORTACIÓN
// ============================================================================

export default {
  // Productos
  validarProductoCreacion,
  validarProductoEdicion,
  PRODUCTO_RULES,
  
  // Requisiciones
  validarRequisicionEnvio,
  validarTransicionRequisicion,
  validarSurtidoRequisicion,
  ESTADOS_FLUJO_V2,
  ACCIONES_POR_ROL,
  
  // Lotes
  validarLoteCreacion,
  
  // Métricas
  getValidationMetrics,
  resetValidationMetrics,
};
