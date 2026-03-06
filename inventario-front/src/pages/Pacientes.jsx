import { useState, useEffect, useCallback, useRef } from 'react';
import { pacientesAPI, centrosAPI } from '../services/api';
import { toast } from 'react-hot-toast';
import {
  FaPlus,
  FaEdit,
  FaTrash,
  FaSearch,
  FaUserInjured,
  FaIdCard,
  FaFilter,
  FaTimes,
  FaFileExcel,
  FaEye,
  FaMale,
  FaFemale,
  FaChevronDown,
  FaInfoCircle,
  FaFileUpload,
  FaDownload,
  FaSpinner,
  FaCheckCircle,
  FaExclamationTriangle,
  FaExchangeAlt,
  FaUserShield,
} from 'react-icons/fa';
import PageHeader from '../components/PageHeader';
import Pagination from '../components/Pagination';
import ConfirmModal from '../components/ConfirmModal';
import { usePermissions } from '../hooks/usePermissions';
import { esFarmaciaAdmin } from '../utils/roles';
import useEscapeToClose from '../hooks/useEscapeToClose';

const PAGE_SIZE = 25;

const SEXO_OPTIONS = [
  { value: '', label: 'Todos' },
  { value: 'M', label: 'Masculino' },
  { value: 'F', label: 'Femenino' },
];

const Pacientes = () => {
  const { user, verificarPermiso } = usePermissions();
  
  // Permisos específicos de pacientes (basados en rol del usuario)
  const puedeCrear = verificarPermiso('crearPaciente');
  const puedeEditar = verificarPermiso('editarPaciente');
  const puedeEliminar = verificarPermiso('eliminarPaciente');
  const puedeExportar = verificarPermiso('exportarPacientes');
  
  // Detectar tipo de usuario para UI adaptativa
  const esUsuarioFarmacia = esFarmaciaAdmin(user) && !puedeCrear;
  const esSoloAuditoria = esUsuarioFarmacia;

  // Estados
  const [pacientes, setPacientes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  
  // Filtros
  const [searchTerm, setSearchTerm] = useState('');
  const [centroFiltro, setCentroFiltro] = useState('');
  const [sexoFiltro, setSexoFiltro] = useState('');
  const [activoFiltro, setActivoFiltro] = useState('true');
  // Mostrar filtros expandidos por defecto para Farmacia
  const [showFilters, setShowFilters] = useState(esUsuarioFarmacia);
  
  // Centros para el filtro
  const [centros, setCentros] = useState([]);
  
  // Modal de formulario
  const [showModal, setShowModal] = useState(false);
  const [editingPaciente, setEditingPaciente] = useState(null);
  const [formData, setFormData] = useState({
    numero_expediente: '',
    nombre: '',
    apellido_paterno: '',
    apellido_materno: '',
    curp: '',
    fecha_nacimiento: '',
    sexo: '',
    centro: '',
    dormitorio: '',
    celda: '',
    tipo_sangre: '',
    alergias: '',
    enfermedades_cronicas: '',
    observaciones_medicas: '',
    activo: true,
    fecha_ingreso: '',
  });
  
  // Modal de confirmación
  const [deleteModal, setDeleteModal] = useState({ show: false, paciente: null });
  
  // Modal de detalle
  const [detailModal, setDetailModal] = useState({ show: false, paciente: null });

  // Modal de traspaso a otra unidad
  const [traspasoModal, setTraspasoModal] = useState({ show: false, paciente: null });
  const [traspasoData, setTraspasoData] = useState({ centro_destino: '', motivo: '', fecha_traspaso: '' });

  // Modal de importación
  const [importModal, setImportModal] = useState(false);
  const [importLoading, setImportLoading] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const fileInputRef = useRef(null);

  // ESC para cerrar modales
  useEscapeToClose({
    isOpen: showModal,
    onClose: () => setShowModal(false),
    modalId: 'pacientes-form-modal',
    disabled: false
  });

  useEscapeToClose({
    isOpen: detailModal.show,
    onClose: () => setDetailModal({ show: false, paciente: null }),
    modalId: 'pacientes-detail-modal',
    disabled: false
  });

  useEscapeToClose({
    isOpen: traspasoModal.show,
    onClose: () => setTraspasoModal({ show: false, paciente: null }),
    modalId: 'pacientes-traspaso-modal',
    disabled: false
  });

  useEscapeToClose({
    isOpen: deleteModal.show,
    onClose: () => setDeleteModal({ show: false, paciente: null }),
    modalId: 'pacientes-delete-modal',
    disabled: false
  });

  useEscapeToClose({
    isOpen: importModal,
    onClose: () => setImportModal(false),
    modalId: 'pacientes-import-modal',
    disabled: importLoading
  });

  // Cargar centros al montar
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

  // Cargar pacientes
  const fetchPacientes = useCallback(async () => {
    setLoading(true);
    try {
      const params = {
        page: currentPage,
        page_size: PAGE_SIZE,
        search: searchTerm || undefined,
        centro: centroFiltro || undefined,
        sexo: sexoFiltro || undefined,
        activo: activoFiltro !== '' ? activoFiltro : undefined,
      };
      
      const response = await pacientesAPI.getAll(params);
      const data = response.data;
      
      setPacientes(data?.results || data || []);
      setTotalItems(data?.count || data?.length || 0);
    } catch (error) {
      console.error('Error al cargar pacientes:', error);
      toast.error('Error al cargar pacientes');
      setPacientes([]);
    } finally {
      setLoading(false);
    }
  }, [currentPage, searchTerm, centroFiltro, sexoFiltro, activoFiltro]);

  useEffect(() => {
    fetchPacientes();
  }, [fetchPacientes]);

  // Handlers del formulario
  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const resetForm = () => {
    // ISS-SEC FIX: Usar fecha LOCAL para evitar desfase de zona horaria UTC
    const hoy = new Date();
    const fechaLocal = `${hoy.getFullYear()}-${String(hoy.getMonth() + 1).padStart(2, '0')}-${String(hoy.getDate()).padStart(2, '0')}`;
    
    setFormData({
      numero_expediente: '',
      nombre: '',
      apellido_paterno: '',
      apellido_materno: '',
      curp: '',
      fecha_nacimiento: '',
      sexo: '',
      centro: user?.centro?.id || '',
      dormitorio: '',
      celda: '',
      tipo_sangre: '',
      alergias: '',
      enfermedades_cronicas: '',
      observaciones_medicas: '',
      activo: true,
      fecha_ingreso: fechaLocal,
    });
    setEditingPaciente(null);
  };

  const handleOpenModal = (paciente = null) => {
    if (paciente) {
      setEditingPaciente(paciente);
      setFormData({
        numero_expediente: paciente.numero_expediente || '',
        nombre: paciente.nombre || '',
        apellido_paterno: paciente.apellido_paterno || '',
        apellido_materno: paciente.apellido_materno || '',
        curp: paciente.curp || '',
        fecha_nacimiento: paciente.fecha_nacimiento || '',
        sexo: paciente.sexo || '',
        centro: paciente.centro || '',
        dormitorio: paciente.dormitorio || '',
        celda: paciente.celda || '',
        tipo_sangre: paciente.tipo_sangre || '',
        alergias: paciente.alergias || '',
        enfermedades_cronicas: paciente.enfermedades_cronicas || '',
        observaciones_medicas: paciente.observaciones_medicas || '',
        activo: paciente.activo ?? true,
        fecha_ingreso: paciente.fecha_ingreso || '',
      });
    } else {
      resetForm();
    }
    setShowModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validaciones completas para todos los campos obligatorios
    if (!formData.numero_expediente.trim()) {
      toast.error('El número de expediente es requerido');
      return;
    }
    if (!formData.curp || formData.curp.length !== 18) {
      toast.error('El CURP debe tener exactamente 18 caracteres');
      return;
    }
    if (!formData.nombre.trim()) {
      toast.error('El nombre es requerido');
      return;
    }
    if (!formData.apellido_paterno.trim()) {
      toast.error('El apellido paterno es requerido');
      return;
    }
    if (!formData.apellido_materno.trim()) {
      toast.error('El apellido materno es requerido');
      return;
    }
    if (!formData.fecha_nacimiento) {
      toast.error('La fecha de nacimiento es requerida');
      return;
    }
    if (!formData.sexo) {
      toast.error('El sexo es requerido');
      return;
    }
    if (!formData.centro) {
      toast.error('El centro es requerido');
      return;
    }
    if (!formData.dormitorio.trim()) {
      toast.error('El dormitorio/módulo es requerido');
      return;
    }
    if (!formData.celda.trim()) {
      toast.error('La celda es requerida');
      return;
    }
    
    try {
      const dataToSend = {
        ...formData,
        centro: formData.centro || null,
        curp: formData.curp?.toUpperCase() || null,
      };
      
      if (editingPaciente) {
        await pacientesAPI.update(editingPaciente.id, dataToSend);
        toast.success('Paciente actualizado correctamente');
      } else {
        await pacientesAPI.create(dataToSend);
        toast.success('Paciente registrado correctamente');
      }
      
      setShowModal(false);
      resetForm();
      fetchPacientes();
    } catch (error) {
      console.error('Error al guardar paciente:', error);
      const errorMsg = error.response?.data?.detail || 
                       error.response?.data?.numero_expediente?.[0] ||
                       error.response?.data?.curp?.[0] ||
                       'Error al guardar paciente';
      toast.error(errorMsg);
    }
  };

  const handleDelete = async () => {
    if (!deleteModal.paciente) return;
    
    try {
      await pacientesAPI.delete(deleteModal.paciente.id);
      toast.success('PPL eliminado correctamente');
      setDeleteModal({ show: false, paciente: null });
      fetchPacientes();
    } catch (error) {
      console.error('Error al eliminar PPL:', error);
      toast.error('Error al eliminar PPL');
    }
  };

  // Función para traspasar PPL a otra unidad
  const handleTraspaso = async () => {
    if (!traspasoModal.paciente) return;
    
    // Validaciones
    if (!traspasoData.centro_destino) {
      toast.error('Debe seleccionar el centro de destino');
      return;
    }
    if (traspasoData.centro_destino === String(traspasoModal.paciente.centro)) {
      toast.error('El centro de destino debe ser diferente al actual');
      return;
    }
    if (!traspasoData.motivo.trim() || traspasoData.motivo.trim().length < 10) {
      toast.error('Debe indicar el motivo del traspaso (mínimo 10 caracteres)');
      return;
    }
    if (!traspasoData.fecha_traspaso) {
      toast.error('Debe indicar la fecha del traspaso');
      return;
    }
    
    try {
      // Actualizar el centro del paciente y registrar el traspaso en observaciones
      const centroDestinoNombre = centros.find(c => String(c.id) === traspasoData.centro_destino)?.nombre || 'N/D';
      const centroOrigenNombre = traspasoModal.paciente.centro_nombre || 'N/D';
      const observacionTraspaso = `[TRASPASO ${traspasoData.fecha_traspaso}] De ${centroOrigenNombre} a ${centroDestinoNombre}. Motivo: ${traspasoData.motivo}`;
      
      const observacionesActuales = traspasoModal.paciente.observaciones_medicas || '';
      const nuevasObservaciones = observacionesActuales 
        ? `${observacionesActuales}\n\n${observacionTraspaso}` 
        : observacionTraspaso;
      
      await pacientesAPI.update(traspasoModal.paciente.id, {
        centro: traspasoData.centro_destino,
        observaciones_medicas: nuevasObservaciones,
        // Resetear ubicación ya que cambia de centro
        dormitorio: '',
        celda: '',
      });
      
      toast.success(`PPL trasladado correctamente a ${centroDestinoNombre}`);
      setTraspasoModal({ show: false, paciente: null });
      setTraspasoData({ centro_destino: '', motivo: '', fecha_traspaso: '' });
      fetchPacientes();
    } catch (error) {
      console.error('Error al traspasar PPL:', error);
      toast.error('Error al realizar el traspaso');
    }
  };

  const handleExportExcel = async () => {
    try {
      const params = {
        centro: centroFiltro || undefined,
        sexo: sexoFiltro || undefined,
        activo: activoFiltro !== '' ? activoFiltro : undefined,
      };
      
      const response = await pacientesAPI.exportarExcel(params);
      
      const blob = new Blob([response.data], { 
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `pacientes_${new Date().toISOString().split('T')[0]}.xlsx`;
      a.click();
      window.URL.revokeObjectURL(url);
      
      toast.success('Excel exportado correctamente');
    } catch (error) {
      console.error('Error al exportar:', error);
      toast.error('Error al exportar Excel');
    }
  };

  // Descargar plantilla de importación
  const handleDownloadTemplate = async () => {
    try {
      const response = await pacientesAPI.descargarPlantilla();
      
      const blob = new Blob([response.data], { 
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'plantilla_pacientes_ppl.xlsx';
      a.click();
      window.URL.revokeObjectURL(url);
      
      toast.success('Plantilla descargada');
    } catch (error) {
      console.error('Error al descargar plantilla:', error);
      toast.error('Error al descargar plantilla');
    }
  };

  // Importar archivo Excel
  const handleImportExcel = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    
    // Validar extensión
    if (!file.name.endsWith('.xlsx')) {
      toast.error('Solo se aceptan archivos .xlsx');
      return;
    }
    
    // Validar tamaño (5MB)
    if (file.size > 5 * 1024 * 1024) {
      toast.error('El archivo es demasiado grande (máximo 5MB)');
      return;
    }
    
    setImportLoading(true);
    setImportResult(null);
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await pacientesAPI.importarExcel(formData);
      
      setImportResult(response.data);
      
      if (response.data.creados > 0 || response.data.actualizados > 0) {
        toast.success(response.data.mensaje);
        fetchPacientes(); // Recargar lista
      }
    } catch (error) {
      console.error('Error al importar:', error);
      const errorMsg = error.response?.data?.error || 'Error al importar archivo';
      toast.error(errorMsg);
      setImportResult({ error: errorMsg });
    } finally {
      setImportLoading(false);
      // Limpiar input para permitir reimportar mismo archivo
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const totalPages = Math.ceil(totalItems / PAGE_SIZE);

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Catálogo de PPL"
        subtitle="Gestión de Personas Privadas de la Libertad"
        icon={FaUserInjured}
      />

      {/* Barra de acciones */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-4">
        <div className="flex flex-col sm:flex-row gap-4 justify-between items-start sm:items-center">
          {/* Búsqueda */}
          <div className="relative flex-1 max-w-md">
            <FaSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Buscar por expediente, nombre, CURP..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-guinda focus:border-guinda"
            />
          </div>

          {/* Botones de acción */}
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
            
            {puedeExportar && (
              <button
                onClick={handleExportExcel}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              >
                <FaFileExcel />
                Exportar
              </button>
            )}
            
            {puedeCrear && (
              <>
                <button
                  onClick={handleDownloadTemplate}
                  className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
                  title="Descargar plantilla Excel para importar PPL"
                >
                  <FaDownload />
                  Plantilla
                </button>
                
                <button
                  onClick={() => setImportModal(true)}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  <FaFileUpload />
                  Importar PPL
                </button>
                
                <button
                  onClick={() => handleOpenModal()}
                  className="flex items-center gap-2 px-4 py-2 bg-guinda text-white rounded-lg hover:bg-guinda-dark transition-colors"
                >
                  <FaPlus />
                  Nuevo PPL
                </button>
              </>
            )}
          </div>
        </div>

        {/* Aviso para farmacia (modo auditoría) - Diseño elegante */}
        {esSoloAuditoria && (
          <div className="mt-4 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 border-l-4 border-blue-500 rounded-r-xl shadow-sm">
            <div className="flex items-center gap-3">
              <div className="flex-shrink-0 p-2 bg-blue-100 rounded-full">
                <FaUserShield className="text-blue-600 text-lg" />
              </div>
              <div>
                <h4 className="font-semibold text-blue-900">Modo Consulta</h4>
                <p className="text-sm text-blue-700">
                  Como personal de Farmacia Central, puede consultar el catálogo de PPL para auditoría pero no tiene permisos de edición.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Panel de filtros */}
        {showFilters && (
          <div className="mt-4 pt-4 border-t grid grid-cols-1 sm:grid-cols-3 gap-4">
            {/* Centro - solo visible para Farmacia */}
            {esUsuarioFarmacia && (
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
              <label className="block text-sm font-medium text-gray-700 mb-1">Sexo</label>
              <select
                value={sexoFiltro}
                onChange={(e) => {
                  setSexoFiltro(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-guinda"
              >
                {SEXO_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Estado</label>
              <select
                value={activoFiltro}
                onChange={(e) => {
                  setActivoFiltro(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-guinda"
              >
                <option value="">Todos</option>
                <option value="true">Activos</option>
                <option value="false">Inactivos</option>
              </select>
            </div>
          </div>
        )}
      </div>

      {/* Tabla de pacientes */}
      <div className="rounded-2xl border border-gray-200 bg-white shadow-sm">
        {loading ? (
          <div className="flex justify-center items-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-4 border-t-transparent spinner-institucional"></div>
          </div>
        ) : pacientes.length === 0 ? (
          <div className="text-center py-12">
            <FaUserInjured className="mx-auto h-12 w-12 text-gray-300" />
            <p className="mt-4 text-gray-500">No se encontraron pacientes</p>
          </div>
        ) : (
          <>
          {/* Vista móvil: tarjetas */}
          <div className="lg:hidden divide-y divide-gray-100">
            {pacientes.map((paciente) => (
              <div key={paciente.id} className="p-4">
                {/* Header con expediente y estado */}
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <FaIdCard className="text-guinda" />
                    <span className="font-medium text-gray-900">{paciente.numero_expediente}</span>
                  </div>
                  <span className={`px-2 py-1 text-xs rounded-full shrink-0 ${
                    paciente.activo ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                  }`}>
                    {paciente.activo ? 'Activo' : 'Inactivo'}
                  </span>
                </div>
                
                {/* Nombre y edad */}
                <div className="mb-2">
                  <div className="font-medium text-gray-900">{paciente.nombre_completo}</div>
                  <div className="flex items-center gap-2 text-sm text-gray-500">
                    {paciente.edad && <span>{paciente.edad} años</span>}
                    {paciente.sexo === 'M' ? (
                      <FaMale className="text-blue-500" title="Masculino" />
                    ) : paciente.sexo === 'F' ? (
                      <FaFemale className="text-pink-500" title="Femenino" />
                    ) : null}
                  </div>
                </div>
                
                {/* Info grid */}
                <div className="grid grid-cols-1 gap-1 text-sm mb-3">
                  {paciente.curp && (
                    <div className="text-gray-500 truncate">
                      <span className="font-medium">CURP:</span> {paciente.curp}
                    </div>
                  )}
                  {paciente.centro_nombre && (
                    <div className="text-gray-500">
                      <span className="font-medium">Centro:</span> {paciente.centro_nombre}
                    </div>
                  )}
                  {paciente.ubicacion_completa && (
                    <div className="text-gray-500">
                      <span className="font-medium">Ubicación:</span> {paciente.ubicacion_completa}
                    </div>
                  )}
                </div>
                
                {/* Acciones */}
                <div className="flex items-center gap-2 pt-2 border-t border-gray-100">
                  <button
                    onClick={() => setDetailModal({ show: true, paciente })}
                    className="flex-1 px-3 py-2 text-sm text-gray-600 bg-gray-100 rounded-lg flex items-center justify-center gap-1"
                  >
                    <FaEye /> Ver
                  </button>
                  {puedeEditar && (
                    <button
                      onClick={() => handleOpenModal(paciente)}
                      className="flex-1 px-3 py-2 text-sm text-guinda bg-guinda/10 rounded-lg flex items-center justify-center gap-1"
                    >
                      <FaEdit /> Editar
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
          
          {/* Vista desktop: tabla */}
          <div className="hidden lg:block w-full overflow-x-auto">
            <table className="w-full min-w-[1000px] divide-y divide-gray-200">
              <thead className="bg-theme-gradient sticky top-0 z-10">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Expediente</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Nombre</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">CURP</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Centro</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Ubicación</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Sexo</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Estado</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Acciones</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-100">
                {pacientes.map((paciente) => (
                  <tr key={paciente.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="flex items-center">
                        <FaIdCard className="text-guinda mr-2" />
                        <span className="font-medium text-gray-900">{paciente.numero_expediente}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-sm font-medium text-gray-900">{paciente.nombre_completo}</div>
                      {paciente.edad && (
                        <div className="text-xs text-gray-500">{paciente.edad} años</div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {paciente.curp || '-'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {paciente.centro_nombre || '-'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {paciente.ubicacion_completa || '-'}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {paciente.sexo === 'M' ? (
                        <FaMale className="inline text-blue-500" title="Masculino" />
                      ) : paciente.sexo === 'F' ? (
                        <FaFemale className="inline text-pink-500" title="Femenino" />
                      ) : '-'}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        paciente.activo 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {paciente.activo ? 'Activo' : 'Inactivo'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <div className="flex justify-center gap-2">
                        <button
                          onClick={() => setDetailModal({ show: true, paciente })}
                          className="text-gray-500 hover:text-guinda p-1"
                          title="Ver detalle"
                        >
                          <FaEye />
                        </button>
                        {puedeEditar && (
                          <>
                            <button
                              onClick={() => handleOpenModal(paciente)}
                              className="text-blue-600 hover:text-blue-800 p-1"
                              title="Editar"
                            >
                              <FaEdit />
                            </button>
                            <button
                              onClick={() => {
                                setTraspasoModal({ show: true, paciente });
                                setTraspasoData({ 
                                  centro_destino: '', 
                                  motivo: '', 
                                  fecha_traspaso: new Date().toISOString().split('T')[0] 
                                });
                              }}
                              className="text-orange-600 hover:text-orange-800 p-1"
                              title="Traspasar a otra unidad"
                            >
                              <FaExchangeAlt />
                            </button>
                          </>
                        )}
                        {puedeEliminar && (
                          <button
                            onClick={() => setDeleteModal({ show: true, paciente })}
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
          </>
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
          <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b bg-gradient-to-r from-guinda to-guinda-dark text-white rounded-t-lg">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-white/20 rounded-lg">
                  <FaUserInjured className="text-xl" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold">
                    {editingPaciente ? 'Editar PPL' : 'Nuevo PPL'}
                  </h3>
                  <p className="text-xs text-white/70">Persona Privada de la Libertad</p>
                </div>
              </div>
              <button onClick={() => setShowModal(false)} className="hover:bg-white/20 p-2 rounded-lg transition-colors">
                <FaTimes />
              </button>
            </div>
            
            <form onSubmit={handleSubmit} className="p-6">
              {/* Datos de identificación */}
              <div className="mb-6">
                <h4 className="text-sm font-semibold text-gray-700 mb-3 pb-2 border-b">
                  Datos de Identificación
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      No. Expediente <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      name="numero_expediente"
                      value={formData.numero_expediente}
                      onChange={handleInputChange}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-guinda"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      CURP <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      name="curp"
                      value={formData.curp}
                      onChange={handleInputChange}
                      maxLength={18}
                      minLength={18}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-guinda uppercase"
                      required
                      placeholder="18 caracteres"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Nombre <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      name="nombre"
                      value={formData.nombre}
                      onChange={handleInputChange}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-guinda"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Apellido Paterno <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      name="apellido_paterno"
                      value={formData.apellido_paterno}
                      onChange={handleInputChange}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-guinda"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Apellido Materno <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      name="apellido_materno"
                      value={formData.apellido_materno}
                      onChange={handleInputChange}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-guinda"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Fecha de Nacimiento <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="date"
                      name="fecha_nacimiento"
                      value={formData.fecha_nacimiento}
                      onChange={handleInputChange}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-guinda"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Sexo <span className="text-red-500">*</span>
                    </label>
                    <select
                      name="sexo"
                      value={formData.sexo}
                      onChange={handleInputChange}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-guinda"
                      required
                    >
                      <option value="">Seleccionar</option>
                      <option value="M">Masculino</option>
                      <option value="F">Femenino</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de Sangre</label>
                    <select
                      name="tipo_sangre"
                      value={formData.tipo_sangre}
                      onChange={handleInputChange}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-guinda"
                    >
                      <option value="">Seleccionar</option>
                      <option value="A+">A+</option>
                      <option value="A-">A-</option>
                      <option value="B+">B+</option>
                      <option value="B-">B-</option>
                      <option value="AB+">AB+</option>
                      <option value="AB-">AB-</option>
                      <option value="O+">O+</option>
                      <option value="O-">O-</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Ubicación */}
              <div className="mb-6">
                <h4 className="text-sm font-semibold text-gray-700 mb-3 pb-2 border-b">
                  Ubicación en Centro
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
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
                      Dormitorio/Módulo <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      name="dormitorio"
                      value={formData.dormitorio}
                      onChange={handleInputChange}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-guinda"
                      required
                      placeholder="Ej: Dorm. 1"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Celda <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      name="celda"
                      value={formData.celda}
                      onChange={handleInputChange}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-guinda"
                      required
                      placeholder="Ej: 101"
                    />
                  </div>
                </div>
              </div>

              {/* Información médica */}
              <div className="mb-6">
                <h4 className="text-sm font-semibold text-gray-700 mb-3 pb-2 border-b">
                  Información Médica
                </h4>
                <div className="grid grid-cols-1 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Alergias</label>
                    <textarea
                      name="alergias"
                      value={formData.alergias}
                      onChange={handleInputChange}
                      rows={2}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-guinda"
                      placeholder="Alergias conocidas..."
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Enfermedades Crónicas</label>
                    <textarea
                      name="enfermedades_cronicas"
                      value={formData.enfermedades_cronicas}
                      onChange={handleInputChange}
                      rows={2}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-guinda"
                      placeholder="Diabetes, hipertensión, etc..."
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Observaciones Médicas</label>
                    <textarea
                      name="observaciones_medicas"
                      value={formData.observaciones_medicas}
                      onChange={handleInputChange}
                      rows={2}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-guinda"
                    />
                  </div>
                </div>
              </div>

              {/* Estado y fechas */}
              <div className="mb-6">
                <h4 className="text-sm font-semibold text-gray-700 mb-3 pb-2 border-b">
                  Estado y Control
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Fecha de Ingreso</label>
                    <input
                      type="date"
                      name="fecha_ingreso"
                      value={formData.fecha_ingreso}
                      onChange={handleInputChange}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-guinda"
                    />
                  </div>
                  <div className="flex items-center">
                    <label className="flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        name="activo"
                        checked={formData.activo}
                        onChange={handleInputChange}
                        className="mr-2 h-4 w-4 text-guinda focus:ring-guinda border-gray-300 rounded"
                      />
                      <span className="text-sm font-medium text-gray-700">Paciente Activo</span>
                    </label>
                  </div>
                </div>
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
                  className="px-4 py-2 bg-guinda text-white rounded-lg hover:bg-guinda-dark transition-colors"
                >
                  {editingPaciente ? 'Actualizar' : 'Registrar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal de detalle */}
      {detailModal.show && detailModal.paciente && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b bg-guinda text-white rounded-t-lg">
              <h3 className="text-lg font-semibold">Detalle del Paciente</h3>
              <button onClick={() => setDetailModal({ show: false, paciente: null })} className="hover:bg-white/20 p-1 rounded">
                <FaTimes />
              </button>
            </div>
            
            <div className="p-6">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div><span className="font-semibold">Expediente:</span> {detailModal.paciente.numero_expediente}</div>
                <div><span className="font-semibold">CURP:</span> {detailModal.paciente.curp || '-'}</div>
                <div className="col-span-2"><span className="font-semibold">Nombre Completo:</span> {detailModal.paciente.nombre_completo}</div>
                <div><span className="font-semibold">Edad:</span> {detailModal.paciente.edad ? `${detailModal.paciente.edad} años` : '-'}</div>
                <div><span className="font-semibold">Sexo:</span> {detailModal.paciente.sexo === 'M' ? 'Masculino' : detailModal.paciente.sexo === 'F' ? 'Femenino' : '-'}</div>
                <div><span className="font-semibold">Tipo de Sangre:</span> {detailModal.paciente.tipo_sangre || '-'}</div>
                <div><span className="font-semibold">Centro:</span> {detailModal.paciente.centro_nombre || '-'}</div>
                <div><span className="font-semibold">Ubicación:</span> {detailModal.paciente.ubicacion_completa || '-'}</div>
                <div><span className="font-semibold">Fecha Ingreso:</span> {detailModal.paciente.fecha_ingreso || '-'}</div>
                <div className="col-span-2"><span className="font-semibold">Alergias:</span> {detailModal.paciente.alergias || 'Ninguna registrada'}</div>
                <div className="col-span-2"><span className="font-semibold">Enfermedades Crónicas:</span> {detailModal.paciente.enfermedades_cronicas || 'Ninguna registrada'}</div>
                <div className="col-span-2"><span className="font-semibold">Observaciones:</span> {detailModal.paciente.observaciones_medicas || '-'}</div>
                <div><span className="font-semibold">Total Dispensaciones:</span> {detailModal.paciente.total_dispensaciones || 0}</div>
                <div><span className="font-semibold">Estado:</span> 
                  <span className={`ml-2 px-2 py-1 text-xs rounded-full ${detailModal.paciente.activo ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                    {detailModal.paciente.activo ? 'Activo' : 'Inactivo'}
                  </span>
                </div>
                
                {/* Trazabilidad: quién registró este paciente */}
                <div className="col-span-2 pt-3 mt-3 border-t border-gray-200">
                  <div className="flex items-center gap-2">
                    <FaUserShield className="text-guinda" />
                    <span className="font-semibold text-guinda">Registrado por:</span>
                    <span className="text-gray-700">{detailModal.paciente.created_by_nombre || '-'}</span>
                    {detailModal.paciente.created_at && (
                      <span className="text-gray-400 text-xs ml-2">
                        ({new Date(detailModal.paciente.created_at).toLocaleDateString()})
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal de confirmación de eliminación */}
      <ConfirmModal
        open={deleteModal.show}
        onCancel={() => setDeleteModal({ show: false, paciente: null })}
        onConfirm={handleDelete}
        title="Eliminar PPL"
        message={`¿Está seguro de eliminar al PPL ${deleteModal.paciente?.nombre_completo}? Esta acción no se puede deshacer.`}
        confirmText="Eliminar"
        tone="danger"
      />

      {/* Modal de Importación de PPL */}
      {importModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-lg w-full">
            <div className="flex items-center justify-between p-4 border-b bg-blue-600 text-white rounded-t-lg">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <FaFileUpload />
                Importar Pacientes / PPL
              </h3>
              <button 
                onClick={() => {
                  setImportModal(false);
                  setImportResult(null);
                }} 
                className="hover:bg-white/20 p-1 rounded"
              >
                <FaTimes />
              </button>
            </div>
            
            <div className="p-6">
              {/* Instrucciones */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                <h4 className="font-semibold text-blue-800 mb-2">Instrucciones:</h4>
                <ol className="text-sm text-blue-700 space-y-1 list-decimal list-inside">
                  <li>Descargue la plantilla Excel</li>
                  <li>Complete los datos de los PPL (campos con * son obligatorios)</li>
                  <li>Suba el archivo completado</li>
                  <li>Los expedientes existentes se actualizarán automáticamente</li>
                </ol>
              </div>
              
              {/* Botón descargar plantilla */}
              <button
                onClick={handleDownloadTemplate}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors mb-4"
              >
                <FaDownload />
                Descargar Plantilla Excel
              </button>
              
              {/* Input de archivo */}
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-400 transition-colors">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".xlsx"
                  onChange={handleImportExcel}
                  className="hidden"
                  id="import-file"
                  disabled={importLoading}
                />
                <label 
                  htmlFor="import-file" 
                  className={`cursor-pointer ${importLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  {importLoading ? (
                    <div className="flex flex-col items-center gap-2">
                      <FaSpinner className="w-10 h-10 text-blue-500 animate-spin" />
                      <span className="text-gray-600">Procesando archivo...</span>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center gap-2">
                      <FaFileUpload className="w-10 h-10 text-gray-400" />
                      <span className="text-gray-600">Haga clic para seleccionar archivo</span>
                      <span className="text-xs text-gray-400">Solo archivos .xlsx (máximo 5MB)</span>
                    </div>
                  )}
                </label>
              </div>
              
              {/* Resultado de importación */}
              {importResult && (
                <div className={`mt-4 p-4 rounded-lg ${
                  importResult.error 
                    ? 'bg-red-50 border border-red-200' 
                    : 'bg-green-50 border border-green-200'
                }`}>
                  {importResult.error ? (
                    <div className="flex items-start gap-2 text-red-700">
                      <FaExclamationTriangle className="mt-0.5 flex-shrink-0" />
                      <span>{importResult.error}</span>
                    </div>
                  ) : (
                    <>
                      <div className="flex items-center gap-2 text-green-700 font-semibold mb-2">
                        <FaCheckCircle />
                        <span>{importResult.mensaje}</span>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <div className="bg-white p-2 rounded">
                          <span className="font-semibold text-green-600">{importResult.creados}</span>
                          <span className="text-gray-600 ml-1">nuevos</span>
                        </div>
                        <div className="bg-white p-2 rounded">
                          <span className="font-semibold text-blue-600">{importResult.actualizados}</span>
                          <span className="text-gray-600 ml-1">actualizados</span>
                        </div>
                      </div>
                      
                      {/* Mostrar errores si los hay */}
                      {importResult.errores && importResult.errores.length > 0 && (
                        <div className="mt-3">
                          <p className="text-sm font-semibold text-orange-700 mb-1">
                            Advertencias ({importResult.total_errores}):
                          </p>
                          <div className="max-h-32 overflow-y-auto bg-white p-2 rounded text-xs text-orange-600">
                            {importResult.errores.map((err, idx) => (
                              <div key={idx} className="py-0.5">{err}</div>
                            ))}
                          </div>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
            
            <div className="flex justify-end gap-2 p-4 border-t bg-gray-50 rounded-b-lg">
              <button
                onClick={() => {
                  setImportModal(false);
                  setImportResult(null);
                }}
                className="px-4 py-2 text-gray-700 bg-white border rounded-lg hover:bg-gray-50"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Traspaso de PPL a otra unidad */}
      {traspasoModal.show && traspasoModal.paciente && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full">
            {/* Header elegante */}
            <div className="p-5 border-b bg-gradient-to-r from-orange-500 to-amber-500 text-white rounded-t-xl">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-white/20 rounded-lg">
                  <FaExchangeAlt className="text-xl" />
                </div>
                <div>
                  <h3 className="text-lg font-bold">Traspaso de PPL</h3>
                  <p className="text-sm text-white/80">Traslado a otra Unidad Penitenciaria</p>
                </div>
              </div>
            </div>
            
            <div className="p-6">
              {/* Información del PPL */}
              <div className="bg-gray-50 rounded-xl p-4 mb-5 border">
                <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                  <FaUserInjured className="text-guinda" />
                  PPL a Trasladar
                </h4>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-gray-500">Expediente:</span>
                    <span className="ml-2 font-semibold">{traspasoModal.paciente.numero_expediente}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Nombre:</span>
                    <span className="ml-2 font-semibold">{traspasoModal.paciente.nombre_completo}</span>
                  </div>
                  <div className="col-span-2">
                    <span className="text-gray-500">Centro Actual:</span>
                    <span className="ml-2 font-semibold text-guinda">{traspasoModal.paciente.centro_nombre || 'Sin asignar'}</span>
                  </div>
                </div>
              </div>
              
              {/* Formulario de traspaso */}
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-1">
                    Centro de Destino <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={traspasoData.centro_destino}
                    onChange={(e) => setTraspasoData(prev => ({ ...prev, centro_destino: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-orange-400 focus:border-orange-400"
                  >
                    <option value="">Seleccionar nuevo centro...</option>
                    {centros
                      .filter(c => String(c.id) !== String(traspasoModal.paciente?.centro))
                      .map(centro => (
                        <option key={centro.id} value={centro.id}>{centro.nombre}</option>
                      ))}
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-1">
                    Fecha del Traspaso <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="date"
                    value={traspasoData.fecha_traspaso}
                    onChange={(e) => setTraspasoData(prev => ({ ...prev, fecha_traspaso: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-orange-400 focus:border-orange-400"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-1">
                    Motivo del Traspaso <span className="text-red-500">*</span>
                  </label>
                  <textarea
                    value={traspasoData.motivo}
                    onChange={(e) => setTraspasoData(prev => ({ ...prev, motivo: e.target.value }))}
                    rows={3}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-orange-400 focus:border-orange-400"
                    placeholder="Indique el motivo del traslado (ej: orden judicial, solicitud de traslado, etc.)"
                  />
                  <p className="text-xs text-gray-500 mt-1">Mínimo 10 caracteres. Esta información quedará registrada en el historial.</p>
                </div>
              </div>
              
              {/* Nota informativa */}
              <div className="mt-4 p-3 bg-amber-50 border-l-4 border-amber-400 rounded-r-lg">
                <p className="text-sm text-amber-800">
                  <strong>Nota:</strong> Al trasladar el PPL, la ubicación (dormitorio/celda) se reiniciará y deberá asignarse en el nuevo centro.
                </p>
              </div>
            </div>
            
            {/* Footer */}
            <div className="flex justify-end gap-3 p-4 border-t bg-gray-50 rounded-b-xl">
              <button
                onClick={() => {
                  setTraspasoModal({ show: false, paciente: null });
                  setTraspasoData({ centro_destino: '', motivo: '', fecha_traspaso: '' });
                }}
                className="px-4 py-2 text-gray-700 bg-white border rounded-lg hover:bg-gray-100 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={handleTraspaso}
                className="px-4 py-2 bg-gradient-to-r from-orange-500 to-amber-500 text-white rounded-lg hover:from-orange-600 hover:to-amber-600 transition-all flex items-center gap-2 font-medium"
              >
                <FaExchangeAlt />
                Confirmar Traspaso
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Pacientes;
