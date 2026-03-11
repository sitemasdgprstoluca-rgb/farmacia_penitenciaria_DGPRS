/**
 * Layout Principal - Sistema de Farmacia Penitenciaria
 * 
 * Diseño moderno tipo SaaS con:
 * - Sidebar blanco colapsable con iconos modernos
 * - Header blanco minimalista con separación sutil
 * - Navegación basada en permisos de usuario
 * - Micro-interacciones y transiciones elegantes
 * - Colores institucionales en estados activos
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
 * Ítem del menú - Diseño limpio tipo SaaS
 * Soporta submenús expandibles y modo colapsado (solo icono)
 */
const MenuItem = ({ item, isActive, onClick, isExpanded, onToggle, location, collapsed }) => {
  const Icon = item.icon;
  const hasSubItems = item.subItems && item.subItems.length > 0;
  
  if (hasSubItems) {
    const isSubActive = item.subItems.some(sub => location?.pathname === sub.path);
    
    return (
      <div>
        <button
          onClick={() => onToggle && onToggle(item.id)}
          className={`
            w-full group relative flex items-center gap-3 rounded-lg transition-all duration-200
            ${collapsed ? 'px-0 py-2 justify-center' : 'px-3 py-2'}
            ${isSubActive 
              ? 'bg-[var(--color-primary-light,rgba(147,32,67,0.1))] text-[var(--color-primary,#932043)]' 
              : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'}
          `}
          title={collapsed ? item.label : undefined}
        >
          {/* Barra indicadora activa */}
          {isSubActive && (
            <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full bg-[var(--color-primary,#932043)]" />
          )}
          
          <div className={`flex items-center justify-center w-8 h-8 rounded-lg flex-shrink-0 transition-colors duration-200
            ${isSubActive ? 'bg-[var(--color-primary,#932043)] text-white' : 'text-gray-400 group-hover:text-gray-600'}`}>
            <Icon size={16} />
          </div>
          
          {!collapsed && (
            <>
              <span className={`flex-1 text-[13px] text-left transition-all duration-200 ${isSubActive ? 'font-semibold' : 'font-medium'}`}>
                {item.label}
              </span>
              <FaChevronDown 
                size={10} 
                className={`transition-transform duration-200 ${isSubActive ? 'text-[var(--color-primary,#932043)]' : 'text-gray-400'}`}
                style={{ transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)' }}
              />
            </>
          )}
        </button>
        
        {!collapsed && (
          <div 
            className="overflow-hidden transition-all duration-200"
            style={{ maxHeight: isExpanded ? `${item.subItems.length * 40}px` : '0', opacity: isExpanded ? 1 : 0 }}
          >
            <div className="ml-[22px] mt-0.5 space-y-0.5 border-l-2 border-gray-100 pl-3">
              {item.subItems.map((subItem) => {
                const SubIcon = subItem.icon;
                const isSubItemActive = location?.pathname === subItem.path;
                return (
                  <Link
                    key={subItem.path}
                    to={subItem.path}
                    onClick={onClick}
                    className={`
                      flex items-center gap-2.5 px-2.5 py-1.5 rounded-md transition-all duration-200 text-[13px]
                      ${isSubItemActive 
                        ? 'text-[var(--color-primary,#932043)] font-semibold bg-[var(--color-primary-light,rgba(147,32,67,0.08))]' 
                        : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50 font-medium'}
                    `}
                  >
                    <SubIcon size={13} className={isSubItemActive ? 'text-[var(--color-primary,#932043)]' : 'text-gray-400'} />
                    <span>{subItem.label}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        )}
      </div>
    );
  }
  
  return (
    <Link
      to={item.path}
      onClick={onClick}
      className={`
        group relative flex items-center gap-3 rounded-lg transition-all duration-200
        ${collapsed ? 'px-0 py-2 justify-center' : 'px-3 py-2'}
        ${isActive
          ? 'bg-[var(--color-primary-light,rgba(147,32,67,0.1))] text-[var(--color-primary,#932043)]'
          : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'}
      `}
      title={collapsed ? item.label : undefined}
    >
      {/* Barra indicadora activa */}
      {isActive && (
        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full bg-[var(--color-primary,#932043)]" />
      )}
      
      <div className={`flex items-center justify-center w-8 h-8 rounded-lg flex-shrink-0 transition-colors duration-200
        ${isActive ? 'bg-[var(--color-primary,#932043)] text-white' : 'text-gray-400 group-hover:text-gray-600'}`}>
        <Icon size={16} />
      </div>
      
      {!collapsed && (
        <>
          <span className={`flex-1 text-[13px] transition-all duration-200 ${isActive ? 'font-semibold' : 'font-medium'}`}>
            {item.label}
          </span>
          
          {item.badge > 0 && (
            <span className="flex items-center justify-center min-w-[20px] h-5 px-1.5 text-[10px] font-bold rounded-full bg-red-500 text-white">
              {item.badge > 99 ? '99+' : item.badge}
            </span>
          )}
        </>
      )}
      
      {collapsed && item.badge > 0 && (
        <span className="absolute top-0.5 right-0.5 w-2 h-2 rounded-full bg-red-500" />
      )}
    </Link>
  );
};

/**
 * Badge de rol — estilo pill moderno
 */
const RolBadge = ({ rol }) => {
  const config = useMemo(() => {
    switch(rol?.toUpperCase()) {
      case 'ADMIN':
        return { icon: FaCrown, label: 'Admin', color: '#D97706', bg: '#FEF3C7' };
      case 'FARMACIA':
        return { icon: FaUserTie, label: 'Farmacia', color: '#059669', bg: '#D1FAE5' };
      case 'CENTRO':
        return { icon: FaBuilding, label: 'Centro', color: '#2563EB', bg: '#DBEAFE' };
      case 'VISTA':
        return { icon: FaEye, label: 'Vista', color: '#7C3AED', bg: '#EDE9FE' };
      default:
        return { icon: FaShieldAlt, label: rol || 'Usuario', color: '#6B7280', bg: '#F3F4F6' };
    }
  }, [rol]);
  
  const Icon = config.icon;
  
  return (
    <div 
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wide w-fit"
      style={{ color: config.color, backgroundColor: config.bg }}
    >
      <Icon size={9} />
      <span>{config.label}</span>
    </div>
  );
};

// ============================================================================
// COMPONENTE PRINCIPAL
// ============================================================================

function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
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
    // Panel Auditoría - Solo SUPER ADMIN
    { path: "/auditoria", icon: FaShieldAlt, label: "Auditoría", superAdminOnly: true },
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
    return menuItems.filter((item) => {
      // Items exclusivos de SUPER ADMIN
      if (item.superAdminOnly) {
        return user?.is_superuser === true;
      }
      // Items normales con permisos
      return !item.permission || permisos[item.permission];
    });
  }, [menuItems, isValidating, permisos, user]);

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

  const sidebarWidth = sidebarCollapsed ? 'w-[68px]' : 'w-64';
  const sidebarMargin = sidebarOpen ? (sidebarCollapsed ? 'lg:ml-[68px]' : 'lg:ml-64') : 'ml-0';

  return (
    <div className="min-h-screen flex" style={{ backgroundColor: "var(--color-background, #F8FAFC)" }}>
      {/* ========== SIDEBAR MODERNO ========== */}
      <aside
        className={`
          fixed top-0 left-0 z-40 h-screen
          transition-all duration-300 ease-out
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}
          ${sidebarWidth} flex flex-col
          bg-white border-r border-gray-200/80
        `}
        style={{ boxShadow: '1px 0 0 rgba(0,0,0,0.03)' }}
      >
        {/* Logo & Brand */}
        <div className={`flex items-center h-16 flex-shrink-0 border-b border-gray-100 ${sidebarCollapsed ? 'px-3 justify-center' : 'px-4 gap-3'}`}>
          <div 
            className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 overflow-hidden"
            style={{ backgroundColor: 'var(--color-primary, #932043)' }}
          >
            <img 
              src={logoHeaderUrl || "/logo-sistema.png"} 
              alt="Logo" 
              className="h-6 w-6 object-contain"
              onError={(e) => { e.target.src = "/logo-sistema.png"; }}
            />
          </div>
          {!sidebarCollapsed && (
            <div className="flex-1 min-w-0">
              <h1 className="text-sm font-bold text-gray-900 tracking-tight truncate">
                {nombreSistema || "SIFP"}
              </h1>
              <p className="text-[10px] text-gray-400 font-medium truncate">
                Sistema Penitenciario
              </p>
            </div>
          )}
          {/* Botón colapsar — solo desktop */}
          {!sidebarCollapsed && (
            <button
              onClick={() => setSidebarCollapsed(true)}
              className="hidden lg:flex w-7 h-7 items-center justify-center rounded-md hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors flex-shrink-0"
              title="Colapsar menú"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7" />
              </svg>
            </button>
          )}
          {sidebarCollapsed && (
            <button
              onClick={() => setSidebarCollapsed(false)}
              className="hidden lg:flex absolute -right-3 top-5 w-6 h-6 items-center justify-center rounded-full bg-white border border-gray-200 shadow-sm hover:bg-gray-50 text-gray-400 hover:text-gray-600 transition-colors z-50"
              title="Expandir menú"
            >
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7" />
              </svg>
            </button>
          )}
        </div>

        {/* Navegación */}
        <nav className={`flex-1 overflow-y-auto overflow-x-hidden py-3 ${sidebarCollapsed ? 'px-2' : 'px-3'} layout-scrollbar`}>
          {!sidebarCollapsed && (
            <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-2 px-3">Menú</p>
          )}
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
                collapsed={sidebarCollapsed}
              />
            ))}
          </div>
        </nav>

        {/* Perfil + Logout — Footer */}
        <div className="flex-shrink-0 border-t border-gray-100">
          {/* Perfil */}
          <div className={`${sidebarCollapsed ? 'p-2 flex justify-center' : 'px-3 py-3'}`}>
            {sidebarCollapsed ? (
              <button
                onClick={() => navigate('/perfil')}
                className="w-9 h-9 rounded-lg flex items-center justify-center text-xs font-bold flex-shrink-0 transition-colors hover:ring-2 hover:ring-gray-200"
                style={{ backgroundColor: 'var(--color-primary-light, rgba(147,32,67,0.1))', color: 'var(--color-primary, #932043)' }}
                title={nombreUsuario}
              >
                {inicialesUsuario}
              </button>
            ) : (
              <div className="flex items-center gap-2.5">
                <button
                  onClick={() => navigate('/perfil')}
                  className="w-9 h-9 rounded-lg flex items-center justify-center text-xs font-bold flex-shrink-0 transition-colors hover:ring-2 hover:ring-gray-200"
                  style={{ backgroundColor: 'var(--color-primary-light, rgba(147,32,67,0.1))', color: 'var(--color-primary, #932043)' }}
                >
                  {inicialesUsuario}
                </button>
                <div className="flex-1 min-w-0">
                  <p className="text-[13px] font-semibold text-gray-800 truncate">{nombreUsuario}</p>
                  <RolBadge rol={rolPrincipal} />
                </div>
              </div>
            )}
          </div>
          
          {/* Logout */}
          <div className={`border-t border-gray-100 ${sidebarCollapsed ? 'p-2' : 'px-3 py-2'}`}>
            <button
              onClick={handleLogout}
              disabled={loggingOut}
              className={`
                flex items-center gap-2 rounded-lg transition-all duration-200
                text-gray-500 hover:text-red-600 hover:bg-red-50
                disabled:opacity-50 disabled:cursor-not-allowed
                ${sidebarCollapsed ? 'w-full justify-center p-2' : 'w-full px-3 py-2 text-[13px] font-medium'}
              `}
              title={sidebarCollapsed ? (loggingOut ? 'Cerrando...' : 'Cerrar Sesión') : undefined}
            >
              <FaSignOutAlt size={14} className={loggingOut ? 'animate-spin' : ''} />
              {!sidebarCollapsed && <span>{loggingOut ? 'Cerrando...' : 'Cerrar Sesión'}</span>}
            </button>
          </div>
        </div>
      </aside>

      {/* ========== CONTENIDO PRINCIPAL ========== */}
      <div className={`flex-1 transition-all duration-300 min-h-screen flex flex-col ${sidebarMargin}`}>
        {/* Header Moderno — Blanco, minimalista */}
        <header 
          className={`fixed top-0 right-0 z-30 h-14 flex items-center px-4 sm:px-6 bg-white border-b border-gray-200/80 transition-all duration-300
            ${sidebarOpen ? (sidebarCollapsed ? 'lg:left-[68px]' : 'lg:left-64') : 'left-0'}`}
        >
          <div className="flex items-center justify-between w-full">
            {/* Izquierda: Toggle + Breadcrumb */}
            <div className="flex items-center gap-3 min-w-0">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="w-9 h-9 rounded-lg transition-colors duration-200 hover:bg-gray-100 flex items-center justify-center text-gray-500"
                title={sidebarOpen ? "Ocultar menú" : "Mostrar menú"}
              >
                {sidebarOpen ? (
                  <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25H12" />
                  </svg>
                ) : (
                  <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
                  </svg>
                )}
              </button>
              
              {/* Título de página */}
              <div className="hidden sm:flex items-center gap-2 min-w-0">
                <h2 className="text-sm font-semibold text-gray-800 truncate">
                  {nombreSistema || "Sistema de Farmacia Penitenciaria"}
                </h2>
              </div>
            </div>
            
            {/* Derecha: Acciones */}
            <div className="flex items-center gap-1.5">
              {/* Estado de conexión — siempre visible como dot */}
              
              {/* Badge desarrollo */}
              {DEV_CONFIG?.ENABLED && (
                <span className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10px] font-bold bg-teal-50 text-teal-700 border border-teal-200">
                  <span className="w-1.5 h-1.5 rounded-full bg-teal-500 animate-pulse" />
                  DEV
                </span>
              )}
              
              {/* Notificaciones */}
              <NotificacionesBell 
                externalCount={unreadCount} 
                onCountChange={handleNotificationCountChange}
              />
              
              {/* Avatar en header — solo móvil */}
              <button 
                onClick={() => navigate('/perfil')}
                className="lg:hidden w-8 h-8 rounded-lg flex items-center justify-center font-bold text-[11px] transition-all"
                style={{ 
                  backgroundColor: 'var(--color-primary-light, rgba(147,32,67,0.1))',
                  color: 'var(--color-primary, #932043)',
                }}
              >
                {inicialesUsuario}
              </button>
            </div>
          </div>
        </header>

        {/* Spacer para header fijo */}
        <div className="h-14 flex-shrink-0" />

        {/* Main Content */}
        <main 
          className="flex-1 p-4 sm:p-6 lg:p-8 w-full max-w-full overflow-x-hidden pb-20 lg:pb-8"
          style={{ backgroundColor: "var(--color-background, #F8FAFC)" }}
        >
          <div className="w-full max-w-full">
            <Outlet />
          </div>
        </main>
        
        {/* Footer */}
        <footer 
          className="hidden lg:block py-3 px-6 text-center text-[11px]"
          style={{ 
            color: 'var(--color-text-secondary, #9CA3AF)',
            borderTop: '1px solid var(--color-border, #E5E7EB)',
          }}
        >
          Sistema de Inventario Farmacéutico Penitenciario — v.2
        </footer>
      </div>

      {/* ========== BOTTOM NAVIGATION MÓVIL ========== */}
      <nav 
        className="fixed bottom-0 left-0 right-0 z-[100] lg:hidden flex items-center justify-around bg-white border-t border-gray-200"
        style={{
          paddingTop: '0.375rem',
          paddingBottom: 'max(0.375rem, env(safe-area-inset-bottom))',
          boxShadow: '0 -1px 3px rgba(0,0,0,0.05)',
        }}
      >
        <Link
          to="/dashboard"
          className={`flex flex-col items-center justify-center py-1 px-3 min-h-[48px] rounded-lg transition-all ${
            location.pathname === '/dashboard' 
              ? 'text-[var(--color-primary,#932043)]' 
              : 'text-gray-400'
          }`}
        >
          <FaHome size={20} />
          <span className="text-[10px] font-semibold mt-0.5">Inicio</span>
        </Link>
        
        {permisos?.verRequisiciones && (
          <Link
            to="/requisiciones"
            className={`flex flex-col items-center justify-center py-1 px-3 min-h-[48px] rounded-lg transition-all ${
              location.pathname === '/requisiciones' 
                ? 'text-[var(--color-primary,#932043)]' 
                : 'text-gray-400'
            }`}
          >
            <FaClipboardList size={20} />
            <span className="text-[10px] font-semibold mt-0.5">Requisiciones</span>
          </Link>
        )}
        
        {tienePermisoNotificaciones && (
          <Link
            to="/notificaciones"
            className={`relative flex flex-col items-center justify-center py-1 px-3 min-h-[48px] rounded-lg transition-all ${
              location.pathname === '/notificaciones' 
                ? 'text-[var(--color-primary,#932043)]' 
                : 'text-gray-400'
            }`}
          >
            <div className="relative">
              <FaBell size={20} />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1.5 flex items-center justify-center min-w-[16px] h-4 px-1 text-[9px] font-bold rounded-full bg-red-500 text-white">
                  {unreadCount > 99 ? '99+' : unreadCount}
                </span>
              )}
            </div>
            <span className="text-[10px] font-semibold mt-0.5">Alertas</span>
          </Link>
        )}
        
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className={`flex flex-col items-center justify-center py-1 px-3 min-h-[48px] rounded-lg transition-all ${
            sidebarOpen ? 'text-[var(--color-primary,#932043)]' : 'text-gray-400'
          }`}
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
          </svg>
          <span className="text-[10px] font-semibold mt-0.5">Menú</span>
        </button>
      </nav>

      {/* Overlay móvil */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/30 backdrop-blur-sm z-30 lg:hidden transition-opacity duration-300"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      
      <ConnectionIndicator />
      
      {/* Scrollbar styles para sidebar */}
      <style>{`
        .layout-scrollbar::-webkit-scrollbar {
          width: 3px;
        }
        .layout-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .layout-scrollbar::-webkit-scrollbar-thumb {
          background: #E5E7EB;
          border-radius: 3px;
        }
        .layout-scrollbar::-webkit-scrollbar-thumb:hover {
          background: #D1D5DB;
        }
      `}</style>
    </div>
  );
}

export default Layout;
