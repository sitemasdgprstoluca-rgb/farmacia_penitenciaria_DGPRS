/**
 * Layout Principal - Sistema de Farmacia Penitenciaria
 * 
 * Diseño moderno y sofisticado con:
 * - Sidebar con animaciones fluidas y glassmorphism
 * - Header dinámico con integración del tema
 * - Navegación basada en permisos de usuario
 * - Soporte completo para CSS variables del tema
 * - Micro-interacciones y transiciones elegantes
 */

import { useEffect, useState, useMemo, useCallback } from "react";
import { Outlet, Link, useLocation, useNavigate } from "react-router-dom";
import { usePermissions } from "../hooks/usePermissions";
import { useTheme } from "../hooks/useTheme";
import { DEV_CONFIG } from "../config/dev";
import NotificacionesBell from "./NotificacionesBell";
import ConnectionIndicator from "./ConnectionIndicator";
import { notificacionesAPI, authAPI } from "../services/api";
import { clearTokens, setLogoutInProgress, hasAccessToken } from "../services/tokenManager";
import {
  FaHome,
  FaBox,
  FaWarehouse,
  FaClipboardList,
  FaBuilding,
  FaUsers,
  FaChartBar,
  FaHistory,
  FaSignOutAlt,
  FaExchangeAlt,
  FaBell,
  FaIdBadge,
  FaPalette,
  FaGift,
  FaChevronRight,
  FaChevronDown,
  FaShieldAlt,
  FaCrown,
  FaUserTie,
  FaEye,
  FaUserInjured,
  FaPills,
  FaMoneyBillWave,
  FaBoxes,
} from "react-icons/fa";

// ============================================================================
// COMPONENTES INTERNOS
// ============================================================================

/**
 * Ítem del menú con animaciones y estados hover
 * Soporta submenús expandibles
 */
const MenuItem = ({ item, isActive, onClick, isExpanded, onToggle, subItems, location }) => {
  const [isHovered, setIsHovered] = useState(false);
  const Icon = item.icon;
  const hasSubItems = item.subItems && item.subItems.length > 0;
  
  // Si tiene subItems, es un menú padre
  if (hasSubItems) {
    const isSubActive = item.subItems.some(sub => location?.pathname === sub.path);
    
    return (
      <div>
        {/* Botón padre del submenú */}
        <button
          onClick={() => onToggle && onToggle(item.id)}
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
          className="w-full group relative flex items-center gap-2.5 px-3 py-2 rounded-xl transition-all duration-300"
          style={{
            backgroundColor: isSubActive 
              ? 'rgba(255,255,255,0.18)' 
              : isHovered 
                ? 'rgba(255,255,255,0.08)' 
                : 'transparent',
          }}
        >
          {/* Indicador activo */}
          <div 
            className="absolute left-0 top-1/2 -translate-y-1/2 w-1 rounded-r-full transition-all duration-300"
            style={{
              height: isSubActive ? '60%' : '0%',
              backgroundColor: 'white',
              opacity: isSubActive ? 1 : 0,
            }}
          />
          
          {/* Icono */}
          <div 
            className="relative flex items-center justify-center w-8 h-8 rounded-lg transition-all duration-300"
            style={{
              backgroundColor: isSubActive ? 'rgba(255,255,255,0.2)' : 'transparent',
            }}
          >
            <Icon 
              size={16} 
              style={{ color: 'white', opacity: isSubActive ? 1 : 0.85 }}
            />
          </div>
          
          {/* Label */}
          <span 
            className="flex-1 text-sm text-left transition-all duration-300"
            style={{ 
              color: 'white',
              fontWeight: isSubActive ? 600 : 400,
              opacity: isSubActive ? 1 : 0.9,
            }}
          >
            {item.label}
          </span>
          
          {/* Flecha expandir/colapsar */}
          <FaChevronDown 
            size={12} 
            className="transition-transform duration-300"
            style={{
              color: 'white',
              opacity: 0.7,
              transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
            }}
          />
        </button>
        
        {/* Submenú */}
        <div 
          className="overflow-hidden transition-all duration-300"
          style={{
            maxHeight: isExpanded ? `${item.subItems.length * 44}px` : '0',
            opacity: isExpanded ? 1 : 0,
          }}
        >
          <div className="ml-4 mt-1 space-y-0.5 border-l border-white/20 pl-2">
            {item.subItems.map((subItem) => {
              const SubIcon = subItem.icon;
              const isSubItemActive = location?.pathname === subItem.path;
              
              return (
                <Link
                  key={subItem.path}
                  to={subItem.path}
                  onClick={onClick}
                  className="group flex items-center gap-2 px-2 py-2 rounded-lg transition-all duration-300"
                  style={{
                    backgroundColor: isSubItemActive 
                      ? 'rgba(255,255,255,0.15)' 
                      : 'transparent',
                  }}
                  onMouseEnter={(e) => !isSubItemActive && (e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.08)')}
                  onMouseLeave={(e) => !isSubItemActive && (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <SubIcon 
                    size={14} 
                    style={{ color: 'white', opacity: isSubItemActive ? 1 : 0.7 }}
                  />
                  <span 
                    className="text-sm"
                    style={{ 
                      color: 'white',
                      fontWeight: isSubItemActive ? 500 : 400,
                      opacity: isSubItemActive ? 1 : 0.85,
                    }}
                  >
                    {subItem.label}
                  </span>
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    );
  }
  
  // Item simple sin submenús
  return (
    <Link
      to={item.path}
      onClick={onClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className="group relative flex items-center gap-2.5 px-3 py-2 rounded-xl transition-all duration-300"
      style={{
        backgroundColor: isActive 
          ? 'rgba(255,255,255,0.18)' 
          : isHovered 
            ? 'rgba(255,255,255,0.08)' 
            : 'transparent',
        transform: isHovered && !isActive ? 'translateX(4px)' : 'translateX(0)',
      }}
    >
      {/* Indicador activo */}
      <div 
        className="absolute left-0 top-1/2 -translate-y-1/2 w-1 rounded-r-full transition-all duration-300"
        style={{
          height: isActive ? '60%' : '0%',
          backgroundColor: 'white',
          opacity: isActive ? 1 : 0,
        }}
      />
      
      {/* Icono con efecto */}
      <div 
        className="relative flex items-center justify-center w-8 h-8 rounded-lg transition-all duration-300"
        style={{
          backgroundColor: isActive ? 'rgba(255,255,255,0.2)' : 'transparent',
          transform: isHovered ? 'scale(1.05)' : 'scale(1)',
        }}
      >
        <Icon 
          size={16} 
          className="transition-transform duration-300"
          style={{ 
            color: 'white',
            opacity: isActive ? 1 : 0.85,
          }}
        />
      </div>
      
      {/* Label */}
      <span 
        className="flex-1 text-sm transition-all duration-300"
        style={{ 
          color: 'white',
          fontWeight: isActive ? 600 : 400,
          opacity: isActive ? 1 : 0.9,
        }}
      >
        {item.label}
      </span>
      
      {/* Badge de notificaciones */}
      {item.badge > 0 && (
        <span 
          className="flex items-center justify-center min-w-[22px] h-[22px] px-1.5 text-[11px] font-bold rounded-full animate-pulse"
          style={{ 
            backgroundColor: '#EF4444',
            color: 'white',
            boxShadow: '0 2px 8px rgba(239, 68, 68, 0.4)',
          }}
        >
          {item.badge > 99 ? '99+' : item.badge}
        </span>
      )}
      
      {/* Flecha indicadora */}
      <FaChevronRight 
        size={12} 
        className="transition-all duration-300"
        style={{
          color: 'white',
          opacity: isHovered || isActive ? 0.8 : 0,
          transform: isActive ? 'translateX(2px)' : 'translateX(-4px)',
        }}
      />
    </Link>
  );
};

/**
 * Badge de rol con colores dinámicos según tipo de usuario
 */
const RolBadge = ({ rol }) => {
  const config = useMemo(() => {
    switch(rol?.toUpperCase()) {
      case 'ADMIN':
        return { 
          icon: FaCrown, 
          label: 'Admin', 
          bg: 'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)',
          shadow: 'rgba(245, 158, 11, 0.3)'
        };
      case 'FARMACIA':
        return { 
          icon: FaUserTie, 
          label: 'Farmacia', 
          bg: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
          shadow: 'rgba(16, 185, 129, 0.3)'
        };
      case 'CENTRO':
        return { 
          icon: FaBuilding, 
          label: 'Centro', 
          bg: 'linear-gradient(135deg, #3B82F6 0%, #2563EB 100%)',
          shadow: 'rgba(59, 130, 246, 0.3)'
        };
      case 'VISTA':
        return { 
          icon: FaEye, 
          label: 'Vista', 
          bg: 'linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%)',
          shadow: 'rgba(139, 92, 246, 0.3)'
        };
      default:
        return { 
          icon: FaShieldAlt, 
          label: rol || 'Usuario', 
          bg: 'linear-gradient(135deg, #6B7280 0%, #4B5563 100%)',
          shadow: 'rgba(107, 114, 128, 0.3)'
        };
    }
  }, [rol]);
  
  const Icon = config.icon;
  
  return (
    <div 
      className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wide text-white"
      style={{ 
        background: config.bg,
        boxShadow: `0 2px 8px ${config.shadow}`,
      }}
    >
      <Icon size={10} />
      <span>{config.label}</span>
    </div>
  );
};

// ============================================================================
// COMPONENTE PRINCIPAL
// ============================================================================

function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarHovered, setSidebarHovered] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loggingOut, setLoggingOut] = useState(false);
  const [expandedMenus, setExpandedMenus] = useState({}); // Para submenús expandidos
  const location = useLocation();
  const navigate = useNavigate();
  const { user, permisos, getRolPrincipal, permisosValidados } = usePermissions();
  const { logoHeaderUrl, nombreSistema } = useTheme();

  const tienePermisoNotificaciones = permisos?.verNotificaciones;
  const rolPrincipal = getRolPrincipal();

  // Nombre completo del usuario
  const nombreUsuario = useMemo(() => {
    if (user?.first_name && user?.last_name) {
      return `${user.first_name} ${user.last_name}`;
    }
    return user?.username || user?.email?.split('@')[0] || 'Usuario';
  }, [user]);

  // Iniciales del usuario para avatar
  const inicialesUsuario = useMemo(() => {
    if (user?.first_name && user?.last_name) {
      return `${user.first_name[0]}${user.last_name[0]}`.toUpperCase();
    }
    return nombreUsuario.slice(0, 2).toUpperCase();
  }, [user, nombreUsuario]);

  const handleLogout = useCallback(async () => {
    if (loggingOut) return;
    setLoggingOut(true);
    setLogoutInProgress(true);
    
    try {
      await authAPI.logout();
    } catch (err) {
      // Ignorar errores
    } finally {
      if (window.notificationInterval) {
        clearInterval(window.notificationInterval);
        window.notificationInterval = null;
      }
      clearTokens();
      
      ['user', 'sifp_tema_cache', 'sifp_tema_updated_at', 'session_uid', 'session_role', 'session_hash'].forEach(key => {
        try {
          localStorage.removeItem(key);
          sessionStorage.removeItem(key);
        } catch (_) { /* Silenciar errores de storage */ }
      });
      
      try {
        navigate("/login");
      } catch (_navError) {
        window.location.href = "/login";
      }
    }
  }, [loggingOut, navigate]);

  // Menú filtrado por permisos
  const menuItems = useMemo(() => [
    { path: "/dashboard", icon: FaHome, label: "Dashboard", permission: "verDashboard" },
    { path: "/productos", icon: FaBox, label: "Productos", permission: "verProductos" },
    { path: "/lotes", icon: FaWarehouse, label: "Lotes", permission: "verLotes" },
    { path: "/requisiciones", icon: FaClipboardList, label: "Requisiciones", permission: "verRequisiciones" },
    { path: "/donaciones", icon: FaGift, label: "Donaciones", permission: "verDonaciones" },
    { path: "/movimientos", icon: FaExchangeAlt, label: "Movimientos", permission: "verMovimientos" },
    // Dispensaciones - con submenú de pacientes
    { 
      id: "dispensaciones-group",
      icon: FaPills, 
      label: "Dispensaciones", 
      permission: "verDispensaciones",
      subItems: [
        { path: "/pacientes", icon: FaUserInjured, label: "Pacientes" },
        { path: "/dispensaciones", icon: FaPills, label: "Dispensaciones" },
      ]
    },
    // Caja Chica - con submenú de inventario
    { 
      id: "caja-chica-group",
      icon: FaMoneyBillWave, 
      label: "Caja Chica", 
      permission: "verComprasCajaChica",
      subItems: [
        { path: "/compras-caja-chica", icon: FaMoneyBillWave, label: "Compras" },
        { path: "/inventario-caja-chica", icon: FaBoxes, label: "Inventario" },
      ]
    },
    // Administración
    { path: "/centros", icon: FaBuilding, label: "Centros", permission: "verCentros" },
    { path: "/usuarios", icon: FaUsers, label: "Usuarios", permission: "verUsuarios" },
    { path: "/reportes", icon: FaChartBar, label: "Reportes", permission: "verReportes" },
    { path: "/trazabilidad", icon: FaHistory, label: "Trazabilidad", permission: "verTrazabilidad" },
    { path: "/notificaciones", icon: FaBell, label: "Notificaciones", permission: "verNotificaciones", badge: unreadCount },
    { path: "/perfil", icon: FaIdBadge, label: "Perfil", permission: "verPerfil" },
    { path: "/configuracion-tema", icon: FaPalette, label: "Personalizar Tema", permission: "configurarTema" },
  ], [unreadCount]);

  // Toggle para expandir/colapsar submenús
  const toggleSubmenu = useCallback((menuId) => {
    setExpandedMenus(prev => ({
      ...prev,
      [menuId]: !prev[menuId]
    }));
  }, []);

  // Auto-expandir submenú si la ruta actual está dentro
  useEffect(() => {
    menuItems.forEach(item => {
      if (item.subItems) {
        const isActive = item.subItems.some(sub => location.pathname === sub.path);
        if (isActive) {
          setExpandedMenus(prev => ({ ...prev, [item.id]: true }));
        }
      }
    });
  }, [location.pathname, menuItems]);

  const isValidating = permisos?._isValidating || permisos?._source === 'pending_validation';
  
  const visibleMenuItems = useMemo(() => {
    if (isValidating) {
      return menuItems.filter(item => item.path === "/perfil");
    }
    return menuItems.filter((item) => !item.permission || permisos[item.permission]);
  }, [menuItems, isValidating, permisos]);

  // Responsive sidebar
  useEffect(() => {
    const handleResize = () => {
      setSidebarOpen(window.innerWidth >= 1024);
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Notificaciones polling
  // ISS-SEC FIX (audit6): Solo hacer polling si hay token de acceso válido
  // Evita errores 401 cuando user existe pero el token aún no se ha refrescado
  useEffect(() => {
    const cargarUnread = async () => {
      // ISS-SEC FIX: Verificar token antes de cada llamada (puede expirar entre polls)
      if (!hasAccessToken()) {
        return; // Token no disponible, saltar silenciosamente
      }
      
      try {
        const res = await notificacionesAPI.noLeidasCount();
        const data = res.data;
        let total = 0;
        
        if (typeof data?.no_leidas === 'number') total = data.no_leidas;
        else if (typeof data?.total === 'number') total = data.total;
        else if (typeof data?.count === 'number') total = data.count;
        else if (typeof data === 'number') total = data;
        
        setUnreadCount(Math.max(0, total));
      } catch (error) {
        // Silenciar errores (401 ya no debería ocurrir, pero por si acaso)
      }
    };
    
    // ISS-SEC FIX: Verificar que permisos estén validados Y haya token
    // permisosValidados indica que el backend confirmó la sesión
    if (user && tienePermisoNotificaciones && permisosValidados && hasAccessToken()) {
      cargarUnread();
      const id = setInterval(cargarUnread, 30000);
      window.notificationInterval = id;
      return () => {
        clearInterval(id);
        window.notificationInterval = null;
      };
    } else {
      setUnreadCount(0);
    }
  }, [user, tienePermisoNotificaciones, permisosValidados]);

  const handleNotificationCountChange = useCallback((count) => {
    setUnreadCount(count);
  }, []);

  return (
    <div className="min-h-screen flex" style={{ backgroundColor: "var(--color-background, #F8FAFC)" }}>
      {/* ========== SIDEBAR ========== */}
      <aside
        onMouseEnter={() => setSidebarHovered(true)}
        onMouseLeave={() => setSidebarHovered(false)}
        className={`
          fixed top-0 left-0 z-40 h-screen
          transition-all duration-500 ease-out
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}
          w-72 flex flex-col
        `}
        style={{ 
          background: "var(--color-sidebar-bg, linear-gradient(180deg, #9F2241 0%, #6B1839 100%))",
          boxShadow: sidebarHovered 
            ? '4px 0 30px rgba(0, 0, 0, 0.15)' 
            : '2px 0 20px rgba(0, 0, 0, 0.1)',
        }}
      >
        {/* Header del Sidebar */}
        <div className="relative px-4 py-3" style={{ borderBottom: "1px solid rgba(255,255,255,0.1)" }}>
          {/* Fondo decorativo */}
          <div 
            className="absolute inset-0 opacity-10"
            style={{
              background: 'radial-gradient(circle at 100% 0%, rgba(255,255,255,0.3) 0%, transparent 50%)',
            }}
          />
          
          <div className="relative flex items-center gap-3">
            {/* Logo con efecto de brillo */}
            <div 
              className="relative w-10 h-10 rounded-xl flex items-center justify-center overflow-hidden"
              style={{ 
                backgroundColor: 'rgba(255,255,255,0.15)',
                boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
              }}
            >
              <img 
                src={logoHeaderUrl || "/logo-sistema.png"} 
                alt="Logo" 
                className="h-7 w-7 object-contain"
                onError={(e) => { e.target.src = "/logo-sistema.png"; }}
              />
            </div>
            
            {/* Título */}
            <div className="flex-1">
              <h1 
                className="text-base font-black tracking-wide"
                style={{ color: "white" }}
              >
                FARMACIA
              </h1>
              <p 
                className="text-[9px] tracking-[0.15em] uppercase"
                style={{ color: "rgba(255,255,255,0.6)" }}
              >
                Sistema Penitenciario
              </p>
            </div>
          </div>
        </div>

        {/* Perfil de Usuario - Compacto */}
        <div 
          className="mx-3 mt-3 mb-1 p-3 rounded-xl"
          style={{ 
            backgroundColor: "rgba(0,0,0,0.15)",
            backdropFilter: 'blur(10px)',
          }}
        >
          <div className="flex items-center gap-2.5">
            {/* Avatar con iniciales */}
            <div 
              className="relative w-10 h-10 rounded-lg flex items-center justify-center font-bold text-sm flex-shrink-0"
              style={{ 
                background: 'linear-gradient(135deg, rgba(255,255,255,0.25) 0%, rgba(255,255,255,0.1) 100%)',
                color: 'white',
                boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
              }}
            >
              {inicialesUsuario}
              {/* Indicador online */}
              <div 
                className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2"
                style={{ 
                  backgroundColor: '#10B981',
                  borderColor: 'var(--color-primary, #9F2241)',
                }}
              />
            </div>
            
            {/* Info usuario */}
            <div className="flex-1 min-w-0">
              <p 
                className="font-semibold text-[13px] truncate leading-tight"
                style={{ color: "white" }}
              >
                {nombreUsuario}
              </p>
              <p 
                className="text-[11px] truncate"
                style={{ color: "rgba(255,255,255,0.6)" }}
              >
                {user?.email}
              </p>
            </div>
            
            {/* Badge de rol - Inline */}
            <RolBadge rol={rolPrincipal} />
          </div>
        </div>

        {/* Navegación - Sin scroll */}
        <nav className="flex-1 px-2 py-1 overflow-y-auto">
          <div className="space-y-0.5">
            {visibleMenuItems.map((item) => (
              <MenuItem
                key={item.path || item.id}
                item={item}
                isActive={location.pathname === item.path}
                isExpanded={expandedMenus[item.id]}
                onToggle={toggleSubmenu}
                location={location}
                onClick={() => window.innerWidth < 1024 && setSidebarOpen(false)}
              />
            ))}
          </div>
        </nav>

        {/* Footer - Logout Compacto */}
        <div 
          className="p-3"
          style={{ 
            borderTop: "1px solid rgba(255,255,255,0.1)",
            background: 'rgba(0,0,0,0.08)',
          }}
        >
          <button
            onClick={handleLogout}
            disabled={loggingOut}
            className="
              w-full flex items-center justify-center gap-2 
              px-3 py-2.5 rounded-xl
              font-semibold text-[13px]
              transition-all duration-300
              disabled:opacity-50 disabled:cursor-not-allowed
            "
            style={{ 
              backgroundColor: loggingOut ? 'rgba(255,255,255,0.1)' : 'rgba(255,255,255,0.12)',
              color: 'white',
            }}
            onMouseEnter={(e) => !loggingOut && (e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.2)')}
            onMouseLeave={(e) => !loggingOut && (e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.12)')}
          >
            <FaSignOutAlt 
              size={15} 
              className={loggingOut ? 'animate-spin' : ''} 
            />
            <span>{loggingOut ? 'Cerrando...' : 'Cerrar Sesión'}</span>
          </button>
          
          {/* Versión */}
          <p 
            className="text-center text-[9px] mt-2"
            style={{ color: 'rgba(255,255,255,0.4)' }}
          >
            SIFP v2.0 • {new Date().getFullYear()}
          </p>
        </div>
      </aside>

      {/* ========== CONTENIDO PRINCIPAL ========== */}
      <div className={`flex-1 transition-all duration-500 min-h-screen flex flex-col ${sidebarOpen ? 'lg:ml-72' : 'ml-0'}`}>
        {/* Header - Fixed para que siempre esté visible */}
        <header 
          className={`fixed top-0 right-0 z-30 h-16 flex items-center px-4 sm:px-6 transition-all duration-500 ${sidebarOpen ? 'lg:left-72' : 'left-0'}`}
          style={{ 
            background: "linear-gradient(135deg, var(--color-header-bg, var(--color-primary, #9F2241)) 0%, var(--color-primary-hover, #6B1839) 100%)",
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
          }}
        >
          <div className="flex items-center justify-between w-full gap-4">
            {/* Izquierda: Menú hamburguesa + Título */}
            <div className="flex items-center gap-4 min-w-0">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="relative w-10 h-10 rounded-lg transition-all duration-300 hover:bg-white/15 flex items-center justify-center"
                style={{ color: 'var(--color-header-text, #FFFFFF)' }}
                title={sidebarOpen ? "Ocultar menú" : "Mostrar menú"}
              >
                {sidebarOpen ? (
                  /* Icono de flecha izquierda (ocultar) */
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
                  </svg>
                ) : (
                  /* Icono de menú hamburguesa */
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                  </svg>
                )}
              </button>
              
              {/* Título del sistema */}
              <div className="hidden sm:block min-w-0">
                <h1
                  className="text-sm md:text-base font-semibold truncate tracking-wide"
                  style={{ color: 'var(--color-header-text, #FFFFFF)' }}
                >
                  {nombreSistema || "Sistema de Farmacia Penitenciaria"}
                </h1>
              </div>
            </div>
            
            {/* Derecha: Acciones */}
            <div className="flex items-center gap-3">
              {/* Notificaciones */}
              <NotificacionesBell 
                externalCount={unreadCount} 
                onCountChange={handleNotificationCountChange}
              />
              
              {/* Badge desarrollo */}
              {DEV_CONFIG?.ENABLED && (
                <span
                  className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold"
                  style={{ 
                    background: "linear-gradient(135deg, #14B8A6 0%, #0D9488 100%)",
                    color: 'var(--color-header-text, #FFFFFF)',
                  }}
                >
                  <span className="w-2 h-2 rounded-full bg-white animate-pulse" />
                  DEV
                </span>
              )}
              
              {/* Avatar mini en móvil */}
              <button 
                onClick={() => navigate('/perfil')}
                className="lg:hidden w-9 h-9 rounded-full flex items-center justify-center font-bold text-xs border-2 transition-all"
                style={{ 
                  backgroundColor: 'rgba(255,255,255,0.15)',
                  color: 'var(--color-header-text, #FFFFFF)',
                  borderColor: 'rgba(255,255,255,0.3)',
                }}
                onMouseEnter={(e) => e.currentTarget.style.borderColor = 'rgba(255,255,255,0.5)'}
                onMouseLeave={(e) => e.currentTarget.style.borderColor = 'rgba(255,255,255,0.3)'}
              >
                {inicialesUsuario}
              </button>
            </div>
          </div>
        </header>

        {/* Spacer para el header fijo */}
        <div className="h-16 flex-shrink-0" />

        {/* Main Content */}
        <main 
          className="flex-1 p-4 sm:p-6 lg:p-8 w-full max-w-full overflow-x-hidden"
          style={{ backgroundColor: "var(--color-background, #F8FAFC)" }}
        >
          <div className="w-full max-w-full">
            <Outlet />
          </div>
        </main>
        
        {/* Footer minimalista */}
        <footer 
          className="py-3 px-6 text-center text-xs"
          style={{ 
            color: 'var(--color-text-secondary, #9CA3AF)',
            borderTop: '1px solid var(--color-border, #E5E7EB)',
          }}
        >
          © {new Date().getFullYear()} Sistema de Inventario Farmacéutico Penitenciario
        </footer>
      </div>

      {/* Overlay móvil */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-30 lg:hidden transition-opacity duration-300"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      
      {/* Indicador de estado de conexión - aparece cuando hay problemas */}
      <ConnectionIndicator />
      
      {/* Estilos del scrollbar personalizado */}
      <style>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(255,255,255,0.2);
          border-radius: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(255,255,255,0.3);
        }
      `}</style>
    </div>
  );
}

export default Layout;
