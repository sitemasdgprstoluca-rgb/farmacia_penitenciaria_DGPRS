import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { FaShieldAlt, FaUser, FaLock, FaSignInAlt, FaCode } from 'react-icons/fa';
import { DEV_CONFIG, devLog } from '../config/dev';
import { authAPI } from '../services/api';

function Login() {
  const [credentials, setCredentials] = useState({ username: '', password: '' });
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const navigate = useNavigate();

  const persistSession = (user, accessToken, refreshToken) => {
    localStorage.setItem('token', accessToken);
    if (refreshToken) {
      localStorage.setItem('refresh_token', refreshToken);
    }
    localStorage.setItem('user', JSON.stringify(user));
  };

  const startDevSession = (creds, reason = 'modo desarrollador') => {
    if (!DEV_CONFIG.AUTO_USER) {
      throw new Error('DEV_USER_NOT_CONFIGURED');
    }
    const simulatedUser = {
      ...DEV_CONFIG.AUTO_USER,
      groups:
        (DEV_CONFIG.AUTO_USER.groups && DEV_CONFIG.AUTO_USER.groups.length > 0)
          ? DEV_CONFIG.AUTO_USER.groups
          : (DEV_CONFIG.AUTO_USER.grupos || []).map((name) => (typeof name === 'string' ? { name } : name)),
    };
    devLog(`Inicio de sesion simulado (${reason})`, creds);
    persistSession(simulatedUser, 'dev-token', 'dev-refresh');
    return simulatedUser;
  };

  const loginWithBackend = async (creds) => {
    const tokenResponse = await authAPI.login(creds);
    const { access, refresh, token } = tokenResponse.data;
    const accessToken = access || token;
    if (accessToken) {
      localStorage.setItem('token', accessToken);
    }
    if (refresh) {
      localStorage.setItem('refresh_token', refresh);
    }
    const meResponse = await authAPI.me();
    persistSession(meResponse.data, accessToken, refresh);
    return meResponse.data;
  };

  const performLogin = async (creds, { useDevCredentials = false, allowDevMock = false } = {}) => {
    if (useDevCredentials && DEV_CONFIG.ENABLED) {
      try {
        const devCreds = DEV_CONFIG.CREDENTIALS || creds;
        return await loginWithBackend(devCreds);
      } catch (err) {
        if (allowDevMock) {
          return startDevSession(creds, 'fallback dev');
        }
        throw err;
      }
    }
    return loginWithBackend(creds);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage('');
    setLoading(true);

    try {
      await performLogin(credentials);
      toast.success('Inicio de sesion exitoso');
      navigate('/dashboard');
    } catch (error) {
      localStorage.removeItem('token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
      if (error.response?.status === 401 || error.response?.status === 400) {
        setErrorMessage('Usuario o contrasena incorrectos');
      } else if (error.response?.status === 404) {
        setErrorMessage('Usuario no existe');
      } else if (error.response?.data?.non_field_errors) {
        setErrorMessage(error.response.data.non_field_errors[0]);
      } else if (error.message === 'DEV_USER_NOT_CONFIGURED') {
        setErrorMessage('No existe un usuario de prueba configurado');
      } else {
        setErrorMessage('Error al iniciar sesion');
      }
      toast.error('No fue posible iniciar sesion');
    } finally {
      setLoading(false);
    }
  };

  const handleDevLogin = async () => {
    setLoading(true);
    setErrorMessage('');
    try {
      if (!DEV_CONFIG.ENABLED) {
        throw new Error('DEV_DISABLED');
      }
      await performLogin(DEV_CONFIG.CREDENTIALS, { useDevCredentials: true, allowDevMock: true });
      toast.success('Acceso de desarrollador habilitado');
      navigate('/dashboard');
    } catch (error) {
      if (error.message === 'DEV_USER_NOT_CONFIGURED') {
        setErrorMessage('Configura un usuario de prueba en src/config/dev.js');
      } else if (error.message === 'DEV_DISABLED') {
        setErrorMessage('El acceso de desarrollador no esta disponible en produccion');
      } else {
        setErrorMessage('No fue posible iniciar sesion como desarrollador');
      }
      toast.error('Error al iniciar sesion como desarrollador');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen w-full flex items-center justify-center p-4 overflow-auto"
      style={{
        background: 'linear-gradient(135deg, #9F2241 0%, #6B1839 50%, #4a0f26 100%)',
      }}
    >
      <div className="max-w-md w-full mx-auto">
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-white rounded-full mb-4 shadow-lg">
            <FaShieldAlt className="text-4xl" style={{ color: '#9F2241' }} />
          </div>
          <h1 className="text-4xl font-bold text-white mb-2">Sistema de Farmacia</h1>
          <p className="text-lg text-pink-100">Control de Abasto Penitenciario</p>
          <p className="text-white text-base mt-2 font-medium">Subsecretaria de Seguridad</p>
        </div>

        <div
          className="bg-white rounded-2xl shadow-2xl p-8 mb-6 border-t-4"
          style={{ borderTopColor: '#9F2241' }}
        >
          <form onSubmit={handleSubmit} className="space-y-5">
            {errorMessage && (
              <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-2 text-sm text-red-700">
                {errorMessage}
              </div>
            )}

            <div>
              <label className="block text-sm font-bold mb-2" style={{ color: '#6B1839' }}>
                Usuario
              </label>
              <div className="relative">
                <FaUser className="absolute left-4 top-4 text-gray-400" />
                <input
                  type="text"
                  value={credentials.username}
                  onChange={(e) => setCredentials({ ...credentials, username: e.target.value })}
                  className="w-full pl-12 pr-4 py-3.5 border-2 border-gray-200 rounded-xl transition-all focus:border-transparent focus:ring-4 focus:outline-none"
                  style={{ '--tw-ring-color': 'rgba(159, 34, 65, 0.2)' }}
                  placeholder="Ingrese su usuario"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-bold mb-2 capitalize" style={{ color: '#6B1839' }}>
                Contrasena
              </label>
              <div className="relative">
                <FaLock className="absolute left-4 top-4 text-gray-400" />
                <input
                  type="password"
                  value={credentials.password}
                  onChange={(e) => setCredentials({ ...credentials, password: e.target.value })}
                  className="w-full pl-12 pr-4 py-3.5 border-2 border-gray-200 rounded-xl transition-all focus:border-transparent focus:ring-4 focus:outline-none"
                  style={{ '--tw-ring-color': 'rgba(159, 34, 65, 0.2)' }}
                  placeholder="Ingrese su contrasena"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full text-white py-4 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 font-bold shadow-xl transition-all transform hover:scale-105 hover:shadow-2xl active:scale-95"
              style={{ background: 'linear-gradient(135deg, #9F2241 0%, #6B1839 100%)' }}
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white" />
                  Iniciando sesion...
                </>
              ) : (
                <>
                  <FaSignInAlt />
                  Iniciar sesion
                </>
              )}
            </button>
          </form>

          {DEV_CONFIG.ENABLED && (
            <div className="mt-6 pt-6 border-t-2 border-gray-100">
              <button
                onClick={handleDevLogin}
                disabled={loading}
                className="w-full bg-gradient-to-r from-gray-600 to-gray-700 text-white py-3.5 rounded-xl hover:from-gray-700 hover:to-gray-800 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 font-bold shadow-lg transition-all transform hover:scale-105 active:scale-95"
              >
                <FaCode />
                Acceso Desarrollador
              </button>
              <p className="text-xs text-gray-500 text-center mt-3 font-medium">
                Solo para configuracion inicial del sistema
              </p>
            </div>
          )}
        </div>

        <div className="text-center mt-6 text-white text-sm space-y-1">
          <p className="font-bold text-base">Sistema de Control de Abasto</p>
          <p className="font-semibold">Subsecretaria de Seguridad</p>
          <p className="text-xs text-pink-100">Gobierno del Estado de México • 2025</p>
        </div>
      </div>
    </div>
  );
}

export default Login;









