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
  Legend, BarChart, Bar
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
          {/* Franja superior Pantone */}
          <div className="h-[2px]" style={{ background: colors.gradient }} />
          
          <div className="relative z-10 p-3 sm:p-4">
            {/* Fila 1: Icono + Título + Trend badge */}
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-center gap-2">
                <div 
                  className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
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
            
            {/* Fila 2: Número principal */}
            <div className="mb-0.5">
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
            
            {/* Fila 3: Métrica secundaria (opcional) */}
            {secondaryLabel && (
              <div className="flex items-center gap-1.5 mb-1">
                <span className="text-[9px] text-gray-400">{secondaryLabel}</span>
                <span className="text-[11px] font-bold" style={{ color: colors.text }}>{secondaryValue}</span>
              </div>
            )}
            
            {/* Sparkline mini-chart (opcional) */}
            {sparklinePath && (
              <div className="mt-1 kpi-sparkline-wrap">
                <svg 
                  viewBox={`0 0 ${sparklinePath.W} ${sparklinePath.H}`} 
                  className="w-full h-7 sm:h-8"
                  preserveAspectRatio="none"
                >
                  <defs>
                    <linearGradient id={`spark-fill-${colorType}-${delay}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={colors.sparkStroke} stopOpacity="0.15" />
                      <stop offset="100%" stopColor={colors.sparkStroke} stopOpacity="0" />
                    </linearGradient>
                  </defs>
                  <path d={sparklinePath.area} fill={`url(#spark-fill-${colorType}-${delay})`} />
                  <path d={sparklinePath.line} fill="none" stroke={colors.sparkStroke} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
            )}
            
            {/* Footer: Action link */}
            {onClick && (
              <div className="flex items-center justify-end mt-1.5 pt-1.5 border-t" style={{ borderColor: 'rgba(0,0,0,0.03)' }}>
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
        transition-all duration-200 hover:shadow-md
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
    stock_por_centro: [],
    stock_por_producto: [],
    requisiciones_por_estado: [],
    requisiciones_por_mes: [],
    requisiciones_resumen: null,
  });
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [movimientosExpanded, setMovimientosExpanded] = useState(true);
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
      setGraficas({ consumo_mensual: [], stock_por_centro: [], stock_por_producto: [], requisiciones_por_estado: [], requisiciones_por_mes: [], requisiciones_resumen: null });
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
    },
  ], [kpis, permisos, navigate, selectedCentro, centroNombre, consumoSparkline, entradasSparkline, stockSparkline, analytics]);

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
      <header 
        className="rounded-xl shadow-sm border border-gray-100/80 overflow-hidden bg-white"
      >
        <div className="h-1 w-full" style={{ background: 'linear-gradient(90deg, var(--color-primary, #9F2241) 0%, var(--color-primary-hover, #6B1839) 40%, #C9A876 100%)' }} />
        
        <div className="px-4 py-3">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
            <div className="flex items-center gap-2.5 min-w-0">
              <div 
                className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
                style={{ background: 'linear-gradient(135deg, var(--color-primary, #9F2241), var(--color-primary-hover, #6B1839))' }}
              >
                <FaChartLine className="text-white text-sm" />
              </div>
              <h1 
                className="text-xl font-black tracking-tight"
                style={{ color: 'var(--color-primary, #9F2241)' }}
              >
                Panel de Control
              </h1>
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
            </div>
          
          {/* Controles */}
          <div className="flex items-center gap-2 flex-shrink-0 w-full md:w-auto">
            {/* Selector de centro */}
            {puedeFiltrarPorCentro && (
              <div className="flex-1 md:flex-none md:min-w-[200px] md:max-w-[300px]">
                <CentroSelector onCentroChange={handleCentroChange} selectedValue={selectedCentro} />
              </div>
            )}
            
            {/* Botón de refresh */}
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className={`
                p-2 rounded-lg bg-gray-50 border border-gray-200
                hover:bg-gray-100 transition-all flex-shrink-0
                ${refreshing ? 'opacity-50 cursor-not-allowed' : ''}
              `}
              title="Actualizar datos"
            >
              <FaSync className={`text-gray-400 text-xs ${refreshing ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
        
        {/* Fila inferior: Subtítulo y fecha */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1.5 mt-3 pt-2.5 border-t border-gray-100/60">
          <p className="text-xs text-gray-500 flex items-center gap-1.5">
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
          <div className="flex items-center gap-1.5 text-xs text-gray-400 flex-shrink-0">
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
        </div>
      </header>

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

        {/* Fila secundaria de analytics - Solo Admin/Farmacia */}
        {puedeVerGraficasCompletas && analytics && (
          <>
            <div className="flex items-center gap-2 mt-4 sm:mt-5 mb-3 sm:mb-3">
              <div className="kpi-section-dot" style={{ background: 'linear-gradient(135deg, #9B7E4C, #C9A876)' }} />
              <h2 
                className="text-[10px] sm:text-[11px] font-extrabold uppercase tracking-[0.15em]"
                style={{ color: '#9B7E4C' }}
              >
                Análisis avanzado
              </h2>
              <div className="h-px flex-1 bg-gradient-to-r from-gray-200 to-transparent" />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
              {/* Requisiciones totales */}
              {permisos?.verRequisiciones && (
                <KPICard
                  title="Requisiciones"
                  value={totalRequisiciones}
                  subtext="Total activas en sistema"
                  icon={FaClipboardList}
                  colorType="gold"
                  delay={400}
                  loading={refreshing}
                  onClick={() => navigate('/requisiciones')}
                  secondaryLabel="Estados:"
                  secondaryValue={`${graficas.requisiciones_por_estado?.length || 0} diferentes`}
                />
              )}
              {/* Caducidades - alerta */}
              {analytics.caducidades && (
                <KPICard
                  title="Alertas Caducidad"
                  value={(analytics.caducidades.vencidos || 0) + (analytics.caducidades.vencen_30_dias || 0)}
                  subtext="Lotes vencidos + próximos 30 días"
                  icon={FaExclamationTriangle}
                  colorType={analytics.caducidades.vencidos > 0 ? 'danger' : 'warning'}
                  delay={500}
                  loading={analyticsLoading}
                  secondaryLabel={analytics.caducidades.vencidos > 0 ? '🔴 Vencidos:' : '90 días:'}
                  secondaryValue={analytics.caducidades.vencidos > 0 
                    ? String(analytics.caducidades.vencidos) 
                    : String(analytics.caducidades.vencen_90_dias || 0)}
                />
              )}
              {/* Donaciones */}
              {analytics.donaciones && permisos?.verDonaciones && (
                <KPICard
                  title="Donaciones"
                  value={analytics.donaciones.total_donaciones || 0}
                  subtext={`${(analytics.donaciones.total_unidades || 0).toLocaleString('es-MX')} unidades donadas`}
                  icon={FaHandHoldingHeart}
                  colorType="info"
                  delay={600}
                  loading={analyticsLoading}
                  onClick={() => navigate('/donaciones')}
                  secondaryLabel="Este mes:"
                  secondaryValue={String(analytics.donaciones.donaciones_mes || 0)}
                />
              )}
              {/* Caja Chica */}
              {analytics.caja_chica && (
                <KPICard
                  title="Caja Chica"
                  value={Math.round(analytics.caja_chica.monto_total || 0)}
                  subtext={`${analytics.caja_chica.total_compras || 0} compras realizadas`}
                  icon={FaMoneyBillWave}
                  colorType="success"
                  delay={700}
                  loading={analyticsLoading}
                  prefix="$"
                  secondaryLabel="Promedio:"
                  secondaryValue={`$${(analytics.caja_chica.promedio_compra || 0).toLocaleString('es-MX', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`}
                />
              )}
            </div>
          </>
        )}
      </section>

      {/* ========== GRÁFICAS PRINCIPALES ========== */}
      {puedeVerGraficasBasicas && (
        <section className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <ChartCard title="Consumo Mensual (Últimos 6 meses)" icon={FaChartLine} expandable>
            {graficas.consumo_mensual.length > 0 ? (
              <>
                {/* Mini KPIs del período */}
                {(() => {
                  const totalEntradas = graficas.consumo_mensual.reduce((s, m) => s + (m.entradas || 0), 0);
                  const totalSalidas = graficas.consumo_mensual.reduce((s, m) => s + (m.salidas || 0), 0);
                  const balance = totalEntradas - totalSalidas;
                  const mesActual = graficas.consumo_mensual[graficas.consumo_mensual.length - 1];
                  const mesAnterior = graficas.consumo_mensual[graficas.consumo_mensual.length - 2];
                  const tendencia = mesAnterior?.salidas ? (((mesActual?.salidas || 0) - mesAnterior.salidas) / mesAnterior.salidas * 100).toFixed(0) : 0;
                  return (
                    <div className="grid grid-cols-3 gap-2 mb-3">
                      <div className="dash-stat-mini dash-stat-success">
                        <div className="flex items-center gap-1 mb-0.5">
                          <FaArrowDown className="text-emerald-500" size={9} />
                          <span className="text-[9px] font-bold text-emerald-600 uppercase tracking-wider">Entradas</span>
                        </div>
                        <p className="text-lg font-black text-emerald-700 tabular-nums">{totalEntradas.toLocaleString('es-MX')}</p>
                        <p className="text-[10px] text-emerald-500 mt-0.5">6 meses</p>
                      </div>
                      <div className="dash-stat-mini dash-stat-danger">
                        <div className="flex items-center gap-1 mb-0.5">
                          <FaArrowUp className="text-red-500" size={9} />
                          <span className="text-[9px] font-bold text-red-600 uppercase tracking-wider">Salidas</span>
                        </div>
                        <p className="text-lg font-black text-red-700 tabular-nums">{totalSalidas.toLocaleString('es-MX')}</p>
                        <p className="text-[10px] text-red-500 mt-0.5">
                          {Number(tendencia) > 0 ? `↑${tendencia}%` : Number(tendencia) < 0 ? `↓${Math.abs(Number(tendencia))}%` : '—'} vs anterior
                        </p>
                      </div>
                      <div className={`dash-stat-mini ${balance >= 0 ? 'dash-stat-info' : 'dash-stat-warning'}`}>
                        <div className="flex items-center gap-1 mb-0.5">
                          <FaChartBar className={balance >= 0 ? 'text-blue-500' : 'text-amber-500'} size={9} />
                          <span className={`text-[9px] font-bold uppercase tracking-wider ${balance >= 0 ? 'text-blue-600' : 'text-amber-600'}`}>Balance</span>
                        </div>
                        <p className={`text-lg font-black tabular-nums ${balance >= 0 ? 'text-blue-700' : 'text-amber-700'}`}>
                          {balance >= 0 ? '+' : ''}{balance.toLocaleString('es-MX')}
                        </p>
                        <p className={`text-[10px] mt-0.5 ${balance >= 0 ? 'text-blue-500' : 'text-amber-500'}`}>{balance >= 0 ? 'Superávit' : 'Déficit'}</p>
                      </div>
                    </div>
                  );
                })()}
                <ResponsiveContainer width="100%" height={280}>
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
                    <XAxis 
                      dataKey="mes" 
                      tick={{ fill: '#9CA3AF', fontSize: 11, fontWeight: 500 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis 
                      tick={{ fill: '#9CA3AF', fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                      tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend 
                      iconType="circle"
                      wrapperStyle={{ paddingTop: '12px', fontSize: '12px' }}
                    />
                    <Area 
                      type="monotone" dataKey="entradas" 
                      stroke="#10B981" strokeWidth={2.5} fill="url(#colorEntradas)" name="Entradas"
                      dot={{ fill: '#10B981', strokeWidth: 2, r: 3.5, stroke: '#fff' }}
                      activeDot={{ r: 6, stroke: '#fff', strokeWidth: 2, fill: '#10B981' }}
                    />
                    <Area 
                      type="monotone" dataKey="salidas" 
                      stroke="#EF4444" strokeWidth={2.5} fill="url(#colorSalidas)" name="Salidas"
                      dot={{ fill: '#EF4444', strokeWidth: 2, r: 3.5, stroke: '#fff' }}
                      activeDot={{ r: 6, stroke: '#fff', strokeWidth: 2, fill: '#EF4444' }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
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
              <ChartCard title={chartTitle} icon={chartIcon} expandable>
                {esCentroUnico ? (
                  renderBarItems(stockProducto, 'producto', 'producto_id', false)
                ) : stockCentro.length > 0 ? (
                  renderBarItems(stockCentro, 'centro', 'centro_id', puedeNavegar, irAReportesCentro)
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

      {/* ========== REQUISICIONES — PANEL COMPACTO ACUMULATIVO ========== */}
      {puedeVerGraficasCompletas && graficas.requisiciones_por_estado.length > 0 && (
        <section>
          <ChartCard 
            title="Requisiciones — Panel Acumulativo" 
            icon={FaClipboardList}
            action={
              <button
                onClick={() => navigate('/requisiciones')}
                className="text-xs px-3 py-1.5 rounded-lg font-medium transition-colors hover:bg-gray-100"
                style={{ color: 'var(--color-primary, #9F2241)' }}
              >
                Ver todas →
              </button>
            }
          >
            {/* Layout principal: 3 columnas — Donut | Tendencia | Métricas */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
              
              {/* Col 1: Mini KPIs + Donut (4 cols) */}
              <div className="lg:col-span-4 space-y-2.5">
                {/* Mini KPIs inline */}
                {graficas.requisiciones_resumen && (
                  <div className="grid grid-cols-2 gap-1.5">
                    {[
                      { label: 'Total', value: graficas.requisiciones_resumen.total, color: '#9F2241' },
                      { label: 'Completadas', value: graficas.requisiciones_resumen.completadas, color: '#10B981', sub: `${graficas.requisiciones_resumen.tasa_cumplimiento}%` },
                      { label: 'En Proceso', value: graficas.requisiciones_resumen.en_proceso, color: '#F59E0B' },
                      { label: 'Rechazadas', value: graficas.requisiciones_resumen.rechazadas, color: '#EF4444', sub: `${graficas.requisiciones_resumen.tasa_rechazo}%` },
                    ].map((k, i) => (
                      <div key={i} className="bg-gray-50 rounded-lg px-2.5 py-1.5 border border-gray-100">
                        <span className="text-[10px] text-gray-400 block">{k.label}</span>
                        <div className="flex items-baseline gap-1">
                          <span className="text-lg font-black" style={{ color: k.color }}>{k.value}</span>
                          {k.sub && <span className="text-[9px] font-bold text-gray-400">{k.sub}</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                {/* Donut compacto */}
                <div className="relative">
                  <ResponsiveContainer width="100%" height={160}>
                    <PieChart>
                      <Pie
                        data={graficas.requisiciones_por_estado}
                        cx="50%"
                        cy="50%"
                        innerRadius={42}
                        outerRadius={68}
                        paddingAngle={3}
                        dataKey="cantidad"
                        cornerRadius={3}
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
                            <div className="bg-white rounded-lg shadow-lg border border-gray-200 p-2 min-w-[120px]">
                              <div className="flex items-center gap-1.5 mb-1">
                                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
                                <span className="font-bold text-gray-800 text-[11px]">{formatearEstado(data.estado)}</span>
                              </div>
                              <p className="text-base font-black text-gray-900">{data.cantidad} <span className="text-[10px] font-normal text-gray-400">/ {totalRequisiciones}</span></p>
                            </div>
                          );
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                    <div className="text-center">
                      <p className="text-2xl font-black text-gray-900">{totalRequisiciones}</p>
                      <p className="text-[9px] text-gray-400">Total</p>
                    </div>
                  </div>
                </div>
                {/* Legend compacta */}
                <div className="flex flex-wrap gap-x-2 gap-y-0.5 justify-center">
                  {graficas.requisiciones_por_estado.map((item) => (
                    <div key={item.estado} className="flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: COLORES_ESTADO_REQUISICION[item.estado] || COLORES_ESTADO_REQUISICION.DEFAULT }} />
                      <span className="text-[9px] text-gray-400">{formatearEstado(item.estado)} ({item.cantidad})</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Col 2: Tendencia mensual (5 cols) */}
              <div className="lg:col-span-5">
                <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1.5">Tendencia Mensual</p>
                {graficas.requisiciones_por_mes.length > 0 ? (
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={graficas.requisiciones_por_mes} barGap={1} margin={{ top: 5, right: 5, left: -15, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
                      <XAxis dataKey="mes_corto" tick={{ fontSize: 10, fill: '#9CA3AF' }} axisLine={false} tickLine={false} />
                      <YAxis tick={{ fontSize: 10, fill: '#9CA3AF' }} axisLine={false} tickLine={false} allowDecimals={false} width={25} />
                      <Tooltip
                        content={({ active, payload }) => {
                          if (!active || !payload?.length) return null;
                          const d = payload[0]?.payload;
                          return (
                            <div className="bg-white rounded-lg shadow-lg border border-gray-200 p-2 min-w-[110px]">
                              <p className="text-[10px] font-bold text-gray-700 mb-1">{d?.mes}</p>
                              <p className="text-[10px] text-gray-500"><span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1" />{d?.completadas} completadas</p>
                              <p className="text-[10px] text-gray-500"><span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-400 mr-1" />{d?.pendientes} en proceso</p>
                              <p className="text-[10px] text-gray-500"><span className="inline-block w-1.5 h-1.5 rounded-full bg-red-400 mr-1" />{d?.rechazadas} rechazadas</p>
                              <p className="text-[10px] font-bold text-gray-800 pt-0.5 mt-0.5 border-t border-gray-100">{d?.total} total</p>
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
                  <div className="flex items-center justify-center h-[200px] text-gray-300 text-xs">Sin datos de tendencia</div>
                )}
                <div className="flex items-center justify-center gap-3 mt-1">
                  {[{ l: 'Completadas', c: '#10B981' }, { l: 'En proceso', c: '#F59E0B' }, { l: 'Rechazadas', c: '#EF4444' }].map(x => (
                    <div key={x.l} className="flex items-center gap-1">
                      <span className="w-2 h-2 rounded-sm" style={{ backgroundColor: x.c }} />
                      <span className="text-[9px] text-gray-400">{x.l}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Col 3: Métricas clave compactas (3 cols) */}
              <div className="lg:col-span-3 space-y-2">
                <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Métricas</p>
                
                {graficas.requisiciones_resumen?.dias_promedio_cumplimiento != null && (
                  <div className="bg-blue-50/80 rounded-lg p-2.5 border border-blue-100">
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <FaClock size={10} className="text-blue-500" />
                      <span className="text-[10px] font-medium text-blue-600">Tiempo Promedio</span>
                    </div>
                    <p className="text-xl font-black text-blue-800">{graficas.requisiciones_resumen.dias_promedio_cumplimiento} <span className="text-[10px] font-medium">días</span></p>
                  </div>
                )}

                {graficas.requisiciones_resumen?.urgentes > 0 && (
                  <div className="bg-orange-50/80 rounded-lg p-2.5 border border-orange-100">
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <FaExclamationTriangle size={10} className="text-orange-500" />
                      <span className="text-[10px] font-medium text-orange-600">Urgentes</span>
                    </div>
                    <p className="text-xl font-black text-orange-800">{graficas.requisiciones_resumen.urgentes}</p>
                  </div>
                )}

                {graficas.requisiciones_resumen && (
                  <div className="bg-emerald-50/80 rounded-lg p-2.5 border border-emerald-100">
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <FaChartLine size={10} className="text-emerald-500" />
                      <span className="text-[10px] font-medium text-emerald-600">Cumplimiento</span>
                    </div>
                    <p className="text-xl font-black text-emerald-800">{graficas.requisiciones_resumen.tasa_cumplimiento}%</p>
                    <div className="w-full bg-emerald-100 rounded-full h-1 mt-1 overflow-hidden">
                      <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${graficas.requisiciones_resumen.tasa_cumplimiento}%` }} />
                    </div>
                  </div>
                )}

                {graficas.requisiciones_resumen?.por_centro?.length > 0 && (
                  <div className="bg-gray-50 rounded-lg p-2.5 border border-gray-100">
                    <div className="flex items-center gap-1.5 mb-1.5">
                      <FaBuilding size={10} className="text-gray-400" />
                      <span className="text-[10px] font-medium text-gray-500">Top Centros</span>
                    </div>
                    <div className="space-y-1">
                      {graficas.requisiciones_resumen.por_centro.slice(0, 3).map((c, i) => (
                        <div key={i} className="flex items-center justify-between">
                          <span className="text-[10px] text-gray-500 truncate flex-1">{c.centro}</span>
                          <span className="text-[10px] font-bold text-gray-700 ml-1">{c.total}</span>
                        </div>
                      ))}
                    </div>
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

              {/* Lotes Críticos detalle */}
              {analytics.caducidades.lotes_criticos?.length > 0 && (
                <div className="bg-white rounded-xl border border-gray-100 p-4">
                  <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <FaExclamationTriangle className="text-red-400" size={10} />
                    Lotes Críticos — Detalle
                  </p>
                  <div className="space-y-2 max-h-52 overflow-y-auto custom-scrollbar">
                    {analytics.caducidades.lotes_criticos.map((lote, idx) => (
                      <div key={idx} className="dash-list-row">
                        <span className={`w-2 h-2 rounded-full flex-shrink-0 ${lote.estado === 'vencido' ? 'bg-red-500' : 'bg-orange-500'}`} />
                        <span className="text-[10px] font-mono text-gray-400 flex-shrink-0">{lote.producto_clave}</span>
                        <span className="text-xs font-medium text-gray-600 truncate flex-1" title={lote.producto_nombre}>{lote.producto_nombre}</span>
                        <span className="text-[10px] font-mono text-gray-400 flex-shrink-0">Lote: {lote.numero_lote}</span>
                        <span className="text-xs font-bold tabular-nums flex-shrink-0" style={{ color: lote.estado === 'vencido' ? '#EF4444' : '#F97316' }}>
                          {lote.dias_para_vencer != null ? (lote.dias_para_vencer < 0 ? `${Math.abs(lote.dias_para_vencer)}d vencido` : `${lote.dias_para_vencer}d`) : ''}
                        </span>
                        <span className="text-[10px] text-gray-400 flex-shrink-0">{lote.cantidad} uds</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
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

            {/* Top Centros Solicitantes */}
            {analytics.top_centros && analytics.top_centros.length > 0 && (
              <ChartCard title="Centros que más Solicitan" icon={FaHospital}>
                {(() => {
                  const maxReq = Math.max(...analytics.top_centros.map(c => c.total_requisiciones || 0), 1);
                  const totalReq = analytics.top_centros.reduce((s, c) => s + (c.total_requisiciones || 0), 0);
                  const totalSurtidas = analytics.top_centros.reduce((s, c) => s + (c.surtidas || 0), 0);
                  const totalPendientes = analytics.top_centros.reduce((s, c) => s + (c.pendientes || 0), 0);
                  return (
                    <div className="space-y-3">
                      <div className="grid grid-cols-3 gap-2 mb-3">
                        <div className="dash-stat-mini dash-stat-info">
                          <span className="text-[9px] font-bold text-blue-600 uppercase tracking-wider">Requisiciones</span>
                          <p className="text-lg font-black text-blue-800 mt-0.5">{totalReq}</p>
                        </div>
                        <div className="dash-stat-mini dash-stat-success">
                          <span className="text-[9px] font-bold text-emerald-600 uppercase tracking-wider">Surtidas</span>
                          <p className="text-lg font-black text-emerald-800 mt-0.5">{totalSurtidas}</p>
                        </div>
                        <div className="dash-stat-mini dash-stat-warning">
                          <span className="text-[9px] font-bold text-amber-600 uppercase tracking-wider">Pendientes</span>
                          <p className="text-lg font-black text-amber-800 mt-0.5">{totalPendientes}</p>
                        </div>
                      </div>
                      <div className={`space-y-2.5 ${analytics.top_centros.length > 5 ? 'max-h-[300px] overflow-y-auto pr-2 custom-scrollbar' : ''}`}>
                        {analytics.top_centros.map((item, idx) => {
                          const pctReq = (item.total_requisiciones || 0) / maxReq * 100;
                          const tasa = item.tasa_cumplimiento || 0;
                          return (
                            <div key={idx} className="dash-centro-item group">
                              <div className="flex items-center justify-between mb-1.5">
                                <div className="flex items-center gap-2 min-w-0">
                                  <span className="dash-bar-rank bg-blue-500 text-white">{idx + 1}</span>
                                  <span className="text-sm font-semibold text-gray-700 truncate" title={item.nombre}>{item.nombre}</span>
                                </div>
                                <span className={`text-[10px] font-black px-2 py-0.5 rounded-full ${tasa >= 80 ? 'bg-emerald-50 text-emerald-700' : tasa >= 50 ? 'bg-amber-50 text-amber-700' : 'bg-red-50 text-red-700'}`}>
                                  {tasa.toFixed(0)}% cumpl.
                                </span>
                              </div>
                              <div className="flex items-center gap-3 text-[10px] text-gray-500 mb-1.5">
                                <span className="tabular-nums"><span className="font-bold text-blue-600">{item.total_requisiciones}</span> req</span>
                                <span className="tabular-nums"><span className="font-bold text-emerald-600">{item.surtidas || 0}</span> surtidas</span>
                                <span className="tabular-nums"><span className="font-bold text-amber-600">{item.pendientes || 0}</span> pend.</span>
                              </div>
                              <div className="w-full bg-gray-100 rounded-full h-1.5 overflow-hidden">
                                <div className="h-full rounded-full transition-all duration-700" style={{ width: `${pctReq}%`, background: tasa >= 80 ? '#10B981' : tasa >= 50 ? '#F59E0B' : '#EF4444' }} />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                      <div className="pt-3 mt-1 border-t border-gray-100 flex justify-between items-center">
                        <span className="text-xs text-gray-400">{analytics.top_centros.length} centros</span>
                        <span className="text-xs text-gray-500">Prom. cumplimiento: <span className="font-bold text-gray-700">{totalReq > 0 ? (totalSurtidas / totalReq * 100).toFixed(0) : 0}%</span></span>
                      </div>
                    </div>
                  );
                })()}
              </ChartCard>
            )}
          </section>

          {/* Donaciones y Caja Chica */}
          <section className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            {/* Resumen Donaciones */}
            {analytics.donaciones && (
              <ChartCard title="Resumen de Donaciones" icon={FaHandHoldingHeart}>
                {/* KPIs principales */}
                <div className="grid grid-cols-2 gap-2 mb-3">
                  <div className="dash-stat-mini dash-stat-primary">
                    <div className="flex items-center gap-1 mb-0.5">
                      <FaGift className="text-purple-500" size={9} />
                      <span className="text-[9px] font-bold text-purple-600 uppercase tracking-wider">Total</span>
                    </div>
                    <p className="text-xl font-black text-purple-700">{analytics.donaciones.total_donaciones || 0}</p>
                    <p className="text-[9px] text-purple-400 mt-0.5">donaciones registradas</p>
                  </div>
                  <div className="dash-stat-mini dash-stat-success">
                    <div className="flex items-center gap-1 mb-0.5">
                      <FaCalendarAlt className="text-emerald-500" size={9} />
                      <span className="text-[9px] font-bold text-emerald-600 uppercase tracking-wider">Este mes</span>
                    </div>
                    <p className="text-xl font-black text-emerald-700">{analytics.donaciones.donaciones_mes || 0}</p>
                    <p className="text-[9px] text-emerald-400 mt-0.5">nuevas donaciones</p>
                  </div>
                </div>
                
                {/* Por Estado */}
                {analytics.donaciones.por_estado?.length > 0 && (
                  <div className="mb-4">
                    <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2.5 flex items-center gap-2">
                      <FaClipboardList className="text-purple-400" size={10} />
                      Por Estado
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {analytics.donaciones.por_estado.map((item, idx) => (
                        <span key={idx} className="text-[10px] font-bold px-2.5 py-1.5 rounded-lg bg-purple-50 text-purple-700 border border-purple-100">
                          {item.estado}: <span className="text-sm">{item.cantidad}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Top Centros Receptores */}
                {analytics.donaciones.top_receptores?.length > 0 && (
                  <div>
                    <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2.5 flex items-center gap-2">
                      <FaBuilding className="text-purple-400" size={10} />
                      Top Centros Receptores
                    </p>
                    <div className="space-y-1.5 max-h-44 overflow-y-auto custom-scrollbar">
                      {analytics.donaciones.top_receptores.map((item, idx) => (
                        <div key={idx} className="dash-list-row">
                          <span className="dash-bar-rank text-[10px]" style={{ background: '#8B5CF6' }}>{idx + 1}</span>
                          <span className="text-xs font-medium text-gray-600 truncate flex-1" title={item.nombre}>{item.nombre}</span>
                          <span className="text-xs font-bold text-purple-600 tabular-nums">{item.total} donaciones</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </ChartCard>
            )}

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
          </section>
        </>
      )}

      {/* ========== SECCIÓN INFERIOR: MOVIMIENTOS + ACCESOS RÁPIDOS ========== */}
      <section className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {/* Últimos Movimientos - Timeline moderno */}
        {puedeVerGraficasBasicas && permisos?.verMovimientos && movimientos.length > 0 && (
          <div className="xl:col-span-2">
            <ChartCard 
              title="Últimos Movimientos" 
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
                    onClick={() => setMovimientosExpanded(!movimientosExpanded)}
                    className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors text-gray-400"
                  >
                    {movimientosExpanded ? <FaChevronUp size={12} /> : <FaChevronDown size={12} />}
                  </button>
                </div>
              }
            >
              {movimientosExpanded ? (
                <div className="dash-timeline">
                  <div className="space-y-0 max-h-[500px] overflow-y-auto pr-2 custom-scrollbar">
                    {(mostrarTodos ? movimientos : movimientos.slice(0, 5)).map((mov, index) => (
                      <div 
                        key={mov.id || index}
                        className="dash-timeline-item group cursor-pointer"
                        onClick={() => permisos?.verMovimientos && navigate('/movimientos', { state: { highlightId: mov.id } })}
                      >
                        <div className="dash-timeline-dot" style={{
                          background: mov.tipo_movimiento === 'ENTRADA' ? '#10B981' : mov.tipo_movimiento === 'SALIDA' ? '#EF4444' : '#6366F1'
                        }} />
                        <div className="dash-timeline-content">
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center flex-wrap gap-1.5 mb-1">
                                <span className={`text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded-md ${
                                  mov.tipo_movimiento === 'ENTRADA' ? 'bg-emerald-50 text-emerald-700' : 
                                  mov.tipo_movimiento === 'SALIDA' ? 'bg-red-50 text-red-700' : 'bg-indigo-50 text-indigo-700'
                                }`}>{mov.tipo_movimiento || 'MOV'}</span>
                                {mov.lote__codigo_lote && (
                                  <span className="text-[10px] font-mono text-gray-400 bg-gray-50 px-1.5 py-0.5 rounded">Lote: {mov.lote__codigo_lote}</span>
                                )}
                              </div>
                              <p className="text-sm font-bold text-gray-800 truncate group-hover:text-gray-900 transition-colors" title={mov.producto__descripcion}>
                                {mov.producto__clave && <span className="text-xs font-mono text-gray-400 mr-1.5">{mov.producto__clave}</span>}
                                {mov.producto__descripcion || 'Producto'}
                              </p>
                              <div className="flex items-center flex-wrap gap-x-3 gap-y-0.5 mt-1">
                                {mov.origen && (
                                  <span className="text-[10px] text-gray-400"><span className="font-semibold text-gray-500">De:</span> {mov.origen}</span>
                                )}
                                {mov.destino && (
                                  <span className="text-[10px] text-gray-400"><span className="font-semibold text-gray-500">A:</span> {mov.destino}</span>
                                )}
                                {mov.usuario && mov.usuario !== 'Sistema' && (
                                  <span className="text-[10px] text-gray-400 flex items-center gap-0.5"><FaUser size={8} className="text-gray-300" />{mov.usuario}</span>
                                )}
                              </div>
                            </div>
                            <div className="text-right flex-shrink-0">
                              <p className={`text-lg font-black tabular-nums ${
                                mov.tipo_movimiento === 'ENTRADA' ? 'text-emerald-600' : mov.tipo_movimiento === 'SALIDA' ? 'text-red-600' : 'text-indigo-600'
                              }`}>
                                {mov.tipo_movimiento === 'ENTRADA' ? '+' : mov.tipo_movimiento === 'SALIDA' ? '-' : ''}{mov.cantidad}
                              </p>
                              <p className="text-[10px] text-gray-400 mt-0.5">{mov.fecha_movimiento ? new Date(mov.fecha_movimiento).toLocaleDateString('es-MX', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : ''}</p>
                              {mov.requisicion_folio && (
                                <p className="text-[9px] font-mono text-blue-400 mt-0.5">Req: {mov.requisicion_folio}</p>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                  
                  <button
                    onClick={() => navigate('/movimientos')}
                    className="w-full mt-4 py-3 rounded-xl font-bold text-sm text-white transition-all hover:shadow-lg hover:opacity-90 flex items-center justify-center gap-2"
                    style={{ background: 'linear-gradient(135deg, var(--color-primary, #9F2241) 0%, var(--color-primary-hover, #6B1839) 100%)' }}
                  >
                    <FaExchangeAlt size={12} />
                    Ver todos los movimientos
                  </button>
                </div>
              ) : (
                <div className="text-center py-8">
                  <button
                    onClick={() => setMovimientosExpanded(true)}
                    className="text-gray-400 hover:text-gray-600 transition-colors flex items-center gap-2 mx-auto text-sm"
                  >
                    <FaChevronDown />
                    Expandir ({movimientos.length} movimientos)
                  </button>
                </div>
              )}
            </ChartCard>
          </div>
        )}

        {/* Accesos Rápidos - Cards modernos */}
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

        {(!movimientos.length || !permisos?.verMovimientos) && quickAccessItems.length === 0 && (
          <div className="xl:col-span-3 text-center py-12 text-gray-400">
            <FaInfoCircle className="text-4xl mx-auto mb-3 opacity-50" />
            <p className="text-sm">No hay datos adicionales para mostrar</p>
          </div>
        )}
      </section>

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
