import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FaBox,
  FaWarehouse,
  FaExclamationTriangle,
  FaArrowUp,
  FaArrowDown,
  FaChartLine,
  FaExchangeAlt,
  FaChevronDown,
  FaChevronUp,
  FaArrowRight,
  FaFileAlt,
  FaUser,
  FaEye,
} from 'react-icons/fa';
import { 
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer 
} from 'recharts';
import { usePermissions } from '../hooks/usePermissions';
import CentroSelector from '../components/CentroSelector';
import '../styles/Dashboard.css';
import { dashboardAPI } from '../services/api';
import { hasAccessToken } from '../services/tokenManager';

// Colores para gráficas - usarán variables CSS cuando sea posible
const COLORS = ['var(--color-primary, #9F2241)', '#10B981', '#F59E0B', '#06B6D4', '#8B5CF6'];

const Dashboard = () => {
  const navigate = useNavigate();
  const { getRolPrincipal, permisos, user } = usePermissions();
  const rolPrincipal = getRolPrincipal();
  const esVistaUser = rolPrincipal === 'VISTA_USER' || rolPrincipal === 'VISTA';
  
  // Detectar si el usuario tiene acceso global o está restringido a un centro
  // NOTA: El backend solo acepta filtro por centro para ADMIN/FARMACIA, no para VISTA
  const puedeVerGlobal = ['ADMIN', 'FARMACIA'].includes(rolPrincipal) || permisos?.isSuperuser;
  // Solo ADMIN/FARMACIA pueden filtrar por centro en el backend
  const puedeFiltrarPorCentro = ['ADMIN', 'FARMACIA'].includes(rolPrincipal) || permisos?.isSuperuser;
  const centroUsuario = user?.centro?.id || user?.centro;
  const esCentroUser = rolPrincipal === 'CENTRO' || (!puedeVerGlobal && centroUsuario && !esVistaUser);

  const [kpis, setKpis] = useState({
    total_productos: 0,
    stock_total: 0,
    lotes_activos: 0,
    movimientos_mes: 0,
  });
  const [movimientos, setMovimientos] = useState([]);
  const [mostrarTodos, setMostrarTodos] = useState(false);
  const [graficas, setGraficas] = useState({
    consumo_mensual: [],
    stock_por_centro: [],
    requisiciones_por_estado: []
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [movimientosCollapsed, setMovimientosCollapsed] = useState(true); // Colapsado por defecto
  // Para usuarios de centro, forzar su centro asignado; para globales, null (todos)
  const [selectedCentro, setSelectedCentro] = useState(esCentroUser ? centroUsuario : null);
  const [centroNombre, setCentroNombre] = useState('');

  // eslint-disable-next-line no-unused-vars
  const applyMockDashboard = useCallback(() => {
    setKpis({
      total_productos: 124,
      stock_total: 4800,
      lotes_activos: 52,
      movimientos_mes: 37,
    });
    setMovimientos([
      {
        id: 1,
        tipo_movimiento: 'ENTRADA',
        producto__clave: 'MED-001',
        producto__descripcion: 'Paracetamol 500mg',
        lote__codigo_lote: 'LOTE-001',
        cantidad: 150,
        fecha_movimiento: new Date().toISOString(),
      },
      {
        id: 2,
        tipo_movimiento: 'SALIDA',
        producto__clave: 'MED-008',
        producto__descripcion: 'Ibuprofeno 400mg',
        lote__codigo_lote: 'LOTE-014',
        cantidad: 80,
        fecha_movimiento: new Date().toISOString(),
      },
    ]);
    setError(null);
    setLoading(false);
  }, []);

  const loadDashboard = useCallback(async (centroId = null) => {
    try {
      setLoading(true);
      setError(null);

      // Verificar que hay token en memoria (tokenManager)
      if (!hasAccessToken()) {
        throw new Error('Sesión no encontrada');
      }

      // Para usuarios de centro, SIEMPRE forzar su centro asignado
      // Esto asegura aislamiento de datos aunque el backend también lo valide
      const centroEfectivo = esCentroUser ? centroUsuario : centroId;
      
      // Parámetros con filtro de centro
      const params = centroEfectivo ? { centro: centroEfectivo } : {};

      // Cargar resumen KPIs y movimientos
      const response = await dashboardAPI.getResumen(params);

      const nextKpis = response.data.kpi || {
        total_productos: 0,
        stock_total: 0,
        lotes_activos: 0,
        movimientos_mes: 0,
      };

      setKpis(
        esVistaUser
          ? {
              lotes_activos: nextKpis.lotes_activos,
              stock_total: nextKpis.stock_total,
            }
          : nextKpis,
      );

      // Filtrar movimientos para Vista: solo los que tengan producto__clave
      // El backend ya debería filtrar por centro, pero añadimos filtro local por seguridad
      const movimientosData = response.data.ultimos_movimientos || [];
      setMovimientos(
        esVistaUser ? movimientosData.filter((mov) => mov.producto__clave) : movimientosData,
      );

      // Cargar datos de gráficas
      try {
        const graficasResponse = await dashboardAPI.getGraficas(params);
        setGraficas({
          consumo_mensual: graficasResponse.data.consumo_mensual || [],
          stock_por_centro: graficasResponse.data.stock_por_centro || [],
          requisiciones_por_estado: graficasResponse.data.requisiciones_por_estado || []
        });
      } catch (graficasError) {
        console.warn('Error al cargar gráficas, usando datos vacíos:', graficasError);
      }
    } catch (err) {
      console.error('Error al cargar dashboard:', err);
      if (err.response?.status === 401) {
        setError('Sesión expirada. Inicia sesión nuevamente.');
      } else {
        setError(err.response?.data?.error || err.message || 'Error al cargar el dashboard');
      }
      setKpis({
        total_productos: 0,
        stock_total: 0,
        lotes_activos: 0,
        movimientos_mes: 0,
      });
      setMovimientos([]);
    } finally {
      setLoading(false);
    }
  }, [esVistaUser, esCentroUser, centroUsuario]);

  useEffect(() => {
    // No cargar si no tiene permiso de dashboard o no hay token
    if (!permisos?.verDashboard) {
      setLoading(false);
      return;
    }
    if (!hasAccessToken()) {
      setError('Sesión no encontrada');
      setLoading(false);
      return;
    }
    loadDashboard(selectedCentro);
  }, [loadDashboard, selectedCentro, permisos?.verDashboard]);

  const handleCentroChange = (centroId, nombreCentro = '') => {
    // Los usuarios de centro no pueden cambiar su centro
    if (esCentroUser) return;
    
    setSelectedCentro(centroId);
    setCentroNombre(nombreCentro);
    // Resetear estados de visualización al cambiar de centro
    setMostrarTodos(false);
    setMovimientosCollapsed(true);
    // El useEffect se encarga de cargar cuando selectedCentro cambia
  };

  const formatFecha = (fecha) =>
    new Date(fecha).toLocaleString('es-MX', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });

  const CentroTick = ({ x, y, payload }) => {
    const label = payload.value || '';
    const display = label.length > 12 ? `${label.slice(0, 12)}…` : label;
    return (
      <g transform={`translate(${x},${y})`}>
        <title>{label}</title>
        <text x={0} y={0} dy={16} textAnchor="middle" fill="#374151" fontSize="12px">
          {display}
        </text>
      </g>
    );
  };

  if (!permisos?.verDashboard) {
    return (
      <div className="dashboard-container">
        <div className="error-alert">No tiene permisos para ver el dashboard.</div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="dashboard-container">
        <div className="loading-state">
          <div className="spinner" />
          <p>Cargando dashboard...</p>
        </div>
      </div>
    );
  }

  // Las tarjetas KPI usan verDashboard como permiso base - si puede ver el dashboard, ve los KPIs
  // Cada KPI adicional puede tener su propio permiso granular si se requiere
  const statCards = [
    {
      title: 'TOTAL',
      subtitle: 'PRODUCTOS',
      value: kpis.total_productos || 0,
      subtext: 'Activos',
      icon: FaBox,
      gradient: 'linear-gradient(135deg, #9F2241 0%, #7D1B35 100%)',
      iconBg: '#9F2241',
      badge: '↑ 12%',
      badgeColor: '#10B981',
      show: permisos?.verDashboard && permisos?.verProductos,
    },
    {
      title: 'INVENTARIO TOTAL',
      subtitle: '',
      value: kpis.stock_total || 0,
      subtext: 'Unidades',
      icon: FaChartLine,
      gradient: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
      iconBg: '#10B981',
      badge: '↑ 6%',
      badgeColor: '#10B981',
      show: permisos?.verDashboard, // KPI básico del dashboard
    },
    {
      title: 'LOTES ACTIVOS',
      subtitle: '',
      value: kpis.lotes_activos || 0,
      subtext: 'Con inventario',
      icon: FaWarehouse,
      gradient: 'linear-gradient(135deg, #06B6D4 0%, #0891B2 100%)',
      iconBg: '#06B6D4',
      badge: '≈ 0%',
      badgeColor: '#6B7280',
      show: permisos?.verDashboard && permisos?.verLotes,
    },
    {
      title: 'MOVIMIENTOS',
      subtitle: '',
      value: kpis.movimientos_mes || 0,
      subtext: 'Este mes',
      icon: FaExchangeAlt,
      gradient: 'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)',
      iconBg: '#F59E0B',
      badge: '↑ 15%',
      badgeColor: '#10B981',
      show: permisos?.verDashboard && permisos?.verMovimientos,
    },
  ];

  return (
    <div className="dashboard-container">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between mb-8 gap-4">
        <div>
          <h1 className="text-4xl font-bold" style={{ color: 'var(--color-primary-hover, #6B1839)' }}>
            Panel de Control
          </h1>
          <p className="text-base mt-2" style={{ color: 'var(--color-text-secondary, #6B7280)' }}>
            {selectedCentro 
              ? `📍 Filtrando: ${centroNombre || 'Centro seleccionado'}`
              : 'Resumen general del sistema de inventario'
            }
          </p>
        </div>
        <div className="flex flex-col md:flex-row items-start md:items-center gap-4">
          {/* Selector de centro solo para admin/farmacia (backend no soporta filtro para vista) */}
          {puedeFiltrarPorCentro && (
            <CentroSelector onCentroChange={handleCentroChange} selectedValue={selectedCentro} />
          )}
          <div
            className="px-5 py-2.5 rounded-2xl font-semibold text-sm"
            style={{ background: 'linear-gradient(135deg, var(--color-primary, #9F2241) 0%, var(--color-primary-hover, #6B1839) 100%)', color: 'white' }}
          >
            <span>
              {new Date().toLocaleDateString('es-MX', {
                weekday: 'long',
                day: 'numeric',
                month: 'long',
                year: 'numeric',
              })}
            </span>
          </div>
        </div>
      </div>

      {/* Indicador de filtro activo - solo para usuarios que pueden cambiar el filtro */}
      {selectedCentro && puedeFiltrarPorCentro && (
        <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-center gap-2">
          <span className="text-amber-600 font-medium">🔍 Mostrando datos filtrados por: <strong>{centroNombre}</strong></span>
          <button 
            onClick={() => handleCentroChange(null, '')}
            className="ml-auto text-sm text-amber-700 hover:text-amber-900 underline"
          >
            Ver todos los centros
          </button>
        </div>
      )}
      
      {/* Indicador de centro fijo para usuarios de centro (no pueden cambiar) */}
      {esCentroUser && centroUsuario && (
        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg flex items-center gap-2">
          <span className="text-blue-600 font-medium">📍 Mostrando datos de tu centro asignado</span>
        </div>
      )}

      {error && (
        <div className="error-alert">
          <FaExclamationTriangle />
          <div>
            <strong>Error de conexión con el backend</strong>
            <p>{error}</p>
            {error.includes('Sesión') ? (
              <button onClick={() => navigate('/login')} className="btn btn-primary">
                Ir a iniciar sesión
              </button>
            ) : (
              <button 
                onClick={() => {
                  if (!hasAccessToken()) {
                    navigate('/login');
                    return;
                  }
                  if (!permisos?.verDashboard) {
                    setError('No tiene permisos para ver el dashboard');
                    return;
                  }
                  loadDashboard(selectedCentro);
                }} 
                className="btn btn-primary"
              >
                Reintentar
              </button>
            )}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {statCards
          .filter((card) => card.show)
          .map((card, index) => {
            const Icon = card.icon;
            return (
              <div
                key={index}
                className="bg-white rounded-xl shadow-lg p-6 border-l-4 hover:shadow-2xl transition-all transform hover:-translate-y-1"
                style={{ borderLeftColor: card.iconBg }}
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <p className="text-xs font-bold mb-1" style={{ color: '#6B7280', letterSpacing: '0.5px' }}>
                      {card.title}
                    </p>
                    {card.subtitle && (
                      <p className="text-xs font-semibold" style={{ color: '#9CA3AF' }}>
                        {card.subtitle}
                      </p>
                    )}
                  </div>
                  <div className="rounded-xl p-3 shadow-md" style={{ background: card.gradient }}>
                    <Icon className="text-white text-2xl" />
                  </div>
                </div>
                <div className="flex items-end justify-between">
                  <div>
                    <p className="text-4xl font-bold" style={{ color: '#1F2937' }}>
                      {card.value}
                    </p>
                    <p className="text-sm font-medium mt-1" style={{ color: '#6B7280' }}>
                      {card.subtext}
                    </p>
                  </div>
                  <div className="px-3 py-1 rounded-full text-xs font-bold text-white" style={{ backgroundColor: card.badgeColor }}>
                    {card.badge}
                  </div>
                </div>
              </div>
            );
          })}
      </div>

      {/* Gráficas Analíticas */}
      {!esVistaUser && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
          {/* Gráfica 1: Consumo Mensual */}
          <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-200">
            <h3 className="text-lg font-bold mb-4 flex items-center gap-2" style={{ color: 'var(--color-primary-hover, #6B1839)' }}>
              <FaChartLine /> Consumo Mensual (Últimos 6 meses)
            </h3>
            {graficas.consumo_mensual.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={graficas.consumo_mensual}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="mes" style={{ fontSize: '12px' }} />
                  <YAxis style={{ fontSize: '12px' }} />
                  <Tooltip />
                  <Legend />
                  <Line 
                    type="monotone" 
                    dataKey="entradas" 
                    stroke="#10B981" 
                    strokeWidth={2}
                    name="Entradas"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="salidas" 
                    stroke="#9F2241" 
                    strokeWidth={2}
                    name="Salidas"
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-64 text-gray-400">
                <p>No hay datos disponibles</p>
              </div>
            )}
          </div>

          {/* Gráfica 2: Inventario por Centro */}
          <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-200">
            <h3 className="text-lg font-bold mb-4 flex items-center gap-2" style={{ color: 'var(--color-primary-hover, #6B1839)' }}>
              <FaWarehouse /> Inventario por Centro
            </h3>
            {graficas.stock_por_centro.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={graficas.stock_por_centro}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="centro" tick={<CentroTick />} />
                  <YAxis style={{ fontSize: '12px' }} />
                  <Tooltip
                    formatter={(value) => [`${value} uds`, 'Inventario']}
                    labelFormatter={(label) => label}
                  />
                  <Bar dataKey="stock" fill="#9F2241" name="Inventario" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-64 text-gray-400">
                <p>No hay datos disponibles</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Gráfica 3: Requisiciones por Estado - Solo si hay datos */}
      {!esVistaUser && graficas.requisiciones_por_estado.length > 0 && (
        <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-200 mt-6">
          <h3 className="text-lg font-bold mb-4 flex items-center gap-2" style={{ color: 'var(--color-primary-hover, #6B1839)' }}>
            <FaBox /> Requisiciones por Estado
          </h3>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={graficas.requisiciones_por_estado}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ estado, cantidad }) => `${estado}: ${cantidad}`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="cantidad"
              >
                {graficas.requisiciones_por_estado.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Últimos Movimientos - Solo si tiene permiso de ver movimientos */}
      {!esVistaUser && permisos?.verMovimientos && movimientos.length > 0 && (
        <div className="dashboard-section mt-6">
          <div className="section-header" style={{ cursor: 'pointer', userSelect: 'none' }} onClick={() => setMovimientosCollapsed(!movimientosCollapsed)}>
            <h3>
              <FaExchangeAlt /> Últimos Movimientos
            </h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <button
                onClick={(e) => { e.stopPropagation(); setMostrarTodos(!mostrarTodos); }}
                className="text-sm px-3 py-1 rounded-full transition-colors"
                style={{ 
                  background: mostrarTodos ? '#9F2241' : '#e5e7eb', 
                  color: mostrarTodos ? 'white' : '#374151',
                  border: 'none',
                  cursor: 'pointer'
                }}
              >
                {mostrarTodos ? 'Ver menos' : `Ver todos (${movimientos.length})`}
              </button>
              <button 
                onClick={(e) => { e.stopPropagation(); setMovimientosCollapsed(!movimientosCollapsed); }}
                className="text-gray-600 hover:text-gray-800 transition-colors"
                style={{ background: 'none', border: 'none', padding: '4px', fontSize: '20px', cursor: 'pointer' }}
                aria-label={movimientosCollapsed ? "Expandir" : "Contraer"}
              >
                {movimientosCollapsed ? <FaChevronDown /> : <FaChevronUp />}
              </button>
            </div>
          </div>

          {!movimientosCollapsed && (
            <div className="movements-container">
              <div className="space-y-3">
                {(mostrarTodos ? movimientos : movimientos.slice(0, 5)).map((mov, index) => (
                  <div 
                    key={mov.id || index} 
                    onClick={() => permisos?.verMovimientos && navigate('/movimientos', { state: { highlightId: mov.id } })}
                    className={`bg-white rounded-lg border border-gray-200 p-4 transition-all ${permisos?.verMovimientos ? 'hover:shadow-md hover:border-gray-300 cursor-pointer' : ''}`}
                    style={{ borderLeft: `4px solid ${mov.tipo_movimiento === 'ENTRADA' ? '#10B981' : '#EF4444'}` }}
                  >
                    <div className="flex items-start justify-between gap-4">
                      {/* Columna izquierda: Tipo + Producto */}
                      <div className="flex items-start gap-3 flex-1 min-w-0">
                        <div className="flex-shrink-0">
                          <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-bold ${
                            mov.tipo_movimiento === 'ENTRADA' 
                              ? 'bg-green-100 text-green-700' 
                              : 'bg-red-100 text-red-700'
                          }`}>
                            {mov.tipo_movimiento === 'ENTRADA' ? <FaArrowDown size={10} /> : <FaArrowUp size={10} />}
                            {mov.tipo_movimiento}
                          </span>
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="font-semibold text-gray-900 text-sm">{mov.producto__clave}</p>
                          <p className="text-gray-600 text-xs truncate" title={mov.producto__descripcion}>
                            {mov.producto__descripcion}
                          </p>
                        </div>
                      </div>

                      {/* Columna central: Flujo */}
                      <div className="flex-shrink-0 text-center hidden md:block" style={{ minWidth: '200px' }}>
                        <div className="flex items-center justify-center gap-2 text-xs">
                          <span className="px-2 py-1 rounded bg-gray-100 text-gray-700 max-w-[90px] truncate" title={mov.origen}>
                            {mov.origen || 'Origen'}
                          </span>
                          <FaArrowRight className="text-gray-400 flex-shrink-0" size={12} />
                          <span className="px-2 py-1 rounded bg-gray-100 text-gray-700 max-w-[90px] truncate" title={mov.destino}>
                            {mov.destino || 'Destino'}
                          </span>
                        </div>
                        {mov.lote__codigo_lote && (
                          <p className="text-xs text-gray-500 mt-1">Lote: {mov.lote__codigo_lote}</p>
                        )}
                      </div>

                      {/* Columna derecha: Cantidad + Fecha */}
                      <div className="flex-shrink-0 text-right">
                        <p className="text-2xl font-bold text-gray-900">{mov.cantidad}</p>
                        <p className="text-xs text-gray-500">unidades</p>
                      </div>
                    </div>

                    {/* Fila inferior: Metadata */}
                    <div className="flex items-center justify-between mt-2 pt-2 border-t border-gray-100 text-xs text-gray-500">
                      <div className="flex items-center gap-4">
                        <span>{formatFecha(mov.fecha_movimiento)}</span>
                        {mov.usuario && (
                          <span className="flex items-center gap-1">
                            <FaUser size={10} /> {mov.usuario}
                          </span>
                        )}
                        {mov.requisicion_folio && (
                          <span className="flex items-center gap-1 text-blue-600">
                            <FaFileAlt size={10} /> {mov.requisicion_folio}
                          </span>
                        )}
                      </div>
                      {permisos?.verMovimientos && (
                        <span className="text-gray-400 flex items-center gap-1">
                          <FaEye size={12} /> Ver detalle
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              
              {/* Botón para ir al módulo de movimientos - solo si tiene permiso */}
              {permisos?.verMovimientos && (
                <div className="text-center mt-4">
                  <button
                    onClick={() => navigate('/movimientos')}
                    className="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                    style={{ 
                      background: 'linear-gradient(135deg, #9F2241 0%, #6B1839 100%)', 
                      color: 'white',
                      border: 'none',
                      cursor: 'pointer'
                    }}
                  >
                    <FaExchangeAlt style={{ display: 'inline', marginRight: '8px' }} />
                    Ver todos los movimientos en detalle
                  </button>
                </div>
              )}
          </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Dashboard;

