import { useEffect, useState } from "react";
import { Outlet, Link, useLocation, useNavigate } from "react-router-dom";
import { usePermissions } from "../hooks/usePermissions";
import { DEV_CONFIG } from "../config/dev";
import NotificacionesBell from "./NotificacionesBell";
import { notificacionesAPI, authAPI } from "../services/api";
import { clearTokens } from "../services/tokenManager";
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
  FaShieldAlt,
  FaExchangeAlt,
  FaBell,
  FaIdBadge,
  FaPalette,
} from "react-icons/fa";

function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loggingOut, setLoggingOut] = useState(false); // Estado para evitar clics múltiples en logout
  const location = useLocation();
  const navigate = useNavigate();
  const { user, permisos, getRolPrincipal } = usePermissions();

  // Verificar permiso de notificaciones para centralizar conteo
  const tienePermisoNotificaciones = permisos?.verNotificaciones;

  const handleLogout = async () => {
    // Evitar múltiples clics durante el logout
    if (loggingOut) return;
    setLoggingOut(true);
    
    let navegacionExitosa = false;
    try {
      const refresh = localStorage.getItem("refresh_token");
      await authAPI.logout({ refresh });
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
      localStorage.removeItem("token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("user");
      try {
        navigate("/login");
        navegacionExitosa = true;
      } catch (navError) {
        // Si la navegación falla por algún motivo, forzar recarga
        console.error("Error navegando al login:", navError);
        try {
          window.location.href = "/login";
          navegacionExitosa = true;
        } catch (fallbackError) {
          console.error("Error en fallback de navegación:", fallbackError);
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
    { path: "/movimientos", icon: FaExchangeAlt, label: "Movimientos", permission: "verMovimientos" },
    { path: "/centros", icon: FaBuilding, label: "Centros", permission: "verCentros" },
    { path: "/usuarios", icon: FaUsers, label: "Usuarios", permission: "verUsuarios" },
    { path: "/reportes", icon: FaChartBar, label: "Reportes", permission: "verReportes" },
    { path: "/trazabilidad", icon: FaHistory, label: "Trazabilidad", permission: "verTrazabilidad" },
    { path: "/notificaciones", icon: FaBell, label: "Notificaciones", permission: "verNotificaciones", badge: unreadCount },
    { path: "/perfil", icon: FaIdBadge, label: "Perfil", permission: "verPerfil" },
    { path: "/configuracion-tema", icon: FaPalette, label: "Personalizar Tema", permission: "configurarTema" },
  ];

  const visibleMenuItems = menuItems.filter((item) => !item.permission || permisos[item.permission]);

  useEffect(() => {
    setSidebarOpen(window.innerWidth >= 1024);
  }, []);

  // Centralizar conteo de notificaciones con validación de permisos
  // NotificacionesBell usará este contador via props para evitar doble polling
  useEffect(() => {
    const cargarUnread = async () => {
      try {
        const res = await notificacionesAPI.noLeidasCount();
        const total = res.data?.no_leidas ?? res.data?.total ?? res.data?.count ?? 0;
        setUnreadCount(total);
      } catch (_) {
        // Silenciar error de conteo de notificaciones
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
    <div className="min-h-screen bg-gray-50">
      <aside
        className={`fixed top-0 left-0 z-40 h-screen shadow-lg transition-transform ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        } w-64 lg:translate-x-0`}
        style={{ background: "var(--color-sidebar-bg, linear-gradient(180deg, #9F2241 0%, #6B1839 100%))" }}
      >
        <div
          className="flex items-center justify-between p-3 border-b"
          style={{ borderBottomColor: "rgba(255,255,255,0.2)" }}
        >
          <div className="flex items-center gap-3">
            <img 
              src="/logo-seguridad.jpg" 
              alt="Logo" 
              className="h-10 w-auto object-contain rounded"
            />
            <div>
              <span className="font-bold text-base text-white block leading-tight">FARMACIA</span>
              <span className="text-[10px] text-pink-100 leading-tight">SISTEMA PENITENCIARIO</span>
            </div>
          </div>
          <button onClick={() => setSidebarOpen(false)} className="lg:hidden text-white hover:text-pink-200">
            <FaTimes size={20} />
          </button>
        </div>

        <div
          className="p-4 border-b"
          style={{ borderBottomColor: "rgba(255,255,255,0.2)", backgroundColor: "rgba(255,255,255,0.1)" }}
        >
          <div className="flex items-center gap-3">
            <div className="bg-white rounded-full p-2">
              <FaUserCircle className="text-3xl" style={{ color: "var(--color-primary, #9F2241)" }} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-bold text-white truncate">
                {user?.first_name} {user?.last_name}
              </p>
              <p className="text-xs text-pink-100 truncate">{user?.email}</p>
              <span
                className="inline-block px-2 py-0.5 mt-1 text-xs rounded font-semibold"
                style={{ backgroundColor: "rgba(255,255,255,0.2)", color: "white" }}
              >
                {getRolPrincipal()}
              </span>
            </div>
          </div>
        </div>

        <nav className="p-4 space-y-1 overflow-y-auto h-[calc(100vh-200px)]">
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
                  <span className="ml-auto inline-flex items-center justify-center px-2 py-0.5 text-xs font-bold bg-white text-red-600 rounded-full min-w-[24px]">
                    {item.badge > 99 ? "99+" : item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        <div
          className="absolute bottom-0 left-0 right-0 p-4 border-t"
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
        <header className="bg-white shadow-sm sticky top-0 z-30" style={{ borderBottom: "3px solid var(--color-primary, #9F2241)" }}>
          <div className="flex flex-wrap items-center justify-between gap-3 px-4 sm:px-6 py-4">
            <div className="flex items-center gap-3 sm:gap-4">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="transition-colors"
                style={{ color: "var(--color-primary, #9F2241)" }}
                onMouseEnter={(e) => (e.currentTarget.style.color = "var(--color-primary-hover, #6B1839)")}
                onMouseLeave={(e) => (e.currentTarget.style.color = "var(--color-primary, #9F2241)")}
              >
                <FaBars size={24} />
              </button>
              <h1
                className="text-sm sm:text-base md:text-lg font-bold leading-snug max-w-3xl"
                style={{ color: "var(--color-primary-hover, #6B1839)" }}
              >
                SISTEMA DE FARMACIA PENITENCIARIA - GOBIERNO DEL ESTADO DE MEXICO
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
    </div>
  );
}

export default Layout;
