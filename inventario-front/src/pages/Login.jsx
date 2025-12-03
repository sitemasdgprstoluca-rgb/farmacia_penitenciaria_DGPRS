import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { FaUser, FaLock, FaSignInAlt } from 'react-icons/fa';
import { authAPI } from '../services/api';
import { usePermissions } from '../hooks/usePermissions';
import { setAccessToken, clearTokens } from '../services/tokenManager';

function Login() {
  const [credentials, setCredentials] = useState({ username: '', password: '' });
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const navigate = useNavigate();
  const { recargarUsuario } = usePermissions();

  const persistSession = (user, accessToken) => {
    // Access token se guarda en memoria (tokenManager) para seguridad
    if (accessToken) {
      setAccessToken(accessToken);
    }
    // Refresh token se maneja automáticamente via cookie HttpOnly
    // Solo guardamos datos del usuario en localStorage (no sensible)
    if (user) {
      localStorage.setItem('user', JSON.stringify(user));
    }
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

  const performLogin = async (creds) => loginWithBackend(creds);

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
      if (error.response?.status === 401 || error.response?.status === 400) {
        setErrorMessage('Credenciales inválidas');
      } else if (error.response?.status === 404) {
        setErrorMessage('Credenciales inválidas');
      } else if (error.response?.data?.non_field_errors) {
        setErrorMessage(error.response.data.non_field_errors[0]);
      } else {
        setErrorMessage('Credenciales inválidas');
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
        background: 'linear-gradient(135deg, #9F2241 0%, #6B1839 50%, #4a0f26 100%)',
      }}
    >
      <div className="max-w-md w-full mx-auto">
        <div className="text-center mb-6">
          {/* Logo del Sistema */}
          <div className="inline-flex items-center justify-center mb-4">
            <img 
              src="/logo-seguridad.jpg" 
              alt="Secretaría de Seguridad" 
              className="h-24 w-auto object-contain rounded-lg"
            />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">Sistema de Farmacia Penitenciaria</h1>
          <p className="text-lg text-pink-100">Control de Abasto de Medicamentos</p>
          <p className="text-white text-sm mt-2 font-medium">Subsecretaría de Seguridad - Estado de México</p>
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
                  <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent" />
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
                style={{ color: '#9F2241' }}
              >
                ¿Olvidaste tu contraseña?
              </Link>
            </div>
          </form>
        </div>

        <div className="text-center mt-6 text-white text-sm space-y-1">
          <p className="font-bold text-base">Sistema Integral de Farmacia Penitenciaria</p>
          <p className="font-semibold">Gobierno del Estado de México</p>
          <p className="text-xs text-pink-100">Subsecretaría de Seguridad • 2025</p>
        </div>
      </div>
    </div>
  );
}

export default Login;
