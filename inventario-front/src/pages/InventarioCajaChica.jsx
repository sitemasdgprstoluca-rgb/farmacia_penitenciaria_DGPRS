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
  centrosAPI 
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
} from 'react-icons/fa';
import PageHeader from '../components/PageHeader';
import Pagination from '../components/Pagination';
import { usePermissions } from '../hooks/usePermissions';
import { esFarmaciaAdmin, esCentro } from '../utils/roles';

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
  
  // Modales
  const [detailModal, setDetailModal] = useState({ show: false, item: null });
  const [salidaModal, setSalidaModal] = useState({ show: false, item: null, cantidad: '', motivo: '', referencia: '' });
  const [ajusteModal, setAjusteModal] = useState({ show: false, item: null, cantidad: '', motivo: '' });
  const [movimientosModal, setMovimientosModal] = useState({ show: false, item: null, movimientos: [] });

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

  // Registrar salida
  const handleRegistrarSalida = async () => {
    if (!salidaModal.item || !salidaModal.cantidad || !salidaModal.motivo) {
      toast.error('Debe completar todos los campos requeridos');
      return;
    }
    
    try {
      await inventarioCajaChicaAPI.registrarSalida(salidaModal.item.id, {
        cantidad: parseInt(salidaModal.cantidad),
        motivo: salidaModal.motivo,
        referencia: salidaModal.referencia,
      });
      toast.success('Salida registrada correctamente');
      setSalidaModal({ show: false, item: null, cantidad: '', motivo: '', referencia: '' });
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
    <div className="min-h-screen bg-gray-50 p-4 sm:p-6">
      <PageHeader 
        title="Inventario Caja Chica" 
        subtitle={esSoloAuditoria 
          ? "Auditoría del inventario del centro (solo lectura)"
          : "Inventario de productos comprados con recursos propios"
        }
        icon={FaWarehouse}
      />

      {/* Banner informativo para auditoría */}
      {esSoloAuditoria && (
        <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg flex items-start gap-3">
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
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          <div className="bg-white p-4 rounded-lg shadow border-l-4 border-purple-400">
            <div className="text-2xl font-bold text-purple-600">{resumen.total_items || 0}</div>
            <div className="text-sm text-gray-500">Total Items</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow border-l-4 border-green-400">
            <div className="text-2xl font-bold text-green-600">{resumen.items_con_stock || 0}</div>
            <div className="text-sm text-gray-500">Con Stock</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow border-l-4 border-gray-400">
            <div className="text-2xl font-bold text-gray-600">{resumen.items_agotados || 0}</div>
            <div className="text-sm text-gray-500">Agotados</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow border-l-4 border-yellow-400">
            <div className="text-2xl font-bold text-yellow-600">{resumen.items_por_caducar || 0}</div>
            <div className="text-sm text-gray-500">Por Caducar</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow border-l-4 border-blue-400">
            <div className="text-2xl font-bold text-blue-600">{formatCurrency(resumen.valor_total)}</div>
            <div className="text-sm text-gray-500">Valor Total</div>
          </div>
        </div>
      )}

      {/* Barra de acciones y filtros */}
      <div className="bg-white rounded-lg shadow-sm p-4 mb-4">
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
              onClick={() => setShowFilters(!showFilters)}
              className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-colors ${
                showFilters ? 'bg-purple-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              <FaFilter />
              Filtros
            </button>
          </div>
        </div>

        {/* Panel de filtros */}
        {showFilters && (
          <div className="mt-4 pt-4 border-t">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Centro (solo para farmacia) */}
              {esUsuarioFarmacia && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Centro</label>
                  <select
                    value={centroFiltro}
                    onChange={(e) => setCentroFiltro(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500"
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
            </div>
            
            <div className="flex justify-end mt-4">
              <button
                onClick={handleClearFilters}
                className="px-4 py-2 text-gray-600 hover:text-gray-800 flex items-center gap-2"
            >
              <FaTimes />
              Limpiar filtros
            </button>
          </div>
        </div>
      )}

      {/* Tabla de inventario */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {esUsuarioFarmacia && (
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Centro
                  </th>
                )}
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Producto
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Lote
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Caducidad
                </th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Stock Inicial
                </th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Stock Actual
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Precio Unit.
                </th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
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
                              onClick={() => setSalidaModal({ show: true, item, cantidad: '', motivo: '', referencia: '' })}
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
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
            <div className="px-6 py-4 border-b">
              <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
                <FaMinusCircle className="text-orange-600" />
                Registrar Salida
              </h2>
            </div>
            <div className="p-6 space-y-4">
              <div className="bg-gray-50 p-3 rounded-lg">
                <div className="text-sm text-gray-500">Producto</div>
                <div className="font-medium">{salidaModal.item?.descripcion_producto}</div>
                <div className="text-sm text-gray-500 mt-2">Stock Disponible</div>
                <div className="font-medium text-green-600">{salidaModal.item?.cantidad_actual} unidades</div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Cantidad a salir *</label>
                <input
                  type="number"
                  value={salidaModal.cantidad}
                  onChange={(e) => setSalidaModal(prev => ({ ...prev, cantidad: e.target.value }))}
                  min="1"
                  max={salidaModal.item?.cantidad_actual}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-orange-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Motivo *</label>
                <textarea
                  value={salidaModal.motivo}
                  onChange={(e) => setSalidaModal(prev => ({ ...prev, motivo: e.target.value }))}
                  rows={2}
                  placeholder="Ej: Uso en paciente, dispensación"
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-orange-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Referencia (opcional)</label>
                <input
                  type="text"
                  value={salidaModal.referencia}
                  onChange={(e) => setSalidaModal(prev => ({ ...prev, referencia: e.target.value }))}
                  placeholder="Ej: Expediente del paciente"
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-orange-500"
                />
              </div>
            </div>
            <div className="px-6 py-4 border-t flex justify-end gap-3">
              <button
                onClick={() => setSalidaModal({ show: false, item: null, cantidad: '', motivo: '', referencia: '' })}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
              >
                Cancelar
              </button>
              <button
                onClick={handleRegistrarSalida}
                disabled={!salidaModal.cantidad || !salidaModal.motivo}
                className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50"
              >
                Registrar Salida
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de ajuste */}
      {ajusteModal.show && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
            <div className="px-6 py-4 border-b">
              <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
                <FaExchangeAlt className="text-purple-600" />
                Ajustar Inventario
              </h2>
            </div>
            <div className="p-6 space-y-4">
              <div className="bg-gray-50 p-3 rounded-lg">
                <div className="text-sm text-gray-500">Producto</div>
                <div className="font-medium">{ajusteModal.item?.descripcion_producto}</div>
                <div className="text-sm text-gray-500 mt-2">Stock Actual</div>
                <div className="font-medium">{ajusteModal.item?.cantidad_actual} unidades</div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nueva Cantidad *</label>
                <input
                  type="number"
                  value={ajusteModal.cantidad}
                  onChange={(e) => setAjusteModal(prev => ({ ...prev, cantidad: e.target.value }))}
                  min="0"
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Motivo del ajuste *</label>
                <textarea
                  value={ajusteModal.motivo}
                  onChange={(e) => setAjusteModal(prev => ({ ...prev, motivo: e.target.value }))}
                  rows={2}
                  placeholder="Ej: Inventario físico, merma, rotura"
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500"
                />
              </div>
            </div>
            <div className="px-6 py-4 border-t flex justify-end gap-3">
              <button
                onClick={() => setAjusteModal({ show: false, item: null, cantidad: '', motivo: '' })}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
              >
                Cancelar
              </button>
              <button
                onClick={handleAjustar}
                disabled={ajusteModal.cantidad === '' || !ajusteModal.motivo}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
              >
                Realizar Ajuste
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
