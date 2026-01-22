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
 * Card de KPI Premium - Diseño pulido y profesional
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
  const [isHovered, setIsHovered] = useState(false);
  
  // Colores por tipo
  const colorConfig = {
    primary: {
      gradient: 'linear-gradient(135deg, #9F2241 0%, #6B1839 100%)',
      bg: 'rgba(159, 34, 65, 0.08)',
      bgHover: 'rgba(159, 34, 65, 0.12)',
      text: '#9F2241',
      light: 'rgba(159, 34, 65, 0.1)',
    },
    success: {
      gradient: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
      bg: 'rgba(16, 185, 129, 0.08)',
      bgHover: 'rgba(16, 185, 129, 0.12)',
      text: '#059669',
      light: 'rgba(16, 185, 129, 0.1)',
    },
    info: {
      gradient: 'linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%)',
      bg: 'rgba(14, 165, 233, 0.08)',
      bgHover: 'rgba(14, 165, 233, 0.12)',
      text: '#0284C7',
      light: 'rgba(14, 165, 233, 0.1)',
    },
    warning: {
      gradient: 'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)',
      bg: 'rgba(245, 158, 11, 0.08)',
      bgHover: 'rgba(245, 158, 11, 0.12)',
      text: '#D97706',
      light: 'rgba(245, 158, 11, 0.1)',
    },
  };
  
  const colors = colorConfig[colorType] || colorConfig.primary;
  
  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(true), delay);
    return () => clearTimeout(timer);
  }, [delay]);
  
  // Animación de contador suave
  useEffect(() => {
    if (!isVisible || loading) return;
    
    const duration = 1200;
    const frameDuration = 1000 / 60;
    const totalFrames = Math.round(duration / frameDuration);
    let frame = 0;
    
    const counter = setInterval(() => {
      frame++;
      const progress = frame / totalFrames;
      // Easing: ease-out-cubic
      const easeProgress = 1 - Math.pow(1 - progress, 3);
      const currentValue = Math.round(easeProgress * value);
      
      setDisplayValue(currentValue);
      
      if (frame === totalFrames) {
        clearInterval(counter);
        setDisplayValue(value);
      }
    }, frameDuration);
    
    return () => clearInterval(counter);
  }, [value, isVisible, loading]);

  return (
    <div 
      onClick={onClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className={`
        relative overflow-hidden rounded-2xl
        bg-white border border-gray-100
        transform transition-all duration-300 ease-out
        ${isVisible ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0'}
        ${onClick ? 'cursor-pointer' : ''}
        group
      `}
      style={{ 
        transitionDelay: `${delay}ms`,
        boxShadow: isHovered 
          ? '0 20px 40px -12px rgba(0, 0, 0, 0.15), 0 0 0 1px rgba(0, 0, 0, 0.02)'
          : '0 4px 16px -4px rgba(0, 0, 0, 0.08), 0 0 0 1px rgba(0, 0, 0, 0.02)',
        transform: isHovered && onClick ? 'translateY(-4px) scale(1.01)' : 'translateY(0) scale(1)',
      }}
    >
      {/* Barra de color superior */}
      <div 
        className="h-1 w-full"
        style={{ background: colors.gradient }}
      />
      
      {/* Contenido principal */}
      <div className="p-5">
        {/* Header: Título + Icono */}
        <div className="flex items-start justify-between gap-3 mb-4">
          <div className="flex-1 min-w-0">
            <p 
              className="text-[11px] font-bold uppercase tracking-widest mb-0.5"
              style={{ color: colors.text }}
            >
              {title}
            </p>
            <p className="text-xs text-gray-400 truncate">{subtext}</p>
          </div>
          
          {/* Icono con fondo */}
          <div 
            className="flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-300"
            style={{ 
              background: colors.gradient,
              boxShadow: isHovered 
                ? `0 8px 20px -4px ${colors.light}`
                : `0 4px 12px -2px ${colors.light}`,
              transform: isHovered ? 'scale(1.08) rotate(3deg)' : 'scale(1) rotate(0)',
            }}
          >
            <Icon className="text-white text-xl" />
          </div>
        </div>
        
        {/* Valor principal */}
        <div className="mb-3">
          {loading ? (
            <div className="h-12 w-28 bg-gray-100 rounded-lg animate-pulse" />
          ) : (
            <div className="flex items-baseline gap-1">
              <span 
                className="text-4xl font-black tracking-tight tabular-nums"
                style={{ 
                  color: '#1F2937',
                  textShadow: '0 1px 2px rgba(0,0,0,0.05)'
                }}
              >
                {displayValue.toLocaleString('es-MX')}
              </span>
            </div>
          )}
        </div>
        
        {/* Footer: Trend o indicador de acción */}
        <div className="flex items-center justify-between pt-3 border-t border-gray-50">
          {trend ? (
            <div 
              className={`
                inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold
                ${trend === 'up' ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-600'}
              `}
            >
              {trend === 'up' ? <FaArrowUp size={9} /> : <FaArrowDown size={9} />}
              {trendValue}%
            </div>
          ) : (
            <div className="text-xs text-gray-300">•</div>
          )}
          
          {onClick && (
            <div 
              className="flex items-center gap-1 text-xs font-medium transition-all duration-300"
              style={{ 
                color: isHovered ? colors.text : '#9CA3AF',
                transform: isHovered ? 'translateX(2px)' : 'translateX(0)',
              }}
            >
              <span>Ver más</span>
              <FaArrowRight size={10} />
            </div>
          )}
        </div>
      </div>
      
      {/* Decoración de fondo */}
      <div 
        className="absolute -right-8 -bottom-8 w-32 h-32 rounded-full opacity-[0.03] transition-opacity duration-300"
        style={{ 
          background: colors.gradient,
          opacity: isHovered ? 0.08 : 0.03,
        }}
      />
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
 * Skeleton loader para KPI cards - Coincide con nuevo diseño
 */
const SkeletonCard = () => (
  <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden animate-pulse">
    <div className="h-1 w-full bg-gray-200" />
    <div className="p-5">
      <div className="flex justify-between mb-4">
        <div className="space-y-2">
          <div className="h-3 w-16 bg-gray-200 rounded" />
          <div className="h-3 w-28 bg-gray-100 rounded" />
        </div>
        <div className="w-12 h-12 bg-gray-200 rounded-xl" />
      </div>
      <div className="h-10 w-24 bg-gray-200 rounded-lg mb-3" />
      <div className="pt-3 border-t border-gray-50 flex justify-between">
        <div className="h-4 w-16 bg-gray-100 rounded" />
        <div className="h-4 w-14 bg-gray-100 rounded" />
      </div>
    </div>
  </div>
);

// ============================================================================
// COMPONENTE PRINCIPAL
// ============================================================================

const Dashboard = () => {
  const navigate = useNavigate();
  const { getRolPrincipal, permisos, user, loading: cargandoPermisos } = usePermissions();
  const rolPrincipal = getRolPrincipal();
  
  // ISS-FIX: Verificar si los permisos están validándose
  const permisosEnValidacion = permisos?._isValidating || permisos?._source === 'pending_validation';
  
  // Roles y permisos - usar valores seguros durante validación
  const esAdmin = !permisosEnValidacion && rolPrincipal === 'ADMIN';
  const esFarmacia = !permisosEnValidacion && rolPrincipal === 'FARMACIA';
  const esVista = !permisosEnValidacion && rolPrincipal === 'VISTA';
  const esCentro = !permisosEnValidacion && rolPrincipal === 'CENTRO';
  
  // ISS-FIX: Durante validación, usar permisos del user si están disponibles
  const puedeVerGlobal = permisosEnValidacion ? false : checkPuedeVerGlobal(user, permisos);
  const puedeFiltrarPorCentro = (esAdmin || esFarmacia) && !esCentro;
  const centroUsuario = user?.centro?.id || user?.centro;
  const nombreCentroUsuario = user?.centro?.nombre || user?.centro_nombre || '';
  // ISS-FIX: Si tiene centro asignado, restringir por defecto hasta validar
  const esCentroRestringido = esCentro || (!puedeVerGlobal && centroUsuario) || (permisosEnValidacion && centroUsuario);
  
  const puedeVerGraficasCompletas = esAdmin || esFarmacia || permisos?.isSuperuser;
  const puedeVerGraficasBasicas = puedeVerGraficasCompletas || esVista || esCentro;
  
  // Permisos granulares adicionales
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
      // ISS-FIX: Agregar refresh=true para forzar recarga sin caché cuando el usuario hace click en actualizar
      const params = { 
        ...(centroEfectivo ? { centro: centroEfectivo } : {}),
        ...(isRefresh ? { refresh: 'true' } : {})
      };

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
    // ISS-FIX: También esperar a que terminen de validarse los permisos
    if (!cargandoPermisos && !permisosEnValidacion && esCentroRestringido && centroUsuario) {
      setSelectedCentro(centroUsuario);
    }
  }, [cargandoPermisos, permisosEnValidacion, esCentroRestringido, centroUsuario]);

  // Cargar datos
  useEffect(() => {
    // Esperar a que termine la carga de permisos
    if (cargandoPermisos) return;
    
    // ISS-FIX: También esperar si los permisos están en validación (aún no completos)
    // Esto evita que el Dashboard se "salte" la carga cuando los permisos están validándose
    if (permisos?._isValidating) return;
    
    // Solo bloquear si permisos están completos Y no tiene acceso
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
  }, [loadDashboard, selectedCentro, permisos?.verDashboard, permisos?._isValidating, cargandoPermisos]);

  // Escuchar evento de limpieza de inventario para refrescar Dashboard
  useEffect(() => {
    const handleInventarioLimpiado = (event) => {
      console.log('🧹 Inventario limpiado, refrescando Dashboard...', event.detail);
      // Forzar refresh con parámetro true para invalidar caché
      loadDashboard(selectedCentro, true);
    };
    
    window.addEventListener('inventarioLimpiado', handleInventarioLimpiado);
    
    return () => {
      window.removeEventListener('inventarioLimpiado', handleInventarioLimpiado);
    };
  }, [loadDashboard, selectedCentro]);

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

  // KPI Cards - Configuración optimizada
  const kpiCards = useMemo(() => [
    {
      title: 'Productos',
      value: kpis.total_productos || 0,
      subtext: 'Registrados en catálogo',
      icon: FaBox,
      colorType: 'primary',
      show: permisos?.verDashboard && permisos?.verProductos,
      onClick: () => permisos?.verProductos && navigate('/productos'),
    },
    {
      title: 'Inventario Total',
      value: kpis.stock_total || 0,
      subtext: selectedCentro ? `En ${centroNombre || 'centro'}` : 'Unidades en inventario',
      icon: FaCubes,
      colorType: 'success',
      show: permisos?.verDashboard,
      onClick: () => permisos?.verLotes && navigate('/lotes'),
    },
    {
      title: 'Lotes Activos',
      value: kpis.lotes_activos || 0,
      subtext: 'Con existencias disponibles',
      icon: FaWarehouse,
      colorType: 'info',
      show: permisos?.verDashboard && permisos?.verLotes,
      onClick: () => permisos?.verLotes && navigate('/lotes'),
    },
    {
      title: 'Movimientos',
      value: kpis.movimientos_mes || 0,
      subtext: `En ${new Date().toLocaleDateString('es-MX', { month: 'long', year: 'numeric' })}`,
      icon: FaExchangeAlt,
      colorType: 'warning',
      show: permisos?.verDashboard && permisos?.verMovimientos,
      onClick: () => permisos?.verMovimientos && navigate('/movimientos'),
    },
  ], [kpis, permisos, navigate, selectedCentro, centroNombre]);

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
    <div className="p-6 max-w-[1600px] mx-auto space-y-6 pb-12">
      {/* ========== HEADER ========== */}
      <header className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5">
        {/* Fila superior: Título y controles */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          {/* Título y badge */}
          <div className="flex items-center gap-3 min-w-0">
            <h1 
              className="text-2xl md:text-3xl font-black tracking-tight whitespace-nowrap"
              style={{ color: 'var(--color-primary, #9F2241)' }}
            >
              Panel de Control
            </h1>
            <span 
              className="px-3 py-1 rounded-full text-xs font-bold text-white shadow-sm flex-shrink-0"
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
          
          {/* Controles */}
          <div className="flex items-center gap-3 flex-shrink-0">
            {/* Selector de centro */}
            {puedeFiltrarPorCentro && (
              <div className="min-w-[200px] max-w-[300px]">
                <CentroSelector onCentroChange={handleCentroChange} selectedValue={selectedCentro} />
              </div>
            )}
            
            {/* Botón de refresh */}
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className={`
                p-2.5 rounded-xl bg-gray-50 border border-gray-200
                hover:bg-gray-100 hover:border-gray-300 transition-all flex-shrink-0
                ${refreshing ? 'opacity-50 cursor-not-allowed' : ''}
              `}
              title="Actualizar datos"
            >
              <FaSync className={`text-gray-500 ${refreshing ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
        
        {/* Fila inferior: Subtítulo y fecha */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mt-3 pt-3 border-t border-gray-100">
          <p className="text-sm text-gray-500 flex items-center gap-2">
            {selectedCentro ? (
              <>
                <FaBuilding className="text-xs flex-shrink-0" />
                <span className="truncate">Datos de: <strong className="text-gray-700">{centroNombre || 'Centro seleccionado'}</strong></span>
              </>
            ) : esCentroRestringido && nombreCentroUsuario ? (
              <>
                <FaBuilding className="text-xs flex-shrink-0" />
                <span className="truncate">Centro: <strong className="text-gray-700">{nombreCentroUsuario}</strong></span>
              </>
            ) : (
              <span>Resumen general del sistema de inventario</span>
            )}
          </p>
          
          {/* Fecha compacta */}
          <div className="flex items-center gap-2 text-sm text-gray-500 flex-shrink-0">
            <FaCalendarAlt className="text-xs" style={{ color: 'var(--color-primary, #9F2241)' }} />
            <span className="capitalize">
              {new Date().toLocaleDateString('es-MX', {
                weekday: 'short',
                day: 'numeric',
                month: 'short',
                year: 'numeric',
              })}
            </span>
          </div>
        </div>
      </header>

      {/* Indicador de filtro activo para admins */}
      {selectedCentro && puedeFiltrarPorCentro && (
        <div 
          className="flex items-center justify-between gap-3 px-4 py-2.5 rounded-xl border text-sm"
          style={{ 
            backgroundColor: 'var(--color-warning-light, rgba(245, 158, 11, 0.05))',
            borderColor: 'var(--color-warning-light, rgba(245, 158, 11, 0.2))'
          }}
        >
          <span className="flex items-center gap-2" style={{ color: 'var(--color-warning-hover, #D97706)' }}>
            <FaBuilding className="flex-shrink-0" />
            <span className="truncate">Filtrado por: <strong>{centroNombre}</strong></span>
          </span>
          <button 
            onClick={() => handleCentroChange(null, '')}
            className="font-medium underline hover:no-underline whitespace-nowrap"
            style={{ color: 'var(--color-warning-hover, #D97706)' }}
          >
            Ver todos
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
              <ResponsiveContainer width="100%" height={Math.max(320, graficas.stock_por_centro.length * 80)}>
                <BarChart 
                  data={graficas.stock_por_centro} 
                  layout="vertical"
                  margin={{ top: 5, right: 80, left: 20, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" horizontal={false} />
                  <XAxis 
                    type="number" 
                    tick={{ fill: '#6B7280', fontSize: 12 }}
                    tickFormatter={(value) => value.toLocaleString('es-MX')}
                  />
                  <YAxis 
                    dataKey="centro" 
                    type="category" 
                    width={180}
                    tick={({ x, y, payload }) => (
                      <g transform={`translate(${x},${y})`}>
                        <title>{payload.value}</title>
                        <text 
                          x={-5} 
                          y={0} 
                          dy={4} 
                          textAnchor="end" 
                          fill="#374151" 
                          fontSize={12}
                          fontWeight={600}
                        >
                          {payload.value.length > 20 ? `${payload.value.slice(0, 17)}...` : payload.value}
                        </text>
                      </g>
                    )}
                  />
                  <Tooltip 
                    content={({ active, payload }) => {
                      if (!active || !payload?.length) return null;
                      const data = payload[0].payload;
                      return (
                        <div className="bg-white rounded-xl shadow-xl border border-gray-200 p-4 min-w-[250px]">
                          <p className="font-bold text-gray-800 mb-2 text-base leading-tight">
                            {data.centro}
                          </p>
                          <div className="flex items-center gap-2">
                            <span 
                              className="w-3 h-3 rounded-full" 
                              style={{ backgroundColor: 'var(--color-primary, #9F2241)' }}
                            />
                            <span className="text-gray-600 text-sm">Inventario:</span>
                            <span className="font-bold text-gray-900 text-lg">
                              {data.stock?.toLocaleString('es-MX')} uds
                            </span>
                          </div>
                        </div>
                      );
                    }}
                  />
                  <Bar 
                    dataKey="stock" 
                    name="Inventario"
                    radius={[0, 8, 8, 0]}
                    fill="var(--color-primary, #9F2241)"
                    label={({ x, y, width, value }) => (
                      <text
                        x={x + width + 8}
                        y={y + 16}
                        fill="#374151"
                        fontSize={12}
                        fontWeight={600}
                      >
                        {value?.toLocaleString('es-MX')} uds
                      </text>
                    )}
                  />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex flex-col items-center justify-center h-64 text-gray-400">
                <FaWarehouse className="text-4xl mb-3 opacity-50" />
                <p>No hay datos de inventario por centro</p>
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
                      content={({ active, payload }) => {
                        if (!active || !payload?.length) return null;
                        const data = payload[0].payload;
                        const color = COLORES_ESTADO_REQUISICION[data.estado] || COLORES_ESTADO_REQUISICION.DEFAULT;
                        return (
                          <div className="bg-white rounded-xl shadow-xl border border-gray-200 p-4 min-w-[180px]">
                            <div className="flex items-center gap-2 mb-2">
                              <span 
                                className="w-3 h-3 rounded-full flex-shrink-0" 
                                style={{ backgroundColor: color }}
                              />
                              <span className="font-bold text-gray-800 text-sm">
                                {formatearEstado(data.estado)}
                              </span>
                            </div>
                            <p className="text-2xl font-black text-gray-900">
                              {data.cantidad} <span className="text-sm font-normal text-gray-500">requisiciones</span>
                            </p>
                          </div>
                        );
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
