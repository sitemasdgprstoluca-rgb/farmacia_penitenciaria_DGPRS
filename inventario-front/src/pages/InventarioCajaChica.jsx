/**
 * Módulo: Inventario de Caja Chica del Centro
 * 
 * PROPÓSITO:
 * Mostrar y gestionar el inventario de productos comprados con caja chica.
 * Este inventario es SEPARADO del inventario principal de farmacia.
 * 
 * PERMISOS:
 * - Centro: CRUD completo, puede registrar salidas y ajustes
 * - Farmacia: Solo lectura (auditoría) para prevenir malas prácticas
 */

import { useState, useEffect, useCallback } from 'react';
import { 
  inventarioCajaChicaAPI, 
  movimientosCajaChicaAPI,
  centrosAPI,
  pacientesAPI
} from '../services/api';
import { toast } from 'react-hot-toast';
import {
  FaSearch,
  FaFilter,
  FaTimes,
  FaEye,
  FaHistory,
  FaBoxOpen,
  FaExclamationTriangle,
  FaInfoCircle,
  FaWarehouse,
  FaMinusCircle,
  FaExchangeAlt,
  FaCalendarAlt,
  FaFileExcel,
  FaDownload,
  FaChevronDown,
} from 'react-icons/fa';
import PageHeader from '../components/PageHeader';
import Pagination from '../components/Pagination';
import { usePermissions } from '../hooks/usePermissions';
import { esFarmaciaAdmin, esCentro } from '../utils/roles';
import useEscapeToClose from '../hooks/useEscapeToClose';

const PAGE_SIZE = 20;

const InventarioCajaChica = () => {
  const { user } = usePermissions();
  
  // Detectar tipo de usuario
  const esUsuarioFarmacia = esFarmaciaAdmin(user);
  const esUsuarioCentro = esCentro(user);
  const esSoloAuditoria = esUsuarioFarmacia;
  
  // Centro del usuario
  const centroUsuario = user?.centro?.id || user?.centro_id;
  
  // Permisos
  const puedeRegistrarSalida = esUsuarioCentro && !esSoloAuditoria;
  const puedeAjustar = esUsuarioCentro && !esSoloAuditoria;

  // Estados principales
  const [inventario, setInventario] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [resumen, setResumen] = useState(null);
  
  // Filtros
  const [searchTerm, setSearchTerm] = useState('');
  const [centroFiltro, setCentroFiltro] = useState(centroUsuario || '');
  const [conStock, setConStock] = useState(true);
  // Mostrar filtros expandidos por defecto para Farmacia
  const [showFilters, setShowFilters] = useState(false);
  
  // Listas auxiliares
  const [centros, setCentros] = useState([]);
  const [pacientes, setPacientes] = useState([]);
  const [pacientesLoading, setPacientesLoading] = useState(false);
  const [searchPaciente, setSearchPaciente] = useState('');
  
  // Modales
  const [detailModal, setDetailModal] = useState({ show: false, item: null });
  const [salidaModal, setSalidaModal] = useState({ show: false, item: null, cantidad: '', motivo: '', referencia: '', pacienteId: null });
  const [ajusteModal, setAjusteModal] = useState({ show: false, item: null, cantidad: '', motivo: '' });
  const [movimientosModal, setMovimientosModal] = useState({ show: false, item: null, movimientos: [] });

  // ESC para cerrar modales
  useEscapeToClose({
    isOpen: detailModal.show,
    onClose: () => setDetailModal({ show: false, item: null }),
    modalId: 'inventario-caja-chica-detail-modal',
    disabled: false
  });

  useEscapeToClose({
    isOpen: salidaModal.show,
    onClose: () => {
      setSalidaModal({ show: false, item: null, cantidad: '', motivo: '', referencia: '', pacienteId: null });
      setSearchPaciente('');
      setPacientes([]);
    },
    modalId: 'inventario-caja-chica-salida-modal',
    disabled: false
  });

  useEscapeToClose({
    isOpen: ajusteModal.show,
    onClose: () => setAjusteModal({ show: false, item: null, cantidad: '', motivo: '' }),
    modalId: 'inventario-caja-chica-ajuste-modal',
    disabled: false
  });

  useEscapeToClose({
    isOpen: movimientosModal.show,
    onClose: () => setMovimientosModal({ show: false, item: null, movimientos: [] }),
    modalId: 'inventario-caja-chica-movimientos-modal',
    disabled: false
  });

  // Expandir filtros automáticamente para farmacia
  useEffect(() => {
    if (esUsuarioFarmacia) {
      setShowFilters(true);
    }
  }, [esUsuarioFarmacia]);

  // Cargar centros
  useEffect(() => {
    const fetchCentros = async () => {
      try {
        console.log('Cargando centros para usuario farmacia...');
        const response = await centrosAPI.getAll({ activo: true, page_size: 100 });
        const data = response.data?.results || response.data || [];
        console.log('Centros cargados:', data.length);
        setCentros(data);
      } catch (error) {
        console.error('Error al cargar centros:', error);
      }
    };
    if (esUsuarioFarmacia) {
      fetchCentros();
    }
  }, [esUsuarioFarmacia]);

  // Cargar inventario
  const fetchInventario = useCallback(async () => {
    setLoading(true);
    try {
      const params = {
        page: currentPage,
        page_size: PAGE_SIZE,
        search: searchTerm || undefined,
        centro: centroFiltro || undefined,
        con_stock: conStock || undefined,
      };
      
      const response = await inventarioCajaChicaAPI.getAll(params);
      const data = response.data;
      
      setInventario(data?.results || data || []);
      setTotalItems(data?.count || data?.length || 0);
    } catch (error) {
      console.error('Error al cargar inventario:', error);
      toast.error('Error al cargar inventario de caja chica');
      setInventario([]);
    } finally {
      setLoading(false);
    }
  }, [currentPage, searchTerm, centroFiltro, conStock]);

  useEffect(() => {
    fetchInventario();
  }, [fetchInventario]);

  // Cargar resumen
  const fetchResumen = useCallback(async () => {
    try {
      const params = centroFiltro ? { centro: centroFiltro } : {};
      const response = await inventarioCajaChicaAPI.resumen(params);
      setResumen(response.data);
    } catch (error) {
      console.error('Error al cargar resumen:', error);
    }
  }, [centroFiltro]);

  useEffect(() => {
    fetchResumen();
  }, [fetchResumen]);

  // Cargar pacientes con búsqueda
  const fetchPacientes = useCallback(async (query = '') => {
    if (!centroFiltro && !centroUsuario) return;
    
    setPacientesLoading(true);
    try {
      const centro = centroFiltro || centroUsuario;
      const response = await pacientesAPI.getAll({
        centro,
        activo: true,
        search: query,
        page_size: 50
      });
      const data = response.data?.results || response.data || [];
      setPacientes(data);
    } catch (error) {
      console.error('Error al cargar pacientes:', error);
    } finally {
      setPacientesLoading(false);
    }
  }, [centroFiltro, centroUsuario]);

  // Cargar pacientes al abrir modal salida
  useEffect(() => {
    if (salidaModal.show) {
      fetchPacientes();
    }
  }, [salidaModal.show, fetchPacientes]);

  // Buscar pacientes al escribir
  useEffect(() => {
    if (salidaModal.show && searchPaciente) {
      const timer = setTimeout(() => {
        fetchPacientes(searchPaciente);
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [searchPaciente, salidaModal.show, fetchPacientes]);

  // Registrar salida
  const handleRegistrarSalida = async () => {
    // Validaciones
    const cantidad = parseInt(salidaModal.cantidad);
    
    if (!salidaModal.item || !cantidad || !salidaModal.motivo || !salidaModal.referencia) {
      toast.error('Debe completar todos los campos requeridos (cantidad, paciente PPL y motivo)');
      return;
    }

    if (cantidad > salidaModal.item.cantidad_actual) {
      toast.error(`Stock insuficiente. Disponible: ${salidaModal.item.cantidad_actual} unidades`);
      return;
    }
    
    try {
      await inventarioCajaChicaAPI.registrarSalida(salidaModal.item.id, {
        cantidad: cantidad,
        motivo: salidaModal.motivo,
        referencia: salidaModal.referencia,
      });
      toast.success('Salida registrada correctamente');
      setSalidaModal({ show: false, item: null, cantidad: '', motivo: '', referencia: '', pacienteId: null });
      setSearchPaciente('');
      setPacientes([]);
      fetchInventario();
      fetchResumen();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al registrar salida');
    }
  };

  // Ajustar inventario
  const handleAjustar = async () => {
    if (!ajusteModal.item || ajusteModal.cantidad === '' || !ajusteModal.motivo) {
      toast.error('Debe completar todos los campos requeridos');
      return;
    }
    
    try {
      await inventarioCajaChicaAPI.ajustar(ajusteModal.item.id, {
        cantidad: parseInt(ajusteModal.cantidad),
        motivo: ajusteModal.motivo,
      });
      toast.success('Ajuste realizado correctamente');
      setAjusteModal({ show: false, item: null, cantidad: '', motivo: '' });
      fetchInventario();
      fetchResumen();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al ajustar inventario');
    }
  };

  // Ver movimientos
  const handleVerMovimientos = async (item) => {
    try {
      const response = await movimientosCajaChicaAPI.porInventario(item.id);
      setMovimientosModal({ 
        show: true, 
        item, 
        movimientos: response.data?.results || response.data || [] 
      });
    } catch (error) {
      toast.error('Error al cargar movimientos');
    }
  };

  // Limpiar filtros
  const handleClearFilters = () => {
    setSearchTerm('');
    setCentroFiltro(centroUsuario || '');
    setConStock(true);
    setCurrentPage(1);
  };

  // Exportar a Excel
  const handleExportar = async () => {
    try {
      toast.loading('Generando archivo Excel...', { id: 'exportar' });
      
      const params = {
        centro: centroFiltro || undefined,
        con_stock: conStock || undefined,
        search: searchTerm || undefined,
      };
      
      const response = await inventarioCajaChicaAPI.exportar(params);
      
      // Crear blob y descargar
      const blob = new Blob([response.data], { 
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      
      // Extraer nombre del archivo del header o usar default
      const contentDisposition = response.headers['content-disposition'];
      let filename = 'inventario_caja_chica.xlsx';
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="(.+)"/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }
      
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success('Archivo descargado correctamente', { id: 'exportar' });
    } catch (error) {
      console.error('Error al exportar:', error);
      toast.error('Error al exportar inventario', { id: 'exportar' });
    }
  };

  // Formatear moneda
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('es-MX', {
      style: 'currency',
      currency: 'MXN'
    }).format(amount || 0);
  };

  // Formatear fecha
  const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('es-MX', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
  };

  // Verificar caducidad
  const getCaducidadStatus = (fechaCaducidad) => {
    if (!fechaCaducidad) return null;
    
    const hoy = new Date();
    const caducidad = new Date(fechaCaducidad);
    const diffDays = Math.floor((caducidad - hoy) / (1000 * 60 * 60 * 24));
    
    if (diffDays < 0) {
      return { type: 'expired', label: 'Caducado', color: 'bg-red-100 text-red-800' };
    } else if (diffDays <= 30) {
      return { type: 'critical', label: `${diffDays}d`, color: 'bg-red-100 text-red-800' };
    } else if (diffDays <= 90) {
      return { type: 'warning', label: `${diffDays}d`, color: 'bg-yellow-100 text-yellow-800' };
    }
    return null;
  };

  return (
    <div className="p-6 space-y-6">
      <PageHeader 
        title="Inventario Caja Chica" 
        subtitle={esSoloAuditoria 
          ? "Auditoría del inventario del centro (solo lectura)"
          : "Inventario de productos comprados con recursos propios"
        }
        icon={FaWarehouse}
        filters={
          <>
            <button
              type="button"
              onClick={() => setShowFilters(!showFilters)}
              aria-expanded={showFilters}
              className="cc-filter-toggle"
            >
              <FaFilter className="text-[10px]" style={{ color: 'var(--color-primary)' }} />
              <span>Filtros</span>
              <FaChevronDown className={`text-[10px] transition-transform ${showFilters ? 'rotate-180' : ''}`} />
            </button>
          </>
        }
      />

      {/* Banner informativo para auditoría */}
      {esSoloAuditoria && (
        <div className="p-4 bg-blue-50 border border-blue-200 rounded-2xl flex items-start gap-3">
          <FaInfoCircle className="text-blue-600 text-xl flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-blue-800">Modo Auditoría</h3>
            <p className="text-blue-700 text-sm">
              Este inventario es SEPARADO del inventario principal de farmacia.
              Como usuario de farmacia, puede ver todo el inventario de caja chica
              de los centros para auditoría.
            </p>
          </div>
        </div>
      )}

      {/* Resumen */}
      {resumen && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          <div className="bg-white p-4 rounded-2xl shadow-sm border-l-4 border-purple-400 hover:shadow-md transition-shadow">
            <div className="text-2xl font-bold text-purple-600">{resumen.total_items || 0}</div>
            <div className="text-sm text-gray-500">Total Items</div>
          </div>
          <div className="bg-white p-4 rounded-2xl shadow-sm border-l-4 border-green-400 hover:shadow-md transition-shadow">
            <div className="text-2xl font-bold text-green-600">{resumen.items_con_stock || 0}</div>
            <div className="text-sm text-gray-500">Con Stock</div>
          </div>
          <div className="bg-white p-4 rounded-2xl shadow-sm border-l-4 border-gray-400 hover:shadow-md transition-shadow">
            <div className="text-2xl font-bold text-gray-600">{resumen.items_agotados || 0}</div>
            <div className="text-sm text-gray-500">Agotados</div>
          </div>
          <div className="bg-white p-4 rounded-2xl shadow-sm border-l-4 border-yellow-400 hover:shadow-md transition-shadow">
            <div className="text-2xl font-bold text-yellow-600">{resumen.items_por_caducar || 0}</div>
            <div className="text-sm text-gray-500">Por Caducar</div>
          </div>
          <div className="bg-white p-4 rounded-2xl shadow-sm border-l-4 border-blue-400 hover:shadow-md transition-shadow">
            <div className="text-2xl font-bold text-blue-600">{formatCurrency(resumen.valor_total)}</div>
            <div className="text-sm text-gray-500">Valor Total</div>
          </div>
        </div>
      )}

      {/* Barra de acciones */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-4">
        <div className="flex flex-col sm:flex-row gap-4 justify-between items-start sm:items-center">
          {/* Búsqueda */}
          <div className="relative flex-1 w-full sm:max-w-md">
            <FaSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Buscar por producto, lote..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
            />
          </div>
          
          {/* Botones */}
          <div className="flex gap-2 flex-wrap">
            <button
              onClick={handleExportar}
              className="px-4 py-2 rounded-lg flex items-center gap-2 bg-green-600 text-white hover:bg-green-700 transition-colors"
              title="Descargar inventario en Excel"
            >
              <FaFileExcel />
              Exportar
            </button>
          </div>
        </div>
      </div>

      {/* Panel de filtros expandido */}
      {showFilters && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {/* Centro (solo para farmacia) */}
            {esUsuarioFarmacia && (
              <div>
                <label className="cc-filter-label">Centro</label>
                <select
                  value={centroFiltro}
                  onChange={(e) => setCentroFiltro(e.target.value)}
                  className="cc-filter-select-full"
                >
                  <option value="">Todos los centros</option>
                  {centros.map(centro => (
                    <option key={centro.id} value={centro.id}>{centro.nombre}</option>
                  ))}
                </select>
              </div>
            )}
            
            {/* Solo con stock */}
            <div className="flex items-center">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={conStock}
                  onChange={(e) => setConStock(e.target.checked)}
                  className="w-4 h-4 text-purple-600 border-gray-300 rounded focus:ring-purple-500"
                />
                <span className="text-sm text-gray-700">Solo con stock disponible</span>
              </label>
            </div>

            <div className="flex items-end">
              <button
                onClick={handleClearFilters}
                className="cc-btn cc-btn-ghost text-xs"
              >
                Limpiar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Tabla de inventario */}
      <div className="rounded-2xl border border-gray-200 bg-white shadow-sm">
        {/* Vista móvil: tarjetas */}
        <div className="lg:hidden">
          {loading ? (
            <div className="flex items-center justify-center gap-2 py-8">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-purple-600"></div>
              <span className="text-gray-500">Cargando...</span>
            </div>
          ) : inventario.length === 0 ? (
            <div className="px-4 py-8 text-center text-gray-500">
              No se encontró inventario de caja chica
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {inventario.map((item) => {
                const caducidadStatus = getCaducidadStatus(item.fecha_caducidad);
                const sinStock = item.cantidad_actual <= 0;
                return (
                  <div key={item.id} className={`p-4 ${sinStock ? 'bg-gray-50 opacity-60' : ''}`}>
                    {/* Header: Producto */}
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-gray-900 truncate">{item.descripcion_producto}</div>
                        {item.producto?.clave && (
                          <div className="text-xs text-gray-500">{item.producto.clave}</div>
                        )}
                      </div>
                      <span className={`font-bold text-lg ${
                        sinStock ? 'text-red-600' : 
                        item.cantidad_actual < item.cantidad_inicial * 0.2 ? 'text-yellow-600' : 
                        'text-green-600'
                      }`}>
                        {item.cantidad_actual}
                      </span>
                    </div>
                    
                    {/* Info grid */}
                    <div className="grid grid-cols-2 gap-2 text-sm mb-3">
                      {esUsuarioFarmacia && (
                        <div>
                          <span className="text-gray-500">Centro:</span>
                          <span className="ml-1 text-gray-700">{item.centro?.nombre || '-'}</span>
                        </div>
                      )}
                      <div>
                        <span className="text-gray-500">Lote:</span>
                        <span className="ml-1 font-mono text-gray-600">{item.numero_lote || '-'}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <span className="text-gray-500">Cad:</span>
                        <span className="text-gray-600">{formatDate(item.fecha_caducidad)}</span>
                        {caducidadStatus && (
                          <span className={`px-1.5 py-0.5 rounded text-xs ${caducidadStatus.color}`}>
                            {caducidadStatus.label}
                          </span>
                        )}
                      </div>
                      <div>
                        <span className="text-gray-500">Precio:</span>
                        <span className="ml-1 text-gray-600">{formatCurrency(item.precio_unitario)}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Stock inicial:</span>
                        <span className="ml-1 text-gray-600">{item.cantidad_inicial}</span>
                      </div>
                    </div>
                    
                    {/* Acciones */}
                    <div className="flex items-center gap-2 pt-2 border-t border-gray-100">
                      <button
                        onClick={() => handleVerMovimientos(item)}
                        className="flex-1 px-3 py-2 text-sm text-blue-600 bg-blue-50 rounded-lg flex items-center justify-center gap-1"
                      >
                        <FaHistory /> Movimientos
                      </button>
                      {puedeRegistrarSalida && !sinStock && (
                        <button
                          onClick={() => setSalidaModal({ show: true, item, cantidad: '', motivo: '', referencia: '', pacienteId: null })}
                          className="flex-1 px-3 py-2 text-sm text-orange-600 bg-orange-50 rounded-lg flex items-center justify-center gap-1"
                        >
                          <FaMinusCircle /> Salida
                        </button>
                      )}
                      {puedeAjustar && (
                        <button
                          onClick={() => setAjusteModal({ show: true, item, cantidad: item.cantidad_actual.toString(), motivo: '' })}
                          className="px-3 py-2 text-sm text-purple-600 bg-purple-50 rounded-lg"
                        >
                          <FaExchangeAlt />
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
        
        {/* Vista desktop: tabla */}
        <div className="hidden lg:block w-full overflow-x-auto">
          <table className="w-full min-w-[650px] divide-y divide-gray-200">
            <thead className="bg-theme-gradient sticky top-0 z-10">
              <tr>
                {esUsuarioFarmacia && (
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">
                    Centro
                  </th>
                )}
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">
                  Producto
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">
                  Lote
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">
                  Caducidad
                </th>
                <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">
                  Stock Inicial
                </th>
                <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">
                  Stock Actual
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">
                  Precio Unit.
                </th>
                <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-100">
              {loading ? (
                <tr>
                  <td colSpan={esUsuarioFarmacia ? 8 : 7} className="px-4 py-8 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-purple-600"></div>
                      <span className="text-gray-500">Cargando...</span>
                    </div>
                  </td>
                </tr>
              ) : inventario.length === 0 ? (
                <tr>
                  <td colSpan={esUsuarioFarmacia ? 8 : 7} className="px-4 py-8 text-center text-gray-500">
                    No se encontró inventario de caja chica
                  </td>
                </tr>
              ) : (
                inventario.map((item) => {
                  const caducidadStatus = getCaducidadStatus(item.fecha_caducidad);
                  const sinStock = item.cantidad_actual <= 0;
                  
                  return (
                    <tr key={item.id} className={`hover:bg-gray-50 ${sinStock ? 'bg-gray-50 opacity-60' : ''}`}>
                      {esUsuarioFarmacia && (
                        <td className="px-4 py-3 whitespace-nowrap">
                          <span className="text-sm text-gray-700">
                            {item.centro?.nombre || '-'}
                          </span>
                        </td>
                      )}
                      <td className="px-4 py-3">
                        <div className="text-sm font-medium text-gray-900">{item.descripcion_producto}</div>
                        {item.producto?.clave && (
                          <div className="text-xs text-gray-500">{item.producto.clave}</div>
                        )}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="font-mono text-sm text-gray-600">{item.numero_lote || '-'}</span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <span className="text-sm text-gray-600">{formatDate(item.fecha_caducidad)}</span>
                          {caducidadStatus && (
                            <span className={`px-1.5 py-0.5 rounded text-xs ${caducidadStatus.color}`}>
                              {caducidadStatus.label}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-center text-sm text-gray-600">
                        {item.cantidad_inicial}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-center">
                        <span className={`font-medium ${
                          sinStock ? 'text-red-600' : 
                          item.cantidad_actual < item.cantidad_inicial * 0.2 ? 'text-yellow-600' : 
                          'text-green-600'
                        }`}>
                          {item.cantidad_actual}
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                        {formatCurrency(item.precio_unitario)}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-center">
                        <div className="flex items-center justify-center gap-1">
                          {/* Ver movimientos */}
                          <button
                            onClick={() => handleVerMovimientos(item)}
                            className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg"
                            title="Ver movimientos"
                          >
                            <FaHistory />
                          </button>
                          
                          {/* Registrar salida */}
                          {puedeRegistrarSalida && !sinStock && (
                            <button
                              onClick={() => setSalidaModal({ show: true, item, cantidad: '', motivo: '', referencia: '', pacienteId: null })}
                              className="p-2 text-orange-600 hover:bg-orange-50 rounded-lg"
                              title="Registrar salida"
                            >
                              <FaMinusCircle />
                            </button>
                          )}
                          
                          {/* Ajustar */}
                          {puedeAjustar && (
                            <button
                              onClick={() => setAjusteModal({ show: true, item, cantidad: item.cantidad_actual.toString(), motivo: '' })}
                              className="p-2 text-purple-600 hover:bg-purple-50 rounded-lg"
                              title="Ajustar inventario"
                            >
                              <FaExchangeAlt />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
        
        {/* Paginación */}
        {totalItems > PAGE_SIZE && (
          <div className="px-4 py-3 border-t">
            <Pagination
              currentPage={currentPage}
              totalItems={totalItems}
              pageSize={PAGE_SIZE}
              onPageChange={setCurrentPage}
            />
          </div>
        )}
      </div>

      {/* Modal de salida */}
      {salidaModal.show && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-lg">
            <div className="px-6 py-4 border-b bg-orange-50">
              <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
                <FaMinusCircle className="text-orange-600" />
                Registrar Salida / Dispensación
              </h2>
              <p className="text-xs text-gray-600 mt-1">
                📋 Registro de entrega de medicamento a paciente PPL
              </p>
            </div>
            <div className="p-6 space-y-4">
              {/* Info del producto */}
              <div className="bg-gradient-to-r from-blue-50 to-blue-100 p-4 rounded-lg border-l-4 border-blue-500">
                <div className="text-sm text-gray-600 font-medium">Producto a Dispensar</div>
                <div className="font-bold text-gray-900 text-lg mt-1">{salidaModal.item?.descripcion_producto}</div>
                <div className="flex items-center gap-4 mt-3">
                  <div>
                    <div className="text-xs text-gray-500">Stock Disponible</div>
                    <div className="font-bold text-green-600 text-xl">{salidaModal.item?.cantidad_actual} <span className="text-sm">unidades</span></div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500">Lote</div>
                    <div className="font-medium text-gray-700">{salidaModal.item?.numero_lote || 'N/A'}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500">Caducidad</div>
                    <div className="font-medium text-gray-700">{salidaModal.item?.fecha_caducidad || 'N/A'}</div>
                  </div>
                </div>
              </div>

              {/* Quien dispensa */}
              <div className="bg-purple-50 p-3 rounded-lg border border-purple-200">
                <div className="flex items-center gap-2">
                  <span className="text-purple-600 font-medium text-sm">👤 Dispensado por:</span>
                  <span className="text-gray-900 font-semibold">{user?.nombre_completo || user?.username || 'Usuario actual'}</span>
                  <span className="text-xs text-gray-500">({user?.rol || 'N/A'})</span>
                </div>
              </div>
              
              {/* Cantidad */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  <span className="text-red-600">*</span> Cantidad a Dispensar
                </label>
                <input
                  type="number"
                  value={salidaModal.cantidad}
                  onChange={(e) => setSalidaModal(prev => ({ ...prev, cantidad: e.target.value }))}
                  min="1"
                  max={salidaModal.item?.cantidad_actual}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                  placeholder="Número de unidades"
                />
                {/* Validación visual de stock */}
                {salidaModal.cantidad && parseInt(salidaModal.cantidad) > 0 && (
                  <div className={`text-sm mt-2 p-2 rounded flex items-center gap-2 ${
                    parseInt(salidaModal.cantidad) > salidaModal.item?.cantidad_actual 
                      ? 'bg-red-50 text-red-700 border border-red-200' 
                      : 'bg-green-50 text-green-700'
                  }`}>
                    {parseInt(salidaModal.cantidad) > salidaModal.item?.cantidad_actual ? (
                      <>
                        <FaExclamationTriangle />
                        <span><strong>❌ Stock insuficiente.</strong> Solo hay {salidaModal.item?.cantidad_actual} unidades disponibles</span>
                      </>
                    ) : (
                      <span>✅ Cantidad válida. Quedarán {salidaModal.item?.cantidad_actual - parseInt(salidaModal.cantidad)} unidades</span>
                    )}
                  </div>
                )}
              </div>

              {/* Paciente PPL - AUTOCOMPLETADO */}
              <div className="bg-yellow-50 border-2 border-yellow-300 rounded-lg p-4">
                <label className="block text-sm font-bold text-gray-900 mb-1">
                  <span className="text-red-600">*</span> Paciente PPL (Seleccionar de lista)
                </label>
                
                {/* Input de búsqueda */}
                <div className="relative">
                  <input
                    type="text"
                    value={searchPaciente}
                    onChange={(e) => {
                      setSearchPaciente(e.target.value);
                      setSalidaModal(prev => ({ ...prev, referencia: '', pacienteId: null }));
                    }}
                    placeholder="Buscar por nombre, apellido o expediente..."
                    className="w-full px-3 py-2 pr-10 border-2 border-yellow-400 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 bg-white"
                  />
                  {pacientesLoading && (
                    <div className="absolute right-3 top-3">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-orange-600"></div>
                    </div>
                  )}
                </div>

                {/* Lista de resultados */}
                {searchPaciente && pacientes.length > 0 && (
                  <div className="mt-2 max-h-40 overflow-y-auto border border-gray-300 rounded-lg bg-white shadow-lg">
                    {pacientes.map(paciente => (
                      <button
                        key={paciente.id}
                        type="button"
                        onClick={() => {
                          setSalidaModal(prev => ({ 
                            ...prev, 
                            referencia: `${paciente.nombre_completo} - Exp: ${paciente.numero_expediente}`,
                            pacienteId: paciente.id
                          }));
                          setSearchPaciente('');
                        }}
                        className="w-full text-left px-3 py-2 hover:bg-orange-50 border-b last:border-b-0 flex items-center justify-between"
                      >
                        <div>
                          <div className="font-medium text-gray-900">{paciente.nombre_completo}</div>
                          <div className="text-xs text-gray-500">Expediente: {paciente.numero_expediente}</div>
                        </div>
                        <span className="text-xs text-gray-400">{paciente.dormitorio || ''}</span>
                      </button>
                    ))}
                  </div>
                )}

                {searchPaciente && pacientes.length === 0 && !pacientesLoading && (
                  <div className="mt-2 p-3 bg-gray-50 border border-gray-200 rounded text-sm text-gray-600 text-center">
                    No se encontraron pacientes con "{searchPaciente}"
                  </div>
                )}

                {/* Paciente seleccionado */}
                {salidaModal.referencia && (
                  <div className="mt-2 p-3 bg-green-50 border border-green-300 rounded-lg flex items-center justify-between">
                    <div>
                      <div className="text-sm font-medium text-green-900">✓ Paciente seleccionado:</div>
                      <div className="text-sm text-green-700">{salidaModal.referencia}</div>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        setSalidaModal(prev => ({ ...prev, referencia: '', pacienteId: null }));
                        setSearchPaciente('');
                      }}
                      className="text-red-600 hover:text-red-800"
                    >
                      <FaTimes />
                    </button>
                  </div>
                )}

                <p className="text-xs text-gray-600 mt-2">⚠️ Busque y seleccione al paciente de la lista para evitar duplicados</p>
              </div>
              
              {/* Motivo/Diagnóstico */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  <span className="text-red-600">*</span> Motivo / Diagnóstico / Indicación
                </label>
                <textarea
                  value={salidaModal.motivo}
                  onChange={(e) => setSalidaModal(prev => ({ ...prev, motivo: e.target.value }))}
                  rows={3}
                  placeholder="Ej: Dolor de cabeza - Cefalea tensional, según indicación médica del Dr. López"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                />
              </div>
            </div>
            <div className="px-6 py-4 border-t bg-gray-50 flex justify-end gap-3">
              <button
                onClick={() => {
                  setSalidaModal({ show: false, item: null, cantidad: '', motivo: '', referencia: '', pacienteId: null });
                  setSearchPaciente('');
                  setPacientes([]);
                }}
                className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-100"
              >
                Cancelar
              </button>
              <button
                onClick={handleRegistrarSalida}
                disabled={!salidaModal.cantidad || !salidaModal.motivo || !salidaModal.referencia}
                className="px-5 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium flex items-center gap-2"
              >
                <FaMinusCircle />
                Confirmar Salida
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de ajuste - SOLO DISMINUCIONES */}
      {ajusteModal.show && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-lg">
            <div className="px-6 py-4 border-b bg-purple-50">
              <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
                <FaExchangeAlt className="text-purple-600" />
                Ajustar Inventario (Solo Disminuciones)
              </h2>
              <p className="text-xs text-gray-600 mt-1">
                📊 Registro de mermas, roturas o faltantes detectados en inventario físico
              </p>
            </div>
            <div className="p-6 space-y-4">
              {/* Info del producto */}
              <div className="bg-gradient-to-r from-purple-50 to-purple-100 p-4 rounded-lg border-l-4 border-purple-500">
                <div className="text-sm text-gray-600 font-medium">Producto a Ajustar</div>
                <div className="font-bold text-gray-900 text-lg mt-1">{ajusteModal.item?.descripcion_producto}</div>
                <div className="flex items-center gap-4 mt-3">
                  <div>
                    <div className="text-xs text-gray-500">Stock Actual (Sistema)</div>
                    <div className="font-bold text-blue-600 text-xl">{ajusteModal.item?.cantidad_actual} <span className="text-sm">unidades</span></div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500">Lote</div>
                    <div className="font-medium text-gray-700">{ajusteModal.item?.numero_lote || 'N/A'}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500">Caducidad</div>
                    <div className="font-medium text-gray-700">{ajusteModal.item?.fecha_caducidad || 'N/A'}</div>
                  </div>
                </div>
              </div>

              {/* Quien ajusta */}
              <div className="bg-indigo-50 p-3 rounded-lg border border-indigo-200">
                <div className="flex items-center gap-2">
                  <span className="text-indigo-600 font-medium text-sm">👤 Ajustado por:</span>
                  <span className="text-gray-900 font-semibold">{user?.nombre_completo || user?.username || 'Usuario actual'}</span>
                  <span className="text-xs text-gray-500">({user?.rol || 'N/A'})</span>
                </div>
              </div>

              {/* Advertencia */}
              <div className="bg-yellow-50 border-2 border-yellow-300 rounded-lg p-3">
                <div className="flex items-start gap-2">
                  <span className="text-yellow-600 text-lg">⚠️</span>
                  <div className="text-xs text-yellow-900">
                    <strong>Importante:</strong> Solo se permiten ajustes negativos (disminuciones).
                    Los aumentos de inventario únicamente se realizan mediante compras autorizadas.
                  </div>
                </div>
              </div>
              
              {/* Nueva cantidad */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  <span className="text-red-600">*</span> Nueva Cantidad en Inventario Físico
                </label>
                <input
                  type="number"
                  value={ajusteModal.cantidad}
                  onChange={(e) => setAjusteModal(prev => ({ ...prev, cantidad: e.target.value }))}
                  min="0"
                  max={ajusteModal.item?.cantidad_actual}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                  placeholder={`Debe ser menor a ${ajusteModal.item?.cantidad_actual}`}
                />
                {ajusteModal.cantidad !== '' && parseInt(ajusteModal.cantidad) >= 0 && (
                  <div className={`text-sm mt-2 p-2 rounded ${
                    parseInt(ajusteModal.cantidad) >= ajusteModal.item?.cantidad_actual 
                      ? 'bg-red-50 text-red-700' 
                      : 'bg-green-50 text-green-700'
                  }`}>
                    {parseInt(ajusteModal.cantidad) >= ajusteModal.item?.cantidad_actual ? (
                      <span>❌ La nueva cantidad debe ser menor al stock actual</span>
                    ) : (
                      <span>
                        📉 Se ajustará: <strong>{ajusteModal.item?.cantidad_actual - parseInt(ajusteModal.cantidad)} unidades menos</strong>
                      </span>
                    )}
                  </div>
                )}
              </div>
              
              {/* Motivo del ajuste */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  <span className="text-red-600">*</span> Motivo del Ajuste / Observaciones
                </label>
                <textarea
                  value={ajusteModal.motivo}
                  onChange={(e) => setAjusteModal(prev => ({ ...prev, motivo: e.target.value }))}
                  rows={3}
                  placeholder="Ej: Merma detectada en inventario físico - 5 unidades con caducidad vencida, 2 unidades con rotura de envase"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                />
              </div>
            </div>
            <div className="px-6 py-4 border-t bg-gray-50 flex justify-end gap-3">
              <button
                onClick={() => setAjusteModal({ show: false, item: null, cantidad: '', motivo: '' })}
                className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-100"
              >
                Cancelar
              </button>
              <button
                onClick={handleAjustar}
                disabled={
                  ajusteModal.cantidad === '' || 
                  !ajusteModal.motivo || 
                  parseInt(ajusteModal.cantidad) >= ajusteModal.item?.cantidad_actual
                }
                className="px-5 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium flex items-center gap-2"
              >
                <FaExchangeAlt />
                Confirmar Ajuste
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de movimientos */}
      {movimientosModal.show && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white px-6 py-4 border-b flex justify-between items-center">
              <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
                <FaHistory className="text-blue-600" />
                Historial de Movimientos
              </h2>
              <button
                onClick={() => setMovimientosModal({ show: false, item: null, movimientos: [] })}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <FaTimes />
              </button>
            </div>
            
            <div className="p-6">
              <div className="bg-gray-50 p-3 rounded-lg mb-4">
                <div className="text-sm text-gray-500">Producto</div>
                <div className="font-medium">{movimientosModal.item?.descripcion_producto}</div>
              </div>
              
              {movimientosModal.movimientos.length === 0 ? (
                <p className="text-center text-gray-500 py-8">No hay movimientos registrados</p>
              ) : (
                <div className="space-y-3">
                  {movimientosModal.movimientos.map((mov, idx) => (
                    <div 
                      key={idx} 
                      className={`p-3 rounded-lg border ${
                        mov.tipo === 'entrada' ? 'border-green-200 bg-green-50' :
                        mov.tipo === 'salida' ? 'border-red-200 bg-red-50' :
                        'border-gray-200 bg-gray-50'
                      }`}
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <span className={`inline-flex px-2 py-1 rounded text-xs font-medium ${
                            mov.tipo === 'entrada' ? 'bg-green-100 text-green-800' :
                            mov.tipo === 'salida' ? 'bg-red-100 text-red-800' :
                            'bg-gray-100 text-gray-800'
                          }`}>
                            {mov.tipo?.toUpperCase()}
                          </span>
                          <p className="text-sm text-gray-700 mt-2">{mov.motivo}</p>
                          {mov.referencia && (
                            <p className="text-xs text-gray-500 mt-1">Ref: {mov.referencia}</p>
                          )}
                        </div>
                        <div className="text-right">
                          <div className={`font-bold ${
                            mov.tipo === 'entrada' ? 'text-green-600' : 
                            mov.tipo === 'salida' ? 'text-red-600' : 
                            'text-gray-600'
                          }`}>
                            {mov.tipo === 'entrada' ? '+' : '-'}{mov.cantidad}
                          </div>
                          <div className="text-xs text-gray-500 mt-1">
                            {mov.cantidad_anterior} → {mov.cantidad_nueva}
                          </div>
                        </div>
                      </div>
                      <div className="mt-2 pt-2 border-t border-gray-200 flex justify-between text-xs text-gray-500">
                        <span>{formatDate(mov.created_at)}</span>
                        <span>Por: {mov.usuario?.username || '-'}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default InventarioCajaChica;
