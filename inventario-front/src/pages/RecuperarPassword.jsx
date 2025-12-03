import { useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { FaEnvelope, FaArrowLeft, FaPaperPlane } from 'react-icons/fa';
import { passwordResetAPI } from '../services/api';

function RecuperarPassword() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [enviado, setEnviado] = useState(false);
  const [debugInfo, setDebugInfo] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!email.trim()) {
      toast.error('Ingresa tu correo electrónico');
      return;
    }

    setLoading(true);
    try {
      const response = await passwordResetAPI.request(email);
      setEnviado(true);
      toast.success('Solicitud enviada correctamente');
      
      // En modo desarrollo, mostrar info de debug
      if (response.data.debug_token) {
        setDebugInfo({
          token: response.data.debug_token,
          url: response.data.debug_url
        });
      }
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al enviar solicitud');
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
          <div className="inline-flex items-center justify-center bg-white rounded-lg mb-4 shadow-lg p-2">
            <img 
              src="/logo-seguridad.jpg" 
              alt="Secretaría de Seguridad" 
              className="h-16 w-auto object-contain"
            />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">Recuperar Contraseña</h1>
          <p className="text-pink-100">Sistema de Farmacia Penitenciaria</p>
        </div>

        <div
          className="bg-white rounded-2xl shadow-2xl p-8 mb-6 border-t-4"
          style={{ borderTopColor: '#9F2241' }}
        >
          {!enviado ? (
            <form onSubmit={handleSubmit} className="space-y-5">
              <p className="text-gray-600 text-center mb-4">
                Ingresa el correo electrónico asociado a tu cuenta. 
                Te enviaremos un enlace para restablecer tu contraseña.
              </p>

              <div>
                <label className="block text-sm font-bold mb-2" style={{ color: '#6B1839' }}>
                  Correo electrónico
                </label>
                <div className="relative">
                  <FaEnvelope className="absolute left-4 top-4 text-gray-400" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full pl-12 pr-4 py-3.5 border-2 border-gray-200 rounded-xl transition-all focus:border-transparent focus:ring-4 focus:outline-none"
                    style={{ '--tw-ring-color': 'rgba(159, 34, 65, 0.2)' }}
                    placeholder="tu.correo@ejemplo.com"
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
                    Enviando...
                  </>
                ) : (
                  <>
                    <FaPaperPlane />
                    Enviar enlace de recuperación
                  </>
                )}
              </button>
            </form>
          ) : (
            <div className="text-center py-4">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <FaEnvelope className="text-green-600 text-2xl" />
              </div>
              <h3 className="text-xl font-bold text-gray-800 mb-2">¡Revisa tu correo!</h3>
              <p className="text-gray-600 mb-4">
                Si el correo <strong>{email}</strong> está registrado, 
                recibirás un enlace para restablecer tu contraseña.
              </p>
              <p className="text-sm text-gray-500">
                No olvides revisar tu carpeta de spam.
              </p>
              
              {/* Debug info para desarrollo */}
              {debugInfo && (
                <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg text-left">
                  <p className="text-xs text-yellow-700 font-bold mb-2">
                    ⚠️ Modo desarrollo (email no configurado):
                  </p>
                  <p className="text-xs text-gray-600 break-all">
                    <strong>URL:</strong> {debugInfo.url}
                  </p>
                  <a 
                    href={debugInfo.url}
                    className="inline-block mt-2 text-sm text-blue-600 hover:underline"
                  >
                    Ir a restablecer contraseña →
                  </a>
                </div>
              )}
              
              <button
                onClick={() => {
                  setEnviado(false);
                  setEmail('');
                  setDebugInfo(null);
                }}
                className="mt-6 text-gray-600 hover:text-gray-800 font-medium"
              >
                ← Enviar a otro correo
              </button>
            </div>
          )}

          <div className="mt-6 pt-6 border-t border-gray-100 text-center">
            <Link 
              to="/login" 
              className="text-gray-600 hover:text-gray-800 font-medium flex items-center justify-center gap-2"
            >
              <FaArrowLeft />
              Volver al inicio de sesión
            </Link>
          </div>
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

export default RecuperarPassword;
