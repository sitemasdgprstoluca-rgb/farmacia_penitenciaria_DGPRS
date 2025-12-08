import { useState, useEffect, useCallback } from 'react';
import { donacionesAPI, productosAPI, centrosAPI, lotesAPI } from '../services/api';
import { toast } from 'react-hot-toast';
import {
  FaPlus,
  FaEdit,
  FaTrash,
  FaEye,
  FaCheck,
  FaFilter,
  FaGift,
  FaChevronDown,
  FaTimes,
  FaSpinner,
  FaBuilding,
  FaUser,
  FaCalendar,
  FaBox,
  FaSearch,
} from 'react-icons/fa';
import PageHeader from '../components/PageHeader';
import { COLORS } from '../constants/theme';
import Pagination from '../components/Pagination';
import { usePermissions } from '../hooks/usePermissions';
import ConfirmModal from '../components/ConfirmModal';

const PAGE_SIZE = 15;

const ESTADOS_DONACION = {
  pendiente: { label: 'Pendiente', color: 'bg-yellow-100 text-yellow-800', icon: '⏳' },
  procesada: { label: 'Procesada', color: 'bg-green-100 text-green-800', icon: '✅' },
  cancelada: { label: 'Cancelada', color: 'bg-red-100 text-red-800', icon: '❌' },
};

const TIPOS_DONANTE = [
  { value: 'gobierno', label: 'Gobierno' },
  { value: 'ong', label: 'ONG' },
  { value: 'empresa', label: 'Empresa' },
  { value: 'particular', label: 'Particular' },
  { value: 'otro', label: 'Otro' },
];

const ESTADOS_PRODUCTO = [
  { value: 'nuevo', label: 'Nuevo' },
  { value: 'buen_estado', label: 'Buen Estado' },
  { value: 'dañado', label: 'Dañado' },
];

const Donaciones = () => {
  const { getRolPrincipal, permisos, user } = usePermissions();
  const rolPrincipal = getRolPrincipal();
  const esFarmaciaAdmin = ['ADMIN', 'FARMACIA'].includes(rolPrincipal) || permisos?.isSuperuser;

  // Permisos - Donaciones solo para ADMIN y FARMACIA
  const puede = {
    crear: esFarmaciaAdmin,
    editar: esFarmaciaAdmin,
    eliminar: esFarmaciaAdmin,
    procesar: esFarmaciaAdmin,
    ver: esFarmaciaAdmin || rolPrincipal === 'VISTA',
  };

  // Estados
  const [donaciones, setDonaciones] = useState([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [showDetalleModal, setShowDetalleModal] = useState(false);
  const [editingDonacion, setEditingDonacion] = useState(null);
  const [viewingDonacion, setViewingDonacion] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [confirmProcesar, setConfirmProcesar] = useState(null);

  // Paginación
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalDonaciones, setTotalDonaciones] = useState(0);

  // Filtros
  const [showFiltersMenu, setShowFiltersMenu] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [filtroEstado, setFiltroEstado] = useState('');
  const [filtroTipoDonante, setFiltroTipoDonante] = useState('');
  const [filtroCentro, setFiltroCentro] = useState('');
  const [filtroFechaDesde, setFiltroFechaDesde] = useState('');
  const [filtroFechaHasta, setFiltroFechaHasta] = useState('');

  // Catálogos
  const [productos, setProductos] = useState([]);
  const [centros, setCentros] = useState([]);
  const [lotes, setLotes] = useState([]);

  // Formulario
  const [formData, setFormData] = useState({
    numero: '',
    donante_nombre: '',
    donante_tipo: 'gobierno',
    donante_rfc: '',
    donante_direccion: '',
    donante_contacto: '',
    fecha_donacion: new Date().toISOString().split('T')[0],
    fecha_recepcion: new Date().toISOString().split('T')[0],
    centro_destino: '',
    notas: '',
    detalles: [],
  });

  // Detalle en edición
  const [detalleForm, setDetalleForm] = useState({
    producto: '',
    numero_lote: '',
    cantidad: '',
    fecha_caducidad: '',
    estado_producto: 'nuevo',
    notas: '',
  });

  const filtrosActivos = [searchTerm, filtroEstado, filtroTipoDonante, filtroCentro, filtroFechaDesde, filtroFechaHasta].filter(Boolean).length;

  // Cargar catálogos
  const cargarCatalogos = useCallback(async () => {
    try {
      const [prodRes, centrosRes] = await Promise.all([
        productosAPI.getAll({ page_size: 500, activo: true, ordering: 'descripcion' }),
        centrosAPI.getAll({ page_size: 100, activo: true, ordering: 'nombre' }),
      ]);
      setProductos(prodRes.data.results || prodRes.data || []);
      setCentros(centrosRes.data.results || centrosRes.data || []);
    } catch (err) {
      console.error('Error cargando catálogos:', err);
    }
  }, []);

  // Cargar donaciones
  const cargarDonaciones = useCallback(async () => {
    setLoading(true);
    try {
      const params = {
        page: currentPage,
        page_size: PAGE_SIZE,
        ordering: '-fecha_donacion',
      };

      if (searchTerm) params.search = searchTerm;
      if (filtroEstado) params.estado = filtroEstado;
      if (filtroTipoDonante) params.donante_tipo = filtroTipoDonante;
      if (filtroCentro) params.centro_destino = filtroCentro;
      if (filtroFechaDesde) params.fecha_donacion_desde = filtroFechaDesde;
      if (filtroFechaHasta) params.fecha_donacion_hasta = filtroFechaHasta;

      const response = await donacionesAPI.getAll(params);
      const data = response.data;

      if (data.results) {
        setDonaciones(data.results);
        setTotalDonaciones(data.count || 0);
        setTotalPages(Math.ceil((data.count || 0) / PAGE_SIZE));
      } else {
        setDonaciones(data || []);
        setTotalDonaciones(data?.length || 0);
        setTotalPages(1);
      }
    } catch (err) {
      console.error('Error cargando donaciones:', err);
      toast.error('Error al cargar donaciones');
    } finally {
      setLoading(false);
    }
  }, [currentPage, searchTerm, filtroEstado, filtroTipoDonante, filtroCentro, filtroFechaDesde, filtroFechaHasta]);

  useEffect(() => {
    cargarCatalogos();
  }, [cargarCatalogos]);

  useEffect(() => {
    cargarDonaciones();
  }, [cargarDonaciones]);

  // Reset formulario
  const resetForm = () => {
    setFormData({
      numero: '',
      donante_nombre: '',
      donante_tipo: 'gobierno',
      donante_rfc: '',
      donante_direccion: '',
      donante_contacto: '',
      fecha_donacion: new Date().toISOString().split('T')[0],
      fecha_recepcion: new Date().toISOString().split('T')[0],
      centro_destino: '',
      notas: '',
      detalles: [],
    });
    setDetalleForm({
      producto: '',
      numero_lote: '',
      cantidad: '',
      fecha_caducidad: '',
      estado_producto: 'nuevo',
      notas: '',
    });
    setEditingDonacion(null);
  };

  // Abrir modal de creación
  const handleNuevo = () => {
    resetForm();
    setShowModal(true);
  };

  // Abrir modal de edición
  const handleEditar = (donacion) => {
    setEditingDonacion(donacion);
    setFormData({
      numero: donacion.numero || '',
      donante_nombre: donacion.donante_nombre || '',
      donante_tipo: donacion.donante_tipo || 'gobierno',
      donante_rfc: donacion.donante_rfc || '',
      donante_direccion: donacion.donante_direccion || '',
      donante_contacto: donacion.donante_contacto || '',
      fecha_donacion: donacion.fecha_donacion || '',
      fecha_recepcion: donacion.fecha_recepcion || '',
      centro_destino: donacion.centro_destino || '',
      notas: donacion.notas || '',
      detalles: donacion.detalles || [],
    });
    setShowModal(true);
  };

  // Ver detalle
  const handleVerDetalle = (donacion) => {
    setViewingDonacion(donacion);
    setShowDetalleModal(true);
  };

  // Agregar detalle al formulario
  const handleAgregarDetalle = () => {
    if (!detalleForm.producto || !detalleForm.cantidad) {
      toast.error('Selecciona un producto y cantidad');
      return;
    }

    const producto = productos.find((p) => p.id === parseInt(detalleForm.producto));
    const nuevoDetalle = {
      tempId: Date.now(),
      producto: parseInt(detalleForm.producto),
      producto_clave: producto?.clave || '',
      producto_descripcion: producto?.descripcion || '',
      numero_lote: detalleForm.numero_lote,
      cantidad: parseInt(detalleForm.cantidad),
      fecha_caducidad: detalleForm.fecha_caducidad || null,
      estado_producto: detalleForm.estado_producto,
      notas: detalleForm.notas,
    };

    setFormData((prev) => ({
      ...prev,
      detalles: [...prev.detalles, nuevoDetalle],
    }));

    setDetalleForm({
      producto: '',
      numero_lote: '',
      cantidad: '',
      fecha_caducidad: '',
      estado_producto: 'nuevo',
      notas: '',
    });
  };

  // Eliminar detalle del formulario
  const handleEliminarDetalle = (index) => {
    setFormData((prev) => ({
      ...prev,
      detalles: prev.detalles.filter((_, i) => i !== index),
    }));
  };

  // Guardar donación
  const handleGuardar = async () => {
    if (!formData.donante_nombre || !formData.centro_destino || formData.detalles.length === 0) {
      toast.error('Completa los campos obligatorios y agrega al menos un producto');
      return;
    }

    setActionLoading('guardar');
    try {
      const payload = {
        ...formData,
        centro_destino: parseInt(formData.centro_destino),
        detalles: formData.detalles.map((d) => ({
          producto: d.producto,
          numero_lote: d.numero_lote || null,
          cantidad: d.cantidad,
          fecha_caducidad: d.fecha_caducidad || null,
          estado_producto: d.estado_producto,
          notas: d.notas || '',
        })),
      };

      if (editingDonacion) {
        await donacionesAPI.update(editingDonacion.id, payload);
        toast.success('Donación actualizada correctamente');
      } else {
        await donacionesAPI.create(payload);
        toast.success('Donación registrada correctamente');
      }

      setShowModal(false);
      resetForm();
      cargarDonaciones();
    } catch (err) {
      console.error('Error guardando donación:', err);
      toast.error(err.response?.data?.error || 'Error al guardar donación');
    } finally {
      setActionLoading(null);
    }
  };

  // Eliminar donación
  const handleEliminar = async (id) => {
    setActionLoading(id);
    try {
      await donacionesAPI.delete(id);
      toast.success('Donación eliminada correctamente');
      cargarDonaciones();
    } catch (err) {
      console.error('Error eliminando donación:', err);
      toast.error(err.response?.data?.error || 'Error al eliminar donación');
    } finally {
      setActionLoading(null);
      setConfirmDelete(null);
    }
  };

  // Procesar donación
  const handleProcesar = async (id) => {
    setActionLoading(id);
    try {
      await donacionesAPI.procesar(id);
      toast.success('Donación procesada - Se crearon los movimientos de entrada');
      cargarDonaciones();
    } catch (err) {
      console.error('Error procesando donación:', err);
      toast.error(err.response?.data?.error || 'Error al procesar donación');
    } finally {
      setActionLoading(null);
      setConfirmProcesar(null);
    }
  };

  // Limpiar filtros
  const limpiarFiltros = () => {
    setSearchTerm('');
    setFiltroEstado('');
    setFiltroTipoDonante('');
    setFiltroCentro('');
    setFiltroFechaDesde('');
    setFiltroFechaHasta('');
    setCurrentPage(1);
  };

  // Formatear fecha
  const formatFecha = (fecha) => {
    if (!fecha) return '-';
    return new Date(fecha).toLocaleDateString('es-MX', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <div className="p-6">
      <PageHeader
        title="Donaciones"
        subtitle="Gestión de donaciones recibidas"
        icon={<FaGift className="text-3xl" style={{ color: COLORS.primary }} />}
      />

      {/* Barra de acciones */}
      <div className="bg-white rounded-xl shadow-sm border p-4 mb-6">
        <div className="flex flex-col lg:flex-row gap-4 items-start lg:items-center justify-between">
          {/* Búsqueda */}
          <div className="relative flex-1 max-w-md">
            <FaSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Buscar por número, donante..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
            />
          </div>

          {/* Acciones */}
          <div className="flex gap-2 flex-wrap">
            {/* Toggle filtros */}
            <button
              onClick={() => setShowFiltersMenu(!showFiltersMenu)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
                filtrosActivos > 0
                  ? 'bg-primary/10 border-primary text-primary'
                  : 'bg-white hover:bg-gray-50'
              }`}
            >
              <FaFilter />
              Filtros
              {filtrosActivos > 0 && (
                <span className="bg-primary text-white text-xs px-2 py-0.5 rounded-full">
                  {filtrosActivos}
                </span>
              )}
              <FaChevronDown className={`transition-transform ${showFiltersMenu ? 'rotate-180' : ''}`} />
            </button>

            {/* Botón nueva donación */}
            {puede.crear && (
              <button
                onClick={handleNuevo}
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-white transition-colors"
                style={{ backgroundColor: COLORS.primary }}
              >
                <FaPlus /> Nueva Donación
              </button>
            )}
          </div>
        </div>

        {/* Panel de filtros colapsable */}
        {showFiltersMenu && (
          <div className="mt-4 pt-4 border-t grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Estado</label>
              <select
                value={filtroEstado}
                onChange={(e) => {
                  setFiltroEstado(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
              >
                <option value="">Todos los estados</option>
                {Object.entries(ESTADOS_DONACION).map(([key, val]) => (
                  <option key={key} value={key}>
                    {val.icon} {val.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de Donante</label>
              <select
                value={filtroTipoDonante}
                onChange={(e) => {
                  setFiltroTipoDonante(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
              >
                <option value="">Todos los tipos</option>
                {TIPOS_DONANTE.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Centro Destino</label>
              <select
                value={filtroCentro}
                onChange={(e) => {
                  setFiltroCentro(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
              >
                <option value="">Todos los centros</option>
                {centros.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.nombre}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex gap-2">
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-1">Desde</label>
                <input
                  type="date"
                  value={filtroFechaDesde}
                  onChange={(e) => {
                    setFiltroFechaDesde(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                />
              </div>
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-1">Hasta</label>
                <input
                  type="date"
                  value={filtroFechaHasta}
                  onChange={(e) => {
                    setFiltroFechaHasta(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>

            {filtrosActivos > 0 && (
              <button
                onClick={limpiarFiltros}
                className="text-sm text-gray-600 hover:text-primary flex items-center gap-1"
              >
                <FaTimes /> Limpiar filtros
              </button>
            )}
          </div>
        )}
      </div>

      {/* Tabla de donaciones */}
      <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <FaSpinner className="animate-spin text-4xl text-gray-400" />
          </div>
        ) : donaciones.length === 0 ? (
          <div className="text-center py-20 text-gray-500">
            <FaGift className="mx-auto text-5xl mb-4 opacity-30" />
            <p>No se encontraron donaciones</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Número</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Donante</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Tipo</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Centro Destino</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Fecha</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Items</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Estado</th>
                  <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {donaciones.map((donacion) => {
                  const estado = ESTADOS_DONACION[donacion.estado] || ESTADOS_DONACION.pendiente;
                  return (
                    <tr key={donacion.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 font-medium text-gray-900">
                        {donacion.numero || `DON-${donacion.id}`}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <FaUser className="text-gray-400" />
                          <span>{donacion.donante_nombre}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 capitalize text-sm text-gray-600">
                        {TIPOS_DONANTE.find((t) => t.value === donacion.donante_tipo)?.label || donacion.donante_tipo}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <FaBuilding className="text-gray-400" />
                          <span>{donacion.centro_destino_nombre || '-'}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        <div className="flex items-center gap-2">
                          <FaCalendar className="text-gray-400" />
                          <span>{formatFecha(donacion.fecha_donacion)}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-medium">
                          <FaBox /> {donacion.detalles?.length || 0} productos
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${estado.color}`}>
                          {estado.icon} {estado.label}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-center gap-1">
                          {/* Ver detalle */}
                          <button
                            onClick={() => handleVerDetalle(donacion)}
                            className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                            title="Ver detalle"
                          >
                            <FaEye />
                          </button>

                          {/* Editar (solo pendientes) */}
                          {puede.editar && donacion.estado === 'pendiente' && (
                            <button
                              onClick={() => handleEditar(donacion)}
                              className="p-2 text-amber-600 hover:bg-amber-50 rounded-lg transition-colors"
                              title="Editar"
                            >
                              <FaEdit />
                            </button>
                          )}

                          {/* Procesar (solo pendientes) */}
                          {puede.procesar && donacion.estado === 'pendiente' && (
                            <button
                              onClick={() => setConfirmProcesar(donacion)}
                              disabled={actionLoading === donacion.id}
                              className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors disabled:opacity-50"
                              title="Procesar donación"
                            >
                              {actionLoading === donacion.id ? (
                                <FaSpinner className="animate-spin" />
                              ) : (
                                <FaCheck />
                              )}
                            </button>
                          )}

                          {/* Eliminar (solo pendientes) */}
                          {puede.eliminar && donacion.estado === 'pendiente' && (
                            <button
                              onClick={() => setConfirmDelete(donacion)}
                              disabled={actionLoading === donacion.id}
                              className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                              title="Eliminar"
                            >
                              <FaTrash />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Paginación */}
        {totalPages > 1 && (
          <div className="border-t p-4">
            <Pagination
              currentPage={currentPage}
              totalPages={totalPages}
              onPageChange={setCurrentPage}
              totalItems={totalDonaciones}
              pageSize={PAGE_SIZE}
            />
          </div>
        )}
      </div>

      {/* Modal de Creación/Edición */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
            {/* Header */}
            <div
              className="px-6 py-4 border-b flex items-center justify-between"
              style={{ backgroundColor: COLORS.primary }}
            >
              <h2 className="text-lg font-semibold text-white">
                {editingDonacion ? 'Editar Donación' : 'Nueva Donación'}
              </h2>
              <button
                onClick={() => {
                  setShowModal(false);
                  resetForm();
                }}
                className="text-white/80 hover:text-white transition-colors"
              >
                <FaTimes size={20} />
              </button>
            </div>

            {/* Contenido */}
            <div className="flex-1 overflow-y-auto p-6">
              {/* Datos del donante */}
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                  <FaUser /> Información del Donante
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-600 mb-1">
                      Nombre del Donante *
                    </label>
                    <input
                      type="text"
                      value={formData.donante_nombre}
                      onChange={(e) => setFormData({ ...formData, donante_nombre: e.target.value })}
                      className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                      placeholder="Nombre o razón social"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-600 mb-1">Tipo de Donante</label>
                    <select
                      value={formData.donante_tipo}
                      onChange={(e) => setFormData({ ...formData, donante_tipo: e.target.value })}
                      className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                    >
                      {TIPOS_DONANTE.map((t) => (
                        <option key={t.value} value={t.value}>
                          {t.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-600 mb-1">RFC</label>
                    <input
                      type="text"
                      value={formData.donante_rfc}
                      onChange={(e) => setFormData({ ...formData, donante_rfc: e.target.value })}
                      className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                      placeholder="RFC del donante"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-600 mb-1">Dirección</label>
                    <input
                      type="text"
                      value={formData.donante_direccion}
                      onChange={(e) => setFormData({ ...formData, donante_direccion: e.target.value })}
                      className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                      placeholder="Dirección"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-600 mb-1">Contacto</label>
                    <input
                      type="text"
                      value={formData.donante_contacto}
                      onChange={(e) => setFormData({ ...formData, donante_contacto: e.target.value })}
                      className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                      placeholder="Teléfono o email"
                    />
                  </div>
                </div>
              </div>

              {/* Datos de la donación */}
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                  <FaGift /> Datos de la Donación
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-600 mb-1">Número de Donación</label>
                    <input
                      type="text"
                      value={formData.numero}
                      onChange={(e) => setFormData({ ...formData, numero: e.target.value })}
                      className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                      placeholder="DON-001"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-600 mb-1">Fecha de Donación</label>
                    <input
                      type="date"
                      value={formData.fecha_donacion}
                      onChange={(e) => setFormData({ ...formData, fecha_donacion: e.target.value })}
                      className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-600 mb-1">Fecha de Recepción</label>
                    <input
                      type="date"
                      value={formData.fecha_recepcion}
                      onChange={(e) => setFormData({ ...formData, fecha_recepcion: e.target.value })}
                      className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-600 mb-1">Centro Destino *</label>
                    <select
                      value={formData.centro_destino}
                      onChange={(e) => setFormData({ ...formData, centro_destino: e.target.value })}
                      className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                    >
                      <option value="">Seleccionar centro</option>
                      {centros.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.nombre}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="mt-4">
                  <label className="block text-sm font-medium text-gray-600 mb-1">Notas</label>
                  <textarea
                    value={formData.notas}
                    onChange={(e) => setFormData({ ...formData, notas: e.target.value })}
                    rows={2}
                    className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                    placeholder="Observaciones adicionales..."
                  />
                </div>
              </div>

              {/* Productos donados */}
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                  <FaBox /> Productos Donados
                </h3>

                {/* Formulario para agregar producto */}
                <div className="bg-gray-50 rounded-lg p-4 mb-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-3">
                    <div className="lg:col-span-2">
                      <label className="block text-xs font-medium text-gray-600 mb-1">Producto *</label>
                      <select
                        value={detalleForm.producto}
                        onChange={(e) => setDetalleForm({ ...detalleForm, producto: e.target.value })}
                        className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary"
                      >
                        <option value="">Seleccionar producto</option>
                        {productos.map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.clave} - {p.descripcion}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Lote</label>
                      <input
                        type="text"
                        value={detalleForm.numero_lote}
                        onChange={(e) => setDetalleForm({ ...detalleForm, numero_lote: e.target.value })}
                        className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary"
                        placeholder="Nº lote"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Cantidad *</label>
                      <input
                        type="number"
                        min="1"
                        value={detalleForm.cantidad}
                        onChange={(e) => setDetalleForm({ ...detalleForm, cantidad: e.target.value })}
                        className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary"
                        placeholder="0"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Caducidad</label>
                      <input
                        type="date"
                        value={detalleForm.fecha_caducidad}
                        onChange={(e) => setDetalleForm({ ...detalleForm, fecha_caducidad: e.target.value })}
                        className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary"
                      />
                    </div>
                    <div className="flex items-end">
                      <button
                        type="button"
                        onClick={handleAgregarDetalle}
                        className="w-full px-4 py-2 rounded-lg text-white transition-colors"
                        style={{ backgroundColor: COLORS.primary }}
                      >
                        <FaPlus className="inline mr-1" /> Agregar
                      </button>
                    </div>
                  </div>
                </div>

                {/* Lista de productos agregados */}
                {formData.detalles.length > 0 ? (
                  <div className="border rounded-lg overflow-hidden">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50 border-b">
                        <tr>
                          <th className="px-3 py-2 text-left font-medium text-gray-600">Producto</th>
                          <th className="px-3 py-2 text-left font-medium text-gray-600">Lote</th>
                          <th className="px-3 py-2 text-center font-medium text-gray-600">Cantidad</th>
                          <th className="px-3 py-2 text-left font-medium text-gray-600">Caducidad</th>
                          <th className="px-3 py-2 text-center font-medium text-gray-600"></th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {formData.detalles.map((d, idx) => (
                          <tr key={d.tempId || d.id || idx} className="hover:bg-gray-50">
                            <td className="px-3 py-2">
                              <span className="font-medium">{d.producto_clave}</span>
                              <span className="block text-xs text-gray-500">{d.producto_descripcion}</span>
                            </td>
                            <td className="px-3 py-2 text-gray-600">{d.numero_lote || '-'}</td>
                            <td className="px-3 py-2 text-center font-medium">{d.cantidad}</td>
                            <td className="px-3 py-2 text-gray-600">{d.fecha_caducidad || '-'}</td>
                            <td className="px-3 py-2 text-center">
                              <button
                                onClick={() => handleEliminarDetalle(idx)}
                                className="p-1 text-red-500 hover:bg-red-50 rounded transition-colors"
                              >
                                <FaTrash />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-400 border-2 border-dashed rounded-lg">
                    <FaBox className="mx-auto text-3xl mb-2" />
                    <p>No hay productos agregados</p>
                  </div>
                )}
              </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t bg-gray-50 flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowModal(false);
                  resetForm();
                }}
                className="px-4 py-2 border rounded-lg hover:bg-gray-100 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={handleGuardar}
                disabled={actionLoading === 'guardar'}
                className="px-6 py-2 rounded-lg text-white transition-colors disabled:opacity-50 flex items-center gap-2"
                style={{ backgroundColor: COLORS.primary }}
              >
                {actionLoading === 'guardar' ? (
                  <>
                    <FaSpinner className="animate-spin" /> Guardando...
                  </>
                ) : (
                  <>Guardar Donación</>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Ver Detalle */}
      {showDetalleModal && viewingDonacion && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
            {/* Header */}
            <div
              className="px-6 py-4 border-b flex items-center justify-between"
              style={{ backgroundColor: COLORS.primary }}
            >
              <h2 className="text-lg font-semibold text-white">
                Detalle de Donación {viewingDonacion.numero || `DON-${viewingDonacion.id}`}
              </h2>
              <button
                onClick={() => {
                  setShowDetalleModal(false);
                  setViewingDonacion(null);
                }}
                className="text-white/80 hover:text-white transition-colors"
              >
                <FaTimes size={20} />
              </button>
            </div>

            {/* Contenido */}
            <div className="flex-1 overflow-y-auto p-6">
              {/* Estado */}
              <div className="mb-6 flex items-center gap-4">
                <span
                  className={`px-4 py-2 rounded-full text-sm font-medium ${
                    ESTADOS_DONACION[viewingDonacion.estado]?.color || 'bg-gray-100'
                  }`}
                >
                  {ESTADOS_DONACION[viewingDonacion.estado]?.icon}{' '}
                  {ESTADOS_DONACION[viewingDonacion.estado]?.label || viewingDonacion.estado}
                </span>
              </div>

              {/* Info del donante */}
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div>
                  <span className="text-sm text-gray-500">Donante</span>
                  <p className="font-medium">{viewingDonacion.donante_nombre}</p>
                </div>
                <div>
                  <span className="text-sm text-gray-500">Tipo</span>
                  <p className="font-medium capitalize">{viewingDonacion.donante_tipo}</p>
                </div>
                <div>
                  <span className="text-sm text-gray-500">RFC</span>
                  <p className="font-medium">{viewingDonacion.donante_rfc || '-'}</p>
                </div>
                <div>
                  <span className="text-sm text-gray-500">Contacto</span>
                  <p className="font-medium">{viewingDonacion.donante_contacto || '-'}</p>
                </div>
                <div>
                  <span className="text-sm text-gray-500">Centro Destino</span>
                  <p className="font-medium">{viewingDonacion.centro_destino_nombre || '-'}</p>
                </div>
                <div>
                  <span className="text-sm text-gray-500">Fecha Donación</span>
                  <p className="font-medium">{formatFecha(viewingDonacion.fecha_donacion)}</p>
                </div>
              </div>

              {/* Productos */}
              <div>
                <h3 className="font-semibold text-gray-700 mb-3">Productos Donados</h3>
                {viewingDonacion.detalles && viewingDonacion.detalles.length > 0 ? (
                  <div className="border rounded-lg overflow-hidden">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50 border-b">
                        <tr>
                          <th className="px-4 py-2 text-left font-medium text-gray-600">Producto</th>
                          <th className="px-4 py-2 text-left font-medium text-gray-600">Lote</th>
                          <th className="px-4 py-2 text-center font-medium text-gray-600">Cantidad</th>
                          <th className="px-4 py-2 text-left font-medium text-gray-600">Caducidad</th>
                          <th className="px-4 py-2 text-left font-medium text-gray-600">Estado</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {viewingDonacion.detalles.map((d, idx) => (
                          <tr key={d.id || idx}>
                            <td className="px-4 py-2">
                              <span className="font-medium">{d.producto_clave}</span>
                              <span className="block text-xs text-gray-500">{d.producto_descripcion}</span>
                            </td>
                            <td className="px-4 py-2 text-gray-600">{d.numero_lote || '-'}</td>
                            <td className="px-4 py-2 text-center font-medium">{d.cantidad}</td>
                            <td className="px-4 py-2 text-gray-600">{formatFecha(d.fecha_caducidad)}</td>
                            <td className="px-4 py-2 capitalize text-gray-600">{d.estado_producto}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-gray-500">Sin productos registrados</p>
                )}
              </div>

              {/* Notas */}
              {viewingDonacion.notas && (
                <div className="mt-6">
                  <h3 className="font-semibold text-gray-700 mb-2">Notas</h3>
                  <p className="text-gray-600 bg-gray-50 p-3 rounded-lg">{viewingDonacion.notas}</p>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t bg-gray-50 flex justify-end">
              <button
                onClick={() => {
                  setShowDetalleModal(false);
                  setViewingDonacion(null);
                }}
                className="px-4 py-2 border rounded-lg hover:bg-gray-100 transition-colors"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de confirmación eliminar */}
      {confirmDelete && (
        <ConfirmModal
          title="Eliminar Donación"
          message={`¿Estás seguro de eliminar la donación "${confirmDelete.numero || 'DON-' + confirmDelete.id}"? Esta acción no se puede deshacer.`}
          confirmText="Eliminar"
          cancelText="Cancelar"
          confirmColor="red"
          onConfirm={() => handleEliminar(confirmDelete.id)}
          onCancel={() => setConfirmDelete(null)}
        />
      )}

      {/* Modal de confirmación procesar */}
      {confirmProcesar && (
        <ConfirmModal
          title="Procesar Donación"
          message={`¿Estás seguro de procesar la donación "${confirmProcesar.numero || 'DON-' + confirmProcesar.id}"? Esto creará los movimientos de entrada y los lotes correspondientes.`}
          confirmText="Procesar"
          cancelText="Cancelar"
          confirmColor="green"
          onConfirm={() => handleProcesar(confirmProcesar.id)}
          onCancel={() => setConfirmProcesar(null)}
        />
      )}
    </div>
  );
};

export default Donaciones;
