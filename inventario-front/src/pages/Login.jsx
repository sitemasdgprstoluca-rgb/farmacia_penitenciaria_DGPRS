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
    if (accessToken) {
      localStorage.setItem('token', accessToken);
    }
    if (refreshToken) {
      localStorage.setItem('refresh_token', refreshToken);
    }
    if (user) {
      localStorage.setItem('user', JSON.stringify(user));
    }
  };

  const loginWithBackend = async (creds) => {
    const tokenResponse = await authAPI.login(creds);
    const { access, refresh, token, user } = tokenResponse.data;
    const accessToken = access || token;
    let userPayload = user || tokenResponse.data.usuario || null;

    if (!userPayload) {
      const meResponse = await authAPI.me();
      userPayload = meResponse.data;
    }

    persistSession(userPayload, accessToken, refresh);
    return userPayload;
  };

  const performLogin = async (creds) => loginWithBackend(creds);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage('');
    setLoading(true);

    try {
      await performLogin(credentials);
      toast.success('Inicio de sesión exitoso');
      navigate('/dashboard');
    } catch (error) {
      localStorage.removeItem('token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
      if (error.response?.status === 401 || error.response?.status === 400) {
        setErrorMessage('Usuario o contraseña incorrectos');
      } else if (error.response?.status === 404) {
        setErrorMessage('Usuario no existe');
      } else if (error.response?.data?.non_field_errors) {
        setErrorMessage(error.response.data.non_field_errors[0]);
      } else {
        setErrorMessage('Error al iniciar sesión');
      }
      toast.error('No fue posible iniciar sesión');
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

      const response = await authAPI.devLogin();
      const { access, refresh, token, user } = response.data;
      const accessToken = access || token;
      persistSession(user, accessToken, refresh);
      toast.success('Acceso de desarrollador habilitado');
      navigate('/dashboard');
    } catch (error) {
      devLog('Error en login de desarrollo', error.message);
      if (error.response?.status === 403) {
        setErrorMessage('El backend tiene deshabilitado el auto-login de desarrollo');
      } else if (error.message === 'DEV_DISABLED') {
        setErrorMessage('El acceso de desarrollador no está disponible en este entorno');
      } else {
        setErrorMessage('No fue posible iniciar sesión como desarrollador');
      }
      toast.error('Error al iniciar sesión como desarrollador');
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
          <p className="text-white text-base mt-2 font-medium">Subsecretaría de Seguridad</p>
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
              <label className="block text-sm font-bold mb-2 capitalize" style={{ color: '#6B1839' }}>
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
              style={{ background: 'linear-gradient(135deg, #9F2241 0%, #6B1839 100%)' }}
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white" />
                  Iniciando sesión...
                </>
              ) : (
                <>
                  <FaSignInAlt />
                  Iniciar sesión
                </>
              )}
            </button>
          </form>

          {DEV_CONFIG.SHOW_BUTTON && (
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
          <p className="font-semibold">Subsecretaría de Seguridad</p>
          <p className="text-xs text-pink-100">Gobierno del Estado de México • 2025</p>
        </div>
      </div>
    </div>
  );
}

export default Login;









