import { useState, useEffect, useCallback } from 'react';
import { centrosAPI } from '../services/api';
import { toast } from 'react-hot-toast';
import { hasAccessToken } from '../services/tokenManager';
import { 
  FaPlus, FaEdit, FaTrash, FaToggleOn, FaToggleOff, 
  FaSearch, FaFileExcel, FaFileUpload, FaDownload, FaFilter,
  FaBuilding
} from 'react-icons/fa';
import PageHeader from '../components/PageHeader';
import { COLORS, PRIMARY_GRADIENT, SECONDARY_GRADIENT } from '../constants/theme';

const MOCK_CENTROS = Array.from({ length: 15 }).map((_, index) => ({
  id: index + 1,
  clave: `CP-${String(index + 1).padStart(3, '0')}`,
  nombre: `Centro Penitenciario Simulado ${index + 1}`,
  tipo: index % 2 === 0 ? 'CERESO' : 'CEPRE',
  direccion: `Dirección ${index + 1}, Municipio Simulado`,
  telefono: `722000${String(100 + index)}`,
  responsable: `Director ${index + 1}`,
  activo: index % 4 !== 0,
  total_requisiciones: 5 + index,
  total_usuarios: 10 + index * 2,
}));

const Centros = () => {
  const [centros, setCentros] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [editingCentro, setEditingCentro] = useState(null);
  
  // Filtros
  const [searchTerm, setSearchTerm] = useState('');
  const [filtroEstado, setFiltroEstado] = useState('');
  
  const [formData, setFormData] = useState({
    clave: '',
    nombre: '',
    tipo: '',
    direccion: '',
    telefono: '',
    responsable: '',
    activo: true
  });

  // eslint-disable-next-line no-unused-vars
  const aplicarCentrosMock = useCallback(() => {
    let data = [...MOCK_CENTROS];
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      data = data.filter(
        (centro) =>
          centro.clave.toLowerCase().includes(term) ||
          centro.nombre.toLowerCase().includes(term) ||
          centro.direccion.toLowerCase().includes(term)
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

      const params = {};
      
      if (searchTerm) params.search = searchTerm;
      if (filtroEstado) params.activo = filtroEstado === 'activo';
      
      const response = await centrosAPI.getAll(params);
      setCentros(response.data.results || response.data);
    } catch (error) {
      toast.error('Error al cargar centros');
      console.error(error);
    } finally {
      setLoading(false);
    }
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
      clave: centro.clave,
      nombre: centro.nombre,
      tipo: centro.tipo,
      direccion: centro.direccion,
      telefono: centro.telefono,
      responsable: centro.responsable,
      activo: centro.activo
    });
    setShowModal(true);
  };

  const handleToggleActivo = async (centro) => {
    try {
      await centrosAPI.update(centro.id, { 
        ...centro, 
        activo: !centro.activo 
      });
      toast.success(`Centro ${!centro.activo ? 'activado' : 'desactivado'}`);
      cargarCentros();
    } catch (error) {
      toast.error('Error al cambiar estado');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('¿Está seguro de eliminar este centro?')) return;
    
    try {
      await centrosAPI.delete(id);
      toast.success('Centro eliminado correctamente');
      cargarCentros();
    } catch (error) {
      const errorMsg = error.response?.data?.error || 'Error al eliminar centro';
      toast.error(errorMsg);
    }
  };

  const resetForm = () => {
    setFormData({
      clave: '',
      nombre: '',
      tipo: '',
      direccion: '',
      telefono: '',
      responsable: '',
      activo: true
    });
    setEditingCentro(null);
  };

  const limpiarFiltros = () => {
    setSearchTerm('');
    setFiltroEstado('');
  };

  const handleDescargarPlantilla = async () => {
    try {
      setLoading(true);
      // -o. CORREGIDO: Usa centrosAPI en lugar de axios directo
      const response = await centrosAPI.plantilla();
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'plantilla_centros.xlsx');
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      toast.success('Plantilla descargada correctamente');
    } catch (error) {
      toast.error('Error al descargar plantilla');
    } finally {
      setLoading(false);
    }
  };

  const handleExportar = async () => {
    try {
      setLoading(true);
      const params = {};
      if (filtroEstado) params.activo = filtroEstado === 'activo';
      
      // -o. CORREGIDO: Usa centrosAPI en lugar de axios directo
      const response = await centrosAPI.exportar(params);
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `centros_${new Date().toISOString().split('T')[0]}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      toast.success('Centros exportados correctamente');
    } catch (error) {
      toast.error('Error al exportar centros');
    } finally {
      setLoading(false);
    }
  };

  const filtrosActivos = [searchTerm, filtroEstado].filter(Boolean).length;

  const headerActions = (
    <>
      <button
        type="button"
        onClick={handleDescargarPlantilla}
        className="flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold text-white transition"
        title="Descargar Plantilla"
        style={{
          backgroundColor: 'rgba(255,255,255,0.15)',
          border: '1px solid rgba(255,255,255,0.4)'
        }}
      >
        <FaDownload /> Plantilla
      </button>
      <button
        type="button"
        onClick={handleExportar}
        className="flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold text-white transition"
        style={{
          background: PRIMARY_GRADIENT,
          border: '1px solid rgba(255,255,255,0.4)'
        }}
      >
        <FaFileExcel /> Exportar
      </button>
      <button
        type="button"
        onClick={() => setShowImportModal(true)}
        className="flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold text-white transition"
        style={{
          background: SECONDARY_GRADIENT,
          border: '1px solid rgba(255,255,255,0.4)'
        }}
      >
        <FaFileUpload /> Importar
      </button>
      <button
        type="button"
        onClick={() => setShowModal(true)}
        className="flex items-center gap-2 rounded-full bg-white/90 px-4 py-2 text-sm font-bold hover:bg-white"
        style={{ color: COLORS.vino }}
      >
        <FaPlus /> Nuevo Centro
      </button>
    </>
  );

  const handleImportar = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    const formDataFile = new FormData();
    formDataFile.append('file', file);
    
    try {
      setLoading(true);
      const response = await centrosAPI.importar(formDataFile);
      
      const resumen = response.data.resumen || response.data;
      toast.success(
        `Importación completada: ${resumen.creados || 0} creados, ${resumen.actualizados || 0} actualizados`
      );
      
      if (response.data.errores && response.data.errores.length > 0) {
        console.warn('Errores en importación:', response.data.errores);
        toast.error(`${response.data.errores.length} errores. Revise la consola.`);
      }
      
      setShowImportModal(false);
      cargarCentros();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al importar centros');
    } finally {
      setLoading(false);
      e.target.value = '';
    }
  };

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        icon={FaBuilding}
        title="Gestión de Centros Penitenciarios"
        subtitle={`Total: ${centros.length} centros registrados`}
        badge={filtrosActivos ? `${filtrosActivos} filtros activos` : null}
        actions={headerActions}
      />

      {/* Filtros */}
      <div className="bg-white p-4 rounded-lg shadow mb-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="md:col-span-2 relative">
            <FaSearch className="absolute left-3 top-3 text-gray-400" />
            <input
              type="text"
              placeholder="Buscar por clave, nombre, dirección..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
          
          <select
            value={filtroEstado}
            onChange={(e) => setFiltroEstado(e.target.value)}
            className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Todos los estados</option>
            <option value="activo">Activo</option>
            <option value="inactivo">Inactivo</option>
          </select>
          
          <button
            onClick={limpiarFiltros}
            className="bg-gray-200 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-300 flex items-center justify-center gap-2"
          >
            <FaFilter /> Limpiar Filtros
          </button>
        </div>
      </div>

      {/* Tabla */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">#</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Clave</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Nombre</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tipo</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Responsable</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Requisiciones</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Usuarios</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Estado</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Acciones</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {loading ? (
                <tr>
                  <td colSpan="9" className="text-center py-8">
                    <div className="flex justify-center items-center">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
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
                  <tr key={centro.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm">{index + 1}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-blue-600">
                      {centro.clave}
                    </td>
                    <td className="px-6 py-4 text-sm">{centro.nombre}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">{centro.tipo || '-'}</td>
                    <td className="px-6 py-4 text-sm">{centro.responsable || '-'}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                      <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-xs">
                        {centro.total_requisiciones || 0}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                      <span className="bg-green-100 text-green-800 px-2 py-1 rounded-full text-xs">
                        {centro.total_usuarios || 0}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        centro.activo ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                      }`}>
                        {centro.activo ? 'Activo' : 'Inactivo'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm space-x-2">
                      <button
                        onClick={() => handleEdit(centro)}
                        className="text-blue-600 hover:text-blue-800"
                        title="Editar"
                      >
                        <FaEdit className="inline" />
                      </button>
                      <button
                        onClick={() => handleToggleActivo(centro)}
                        className={centro.activo ? 'text-green-600 hover:text-green-800' : 'text-gray-400 hover:text-gray-600'}
                        title={centro.activo ? 'Desactivar' : 'Activar'}
                      >
                        {centro.activo ? <FaToggleOn className="inline" /> : <FaToggleOff className="inline" />}
                      </button>
                      <button
                        onClick={() => handleDelete(centro.id)}
                        className="text-red-600 hover:text-red-800"
                        title="Eliminar"
                      >
                        <FaTrash className="inline" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal Crear/Editar */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <h2 className="text-xl font-bold mb-4">
              {editingCentro ? 'Editar Centro' : 'Nuevo Centro'}
            </h2>
            
            <form onSubmit={handleSubmit}>
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Clave *</label>
                  <input
                    type="text"
                    value={formData.clave}
                    onChange={(e) => setFormData({...formData, clave: e.target.value.toUpperCase()})}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    required
                    disabled={editingCentro}
                    minLength={2}
                    maxLength={50}
                  />
                  <p className="text-xs text-gray-500 mt-1">2-50 caracteres (se convierte a mayúsculas)</p>
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-1">Tipo</label>
                  <input
                    type="text"
                    value={formData.tipo}
                    onChange={(e) => setFormData({...formData, tipo: e.target.value})}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="CERESO, CEFERESO, etc."
                  />
                </div>
              </div>
              
              <div className="mb-4">
                <label className="block text-sm font-medium mb-1">Nombre *</label>
                <input
                  type="text"
                  value={formData.nombre}
                  onChange={(e) => setFormData({...formData, nombre: e.target.value})}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  required
                  minLength={5}
                  maxLength={200}
                />
                <p className="text-xs text-gray-500 mt-1">5-200 caracteres</p>
              </div>
              
              <div className="mb-4">
                <label className="block text-sm font-medium mb-1">Dirección</label>
                <textarea
                  value={formData.direccion}
                  onChange={(e) => setFormData({...formData, direccion: e.target.value})}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  rows="2"
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Teléfono</label>
                  <input
                    type="text"
                    value={formData.telefono}
                    onChange={(e) => setFormData({...formData, telefono: e.target.value})}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="5551234567"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-1">Responsable</label>
                  <input
                    type="text"
                    value={formData.responsable}
                    onChange={(e) => setFormData({...formData, responsable: e.target.value})}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
              
              <div className="mb-4">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={formData.activo}
                    onChange={(e) => setFormData({...formData, activo: e.target.checked})}
                    className="mr-2 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <span className="text-sm font-medium">Centro Activo</span>
                </label>
              </div>
              
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => { setShowModal(false); resetForm(); }}
                  className="px-4 py-2 border rounded-lg hover:bg-gray-100"
                  disabled={loading}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {loading ? 'Guardando...' : 'Guardar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Importar */}
      {showImportModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">Importar Centros desde Excel</h2>
            
            <div className="mb-4">
              <p className="text-sm text-gray-600 mb-2">
                El archivo debe contener las siguientes columnas:
              </p>
              <ul className="text-sm text-gray-600 list-disc list-inside">
                <li>Clave (requerido, único)</li>
                <li>Nombre (requerido, mín 5 caracteres)</li>
                <li>Tipo (opcional)</li>
                <li>Dirección (opcional)</li>
                <li>Teléfono (opcional)</li>
                <li>Responsable (opcional)</li>
              </ul>
              <p className="text-sm text-blue-600 mt-2">
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
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                disabled={loading}
              />
            </div>
            
            {loading && (
              <div className="mb-4 text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
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
      )}
    </div>
  );
};

export default Centros;








