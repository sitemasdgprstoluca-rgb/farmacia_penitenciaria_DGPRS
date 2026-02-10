/**
 * Mocks compartidos para tests de Dispensaciones, Caja Chica y Seguridad E2E
 *
 * Fábricas de datos, usuarios por rol, permisos por rol, y helpers
 * para simular respuestas de API y estados de la aplicación.
 */
import { vi } from 'vitest';

// ───────────────────────── Centros ─────────────────────────
export const CENTRO_A = { id: 1, nombre: 'Centro Penitenciario Norte' };
export const CENTRO_B = { id: 2, nombre: 'Centro Penitenciario Sur' };
export const CENTRO_FARMACIA = { id: 99, nombre: 'Farmacia Central' };

// ───────────────────────── Usuarios por Rol ─────────────────────────
export const createUsuarioCentro = (centro = CENTRO_A, overrides = {}) => ({
  id: 10,
  username: 'medico_centro',
  first_name: 'Dr. Centro',
  last_name: 'Test',
  email: 'medico@centro.test',
  rol: 'medico',
  rol_efectivo: 'medico',
  is_superuser: false,
  is_staff: false,
  centro: { id: centro.id, nombre: centro.nombre },
  centro_id: centro.id,
  permisos: {
    verDispensaciones: true,
    crearDispensacion: true,
    editarDispensacion: true,
    dispensar: true,
    cancelarDispensacion: true,
    verComprasCajaChica: true,
    crearCompraCajaChica: true,
    verInventarioCajaChica: true,
    verPacientes: true,
    crearPaciente: true,
  },
  ...overrides,
});

export const createUsuarioAdminCentro = (centro = CENTRO_A, overrides = {}) => ({
  id: 11,
  username: 'admin_centro',
  first_name: 'Admin',
  last_name: 'Centro',
  email: 'admin@centro.test',
  rol: 'administrador_centro',
  rol_efectivo: 'administrador_centro',
  is_superuser: false,
  is_staff: false,
  centro: { id: centro.id, nombre: centro.nombre },
  centro_id: centro.id,
  permisos: {
    verDispensaciones: true,
    crearDispensacion: true,
    editarDispensacion: true,
    dispensar: true,
    cancelarDispensacion: true,
    verComprasCajaChica: true,
    crearCompraCajaChica: true,
    verInventarioCajaChica: true,
    verPacientes: true,
    crearPaciente: true,
  },
  ...overrides,
});

export const createUsuarioDirectorCentro = (centro = CENTRO_A, overrides = {}) => ({
  id: 12,
  username: 'director_centro',
  first_name: 'Director',
  last_name: 'Centro',
  email: 'director@centro.test',
  rol: 'director_centro',
  rol_efectivo: 'director_centro',
  is_superuser: false,
  is_staff: false,
  centro: { id: centro.id, nombre: centro.nombre },
  centro_id: centro.id,
  permisos: {
    verDispensaciones: true,
    verComprasCajaChica: true,
    verInventarioCajaChica: true,
    verPacientes: true,
  },
  ...overrides,
});

export const createUsuarioFarmacia = (overrides = {}) => ({
  id: 20,
  username: 'farmacia_user',
  first_name: 'Farmacia',
  last_name: 'User',
  email: 'farmacia@test.com',
  rol: 'farmacia',
  rol_efectivo: 'farmacia',
  is_superuser: false,
  is_staff: false,
  centro: null,
  centro_id: null,
  permisos: {
    verDispensaciones: true,
    verComprasCajaChica: true,
    verInventarioCajaChica: true,
    verPacientes: true,
  },
  ...overrides,
});

export const createUsuarioAdmin = (overrides = {}) => ({
  id: 1,
  username: 'admin',
  first_name: 'Super',
  last_name: 'Admin',
  email: 'admin@test.com',
  rol: 'admin',
  rol_efectivo: 'admin',
  is_superuser: true,
  is_staff: true,
  centro: null,
  centro_id: null,
  permisos: {
    verDispensaciones: true,
    crearDispensacion: true,
    editarDispensacion: true,
    dispensar: true,
    cancelarDispensacion: true,
    verComprasCajaChica: true,
    crearCompraCajaChica: true,
    verInventarioCajaChica: true,
    verPacientes: true,
    crearPaciente: true,
    esSuperusuario: true,
  },
  ...overrides,
});

export const createUsuarioVistaOnly = (overrides = {}) => ({
  id: 30,
  username: 'vista_user',
  first_name: 'Vista',
  last_name: 'Solo',
  email: 'vista@test.com',
  rol: 'vista',
  rol_efectivo: 'vista',
  is_superuser: false,
  is_staff: false,
  centro: null,
  centro_id: null,
  permisos: {
    verDispensaciones: true,
    verComprasCajaChica: true,
    verInventarioCajaChica: true,
    verPacientes: true,
  },
  ...overrides,
});

// ───────────────────────── Permisos por Rol (para mock usePermissions) ─────
export const buildPermissions = (user) => ({
  user,
  loading: false,
  error: null,
  permisos: user.permisos,
  verificarPermiso: vi.fn((key) => !!user.permisos[key]),
  getRolPrincipal: vi.fn(() => {
    const r = (user.rol_efectivo || user.rol || '').toLowerCase();
    if (['admin', 'superuser'].includes(r) || user.is_superuser) return 'ADMIN';
    if (['farmacia', 'admin_farmacia'].includes(r)) return 'FARMACIA';
    if (['medico', 'administrador_centro', 'director_centro', 'centro'].includes(r)) return 'CENTRO';
    return 'VISTA';
  }),
  recargarUsuario: vi.fn(),
  logout: vi.fn(),
});

// ───────────────────────── Productos ─────────────────────────
export const createProducto = (overrides = {}) => ({
  id: 1,
  clave: 'MED-001',
  descripcion: 'Paracetamol 500mg',
  unidad_medida: 'TABLETA',
  stock_minimo: 10,
  stock_actual: 100,
  activo: true,
  ...overrides,
});

export const PRODUCTOS_LIST = [
  createProducto({ id: 1, clave: 'MED-001', descripcion: 'Paracetamol 500mg' }),
  createProducto({ id: 2, clave: 'MED-002', descripcion: 'Ibuprofeno 400mg' }),
  createProducto({ id: 3, clave: 'MED-003', descripcion: 'Amoxicilina 500mg', stock_actual: 0 }),
];

// ───────────────────────── Lotes ─────────────────────────
export const createLote = (overrides = {}) => ({
  id: 1,
  numero_lote: 'LOTE-2025-001',
  producto: 1,
  producto_nombre: 'Paracetamol 500mg',
  fecha_caducidad: '2026-12-31',
  cantidad_inicial: 100,
  cantidad_actual: 50,
  ubicacion: 'A-1-1',
  centro: CENTRO_A.id,
  activo: true,
  ...overrides,
});

// ───────────────────────── Pacientes ─────────────────────────
export const createPaciente = (overrides = {}) => ({
  id: 1,
  nombre: 'Juan',
  apellido_paterno: 'Pérez',
  apellido_materno: 'García',
  numero_expediente: 'EXP-001',
  centro: CENTRO_A.id,
  centro_nombre: CENTRO_A.nombre,
  activo: true,
  ...overrides,
});

// ───────────────────────── Dispensaciones ─────────────────────────
export const ESTADOS_DISPENSACION = {
  PENDIENTE: 'pendiente',
  DISPENSADA: 'dispensada',
  CANCELADA: 'cancelada',
};

export const TIPOS_DISPENSACION = [
  { value: 'regular', label: 'Regular' },
  { value: 'urgente', label: 'Urgente' },
  { value: 'controlada', label: 'Controlada' },
];

export const createDispensacion = (overrides = {}) => ({
  id: 1,
  folio: 'DISP-1-20250101-abc123',
  paciente: 1,
  paciente_nombre: 'Juan Pérez García',
  centro: CENTRO_A.id,
  centro_nombre: CENTRO_A.nombre,
  tipo_dispensacion: 'regular',
  estado: 'pendiente',
  fecha_dispensacion: null,
  fecha_creacion: '2025-01-15T10:00:00Z',
  usuario_creador: 10,
  usuario_creador_nombre: 'Dr. Centro Test',
  detalles: [
    {
      id: 1,
      producto: 1,
      producto_nombre: 'Paracetamol 500mg',
      lote: 1,
      lote_numero: 'LOTE-2025-001',
      cantidad_prescrita: 10,
      cantidad_dispensada: 0,
      dosis: '1 tableta',
      frecuencia: 'cada 8 horas',
      duracion_tratamiento: '5 días',
      notas: '',
    },
  ],
  ...overrides,
});

export const createDispensacionDispensada = (overrides = {}) =>
  createDispensacion({
    id: 2,
    folio: 'DISP-1-20250115-def456',
    estado: 'dispensada',
    fecha_dispensacion: '2025-01-15T14:00:00Z',
    detalles: [
      {
        id: 2,
        producto: 1,
        producto_nombre: 'Paracetamol 500mg',
        lote: 1,
        lote_numero: 'LOTE-2025-001',
        cantidad_prescrita: 10,
        cantidad_dispensada: 10,
        dosis: '1 tableta',
        frecuencia: 'cada 8 horas',
        duracion_tratamiento: '5 días',
        notas: '',
      },
    ],
    ...overrides,
  });

export const createDispensacionCancelada = (overrides = {}) =>
  createDispensacion({
    id: 3,
    folio: 'DISP-1-20250115-ghi789',
    estado: 'cancelada',
    motivo_cancelacion: 'Paciente trasladado',
    ...overrides,
  });

// ───────────────────────── Caja Chica (Compras) ─────────────────────────
export const ESTADOS_COMPRA = {
  PENDIENTE: 'pendiente',
  ENVIADA_FARMACIA: 'enviada_farmacia',
  SIN_STOCK_FARMACIA: 'sin_stock_farmacia',
  RECHAZADA_FARMACIA: 'rechazada_farmacia',
  ENVIADA_ADMIN: 'enviada_admin',
  AUTORIZADA_ADMIN: 'autorizada_admin',
  ENVIADA_DIRECTOR: 'enviada_director',
  AUTORIZADA: 'autorizada',
  COMPRADA: 'comprada',
  RECIBIDA: 'recibida',
  CANCELADA: 'cancelada',
  RECHAZADA: 'rechazada',
  DEVUELTA: 'devuelta',
};

export const createCompra = (overrides = {}) => ({
  id: 1,
  folio: 'CC-1-20250115-aaa111',
  centro: CENTRO_A.id,
  centro_nombre: CENTRO_A.nombre,
  motivo_compra: 'Medicamento agotado en farmacia central',
  estado: 'pendiente',
  total: 500.0,
  fecha_creacion: '2025-01-15T09:00:00Z',
  usuario_creador: 10,
  usuario_creador_nombre: 'Dr. Centro Test',
  proveedor: null,
  numero_factura: null,
  observaciones: '',
  detalles: [
    {
      id: 1,
      descripcion_producto: 'Paracetamol 500mg (genérico)',
      cantidad_solicitada: 50,
      precio_unitario: 10.0,
      importe: 500.0,
    },
  ],
  ...overrides,
});

// ───────────────────────── Inventario Caja Chica ─────
export const createInventarioItem = (overrides = {}) => ({
  id: 1,
  producto_nombre: 'Paracetamol 500mg',
  descripcion: 'Paracetamol genérico',
  centro: CENTRO_A.id,
  centro_nombre: CENTRO_A.nombre,
  cantidad_actual: 30,
  cantidad_minima: 5,
  unidad_medida: 'TABLETA',
  ...overrides,
});

// ───────────────────────── Historial ─────────────────────────
export const createHistorial = (overrides = {}) => ({
  id: 1,
  accion: 'creacion',
  descripcion: 'Dispensación creada',
  usuario: 10,
  usuario_nombre: 'Dr. Centro Test',
  fecha: '2025-01-15T10:00:00Z',
  ...overrides,
});

// ───────────────────────── API Error Responses ─────────────────────────
export const API_ERRORS = {
  unauthorized_401: {
    response: { status: 401, data: { detail: 'Token inválido o expirado.' } },
    message: 'Request failed with status code 401',
  },
  forbidden_403: {
    response: { status: 403, data: { detail: 'No tiene permisos para esta acción.' } },
    message: 'Request failed with status code 403',
  },
  conflict_409: {
    response: {
      status: 409,
      data: { detail: 'El recurso ha sido modificado por otro usuario.' },
    },
    message: 'Request failed with status code 409',
  },
  validation_422: {
    response: {
      status: 422,
      data: {
        detail: 'Los datos enviados no son válidos.',
        errors: { cantidad_prescrita: ['Este campo es requerido.'] },
      },
    },
    message: 'Request failed with status code 422',
  },
  validation_422_missing_paciente: {
    response: {
      status: 422,
      data: {
        detail: 'Datos inválidos.',
        errors: { paciente: ['Este campo es requerido.'] },
      },
    },
    message: 'Request failed with status code 422',
  },
  validation_422_invalid_quantity: {
    response: {
      status: 422,
      data: {
        detail: 'Cantidad debe ser un número entero positivo.',
        errors: { cantidad_prescrita: ['Ingrese un número entero válido.'] },
      },
    },
    message: 'Request failed with status code 422',
  },
  validation_422_monto_cero: {
    response: {
      status: 422,
      data: {
        detail: 'El monto debe ser mayor a cero.',
        errors: { total: ['Asegúrese de que este valor sea mayor que 0.'] },
      },
    },
    message: 'Request failed with status code 422',
  },
  validation_422_motivo_required: {
    response: {
      status: 422,
      data: {
        detail: 'El motivo de compra es requerido.',
        errors: { motivo_compra: ['Este campo es requerido.'] },
      },
    },
    message: 'Request failed with status code 422',
  },
  server_error_500: {
    response: { status: 500, data: { detail: 'Error interno del servidor.' } },
    message: 'Request failed with status code 500',
  },
  stock_conflict_dispensacion: {
    response: {
      status: 409,
      data: {
        error: 'No se pudo dispensar por falta de stock',
        detalles_error: [
          {
            producto: 'Paracetamol 500mg',
            lote: 'LOTE-2025-001',
            solicitado: 10,
            disponible: 3,
          },
        ],
        sugerencia: 'Edite la dispensación y ajuste las cantidades.',
      },
    },
    message: 'Request failed with status code 409',
  },
  saldo_insuficiente: {
    response: {
      status: 422,
      data: {
        detail: 'Saldo insuficiente en caja chica.',
        saldo_disponible: 150.0,
        monto_solicitado: 500.0,
      },
    },
    message: 'Request failed with status code 422',
  },
};

// ───────────────────────── API Mock Factories ─────────────────────────
export const createDispensacionesAPIMock = () => ({
  getAll: vi.fn().mockResolvedValue({ data: { results: [], count: 0 } }),
  getById: vi.fn().mockResolvedValue({ data: createDispensacion() }),
  create: vi.fn().mockResolvedValue({ data: createDispensacion() }),
  update: vi.fn().mockResolvedValue({ data: createDispensacion() }),
  delete: vi.fn().mockResolvedValue({ data: {} }),
  dispensar: vi.fn().mockResolvedValue({ data: createDispensacionDispensada() }),
  cancelar: vi.fn().mockResolvedValue({ data: createDispensacionCancelada() }),
  agregarDetalle: vi.fn().mockResolvedValue({ data: {} }),
  historial: vi.fn().mockResolvedValue({ data: [createHistorial()] }),
  exportarPdf: vi.fn().mockResolvedValue(new Blob(['pdf-content'])),
  exportarControlMensualCPRS: vi.fn().mockResolvedValue(new Blob(['pdf-content'])),
});

export const createComprasCajaChicaAPIMock = () => ({
  getAll: vi.fn().mockResolvedValue({ data: { results: [], count: 0 } }),
  getById: vi.fn().mockResolvedValue({ data: createCompra() }),
  create: vi.fn().mockResolvedValue({ data: createCompra() }),
  update: vi.fn().mockResolvedValue({ data: createCompra() }),
  delete: vi.fn().mockResolvedValue({ data: {} }),
  enviarFarmacia: vi.fn().mockResolvedValue({ data: {} }),
  confirmarSinStock: vi.fn().mockResolvedValue({ data: {} }),
  rechazarTieneStock: vi.fn().mockResolvedValue({ data: {} }),
  enviarAdmin: vi.fn().mockResolvedValue({ data: {} }),
  autorizarAdmin: vi.fn().mockResolvedValue({ data: {} }),
  enviarDirector: vi.fn().mockResolvedValue({ data: {} }),
  autorizarDirector: vi.fn().mockResolvedValue({ data: {} }),
  rechazar: vi.fn().mockResolvedValue({ data: {} }),
  devolver: vi.fn().mockResolvedValue({ data: {} }),
  autorizar: vi.fn().mockResolvedValue({ data: {} }),
  registrarCompra: vi.fn().mockResolvedValue({ data: {} }),
  recibir: vi.fn().mockResolvedValue({ data: {} }),
  cancelar: vi.fn().mockResolvedValue({ data: {} }),
  agregarDetalle: vi.fn().mockResolvedValue({ data: {} }),
  resumen: vi.fn().mockResolvedValue({
    data: { saldo_disponible: 5000, total_egresos: 1500, total_ingresos: 6500 },
  }),
});

export const createInventarioCajaChicaAPIMock = () => ({
  getAll: vi.fn().mockResolvedValue({ data: { results: [], count: 0 } }),
  getById: vi.fn().mockResolvedValue({ data: createInventarioItem() }),
  create: vi.fn().mockResolvedValue({ data: createInventarioItem() }),
  update: vi.fn().mockResolvedValue({ data: createInventarioItem() }),
  delete: vi.fn().mockResolvedValue({ data: {} }),
  registrarSalida: vi.fn().mockResolvedValue({ data: {} }),
  ajustar: vi.fn().mockResolvedValue({ data: {} }),
  resumen: vi.fn().mockResolvedValue({
    data: { total_items: 10, items_con_stock: 8, items_sin_stock: 2 },
  }),
  exportar: vi.fn().mockResolvedValue(new Blob(['csv-content'])),
});

export const createMovimientosCajaChicaAPIMock = () => ({
  getAll: vi.fn().mockResolvedValue({ data: { results: [], count: 0 } }),
  getById: vi.fn().mockResolvedValue({ data: {} }),
  porInventario: vi.fn().mockResolvedValue({ data: [] }),
});

export const createCentrosAPIMock = () => ({
  getAll: vi.fn().mockResolvedValue({
    data: { results: [CENTRO_A, CENTRO_B], count: 2 },
  }),
});

export const createProductosAPIMock = () => ({
  getAll: vi.fn().mockResolvedValue({
    data: { results: PRODUCTOS_LIST, count: PRODUCTOS_LIST.length },
  }),
});

export const createLotesAPIMock = () => ({
  getAll: vi.fn().mockResolvedValue({
    data: {
      results: [
        createLote({ id: 1, cantidad_actual: 50 }),
        createLote({ id: 2, numero_lote: 'LOTE-2025-002', cantidad_actual: 30 }),
      ],
      count: 2,
    },
  }),
});

export const createPacientesAPIMock = () => ({
  getAll: vi.fn().mockResolvedValue({ data: { results: [createPaciente()], count: 1 } }),
  autocomplete: vi.fn().mockResolvedValue({ data: [createPaciente()] }),
  getById: vi.fn().mockResolvedValue({ data: createPaciente() }),
  create: vi.fn().mockResolvedValue({ data: createPaciente() }),
  update: vi.fn().mockResolvedValue({ data: createPaciente() }),
  delete: vi.fn().mockResolvedValue({ data: {} }),
  historialDispensaciones: vi.fn().mockResolvedValue({ data: [] }),
  exportarExcel: vi.fn().mockResolvedValue(new Blob()),
  importarExcel: vi.fn().mockResolvedValue({ data: {} }),
});

export const createDescargarArchivoMock = () => vi.fn();
