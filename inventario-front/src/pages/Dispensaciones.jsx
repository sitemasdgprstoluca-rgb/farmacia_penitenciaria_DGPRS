import { useState, useEffect, useCallback } from 'react';
import { dispensacionesAPI, pacientesAPI, centrosAPI, productosAPI, lotesAPI } from '../services/api';
import { toast } from 'react-hot-toast';
import {
  FaPlus,
  FaEdit,
  FaTrash,
  FaSearch,
  FaPills,
  FaFilter,
  FaTimes,
  FaFilePdf,
  FaEye,
  FaHistory,
  FaCheck,
  FaBan,
  FaChevronDown,
  FaUserInjured,
  FaCalendarAlt,
  FaClipboardList,
  FaStethoscope,
  FaBoxOpen,
  FaExclamationTriangle,
  FaInfoCircle,
} from 'react-icons/fa';
import PageHeader from '../components/PageHeader';
import Pagination from '../components/Pagination';
import ConfirmModal from '../components/ConfirmModal';
import { usePermissions } from '../hooks/usePermissions';
import { esFarmaciaAdmin } from '../utils/roles';

const PAGE_SIZE = 20;

const TIPOS_DISPENSACION = [
  { value: '', label: 'Todos' },
  { value: 'REGULAR', label: 'Regular' },
  { value: 'URGENCIA', label: 'Urgencia' },
  { value: 'CRONICO', label: 'Crónico' },
  { value: 'PROFILAXIS', label: 'Profilaxis' },
];

const ESTADOS_DISPENSACION = [
  { value: '', label: 'Todos' },
  { value: 'PENDIENTE', label: 'Pendiente' },
  { value: 'DISPENSADA', label: 'Dispensada' },
  { value: 'CANCELADA', label: 'Cancelada' },
];

const ESTADO_COLORS = {
  PENDIENTE: 'bg-yellow-100 text-yellow-800',
  DISPENSADA: 'bg-green-100 text-green-800',
  CANCELADA: 'bg-red-100 text-red-800',
};

const Dispensaciones = () => {
  const { user, verificarPermiso } = usePermissions();
  
  // Permisos específicos de dispensación (basados en rol del usuario)
  const puedeCrear = verificarPermiso('crearDispensacion');
  const puedeEditar = verificarPermiso('editarDispensacion');
  const puedeDispensar = verificarPermiso('dispensar');
  const puedeCancelar = verificarPermiso('cancelarDispensacion');
  
  // Detectar tipo de usuario para UI adaptativa
  const esUsuarioFarmacia = esFarmaciaAdmin(user) && !puedeCrear; // Farmacia sin permisos de crear = auditor
  const esSoloAuditoria = esUsuarioFarmacia;  // Alias para claridad
  
  // Centro del usuario (para filtrado automático)
  const centroUsuario = user?.centro?.id || user?.centro_id;

  // Estados principales
  const [dispensaciones, setDispensaciones] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  
  // Filtros - Si es usuario de centro, filtrar por su centro automáticamente
  const [searchTerm, setSearchTerm] = useState('');
  const [centroFiltro, setCentroFiltro] = useState(centroUsuario || '');
  const [estadoFiltro, setEstadoFiltro] = useState('');
  const [tipoFiltro, setTipoFiltro] = useState('');
  const [fechaInicio, setFechaInicio] = useState('');
  const [fechaFin, setFechaFin] = useState('');
  // Mostrar filtros expandidos por defecto para Farmacia
  const [showFilters, setShowFilters] = useState(!centroUsuario);
  
  // Listas auxiliares
  const [centros, setCentros] = useState([]);
  const [productos, setProductos] = useState([]);
  const [lotes, setLotes] = useState([]);
  const [pacientes, setPacientes] = useState([]);
  const [pacienteSearchTerm, setPacienteSearchTerm] = useState('');
  const [showPacienteDropdown, setShowPacienteDropdown] = useState(false);
  
  // Modal de formulario
  const [showModal, setShowModal] = useState(false);
  const [editingDispensacion, setEditingDispensacion] = useState(null);
  const [formData, setFormData] = useState({
    paciente: '',
    centro: '',
    tipo_dispensacion: 'REGULAR',
    fecha_prescripcion: '',
    medico_prescriptor: '',
    diagnostico: '',
    indicaciones_medicas: '',
    observaciones: '',
    detalles: [],
  });
  
  // Detalle actual siendo agregado
  const [currentDetalle, setCurrentDetalle] = useState({
    producto: '',
    lote: '',
    cantidad_prescrita: '',
    dosis: '',
    frecuencia: '',
    duracion_tratamiento: '',
    indicaciones: '',
  });
  
  // Modales
  const [deleteModal, setDeleteModal] = useState({ show: false, dispensacion: null });
  const [cancelModal, setCancelModal] = useState({ show: false, dispensacion: null, motivo: '' });
  const [dispensarModal, setDispensarModal] = useState({ show: false, dispensacion: null });
  const [detailModal, setDetailModal] = useState({ show: false, dispensacion: null });
  const [historialModal, setHistorialModal] = useState({ show: false, dispensacion: null, historial: [] });

  // Cargar centros
  useEffect(() => {
    const fetchCentros = async () => {
      try {
        const response = await centrosAPI.getAll({ activo: true, page_size: 100 });
        setCentros(response.data?.results || response.data || []);
      } catch (error) {
        console.error('Error al cargar centros:', error);
      }
    };
    fetchCentros();
  }, []);

  // Cargar productos
  useEffect(() => {
    const fetchProductos = async () => {
      try {
        const response = await productosAPI.getAll({ activo: true, page_size: 500 });
        setProductos(response.data?.results || response.data || []);
      } catch (error) {
        console.error('Error al cargar productos:', error);
      }
    };
    fetchProductos();
  }, []);

  // Cargar dispensaciones
  const fetchDispensaciones = useCallback(async () => {
    setLoading(true);
    try {
      const params = {
        page: currentPage,
        page_size: PAGE_SIZE,
        search: searchTerm || undefined,
        centro: centroFiltro || undefined,
        estado: estadoFiltro || undefined,
        tipo_dispensacion: tipoFiltro || undefined,
        fecha_inicio: fechaInicio || undefined,
        fecha_fin: fechaFin || undefined,
      };
      
      const response = await dispensacionesAPI.getAll(params);
      const data = response.data;
      
      setDispensaciones(data?.results || data || []);
      setTotalItems(data?.count || data?.length || 0);
    } catch (error) {
      console.error('Error al cargar dispensaciones:', error);
      toast.error('Error al cargar dispensaciones');
      setDispensaciones([]);
    } finally {
      setLoading(false);
    }
  }, [currentPage, searchTerm, centroFiltro, estadoFiltro, tipoFiltro, fechaInicio, fechaFin]);

  useEffect(() => {
    fetchDispensaciones();
  }, [fetchDispensaciones]);

  // Buscar pacientes (si term está vacío, trae los primeros del centro)
  const searchPacientes = useCallback(async (term = '') => {
    if (!formData.centro) {
      setPacientes([]);
      return;
    }
    try {
      const params = { 
        centro: formData.centro,
        page_size: 20 
      };
      // Si hay término de búsqueda, filtramos
      if (term && term.length >= 1) {
        params.search = term;
      }
      const response = await pacientesAPI.autocomplete(params);
      setPacientes(response.data?.results || response.data || []);
    } catch (error) {
      console.error('Error al buscar pacientes:', error);
    }
  }, [formData.centro]);

  // Precargar pacientes cuando se selecciona un centro
  useEffect(() => {
    if (formData.centro) {
      searchPacientes('');
    } else {
      setPacientes([]);
    }
  }, [formData.centro, searchPacientes]);

  // Buscar pacientes con debounce cuando escribe
  useEffect(() => {
    const timer = setTimeout(() => {
      if (formData.centro) {
        searchPacientes(pacienteSearchTerm);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [pacienteSearchTerm, formData.centro, searchPacientes]);

  // Cargar lotes cuando se selecciona producto
  const fetchLotes = async (productoId, centroId) => {
    if (!productoId || !centroId) {
      setLotes([]);
      return;
    }
    try {
      const response = await lotesAPI.getAll({
        producto: productoId,
        centro: centroId,
        cantidad_disponible_gt: 0,
        page_size: 50
      });
      setLotes(response.data?.results || response.data || []);
    } catch (error) {
      console.error('Error al cargar lotes:', error);
      setLotes([]);
    }
  };

  // Handlers del formulario
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    
    if (name === 'centro') {
      // Limpiar paciente y lotes cuando cambia el centro
      setFormData(prev => ({ ...prev, paciente: '' }));
      setPacienteSearchTerm('');
      setLotes([]);
    }
  };

  const handleDetalleChange = (e) => {
    const { name, value } = e.target;
    setCurrentDetalle(prev => ({
      ...prev,
      [name]: value
    }));
    
    if (name === 'producto') {
      setCurrentDetalle(prev => ({ ...prev, lote: '' }));
      fetchLotes(value, formData.centro);
    }
  };

  const addDetalle = () => {
    if (!currentDetalle.producto) {
      toast.error('Seleccione un producto');
      return;
    }
    if (!currentDetalle.lote) {
      toast.error('Seleccione un lote');
      return;
    }
    if (!currentDetalle.cantidad_prescrita || currentDetalle.cantidad_prescrita <= 0) {
      toast.error('Ingrese una cantidad válida');
      return;
    }
    
    const producto = productos.find(p => p.id == currentDetalle.producto);
    const lote = lotes.find(l => l.id == currentDetalle.lote);
    
    if (parseInt(currentDetalle.cantidad_prescrita) > lote?.cantidad_disponible) {
      toast.error(`Stock insuficiente. Disponible: ${lote?.cantidad_disponible}`);
      return;
    }
    
    setFormData(prev => ({
      ...prev,
      detalles: [...prev.detalles, {
        ...currentDetalle,
        producto_nombre: producto?.nombre,
        lote_numero: lote?.numero_lote,
        stock_disponible: lote?.cantidad_disponible,
      }]
    }));
    
    setCurrentDetalle({
      producto: '',
      lote: '',
      cantidad_prescrita: '',
      dosis: '',
      frecuencia: '',
      duracion_tratamiento: '',
      indicaciones: '',
    });
    setLotes([]);
  };

  const removeDetalle = (index) => {
    setFormData(prev => ({
      ...prev,
      detalles: prev.detalles.filter((_, i) => i !== index)
    }));
  };

  const resetForm = () => {
    setFormData({
      paciente: '',
      centro: user?.centro?.id || '',
      tipo_dispensacion: 'REGULAR',
      fecha_prescripcion: new Date().toISOString().split('T')[0],
      medico_prescriptor: '',
      diagnostico: '',
      indicaciones_medicas: '',
      observaciones: '',
      detalles: [],
    });
    setCurrentDetalle({
      producto: '',
      lote: '',
      cantidad_prescrita: '',
      dosis: '',
      frecuencia: '',
      duracion_tratamiento: '',
      indicaciones: '',
    });
    setEditingDispensacion(null);
    setPacienteSearchTerm('');
    setPacientes([]);
    setLotes([]);
  };

  const handleOpenModal = (dispensacion = null) => {
    if (dispensacion) {
      // Editar (solo si está pendiente)
      if (dispensacion.estado !== 'PENDIENTE') {
        toast.error('Solo se pueden editar dispensaciones pendientes');
        return;
      }
      setEditingDispensacion(dispensacion);
      setFormData({
        paciente: dispensacion.paciente,
        centro: dispensacion.centro,
        tipo_dispensacion: dispensacion.tipo_dispensacion || 'REGULAR',
        fecha_prescripcion: dispensacion.fecha_prescripcion || '',
        medico_prescriptor: dispensacion.medico_prescriptor || '',
        diagnostico: dispensacion.diagnostico || '',
        indicaciones_medicas: dispensacion.indicaciones_medicas || '',
        observaciones: dispensacion.observaciones || '',
        detalles: (dispensacion.detalles || []).map(d => ({
          id: d.id,
          producto: d.producto,
          lote: d.lote,
          cantidad_prescrita: d.cantidad_prescrita,
          dosis: d.dosis || '',
          frecuencia: d.frecuencia || '',
          duracion_tratamiento: d.duracion_tratamiento || '',
          indicaciones: d.indicaciones || '',
          producto_nombre: d.producto_nombre,
          lote_numero: d.lote_numero,
        }))
      });
      setPacienteSearchTerm(dispensacion.paciente_nombre || '');
    } else {
      resetForm();
    }
    setShowModal(true);
  };

  const handleSelectPaciente = (paciente) => {
    setFormData(prev => ({ ...prev, paciente: paciente.id }));
    setPacienteSearchTerm(paciente.nombre_completo);
    setShowPacienteDropdown(false);
    setPacientes([]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.paciente) {
      toast.error('Seleccione un paciente');
      return;
    }
    if (!formData.centro) {
      toast.error('Seleccione un centro');
      return;
    }
    if (formData.detalles.length === 0) {
      toast.error('Agregue al menos un medicamento');
      return;
    }
    
    try {
      const dataToSend = {
        paciente: formData.paciente,
        centro: formData.centro,
        tipo_dispensacion: formData.tipo_dispensacion,
        fecha_prescripcion: formData.fecha_prescripcion || null,
        medico_prescriptor: formData.medico_prescriptor || null,
        diagnostico: formData.diagnostico || null,
        indicaciones_medicas: formData.indicaciones_medicas || null,
        observaciones: formData.observaciones || null,
        detalles: formData.detalles.map(d => ({
          producto: d.producto,
          lote: d.lote,
          cantidad_prescrita: parseInt(d.cantidad_prescrita),
          dosis: d.dosis || null,
          frecuencia: d.frecuencia || null,
          duracion_tratamiento: d.duracion_tratamiento || null,
          indicaciones: d.indicaciones || null,
        }))
      };
      
      if (editingDispensacion) {
        await dispensacionesAPI.update(editingDispensacion.id, dataToSend);
        toast.success('Dispensación actualizada correctamente');
      } else {
        await dispensacionesAPI.create(dataToSend);
        toast.success('Dispensación creada correctamente');
      }
      
      setShowModal(false);
      resetForm();
      fetchDispensaciones();
    } catch (error) {
      console.error('Error al guardar:', error);
      const errorMsg = error.response?.data?.detail || 
                       error.response?.data?.message ||
                       'Error al guardar dispensación';
      toast.error(errorMsg);
    }
  };

  const handleDispensar = async () => {
    if (!dispensarModal.dispensacion) return;
    
    try {
      await dispensacionesAPI.dispensar(dispensarModal.dispensacion.id);
      toast.success('Dispensación procesada correctamente');
      setDispensarModal({ show: false, dispensacion: null });
      fetchDispensaciones();
    } catch (error) {
      console.error('Error al dispensar:', error);
      const errorMsg = error.response?.data?.detail || 'Error al procesar dispensación';
      toast.error(errorMsg);
    }
  };

  const handleCancelar = async () => {
    if (!cancelModal.dispensacion) return;
    
    try {
      await dispensacionesAPI.cancelar(cancelModal.dispensacion.id, {
        motivo: cancelModal.motivo || 'Cancelado por el usuario'
      });
      toast.success('Dispensación cancelada');
      setCancelModal({ show: false, dispensacion: null, motivo: '' });
      fetchDispensaciones();
    } catch (error) {
      console.error('Error al cancelar:', error);
      toast.error('Error al cancelar dispensación');
    }
  };

  const handleDelete = async () => {
    if (!deleteModal.dispensacion) return;
    
    try {
      await dispensacionesAPI.delete(deleteModal.dispensacion.id);
      toast.success('Dispensación eliminada');
      setDeleteModal({ show: false, dispensacion: null });
      fetchDispensaciones();
    } catch (error) {
      console.error('Error al eliminar:', error);
      toast.error('Error al eliminar dispensación');
    }
  };

  const handleExportPdf = async (dispensacion) => {
    try {
      const response = await dispensacionesAPI.exportarPdf(dispensacion.id);
      
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Formato_C_${dispensacion.folio}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
      
      toast.success('PDF generado correctamente');
    } catch (error) {
      console.error('Error al generar PDF:', error);
      toast.error('Error al generar PDF');
    }
  };

  const handleShowHistorial = async (dispensacion) => {
    try {
      const response = await dispensacionesAPI.historial(dispensacion.id);
      setHistorialModal({
        show: true,
        dispensacion,
        historial: response.data || []
      });
    } catch (error) {
      console.error('Error al cargar historial:', error);
      toast.error('Error al cargar historial');
    }
  };

  const totalPages = Math.ceil(totalItems / PAGE_SIZE);

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Dispensación a Pacientes"
        subtitle="Formato C - Gestión de entrega de medicamentos a internos"
        icon={FaPills}
      />

      {/* Barra de acciones */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-4">
        <div className="flex flex-col sm:flex-row gap-4 justify-between items-start sm:items-center">
          {/* Búsqueda */}
          <div className="relative flex-1 max-w-md">
            <FaSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Buscar por folio, paciente..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-guinda focus:border-guinda"
            />
          </div>

          {/* Botones */}
          <div className="flex gap-2 flex-wrap">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
                showFilters ? 'bg-guinda text-white border-guinda' : 'bg-white text-gray-700 hover:bg-gray-50'
              }`}
            >
              <FaFilter />
              Filtros
              <FaChevronDown className={`transform transition-transform ${showFilters ? 'rotate-180' : ''}`} />
            </button>
            
            {puedeCrear && (
              <button
                onClick={() => handleOpenModal()}
                className="flex items-center gap-2 px-4 py-2 bg-guinda text-white rounded-lg hover:bg-guinda-dark transition-colors"
              >
                <FaPlus />
                Nueva Dispensación
              </button>
            )}
          </div>
        </div>

        {/* Aviso para farmacia (modo auditoría) */}
        {esSoloAuditoria && (
          <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-2xl flex items-center gap-2 text-blue-700">
            <FaInfoCircle />
            <span className="text-sm">
              <strong>Modo Auditoría:</strong> Como personal de Farmacia, puede consultar las dispensaciones realizadas por los centros pero no operarlas.
            </span>
          </div>
        )}

        {/* Panel de filtros */}
        {showFilters && (
          <div className="mt-4 pt-4 border-t grid grid-cols-1 sm:grid-cols-4 gap-4">
            {/* Centro - solo visible para Farmacia/Admin */}
            {esSoloAuditoria && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Centro</label>
                <select
                  value={centroFiltro}
                  onChange={(e) => {
                    setCentroFiltro(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-guinda"
                >
                  <option value="">Todos los centros</option>
                  {centros.map(centro => (
                    <option key={centro.id} value={centro.id}>{centro.nombre}</option>
                  ))}
                </select>
              </div>
            )}
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Estado</label>
              <select
                value={estadoFiltro}
                onChange={(e) => {
                  setEstadoFiltro(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-guinda"
              >
                {ESTADOS_DISPENSACION.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tipo</label>
              <select
                value={tipoFiltro}
                onChange={(e) => {
                  setTipoFiltro(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-guinda"
              >
                {TIPOS_DISPENSACION.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Desde</label>
              <input
                type="date"
                value={fechaInicio}
                onChange={(e) => {
                  setFechaInicio(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-guinda"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Hasta</label>
              <input
                type="date"
                value={fechaFin}
                onChange={(e) => {
                  setFechaFin(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-guinda"
              />
            </div>
          </div>
        )}
      </div>

      {/* Tabla de dispensaciones */}
      <div className="rounded-2xl border border-gray-200 bg-white shadow-sm">
        {loading ? (
          <div className="flex justify-center items-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-4 border-t-transparent spinner-institucional"></div>
          </div>
        ) : dispensaciones.length === 0 ? (
          <div className="text-center py-12">
            <FaPills className="mx-auto h-12 w-12 text-gray-300" />
            <p className="mt-4 text-gray-500">No se encontraron dispensaciones</p>
          </div>
        ) : (
          <div className="w-full overflow-x-auto">
            <table className="w-full min-w-[1000px] divide-y divide-gray-200">
              <thead className="bg-theme-gradient sticky top-0 z-10">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Folio</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Paciente</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Centro</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Tipo</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Fecha</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Items</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Estado</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Acciones</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-100">
                {dispensaciones.map((disp) => (
                  <tr key={disp.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="font-mono font-medium text-guinda">{disp.folio}</span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center">
                        <FaUserInjured className="text-gray-400 mr-2" />
                        <div>
                          <div className="text-sm font-medium text-gray-900">{disp.paciente_nombre}</div>
                          <div className="text-xs text-gray-500">Exp: {disp.paciente_expediente}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {disp.centro_nombre}
                    </td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-800">
                        {disp.tipo_dispensacion_display || disp.tipo_dispensacion}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      <div className="flex items-center">
                        <FaCalendarAlt className="mr-2 text-gray-400" />
                        {new Date(disp.fecha_dispensacion || disp.created_at).toLocaleDateString()}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="px-2 py-1 bg-gray-100 rounded-full text-sm">
                        {disp.total_items || disp.detalles?.length || 0}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`px-2 py-1 text-xs rounded-full ${ESTADO_COLORS[disp.estado]}`}>
                        {disp.estado_display || disp.estado}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <div className="flex justify-center gap-1">
                        <button
                          onClick={() => setDetailModal({ show: true, dispensacion: disp })}
                          className="text-gray-500 hover:text-guinda p-1"
                          title="Ver detalle"
                        >
                          <FaEye />
                        </button>
                        
                        {disp.estado === 'PENDIENTE' && puedeDispensar && (
                          <button
                            onClick={() => setDispensarModal({ show: true, dispensacion: disp })}
                            className="text-green-600 hover:text-green-800 p-1"
                            title="Dispensar"
                          >
                            <FaCheck />
                          </button>
                        )}
                        
                        {disp.estado === 'PENDIENTE' && puedeEditar && (
                          <button
                            onClick={() => handleOpenModal(disp)}
                            className="text-blue-600 hover:text-blue-800 p-1"
                            title="Editar"
                          >
                            <FaEdit />
                          </button>
                        )}
                        
                        {disp.estado === 'PENDIENTE' && puedeCancelar && (
                          <button
                            onClick={() => setCancelModal({ show: true, dispensacion: disp, motivo: '' })}
                            className="text-orange-600 hover:text-orange-800 p-1"
                            title="Cancelar"
                          >
                            <FaBan />
                          </button>
                        )}
                        
                        {disp.estado === 'DISPENSADA' && (
                          <button
                            onClick={() => handleExportPdf(disp)}
                            className="text-red-600 hover:text-red-800 p-1"
                            title="Descargar Formato C"
                          >
                            <FaFilePdf />
                          </button>
                        )}
                        
                        <button
                          onClick={() => handleShowHistorial(disp)}
                          className="text-gray-500 hover:text-guinda p-1"
                          title="Historial"
                        >
                          <FaHistory />
                        </button>
                        
                        {disp.estado === 'PENDIENTE' && puedeEditar && (
                          <button
                            onClick={() => setDeleteModal({ show: true, dispensacion: disp })}
                            className="text-red-600 hover:text-red-800 p-1"
                            title="Eliminar"
                          >
                            <FaTrash />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Paginación */}
        {totalPages > 1 && (
          <div className="px-4 py-3 border-t">
            <Pagination
              currentPage={currentPage}
              totalPages={totalPages}
              onPageChange={setCurrentPage}
            />
          </div>
        )}
      </div>

      {/* Modal de formulario */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[95vh] overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b bg-guinda text-white rounded-t-lg">
              <h3 className="text-lg font-semibold">
                {editingDispensacion ? 'Editar Dispensación' : 'Nueva Dispensación'}
              </h3>
              <button onClick={() => setShowModal(false)} className="hover:bg-white/20 p-1 rounded">
                <FaTimes />
              </button>
            </div>
            
            <form onSubmit={handleSubmit} className="p-6">
              {/* Datos generales */}
              <div className="mb-6">
                <h4 className="text-sm font-semibold text-gray-700 mb-3 pb-2 border-b flex items-center">
                  <FaClipboardList className="mr-2" /> Datos de la Dispensación
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Centro <span className="text-red-500">*</span>
                    </label>
                    <select
                      name="centro"
                      value={formData.centro}
                      onChange={handleInputChange}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-guinda"
                      required
                    >
                      <option value="">Seleccionar centro</option>
                      {centros.map(centro => (
                        <option key={centro.id} value={centro.id}>{centro.nombre}</option>
                      ))}
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Tipo <span className="text-red-500">*</span>
                    </label>
                    <select
                      name="tipo_dispensacion"
                      value={formData.tipo_dispensacion}
                      onChange={handleInputChange}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-guinda"
                      required
                    >
                      {TIPOS_DISPENSACION.filter(t => t.value).map(tipo => (
                        <option key={tipo.value} value={tipo.value}>{tipo.label}</option>
                      ))}
                    </select>
                  </div>
                  
                  <div className="relative sm:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Paciente <span className="text-red-500">*</span>
                    </label>
                    <div className="relative">
                      <FaSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                      <input
                        type="text"
                        placeholder="Buscar por expediente o nombre..."
                        value={pacienteSearchTerm}
                        onChange={(e) => {
                          setPacienteSearchTerm(e.target.value);
                          setShowPacienteDropdown(true);
                          if (!e.target.value) {
                            setFormData(prev => ({ ...prev, paciente: '' }));
                          }
                        }}
                        onFocus={() => setShowPacienteDropdown(true)}
                        className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-guinda"
                        disabled={!formData.centro}
                      />
                    </div>
                    {!formData.centro && (
                      <p className="text-xs text-gray-500 mt-1">Seleccione primero un centro</p>
                    )}
                    {showPacienteDropdown && formData.centro && (
                      <div className="absolute z-10 w-full mt-1 bg-white border rounded-lg shadow-lg max-h-48 overflow-y-auto">
                        {pacientes.length > 0 ? (
                          pacientes.map(pac => (
                            <button
                              type="button"
                              key={pac.id}
                              onClick={() => handleSelectPaciente(pac)}
                              className="w-full px-4 py-2 text-left hover:bg-gray-100 flex items-center"
                            >
                              <FaUserInjured className="mr-2 text-gray-400" />
                              <div>
                                <div className="font-medium">{pac.nombre_completo}</div>
                                <div className="text-xs text-gray-500">Exp: {pac.numero_expediente}</div>
                              </div>
                            </button>
                          ))
                        ) : (
                          <div className="px-4 py-3 text-sm text-gray-500 text-center">
                            No hay pacientes registrados en este centro
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Datos médicos */}
              <div className="mb-6">
                <h4 className="text-sm font-semibold text-gray-700 mb-3 pb-2 border-b flex items-center">
                  <FaStethoscope className="mr-2" /> Información Médica
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Fecha de Prescripción</label>
                    <input
                      type="date"
                      name="fecha_prescripcion"
                      value={formData.fecha_prescripcion}
                      onChange={handleInputChange}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-guinda"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Médico Prescriptor</label>
                    <input
                      type="text"
                      name="medico_prescriptor"
                      value={formData.medico_prescriptor}
                      onChange={handleInputChange}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-guinda"
                      placeholder="Nombre del médico"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Diagnóstico</label>
                    <input
                      type="text"
                      name="diagnostico"
                      value={formData.diagnostico}
                      onChange={handleInputChange}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-guinda"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Indicaciones Médicas</label>
                    <textarea
                      name="indicaciones_medicas"
                      value={formData.indicaciones_medicas}
                      onChange={handleInputChange}
                      rows={2}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-guinda"
                    />
                  </div>
                </div>
              </div>

              {/* Agregar medicamentos */}
              <div className="mb-6">
                <h4 className="text-sm font-semibold text-gray-700 mb-3 pb-2 border-b flex items-center">
                  <FaBoxOpen className="mr-2" /> Medicamentos a Dispensar
                </h4>
                
                <div className="bg-gray-50 p-4 rounded-lg mb-4">
                  <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">Producto</label>
                      <select
                        name="producto"
                        value={currentDetalle.producto}
                        onChange={handleDetalleChange}
                        className="w-full px-2 py-1.5 border rounded text-sm focus:ring-2 focus:ring-guinda"
                        disabled={!formData.centro}
                      >
                        <option value="">Seleccionar</option>
                        {productos.map(prod => (
                          <option key={prod.id} value={prod.id}>{prod.nombre}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">Lote</label>
                      <select
                        name="lote"
                        value={currentDetalle.lote}
                        onChange={handleDetalleChange}
                        className="w-full px-2 py-1.5 border rounded text-sm focus:ring-2 focus:ring-guinda"
                        disabled={!currentDetalle.producto || lotes.length === 0}
                      >
                        <option value="">Seleccionar</option>
                        {lotes.map(lote => (
                          <option key={lote.id} value={lote.id}>
                            {lote.numero_lote} (Disp: {lote.cantidad_disponible})
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">Cantidad</label>
                      <input
                        type="number"
                        name="cantidad_prescrita"
                        value={currentDetalle.cantidad_prescrita}
                        onChange={handleDetalleChange}
                        min="1"
                        className="w-full px-2 py-1.5 border rounded text-sm focus:ring-2 focus:ring-guinda"
                      />
                    </div>
                    <div className="flex items-end">
                      <button
                        type="button"
                        onClick={addDetalle}
                        className="w-full px-3 py-1.5 bg-guinda text-white rounded hover:bg-guinda-dark transition-colors text-sm"
                      >
                        <FaPlus className="inline mr-1" /> Agregar
                      </button>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 mt-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">Dosis</label>
                      <input
                        type="text"
                        name="dosis"
                        value={currentDetalle.dosis}
                        onChange={handleDetalleChange}
                        placeholder="Ej: 500mg"
                        className="w-full px-2 py-1.5 border rounded text-sm focus:ring-2 focus:ring-guinda"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">Frecuencia</label>
                      <input
                        type="text"
                        name="frecuencia"
                        value={currentDetalle.frecuencia}
                        onChange={handleDetalleChange}
                        placeholder="Ej: Cada 8 horas"
                        className="w-full px-2 py-1.5 border rounded text-sm focus:ring-2 focus:ring-guinda"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">Duración</label>
                      <input
                        type="text"
                        name="duracion_tratamiento"
                        value={currentDetalle.duracion_tratamiento}
                        onChange={handleDetalleChange}
                        placeholder="Ej: 7 días"
                        className="w-full px-2 py-1.5 border rounded text-sm focus:ring-2 focus:ring-guinda"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">Indicaciones</label>
                      <input
                        type="text"
                        name="indicaciones"
                        value={currentDetalle.indicaciones}
                        onChange={handleDetalleChange}
                        placeholder="Opcional"
                        className="w-full px-2 py-1.5 border rounded text-sm focus:ring-2 focus:ring-guinda"
                      />
                    </div>
                  </div>
                </div>

                {/* Lista de medicamentos agregados */}
                {formData.detalles.length > 0 ? (
                  <div className="border rounded-lg overflow-hidden">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-100">
                        <tr>
                          <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">Producto</th>
                          <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">Lote</th>
                          <th className="px-3 py-2 text-center text-xs font-medium text-gray-500">Cantidad</th>
                          <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">Dosis</th>
                          <th className="px-3 py-2 text-center text-xs font-medium text-gray-500">Acciones</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200">
                        {formData.detalles.map((det, index) => (
                          <tr key={index}>
                            <td className="px-3 py-2 text-sm">{det.producto_nombre}</td>
                            <td className="px-3 py-2 text-sm font-mono">{det.lote_numero}</td>
                            <td className="px-3 py-2 text-sm text-center">{det.cantidad_prescrita}</td>
                            <td className="px-3 py-2 text-sm">
                              {det.dosis && <span>{det.dosis}</span>}
                              {det.frecuencia && <span className="text-gray-500"> - {det.frecuencia}</span>}
                            </td>
                            <td className="px-3 py-2 text-center">
                              <button
                                type="button"
                                onClick={() => removeDetalle(index)}
                                className="text-red-600 hover:text-red-800"
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
                  <div className="text-center py-8 text-gray-500 border-2 border-dashed rounded-lg">
                    <FaBoxOpen className="mx-auto h-8 w-8 mb-2" />
                    <p>No hay medicamentos agregados</p>
                  </div>
                )}
              </div>

              {/* Observaciones */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-1">Observaciones</label>
                <textarea
                  name="observaciones"
                  value={formData.observaciones}
                  onChange={handleInputChange}
                  rows={2}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-guinda"
                />
              </div>

              {/* Botones */}
              <div className="flex justify-end gap-3 pt-4 border-t">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={formData.detalles.length === 0}
                  className="px-4 py-2 bg-guinda text-white rounded-lg hover:bg-guinda-dark transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {editingDispensacion ? 'Actualizar' : 'Crear Dispensación'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal de detalle */}
      {detailModal.show && detailModal.dispensacion && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b bg-guinda text-white rounded-t-lg">
              <h3 className="text-lg font-semibold">
                Detalle - {detailModal.dispensacion.folio}
              </h3>
              <button onClick={() => setDetailModal({ show: false, dispensacion: null })} className="hover:bg-white/20 p-1 rounded">
                <FaTimes />
              </button>
            </div>
            
            <div className="p-6">
              <div className="grid grid-cols-2 gap-4 text-sm mb-6">
                <div><span className="font-semibold">Folio:</span> {detailModal.dispensacion.folio}</div>
                <div><span className="font-semibold">Estado:</span> 
                  <span className={`ml-2 px-2 py-1 text-xs rounded-full ${ESTADO_COLORS[detailModal.dispensacion.estado]}`}>
                    {detailModal.dispensacion.estado}
                  </span>
                </div>
                <div><span className="font-semibold">Paciente:</span> {detailModal.dispensacion.paciente_nombre}</div>
                <div><span className="font-semibold">Expediente:</span> {detailModal.dispensacion.paciente_expediente}</div>
                <div><span className="font-semibold">Centro:</span> {detailModal.dispensacion.centro_nombre}</div>
                <div><span className="font-semibold">Tipo:</span> {detailModal.dispensacion.tipo_dispensacion}</div>
                <div><span className="font-semibold">Médico:</span> {detailModal.dispensacion.medico_prescriptor || '-'}</div>
                <div><span className="font-semibold">Diagnóstico:</span> {detailModal.dispensacion.diagnostico || '-'}</div>
                {detailModal.dispensacion.indicaciones_medicas && (
                  <div className="col-span-2"><span className="font-semibold">Indicaciones:</span> {detailModal.dispensacion.indicaciones_medicas}</div>
                )}
              </div>

              <h4 className="font-semibold mb-3">Medicamentos</h4>
              <div className="border rounded-lg overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-100">
                    <tr>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">Producto</th>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">Lote</th>
                      <th className="px-3 py-2 text-center text-xs font-medium text-gray-500">Prescrita</th>
                      <th className="px-3 py-2 text-center text-xs font-medium text-gray-500">Dispensada</th>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">Dosis</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {(detailModal.dispensacion.detalles || []).map((det, i) => (
                      <tr key={i}>
                        <td className="px-3 py-2 text-sm">{det.producto_nombre}</td>
                        <td className="px-3 py-2 text-sm font-mono">{det.lote_numero}</td>
                        <td className="px-3 py-2 text-sm text-center">{det.cantidad_prescrita}</td>
                        <td className="px-3 py-2 text-sm text-center">{det.cantidad_dispensada || 0}</td>
                        <td className="px-3 py-2 text-sm">
                          {det.dosis} {det.frecuencia && `- ${det.frecuencia}`}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal de confirmar dispensación */}
      <ConfirmModal
        isOpen={dispensarModal.show}
        onClose={() => setDispensarModal({ show: false, dispensacion: null })}
        onConfirm={handleDispensar}
        title="Confirmar Dispensación"
        message={`¿Está seguro de procesar la dispensación ${dispensarModal.dispensacion?.folio}? Esta acción descontará los medicamentos del inventario.`}
        confirmText="Dispensar"
        confirmStyle="success"
      />

      {/* Modal de cancelar */}
      {cancelModal.show && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
            <div className="flex items-center justify-between p-4 border-b bg-orange-500 text-white rounded-t-lg">
              <h3 className="text-lg font-semibold flex items-center">
                <FaExclamationTriangle className="mr-2" /> Cancelar Dispensación
              </h3>
              <button onClick={() => setCancelModal({ show: false, dispensacion: null, motivo: '' })} className="hover:bg-white/20 p-1 rounded">
                <FaTimes />
              </button>
            </div>
            <div className="p-6">
              <p className="text-gray-600 mb-4">
                ¿Está seguro de cancelar la dispensación <strong>{cancelModal.dispensacion?.folio}</strong>?
              </p>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Motivo de cancelación
                </label>
                <textarea
                  value={cancelModal.motivo}
                  onChange={(e) => setCancelModal(prev => ({ ...prev, motivo: e.target.value }))}
                  rows={3}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-orange-500"
                  placeholder="Ingrese el motivo..."
                />
              </div>
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => setCancelModal({ show: false, dispensacion: null, motivo: '' })}
                  className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
                >
                  No, volver
                </button>
                <button
                  onClick={handleCancelar}
                  className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600"
                >
                  Sí, cancelar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal de historial */}
      {historialModal.show && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b bg-guinda text-white rounded-t-lg">
              <h3 className="text-lg font-semibold flex items-center">
                <FaHistory className="mr-2" /> Historial - {historialModal.dispensacion?.folio}
              </h3>
              <button onClick={() => setHistorialModal({ show: false, dispensacion: null, historial: [] })} className="hover:bg-white/20 p-1 rounded">
                <FaTimes />
              </button>
            </div>
            <div className="p-6">
              {historialModal.historial.length > 0 ? (
                <div className="space-y-4">
                  {historialModal.historial.map((item, i) => (
                    <div key={i} className="flex items-start gap-4 p-3 bg-gray-50 rounded-lg">
                      <div className="flex-shrink-0 w-8 h-8 bg-guinda text-white rounded-full flex items-center justify-center text-sm">
                        {i + 1}
                      </div>
                      <div>
                        <div className="font-medium">{item.accion}</div>
                        <div className="text-sm text-gray-500">
                          {item.usuario_nombre} - {new Date(item.created_at).toLocaleString()}
                        </div>
                        {item.detalles && (
                          <div className="text-sm text-gray-600 mt-1">{item.detalles}</div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-center text-gray-500">No hay historial disponible</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Modal de confirmar eliminación */}
      <ConfirmModal
        isOpen={deleteModal.show}
        onClose={() => setDeleteModal({ show: false, dispensacion: null })}
        onConfirm={handleDelete}
        title="Eliminar Dispensación"
        message={`¿Está seguro de eliminar la dispensación ${deleteModal.dispensacion?.folio}?`}
        confirmText="Eliminar"
        confirmStyle="danger"
      />
    </div>
  );
};

export default Dispensaciones;
