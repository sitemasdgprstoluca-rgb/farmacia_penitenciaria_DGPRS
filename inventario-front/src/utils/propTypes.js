/**
 * ISS-004 FIX: PropTypes centralizados para entidades del sistema
 * 
 * Este archivo define los shapes de PropTypes para las principales
 * entidades, garantizando consistencia en la validación de props
 * a través de toda la aplicación.
 */
import PropTypes from 'prop-types';

// ============================================================================
// USUARIO
// ============================================================================

export const UsuarioPropType = PropTypes.shape({
  id: PropTypes.number.isRequired,
  username: PropTypes.string.isRequired,
  email: PropTypes.string,
  nombre: PropTypes.string,
  apellido: PropTypes.string,
  rol: PropTypes.oneOf(['admin', 'farmaceutico', 'medico', 'enfermero', 'almacenista']),
  activo: PropTypes.bool,
  centro_id: PropTypes.number,
  centro_nombre: PropTypes.string,
  permisos: PropTypes.arrayOf(PropTypes.string),
});

export const UsuarioResumenPropType = PropTypes.shape({
  id: PropTypes.number.isRequired,
  username: PropTypes.string.isRequired,
  nombre: PropTypes.string,
});

// ============================================================================
// PRODUCTO
// ============================================================================

export const ProductoPropType = PropTypes.shape({
  id: PropTypes.number.isRequired,
  clave: PropTypes.string.isRequired,
  nombre: PropTypes.string.isRequired,
  descripcion: PropTypes.string,
  unidad_medida: PropTypes.string,
  categoria: PropTypes.string,
  stock_minimo: PropTypes.number,
  stock_actual: PropTypes.number,
  sustancia_activa: PropTypes.string,
  presentacion: PropTypes.string,
  concentracion: PropTypes.string,
  via_administracion: PropTypes.string,
  requiere_receta: PropTypes.bool,
  es_controlado: PropTypes.bool,
  activo: PropTypes.bool,
  imagen: PropTypes.string,
  created_at: PropTypes.string,
  updated_at: PropTypes.string,
});

export const ProductoResumenPropType = PropTypes.shape({
  id: PropTypes.number.isRequired,
  clave: PropTypes.string.isRequired,
  nombre: PropTypes.string.isRequired,
  stock_actual: PropTypes.number,
  unidad_medida: PropTypes.string,
});

// ============================================================================
// LOTE
// ============================================================================

export const LotePropType = PropTypes.shape({
  id: PropTypes.number.isRequired,
  producto_id: PropTypes.number,
  numero_lote: PropTypes.string.isRequired,
  cantidad_inicial: PropTypes.number,
  cantidad_actual: PropTypes.number,
  fecha_caducidad: PropTypes.string,
  fecha_fabricacion: PropTypes.string, // Representa fecha de entrega del lote
  estado: PropTypes.oneOf(['disponible', 'agotado', 'vencido', 'por_vencer', 'bloqueado', 'retirado']),
  activo: PropTypes.bool,
  marca: PropTypes.string,
  precio_unitario: PropTypes.number,
});

// ============================================================================
// REQUISICION
// ============================================================================

export const EstadoRequisicionPropType = PropTypes.oneOf([
  'borrador',
  'pendiente',
  'aprobada',
  'en_proceso',
  'surtida_parcial',
  'surtida',
  'rechazada',
  'cancelada',
]);

export const DetalleRequisicionPropType = PropTypes.shape({
  id: PropTypes.number,
  producto_id: PropTypes.number,
  producto_clave: PropTypes.string,
  producto_nombre: PropTypes.string,
  cantidad_solicitada: PropTypes.number.isRequired,
  cantidad_aprobada: PropTypes.number,
  cantidad_surtida: PropTypes.number,
  unidad_medida: PropTypes.string,
  observaciones: PropTypes.string,
});

export const RequisicionPropType = PropTypes.shape({
  id: PropTypes.number.isRequired,
  folio: PropTypes.string.isRequired,
  estado: EstadoRequisicionPropType.isRequired,
  fecha_creacion: PropTypes.string,
  fecha_aprobacion: PropTypes.string,
  fecha_surtido: PropTypes.string,
  solicitante_id: PropTypes.number,
  solicitante_nombre: PropTypes.string,
  aprobador_id: PropTypes.number,
  aprobador_nombre: PropTypes.string,
  lugar_entrega: PropTypes.string,
  observaciones: PropTypes.string,
  detalles: PropTypes.arrayOf(DetalleRequisicionPropType),
  centro_id: PropTypes.number,
  centro_nombre: PropTypes.string,
});

// ============================================================================
// MOVIMIENTO
// ============================================================================

export const TipoMovimientoPropType = PropTypes.oneOf([
  'entrada',
  'salida',
  'ajuste',
  'transferencia',
  'merma',
  'devolucion',
]);

export const MovimientoPropType = PropTypes.shape({
  id: PropTypes.number.isRequired,
  tipo: TipoMovimientoPropType.isRequired,
  cantidad: PropTypes.number.isRequired,
  lote_id: PropTypes.number,
  producto_id: PropTypes.number,
  fecha: PropTypes.string,
  referencia: PropTypes.string,
  observaciones: PropTypes.string,
  usuario_id: PropTypes.number,
  usuario_nombre: PropTypes.string,
});

// ============================================================================
// NOTIFICACION
// ============================================================================

export const NotificacionPropType = PropTypes.shape({
  id: PropTypes.oneOfType([PropTypes.number, PropTypes.string]).isRequired,
  tipo: PropTypes.string,
  mensaje: PropTypes.string,
  titulo: PropTypes.string,
  leida: PropTypes.bool,
  created_at: PropTypes.string,
  prioridad: PropTypes.oneOf(['baja', 'normal', 'alta', 'urgente']),
  enlace: PropTypes.string,
  data: PropTypes.object,
});

// ============================================================================
// CENTRO
// ============================================================================

export const CentroPropType = PropTypes.shape({
  id: PropTypes.number.isRequired,
  nombre: PropTypes.string.isRequired,
  codigo: PropTypes.string,
  direccion: PropTypes.string,
  telefono: PropTypes.string,
  activo: PropTypes.bool,
});

// ============================================================================
// PAGINACIÓN
// ============================================================================

export const PaginacionPropType = PropTypes.shape({
  page: PropTypes.number.isRequired,
  totalPages: PropTypes.number.isRequired,
  totalItems: PropTypes.number,
  pageSize: PropTypes.number,
  onPageChange: PropTypes.func.isRequired,
});

// ============================================================================
// FILTROS COMUNES
// ============================================================================

export const FiltrosProductoPropType = PropTypes.shape({
  search: PropTypes.string,
  categoria: PropTypes.string,
  nivelStock: PropTypes.string,
  activo: PropTypes.oneOf(['', 'true', 'false']),
});

export const FiltrosRequisicionPropType = PropTypes.shape({
  search: PropTypes.string,
  estado: PropTypes.string,
  fechaDesde: PropTypes.string,
  fechaHasta: PropTypes.string,
  solicitante: PropTypes.string,
  centro: PropTypes.string,
});

// ============================================================================
// CALLBACKS Y HANDLERS
// ============================================================================

export const CallbackPropTypes = {
  onSuccess: PropTypes.func,
  onError: PropTypes.func,
  onCancel: PropTypes.func,
  onSubmit: PropTypes.func,
  onChange: PropTypes.func,
  onClick: PropTypes.func,
  onClose: PropTypes.func,
  onConfirm: PropTypes.func,
};

// ============================================================================
// ESTADOS DE CARGA
// ============================================================================

export const LoadStatePropType = PropTypes.oneOf(['idle', 'loading', 'success', 'error']);

// ============================================================================
// PERMISOS
// ============================================================================

export const PermisosPropType = PropTypes.shape({
  verProductos: PropTypes.bool,
  crearProductos: PropTypes.bool,
  editarProductos: PropTypes.bool,
  eliminarProductos: PropTypes.bool,
  verRequisiciones: PropTypes.bool,
  crearRequisicion: PropTypes.bool,
  aprobarRequisicion: PropTypes.bool,
  surtirRequisicion: PropTypes.bool,
  cancelarRequisicion: PropTypes.bool,
  verUsuarios: PropTypes.bool,
  crearUsuarios: PropTypes.bool,
  editarUsuarios: PropTypes.bool,
  verReportes: PropTypes.bool,
  verNotificaciones: PropTypes.bool,
  configurarTema: PropTypes.bool,
});

// ============================================================================
// TEMA / UI
// ============================================================================

export const TemaPropType = PropTypes.shape({
  id: PropTypes.number,
  nombre: PropTypes.string,
  colores: PropTypes.shape({
    primario: PropTypes.string,
    secundario: PropTypes.string,
    fondo: PropTypes.string,
    texto: PropTypes.string,
    exito: PropTypes.string,
    error: PropTypes.string,
    advertencia: PropTypes.string,
  }),
  logo_header: PropTypes.string,
  logo_login: PropTypes.string,
});

// ============================================================================
// EXPORTACIÓN COMBINADA
// ============================================================================

export default {
  // Usuarios
  UsuarioPropType,
  UsuarioResumenPropType,
  // Productos
  ProductoPropType,
  ProductoResumenPropType,
  // Lotes
  LotePropType,
  // Requisiciones
  RequisicionPropType,
  DetalleRequisicionPropType,
  EstadoRequisicionPropType,
  // Movimientos
  MovimientoPropType,
  TipoMovimientoPropType,
  // Notificaciones
  NotificacionPropType,
  // Centros
  CentroPropType,
  // UI/Navegación
  PaginacionPropType,
  LoadStatePropType,
  // Filtros
  FiltrosProductoPropType,
  FiltrosRequisicionPropType,
  // Permisos
  PermisosPropType,
  // Tema
  TemaPropType,
  // Callbacks
  CallbackPropTypes,
};
