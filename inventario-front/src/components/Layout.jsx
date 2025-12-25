import { useEffect, useState } from "react";
import { Outlet, Link, useLocation, useNavigate } from "react-router-dom";
import { usePermissions } from "../hooks/usePermissions";
import { useTheme } from "../hooks/useTheme";
import { DEV_CONFIG } from "../config/dev";
import NotificacionesBell from "./NotificacionesBell";
import ConnectionIndicator from "./ConnectionIndicator";
import { notificacionesAPI, authAPI } from "../services/api";
import { clearTokens, setLogoutInProgress } from "../services/tokenManager";
import {
  FaHome,
  FaBox,
  FaWarehouse,
  FaClipboardList,
  FaBuilding,
  FaUsers,
  FaChartBar,
  FaHistory,
  FaUserCircle,
  FaBars,
  FaTimes,
  FaSignOutAlt,
  FaExchangeAlt,
  FaBell,
  FaIdBadge,
  FaPalette,
  FaGift,
} from "react-icons/fa";

function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loggingOut, setLoggingOut] = useState(false); // Estado para evitar clics múltiples en logout
  const location = useLocation();
  const navigate = useNavigate();
  const { user, permisos, getRolPrincipal } = usePermissions();
  const { temaGlobal, logoHeaderUrl, nombreSistema } = useTheme();

  // Verificar permiso de notificaciones para centralizar conteo
  const tienePermisoNotificaciones = permisos?.verNotificaciones;

  const handleLogout = async () => {
    // Evitar múltiples clics durante el logout
    if (loggingOut) return;
    setLoggingOut(true);
    
    // ISS-003 FIX: Marcar logout en progreso ANTES de cualquier operación
    // Esto previene que otros componentes intenten refresh mientras se cierra sesión
    setLogoutInProgress(true);
    
    let navegacionExitosa = false;
    try {
      // El refresh token está en cookie HttpOnly, no necesitamos enviarlo
      await authAPI.logout();
    } catch (err) {
      // Ignorar errores de logout - siempre limpiar sesión local
      // El backend retorna 200 incluso si el token es inválido
    } finally {
      // Limpiar timers de polling
      if (window.notificationInterval) {
        clearInterval(window.notificationInterval);
        window.notificationInterval = null;
      }
      // Limpiar token en memoria del tokenManager
      clearTokens();
      
      // ISS-003 FIX: Limpiar TODOS los datos locales relacionados con la sesión
      const keysToRemove = [
        'user',                    // Datos de usuario
        'sifp_tema_cache',         // Cache de tema
        'sifp_tema_updated_at',    // Timestamp de tema
        'session_uid',             // ID de sesión
        'session_role',            // Rol de sesión
        'session_hash',            // Hash de sesión
      ];
      keysToRemove.forEach(key => {
        try {
          localStorage.removeItem(key);
          sessionStorage.removeItem(key);
        } catch (_) { /* Ignorar errores de storage */ }
      });
      
      try {
        navigate("/login");
        navegacionExitosa = true;
      } catch (navError) {
        // Si la navegación falla, forzar recarga
        try {
          window.location.href = "/login";
          navegacionExitosa = true;
        } catch (fallbackError) {
          // Silenciar - no hay más opciones
        }
      }
      // Resetear loggingOut solo si la navegación falló completamente
      if (!navegacionExitosa) {
        setLoggingOut(false);
      }
    }
  };

  const menuItems = [
    { path: "/dashboard", icon: FaHome, label: "Dashboard", permission: "verDashboard" },
    { path: "/productos", icon: FaBox, label: "Productos", permission: "verProductos" },
    { path: "/lotes", icon: FaWarehouse, label: "Lotes", permission: "verLotes" },
    { path: "/requisiciones", icon: FaClipboardList, label: "Requisiciones", permission: "verRequisiciones" },
    { path: "/donaciones", icon: FaGift, label: "Donaciones", permission: "verDonaciones" },
    { path: "/movimientos", icon: FaExchangeAlt, label: "Movimientos", permission: "verMovimientos" },
    { path: "/centros", icon: FaBuilding, label: "Centros", permission: "verCentros" },
    { path: "/usuarios", icon: FaUsers, label: "Usuarios", permission: "verUsuarios" },
    { path: "/reportes", icon: FaChartBar, label: "Reportes", permission: "verReportes" },
    { path: "/trazabilidad", icon: FaHistory, label: "Trazabilidad", permission: "verTrazabilidad" },
    { path: "/notificaciones", icon: FaBell, label: "Notificaciones", permission: "verNotificaciones", badge: unreadCount },
    { path: "/perfil", icon: FaIdBadge, label: "Perfil", permission: "verPerfil" },
    { path: "/configuracion-tema", icon: FaPalette, label: "Personalizar Tema", permission: "configurarTema" },
  ];

  // ISS-009 FIX: NO mostrar menús sensibles durante validación pendiente
  // Solo mostrar perfil mientras se valida con backend para prevenir escalación de privilegios
  const isValidating = permisos?._isValidating || permisos?._source === 'pending_validation';
  const visibleMenuItems = isValidating 
    ? menuItems.filter(item => item.path === "/perfil") // Solo perfil durante validación
    : menuItems.filter((item) => !item.permission || permisos[item.permission]);

  useEffect(() => {
    setSidebarOpen(window.innerWidth >= 1024);
  }, []);

  // Centralizar conteo de notificaciones con validación de permisos
  // NotificacionesBell usará este contador via props para evitar doble polling
  useEffect(() => {
    const cargarUnread = async () => {
      try {
        const res = await notificacionesAPI.noLeidasCount();
        // ISS-003 FIX: Validar formato de respuesta y loguear discrepancias
        const data = res.data;
        let total = 0;
        
        // Priorizar campos en orden de preferencia
        if (typeof data?.no_leidas === 'number') {
          total = data.no_leidas;
        } else if (typeof data?.total === 'number') {
          total = data.total;
          // Log de discrepancia en desarrollo
          if (import.meta.env.DEV) {
            console.info('[Layout] Notificaciones: usando campo "total" en lugar de "no_leidas"');
          }
        } else if (typeof data?.count === 'number') {
          total = data.count;
          if (import.meta.env.DEV) {
            console.info('[Layout] Notificaciones: usando campo "count" en lugar de "no_leidas"');
          }
        } else if (typeof data === 'number') {
          // Backend puede retornar número directo
          total = data;
        } else if (import.meta.env.DEV) {
          console.warn('[Layout] Formato de respuesta de notificaciones no reconocido:', data);
        }
        
        setUnreadCount(Math.max(0, total));
      } catch (error) {
        // ISS-003 FIX: Mostrar error explícito en desarrollo
        if (import.meta.env.DEV && error?.response?.status !== 401) {
          console.warn('[Layout] Error cargando notificaciones:', error.message);
        }
        // Mantener contador anterior en caso de error temporal
      }
    };
    // Solo cargar si tiene usuario Y permiso de ver notificaciones
    if (user && tienePermisoNotificaciones) {
      cargarUnread();
      const id = setInterval(cargarUnread, 30000);
      // Guardar referencia para limpieza en logout
      window.notificationInterval = id;
      return () => {
        clearInterval(id);
        window.notificationInterval = null;
      };
    } else {
      // Sin permiso, resetear contador
      setUnreadCount(0);
    }
  }, [user, tienePermisoNotificaciones]);

  // Callback para que NotificacionesBell notifique cambios de contador
  const handleNotificationCountChange = (count) => {
    setUnreadCount(count);
  };

  return (
    <div className="min-h-screen" style={{ backgroundColor: "var(--color-background, #F5F5F5)" }}>
      <aside
        className={`fixed top-0 left-0 z-40 h-screen shadow-lg transition-transform ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        } w-64 lg:translate-x-0 flex flex-col`}
        style={{ background: "var(--color-sidebar-bg, linear-gradient(180deg, #9F2241 0%, #6B1839 100%))" }}
      >
        {/* Header del Sidebar - Logo y Título integrados */}
        <div
          className="flex items-center justify-between px-4 h-[72px]"
          style={{ borderBottom: "1px solid rgba(255,255,255,0.15)" }}
        >
          <div className="flex items-center gap-3">
            <img 
              src={logoHeaderUrl || "/logo-sistema.png"} 
              alt="Logo" 
              className="h-9 w-9 object-contain"
              onError={(e) => { e.target.src = "/logo-sistema.png"; }}
            />
            <div className="leading-none">
              <span className="font-bold text-[15px] tracking-wide" style={{ color: "var(--color-sidebar-text, #FFFFFF)" }}>FARMACIA</span>
              <span className="block text-[9px] tracking-widest mt-0.5" style={{ color: "var(--color-sidebar-text, #FFFFFF)", opacity: 0.7 }}>SISTEMA PENITENCIARIO</span>
            </div>
          </div>
          <button onClick={() => setSidebarOpen(false)} className="lg:hidden text-white/70 hover:text-white transition-colors">
            <FaTimes size={18} />
          </button>
        </div>

        {/* Perfil de Usuario - Compacto y elegante */}
        <div
          className="px-4 py-3 border-b"
          style={{ borderBottomColor: "rgba(255,255,255,0.15)", backgroundColor: "rgba(0,0,0,0.1)" }}
        >
          <div className="flex items-center gap-3">
            <div className="bg-white/90 rounded-full p-1.5 shadow-sm">
              <FaUserCircle className="text-2xl" style={{ color: "var(--color-primary, #9F2241)" }} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-white truncate leading-tight">
                {user?.first_name} {user?.last_name}
              </p>
              <p className="text-[11px] truncate" style={{ color: "rgba(255,255,255,0.7)" }}>{user?.email}</p>
            </div>
            <span
              className="px-2 py-0.5 text-[10px] rounded font-bold uppercase tracking-wide"
              style={{ backgroundColor: "rgba(255,255,255,0.2)", color: "white" }}
            >
              {getRolPrincipal()}
            </span>
          </div>
        </div>

        <nav className="p-4 space-y-1 overflow-y-auto flex-1">
          {visibleMenuItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;

            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setSidebarOpen(false)}
                className="flex items-center gap-3 px-4 py-3 rounded-lg transition-all"
                style={{
                  backgroundColor: isActive ? "rgba(255,255,255,0.15)" : "transparent",
                  color: "white",
                  fontWeight: isActive ? "600" : "400",
                  borderLeft: isActive ? "3px solid white" : "3px solid transparent",
                }}
                onMouseEnter={(e) => {
                  if (!isActive) e.currentTarget.style.backgroundColor = "rgba(255,255,255,0.08)";
                }}
                onMouseLeave={(e) => {
                  if (!isActive) e.currentTarget.style.backgroundColor = "transparent";
                }}
              >
                <Icon size={18} />
                <span className="text-sm flex-1">{item.label}</span>
                {item.badge > 0 && (
                  <span 
                    className="ml-auto inline-flex items-center justify-center px-2 py-0.5 text-xs font-bold bg-white rounded-full min-w-[24px]"
                    style={{ color: "var(--color-primary, #9F2241)" }}
                  >
                    {item.badge > 99 ? "99+" : item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Botón de Logout - Siempre visible al final del sidebar */}
        <div
          className="p-4 border-t mt-auto"
          style={{ borderTopColor: "rgba(255,255,255,0.2)", backgroundColor: "rgba(0,0,0,0.1)" }}
        >
          <button
            onClick={handleLogout}
            disabled={loggingOut}
            className="w-full flex items-center justify-center gap-3 px-4 py-3 rounded-lg text-white font-bold transition-all disabled:opacity-60 disabled:cursor-not-allowed"
            style={{ backgroundColor: "rgba(255,255,255,0.15)" }}
            onMouseEnter={(e) => !loggingOut && (e.currentTarget.style.backgroundColor = "rgba(255,255,255,0.25)")}
            onMouseLeave={(e) => !loggingOut && (e.currentTarget.style.backgroundColor = "rgba(255,255,255,0.15)")}
          >
            <FaSignOutAlt size={20} className={loggingOut ? 'animate-pulse' : ''} />
            <span>{loggingOut ? 'Cerrando...' : 'Cerrar Sesión'}</span>
          </button>
        </div>
      </aside>

      <div className="transition-all min-h-screen flex flex-col lg:ml-64">
        <header 
          className="shadow-sm sticky top-0 z-30 h-[72px] flex items-center" 
          style={{ 
            background: "linear-gradient(135deg, var(--color-header-bg, var(--color-primary, #9F2241)) 0%, var(--color-primary-hover, #6B1839) 100%)",
            borderBottom: "3px solid var(--color-primary-hover, #6B1839)" 
          }}
        >
          <div className="flex flex-wrap items-center justify-between gap-3 px-4 sm:px-6 w-full">
            <div className="flex items-center gap-3 sm:gap-4">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="transition-colors"
                style={{ color: "var(--color-header-text, #FFFFFF)" }}
                onMouseEnter={(e) => (e.currentTarget.style.opacity = "0.8")}
                onMouseLeave={(e) => (e.currentTarget.style.opacity = "1")}
              >
                <FaBars size={24} />
              </button>
              <h1
                className="text-sm sm:text-base md:text-lg font-bold leading-snug max-w-3xl"
                style={{ color: "var(--color-header-text, #FFFFFF)" }}
              >
                {nombreSistema || temaGlobal?.reporte_titulo_institucion || "SISTEMA DE FARMACIA PENITENCIARIA - GOBIERNO DEL ESTADO DE MEXICO"}
              </h1>
            </div>
            <div className="flex items-center gap-4">
              <NotificacionesBell 
                externalCount={unreadCount} 
                onCountChange={handleNotificationCountChange}
              />
              {DEV_CONFIG?.ENABLED && (
                <span
                  className="px-3 py-2 rounded-full text-xs sm:text-sm font-bold text-white whitespace-nowrap"
                  style={{ background: "linear-gradient(135deg, #14B8A6 0%, #0D9488 100%)" }}
                >
                  MODO DESARROLLO
                </span>
              )}
            </div>
          </div>
        </header>

        <main className="p-4 sm:p-6 lg:p-8 flex-1 w-full overflow-x-hidden">
          <Outlet />
        </main>
      </div>

      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-gray-900 bg-opacity-50 z-30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      
      {/* Indicador de estado de conexión - aparece cuando hay problemas */}
      <ConnectionIndicator />
    </div>
  );
}

export default Layout;
