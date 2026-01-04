/**
 * Dashboard - Panel de Control Principal
 * 
 * Diseño moderno y sofisticado con:
 * - CSS Variables dinámicos del tema global
 * - Animaciones fluidas y micro-interacciones
 * - Gráficos interactivos con Recharts
 * - Cards con gradientes dinámicos
 * - Navegación intuitiva a módulos
 * - Diseño 100% responsive
 * 
 * @author SIFP - Sistema de Inventario Farmacéutico Penitenciario
 */

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
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
  FaUser,
  FaCalendarAlt,
  FaBuilding,
  FaClipboardList,
  FaBoxes,
  FaSync,
  FaClock,
  FaTimesCircle,
  FaInfoCircle,
  FaCubes,
  FaHistory,
  FaExpand,
  FaCompress,
  FaGift,
  FaShieldAlt,
} from 'react-icons/fa';
import { 
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  Legend
} from 'recharts';
import { usePermissions } from '../hooks/usePermissions';
import CentroSelector from '../components/CentroSelector';
import { dashboardAPI } from '../services/api';
import { hasAccessToken } from '../services/tokenManager';
import { puedeVerGlobal as checkPuedeVerGlobal } from '../utils/roles';
import './Dashboard.css';

// ============================================================================
// CONSTANTES Y CONFIGURACIÓN
// ============================================================================

const COLORES_ESTADO_REQUISICION = {
  'BORRADOR': '#9CA3AF',
  'PENDIENTE_ADMIN': '#F59E0B',
  'PENDIENTE_DIRECTOR': '#F97316',
  'ENVIADA': '#3B82F6',
  'EN_REVISION': '#6366F1',
  'AUTORIZADA': '#06B6D4',
  'EN_SURTIDO': '#14B8A6',
  'PARCIAL': '#A855F7',
  'SURTIDA': '#22C55E',
  'ENTREGADA': '#10B981',
  'RECHAZADA': '#EF4444',
  'CANCELADA': '#DC2626',
  'VENCIDA': '#B91C1C',
  'DEVUELTA': '#F87171',
  'DEFAULT': '#9F2241',
};

const formatearEstado = (estado) => {
  const ESTADOS_LABEL = {
    'BORRADOR': 'Borrador',
    'PENDIENTE_ADMIN': 'Pend. Admin',
    'PENDIENTE_DIRECTOR': 'Pend. Director',
    'ENVIADA': 'Enviada',
    'EN_REVISION': 'En Revisión',
    'AUTORIZADA': 'Autorizada',
    'EN_SURTIDO': 'En Surtido',
    'SURTIDA': 'Surtida',
    'ENTREGADA': 'Entregada',
    'RECHAZADA': 'Rechazada',
    'CANCELADA': 'Cancelada',
    'VENCIDA': 'Vencida',
    'DEVUELTA': 'Devuelta',
    'PARCIAL': 'Parcial',
  };
  return ESTADOS_LABEL[estado] || estado?.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, c => c.toUpperCase()) || estado;
};

// ============================================================================
// COMPONENTES DE UI REUTILIZABLES
// ============================================================================

/**
 * Tooltip personalizado para gráficas - Usa CSS variables del tema
 */
const CustomTooltip = ({ active, payload, label, formatter }) => {
  if (!active || !payload?.length) return null;
  
  return (
    <div 
      className="rounded-xl shadow-2xl border p-4 min-w-[180px]"
      style={{ 
        backgroundColor: 'rgba(255, 255, 255, 0.98)',
        backdropFilter: 'blur(8px)',
        borderColor: 'var(--color-primary-light, rgba(159, 34, 65, 0.1))'
      }}
    >
      <p 
        className="text-sm font-bold mb-2 pb-2 border-b"
        style={{ 
          color: 'var(--color-primary, #9F2241)',
          borderColor: 'var(--color-primary-light, rgba(159, 34, 65, 0.1))'
        }}
      >
        {label}
      </p>
      {payload.map((entry, index) => (
        <div key={index} className="flex items-center justify-between gap-4 py-1">
          <span className="flex items-center gap-2 text-sm text-gray-600">
            <span 
              className="w-3 h-3 rounded-full shadow-sm" 
              style={{ backgroundColor: entry.color }}
            />
            {entry.name}
          </span>
          <span className="text-sm font-bold text-gray-900">
            {formatter ? formatter(entry.value) : entry.value?.toLocaleString('es-MX')}
          </span>
        </div>
      ))}
    </div>
  );
};

/**
 * Card de KPI animada con gradiente dinámico - Usa CSS variables del tema
 */
const KPICard = ({ 
  title, 
  value, 
  subtext, 
  icon: Icon, 
  trend, 
  trendValue,
  colorType = 'primary',
  onClick,
  delay = 0,
  loading = false
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const [displayValue, setDisplayValue] = useState(0);
  
  // Mapeo de tipos de color a CSS variables
  const getGradient = () => {
    switch(colorType) {
      case 'primary':
        return 'linear-gradient(135deg, var(--color-primary, #9F2241) 0%, var(--color-primary-hover, #6B1839) 100%)';
      case 'success':
        return 'linear-gradient(135deg, var(--color-success, #10B981) 0%, var(--color-success-hover, #059669) 100%)';
      case 'info':
        return 'linear-gradient(135deg, var(--color-info, #06B6D4) 0%, var(--color-info-hover, #0891B2) 100%)';
      case 'warning':
        return 'linear-gradient(135deg, var(--color-warning, #F59E0B) 0%, var(--color-warning-hover, #D97706) 100%)';
      default:
        return 'linear-gradient(135deg, var(--color-primary, #9F2241) 0%, var(--color-primary-hover, #6B1839) 100%)';
    }
  };
  
  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(true), delay);
    return () => clearTimeout(timer);
  }, [delay]);
  
  // Animación de contador
  useEffect(() => {
    if (!isVisible || loading) return;
    
    const duration = 1500;
    const steps = 60;
    const increment = value / steps;
    let current = 0;
    
    const timer = setInterval(() => {
      current += increment;
      if (current >= value) {
        setDisplayValue(value);
        clearInterval(timer);
      } else {
        setDisplayValue(Math.floor(current));
      }
    }, duration / steps);
    
    return () => clearInterval(timer);
  }, [value, isVisible, loading]);

  const gradient = getGradient();

  return (
    <div 
      onClick={onClick}
      className={`
        relative overflow-hidden rounded-2xl p-6
        bg-white shadow-lg border border-gray-100
        transform transition-all duration-500 ease-out
        ${isVisible ? 'translate-y-0 opacity-100' : 'translate-y-8 opacity-0'}
        ${onClick ? 'cursor-pointer hover:shadow-2xl hover:-translate-y-1 hover:scale-[1.02]' : ''}
        group
      `}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {/* Gradiente de fondo sutil */}
      <div 
        className="absolute inset-0 opacity-[0.03] group-hover:opacity-[0.08] transition-opacity duration-500"
        style={{ background: gradient }}
      />
      
      {/* Línea superior de color */}
      <div 
        className="absolute top-0 left-0 right-0 h-1 rounded-t-2xl"
        style={{ background: gradient }}
      />
      
      {/* Contenido */}
      <div className="relative z-10">
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <p className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-1">
              {title}
            </p>
            {loading ? (
              <div className="h-10 w-24 bg-gray-200 rounded animate-pulse" />
            ) : (
              <p className="text-4xl font-black text-gray-900 tabular-nums">
                {displayValue.toLocaleString('es-MX')}
              </p>
            )}
          </div>
          <div 
            className="w-14 h-14 rounded-2xl flex items-center justify-center shadow-lg transform group-hover:scale-110 group-hover:rotate-3 transition-transform duration-300"
            style={{ background: gradient }}
          >
            <Icon className="text-white text-2xl" />
          </div>
        </div>
        
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-500">{subtext}</span>
          {trend && (
            <span className={`
              flex items-center gap-1 text-xs font-bold px-2 py-1 rounded-full
              ${trend === 'up' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}
            `}>
              {trend === 'up' ? <FaArrowUp size={10} /> : <FaArrowDown size={10} />}
              {trendValue}%
            </span>
          )}
        </div>
      </div>
      
      {/* Efecto de hover */}
      {onClick && (
        <div className="absolute bottom-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
          <FaArrowRight className="text-gray-300" />
        </div>
      )}
    </div>
  );
};

/**
 * Card de gráfica con header elegante - Usa CSS variables del tema
 */
const ChartCard = ({ 
  title, 
  icon: Icon, 
  children, 
  action,
  className = "",
  expandable = false,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  
  return (
    <div className={`
      bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden
      transition-all duration-300 hover:shadow-xl
      ${isExpanded ? 'fixed inset-4 z-50' : ''}
      ${className}
    `}>
      {/* Header con gradiente del tema */}
      <div 
        className="px-6 py-4 border-b border-gray-100 flex items-center justify-between"
        style={{ 
          background: 'linear-gradient(to right, var(--color-primary-light, rgba(159, 34, 65, 0.05)), transparent)'
        }}
      >
        <div className="flex items-center gap-3">
          <div 
            className="w-10 h-10 rounded-xl flex items-center justify-center"
            style={{ backgroundColor: 'var(--color-primary-light, rgba(159, 34, 65, 0.1))' }}
          >
            <Icon className="text-lg" style={{ color: 'var(--color-primary, #9F2241)' }} />
          </div>
          <h3 className="font-bold text-gray-800">{title}</h3>
        </div>
        <div className="flex items-center gap-2">
          {action}
          {expandable && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-2 rounded-lg hover:bg-gray-100 transition-colors text-gray-400 hover:text-gray-600"
            >
              {isExpanded ? <FaCompress /> : <FaExpand />}
            </button>
          )}
        </div>
      </div>
      
      {/* Contenido */}
      <div className={`p-6 ${isExpanded ? 'h-[calc(100%-80px)]' : ''}`}>
        {children}
      </div>
      
      {/* Overlay para modo expandido */}
      {isExpanded && (
        <div 
          className="fixed inset-0 bg-black/50 -z-10"
          onClick={() => setIsExpanded(false)}
        />
      )}
    </div>
  );
};

/**
 * Badge de estado con animación - Colores semánticos
 */
const StatusBadge = ({ status, count }) => {
  const color = COLORES_ESTADO_REQUISICION[status] || COLORES_ESTADO_REQUISICION.DEFAULT;
  
  return (
    <div 
      className="flex items-center gap-2 px-3 py-2 rounded-xl transition-all hover:scale-105 cursor-default"
      style={{ backgroundColor: `${color}15` }}
    >
      <span 
        className="w-2.5 h-2.5 rounded-full"
        style={{ backgroundColor: color }}
      />
      <span className="text-sm font-medium text-gray-700">
        {formatearEstado(status)}
      </span>
      <span 
        className="text-xs font-bold px-2 py-0.5 rounded-full text-white"
        style={{ backgroundColor: color }}
      >
        {count}
      </span>
    </div>
  );
};

/**
 * Tarjeta de movimiento reciente - Diseño moderno con colores del tema
 */
const MovimientoCard = ({ mov, onClick, canNavigate }) => {
  const isEntrada = mov.tipo_movimiento === 'ENTRADA';
  
  return (
    <div 
      onClick={onClick}
      className={`
        group bg-white rounded-xl border border-gray-100 p-4
        transition-all duration-300 hover:shadow-lg
        ${canNavigate ? 'cursor-pointer hover:border-gray-200' : ''}
      `}
      style={{ 
        borderLeftWidth: '4px',
        borderLeftColor: isEntrada 
          ? 'var(--color-success, #10B981)' 
          : 'var(--color-error, #EF4444)'
      }}
    >
      <div className="flex items-start gap-4">
        {/* Icono de tipo */}
        <div 
          className="flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center transform group-hover:scale-110 transition-transform duration-300"
          style={{ 
            backgroundColor: isEntrada 
              ? 'var(--color-success-light, rgba(16, 185, 129, 0.1))' 
              : 'var(--color-error-light, rgba(239, 68, 68, 0.1))'
          }}
        >
          {isEntrada ? (
            <FaArrowDown style={{ color: 'var(--color-success, #10B981)', fontSize: '1.25rem' }} />
          ) : (
            <FaArrowUp style={{ color: 'var(--color-error, #EF4444)', fontSize: '1.25rem' }} />
          )}
        </div>
        
        {/* Información principal */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2 mb-2">
            <div>
              <p className="font-bold text-gray-900 group-hover:text-gray-700 transition-colors">
                {mov.producto__clave}
              </p>
              <p className="text-sm text-gray-500 truncate" title={mov.producto__descripcion}>
                {mov.producto__descripcion}
              </p>
            </div>
            <div className="text-right flex-shrink-0">
              <p className="text-2xl font-black text-gray-900">
                {mov.cantidad}
              </p>
              <p className="text-xs text-gray-400">unidades</p>
            </div>
          </div>
          
          {/* Flujo */}
          <div className="flex items-center gap-2 text-xs text-gray-500 mb-2">
            <span className="px-2 py-1 bg-gray-50 rounded-lg font-medium truncate max-w-[100px]" title={mov.origen}>
              {mov.origen || 'Origen'}
            </span>
            <FaArrowRight className="text-gray-300 flex-shrink-0" />
            <span className="px-2 py-1 bg-gray-50 rounded-lg font-medium truncate max-w-[100px]" title={mov.destino}>
              {mov.destino || 'Destino'}
            </span>
          </div>
          
          {/* Metadata */}
          <div className="flex items-center gap-4 text-xs text-gray-400">
            <span className="flex items-center gap-1">
              <FaClock size={10} />
              {new Date(mov.fecha_movimiento).toLocaleString('es-MX', {
                day: '2-digit',
                month: 'short',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>
            {mov.lote__codigo_lote && mov.lote__codigo_lote !== 'N/A' && (
              <span className="flex items-center gap-1">
                <FaBoxes size={10} />
                {mov.lote__codigo_lote}
              </span>
            )}
            {mov.usuario && (
              <span className="flex items-center gap-1">
                <FaUser size={10} />
                {mov.usuario}
              </span>
            )}
          </div>
        </div>
        
        {/* Indicador de navegación */}
        {canNavigate && (
          <div className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity self-center">
            <FaArrowRight className="text-gray-300" />
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * Mini card de acceso rápido - Usa CSS variables del tema
 */
const QuickAccessCard = ({ icon: Icon, title, subtitle, onClick, colorVar }) => (
  <button
    onClick={onClick}
    className="
      flex items-center gap-4 p-4 rounded-xl bg-white border border-gray-100
      shadow-sm hover:shadow-lg transition-all duration-300
      hover:-translate-y-1 hover:border-gray-200 text-left w-full
      group
    "
  >
    <div 
      className="w-12 h-12 rounded-xl flex items-center justify-center transition-transform group-hover:scale-110 group-hover:rotate-3"
      style={{ backgroundColor: `var(${colorVar}-light, rgba(159, 34, 65, 0.1))` }}
    >
      <Icon className="text-xl" style={{ color: `var(${colorVar}, #9F2241)` }} />
    </div>
    <div className="flex-1">
      <p className="font-semibold text-gray-900 group-hover:text-gray-700 transition-colors">
        {title}
      </p>
      <p className="text-sm text-gray-500">{subtitle}</p>
    </div>
    <FaArrowRight className="text-gray-300 group-hover:text-gray-400 transition-colors" />
  </button>
);

/**
 * Skeleton loader para cards
 */
const SkeletonCard = () => (
  <div className="bg-white rounded-2xl p-6 shadow-lg border border-gray-100 animate-pulse">
    <div className="flex justify-between mb-4">
      <div className="space-y-2">
        <div className="h-3 w-20 bg-gray-200 rounded" />
        <div className="h-8 w-32 bg-gray-200 rounded" />
      </div>
      <div className="w-14 h-14 bg-gray-200 rounded-2xl" />
    </div>
    <div className="h-4 w-24 bg-gray-200 rounded" />
  </div>
);

// ============================================================================
// COMPONENTE PRINCIPAL
// ============================================================================

const Dashboard = () => {
  const navigate = useNavigate();
  const { getRolPrincipal, permisos, user, loading: cargandoPermisos } = usePermissions();
  const rolPrincipal = getRolPrincipal();
  
  // Roles y permisos
  const esAdmin = rolPrincipal === 'ADMIN';
  const esFarmacia = rolPrincipal === 'FARMACIA';
  const esVista = rolPrincipal === 'VISTA';
  const esCentro = rolPrincipal === 'CENTRO';
  
  const puedeVerGlobal = checkPuedeVerGlobal(user, permisos);
  const puedeFiltrarPorCentro = (esAdmin || esFarmacia) && !esCentro;
  const centroUsuario = user?.centro?.id || user?.centro;
  const nombreCentroUsuario = user?.centro?.nombre || user?.centro_nombre || '';
  const esCentroRestringido = esCentro || (!puedeVerGlobal && centroUsuario);
  
  const puedeVerGraficasCompletas = esAdmin || esFarmacia || permisos?.isSuperuser;
  const puedeVerGraficasBasicas = puedeVerGraficasCompletas || esVista || esCentro;
  
  // Permisos granulares adicionales
  const puedeGestionarProductos = esAdmin || esFarmacia;
  const puedeGestionarLotes = esAdmin || esFarmacia;
  const puedeCrearRequisiciones = esAdmin || esFarmacia || esCentro;
  const puedeVerCentros = esAdmin || esFarmacia;
  const puedeVerUsuarios = esAdmin;

  // Estados
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
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [movimientosExpanded, setMovimientosExpanded] = useState(true);
  const [selectedCentro, setSelectedCentro] = useState(esCentroRestringido ? centroUsuario : null);
  const [centroNombre, setCentroNombre] = useState('');
  const [lastUpdate, setLastUpdate] = useState(null);
  
  const isMountedRef = useRef(true);

  // Cleanup
  useEffect(() => {
    isMountedRef.current = true;
    return () => { isMountedRef.current = false; };
  }, []);

  // Carga de datos
  const loadDashboard = useCallback(async (centroId = null, isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);

      if (!hasAccessToken()) {
        throw new Error('Sesión no encontrada');
      }

      const centroEfectivo = esCentroRestringido ? centroUsuario : centroId;
      const params = centroEfectivo ? { centro: centroEfectivo } : {};

      const response = await dashboardAPI.getResumen(params);
      
      if (!isMountedRef.current) return;

      const nextKpis = response.data.kpi || {
        total_productos: 0,
        stock_total: 0,
        lotes_activos: 0,
        movimientos_mes: 0,
      };

      setKpis(nextKpis);

      const movimientosData = response.data.ultimos_movimientos || [];
      setMovimientos(
        esVista ? movimientosData.filter((mov) => mov.producto__clave) : movimientosData,
      );

      // Cargar gráficas
      try {
        const graficasResponse = await dashboardAPI.getGraficas(params);
        if (!isMountedRef.current) return;
        setGraficas({
          consumo_mensual: graficasResponse.data.consumo_mensual || [],
          stock_por_centro: graficasResponse.data.stock_por_centro || [],
          requisiciones_por_estado: graficasResponse.data.requisiciones_por_estado || []
        });
      } catch (graficasError) {
        console.warn('Error al cargar gráficas:', graficasError);
        if (isMountedRef.current) {
          setGraficas({
            consumo_mensual: [],
            stock_por_centro: [],
            requisiciones_por_estado: []
          });
        }
      }
      
      setLastUpdate(new Date());
    } catch (err) {
      if (!isMountedRef.current) return;
      
      console.error('Error al cargar dashboard:', err);
      if (err.response?.status === 401) {
        setError('Sesión expirada. Inicia sesión nuevamente.');
      } else {
        setError(err.response?.data?.error || err.message || 'Error al cargar el dashboard');
      }
      setKpis({ total_productos: 0, stock_total: 0, lotes_activos: 0, movimientos_mes: 0 });
      setMovimientos([]);
      setGraficas({ consumo_mensual: [], stock_por_centro: [], requisiciones_por_estado: [] });
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
        setRefreshing(false);
      }
    }
  }, [esVista, esCentroRestringido, centroUsuario]);

  // Sincronizar centro
  useEffect(() => {
    if (!cargandoPermisos && esCentroRestringido && centroUsuario) {
      setSelectedCentro(centroUsuario);
    }
  }, [cargandoPermisos, esCentroRestringido, centroUsuario]);

  // Cargar datos
  useEffect(() => {
    if (cargandoPermisos) return;
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
  }, [loadDashboard, selectedCentro, permisos?.verDashboard, cargandoPermisos]);

  const handleCentroChange = (centroId, nombreCentro = '') => {
    if (esCentroRestringido) return;
    setSelectedCentro(centroId);
    setCentroNombre(nombreCentro);
    setMostrarTodos(false);
  };

  const handleRefresh = () => {
    loadDashboard(selectedCentro, true);
  };

  // Datos computados
  const totalRequisiciones = useMemo(() => {
    return graficas.requisiciones_por_estado.reduce((sum, item) => sum + (item.cantidad || 0), 0);
  }, [graficas.requisiciones_por_estado]);

  // Obtener etiqueta del rol para mostrar
  const getRolLabel = () => {
    if (permisos?.isSuperuser) return 'Superusuario';
    switch(rolPrincipal) {
      case 'ADMIN': return 'Administrador';
      case 'FARMACIA': return 'Farmacia';
      case 'CENTRO': return 'Centro';
      case 'VISTA': return 'Solo Vista';
      default: return 'Usuario';
    }
  };

  // KPI Cards - Usando colorType para CSS variables
  const kpiCards = useMemo(() => [
    {
      title: 'Productos',
      value: kpis.total_productos || 0,
      subtext: puedeGestionarProductos ? 'Gestionar catálogo' : 'Activos en catálogo',
      icon: FaBox,
      colorType: 'primary',
      show: permisos?.verDashboard && permisos?.verProductos,
      onClick: () => permisos?.verProductos && navigate('/productos'),
    },
    {
      title: 'Stock Total',
      value: kpis.stock_total || 0,
      subtext: selectedCentro ? 'En este centro' : 'Unidades disponibles',
      icon: FaCubes,
      colorType: 'success',
      show: permisos?.verDashboard,
      onClick: () => permisos?.verLotes && navigate('/lotes'),
    },
    {
      title: 'Lotes Activos',
      value: kpis.lotes_activos || 0,
      subtext: puedeGestionarLotes ? 'Gestionar lotes' : 'Con inventario',
      icon: FaWarehouse,
      colorType: 'info',
      show: permisos?.verDashboard && permisos?.verLotes,
      onClick: () => permisos?.verLotes && navigate('/lotes'),
    },
    {
      title: 'Movimientos',
      value: kpis.movimientos_mes || 0,
      subtext: 'Este mes',
      icon: FaExchangeAlt,
      colorType: 'warning',
      show: permisos?.verDashboard && permisos?.verMovimientos,
      onClick: () => permisos?.verMovimientos && navigate('/movimientos'),
    },
  ], [kpis, permisos, navigate, puedeGestionarProductos, puedeGestionarLotes, selectedCentro]);

  // Quick access items - Usando CSS variables y permisos granulares
  const quickAccessItems = useMemo(() => [
    {
      icon: FaClipboardList,
      title: 'Requisiciones',
      subtitle: puedeCrearRequisiciones ? 'Crear y gestionar' : 'Ver solicitudes',
      colorVar: '--color-primary',
      show: permisos?.verRequisiciones,
      onClick: () => navigate('/requisiciones'),
    },
    {
      icon: FaGift,
      title: 'Donaciones',
      subtitle: (esAdmin || esFarmacia) ? 'Registrar donaciones' : 'Ver donaciones',
      colorVar: '--color-error',
      show: permisos?.verDonaciones,
      onClick: () => navigate('/donaciones'),
    },
    {
      icon: FaChartLine,
      title: 'Reportes',
      subtitle: 'Análisis y estadísticas',
      colorVar: '--color-info',
      show: permisos?.verReportes,
      onClick: () => navigate('/reportes'),
    },
    {
      icon: FaHistory,
      title: 'Trazabilidad',
      subtitle: 'Historial de lotes',
      colorVar: '--color-warning',
      show: permisos?.verTrazabilidad,
      onClick: () => navigate('/trazabilidad'),
    },
    {
      icon: FaBuilding,
      title: 'Centros',
      subtitle: 'Gestionar centros',
      colorVar: '--color-success',
      show: puedeVerCentros && permisos?.verCentros,
      onClick: () => navigate('/centros'),
    },
    {
      icon: FaUser,
      title: 'Usuarios',
      subtitle: 'Administrar usuarios',
      colorVar: '--color-info',
      show: puedeVerUsuarios && permisos?.verUsuarios,
      onClick: () => navigate('/usuarios'),
    },
    {
      icon: FaShieldAlt,
      title: 'Auditoría',
      subtitle: 'Registro de actividad',
      colorVar: '--color-secondary',
      show: permisos?.verAuditoria,
      onClick: () => navigate('/auditoria'),
    },
  ].filter(item => item.show), [permisos, navigate, puedeCrearRequisiciones, esAdmin, esFarmacia, puedeVerCentros, puedeVerUsuarios]);

  // ========== RENDER ==========
  
  // Loading permisos
  if (cargandoPermisos) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div 
            className="w-16 h-16 border-4 border-t-transparent rounded-full animate-spin mx-auto mb-4"
            style={{ borderColor: 'var(--color-primary, #9F2241)', borderTopColor: 'transparent' }}
          />
          <p className="text-gray-600 font-medium">Cargando permisos...</p>
        </div>
      </div>
    );
  }

  // Sin permisos
  if (!permisos?.verDashboard) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 p-6">
        <div className="bg-white rounded-2xl shadow-xl p-8 text-center max-w-md">
          <div 
            className="w-20 h-20 mx-auto mb-6 rounded-full flex items-center justify-center"
            style={{ backgroundColor: 'var(--color-error-light, rgba(239, 68, 68, 0.1))' }}
          >
            <FaTimesCircle className="text-4xl" style={{ color: 'var(--color-error, #EF4444)' }} />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Acceso Denegado</h2>
          <p className="text-gray-600 mb-6">No tienes permisos para ver el dashboard.</p>
          <button
            onClick={() => navigate('/login')}
            className="px-6 py-3 rounded-xl font-semibold text-white transition-all hover:shadow-lg hover:opacity-90"
            style={{ backgroundColor: 'var(--color-primary, #9F2241)' }}
          >
            Ir a iniciar sesión
          </button>
        </div>
      </div>
    );
  }

  // Usuario de centro sin centro asignado
  if (esCentro && !centroUsuario) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 p-6">
        <div className="bg-white rounded-2xl shadow-xl p-8 text-center max-w-md">
          <div 
            className="w-20 h-20 mx-auto mb-6 rounded-full flex items-center justify-center"
            style={{ backgroundColor: 'var(--color-warning-light, rgba(245, 158, 11, 0.1))' }}
          >
            <FaExclamationTriangle className="text-4xl" style={{ color: 'var(--color-warning, #F59E0B)' }} />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Centro No Asignado</h2>
          <p className="text-gray-600 mb-6">
            Tu cuenta está configurada como usuario de Centro pero no tienes un centro asignado.
            Por favor contacta al administrador.
          </p>
        </div>
      </div>
    );
  }

  // Loading dashboard
  if (loading) {
    return (
      <div className="p-6 max-w-[1600px] mx-auto">
        {/* Header skeleton */}
        <div className="mb-8">
          <div className="h-10 w-64 bg-gray-200 rounded-lg animate-pulse mb-2" />
          <div className="h-5 w-96 bg-gray-200 rounded animate-pulse" />
        </div>
        
        {/* KPI skeletons */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {[1,2,3,4].map(i => <SkeletonCard key={i} />)}
        </div>
        
        {/* Chart skeletons */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-2xl p-6 h-96 animate-pulse">
            <div className="h-6 w-48 bg-gray-200 rounded mb-4" />
            <div className="h-72 bg-gray-100 rounded-xl" />
          </div>
          <div className="bg-white rounded-2xl p-6 h-96 animate-pulse">
            <div className="h-6 w-48 bg-gray-200 rounded mb-4" />
            <div className="h-72 bg-gray-100 rounded-xl" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-[1600px] mx-auto space-y-8 pb-12">
      {/* ========== HEADER ========== */}
      <header className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <h1 
              className="text-4xl font-black tracking-tight"
              style={{ color: 'var(--color-primary, #9F2241)' }}
            >
              Panel de Control
            </h1>
            {/* Badge de rol */}
            <span 
              className="px-3 py-1 rounded-full text-xs font-bold text-white shadow-sm"
              style={{ 
                background: rolPrincipal === 'ADMIN' 
                  ? 'linear-gradient(135deg, #9F2241 0%, #6B1839 100%)'
                  : rolPrincipal === 'FARMACIA'
                  ? 'linear-gradient(135deg, #10B981 0%, #059669 100%)'
                  : rolPrincipal === 'CENTRO'
                  ? 'linear-gradient(135deg, #3B82F6 0%, #2563EB 100%)'
                  : 'linear-gradient(135deg, #6B7280 0%, #4B5563 100%)'
              }}
            >
              {getRolLabel()}
            </span>
          </div>
          <p className="text-gray-500 flex items-center gap-2 flex-wrap">
            {selectedCentro ? (
              <>
                <FaBuilding className="text-sm" />
                Mostrando datos de: <span className="font-semibold">{centroNombre || 'Centro seleccionado'}</span>
              </>
            ) : esCentroRestringido && nombreCentroUsuario ? (
              <>
                <FaBuilding className="text-sm" />
                Centro: <span className="font-semibold">{nombreCentroUsuario}</span>
              </>
            ) : (
              'Resumen general del sistema de inventario'
            )}
          </p>
        </div>
        
        <div className="flex flex-wrap items-center gap-4">
          {/* Selector de centro */}
          {puedeFiltrarPorCentro && (
            <CentroSelector onCentroChange={handleCentroChange} selectedValue={selectedCentro} />
          )}
          
          {/* Botón de refresh */}
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className={`
              p-3 rounded-xl bg-white border border-gray-200 shadow-sm
              hover:shadow-md hover:border-gray-300 transition-all
              ${refreshing ? 'opacity-50 cursor-not-allowed' : ''}
            `}
            title="Actualizar datos"
          >
            <FaSync className={`text-gray-600 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
          
          {/* Fecha actual */}
          <div
            className="hidden md:flex items-center gap-2 px-5 py-3 rounded-2xl font-semibold text-sm text-white shadow-lg"
            style={{ background: 'linear-gradient(135deg, var(--color-primary, #9F2241) 0%, var(--color-primary-hover, #6B1839) 100%)' }}
          >
            <FaCalendarAlt />
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
      </header>

      {/* Indicador de filtro para usuarios restringidos */}
      {esCentroRestringido && centroUsuario && (
        <div 
          className="flex items-center gap-3 px-4 py-3 rounded-xl border"
          style={{ 
            backgroundColor: 'var(--color-primary-light, rgba(159, 34, 65, 0.05))',
            borderColor: 'var(--color-primary-light, rgba(159, 34, 65, 0.2))'
          }}
        >
          <FaInfoCircle style={{ color: 'var(--color-primary, #9F2241)' }} />
          <span className="text-sm" style={{ color: 'var(--color-primary, #9F2241)' }}>
            Mostrando datos exclusivos de: <strong>{nombreCentroUsuario || 'Tu centro asignado'}</strong>
          </span>
        </div>
      )}

      {/* Indicador de filtro activo para admins */}
      {selectedCentro && puedeFiltrarPorCentro && (
        <div 
          className="flex items-center justify-between gap-3 px-4 py-3 rounded-xl border"
          style={{ 
            backgroundColor: 'var(--color-warning-light, rgba(245, 158, 11, 0.05))',
            borderColor: 'var(--color-warning-light, rgba(245, 158, 11, 0.2))'
          }}
        >
          <span className="text-sm flex items-center gap-2" style={{ color: 'var(--color-warning-hover, #D97706)' }}>
            <FaBuilding />
            🔍 Mostrando datos filtrados por: <strong>{centroNombre}</strong>
          </span>
          <button 
            onClick={() => handleCentroChange(null, '')}
            className="text-sm font-medium underline hover:no-underline"
            style={{ color: 'var(--color-warning-hover, #D97706)' }}
          >
            Ver todos los centros
          </button>
        </div>
      )}

      {/* Error */}
      {error && (
        <div 
          className="rounded-xl p-4 flex items-start gap-4 border"
          style={{ 
            backgroundColor: 'var(--color-error-light, rgba(239, 68, 68, 0.05))',
            borderColor: 'var(--color-error-light, rgba(239, 68, 68, 0.2))'
          }}
        >
          <div 
            className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
            style={{ backgroundColor: 'var(--color-error-light, rgba(239, 68, 68, 0.1))' }}
          >
            <FaExclamationTriangle style={{ color: 'var(--color-error, #EF4444)' }} />
          </div>
          <div className="flex-1">
            <h4 className="font-semibold" style={{ color: 'var(--color-error, #EF4444)' }}>Error de conexión</h4>
            <p className="text-sm mt-1" style={{ color: 'var(--color-error-hover, #DC2626)' }}>{error}</p>
            <button
              onClick={error.includes('Sesión') ? () => navigate('/login') : handleRefresh}
              className="mt-3 px-4 py-2 rounded-lg text-white text-sm font-semibold transition-colors hover:opacity-90"
              style={{ backgroundColor: 'var(--color-error, #EF4444)' }}
            >
              {error.includes('Sesión') ? 'Ir a iniciar sesión' : 'Reintentar'}
            </button>
          </div>
        </div>
      )}

      {/* ========== KPI CARDS ========== */}
      <section>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {kpiCards
            .filter(card => card.show)
            .map((card, index) => (
              <KPICard
                key={card.title}
                {...card}
                delay={index * 100}
                loading={refreshing}
              />
            ))}
        </div>
      </section>

      {/* ========== GRÁFICAS PRINCIPALES ========== */}
      {puedeVerGraficasBasicas && (
        <section className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          {/* Consumo Mensual - Area Chart */}
          <ChartCard title="Consumo Mensual (Últimos 6 meses)" icon={FaChartLine} expandable>
            {graficas.consumo_mensual.length > 0 ? (
              <ResponsiveContainer width="100%" height={320}>
                <AreaChart data={graficas.consumo_mensual}>
                  <defs>
                    <linearGradient id="colorEntradas" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--color-success, #10B981)" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="var(--color-success, #10B981)" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorSalidas" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--color-error, #EF4444)" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="var(--color-error, #EF4444)" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                  <XAxis 
                    dataKey="mes" 
                    tick={{ fill: '#6B7280', fontSize: 12 }}
                    axisLine={{ stroke: '#E5E7EB' }}
                  />
                  <YAxis 
                    tick={{ fill: '#6B7280', fontSize: 12 }}
                    axisLine={{ stroke: '#E5E7EB' }}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend />
                  <Area 
                    type="monotone" 
                    dataKey="entradas" 
                    stroke="var(--color-success, #10B981)" 
                    strokeWidth={3}
                    fill="url(#colorEntradas)"
                    name="Entradas"
                    dot={{ fill: 'var(--color-success, #10B981)', strokeWidth: 2, r: 4 }}
                    activeDot={{ r: 6, stroke: '#fff', strokeWidth: 2 }}
                  />
                  <Area 
                    type="monotone" 
                    dataKey="salidas" 
                    stroke="var(--color-error, #EF4444)" 
                    strokeWidth={3}
                    fill="url(#colorSalidas)"
                    name="Salidas"
                    dot={{ fill: 'var(--color-error, #EF4444)', strokeWidth: 2, r: 4 }}
                    activeDot={{ r: 6, stroke: '#fff', strokeWidth: 2 }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex flex-col items-center justify-center h-64 text-gray-400">
                <FaChartLine className="text-4xl mb-3 opacity-50" />
                <p>No hay datos de consumo disponibles</p>
              </div>
            )}
          </ChartCard>

          {/* Stock por Centro - Bar Chart Horizontal */}
          <ChartCard title="Inventario por Centro" icon={FaWarehouse} expandable>
            {graficas.stock_por_centro.length > 0 ? (
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={graficas.stock_por_centro} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" horizontal={false} />
                  <XAxis type="number" tick={{ fill: '#6B7280', fontSize: 12 }} />
                  <YAxis 
                    dataKey="centro" 
                    type="category" 
                    width={120}
                    tick={{ fill: '#6B7280', fontSize: 11 }}
                    tickFormatter={(value) => value.length > 15 ? `${value.slice(0, 15)}...` : value}
                  />
                  <Tooltip content={<CustomTooltip formatter={(v) => `${v.toLocaleString('es-MX')} uds`} />} />
                  <Bar 
                    dataKey="stock" 
                    name="Stock"
                    radius={[0, 8, 8, 0]}
                    fill="var(--color-primary, #9F2241)"
                  />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex flex-col items-center justify-center h-64 text-gray-400">
                <FaWarehouse className="text-4xl mb-3 opacity-50" />
                <p>No hay datos de stock por centro</p>
              </div>
            )}
          </ChartCard>
        </section>
      )}

      {/* ========== REQUISICIONES POR ESTADO ========== */}
      {puedeVerGraficasCompletas && graficas.requisiciones_por_estado.length > 0 && (
        <section>
          <ChartCard 
            title="Requisiciones por Estado" 
            icon={FaClipboardList}
            action={
              <button
                onClick={() => navigate('/requisiciones')}
                className="text-sm px-4 py-2 rounded-lg font-medium transition-colors hover:bg-gray-100"
                style={{ color: 'var(--color-primary, #9F2241)' }}
              >
                Ver todas →
              </button>
            }
          >
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-center">
              {/* Pie Chart */}
              <div className="relative">
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={graficas.requisiciones_por_estado}
                      cx="50%"
                      cy="50%"
                      innerRadius={70}
                      outerRadius={110}
                      paddingAngle={2}
                      dataKey="cantidad"
                    >
                      {graficas.requisiciones_por_estado.map((entry, index) => (
                        <Cell 
                          key={`cell-${index}`} 
                          fill={COLORES_ESTADO_REQUISICION[entry.estado] || COLORES_ESTADO_REQUISICION.DEFAULT}
                          stroke="#fff"
                          strokeWidth={2}
                        />
                      ))}
                    </Pie>
                    <Tooltip 
                      formatter={(value, name, props) => [value, formatearEstado(props.payload.estado)]}
                      contentStyle={{
                        backgroundColor: 'rgba(255,255,255,0.98)',
                        borderRadius: '12px',
                        border: '1px solid #E5E7EB',
                        boxShadow: '0 4px 20px rgba(0,0,0,0.1)'
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
                {/* Centro del donut */}
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                  <div className="text-center">
                    <p className="text-4xl font-black text-gray-900">{totalRequisiciones}</p>
                    <p className="text-sm text-gray-500">Total</p>
                  </div>
                </div>
              </div>
              
              {/* Legend con badges */}
              <div className="flex flex-wrap gap-2 justify-center lg:justify-start">
                {graficas.requisiciones_por_estado.map((item) => (
                  <StatusBadge 
                    key={item.estado}
                    status={item.estado}
                    count={item.cantidad}
                  />
                ))}
              </div>
            </div>
          </ChartCard>
        </section>
      )}

      {/* ========== SECCIÓN INFERIOR: MOVIMIENTOS + ACCESOS RÁPIDOS ========== */}
      <section className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Últimos Movimientos */}
        {puedeVerGraficasBasicas && permisos?.verMovimientos && movimientos.length > 0 && (
          <div className="xl:col-span-2">
            <ChartCard 
              title="Últimos Movimientos" 
              icon={FaExchangeAlt}
              action={
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setMostrarTodos(!mostrarTodos)}
                    className="text-sm px-3 py-1.5 rounded-lg font-medium transition-colors"
                    style={{ 
                      backgroundColor: mostrarTodos ? 'var(--color-primary, #9F2241)' : '#F3F4F6',
                      color: mostrarTodos ? 'white' : '#374151'
                    }}
                  >
                    {mostrarTodos ? 'Ver menos' : `Ver todos (${movimientos.length})`}
                  </button>
                  <button
                    onClick={() => setMovimientosExpanded(!movimientosExpanded)}
                    className="p-2 rounded-lg hover:bg-gray-100 transition-colors text-gray-400"
                  >
                    {movimientosExpanded ? <FaChevronUp /> : <FaChevronDown />}
                  </button>
                </div>
              }
            >
              {movimientosExpanded ? (
                <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2 custom-scrollbar">
                  {(mostrarTodos ? movimientos : movimientos.slice(0, 5)).map((mov, index) => (
                    <MovimientoCard 
                      key={mov.id || index}
                      mov={mov}
                      canNavigate={permisos?.verMovimientos}
                      onClick={() => permisos?.verMovimientos && navigate('/movimientos', { state: { highlightId: mov.id } })}
                    />
                  ))}
                  
                  {/* Botón ir a movimientos */}
                  <button
                    onClick={() => navigate('/movimientos')}
                    className="w-full py-4 rounded-xl font-semibold text-white transition-all hover:shadow-lg hover:opacity-90 flex items-center justify-center gap-2"
                    style={{ background: 'linear-gradient(135deg, var(--color-primary, #9F2241) 0%, var(--color-primary-hover, #6B1839) 100%)' }}
                  >
                    <FaExchangeAlt />
                    Ver todos los movimientos
                  </button>
                </div>
              ) : (
                <div className="text-center py-8">
                  <button
                    onClick={() => setMovimientosExpanded(true)}
                    className="text-gray-400 hover:text-gray-600 transition-colors flex items-center gap-2 mx-auto"
                  >
                    <FaChevronDown />
                    Click para expandir ({movimientos.length} movimientos)
                  </button>
                </div>
              )}
            </ChartCard>
          </div>
        )}

        {/* Accesos Rápidos */}
        {quickAccessItems.length > 0 && (
          <div className="space-y-4">
            <h3 className="font-bold text-gray-800 flex items-center gap-2 px-1">
              <FaArrowRight style={{ color: 'var(--color-primary, #9F2241)' }} />
              Accesos Rápidos
            </h3>
            <div className="space-y-3">
              {quickAccessItems.map((item, index) => (
                <QuickAccessCard key={index} {...item} />
              ))}
            </div>
            
            {/* Última actualización */}
            {lastUpdate && (
              <div className="text-center pt-4 border-t border-gray-100 mt-4">
                <p className="text-xs text-gray-400 flex items-center justify-center gap-1">
                  <FaClock />
                  Última actualización: {lastUpdate.toLocaleTimeString('es-MX')}
                </p>
              </div>
            )}
          </div>
        )}

        {/* Si no hay movimientos pero hay accesos rápidos, mostrarlos en columna completa */}
        {(!movimientos.length || !permisos?.verMovimientos) && quickAccessItems.length === 0 && (
          <div className="xl:col-span-3 text-center py-12 text-gray-400">
            <FaInfoCircle className="text-4xl mx-auto mb-3 opacity-50" />
            <p>No hay datos adicionales para mostrar</p>
          </div>
        )}
      </section>

      {/* ========== FOOTER CON INFO ========== */}
      <footer className="pt-6 border-t border-gray-100 text-center">
        <p className="text-xs text-gray-400">
          Sistema de Inventario Farmacéutico Penitenciario • Versión 2.0
        </p>
      </footer>
    </div>
  );
};

export default Dashboard;
