import { useState, useEffect, useCallback } from 'react';
import { centrosAPI } from '../services/api';
import { toast } from 'react-hot-toast';
import { hasAccessToken } from '../services/tokenManager';
import { usePermissions } from '../hooks/usePermissions';
import Pagination from '../components/Pagination';
import { 
  FaPlus, FaEdit, FaTrash, FaToggleOn, FaToggleOff, 
  FaSearch, FaFileExcel, FaFileUpload, FaDownload, FaFilter,
  FaBuilding, FaChevronDown, FaTimes, FaSpinner
} from 'react-icons/fa';
import PageHeader from '../components/PageHeader';
import { COLORS, SECONDARY_GRADIENT } from '../constants/theme';
// ISS-SEC: Componentes para confirmación en 2 pasos
import TwoStepConfirmModal from '../components/TwoStepConfirmModal';
import { useConfirmation } from '../hooks/useConfirmation';
import useEscapeToClose from '../hooks/useEscapeToClose';

const PAGE_SIZE = 25;

// Extensiones y tamaño máximo permitidos para importación
const IMPORT_ALLOWED_EXTENSIONS = ['.xlsx', '.xls'];
const IMPORT_MAX_FILE_SIZE_MB = 10;

const MOCK_CENTROS = Array.from({ length: 15 }).map((_, index) => ({
  id: index + 1,
  nombre: `Centro Penitenciario Simulado ${index + 1}`,
  direccion: `Dirección ${index + 1}, Municipio Simulado`,
  telefono: `(555) 000-00${String(index).padStart(2, '0')}`,
  email: `centro${index + 1}@ejemplo.gob.mx`,
  activo: index % 4 !== 0,
  total_requisiciones: 5 + index,
  total_usuarios: 10 + index * 2,
}));

const Centros = () => {
  const { permisos } = usePermissions();
  const [centros, setCentros] = useState([]);
  const [loading, setLoading] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);
  const [importLoading, setImportLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(null); // ID del centro en acción
  const [showModal, setShowModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [editingCentro, setEditingCentro] = useState(null);
  
  // Paginación
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCentros, setTotalCentros] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  
  // Filtros
  const [searchTerm, setSearchTerm] = useState('');
  const [filtroEstado, setFiltroEstado] = useState('');
  const [showFiltersMenu, setShowFiltersMenu] = useState(false);
  
  // ISS-SEC: Hook para confirmación en 2 pasos
  const {
    confirmState,
    requestDeleteConfirmation,
    executeWithConfirmation,
    cancelConfirmation,
  } = useConfirmation();
  
  // Permisos derivados
  const puedeEditar = permisos.isFarmaciaAdmin || permisos.isAdmin || permisos.isSuperuser;
  const puedeCrear = puedeEditar;
  const puedeEliminar = puedeEditar;
  const puedeImportar = puedeEditar;
  const puedeExportar = puedeEditar || permisos.isVista;
  
  const [formData, setFormData] = useState({
    nombre: '',
    direccion: '',
    telefono: '',
    email: '',
    activo: true
  });

  // ESC para cerrar modales
  useEscapeToClose({
    isOpen: showModal,
    onClose: () => { setShowModal(false); resetForm(); },
    modalId: 'centros-form-modal',
    disabled: false
  });

  useEscapeToClose({
    isOpen: showImportModal,
    onClose: () => setShowImportModal(false),
    modalId: 'centros-import-modal',
    disabled: importLoading
  });

  // eslint-disable-next-line no-unused-vars
  const aplicarCentrosMock = useCallback(() => {
    let data = [...MOCK_CENTROS];
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      data = data.filter(
        (centro) =>
          centro.nombre.toLowerCase().includes(term) ||
          (centro.direccion && centro.direccion.toLowerCase().includes(term)) ||
          (centro.email && centro.email.toLowerCase().includes(term))
      );
    }
    if (filtroEstado) {
      const activos = filtroEstado === 'activo';
      data = data.filter((centro) => centro.activo === activos);
    }
    setCentros(data);
    setLoading(false);
  }, [filtroEstado, searchTerm]);

  const cargarCentros = useCallback(async () => {
    setLoading(true);
    try {
      if (!hasAccessToken()) {
        throw new Error('Sesión no encontrada');
      }

      const params = {
        page: currentPage,
        page_size: PAGE_SIZE,
        ordering: 'nombre',
      };
      
      if (searchTerm) params.search = searchTerm;
      if (filtroEstado) params.activo = filtroEstado === 'activo';
      
      const response = await centrosAPI.getAll(params);
      const results = response.data.results || response.data;
      setCentros(Array.isArray(results) ? results : []);
      
      // Usar el total del backend para paginación correcta
      const total = response.data.count || (Array.isArray(results) ? results.length : 0);
      setTotalCentros(total);
      setTotalPages(Math.max(1, Math.ceil(total / PAGE_SIZE)));
    } catch (error) {
      toast.error('Error al cargar centros');
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, [currentPage, filtroEstado, searchTerm]);

  useEffect(() => {
    setCurrentPage(1);
  }, [filtroEstado, searchTerm]);

  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      cargarCentros();
    }, 500);

    return () => clearTimeout(delayDebounceFn);
  }, [cargarCentros]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      if (editingCentro) {
        await centrosAPI.update(editingCentro.id, formData);
        toast.success('Centro actualizado correctamente');
      } else {
        await centrosAPI.create(formData);
        toast.success('Centro creado correctamente');
      }
      
      setShowModal(false);
      resetForm();
      cargarCentros();
    } catch (error) {
      const errorMsg = error.response?.data?.clave?.[0] || 
                       error.response?.data?.nombre?.[0] ||
                       error.response?.data?.error || 
                       'Error al guardar centro';
      toast.error(errorMsg);
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (centro) => {
    setEditingCentro(centro);
    setFormData({
      nombre: centro.nombre || '',
      direccion: centro.direccion || '',
      telefono: centro.telefono || '',
      email: centro.email || '',
      activo: centro.activo
    });
    setShowModal(true);
  };

  // ISS-SEC: Función auxiliar para ejecutar toggle activo con confirmación
  const executeToggleActivo = async ({ actionData }) => {
    const { centro, nuevoEstado } = actionData;
    
    setActionLoading(centro.id);
    try {
      const response = await centrosAPI.toggleActivo(centro.id);
      toast.success(response.data?.mensaje || `Centro ${nuevoEstado ? 'activado' : 'desactivado'}`);
      cargarCentros();
    } catch (error) {
      const errorMsg = error.response?.data?.error || 
                       error.response?.data?.detail ||
                       'Error al cambiar estado';
      toast.error(errorMsg);
      throw error;
    } finally {
      setActionLoading(null);
    }
  };

  // ISS-SEC: handleToggleActivo ahora usa confirmación en 2 pasos
  const handleToggleActivo = (centro) => {
    if (actionLoading) return;
    
    const nuevoEstado = !centro.activo;
    const accion = nuevoEstado ? 'activar' : 'desactivar';
    
    requestDeleteConfirmation({
      title: `${nuevoEstado ? 'Activar' : 'Desactivar'} centro`,
      message: `¿Está seguro de ${accion} el centro "${centro.nombre}"?`,
      itemInfo: {
        'Nombre': centro.nombre,
        'Estado actual': centro.activo ? 'Activo' : 'Inactivo',
        'Nuevo estado': nuevoEstado ? 'Activo' : 'Inactivo'
      },
      onConfirm: executeToggleActivo,
      actionData: { centro, nuevoEstado },
      isCritical: false,
      confirmText: nuevoEstado ? 'Activar' : 'Desactivar'
    });
  };

  // ISS-SEC: Función auxiliar para ejecutar eliminación de centro con confirmación
  const executeDeleteCentro = async ({ confirmed, actionData }) => {
    const { centro } = actionData;
    
    setActionLoading(centro.id);
    try {
      await centrosAPI.delete(centro.id, { confirmed });
      toast.success('Centro eliminado correctamente');
      cargarCentros();
    } catch (error) {
      // Mostrar mensaje específico del backend
      let errorMsg = 'Error al eliminar centro';
      if (error.response?.data?.error) {
        errorMsg = error.response.data.error;
      } else if (error.response?.data?.detail) {
        errorMsg = error.response.data.detail;
      } else if (error.response?.status === 403) {
        errorMsg = 'No tiene permisos para eliminar este centro';
      } else if (error.response?.status === 409 || error.response?.data?.requisiciones || error.response?.data?.usuarios) {
        errorMsg = 'No se puede eliminar: el centro tiene requisiciones o usuarios asociados';
      }
      toast.error(errorMsg);
      throw error;
    } finally {
      setActionLoading(null);
    }
  };

  // ISS-SEC: handleDelete ahora inicia el flujo de confirmación en 2 pasos
  const handleDelete = (centro) => {
    if (actionLoading) return; // Prevenir doble clic
    
    // Verificar si tiene dependencias para construir advertencias
    const tieneRequisiciones = (centro.total_requisiciones || 0) > 0;
    const tieneUsuarios = (centro.total_usuarios || 0) > 0;
    
    const warnings = [
      'Esta acción eliminará permanentemente el centro',
      'Esta acción no se puede deshacer'
    ];
    
    if (tieneRequisiciones) {
      warnings.push(`⚠️ Tiene ${centro.total_requisiciones} requisiciones asociadas`);
    }
    if (tieneUsuarios) {
      warnings.push(`⚠️ Tiene ${centro.total_usuarios} usuarios asignados`);
    }
    if (tieneRequisiciones || tieneUsuarios) {
      warnings.push('Es posible que el sistema impida la eliminación');
    }
    
    // Solicitar confirmación en 2 pasos con escritura de "ELIMINAR"
    requestDeleteConfirmation({
      title: 'Confirmar Eliminación de Centro',
      message: '¿Está seguro de ELIMINAR PERMANENTEMENTE este centro penitenciario?',
      warnings,
      itemInfo: {
        'Nombre': centro.nombre,
        'Dirección': centro.direccion || 'N/A',
        'Requisiciones': centro.total_requisiciones || 0,
        'Usuarios': centro.total_usuarios || 0
      },
      isCritical: true,
      confirmPhrase: 'ELIMINAR',
      confirmText: 'Eliminar Centro',
      cancelText: 'Cancelar',
      tone: 'danger',
      onConfirm: executeDeleteCentro,
      actionData: { centro }
    });
  };

  const resetForm = () => {
    setFormData({
      nombre: '',
      direccion: '',
      telefono: '',
      email: '',
      activo: true
    });
    setEditingCentro(null);
  };

  const limpiarFiltros = () => {
    setSearchTerm('');
    setFiltroEstado('');
  };

  const handleDescargarPlantilla = async () => {
    if (exportLoading) return; // Prevenir doble clic
    
    try {
      setExportLoading(true);
      const response = await centrosAPI.plantilla();
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'plantilla_centros.xlsx');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success('Plantilla descargada correctamente');
    } catch (error) {
      toast.error('Error al descargar plantilla');
    } finally {
      setExportLoading(false);
    }
  };

  const handleExportar = async () => {
    if (exportLoading) return; // Prevenir doble clic
    
    try {
      setExportLoading(true);
      const params = {};
      if (filtroEstado) params.activo = filtroEstado === 'activo';
      if (searchTerm) params.search = searchTerm;
      
      const response = await centrosAPI.exportar(params);
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `centros_${new Date().toISOString().split('T')[0]}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success('Centros exportados correctamente');
    } catch (error) {
      toast.error('Error al exportar centros');
    } finally {
      setExportLoading(false);
    }
  };

  const filtrosActivos = [searchTerm, filtroEstado].filter(Boolean).length;

  const headerActions = (
    <>
      {puedeExportar && (
        <button
          type="button"
          onClick={handleDescargarPlantilla}
          disabled={exportLoading}
          className="cc-btn cc-btn-ghost"
          title="Descargar Plantilla"
        >
          {exportLoading ? <FaSpinner className="animate-spin" /> : <FaDownload />} 
          {exportLoading ? 'Descargando...' : 'Plantilla'}
        </button>
      )}
      {puedeExportar && (
        <button
          type="button"
          onClick={handleExportar}
          disabled={exportLoading}
          className="cc-btn cc-btn-secondary"
        >
          {exportLoading ? <FaSpinner className="animate-spin" /> : <FaFileExcel />} 
          {exportLoading ? 'Exportando...' : 'Exportar'}
        </button>
      )}
      {puedeImportar && (
        <button
          type="button"
          onClick={() => setShowImportModal(true)}
          disabled={importLoading}
          className="cc-btn cc-btn-secondary"
        >
          {importLoading ? <FaSpinner className="animate-spin" /> : <FaFileUpload />} 
          {importLoading ? 'Importando...' : 'Importar'}
        </button>
      )}
      {puedeCrear && (
        <button
          type="button"
          onClick={() => setShowModal(true)}
          className="cc-btn cc-btn-primary"
        >
          <FaPlus /> Nuevo Centro
        </button>
      )}
    </>
  );

  const handleImportar = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    // Validar extensión localmente
    const extension = '.' + file.name.split('.').pop().toLowerCase();
    if (!IMPORT_ALLOWED_EXTENSIONS.includes(extension)) {
      toast.error(`Extensión no permitida: ${extension}. Use: ${IMPORT_ALLOWED_EXTENSIONS.join(', ')}`);
      e.target.value = '';
      return;
    }
    
    // Validar tamaño localmente
    const sizeMB = file.size / (1024 * 1024);
    if (sizeMB > IMPORT_MAX_FILE_SIZE_MB) {
      toast.error(`Archivo demasiado grande: ${sizeMB.toFixed(1)}MB. Máximo: ${IMPORT_MAX_FILE_SIZE_MB}MB`);
      e.target.value = '';
      return;
    }
    
    const formDataFile = new FormData();
    formDataFile.append('file', file);
    
    setImportLoading(true);
    try {
      const response = await centrosAPI.importar(formDataFile);
      
      const resumen = response.data.resumen || response.data;
      toast.success(
        `Importación completada: ${resumen.creados || 0} creados, ${resumen.actualizados || 0} actualizados`
      );
      
      if (response.data.errores && response.data.errores.length > 0) {
        // Mostrar errores detallados
        const errores = response.data.errores;
        console.warn('Errores en importación:', errores);
        
        // Mostrar hasta 5 errores en toasts
        errores.slice(0, 5).forEach((err, idx) => {
          const fila = err.fila || idx + 1;
          const msg = err.error || err.mensaje || JSON.stringify(err);
          toast.error(`Fila ${fila}: ${msg}`, { duration: 5000 });
        });
        
        if (errores.length > 5) {
          toast.error(`... y ${errores.length - 5} errores más. Revise la consola.`, { duration: 5000 });
        }
      }
      
      setShowImportModal(false);
      cargarCentros();
    } catch (error) {
      const errorMsg = error.response?.data?.error || 
                       error.response?.data?.detail ||
                       'Error al importar centros';
      toast.error(errorMsg);
    } finally {
      setImportLoading(false);
      e.target.value = '';
    }
  };

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        icon={FaBuilding}
        title="Gestión de Centros Penitenciarios"
        subtitle={`Total: ${totalCentros} centros registrados | Página ${currentPage} de ${totalPages}`}
        badge={filtrosActivos ? `${filtrosActivos} filtros activos` : null}
        actions={headerActions}
        filters={
          <>
            <button
              type="button"
              onClick={() => setShowFiltersMenu(!showFiltersMenu)}
              aria-expanded={showFiltersMenu}
              className="cc-filter-toggle"
            >
              <FaFilter className="text-[10px]" style={{ color: 'var(--color-primary)' }} />
              <span>Filtros</span>
              <FaChevronDown className={`text-[10px] transition-transform ${showFiltersMenu ? 'rotate-180' : ''}`} />
            </button>

            <select
              value={filtroEstado}
              onChange={(e) => setFiltroEstado(e.target.value)}
              className="cc-filter-select"
            >
              <option value="">Estado ▾</option>
              <option value="activo">Activo</option>
              <option value="inactivo">Inactivo</option>
            </select>
          </>
        }
      />

      {/* Panel de filtros expandido */}
      {showFiltersMenu && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-4">
            <div className="lg:col-span-2">
              <label className="cc-filter-label">Búsqueda</label>
              <div className="cc-filter-input-wrap">
                <FaSearch className="text-gray-400 text-xs" />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full bg-transparent text-sm focus:outline-none"
                  placeholder="Buscar por nombre, dirección, email o teléfono..."
                />
              </div>
            </div>
            <div>
              <label className="cc-filter-label">Estado</label>
              <select
                value={filtroEstado}
                onChange={(e) => setFiltroEstado(e.target.value)}
                className="cc-filter-select-full"
              >
                <option value="">Todos los estados</option>
                <option value="activo">Activo</option>
                <option value="inactivo">Inactivo</option>
              </select>
            </div>
            <div className="flex items-end">
              <button
                type="button"
                onClick={limpiarFiltros}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm font-medium text-gray-500 hover:bg-gray-50 transition"
              >
                Limpiar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Contenedor Tabla + Paginación */}
      <div className="rounded-2xl border border-gray-200 bg-white shadow-sm">
        {/* Tabla */}
        {/* Vista móvil: tarjetas */}
        <div className="lg:hidden space-y-3 p-4">
          {loading ? (
            <div className="flex justify-center py-8"><div className="animate-spin rounded-full h-8 w-8 border-4 border-t-transparent spinner-institucional"></div></div>
          ) : centros.length === 0 ? (
            <div className="py-8 text-center text-gray-500">No hay centros registrados</div>
          ) : (
            centros.map((centro, index) => (
              <div key={centro.id} className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
                <div className="flex items-start justify-between gap-2 mb-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs text-gray-500">#{(currentPage - 1) * PAGE_SIZE + index + 1}</span>
                      <span className="font-bold text-gray-800">{centro.nombre}</span>
                      <span className={`px-2 py-0.5 text-xs rounded-full ${centro.activo ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                        {centro.activo ? 'Activo' : 'Inactivo'}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 mt-1">{centro.direccion || 'Sin dirección'}</p>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3 py-3 border-y border-gray-100 text-sm">
                  <div><div className="text-xs text-gray-500">Teléfono</div><div className="font-medium">{centro.telefono || '-'}</div></div>
                  <div><div className="text-xs text-gray-500">Email</div><div className="font-medium truncate">{centro.email || '-'}</div></div>
                  <div><div className="text-xs text-gray-500">Requisiciones</div><div className="font-medium text-blue-600">{centro.total_requisiciones || 0}</div></div>
                  <div><div className="text-xs text-gray-500">Usuarios</div><div className="font-medium text-green-600">{centro.total_usuarios || 0}</div></div>
                </div>
                <div className="flex items-center justify-end gap-3 mt-3">
                  {puedeEditar && (
                    <button onClick={() => handleEdit(centro)} className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg"><FaEdit size={18} /></button>
                  )}
                  {puedeEditar && (
                    <button onClick={() => handleToggleActivo(centro)} className={`p-2 rounded-lg ${centro.activo ? 'text-green-600 hover:bg-green-50' : 'text-gray-500 hover:bg-gray-100'}`}>
                      {centro.activo ? <FaToggleOn size={20} /> : <FaToggleOff size={20} />}
                    </button>
                  )}
                  {puedeEliminar && (
                    <button onClick={() => handleDelete(centro)} className="p-2 text-red-600 hover:bg-red-50 rounded-lg"><FaTrash size={18} /></button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
          <div className="hidden lg:block w-full overflow-x-auto table-soft">
            <table className="w-full min-w-[700px] divide-y divide-gray-200">
            <thead className="thead-soft sticky top-0 z-10">
            <tr>
              {['#', 'Nombre', 'Dirección', 'Teléfono', 'Email', 'Requisiciones', 'Usuarios', 'Estado', 'Acciones'].map((col) => (
                <th key={col} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
            <tbody className="bg-white divide-y divide-gray-100">
              {loading ? (
                <tr>
                  <td colSpan="9" className="text-center py-8">
                    <div className="flex justify-center items-center">
                      <div className="animate-spin rounded-full h-8 w-8 border-4 border-t-transparent spinner-institucional"></div>
                      <span className="ml-2">Cargando centros...</span>
                    </div>
                  </td>
                </tr>
              ) : centros.length === 0 ? (
                <tr>
                  <td colSpan="9" className="text-center py-8 text-gray-500">
                    No hay centros registrados
                  </td>
                </tr>
              ) : (
                centros.map((centro, index) => (
                  <tr key={centro.id} className={`transition ${index % 2 === 0 ? 'bg-white' : 'bg-gray-50'} hover:bg-gray-100`}>
                    <td className="px-4 py-3 text-sm font-semibold text-gray-500">{(currentPage - 1) * PAGE_SIZE + index + 1}</td>
                    <td className="px-4 py-3 text-sm font-semibold text-gray-800">{centro.nombre}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{centro.direccion || '-'}</td>
                    <td className="px-4 py-3 text-sm">{centro.telefono || '-'}</td>
                    <td className="px-4 py-3 text-sm">{centro.email || '-'}</td>
                    <td className="px-4 py-3 text-sm text-center">
                      <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-xs font-semibold">
                        {centro.total_requisiciones || 0}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-center">
                      <span className="bg-green-100 text-green-800 px-2 py-1 rounded-full text-xs font-semibold">
                        {centro.total_usuarios || 0}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        centro.activo ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                      }`}>
                        {centro.activo ? 'Activo' : 'Inactivo'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <div className="flex items-center gap-3">
                        {puedeEditar ? (
                          <>
                            <button
                              onClick={() => handleEdit(centro)}
                              className="text-blue-600 hover:text-blue-800 disabled:opacity-50 disabled:cursor-not-allowed"
                              title="Editar"
                              disabled={actionLoading === centro.id}
                            >
                              <FaEdit />
                            </button>
                            <button
                              onClick={() => handleToggleActivo(centro)}
                              className={`disabled:opacity-50 disabled:cursor-not-allowed ${centro.activo ? 'text-green-600 hover:text-green-800' : 'text-gray-400 hover:text-gray-600'}`}
                              title={centro.activo ? 'Desactivar' : 'Activar'}
                              disabled={actionLoading === centro.id}
                            >
                              {actionLoading === centro.id ? (
                                <div className="animate-spin rounded-full h-4 w-4 border-2 border-current border-t-transparent inline-block" />
                              ) : centro.activo ? (
                                <FaToggleOn size={18} />
                              ) : (
                                <FaToggleOff size={18} />
                              )}
                            </button>
                            {puedeEliminar && (
                              <button
                                onClick={() => handleDelete(centro)}
                                className="text-red-600 hover:text-red-800 disabled:opacity-50 disabled:cursor-not-allowed"
                                title="Eliminar"
                                disabled={actionLoading === centro.id}
                              >
                                <FaTrash />
                              </button>
                            )}
                          </>
                        ) : (
                          <span className="text-gray-400 text-xs">Sin acciones</span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        
        {/* Paginación */}
        {totalPages > 1 && (
          <div className="px-6 py-4 border-t">
            <Pagination
              page={currentPage}
              totalPages={totalPages}
              onPageChange={setCurrentPage}
              totalItems={totalCentros}
              pageSize={PAGE_SIZE}
            />
          </div>
        )}
      </div>

      {/* Modal Crear/Editar */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-2xl rounded-2xl bg-white shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between rounded-t-2xl px-6 py-4 text-white bg-theme-gradient sticky top-0">
              <div>
                <h2 className="text-xl font-bold">{editingCentro ? 'Editar Centro' : 'Nuevo Centro'}</h2>
                <p className="text-sm text-white/80">Complete los campos obligatorios (*)</p>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm font-semibold">{editingCentro ? editingCentro.nombre?.slice(0, 15) : 'Nuevo'}</span>
                <button
                  onClick={() => { setShowModal(false); resetForm(); }}
                  className="text-white hover:text-gray-200 p-1 transition-colors"
                  title="Cerrar"
                >
                  <FaTimes className="text-xl" />
                </button>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4 px-6 py-6">
              <div>
                <label className="text-xs font-semibold text-theme-primary-hover">Nombre *</label>
                <input
                  type="text"
                  value={formData.nombre}
                  onChange={(e) => setFormData({...formData, nombre: e.target.value})}
                  className="mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:ring-2 border-theme-primary"
                  required
                  minLength={3}
                  maxLength={200}
                  placeholder="Nombre del centro penitenciario"
                />
                <p className="text-xs text-gray-400 mt-1">3-200 caracteres (debe ser único)</p>
              </div>

              <div>
                <label className="text-xs font-semibold text-theme-primary-hover">Dirección</label>
                <textarea
                  value={formData.direccion}
                  onChange={(e) => setFormData({...formData, direccion: e.target.value})}
                  className="mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:ring-2 border-theme-primary"
                  rows="2"
                  placeholder="Dirección completa del centro"
                />
              </div>

              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div>
                  <label className="text-xs font-semibold text-theme-primary-hover">Teléfono</label>
                  <input
                    type="text"
                    value={formData.telefono}
                    onChange={(e) => setFormData({...formData, telefono: e.target.value})}
                    className="mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:ring-2 border-theme-primary"
                    placeholder="(555) 123-4567"
                    maxLength={20}
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-theme-primary-hover">Email</label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({...formData, email: e.target.value})}
                    className="mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:ring-2 border-theme-primary"
                    placeholder="centro@ejemplo.gob.mx"
                    maxLength={254}
                  />
                </div>
              </div>

              <div className="flex items-center gap-2 rounded-lg border px-4 py-3 border-theme-primary">
                <input
                  type="checkbox"
                  checked={formData.activo}
                  onChange={(e) => setFormData({...formData, activo: e.target.checked})}
                  className="h-4 w-4"
                />
                <span className="text-sm font-semibold text-gray-700">Centro Activo</span>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => { setShowModal(false); resetForm(); }}
                  disabled={loading}
                  className="rounded-lg border px-4 py-2 text-sm font-semibold text-gray-600 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="rounded-lg px-5 py-2 text-sm font-semibold text-white disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 bg-theme-gradient"
                >
                  {loading ? <><FaSpinner className="animate-spin" /> Guardando...</> : 'Guardar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Importar */}
      {showImportModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl w-full max-w-md overflow-hidden shadow-2xl">
            <div className="px-6 py-4 bg-theme-gradient rounded-t-2xl flex items-center justify-between">
              <h2 className="text-xl font-bold text-white">Importar Centros desde Excel</h2>
              <button onClick={() => setShowImportModal(false)} className="text-white/70 hover:text-white">
                <FaTimes size={24} />
              </button>
            </div>
            
            <div className="p-6">
              <div className="mb-4">
                <p className="text-sm text-gray-600 mb-2">
                  El archivo debe contener las siguientes columnas:
                </p>
                <ul className="text-sm text-gray-600 list-disc list-inside">
                  <li><strong>Nombre</strong> (requerido, único)</li>
                  <li>Dirección (opcional)</li>
                  <li>Teléfono (opcional)</li>
                  <li>Email (opcional)</li>
                  <li>Estado (opcional: Activo/Inactivo)</li>
                </ul>
                <p className="text-sm text-theme-primary mt-2">
                  Descarga la plantilla para ver el formato correcto
                </p>
              </div>
              
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">
                  Seleccionar archivo Excel (.xlsx, .xls)
                </label>
                <input
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={handleImportar}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-theme-primary"
                  disabled={importLoading}
                />
              </div>
              
              {importLoading && (
                <div className="mb-4 text-center">
                  <FaSpinner className="animate-spin h-8 w-8 mx-auto text-theme-primary" />
                  <p className="text-sm text-gray-600 mt-2">Procesando archivo...</p>
                </div>
              )}
              
              <div className="flex justify-end gap-2">
                <button
                  onClick={() => setShowImportModal(false)}
                  className="px-4 py-2 border rounded-lg hover:bg-gray-100"
                  disabled={loading}
                >
                  Cerrar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal de confirmación en dos pasos */}
      <TwoStepConfirmModal
        isOpen={confirmState.isOpen}
        onClose={cancelConfirmation}
        onConfirm={() => executeWithConfirmation(confirmState.onConfirm)}
        title={confirmState.title}
        message={confirmState.message}
        itemInfo={confirmState.itemInfo}
        confirmText={confirmState.confirmText}
        cancelText={confirmState.cancelText}
        actionType={confirmState.actionType}
        isCritical={confirmState.isCritical}
        confirmPhrase={confirmState.confirmPhrase}
        isLoading={confirmState.isLoading}
      />
    </div>
  );
};

export default Centros;








