import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { FaUser, FaLock, FaSignInAlt, FaSpinner, FaEye, FaEyeSlash, FaServer } from 'react-icons/fa';
import { authAPI, checkApiHealth } from '../services/api';
import { usePermissions } from '../hooks/usePermissions';
import { useTheme } from '../hooks/useTheme';
import { setAccessToken, clearTokens } from '../services/tokenManager';

function Login() {
  const [credentials, setCredentials] = useState({ username: '', password: '' });
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [serverWaking, setServerWaking] = useState(false);
  const [serverReady, setServerReady] = useState(null); // null = no verificado, true = listo, false = no disponible
  const [wakingProgress, setWakingProgress] = useState(0);
  const navigate = useNavigate();
  const { recargarUsuario } = usePermissions();
  const { temaGlobal, logoLoginUrl, nombreSistema } = useTheme();

  // Pre-verificar si el servidor está disponible al cargar el login
  useEffect(() => {
    let mounted = true;
    let progressInterval = null;
    
    const warmupServer = async () => {
      // Simular progreso mientras el servidor despierta
      progressInterval = setInterval(() => {
        if (mounted) {
          setWakingProgress(prev => Math.min(prev + Math.random() * 15, 90));
        }
      }, 500);
      
      try {
        const result = await checkApiHealth({ retries: 2 });
        if (mounted) {
          setServerReady(result.healthy);
          setServerWaking(false);
          setWakingProgress(100);
          if (!result.healthy && result.isServerStarting) {
            // El servidor está iniciando, intentar de nuevo en unos segundos
            setTimeout(warmupServer, 3000);
          }
        }
      } catch {
        if (mounted) {
          // En caso de error, asumir que el servidor está iniciando
          setServerReady(false);
          setServerWaking(true);
          // Reintentar después de un tiempo
          setTimeout(warmupServer, 5000);
        }
      } finally {
        if (progressInterval) clearInterval(progressInterval);
      }
    };

    warmupServer();
    
    return () => {
      mounted = false;
      if (progressInterval) clearInterval(progressInterval);
    };
  }, []);

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
  const performLogin = async (creds, maxRetries = 4) => {
    let lastError = null;
    
    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        if (attempt > 0) {
          // Mostrar UI de servidor despertando en lugar de mensaje de error
          setServerWaking(true);
          setErrorMessage('');
          setWakingProgress(Math.min(30 + (attempt * 20), 85));
          await sleep(2000 * attempt); // Backoff: 2s, 4s, 6s, 8s
        }
        const result = await loginWithBackend(creds);
        setServerWaking(false);
        setServerReady(true);
        return result;
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
          setServerWaking(false);
          throw error;
        }
        
        // En el último intento, propagar el error
        if (attempt === maxRetries - 1) {
          setServerWaking(false);
          throw error;
        }
        
        console.warn(`[Login] Intento ${attempt + 1} fallido, reintentando...`, error.message);
      }
    }
    
    setServerWaking(false);
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
        toast.error('Credenciales inválidas');
      } else if (error.response?.status === 404) {
        setErrorMessage('Usuario o contraseña incorrectos');
        toast.error('Credenciales inválidas');
      } else if (error.response?.data?.non_field_errors) {
        setErrorMessage(error.response.data.non_field_errors[0]);
        toast.error('No fue posible iniciar sesión');
      } else if (error.response?.data?.detail) {
        setErrorMessage(error.response.data.detail);
        toast.error('No fue posible iniciar sesión');
      } else if (!error.response) {
        // Error de red - probablemente el servidor está despertando
        setServerWaking(true);
        setErrorMessage('');
        // Esperar un momento y marcar como que el servidor no está disponible
        setTimeout(() => {
          setServerWaking(false);
          setServerReady(false);
        }, 3000);
        toast.error('El servidor está iniciando, intenta de nuevo');
      } else {
        setErrorMessage('Error al conectar con el servidor');
        toast.error('No fue posible iniciar sesión');
      }
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
          {/* Indicador de servidor despertando */}
          {serverWaking && (
            <div className="mb-5 rounded-xl bg-amber-50 border border-amber-200 p-4 text-center animate-pulse">
              <div className="flex items-center justify-center gap-3 mb-2">
                <FaServer className="text-amber-600 text-xl animate-bounce" />
                <span className="font-semibold text-amber-800">Servidor iniciando...</span>
              </div>
              <p className="text-sm text-amber-700 mb-3">
                El servidor está despertando. Esto puede tomar hasta 60 segundos en servicios gratuitos.
              </p>
              {/* Barra de progreso animada */}
              <div className="w-full bg-amber-200 rounded-full h-2 overflow-hidden">
                <div 
                  className="bg-amber-500 h-2 rounded-full transition-all duration-500 ease-out"
                  style={{ width: `${wakingProgress}%` }}
                />
              </div>
              <p className="text-xs text-amber-600 mt-2">Por favor espera...</p>
            </div>
          )}

          {/* Indicador de servidor no disponible */}
          {serverReady === false && !serverWaking && (
            <div className="mb-5 rounded-xl bg-orange-50 border border-orange-200 p-4 text-center">
              <div className="flex items-center justify-center gap-2 mb-2">
                <FaServer className="text-orange-600" />
                <span className="font-medium text-orange-800">Servidor en espera</span>
              </div>
              <p className="text-sm text-orange-700">
                El servidor puede tardar unos segundos en responder. 
                Puedes intentar iniciar sesión normalmente.
              </p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {errorMessage && !serverWaking && (
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
                  type={showPassword ? "text" : "password"}
                  value={credentials.password}
                  onChange={(e) => setCredentials({ ...credentials, password: e.target.value })}
                  className="w-full pl-12 pr-12 py-3.5 border-2 border-gray-200 rounded-xl transition-all focus:border-transparent focus:ring-4 focus:outline-none"
                  style={{ '--tw-ring-color': 'rgba(159, 34, 65, 0.2)' }}
                  placeholder="Ingrese su contraseña"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-4 text-gray-400 hover:text-gray-600"
                  tabIndex={-1}
                >
                  {showPassword ? <FaEyeSlash size={18} /> : <FaEye size={18} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || serverWaking}
              className="w-full text-white py-4 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 font-bold shadow-xl transition-all transform hover:scale-105 hover:shadow-2xl active:scale-95"
              style={{ background: 'linear-gradient(135deg, var(--color-primary, #9F2241) 0%, var(--color-primary-hover, #6B1839) 100%)' }}
            >
              {loading || serverWaking ? (
                <>
                  <FaSpinner className="animate-spin" />
                  {serverWaking ? 'Conectando con servidor...' : 'Iniciando sesión...'}
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
