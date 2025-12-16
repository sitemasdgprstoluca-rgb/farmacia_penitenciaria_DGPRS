import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { FaUser, FaLock, FaSignInAlt, FaSpinner } from 'react-icons/fa';
import { authAPI } from '../services/api';
import { usePermissions } from '../hooks/usePermissions';
import { useTheme } from '../hooks/useTheme';
import { setAccessToken, clearTokens } from '../services/tokenManager';

function Login() {
  const [credentials, setCredentials] = useState({ username: '', password: '' });
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const navigate = useNavigate();
  const { recargarUsuario } = usePermissions();
  const { temaGlobal, logoLoginUrl, nombreSistema } = useTheme();

  const persistSession = (user, accessToken) => {
    // ISS-009 FIX: NO persistir usuario completo en localStorage (manipulable)
    // Access token se guarda en memoria (tokenManager) para seguridad
    if (accessToken) {
      setAccessToken(accessToken);
    }
    // Refresh token se maneja automáticamente via cookie HttpOnly
    // NO guardar datos de usuario - PermissionProvider los cargará del backend
    // Esto previene que datos manipulados otorguen permisos en UI
  };

  const loginWithBackend = async (creds) => {
    const tokenResponse = await authAPI.login(creds);
    const { access, token, user } = tokenResponse.data;
    const accessToken = access || token;
    let userPayload = user || tokenResponse.data.usuario || null;

    if (!userPayload) {
      const meResponse = await authAPI.me();
      userPayload = meResponse.data;
    }

    persistSession(userPayload, accessToken);
    return userPayload;
  };

  // ISS-FIX: Helper para esperar entre reintentos
  const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

  // ISS-FIX: Login con reintentos automáticos para cold starts de Render
  const performLogin = async (creds, maxRetries = 3) => {
    let lastError = null;
    
    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        if (attempt > 0) {
          // Mostrar mensaje de reintento
          setErrorMessage(`Conectando con el servidor... (intento ${attempt + 1}/${maxRetries})`);
          await sleep(2000 * attempt); // Backoff: 2s, 4s, 6s
        }
        return await loginWithBackend(creds);
      } catch (error) {
        lastError = error;
        
        // Solo reintentar en errores de red/conexión (no en 401/400)
        const isNetworkError = !error.response || 
          error.code === 'ECONNABORTED' || 
          error.code === 'ERR_NETWORK' ||
          error.message?.includes('SSL') ||
          error.message?.includes('Network') ||
          error.message?.includes('timeout');
        
        if (!isNetworkError) {
          // Error de autenticación, no reintentar
          throw error;
        }
        
        // En el último intento, propagar el error
        if (attempt === maxRetries - 1) {
          throw error;
        }
        
        console.warn(`[Login] Intento ${attempt + 1} fallido, reintentando...`, error.message);
      }
    }
    
    throw lastError;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage('');
    setLoading(true);

    try {
      await performLogin(credentials);
      await recargarUsuario(); // Actualizar el contexto de permisos
      toast.success('Inicio de sesión exitoso');
      navigate('/dashboard');
    } catch (error) {
      // Limpiar tokens usando tokenManager (no localStorage directo)
      clearTokens();
      localStorage.removeItem('user');
      
      // Mensajes de error alineados con contratos de prueba
      if (error.response?.status === 401 || error.response?.status === 400) {
        setErrorMessage('Usuario o contraseña incorrectos');
      } else if (error.response?.status === 404) {
        setErrorMessage('Usuario o contraseña incorrectos');
      } else if (error.response?.data?.non_field_errors) {
        setErrorMessage(error.response.data.non_field_errors[0]);
      } else if (error.response?.data?.detail) {
        setErrorMessage(error.response.data.detail);
      } else if (error.message) {
        setErrorMessage('Error interno del servidor. El servicio puede estar iniciando, intente de nuevo en unos segundos.');
      } else {
        setErrorMessage('Usuario o contraseña incorrectos');
      }
      toast.error('No fue posible iniciar sesión');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen w-full flex items-center justify-center p-4 overflow-auto"
      style={{
        background: `linear-gradient(135deg, var(--color-primary, #9F2241) 0%, var(--color-primary-hover, #6B1839) 50%, ${temaGlobal?.color_primario_hover || '#4a0f26'} 100%)`,
      }}
    >
      <div className="max-w-md w-full mx-auto">
        <div className="text-center mb-6">
          {/* Logo del Sistema - Dinámico desde el tema */}
          <div className="inline-flex items-center justify-center mb-4">
            <img 
              src={logoLoginUrl || "/logo-sistema.png"} 
              alt="Logo del Sistema" 
              className="h-40 w-80 object-contain rounded-lg"
              onError={(e) => { e.target.src = "/logo-sistema.png"; }}
            />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">
            {nombreSistema || temaGlobal?.reporte_titulo_institucion || 'Sistema de Farmacia Penitenciaria'}
          </h1>
        </div>

        <div
          className="bg-white rounded-2xl shadow-2xl p-8 mb-6 border-t-4"
          style={{ borderTopColor: 'var(--color-primary, #9F2241)' }}
        >
          <form onSubmit={handleSubmit} className="space-y-5">
            {errorMessage && (
              <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-2 text-sm text-red-700">
                {errorMessage}
              </div>
            )}

            <div>
              <label className="block text-sm font-bold mb-2" style={{ color: 'var(--color-primary-hover, #6B1839)' }}>
                Usuario o correo
              </label>
              <div className="relative">
                <FaUser className="absolute left-4 top-4 text-gray-400" />
                <input
                  type="text"
                  value={credentials.username}
                  onChange={(e) => setCredentials({ ...credentials, username: e.target.value })}
                  className="w-full pl-12 pr-4 py-3.5 border-2 border-gray-200 rounded-xl transition-all focus:border-transparent focus:ring-4 focus:outline-none"
                  style={{ '--tw-ring-color': 'rgba(159, 34, 65, 0.2)' }}
                  placeholder="Ingrese su usuario o correo"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-bold mb-2 capitalize" style={{ color: 'var(--color-primary-hover, #6B1839)' }}>
                Contraseña
              </label>
              <div className="relative">
                <FaLock className="absolute left-4 top-4 text-gray-400" />
                <input
                  type="password"
                  value={credentials.password}
                  onChange={(e) => setCredentials({ ...credentials, password: e.target.value })}
                  className="w-full pl-12 pr-4 py-3.5 border-2 border-gray-200 rounded-xl transition-all focus:border-transparent focus:ring-4 focus:outline-none"
                  style={{ '--tw-ring-color': 'rgba(159, 34, 65, 0.2)' }}
                  placeholder="Ingrese su contraseña"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full text-white py-4 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 font-bold shadow-xl transition-all transform hover:scale-105 hover:shadow-2xl active:scale-95"
              style={{ background: 'linear-gradient(135deg, var(--color-primary, #9F2241) 0%, var(--color-primary-hover, #6B1839) 100%)' }}
            >
              {loading ? (
                <>
                  <FaSpinner className="animate-spin" />
                  Iniciando sesión...
                </>
              ) : (
                <>
                  <FaSignInAlt />
                  Iniciar sesión
                </>
              )}
            </button>

            <div className="text-center mt-4">
              <Link 
                to="/recuperar-password" 
                className="text-sm font-medium hover:underline transition-colors"
                style={{ color: 'var(--color-primary, #9F2241)' }}
              >
                ¿Olvidaste tu contraseña?
              </Link>
            </div>
          </form>
        </div>

        <div className="text-center mt-6 text-white text-sm space-y-1">
          <p className="font-bold text-base">{nombreSistema || 'Sistema Integral de Farmacia Penitenciaria'}</p>
          <p className="font-semibold">{temaGlobal?.reporte_subtitulo || 'Gobierno del Estado de México'}</p>
          <p className="text-xs" style={{ color: 'var(--color-sidebar-text, #FFFFFF)', opacity: 0.7 }}>
            {temaGlobal?.reporte_pie_pagina || 'Subsecretaría de Seguridad'} {temaGlobal?.reporte_ano_visible !== false ? '• 2025' : ''}
          </p>
        </div>
      </div>
    </div>
  );
}

export default Login;
