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
  FaMoneyBillWave,
  FaChartBar,
  FaTrophy,
  FaHospital,
  FaUserTie,
  FaHandHoldingHeart,
  FaExclamationCircle,
} from 'react-icons/fa';
import { 
  AreaChart, Area, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  Legend, BarChart, Bar, LineChart, Line
} from 'recharts';
import { usePermissions } from '../hooks/usePermissions';
import PageHeader from '../components/PageHeader';
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
 * Card de KPI Profesional
 * - Sparkline mini-chart integrado
 * - Doble métrica (principal + secundaria)
 * - Colores Pantone institucionales (Guinda + Dorado)
 * - Glassmorphism + border animado
 * - 3D tilt en hover
 * - Counter con spring physics
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
  loading = false,
  sparklineData,
  secondaryLabel,
  secondaryValue,
  prefix = '',
  suffix = '',
}) => {
  const cardRef = useRef(null);
  const [isVisible, setIsVisible] = useState(false);
  const [displayValue, setDisplayValue] = useState(0);
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  
  // Paleta institucional Pantone
  const colorConfig = {
    primary: { // Pantone 7420C Guinda
      solid: '#932043',
      accent: '#C9A876', // Pantone 467C Dorado
      glow: 'rgba(147, 32, 67, 0.25)',
      text: '#932043',
      light: 'rgba(147, 32, 67, 0.08)',
      lightHover: 'rgba(147, 32, 67, 0.14)',
      gradient: 'linear-gradient(135deg, #932043, #632842)',
      sparkStroke: '#932043',
      sparkFill: 'rgba(147, 32, 67, 0.12)',
    },
    success: { // Verde institucional
      solid: '#0F766E',
      accent: '#5EEAD4',
      glow: 'rgba(15, 118, 110, 0.25)',
      text: '#0F766E',
      light: 'rgba(15, 118, 110, 0.08)',
      lightHover: 'rgba(15, 118, 110, 0.14)',
      gradient: 'linear-gradient(135deg, #0F766E, #134E4A)',
      sparkStroke: '#0F766E',
      sparkFill: 'rgba(15, 118, 110, 0.12)',
    },
    info: { // Azul institucional
      solid: '#1E40AF',
      accent: '#60A5FA',
      glow: 'rgba(30, 64, 175, 0.25)',
      text: '#1E40AF',
      light: 'rgba(30, 64, 175, 0.08)',
      lightHover: 'rgba(30, 64, 175, 0.14)',
      gradient: 'linear-gradient(135deg, #1E40AF, #1E3A5F)',
      sparkStroke: '#1E40AF',
      sparkFill: 'rgba(30, 64, 175, 0.12)',
    },
    warning: { // Pantone 4635C Terracota
      solid: '#9F663E',
      accent: '#D2B595', // Pantone 468C Beige
      glow: 'rgba(159, 102, 62, 0.25)',
      text: '#9F663E',
      light: 'rgba(159, 102, 62, 0.08)',
      lightHover: 'rgba(159, 102, 62, 0.14)',
      gradient: 'linear-gradient(135deg, #9F663E, #7A4E2F)',
      sparkStroke: '#9F663E',
      sparkFill: 'rgba(159, 102, 62, 0.12)',
    },
    gold: { // Pantone 7504C Dorado institucional
      solid: '#9B7E4C',
      accent: '#C9A876',
      glow: 'rgba(155, 126, 76, 0.25)',
      text: '#9B7E4C',
      light: 'rgba(155, 126, 76, 0.08)',
      lightHover: 'rgba(155, 126, 76, 0.14)',
      gradient: 'linear-gradient(135deg, #9B7E4C, #7A6339)',
      sparkStroke: '#9B7E4C',
      sparkFill: 'rgba(155, 126, 76, 0.12)',
    },
    danger: { // Rojo alertas
      solid: '#DC2626',
      accent: '#FCA5A5',
      glow: 'rgba(220, 38, 38, 0.25)',
      text: '#DC2626',
      light: 'rgba(220, 38, 38, 0.08)',
      lightHover: 'rgba(220, 38, 38, 0.14)',
      gradient: 'linear-gradient(135deg, #DC2626, #991B1B)',
      sparkStroke: '#DC2626',
      sparkFill: 'rgba(220, 38, 38, 0.12)',
    },
  };
  
  const colors = colorConfig[colorType] || colorConfig.primary;
  
  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(true), delay);
    return () => clearTimeout(timer);
  }, [delay]);
  
  // Counter con spring physics
  useEffect(() => {
    if (!isVisible || loading) return;
    const duration = 1400;
    const frameDuration = 1000 / 60;
    const totalFrames = Math.round(duration / frameDuration);
    let frame = 0;
    const counter = setInterval(() => {
      frame++;
      const progress = frame / totalFrames;
      const spring = 1 - Math.pow(Math.E, -5.5 * progress) * Math.cos(progress * Math.PI * 1.8);
      setDisplayValue(Math.round(Math.min(1, Math.max(0, spring)) * value));
      if (frame >= totalFrames) { clearInterval(counter); setDisplayValue(value); }
    }, frameDuration);
    return () => clearInterval(counter);
  }, [value, isVisible, loading]);
  
  // 3D tilt
  const handleMouseMove = useCallback((e) => {
    if (!cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;
    setTilt({ x: (y - 0.5) * -8, y: (x - 0.5) * 8 });
  }, []);
  const handleMouseLeave = useCallback(() => setTilt({ x: 0, y: 0 }), []);
  
  // Sparkline SVG path
  const sparklinePath = useMemo(() => {
    if (!sparklineData || sparklineData.length < 2) return null;
    const W = 120, H = 36, pad = 2;
    const vals = sparklineData.map(d => (typeof d === 'number' ? d : d.value || 0));
    const max = Math.max(...vals, 1);
    const min = Math.min(...vals, 0);
    const range = max - min || 1;
    const points = vals.map((v, i) => ({
      x: pad + (i / (vals.length - 1)) * (W - pad * 2),
      y: pad + (1 - (v - min) / range) * (H - pad * 2),
    }));
    const line = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
    const area = `${line} L${points[points.length - 1].x.toFixed(1)},${H} L${points[0].x.toFixed(1)},${H} Z`;
    return { line, area, W, H };
  }, [sparklineData]);

  return (
    <div 
      className="kpi-card-wrapper"
      style={{ 
        perspective: '800px',
        opacity: isVisible ? 1 : 0,
        transform: isVisible ? 'translateY(0)' : 'translateY(24px)',
        transition: `all 0.6s cubic-bezier(0.16, 1, 0.3, 1) ${delay}ms`,
      }}
    >
      <div 
        className="kpi-glow-border"
        style={{ '--kpi-color-1': colors.solid, '--kpi-color-2': colors.accent, '--kpi-glow': colors.glow }}
      >
        <div 
          ref={cardRef}
          onClick={onClick}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
          className={`kpi-card-modern ${onClick ? 'cursor-pointer' : ''}`}
          style={{
            transform: `rotateX(${tilt.x}deg) rotateY(${tilt.y}deg)`,
            transition: tilt.x === 0 && tilt.y === 0 
              ? 'transform 0.5s cubic-bezier(0.16, 1, 0.3, 1)' 
              : 'transform 0.08s ease-out',
          }}
        >
          {/* Header institucional con fondo coloreado */}
          <div 
            className="relative z-10 px-3 sm:px-4 pt-2.5 pb-2"
            style={{ 
              background: `linear-gradient(135deg, ${colors.light}, ${colors.lightHover})`,
              borderBottom: `1px solid ${colors.solid}12`
            }}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2">
                <div 
                  className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 shadow-sm"
                  style={{ background: colors.gradient }}
                >
                  <Icon className="text-white text-xs" />
                </div>
                <div className="min-w-0">
                  <p className="text-[10px] font-bold uppercase tracking-[0.1em]" style={{ color: colors.text }}>
                    {title}
                  </p>
                  <p className="text-[9px] text-gray-400 truncate">{subtext}</p>
                </div>
              </div>
              {trend && (
                <div className={`
                  flex items-center gap-0.5 px-1.5 py-0.5 rounded-md text-[9px] font-bold flex-shrink-0
                  ${trend === 'up' ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-500'}
                `}>
                  {trend === 'up' ? <FaArrowUp size={7} /> : <FaArrowDown size={7} />}
                  {trendValue}%
                </div>
              )}
            </div>
          </div>
          
          {/* Contenido principal */}
          <div className="relative z-10 px-3 sm:px-4 py-2.5">
            {/* Número principal */}
            <div className="mb-1">
              {loading ? (
                <div className="h-8 w-24 rounded skeleton-loader" />
              ) : (
                <div className="flex items-baseline gap-0.5">
                  {prefix && <span className="text-base font-bold" style={{ color: colors.text }}>{prefix}</span>}
                  <span className="text-2xl sm:text-3xl font-black tracking-tight tabular-nums" style={{ color: '#111827' }}>
                    {displayValue.toLocaleString('es-MX')}
                  </span>
                  {suffix && <span className="text-xs font-medium text-gray-400 ml-0.5">{suffix}</span>}
                </div>
              )}
            </div>
            
            {/* Métrica secundaria */}
            {secondaryLabel && (
              <div className="flex items-center gap-1.5 mb-1">
                <span className="text-[9px] text-gray-400">{secondaryLabel}</span>
                <span className="text-[11px] font-bold" style={{ color: colors.text }}>{secondaryValue}</span>
              </div>
            )}
            
            {/* Sparkline mini-chart */}
            {sparklinePath && (
              <div className="mt-1 kpi-sparkline-wrap">
                <svg 
                  viewBox={`0 0 ${sparklinePath.W} ${sparklinePath.H}`} 
                  className="w-full h-8 sm:h-9"
                  preserveAspectRatio="none"
                >
                  <defs>
                    <linearGradient id={`spark-fill-${colorType}-${delay}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={colors.sparkStroke} stopOpacity="0.2" />
                      <stop offset="100%" stopColor={colors.sparkStroke} stopOpacity="0.02" />
                    </linearGradient>
                  </defs>
                  <path d={sparklinePath.area} fill={`url(#spark-fill-${colorType}-${delay})`} />
                  <path d={sparklinePath.line} fill="none" stroke={colors.sparkStroke} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
            )}
            
            {/* Footer: Action link */}
            {onClick && (
              <div className="flex items-center justify-end mt-1.5 pt-1.5 border-t" style={{ borderColor: 'rgba(0,0,0,0.04)' }}>
                <div 
                  className="kpi-action-link flex items-center gap-1 text-[9px] font-semibold px-2 py-0.5 rounded-md"
                  style={{ color: colors.text, backgroundColor: colors.light }}
                >
                  <span>Ver detalle</span>
                  <FaArrowRight size={7} className="kpi-action-arrow" />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
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
    <>
      {/* Overlay claro para modo expandido */}
      {isExpanded && (
        <div 
          className="fixed inset-0 z-40 backdrop-blur-sm"
          style={{ backgroundColor: 'rgba(255, 255, 255, 0.85)' }}
          onClick={() => setIsExpanded(false)}
        />
      )}
      <div className={`
        bg-white rounded-xl shadow-sm border border-gray-100/80 overflow-hidden
        transition-all duration-300 hover:shadow-lg hover:border-gray-200/80
        ${isExpanded ? 'fixed inset-6 z-50 shadow-2xl overflow-y-auto' : ''}
        ${className}
      `}>
        {/* Header */}
        <div 
          className="px-4 py-2.5 border-b border-gray-100/60 flex items-center justify-between"
          style={{ 
            background: 'linear-gradient(to right, var(--color-primary-light, rgba(159, 34, 65, 0.03)), transparent)'
          }}
        >
          <div className="flex items-center gap-2.5">
            <div 
              className="w-7 h-7 rounded-lg flex items-center justify-center"
              style={{ backgroundColor: 'var(--color-primary-light, rgba(159, 34, 65, 0.08))' }}
            >
              <Icon className="text-xs" style={{ color: 'var(--color-primary, #9F2241)' }} />
            </div>
            <h3 className="text-sm font-bold text-gray-700">{title}</h3>
          </div>
          <div className="flex items-center gap-1.5">
            {action}
            {expandable && (
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="p-1.5 rounded-md hover:bg-gray-100 transition-colors text-gray-400 hover:text-gray-600"
                title={isExpanded ? 'Minimizar' : 'Pantalla completa'}
              >
                {isExpanded ? <FaCompress size={11} /> : <FaExpand size={11} />}
              </button>
            )}
          </div>
        </div>
        
        {/* Contenido */}
        <div className={`p-4 ${isExpanded ? 'h-[calc(100%-56px)] overflow-y-auto' : ''}`}>
          {children}
        </div>
      </div>
    </>
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
 * Mini card de acceso rápido - Usa CSS variables del tema
 */
const QuickAccessCard = ({ icon: Icon, title, subtitle, onClick, colorVar }) => (
  <button
    onClick={onClick}
    className="
      flex items-center gap-3 p-3 rounded-lg bg-white border border-gray-100
      shadow-sm hover:shadow-md transition-all duration-200
      hover:border-gray-200 text-left w-full group
    "
  >
    <div 
      className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
      style={{ backgroundColor: `var(${colorVar}-light, rgba(159, 34, 65, 0.08))` }}
    >
      <Icon className="text-sm" style={{ color: `var(${colorVar}, #9F2241)` }} />
    </div>
    <div className="flex-1 min-w-0">
      <p className="text-sm font-semibold text-gray-800">{title}</p>
      <p className="text-[11px] text-gray-400 truncate">{subtitle}</p>
    </div>
    <FaArrowRight className="text-gray-300 group-hover:text-gray-400 transition-colors text-xs flex-shrink-0" />
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
    consumo_por_producto: [],
    stock_por_centro: [],
    stock_por_producto: [],
    requisiciones_por_estado: [],
    requisiciones_por_mes: [],
    requisiciones_resumen: null,
  });
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  // Analytics avanzados
  const [analytics, setAnalytics] = useState(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  // ISS-FIX: Default a 'central' (Farmacia Central) para usuarios con acceso global
  const [selectedCentro, setSelectedCentro] = useState(esCentroRestringido ? centroUsuario : 'central');
  const [centroNombre, setCentroNombre] = useState(esCentroRestringido ? '' : 'Farmacia Central');
  const [lastUpdate, setLastUpdate] = useState(null);
  
  const isMountedRef = useRef(true);
  const centroChangedRef = useRef(false);

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
      // ISS-FIX: 'todos' significa global (sin filtro de centro), 'central' significa Farmacia Central
      const params = { 
        ...(centroEfectivo && centroEfectivo !== 'todos' ? { centro: centroEfectivo } : {}),
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
          consumo_por_producto: graficasResponse.data.consumo_por_producto || [],
          stock_por_centro: graficasResponse.data.stock_por_centro || [],
          stock_por_producto: graficasResponse.data.stock_por_producto || [],
          requisiciones_por_estado: graficasResponse.data.requisiciones_por_estado || [],
          requisiciones_por_mes: graficasResponse.data.requisiciones_por_mes || [],
          requisiciones_resumen: graficasResponse.data.requisiciones_resumen || null,
        });
      } catch (graficasError) {
        console.warn('Error al cargar gráficas:', graficasError);
        if (isMountedRef.current) {
          setGraficas({
            consumo_mensual: [],
            consumo_por_producto: [],
            stock_por_centro: [],
            stock_por_producto: [],
            requisiciones_por_estado: [],
            requisiciones_por_mes: [],
            requisiciones_resumen: null,
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
      setGraficas({ consumo_mensual: [], consumo_por_producto: [], stock_por_centro: [], stock_por_producto: [], requisiciones_por_estado: [], requisiciones_por_mes: [], requisiciones_resumen: null });
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
        setRefreshing(false);
      }
    }
  }, [esVista, esCentroRestringido, centroUsuario]);

  // Cargar analytics avanzados (solo para Farmacia y Admin)
  const loadAnalytics = useCallback(async (centroId = null) => {
    if (!puedeVerGraficasCompletas) return;
    
    try {
      setAnalyticsLoading(true);
      const centroEfectivo = esCentroRestringido ? centroUsuario : centroId;
      const params = centroEfectivo && centroEfectivo !== 'todos' ? { centro: centroEfectivo } : {};
      
      const response = await dashboardAPI.getAnalytics(params);
      if (isMountedRef.current) {
        setAnalytics(response.data);
      }
    } catch (err) {
      console.warn('Error al cargar analytics:', err);
      if (isMountedRef.current) {
        setAnalytics(null);
      }
    } finally {
      if (isMountedRef.current) {
        setAnalyticsLoading(false);
      }
    }
  }, [puedeVerGraficasCompletas, esCentroRestringido, centroUsuario]);

  // Sincronizar centro
  useEffect(() => {
    // ISS-FIX: También esperar a que terminen de validarse los permisos
    if (!cargandoPermisos && !permisosEnValidacion && esCentroRestringido && centroUsuario) {
      setSelectedCentro(centroUsuario);
    }
    // ISS-FIX: Garantizar que usuarios con acceso global siempre tengan un valor válido
    if (!cargandoPermisos && !permisosEnValidacion && !esCentroRestringido && !selectedCentro) {
      setSelectedCentro('central');
      setCentroNombre('Farmacia Central');
    }
  }, [cargandoPermisos, permisosEnValidacion, esCentroRestringido, centroUsuario, selectedCentro]);

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

  // Cargar analytics avanzados
  useEffect(() => {
    if (cargandoPermisos || permisos?._isValidating) return;
    if (!permisos?.verDashboard || !puedeVerGraficasCompletas) return;
    if (!hasAccessToken()) return;
    
    loadAnalytics(selectedCentro);
  }, [loadAnalytics, selectedCentro, permisos?.verDashboard, permisos?._isValidating, cargandoPermisos, puedeVerGraficasCompletas]);

  // Cuando cambia el centro seleccionado por el usuario, forzar refresh
  // para obtener datos frescos del backend (sin caché)
  useEffect(() => {
    if (centroChangedRef.current) {
      centroChangedRef.current = false;
      // El effect principal ya cargó datos, pero necesitamos forzar refresh
      loadDashboard(selectedCentro, true);
    }
  }, [selectedCentro]); // eslint-disable-line react-hooks/exhaustive-deps

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

  // Auto-refresh cada 2 minutos para mantener datos sincronizados
  useEffect(() => {
    if (!permisos?.verDashboard || !hasAccessToken()) return;
    
    const interval = setInterval(() => {
      if (isMountedRef.current && document.visibilityState === 'visible') {
        loadDashboard(selectedCentro, true);
      }
    }, 120_000); // 2 minutos
    
    return () => clearInterval(interval);
  }, [loadDashboard, selectedCentro, permisos?.verDashboard]);

  // Refrescar datos cuando el usuario regresa a la pestaña
  useEffect(() => {
    const handleVisibility = () => {
      if (document.visibilityState === 'visible' && isMountedRef.current && permisos?.verDashboard) {
        // Solo refrescar si han pasado al menos 30 segundos desde la última actualización
        if (lastUpdate && (Date.now() - lastUpdate.getTime()) > 30_000) {
          loadDashboard(selectedCentro, true);
        }
      }
    };
    
    document.addEventListener('visibilitychange', handleVisibility);
    return () => document.removeEventListener('visibilitychange', handleVisibility);
  }, [loadDashboard, selectedCentro, permisos?.verDashboard, lastUpdate]);

  const handleCentroChange = (centroId, nombreCentro = '') => {
    if (esCentroRestringido) return;
    centroChangedRef.current = true;
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

  // KPI Cards - Con sparklines y métricas enriquecidas
  const consumoSparkline = useMemo(() => {
    if (!graficas.consumo_mensual || graficas.consumo_mensual.length < 2) return null;
    return graficas.consumo_mensual.map(m => m.salidas || 0);
  }, [graficas.consumo_mensual]);

  const entradasSparkline = useMemo(() => {
    if (!graficas.consumo_mensual || graficas.consumo_mensual.length < 2) return null;
    return graficas.consumo_mensual.map(m => m.entradas || 0);
  }, [graficas.consumo_mensual]);

  const stockSparkline = useMemo(() => {
    if (!graficas.stock_por_centro || graficas.stock_por_centro.length < 2) return null;
    return graficas.stock_por_centro.map(c => c.stock || 0);
  }, [graficas.stock_por_centro]);

  // Tendencias calculadas desde consumo mensual (mes actual vs anterior)
  const trends = useMemo(() => {
    const cm = graficas.consumo_mensual;
    if (!cm || cm.length < 2) return {};
    const curr = cm[cm.length - 1];
    const prev = cm[cm.length - 2];
    const calcTrend = (c, p) => {
      if (!p || p === 0) return null;
      const pct = Math.round(((c - p) / p) * 100);
      return { dir: pct >= 0 ? 'up' : 'down', val: Math.abs(pct) };
    };
    return {
      entradas: calcTrend(curr?.entradas || 0, prev?.entradas),
      salidas: calcTrend(curr?.salidas || 0, prev?.salidas),
      movimientos: calcTrend(
        (curr?.entradas || 0) + (curr?.salidas || 0),
        (prev?.entradas || 0) + (prev?.salidas || 0)
      ),
    };
  }, [graficas.consumo_mensual]);

  const kpiCards = useMemo(() => [
    {
      title: 'Productos',
      value: kpis.total_productos || 0,
      subtext: selectedCentro && selectedCentro !== 'central' ? `En ${centroNombre || 'centro'}` : 'Catálogo activo',
      icon: FaBox,
      colorType: 'primary',
      show: permisos?.verDashboard && permisos?.verProductos,
      onClick: () => permisos?.verProductos && navigate('/productos'),
      sparklineData: entradasSparkline,
      trend: trends.entradas?.dir,
      trendValue: trends.entradas?.val,
      secondaryLabel: 'Lotes:',
      secondaryValue: (kpis.lotes_activos || 0).toLocaleString('es-MX'),
    },
    {
      title: 'Inventario Total',
      value: kpis.stock_total || 0,
      subtext: selectedCentro ? `En ${centroNombre || 'centro'}` : 'Unidades en existencia',
      icon: FaCubes,
      colorType: 'success',
      show: permisos?.verDashboard,
      onClick: () => permisos?.verLotes && navigate('/lotes'),
      sparklineData: stockSparkline,
      trend: trends.entradas?.dir === 'up' ? 'up' : trends.salidas?.dir === 'up' ? 'down' : null,
      trendValue: trends.entradas?.val || trends.salidas?.val,
      suffix: 'uds',
    },
    {
      title: 'Lotes Activos',
      value: kpis.lotes_activos || 0,
      subtext: 'Con existencias disponibles',
      icon: FaWarehouse,
      colorType: 'info',
      show: permisos?.verDashboard && permisos?.verLotes,
      onClick: () => permisos?.verLotes && navigate('/lotes'),
      secondaryLabel: analytics?.caducidades?.vencen_30_dias > 0 ? '⚠ Por vencer (30d):' : null,
      secondaryValue: analytics?.caducidades?.vencen_30_dias > 0 ? String(analytics.caducidades.vencen_30_dias) : null,
    },
    {
      title: 'Movimientos',
      value: kpis.movimientos_mes || 0,
      subtext: `${(() => { const m = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']; return m[new Date().getMonth()]; })()} ${new Date().getFullYear()}`,
      icon: FaExchangeAlt,
      colorType: 'warning',
      show: permisos?.verDashboard && permisos?.verMovimientos,
      onClick: () => permisos?.verMovimientos && navigate('/movimientos'),
      sparklineData: consumoSparkline,
      trend: trends.movimientos?.dir,
      trendValue: trends.movimientos?.val,
    },
  ], [kpis, permisos, navigate, selectedCentro, centroNombre, consumoSparkline, entradasSparkline, stockSparkline, analytics, trends]);

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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {[1,2,3,4].map(i => <SkeletonCard key={i} />)}
        </div>
        
        {/* Chart skeletons */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="bg-white rounded-xl p-4 h-80 animate-pulse">
            <div className="h-5 w-40 bg-gray-200 rounded mb-3" />
            <div className="h-60 bg-gray-100 rounded-lg" />
          </div>
          <div className="bg-white rounded-xl p-4 h-80 animate-pulse">
            <div className="h-5 w-40 bg-gray-200 rounded mb-3" />
            <div className="h-60 bg-gray-100 rounded-lg" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="px-4 sm:px-6 py-4 max-w-[1600px] mx-auto space-y-4 pb-8">
      {/* ========== HEADER ========== */}
      <PageHeader
        icon={FaChartLine}
        title="Panel de Control"
        subtitle={
          selectedCentro
            ? `Datos de: ${centroNombre || 'Centro seleccionado'}`
            : esCentroRestringido && nombreCentroUsuario
            ? `Centro: ${nombreCentroUsuario}`
            : 'Resumen general del sistema de inventario'
        }
        badge={
          <span 
            className="px-2 py-0.5 rounded-full text-[10px] font-bold text-white flex-shrink-0"
            style={{ 
              background: rolPrincipal === 'ADMIN' 
                ? 'linear-gradient(135deg, #9F2241, #6B1839)'
                : rolPrincipal === 'FARMACIA'
                ? 'linear-gradient(135deg, #10B981, #059669)'
                : rolPrincipal === 'CENTRO'
                ? 'linear-gradient(135deg, #3B82F6, #2563EB)'
                : 'linear-gradient(135deg, #6B7280, #4B5563)'
            }}
          >
            {getRolLabel()}
          </span>
        }
        actions={
          <div className="flex items-center gap-2 w-full md:w-auto">
            {puedeFiltrarPorCentro && (
              <div className="flex-1 md:flex-none md:min-w-[200px] md:max-w-[300px]">
                <CentroSelector onCentroChange={handleCentroChange} selectedValue={selectedCentro} />
              </div>
            )}
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className={`cc-btn cc-btn-secondary ${refreshing ? 'opacity-50 cursor-not-allowed' : ''}`}
              title="Actualizar datos"
            >
              <FaSync className={`text-xs ${refreshing ? 'animate-spin' : ''}`} />
            </button>
          </div>
        }
        filters={
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-1.5 text-xs text-gray-400">
              <FaCalendarAlt className="text-[10px]" style={{ color: 'var(--color-primary, #9F2241)' }} />
              <span>
                {(() => {
                  const d = new Date();
                  const dias = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];
                  const meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
                  return `${dias[d.getDay()]}, ${d.getDate()} de ${meses[d.getMonth()]} de ${d.getFullYear()}`;
                })()}
              </span>
            </div>
          </div>
        }
      />

      {/* Indicador de filtro activo - solo mostrar cuando NO es Farmacia Central (el default) */}
      {selectedCentro && selectedCentro !== 'central' && puedeFiltrarPorCentro && (
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
            onClick={() => handleCentroChange('central', 'Farmacia Central')}
            className="font-medium underline hover:no-underline whitespace-nowrap"
            style={{ color: 'var(--color-warning-hover, #D97706)' }}
          >
            Volver a Farmacia Central
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

      {/* ========== KPI CARDS - Dashboard Profesional ========== */}
      <section className="kpi-section-wrapper rounded-xl sm:rounded-2xl p-3 sm:p-4">
        <div className="flex items-center gap-2 mb-3 sm:mb-3">
          <div className="kpi-section-dot" />
          <h2 
            className="text-[10px] sm:text-[11px] font-extrabold uppercase tracking-[0.15em]"
            style={{ color: 'var(--color-primary, #932043)' }}
          >
            Indicadores principales
          </h2>
          <div className="h-px flex-1 bg-gradient-to-r from-gray-200 to-transparent" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
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

        {/* Fila de Alertas del Sistema - Estilo referencia */}
        {puedeVerGraficasCompletas && analytics && (
          <>
            <div className="flex items-center gap-2 mt-4 sm:mt-5 mb-3">
              <div className="kpi-section-dot" style={{ background: 'linear-gradient(135deg, #9B7E4C, #C9A876)' }} />
              <h2 
                className="text-[10px] sm:text-[11px] font-extrabold uppercase tracking-[0.15em]"
                style={{ color: '#9B7E4C' }}
              >
                Alertas del sistema
              </h2>
              <div className="h-px flex-1 bg-gradient-to-r from-gray-200 to-transparent" />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
              <KPICard
                title="Alertas de Inventario"
                value={(analytics.caducidades?.vencidos || 0) + (analytics.caducidades?.vencen_30_dias || 0) + (analytics.caducidades?.vencen_15_dias || 0)}
                subtext="Notificaciones activas"
                icon={FaBox}
                colorType="danger"
                delay={0}
                secondaryLabel="Preventivas:"
                secondaryValue={String(analytics.caducidades?.vencen_90_dias || 0)}
              />
              <KPICard
                title="Alertas de Lotes"
                value={(analytics.caducidades?.vencen_15_dias || 0) + (analytics.caducidades?.vencen_30_dias || 0)}
                subtext="Lotes cercanos a vencer"
                icon={FaWarehouse}
                colorType="warning"
                delay={50}
                secondaryLabel="En 15d:"
                secondaryValue={String(analytics.caducidades?.vencen_15_dias || 0)}
              />
              <KPICard
                title="Alertas de Caducidad"
                value={analytics.caducidades?.vencidos || 0}
                subtext="Productos vencidos o próximos"
                icon={FaExclamationTriangle}
                colorType="danger"
                delay={100}
                secondaryLabel="Vencen 30d:"
                secondaryValue={String(analytics.caducidades?.vencen_30_dias || 0)}
              />
              <KPICard
                title="Alertas de Donaciones"
                value={analytics.donaciones?.donaciones_mes || 0}
                subtext="Donaciones recibidas este mes"
                icon={FaHandHoldingHeart}
                colorType="info"
                delay={150}
                secondaryLabel="Total:"
                secondaryValue={String(analytics.donaciones?.total_donaciones || 0)}
              />
            </div>
          </>
        )}
      </section>

      {/* ========== GRÁFICAS PRINCIPALES ========== */}
      {puedeVerGraficasBasicas && (
        <section className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <ChartCard 
            title="Consumo Mensual (Últimos 6 meses)" 
            icon={FaChartLine} 
            expandable
            action={
              <div className="flex items-center gap-2">
                {(() => {
                  const totalE = graficas.consumo_mensual.reduce((s, m) => s + (m.entradas || 0), 0);
                  const totalS = graficas.consumo_mensual.reduce((s, m) => s + (m.salidas || 0), 0);
                  return (
                    <>
                      <span className="text-[10px] font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-md">↓ {totalE.toLocaleString('es-MX')}</span>
                      <span className="text-[10px] font-bold text-red-500 bg-red-50 px-2 py-0.5 rounded-md">↑ {totalS.toLocaleString('es-MX')}</span>
                    </>
                  );
                })()}
              </div>
            }
          >
            {graficas.consumo_mensual.length > 0 ? (
              <>
                {/* Resumen compacto del período */}
                {(() => {
                  const totalEntradas = graficas.consumo_mensual.reduce((s, m) => s + (m.entradas || 0), 0);
                  const totalSalidas = graficas.consumo_mensual.reduce((s, m) => s + (m.salidas || 0), 0);
                  const balance = totalEntradas - totalSalidas;
                  const mesActual = graficas.consumo_mensual[graficas.consumo_mensual.length - 1];
                  const mesAnterior = graficas.consumo_mensual[graficas.consumo_mensual.length - 2];
                  const tendencia = mesAnterior?.salidas ? (((mesActual?.salidas || 0) - mesAnterior.salidas) / mesAnterior.salidas * 100).toFixed(0) : 0;
                  return (
                    <div className="flex items-center gap-3 mb-3 flex-wrap">
                      <div className="dash-stat-mini dash-stat-success flex-1 min-w-[100px]">
                        <div className="flex items-center gap-1 mb-0.5">
                          <FaArrowDown className="text-emerald-500" size={9} />
                          <span className="text-[9px] font-bold text-emerald-600 uppercase tracking-wider">Entradas</span>
                        </div>
                        <p className="text-lg font-black text-emerald-700 tabular-nums">{totalEntradas.toLocaleString('es-MX')}</p>
                      </div>
                      <div className="dash-stat-mini dash-stat-danger flex-1 min-w-[100px]">
                        <div className="flex items-center gap-1 mb-0.5">
                          <FaArrowUp className="text-red-500" size={9} />
                          <span className="text-[9px] font-bold text-red-600 uppercase tracking-wider">Salidas</span>
                        </div>
                        <p className="text-lg font-black text-red-700 tabular-nums">{totalSalidas.toLocaleString('es-MX')}</p>
                      </div>
                      <div className={`dash-stat-mini ${balance >= 0 ? 'dash-stat-info' : 'dash-stat-warning'} flex-1 min-w-[100px]`}>
                        <div className="flex items-center gap-1 mb-0.5">
                          <FaChartBar className={balance >= 0 ? 'text-blue-500' : 'text-amber-500'} size={9} />
                          <span className={`text-[9px] font-bold uppercase tracking-wider ${balance >= 0 ? 'text-blue-600' : 'text-amber-600'}`}>Balance</span>
                        </div>
                        <p className={`text-lg font-black tabular-nums ${balance >= 0 ? 'text-blue-700' : 'text-amber-700'}`}>
                          {balance >= 0 ? '+' : ''}{balance.toLocaleString('es-MX')}
                        </p>
                      </div>
                    </div>
                  );
                })()}
                {/* Gráfica Multi-línea de consumo por producto */}
                {(() => {
                  const consumoProd = graficas.consumo_por_producto || [];
                  const PROD_COLORS = ['#932043', '#0EA5E9', '#10B981', '#F59E0B', '#8B5CF6'];
                  if (consumoProd.length > 0) {
                    const meses = graficas.consumo_mensual.map(m => m.mes);
                    const multiLineData = meses.map((mes, i) => {
                      const row = { mes };
                      consumoProd.forEach(p => { row[p.nombre] = p.data?.[i] || 0; });
                      return row;
                    });
                    return (
                      <>
                        <ResponsiveContainer width="100%" height={280} minWidth={0} minHeight={0}>
                          <LineChart data={multiLineData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" vertical={false} />
                            <XAxis dataKey="mes" tick={{ fill: '#9CA3AF', fontSize: 11, fontWeight: 500 }} axisLine={false} tickLine={false} />
                            <YAxis tick={{ fill: '#9CA3AF', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v) => v >= 1000 ? `${(v/1000).toFixed(0)}k` : v} />
                            <Tooltip content={<CustomTooltip />} />
                            {consumoProd.map((prod, idx) => (
                              <Line
                                key={prod.clave}
                                type="monotone"
                                dataKey={prod.nombre}
                                stroke={PROD_COLORS[idx % PROD_COLORS.length]}
                                strokeWidth={2.5}
                                dot={{ fill: PROD_COLORS[idx % PROD_COLORS.length], strokeWidth: 2, r: 3.5, stroke: '#fff' }}
                                activeDot={{ r: 6, stroke: '#fff', strokeWidth: 2, fill: PROD_COLORS[idx % PROD_COLORS.length] }}
                                name={prod.nombre}
                              />
                            ))}
                          </LineChart>
                        </ResponsiveContainer>
                        <div className="flex flex-wrap justify-center gap-3 mt-2">
                          {consumoProd.map((prod, idx) => (
                            <div key={prod.clave} className="flex items-center gap-1.5">
                              <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: PROD_COLORS[idx % PROD_COLORS.length] }} />
                              <span className="text-[10px] font-medium text-gray-500">{prod.nombre}</span>
                            </div>
                          ))}
                        </div>
                      </>
                    );
                  }
                  // Fallback: Entradas/Salidas AreaChart
                  return (
                    <ResponsiveContainer width="100%" height={280} minWidth={0} minHeight={0}>
                      <AreaChart data={graficas.consumo_mensual}>
                        <defs>
                          <linearGradient id="colorEntradas" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#10B981" stopOpacity={0.25}/>
                            <stop offset="95%" stopColor="#10B981" stopOpacity={0}/>
                          </linearGradient>
                          <linearGradient id="colorSalidas" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#EF4444" stopOpacity={0.25}/>
                            <stop offset="95%" stopColor="#EF4444" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" vertical={false} />
                        <XAxis dataKey="mes" tick={{ fill: '#9CA3AF', fontSize: 11, fontWeight: 500 }} axisLine={false} tickLine={false} />
                        <YAxis tick={{ fill: '#9CA3AF', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v) => v >= 1000 ? `${(v/1000).toFixed(0)}k` : v} />
                        <Tooltip content={<CustomTooltip />} />
                        <Legend iconType="circle" wrapperStyle={{ paddingTop: '12px', fontSize: '12px' }} />
                        <Area type="monotone" dataKey="entradas" stroke="#10B981" strokeWidth={2.5} fill="url(#colorEntradas)" name="Entradas" dot={{ fill: '#10B981', strokeWidth: 2, r: 3.5, stroke: '#fff' }} activeDot={{ r: 6, stroke: '#fff', strokeWidth: 2, fill: '#10B981' }} />
                        <Area type="monotone" dataKey="salidas" stroke="#EF4444" strokeWidth={2.5} fill="url(#colorSalidas)" name="Salidas" dot={{ fill: '#EF4444', strokeWidth: 2, r: 3.5, stroke: '#fff' }} activeDot={{ r: 6, stroke: '#fff', strokeWidth: 2, fill: '#EF4444' }} />
                      </AreaChart>
                    </ResponsiveContainer>
                  );
                })()}
              </>
            ) : (
              <div className="flex flex-col items-center justify-center h-64 text-gray-400">
                <FaChartLine className="text-4xl mb-3 opacity-50" />
                <p>No hay datos de consumo disponibles</p>
              </div>
            )}
          </ChartCard>

          {/* Stock por Centro / por Producto */}
          {(() => {
            const stockCentro = graficas.stock_por_centro || [];
            const stockProducto = graficas.stock_por_producto || [];
            const esCentroUnico = stockCentro.length <= 1 && stockProducto.length > 0;
            const chartTitle = esCentroUnico ? 'Inventario por Producto' : 'Inventario por Centro';
            const chartIcon = esCentroUnico ? FaCubes : FaWarehouse;
            const COLORS_BAR = ['#932043', '#0EA5E9', '#10B981', '#F59E0B', '#8B5CF6', '#EC4899', '#14B8A6', '#F97316', '#6366F1', '#EF4444'];

            const renderBarItems = (items, labelKey, idKey, canClick, onClickFn) => {
              const sorted = [...items].sort((a, b) => b.stock - a.stock);
              const maxStock = sorted[0]?.stock || 1;
              const totalStock = sorted.reduce((s, p) => s + p.stock, 0);
              return (
                <div>
                  {/* Resumen superior */}
                  <div className="grid grid-cols-3 gap-2 mb-3">
                    <div className="dash-stat-mini dash-stat-primary">
                      <span className="text-[9px] font-bold text-gray-500 uppercase tracking-wider">{esCentroUnico ? 'Productos' : 'Centros'}</span>
                      <p className="text-lg font-black text-gray-800 mt-0.5">{sorted.length}</p>
                    </div>
                    <div className="dash-stat-mini dash-stat-success">
                      <span className="text-[9px] font-bold text-gray-500 uppercase tracking-wider">Stock total</span>
                      <p className="text-lg font-black text-gray-800 mt-0.5">{totalStock.toLocaleString('es-MX')}</p>
                    </div>
                    <div className="dash-stat-mini dash-stat-info">
                      <span className="text-[9px] font-bold text-gray-500 uppercase tracking-wider">Promedio</span>
                      <p className="text-lg font-black text-gray-800 mt-0.5">{Math.round(totalStock / (sorted.length || 1)).toLocaleString('es-MX')}</p>
                    </div>
                  </div>
                  {/* Barras */}
                  <div className={`space-y-2.5 ${sorted.length > 6 ? 'max-h-[340px] overflow-y-auto pr-2 custom-scrollbar' : ''}`}>
                    {sorted.map((item, index) => {
                      const pct = Math.max((item.stock / maxStock) * 100, 2);
                      const pctTotal = ((item.stock / totalStock) * 100).toFixed(1);
                      const color = COLORS_BAR[index % COLORS_BAR.length];
                      return (
                        <div
                          key={item[idKey] || item[labelKey]}
                          className={`dash-bar-item group ${canClick ? 'cursor-pointer' : ''}`}
                          onClick={() => canClick && onClickFn?.(item.centro_id)}
                        >
                          <div className="flex items-center gap-2.5 mb-1.5">
                            <span className="dash-bar-rank" style={{ background: color }}>{index + 1}</span>
                            <span className="text-sm font-semibold text-gray-700 truncate flex-1 group-hover:text-gray-900 transition-colors" title={item[labelKey]}>
                              {item[labelKey]}
                            </span>
                            <span className="text-sm font-bold text-gray-900 tabular-nums whitespace-nowrap">
                              {item.stock.toLocaleString('es-MX')} <span className="text-gray-400 font-normal text-[10px]">uds</span>
                            </span>
                            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-md tabular-nums" style={{ color, backgroundColor: `${color}15` }}>
                              {pctTotal}%
                            </span>
                          </div>
                          <div className="w-full bg-gray-100 rounded-full h-2 overflow-hidden">
                            <div className="h-full rounded-full transition-all duration-700 ease-out" style={{ width: `${pct}%`, background: `linear-gradient(90deg, ${color}99, ${color})` }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            };

            const puedeNavegar = permisos?.verReportes;
            const irAReportesCentro = (centroId) => {
              if (puedeNavegar) navigate('/reportes', { state: { tipo: 'inventario', centro: centroId } });
            };

            return (
              <ChartCard 
                title={chartTitle} 
                icon={chartIcon} 
                expandable
                action={
                  puedeNavegar && !esCentroUnico ? (
                    <button
                      onClick={() => navigate('/reportes', { state: { tipo: 'inventario' } })}
                      className="text-xs px-3 py-1.5 rounded-lg font-medium transition-colors hover:bg-gray-100"
                      style={{ color: 'var(--color-primary, #9F2241)' }}
                    >
                      Ver todos →
                    </button>
                  ) : null
                }
              >
                {esCentroUnico ? (
                  renderBarItems(stockProducto, 'producto', 'producto_id', false)
                ) : stockCentro.length > 0 ? (
                  (() => {
                    const sorted = [...stockCentro].sort((a, b) => b.stock - a.stock);
                    const maxStock = sorted[0]?.stock || 1;
                    const totalStock = sorted.reduce((s, p) => s + p.stock, 0);
                    return (
                      <div>
                        <div className="grid grid-cols-3 gap-2 mb-4">
                          <div className="dash-stat-mini dash-stat-primary">
                            <span className="text-[9px] font-bold text-gray-500 uppercase tracking-wider">Centros</span>
                            <p className="text-lg font-black text-gray-800 mt-0.5">{sorted.length}</p>
                          </div>
                          <div className="dash-stat-mini dash-stat-success">
                            <span className="text-[9px] font-bold text-gray-500 uppercase tracking-wider">Stock total</span>
                            <p className="text-lg font-black text-gray-800 mt-0.5">{totalStock.toLocaleString('es-MX')}</p>
                          </div>
                          <div className="dash-stat-mini dash-stat-info">
                            <span className="text-[9px] font-bold text-gray-500 uppercase tracking-wider">Promedio</span>
                            <p className="text-lg font-black text-gray-800 mt-0.5">{Math.round(totalStock / (sorted.length || 1)).toLocaleString('es-MX')}</p>
                          </div>
                        </div>
                        <div className={`grid grid-cols-1 sm:grid-cols-2 gap-3 ${sorted.length > 4 ? 'max-h-[380px] overflow-y-auto pr-1 custom-scrollbar' : ''}`}>
                          {sorted.map((item, index) => {
                            const pct = Math.max((item.stock / maxStock) * 100, 2);
                            const pctTotal = ((item.stock / totalStock) * 100).toFixed(1);
                            const color = COLORS_BAR[index % COLORS_BAR.length];
                            return (
                              <div
                                key={item.centro_id || item.centro}
                                className={`rounded-xl border border-gray-100 p-3.5 transition-all hover:shadow-lg hover:border-gray-200 ${puedeNavegar ? 'cursor-pointer' : ''}`}
                                style={{ borderLeft: `4px solid ${color}` }}
                                onClick={() => puedeNavegar && irAReportesCentro(item.centro_id)}
                              >
                                <div className="flex items-center justify-between mb-1">
                                  <p className="text-xs font-semibold text-gray-500 truncate flex-1" title={item.centro}>
                                    {item.centro}
                                  </p>
                                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-md tabular-nums ml-2 flex-shrink-0" style={{ color, backgroundColor: `${color}15` }}>
                                    {pctTotal}%
                                  </span>
                                </div>
                                <p className="text-2xl font-black text-gray-900 tabular-nums leading-tight">{item.stock.toLocaleString('es-MX')}</p>
                                <p className="text-[10px] text-gray-400 mb-2.5">unidades en stock</p>
                                <div className="w-full bg-gray-100 rounded-full h-2 overflow-hidden">
                                  <div className="h-full rounded-full transition-all duration-700 ease-out" style={{ width: `${pct}%`, background: `linear-gradient(90deg, ${color}99, ${color})` }} />
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })()
                ) : (
                  <div className="flex flex-col items-center justify-center h-64 text-gray-400">
                    <FaWarehouse className="text-4xl mb-3 opacity-50" />
                    <p>No hay datos de inventario</p>
                  </div>
                )}
              </ChartCard>
            );
          })()}
        </section>
      )}

      {/* ========== REQUISICIONES + INVENTARIO LADO A LADO ========== */}
      {puedeVerGraficasCompletas && graficas.requisiciones_por_estado.length > 0 && (
        <section className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {/* Requisiciones — Turno Automatizado */}
          <ChartCard 
            title="Requisiciones - Turno Automatizado" 
            icon={FaClipboardList}
            action={
              <div className="flex items-center gap-2">
                <button
                  onClick={() => navigate('/requisiciones')}
                  className="text-xs px-3 py-1.5 rounded-lg font-medium transition-colors hover:bg-gray-100"
                  style={{ color: 'var(--color-primary, #9F2241)' }}
                >
                  Ver todas →
                </button>
              </div>
            }
          >
            {/* Badges de resumen */}
            {graficas.requisiciones_resumen && (
              <div className="flex items-center flex-wrap gap-2 mb-3 pb-3 border-b border-gray-100">
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg" style={{ background: 'rgba(159, 34, 65, 0.06)' }}>
                  <span className="text-lg font-black" style={{ color: '#9F2241' }}>{graficas.requisiciones_resumen.total}</span>
                  <span className="text-[10px] text-gray-500">Pendientes</span>
                </div>
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-50">
                  <span className="text-lg font-black text-amber-700">{graficas.requisiciones_resumen.en_proceso}</span>
                  <span className="text-[10px] text-gray-500">Procesando</span>
                </div>
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-50">
                  <span className="text-lg font-black text-emerald-700">{graficas.requisiciones_resumen.completadas}</span>
                  <span className="text-[10px] text-gray-500">Aportado</span>
                </div>
                {graficas.requisiciones_resumen.dias_promedio_cumplimiento != null && (
                  <div className="ml-auto flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-blue-50">
                    <FaClock size={10} className="text-blue-500" />
                    <span className="text-[10px] font-bold text-blue-700">VM {graficas.requisiciones_resumen.dias_promedio_cumplimiento}d</span>
                  </div>
                )}
              </div>
            )}

            {/* Stacked progress bar — Distribución de estados */}
            {graficas.requisiciones_por_estado.length > 0 && totalRequisiciones > 0 && (
              <div className="mb-4">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[9px] font-bold text-gray-400 uppercase tracking-wider">Distribución por Estado</span>
                  <span className="text-[10px] font-bold text-gray-500">{totalRequisiciones} total</span>
                </div>
                <div className="w-full h-3 rounded-full overflow-hidden flex bg-gray-100">
                  {graficas.requisiciones_por_estado.map((item, idx) => {
                    const pct = (item.cantidad / totalRequisiciones) * 100;
                    if (pct < 0.5) return null;
                    const color = COLORES_ESTADO_REQUISICION[item.estado] || COLORES_ESTADO_REQUISICION.DEFAULT;
                    return (
                      <div
                        key={item.estado}
                        className="h-full transition-all duration-700 first:rounded-l-full last:rounded-r-full"
                        style={{ width: `${pct}%`, backgroundColor: color }}
                        title={`${formatearEstado(item.estado)}: ${item.cantidad} (${pct.toFixed(0)}%)`}
                      />
                    );
                  })}
                </div>
                <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1.5">
                  {graficas.requisiciones_por_estado.slice(0, 5).map((item) => {
                    const color = COLORES_ESTADO_REQUISICION[item.estado] || COLORES_ESTADO_REQUISICION.DEFAULT;
                    return (
                      <div key={item.estado} className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-sm flex-shrink-0" style={{ backgroundColor: color }} />
                        <span className="text-[8px] text-gray-400">{formatearEstado(item.estado)}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Gráfica de tendencia */}
            <div className="min-w-0 mb-3">
              <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Tendencia Mensual</p>
              {graficas.requisiciones_por_mes.length > 0 ? (
                <ResponsiveContainer width="100%" height={130} minWidth={0} minHeight={0}>
                  <BarChart data={graficas.requisiciones_por_mes} barGap={1} margin={{ top: 5, right: 5, left: -15, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
                    <XAxis dataKey="mes_corto" tick={{ fontSize: 9, fill: '#9CA3AF' }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 9, fill: '#9CA3AF' }} axisLine={false} tickLine={false} allowDecimals={false} width={22} />
                    <Tooltip
                      content={({ active, payload }) => {
                        if (!active || !payload?.length) return null;
                        const d = payload[0]?.payload;
                        return (
                          <div className="bg-white rounded-lg shadow-lg border border-gray-200 p-2 min-w-[100px]">
                            <p className="text-[10px] font-bold text-gray-700 mb-1">{d?.mes}</p>
                            <p className="text-[10px]"><span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1" />{d?.completadas} completadas</p>
                            <p className="text-[10px]"><span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-400 mr-1" />{d?.pendientes} en proceso</p>
                            <p className="text-[10px]"><span className="inline-block w-1.5 h-1.5 rounded-full bg-red-400 mr-1" />{d?.rechazadas} rechazadas</p>
                          </div>
                        );
                      }}
                    />
                    <Bar dataKey="completadas" stackId="a" fill="#10B981" radius={[0, 0, 0, 0]} />
                    <Bar dataKey="pendientes" stackId="a" fill="#F59E0B" radius={[0, 0, 0, 0]} />
                    <Bar dataKey="rechazadas" stackId="a" fill="#EF4444" radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-[130px] text-gray-300 text-xs">Sin datos</div>
              )}
              <div className="flex items-center justify-center gap-3 mt-0.5">
                {[{ l: 'Completadas', c: '#10B981' }, { l: 'En proceso', c: '#F59E0B' }, { l: 'Rechazadas', c: '#EF4444' }].map(x => (
                  <div key={x.l} className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-sm" style={{ backgroundColor: x.c }} />
                    <span className="text-[9px] text-gray-400">{x.l}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Tabla de detalle por producto */}
            {analytics?.top_productos?.length > 0 && (
              <div className="pt-3 border-t border-gray-100">
                <div className="max-h-[180px] overflow-y-auto custom-scrollbar">
                  <table className="w-full text-left">
                    <thead className="sticky top-0 z-10">
                      <tr className="bg-gray-50/90">
                        <th className="text-[9px] font-bold text-gray-400 uppercase tracking-wider px-2 py-1">Clave</th>
                        <th className="text-[9px] font-bold text-gray-400 uppercase tracking-wider px-2 py-1">Producto</th>
                        <th className="text-[9px] font-bold text-gray-400 uppercase tracking-wider px-2 py-1 text-center">Surtido</th>
                        <th className="text-[9px] font-bold text-gray-400 uppercase tracking-wider px-2 py-1 text-center">Solicit.</th>
                        <th className="text-[9px] font-bold text-gray-400 uppercase tracking-wider px-2 py-1 text-right w-20">Cumpl.</th>
                      </tr>
                    </thead>
                    <tbody>
                      {analytics.top_productos.slice(0, 5).map((item, idx) => (
                        <tr key={idx} className="border-b border-gray-50 last:border-0 hover:bg-gray-50/50 transition-colors">
                          <td className="px-2 py-1">
                            <span className="text-[10px] font-mono font-bold text-gray-600">{item.clave}</span>
                          </td>
                          <td className="px-2 py-1">
                            <span className="text-[10px] text-gray-500 truncate block max-w-[100px]" title={item.nombre}>{item.nombre}</span>
                          </td>
                          <td className="px-2 py-1 text-center">
                            <span className="text-[11px] font-bold text-gray-800 tabular-nums">{(item.total_surtido || 0).toLocaleString('es-MX')}</span>
                          </td>
                          <td className="px-2 py-1 text-center">
                            <span className="text-[11px] font-bold text-gray-600 tabular-nums">{item.veces_solicitado || 0}</span>
                          </td>
                          <td className="px-2 py-1">
                            <div className="flex items-center gap-1 justify-end">
                              <div className="w-10 bg-gray-100 rounded-full h-1.5 overflow-hidden">
                                <div className="h-full rounded-full" style={{ width: `${item.porcentaje_cumplimiento || 0}%`, backgroundColor: (item.porcentaje_cumplimiento || 0) >= 80 ? '#10B981' : (item.porcentaje_cumplimiento || 0) >= 50 ? '#F59E0B' : '#EF4444' }} />
                              </div>
                              <span className={`text-[10px] font-black tabular-nums ${(item.porcentaje_cumplimiento || 0) >= 80 ? 'text-emerald-600' : (item.porcentaje_cumplimiento || 0) >= 50 ? 'text-amber-600' : 'text-red-600'}`}>{(item.porcentaje_cumplimiento || 0).toFixed(0)}%</span>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </ChartCard>

          {/* Inventario por Centro — Vista barras horizontales */}
          <ChartCard 
            title="Inventario por Centro" 
            icon={FaWarehouse}
            action={
              permisos?.verReportes ? (
                <button
                  onClick={() => navigate('/reportes', { state: { tipo: 'inventario' } })}
                  className="text-xs px-3 py-1.5 rounded-lg font-medium transition-colors hover:bg-gray-100"
                  style={{ color: 'var(--color-primary, #9F2241)' }}
                >
                  Ver todos →
                </button>
              ) : null
            }
          >
            {(() => {
              const stockCentro = graficas.stock_por_centro || [];
              const stockProducto = graficas.stock_por_producto || [];
              const items = stockCentro.length > 1 ? stockCentro : stockProducto;
              const labelKey = stockCentro.length > 1 ? 'centro' : 'producto';
              if (items.length === 0) return (
                <div className="flex flex-col items-center justify-center h-48 text-gray-400">
                  <FaWarehouse className="text-3xl mb-2 opacity-50" />
                  <p className="text-sm">Sin datos de inventario</p>
                </div>
              );
              const sorted = [...items].sort((a, b) => b.stock - a.stock);
              const maxStock = sorted[0]?.stock || 1;
              const totalStock = sorted.reduce((s, p) => s + p.stock, 0);
              return (
                <div className={`space-y-3 ${sorted.length > 5 ? 'max-h-[420px] overflow-y-auto pr-1 custom-scrollbar' : ''}`}>
                  {sorted.map((item, index) => {
                    const pct = Math.max((item.stock / maxStock) * 100, 3);
                    return (
                      <div
                        key={item.centro_id || item[labelKey]}
                        className={`group ${permisos?.verReportes && stockCentro.length > 1 ? 'cursor-pointer' : ''}`}
                        onClick={() => permisos?.verReportes && stockCentro.length > 1 && navigate('/reportes', { state: { tipo: 'inventario', centro: item.centro_id } })}
                      >
                        <div className="flex items-baseline justify-between mb-1">
                          <span className="text-sm font-semibold text-gray-700 truncate flex-1 mr-3 group-hover:text-gray-900 transition-colors" title={item[labelKey]}>
                            {item[labelKey]}
                          </span>
                          <div className="flex items-baseline gap-3 flex-shrink-0">
                            <span className="text-lg font-black text-gray-900 tabular-nums">{item.stock.toLocaleString('es-MX')}</span>
                            <span className="text-xs text-gray-400 tabular-nums">{totalStock.toLocaleString('es-MX')}</span>
                          </div>
                        </div>
                        <div className="w-full bg-gray-100 rounded-full h-2.5 overflow-hidden">
                          <div className="h-full rounded-full transition-all duration-700 ease-out" style={{ width: `${pct}%`, background: `linear-gradient(90deg, var(--color-primary, #932043)88, var(--color-primary, #932043))` }} />
                        </div>
                      </div>
                    );
                  })}
                  <div className="pt-2 mt-1 border-t border-gray-100 flex items-center justify-between text-[10px] text-gray-400">
                    <span>Uso de compras</span>
                    <span>Caducidad próxima</span>
                  </div>
                </div>
              );
            })()}
          </ChartCard>
        </section>
      )}

      {/* ========== CADUCOS QUE REQUIEREN SOLUCIÓN ========== */}
      {puedeVerGraficasCompletas && analytics?.caducidades?.lotes_criticos?.length > 0 && (
        <section>
          <ChartCard title="Caducos que requieren Solución" icon={FaExclamationTriangle}>
            {/* Progress indicator: Nivel de urgencia */}
            {(() => {
              const lc = analytics.caducidades.lotes_criticos;
              const vencidos = lc.filter(l => l.estado === 'vencido').length;
              const urgentes = lc.filter(l => l.dias_para_vencer != null && l.dias_para_vencer <= 15 && l.estado !== 'vencido').length;
              const proximos = lc.length - vencidos - urgentes;
              const total = lc.length;
              return (
                <div className="mb-4 p-3 rounded-xl bg-gray-50/80 border border-gray-100">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[9px] font-bold text-gray-400 uppercase tracking-wider">Nivel de Urgencia</span>
                    <span className="text-[10px] font-bold text-gray-600">{total} lotes afectados</span>
                  </div>
                  <div className="w-full h-3 rounded-full overflow-hidden flex bg-gray-200">
                    {vencidos > 0 && <div className="h-full bg-red-500 transition-all duration-700" style={{ width: `${(vencidos / total) * 100}%` }} title={`${vencidos} vencidos`} />}
                    {urgentes > 0 && <div className="h-full bg-orange-500 transition-all duration-700" style={{ width: `${(urgentes / total) * 100}%` }} title={`${urgentes} urgentes (≤15d)`} />}
                    {proximos > 0 && <div className="h-full bg-amber-400 transition-all duration-700" style={{ width: `${(proximos / total) * 100}%` }} title={`${proximos} próximos`} />}
                  </div>
                  <div className="flex items-center gap-4 mt-1.5">
                    {vencidos > 0 && <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500" /><span className="text-[9px] text-gray-500">{vencidos} vencidos</span></div>}
                    {urgentes > 0 && <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-orange-500" /><span className="text-[9px] text-gray-500">{urgentes} urgentes</span></div>}
                    {proximos > 0 && <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-400" /><span className="text-[9px] text-gray-500">{proximos} próximos</span></div>}
                  </div>
                </div>
              );
            })()}
            <div className="space-y-2.5 max-h-[280px] overflow-y-auto custom-scrollbar">
              {analytics.caducidades.lotes_criticos.map((lote, idx) => {
                const isVencido = lote.estado === 'vencido';
                const diasAbs = lote.dias_para_vencer != null ? Math.abs(lote.dias_para_vencer) : 0;
                const barPct = isVencido ? 100 : Math.max(Math.min(100 - (lote.dias_para_vencer / 90 * 100), 100), 10);
                return (
                  <div key={idx} className="flex items-center gap-3 py-2 px-3 rounded-xl border border-gray-100 hover:bg-gray-50/50 transition-colors">
                    <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${isVencido ? 'bg-red-500' : lote.dias_para_vencer <= 15 ? 'bg-orange-500' : 'bg-amber-400'}`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold text-gray-700 truncate" title={`${lote.producto_nombre} - ${lote.numero_lote}`}>
                        {lote.centro_nombre || 'Centro'} - {lote.producto_nombre}
                      </p>
                      <p className="text-[10px] text-gray-400">Lote {lote.numero_lote} · {lote.producto_clave}</p>
                    </div>
                    <div className="w-24 flex-shrink-0">
                      <div className="w-full bg-gray-100 rounded-full h-2 overflow-hidden">
                        <div className="h-full rounded-full transition-all duration-500" style={{ width: `${barPct}%`, backgroundColor: isVencido ? '#EF4444' : lote.dias_para_vencer <= 15 ? '#F97316' : '#F59E0B' }} />
                      </div>
                    </div>
                    <div className="text-right flex-shrink-0 min-w-[90px]">
                      <span className={`text-[10px] font-bold ${isVencido ? 'text-red-600' : 'text-orange-600'}`}>
                        {isVencido ? 'CADUCADO' : 'CADUCIDAD'}
                      </span>
                      <span className="text-[10px] text-gray-400 ml-1">
                        {isVencido ? `${diasAbs}d vencido` : `${lote.dias_para_vencer}d`}
                      </span>
                    </div>
                    <span className="text-[10px] text-gray-400 flex-shrink-0 tabular-nums">{lote.cantidad} uds</span>
                  </div>
                );
              })}
            </div>
            <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-100">
              <button
                onClick={() => navigate('/lotes')}
                className="text-xs px-3 py-1.5 rounded-lg font-medium transition-colors hover:bg-gray-100 flex items-center gap-1.5"
                style={{ color: 'var(--color-primary, #9F2241)' }}
              >
                <FaBoxes size={10} />
                Gestionar Lotes
              </button>
              <button
                onClick={() => navigate('/productos')}
                className="text-xs px-3 py-1.5 rounded-lg font-medium transition-colors hover:bg-gray-100 flex items-center gap-1.5"
                style={{ color: 'var(--color-primary, #9F2241)' }}
              >
                Actualizar stock →
              </button>
            </div>
          </ChartCard>
        </section>
      )}

      {/* ========== USO DE REQUISICIONES — DONUT GRANDE ========== */}
      {puedeVerGraficasCompletas && graficas.requisiciones_por_estado.length > 0 && (
        <section>
          <ChartCard title="Uso de Requisiciones" icon={FaChartBar}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
              {/* Donut grande */}
              <div className="flex flex-col items-center">
                <div className="relative" style={{ width: 220, height: 220 }}>
                  <ResponsiveContainer width={220} height={220} minWidth={0} minHeight={0}>
                    <PieChart>
                      <Pie
                        data={graficas.requisiciones_por_estado}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={95}
                        paddingAngle={2}
                        dataKey="cantidad"
                        cornerRadius={4}
                      >
                        {graficas.requisiciones_por_estado.map((entry, index) => (
                          <Cell 
                            key={`usecell-${index}`} 
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
                            <div className="bg-white rounded-lg shadow-lg border border-gray-200 p-2 min-w-[110px]">
                              <div className="flex items-center gap-1.5 mb-0.5">
                                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
                                <span className="font-bold text-gray-800 text-xs">{formatearEstado(data.estado)}</span>
                              </div>
                              <p className="text-sm font-black text-gray-900">{data.cantidad} <span className="text-[10px] font-normal text-gray-400">/ {totalRequisiciones}</span></p>
                            </div>
                          );
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                    <div className="text-center">
                      <p className="text-3xl font-black text-gray-900">{totalRequisiciones}</p>
                      <p className="text-xs text-gray-400 font-semibold">
                        {graficas.requisiciones_resumen?.tasa_cumplimiento != null ? `${graficas.requisiciones_resumen.tasa_cumplimiento}%` : ''} Demanda
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Stats desglose */}
              <div>
                <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-3">Referencia / Desglose</p>
                <div className="grid grid-cols-3 gap-3 mb-4">
                  {(() => {
                    const completadas = graficas.requisiciones_resumen?.completadas || 0;
                    const enProceso = graficas.requisiciones_resumen?.en_proceso || 0;
                    const rechazadas = graficas.requisiciones_resumen?.rechazadas || 0;
                    return (
                      <>
                        <div className="text-center p-3 rounded-xl bg-emerald-50 border border-emerald-100">
                          <p className="text-2xl font-black text-emerald-700">{completadas}</p>
                          <p className="text-[10px] text-emerald-600 font-semibold">Realizados</p>
                        </div>
                        <div className="text-center p-3 rounded-xl bg-amber-50 border border-amber-100">
                          <p className="text-2xl font-black text-amber-700">{enProceso}</p>
                          <p className="text-[10px] text-amber-600 font-semibold">Formalizados</p>
                        </div>
                        <div className="text-center p-3 rounded-xl bg-red-50 border border-red-100">
                          <p className="text-2xl font-black text-red-600">{rechazadas}</p>
                          <p className="text-[10px] text-red-600 font-semibold">Parciales</p>
                        </div>
                      </>
                    );
                  })()}
                </div>
                {/* Leyenda detallada */}
                <div className="space-y-2">
                  {graficas.requisiciones_por_estado.map((item) => {
                    const color = COLORES_ESTADO_REQUISICION[item.estado] || COLORES_ESTADO_REQUISICION.DEFAULT;
                    const pct = totalRequisiciones > 0 ? ((item.cantidad / totalRequisiciones) * 100).toFixed(0) : 0;
                    return (
                      <div key={item.estado} className="flex items-center gap-2">
                        <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
                        <span className="text-xs text-gray-600 flex-1">{formatearEstado(item.estado)}</span>
                        <span className="text-xs font-bold text-gray-800 tabular-nums">{item.cantidad}</span>
                        <span className="text-[10px] text-gray-400 tabular-nums w-8 text-right">{pct}%</span>
                      </div>
                    );
                  })}
                </div>
                {graficas.requisiciones_resumen && (
                  <div className="mt-3 pt-3 border-t border-gray-100 flex items-center gap-2">
                    <FaChartLine size={10} className="text-emerald-500" />
                    <span className="text-xs font-medium text-gray-500">Cumplimiento</span>
                    <div className="w-20 bg-gray-100 rounded-full h-2 overflow-hidden flex-shrink-0">
                      <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${graficas.requisiciones_resumen.tasa_cumplimiento}%` }} />
                    </div>
                    <span className="text-sm font-black text-emerald-700">{graficas.requisiciones_resumen.tasa_cumplimiento}%</span>
                  </div>
                )}
              </div>
            </div>
          </ChartCard>
        </section>
      )}

      {/* ========== ANALYTICS AVANZADOS (Solo Farmacia/Admin) ========== */}
      {puedeVerGraficasCompletas && analytics && (
        <>
          {/* Separador de sección Analytics */}
          <div className="flex items-center gap-3 pt-2">
            <div className="w-1.5 h-6 rounded-full" style={{ background: 'linear-gradient(180deg, #932043, #C9A876)' }} />
            <h2 className="text-xs font-extrabold text-gray-600 uppercase tracking-[0.15em]">Analytics Avanzados</h2>
            <div className="h-px flex-1 bg-gradient-to-r from-gray-200 to-transparent" />
          </div>

          {/* Alertas de Caducidad */}
          {analytics.caducidades && (analytics.caducidades.vencidos > 0 || analytics.caducidades.vencen_15_dias > 0 || analytics.caducidades.vencen_30_dias > 0) && (
            <section className="dash-alert-section">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-8 h-8 rounded-lg bg-red-50 flex items-center justify-center">
                  <FaExclamationTriangle className="text-red-500" size={14} />
                </div>
                <h2 className="text-sm font-bold text-gray-700 uppercase tracking-wider">Alertas de Caducidad</h2>
                <div className="h-px flex-1 bg-gradient-to-r from-red-200 to-transparent" />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-3">
                {analytics.caducidades.vencidos > 0 && (
                  <div className="dash-caducidad-card dash-caducidad-red">
                    <div className="dash-caducidad-icon bg-red-100">
                      <FaTimesCircle className="text-red-500 text-base" />
                    </div>
                    <div className="flex-1">
                      <p className="text-2xl font-black text-red-700">{analytics.caducidades.vencidos}</p>
                      <p className="text-xs text-red-600 font-semibold">Lotes Vencidos</p>
                      <p className="text-[9px] text-red-400 mt-0.5">Acción inmediata</p>
                    </div>
                    <div className="dash-caducidad-bar bg-red-500" />
                  </div>
                )}
                {analytics.caducidades.vencen_15_dias > 0 && (
                  <div className="dash-caducidad-card dash-caducidad-orange">
                    <div className="dash-caducidad-icon bg-orange-100">
                      <FaExclamationCircle className="text-orange-500 text-base" />
                    </div>
                    <div className="flex-1">
                      <p className="text-2xl font-black text-orange-700">{analytics.caducidades.vencen_15_dias}</p>
                      <p className="text-xs text-orange-600 font-semibold">Vencen en 15 días</p>
                      <p className="text-[9px] text-orange-400 mt-0.5">Prioridad alta</p>
                    </div>
                    <div className="dash-caducidad-bar bg-orange-500" />
                  </div>
                )}
                {analytics.caducidades.vencen_30_dias > 0 && (
                  <div className="dash-caducidad-card dash-caducidad-yellow">
                    <div className="dash-caducidad-icon bg-amber-100">
                      <FaExclamationTriangle className="text-amber-500 text-base" />
                    </div>
                    <div className="flex-1">
                      <p className="text-2xl font-black text-amber-700">{analytics.caducidades.vencen_30_dias}</p>
                      <p className="text-xs text-amber-600 font-semibold">Vencen en 30 días</p>
                      <p className="text-[9px] text-amber-400 mt-0.5">Monitorear</p>
                    </div>
                    <div className="dash-caducidad-bar bg-amber-500" />
                  </div>
                )}
                {(analytics.caducidades.vencen_90_dias || 0) > 0 && (
                  <div className="dash-caducidad-card" style={{ background: 'linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%)', borderLeft: '4px solid #3B82F6' }}>
                    <div className="dash-caducidad-icon bg-blue-100">
                      <FaCalendarAlt className="text-blue-500 text-base" />
                    </div>
                    <div className="flex-1">
                      <p className="text-2xl font-black text-blue-700">{analytics.caducidades.vencen_90_dias}</p>
                      <p className="text-xs text-blue-600 font-semibold">Vencen en 90 días</p>
                      <p className="text-[9px] text-blue-400 mt-0.5">Atención preventiva</p>
                    </div>
                    <div className="dash-caducidad-bar bg-blue-500" />
                  </div>
                )}
              </div>
            </section>
          )}

          {/* Top Productos y Top Centros */}
          <section className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            {/* Top 10 Productos más Surtidos */}
            {analytics.top_productos && analytics.top_productos.length > 0 && (
              <ChartCard title="Top 10 Productos más Surtidos" icon={FaTrophy}>
                {(() => {
                  const MEDAL_COLORS = ['#F59E0B', '#9CA3AF', '#CD7F32'];
                  const maxVal = Math.max(...analytics.top_productos.map(p => p.total_surtido || 0), 1);
                  const totalSurtido = analytics.top_productos.reduce((s, p) => s + (p.total_surtido || 0), 0);
                  return (
                    <div className="space-y-2">
                      {analytics.top_productos.map((item, idx) => {
                        const pct = ((item.total_surtido || 0) / maxVal * 100).toFixed(0);
                        const pctTotal = ((item.total_surtido || 0) / totalSurtido * 100).toFixed(1);
                        return (
                          <div key={idx} className="dash-ranking-item group">
                            <div className="flex items-center gap-3">
                              <span className={`dash-ranking-badge ${idx < 3 ? 'dash-ranking-medal' : ''}`} style={idx < 3 ? { background: MEDAL_COLORS[idx], color: '#fff' } : {}}>
                                {idx + 1}
                              </span>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center justify-between mb-1">
                                  <span className="text-sm font-bold text-gray-700 truncate mr-2" title={`${item.clave} - ${item.nombre}`}>
                                    {item.clave}
                                  </span>
                                  <div className="flex items-center gap-2 flex-shrink-0">
                                    <span className="text-sm font-black text-gray-900 tabular-nums">
                                      {(item.total_surtido || 0).toLocaleString('es-MX')}
                                    </span>
                                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-md text-gray-500 bg-gray-100">{pctTotal}%</span>
                                  </div>
                                </div>
                                <p className="text-[10px] text-gray-400 truncate" title={item.nombre}>{item.nombre}</p>
                                <div className="flex items-center gap-3 text-[10px] text-gray-400 mb-1.5">
                                  <span>Solicitado <span className="font-bold text-gray-600">{(item.veces_solicitado || 0)}×</span></span>
                                  <span>Cumpl. <span className={`font-bold ${(item.porcentaje_cumplimiento || 0) >= 80 ? 'text-emerald-600' : (item.porcentaje_cumplimiento || 0) >= 50 ? 'text-amber-600' : 'text-red-600'}`}>{(item.porcentaje_cumplimiento || 0).toFixed(0)}%</span></span>
                                </div>
                                <div className="w-full bg-gray-100 rounded-full h-1.5 overflow-hidden">
                                  <div className="h-full rounded-full transition-all duration-700" style={{ width: `${pct}%`, background: idx < 3 ? `linear-gradient(90deg, ${MEDAL_COLORS[Math.min(idx, 2)]}99, ${MEDAL_COLORS[Math.min(idx, 2)]})` : 'linear-gradient(90deg, #932043aa, #932043)' }} />
                                </div>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                      <div className="pt-3 mt-1 border-t border-gray-100 flex justify-between items-center">
                        <span className="text-xs text-gray-400">{analytics.top_productos.length} productos</span>
                        <span className="text-sm font-bold text-gray-700">{totalSurtido.toLocaleString('es-MX')} uds surtidas</span>
                      </div>
                    </div>
                  );
                })()}
              </ChartCard>
            )}

            {/* Centros que más Solicitan — tabla con desglose */}
            {graficas.requisiciones_resumen?.por_centro?.length > 0 && (
              <ChartCard title="Centros que más Solicitan" icon={FaBuilding}>
                {(() => {
                  const centros = graficas.requisiciones_resumen.por_centro;
                  const totalCentros = centros.reduce((s, c) => s + c.total, 0);
                  const totalCompl = centros.reduce((s, c) => s + c.completadas, 0);
                  return (
                    <div>
                      {/* Mini KPIs */}
                      <div className="grid grid-cols-3 gap-2 mb-3">
                        <div className="dash-stat-mini dash-stat-info">
                          <span className="text-[9px] font-bold text-blue-600 uppercase tracking-wider">Requisiciones</span>
                          <p className="text-lg font-black text-blue-800 mt-0.5">{totalCentros}</p>
                        </div>
                        <div className="dash-stat-mini dash-stat-success">
                          <span className="text-[9px] font-bold text-emerald-600 uppercase tracking-wider">Completadas</span>
                          <p className="text-lg font-black text-emerald-800 mt-0.5">{totalCompl}</p>
                        </div>
                        <div className="dash-stat-mini dash-stat-warning">
                          <span className="text-[9px] font-bold text-amber-600 uppercase tracking-wider">Cumplimiento</span>
                          <p className="text-lg font-black text-amber-800 mt-0.5">{totalCentros > 0 ? Math.round(totalCompl / totalCentros * 100) : 0}%</p>
                        </div>
                      </div>
                      {/* Tabla */}
                      <div className={`${centros.length > 5 ? 'max-h-[340px] overflow-y-auto pr-1 custom-scrollbar' : ''}`}>
                        <table className="w-full text-left">
                          <thead className="sticky top-0 z-10">
                            <tr className="bg-gray-50/90 border-b border-gray-100">
                              <th className="text-[9px] font-bold text-gray-400 uppercase tracking-wider pl-2 pr-1 py-1.5 w-7">#</th>
                              <th className="text-[9px] font-bold text-gray-400 uppercase tracking-wider px-2 py-1.5">Centro</th>
                              <th className="text-[9px] font-bold text-gray-400 uppercase tracking-wider px-2 py-1.5 text-center w-12">Total</th>
                              <th className="text-[9px] font-bold text-gray-400 uppercase tracking-wider px-2 py-1.5 text-center w-14">
                                <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500 align-middle mr-0.5" />Compl.
                              </th>
                              <th className="text-[9px] font-bold text-gray-400 uppercase tracking-wider px-2 py-1.5 text-center w-14">
                                <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-400 align-middle mr-0.5" />Proc.
                              </th>
                              <th className="text-[9px] font-bold text-gray-400 uppercase tracking-wider pl-2 pr-3 py-1.5 text-right w-16">Tasa</th>
                            </tr>
                          </thead>
                          <tbody>
                            {centros.map((c, i) => {
                              const maxTotal = centros[0]?.total || 1;
                              const barWidth = (c.total / maxTotal) * 100;
                              return (
                                <tr key={i} className="border-b border-gray-50 last:border-0 hover:bg-gray-50/50 transition-colors">
                                  <td className="pl-2 pr-1 py-1.5">
                                    <span className={`inline-flex items-center justify-center w-5 h-5 rounded-full text-[8px] font-black text-white ${i === 0 ? 'bg-yellow-400' : i === 1 ? 'bg-gray-300' : i === 2 ? 'bg-amber-600' : 'bg-gray-200 text-gray-500'}`}>
                                      {i + 1}
                                    </span>
                                  </td>
                                  <td className="px-2 py-1.5">
                                    <p className="text-xs font-semibold text-gray-700 break-words leading-tight" title={c.centro}>{c.centro}</p>
                                    <div className="w-full bg-gray-100 rounded-full h-1 mt-1 overflow-hidden">
                                      <div className="h-full rounded-full transition-all duration-700" style={{ width: `${barWidth}%`, background: 'linear-gradient(90deg, #932043aa, #932043)' }} />
                                    </div>
                                  </td>
                                  <td className="px-2 py-1.5 text-center">
                                    <span className="text-sm font-black text-gray-800">{c.total}</span>
                                  </td>
                                  <td className="px-2 py-1.5 text-center">
                                    <span className="text-xs font-bold text-emerald-600">{c.completadas}</span>
                                  </td>
                                  <td className="px-2 py-1.5 text-center">
                                    <span className="text-xs font-bold text-amber-600">{c.en_proceso}</span>
                                  </td>
                                  <td className="pl-2 pr-3 py-1.5 text-right">
                                    <span className={`text-[10px] font-black px-1.5 py-0.5 rounded-full ${c.tasa >= 70 ? 'bg-emerald-50 text-emerald-700' : c.tasa >= 40 ? 'bg-amber-50 text-amber-700' : 'bg-red-50 text-red-700'}`}>
                                      {c.tasa}%
                                    </span>
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                      <div className="pt-3 mt-1 border-t border-gray-100 flex justify-between items-center">
                        <span className="text-xs text-gray-400">{centros.length} centros</span>
                        <span className="text-xs text-gray-500">Prom. cumplimiento: <span className="font-bold text-gray-700">{totalCentros > 0 ? Math.round(totalCompl / totalCentros * 100) : 0}%</span></span>
                      </div>
                    </div>
                  );
                })()}
              </ChartCard>
            )}
          </section>

          {/* Donaciones + Logs Críticos — lado a lado (referencia) */}
          <section className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            {/* Resumen Donaciones */}
            {analytics.donaciones && (
              <ChartCard title="Recepción de Donaciones" icon={FaHandHoldingHeart}>
                {/* Total KPI + badges */}
                <div className="flex items-center flex-wrap gap-3 mb-4 pb-3 border-b border-gray-100">
                  <div className="flex items-center gap-2">
                    <FaGift className="text-purple-500" size={14} />
                    <span className="text-3xl font-black text-gray-900">{(analytics.donaciones.total_donaciones || 0).toLocaleString('es-MX')}</span>
                    <span className="text-xs text-gray-400">totalidades</span>
                  </div>
                  <div className="flex items-center gap-2 ml-auto">
                    <span className="text-[10px] font-bold px-2 py-1 rounded-md bg-emerald-50 text-emerald-700 border border-emerald-100">
                      <FaArrowDown size={8} className="inline mr-1" />{analytics.donaciones.donaciones_mes || 0} lotes
                    </span>
                    <span className="text-[10px] font-bold px-2 py-1 rounded-md bg-blue-50 text-blue-700 border border-blue-100">
                      {((analytics.donaciones.donaciones_mes || 0) / Math.max(analytics.donaciones.total_donaciones || 1, 1) * 100).toFixed(1)}% utilizados
                    </span>
                  </div>
                </div>

                {/* Stacked bar de donaciones por estado */}
                {analytics.donaciones.por_estado?.length > 0 && (() => {
                  const totalDon = analytics.donaciones.por_estado.reduce((s, i) => s + (i.cantidad || 0), 0) || 1;
                  const DON_COLORS = ['#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#0EA5E9'];
                  return (
                    <div className="mb-4">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-[9px] font-bold text-gray-400 uppercase tracking-wider">Distribución por Estado</span>
                        <span className="text-[10px] font-bold text-gray-500">{totalDon} total</span>
                      </div>
                      <div className="w-full h-3 rounded-full overflow-hidden flex bg-gray-100">
                        {analytics.donaciones.por_estado.map((item, idx) => {
                          const pct = (item.cantidad / totalDon) * 100;
                          if (pct < 0.5) return null;
                          return (
                            <div
                              key={idx}
                              className="h-full transition-all duration-700 first:rounded-l-full last:rounded-r-full"
                              style={{ width: `${pct}%`, backgroundColor: DON_COLORS[idx % DON_COLORS.length] }}
                              title={`${item.estado}: ${item.cantidad} (${pct.toFixed(0)}%)`}
                            />
                          );
                        })}
                      </div>
                    </div>
                  );
                })()}

                {/* Por Estado con barras horizontales */}
                {analytics.donaciones.por_estado?.length > 0 && (
                  <div className="space-y-3">
                    {(() => {
                      const totalDon = analytics.donaciones.por_estado.reduce((s, i) => s + (i.cantidad || 0), 0) || 1;
                      const maxDon = Math.max(...analytics.donaciones.por_estado.map(i => i.cantidad || 0), 1);
                      const DON_COLORS = { 'Cuadrado': '#10B981', 'Procesando': '#F59E0B', 'Cancelados': '#EF4444' };
                      return analytics.donaciones.por_estado.map((item, idx) => {
                        const pct = ((item.cantidad || 0) / totalDon * 100).toFixed(0);
                        const barPct = Math.max((item.cantidad / maxDon) * 100, 5);
                        return (
                          <div key={idx} className="flex items-center gap-3">
                            <span className={`w-2 h-2 rounded-full flex-shrink-0`} style={{ backgroundColor: Object.values(DON_COLORS)[idx % 3] || '#8B5CF6' }} />
                            <span className="text-xs font-semibold text-gray-600 w-24 truncate">{item.estado}</span>
                            <div className="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
                              <div className="h-full rounded-full transition-all duration-500" style={{ width: `${barPct}%`, backgroundColor: Object.values(DON_COLORS)[idx % 3] || '#8B5CF6' }} />
                            </div>
                            <span className="text-xs font-bold text-gray-700 tabular-nums w-10 text-right">{pct}%</span>
                            <span className="text-[10px] text-gray-400 tabular-nums w-12 text-right">{item.cantidad}</span>
                          </div>
                        );
                      });
                    })()}
                  </div>
                )}
              </ChartCard>
            )}

            {/* Últimos Logs Críticos — junto a Donaciones (referencia) */}
            {puedeVerGraficasBasicas && permisos?.verMovimientos && movimientos.length > 0 && (
              <ChartCard 
                title="Últimos Logs Críticos" 
                icon={FaExchangeAlt}
                action={
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">{movimientos.length} registros</span>
                    <button
                      onClick={() => setMostrarTodos(!mostrarTodos)}
                      className="text-xs px-3 py-1.5 rounded-lg font-bold transition-all"
                      style={{ 
                        backgroundColor: mostrarTodos ? 'var(--color-primary, #9F2241)' : '#F3F4F6',
                        color: mostrarTodos ? 'white' : '#374151'
                      }}
                    >
                      {mostrarTodos ? 'Menos' : 'Todos'}
                    </button>
                    <button
                      onClick={handleRefresh}
                      className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors text-gray-400"
                      title="Actualizar"
                    >
                      <FaSync size={11} className={refreshing ? 'animate-spin' : ''} />
                    </button>
                  </div>
                }
              >
                {/* Activity Timeline */}
                <div className="dash-timeline max-h-[420px] overflow-y-auto custom-scrollbar">
                  {(mostrarTodos ? movimientos : movimientos.slice(0, 8)).map((mov, index) => {
                    const isEntrada = mov.tipo_movimiento === 'ENTRADA';
                    const isSalida = mov.tipo_movimiento === 'SALIDA';
                    const dotColor = isEntrada ? '#10B981' : isSalida ? '#EF4444' : '#6366F1';
                    return (
                      <div
                        key={mov.id || index}
                        className="dash-timeline-item cursor-pointer group"
                        style={{ '--timeline-color': dotColor }}
                        onClick={() => permisos?.verMovimientos && navigate('/movimientos', { state: { highlightId: mov.id } })}
                      >
                        <div className="dash-timeline-dot" style={{ color: dotColor, backgroundColor: dotColor }} />
                        <div className="dash-timeline-content">
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-0.5">
                                <span className={`inline-flex items-center gap-1 text-[9px] font-black uppercase tracking-wider px-1.5 py-0.5 rounded-md ${
                                  isEntrada ? 'bg-emerald-50 text-emerald-700' : isSalida ? 'bg-red-50 text-red-700' : 'bg-indigo-50 text-indigo-700'
                                }`}>
                                  {isEntrada ? <FaArrowDown size={7} /> : <FaArrowUp size={7} />}
                                  {mov.tipo_movimiento || 'MOV'}
                                </span>
                                <span className="text-[10px] text-gray-400">{mov.usuario || 'Sistema'}</span>
                              </div>
                              <p className="text-xs font-semibold text-gray-800 truncate group-hover:text-gray-900 transition-colors" title={mov.producto__descripcion}>
                                {mov.producto__descripcion || 'Producto'}
                              </p>
                              <div className="flex items-center gap-2 mt-0.5">
                                {mov.producto__clave && <span className="text-[10px] font-mono text-gray-400">{mov.producto__clave}</span>}
                                {mov.lote__codigo_lote && mov.lote__codigo_lote !== 'N/A' && (
                                  <span className="text-[10px] text-gray-400">Lote: {mov.lote__codigo_lote}</span>
                                )}
                              </div>
                            </div>
                            <div className="flex flex-col items-end flex-shrink-0">
                              <span className={`text-sm font-black tabular-nums ${isEntrada ? 'text-emerald-600' : isSalida ? 'text-red-600' : 'text-indigo-600'}`}>
                                {isEntrada ? '+' : isSalida ? '-' : ''}{mov.cantidad}
                              </span>
                              <span className="text-[10px] text-gray-400 whitespace-nowrap mt-0.5">
                                {mov.fecha_movimiento ? new Date(mov.fecha_movimiento).toLocaleDateString('es-MX', { day: '2-digit', month: 'short' }) : ''}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
                <button
                  onClick={() => navigate('/movimientos')}
                  className="w-full mt-4 py-2.5 rounded-xl font-bold text-sm text-white transition-all hover:shadow-lg hover:opacity-90 flex items-center justify-center gap-2"
                  style={{ background: 'linear-gradient(135deg, var(--color-primary, #9F2241) 0%, var(--color-primary-hover, #6B1839) 100%)' }}
                >
                  <FaExchangeAlt size={12} />
                  Ver todos los movimientos
                </button>
              </ChartCard>
            )}
          </section>

          {/* Caja Chica */}
          <section className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            {/* Resumen Caja Chica */}
            {analytics.caja_chica && (
              <ChartCard title="Resumen Caja Chica" icon={FaMoneyBillWave}>
                {/* KPIs principales */}
                <div className="grid grid-cols-2 gap-2 mb-3">
                  <div className="dash-money-card">
                    <span className="text-[9px] font-bold text-emerald-600 uppercase tracking-wider">Monto Total</span>
                    <p className="text-xl font-black text-emerald-700 mt-0.5">
                      <span className="text-sm">$</span>{(analytics.caja_chica.monto_total || 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}
                    </p>
                    <div className="w-full bg-emerald-100 rounded-full h-1 mt-2">
                      <div className="h-full rounded-full bg-emerald-500" style={{ width: '100%' }} />
                    </div>
                  </div>
                  <div className="dash-money-card">
                    <span className="text-[9px] font-bold text-teal-600 uppercase tracking-wider">Promedio/Compra</span>
                    <p className="text-xl font-black text-teal-700 mt-0.5">
                      <span className="text-sm">$</span>{(analytics.caja_chica.promedio_compra || 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}
                    </p>
                    <p className="text-[10px] text-gray-400 mt-1.5">{analytics.caja_chica.total_compras || 0} compras totales</p>
                  </div>
                </div>
                
                {/* Stats del mes */}
                <div className="grid grid-cols-2 gap-2 mb-3">
                  <div className="dash-stat-mini dash-stat-info">
                    <span className="text-[9px] font-bold text-blue-600 uppercase">Compras este mes</span>
                    <p className="text-lg font-black text-blue-800 mt-0.5">{analytics.caja_chica.compras_mes || 0}</p>
                  </div>
                  <div className="dash-stat-mini dash-stat-success">
                    <span className="text-[9px] font-bold text-emerald-600 uppercase">Monto del mes</span>
                    <p className="text-base font-black text-emerald-800 mt-0.5"><span className="text-[10px]">$</span>{(analytics.caja_chica.monto_mes || 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</p>
                  </div>
                </div>

                {/* Por Estado */}
                {analytics.caja_chica.por_estado?.length > 0 && (
                  <div className="mb-4">
                    <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-2">
                      <FaClipboardList className="text-emerald-400" size={10} />
                      Por Estado
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {analytics.caja_chica.por_estado.map((item, idx) => (
                        <span key={idx} className="text-[10px] font-bold px-2.5 py-1.5 rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-100">
                          {item.estado}: <span className="text-sm">{item.cantidad}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* Top Compradores */}
                {analytics.caja_chica.top_compradores?.length > 0 && (
                  <div>
                    <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2.5 flex items-center gap-2">
                      <FaUserTie className="text-emerald-400" size={10} />
                      Principales Compradores
                    </p>
                    <div className="space-y-1.5 max-h-44 overflow-y-auto custom-scrollbar">
                      {analytics.caja_chica.top_compradores.map((item, idx) => (
                        <div key={idx} className="dash-list-row">
                          <span className="dash-bar-rank text-[10px]" style={{ background: '#0F766E' }}>{idx + 1}</span>
                          <span className="text-xs font-medium text-gray-600 truncate flex-1">{item.nombre}</span>
                          <div className="text-right flex-shrink-0">
                            <span className="text-xs font-bold text-emerald-600">${(item.monto_total || 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</span>
                            <span className="text-[10px] text-gray-400 ml-1.5">{item.total_compras}c</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </ChartCard>
            )}

            {/* Accesos Rápidos — en la misma fila que Caja Chica */}
            {quickAccessItems.length > 0 && (
              <div className="space-y-4">
                <div className="flex items-center gap-3 px-1">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: 'linear-gradient(135deg, var(--color-primary, #9F2241), var(--color-primary-hover, #6B1839))' }}>
                    <FaArrowRight className="text-white" size={12} />
                  </div>
                  <div>
                    <h3 className="font-bold text-gray-800 text-sm">Accesos Rápidos</h3>
                    <p className="text-[10px] text-gray-400">Navegación directa</p>
                  </div>
                </div>
                <div className="space-y-2.5">
                  {quickAccessItems.map((item, index) => (
                    <QuickAccessCard key={index} {...item} />
                  ))}
                </div>
                {lastUpdate && (
                  <div className="dash-update-footer">
                    <FaClock className="text-gray-300" size={10} />
                    <span className="text-[10px] text-gray-400">
                      Actualizado: {lastUpdate.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                )}
              </div>
            )}
          </section>
        </>
      )}

      {/* Logs Críticos — fallback para usuarios sin analytics */}
      {!(puedeVerGraficasCompletas && analytics) && puedeVerGraficasBasicas && permisos?.verMovimientos && movimientos.length > 0 && (
        <section>
          <ChartCard 
            title="Últimos Logs Críticos" 
            icon={FaExchangeAlt}
            action={
              <div className="flex items-center gap-2">
                <button onClick={handleRefresh} className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors text-gray-400" title="Actualizar">
                  <FaSync size={11} className={refreshing ? 'animate-spin' : ''} />
                </button>
              </div>
            }
          >
            <div className="max-h-[320px] overflow-y-auto custom-scrollbar">
              <table className="dash-logs-table">
                <thead>
                  <tr>
                    <th>Tipo</th>
                    <th>Responsable</th>
                    <th>Descripción</th>
                    <th className="text-center">Cant.</th>
                    <th className="text-right">Fecha</th>
                  </tr>
                </thead>
                <tbody>
                  {movimientos.slice(0, 6).map((mov, index) => (
                    <tr key={mov.id || index} className="cursor-pointer group" onClick={() => navigate('/movimientos', { state: { highlightId: mov.id } })}>
                      <td>
                        <span className={`inline-flex items-center gap-1 text-[10px] font-black uppercase px-2 py-0.5 rounded-md ${
                          mov.tipo_movimiento === 'ENTRADA' ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'
                        }`}>
                          {mov.tipo_movimiento === 'ENTRADA' ? <FaArrowDown size={8} /> : <FaArrowUp size={8} />}
                          {mov.tipo_movimiento || 'MOV'}
                        </span>
                      </td>
                      <td><span className="text-xs font-medium text-gray-600">{mov.usuario || 'Sistema'}</span></td>
                      <td><span className="text-xs text-gray-700 truncate block max-w-[180px]">{mov.producto__descripcion || 'Producto'}</span></td>
                      <td className="text-center">
                        <span className={`text-sm font-black tabular-nums ${mov.tipo_movimiento === 'ENTRADA' ? 'text-emerald-600' : 'text-red-600'}`}>
                          {mov.tipo_movimiento === 'ENTRADA' ? '+' : '-'}{mov.cantidad}
                        </span>
                      </td>
                      <td className="text-right">
                        <span className="text-[11px] text-gray-500 whitespace-nowrap">
                          {mov.fecha_movimiento ? new Date(mov.fecha_movimiento).toLocaleDateString('es-MX', { day: '2-digit', month: 'short', year: 'numeric' }) : ''}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </ChartCard>
        </section>
      )}

      {/* ========== FOOTER CON INFO ========== */}
      <footer className="dash-footer">
        <div className="flex items-center justify-center gap-3">
          <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: 'var(--color-primary, #9F2241)', opacity: 0.5 }} />
          <p className="text-[10px] text-gray-400 font-medium tracking-wider uppercase">
            SIFP &mdash; Sistema de Inventario Farmacéutico Penitenciario &bull; v2.0
          </p>
          <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: 'var(--color-primary, #9F2241)', opacity: 0.5 }} />
        </div>
      </footer>
    </div>
  );
};

export default Dashboard;
