import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { FaLock, FaCheck, FaArrowLeft, FaExclamationTriangle, FaSpinner } from 'react-icons/fa';
import { passwordResetAPI } from '../services/api';
import { useTheme } from '../hooks/useTheme';

function RestablecerPassword() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token');
  const { temaGlobal, logoLoginUrl, nombreSistema } = useTheme();

  const [loading, setLoading] = useState(true);
  const [validToken, setValidToken] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  
  const [formData, setFormData] = useState({
    new_password: '',
    confirm_password: ''
  });

  useEffect(() => {
    const validateToken = async () => {
      if (!token) {
        setErrorMessage('No se proporcionó un token válido');
        setLoading(false);
        return;
      }

      try {
        const response = await passwordResetAPI.validate(token);
        if (response.data.valid) {
          setValidToken(true);
        } else {
          setErrorMessage(response.data.error || 'El enlace no es válido');
        }
      } catch (error) {
        setErrorMessage('El enlace ha expirado o no es válido');
      } finally {
        setLoading(false);
      }
    };

    validateToken();
  }, [token]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (formData.new_password.length < 8) {
      toast.error('La contraseña debe tener al menos 8 caracteres');
      return;
    }

    if (formData.new_password !== formData.confirm_password) {
      toast.error('Las contraseñas no coinciden');
      return;
    }

    setSubmitting(true);
    try {
      await passwordResetAPI.confirm({
        token,
        new_password: formData.new_password,
        confirm_password: formData.confirm_password
      });
      setSuccess(true);
      toast.success('Contraseña restablecida exitosamente');
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al restablecer la contraseña');
    } finally {
      setSubmitting(false);
    }
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" 
           style={{ background: 'linear-gradient(135deg, var(--color-primary, #9F2241) 0%, var(--color-primary-hover, #6B1839) 50%, #4a0f26 100%)' }}>
                <div className="text-center text-white">
          <FaSpinner className="animate-spin h-10 w-10 mx-auto mb-4" />
          <p>Verificando enlace...</p>
        </div>
      </div>
    );
  }

  return (
    <div
      className="min-h-screen w-full flex items-center justify-center p-4 overflow-auto"
      style={{
        background: `linear-gradient(135deg, var(--color-primary, #9F2241) 0%, var(--color-primary-hover, #6B1839) 50%, ${temaGlobal?.color_primario_hover || '#4a0f26'} 100%)`,
      }}
    >
      <div className="max-w-md w-full mx-auto">
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center bg-white rounded-lg mb-4 shadow-lg p-3">
            <img 
              src={logoLoginUrl || "/logo-sistema.png"} 
              alt="Logo del Sistema" 
              className="h-32 w-64 object-contain"
              onError={(e) => { e.target.src = "/logo-sistema.png"; }}
            />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">
            {success ? '¡Listo!' : 'Nueva Contraseña'}
          </h1>
          <p style={{ color: 'var(--color-sidebar-text, #FFFFFF)', opacity: 0.7 }}>
            {nombreSistema || 'Sistema de Farmacia Penitenciaria'}
          </p>
        </div>

        <div
          className="bg-white rounded-2xl shadow-2xl p-8 mb-6 border-t-4"
          style={{ borderTopColor: 'var(--color-primary, #9F2241)' }}
        >
          {/* Token inválido */}
          {!validToken && !success && (
            <div className="text-center py-4">
              <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <FaExclamationTriangle className="text-red-600 text-2xl" />
              </div>
              <h3 className="text-xl font-bold text-gray-800 mb-2">Enlace no válido</h3>
              <p className="text-gray-600 mb-4">{errorMessage}</p>
              <Link
                to="/recuperar-password"
                className="inline-flex items-center gap-2 text-white py-3 px-6 rounded-xl font-bold"
                style={{ background: 'linear-gradient(135deg, var(--color-primary, #9F2241) 0%, var(--color-primary-hover, #6B1839) 100%)' }}
              >
                Solicitar nuevo enlace
              </Link>
            </div>
          )}

          {/* Formulario de nueva contraseña */}
          {validToken && !success && (
            <form onSubmit={handleSubmit} className="space-y-5">
              <p className="text-gray-600 text-center mb-4">
                Ingresa tu nueva contraseña. Debe tener al menos 8 caracteres.
              </p>

              <div>
                <label className="block text-sm font-bold mb-2" style={{ color: 'var(--color-primary-hover, #6B1839)' }}>
                  Nueva contraseña
                </label>
                <div className="relative">
                  <FaLock className="absolute left-4 top-4 text-gray-400" />
                  <input
                    type="password"
                    name="new_password"
                    value={formData.new_password}
                    onChange={handleChange}
                    className="w-full pl-12 pr-4 py-3.5 border-2 border-gray-200 rounded-xl transition-all focus:border-transparent focus:ring-4 focus:outline-none"
                    style={{ '--tw-ring-color': 'rgba(159, 34, 65, 0.2)' }}
                    placeholder="Mínimo 8 caracteres"
                    minLength={8}
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-bold mb-2" style={{ color: 'var(--color-primary-hover, #6B1839)' }}>
                  Confirmar contraseña
                </label>
                <div className="relative">
                  <FaLock className="absolute left-4 top-4 text-gray-400" />
                  <input
                    type="password"
                    name="confirm_password"
                    value={formData.confirm_password}
                    onChange={handleChange}
                    className="w-full pl-12 pr-4 py-3.5 border-2 border-gray-200 rounded-xl transition-all focus:border-transparent focus:ring-4 focus:outline-none"
                    style={{ '--tw-ring-color': 'rgba(159, 34, 65, 0.2)' }}
                    placeholder="Repite la contraseña"
                    minLength={8}
                    required
                  />
                </div>
              </div>

              {formData.new_password && formData.confirm_password && 
               formData.new_password !== formData.confirm_password && (
                <p className="text-red-500 text-sm">Las contraseñas no coinciden</p>
              )}

              <button
                type="submit"
                disabled={submitting || formData.new_password !== formData.confirm_password}
                className="w-full text-white py-4 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 font-bold shadow-xl transition-all transform hover:scale-105 hover:shadow-2xl active:scale-95"
                style={{ background: 'linear-gradient(135deg, var(--color-primary, #9F2241) 0%, var(--color-primary-hover, #6B1839) 100%)' }}
              >
                              {submitting ? (
                  <>
                    <FaSpinner className="animate-spin" />
                    Guardando...
                  </>
                ) : (
                  <>
                    <FaCheck />
                    Restablecer contraseña
                  </>
                )}
              </button>
            </form>
          )}

          {/* Éxito */}
          {success && (
            <div className="text-center py-4">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <FaCheck className="text-green-600 text-2xl" />
              </div>
              <h3 className="text-xl font-bold text-gray-800 mb-2">¡Contraseña actualizada!</h3>
              <p className="text-gray-600 mb-6">
                Tu contraseña ha sido restablecida exitosamente. 
                Ya puedes iniciar sesión con tu nueva contraseña.
              </p>
              <button
                onClick={() => navigate('/login')}
                className="inline-flex items-center gap-2 text-white py-3 px-6 rounded-xl font-bold transition-all transform hover:scale-105"
                style={{ background: 'linear-gradient(135deg, var(--color-primary, #9F2241) 0%, var(--color-primary-hover, #6B1839) 100%)' }}
              >
                Ir a iniciar sesión
              </button>
            </div>
          )}

          {!success && (
            <div className="mt-6 pt-6 border-t border-gray-100 text-center">
              <Link 
                to="/login" 
                className="text-gray-600 hover:text-gray-800 font-medium flex items-center justify-center gap-2"
              >
                <FaArrowLeft />
                Volver al inicio de sesión
              </Link>
            </div>
          )}
        </div>

        <div className="text-center mt-6 text-white text-sm space-y-1">
          <p className="font-bold text-base">{nombreSistema || 'Sistema de Control de Abasto'}</p>
          <p className="font-semibold">{temaGlobal?.reporte_subtitulo || 'Subsecretaría de Seguridad'}</p>
          <p className="text-xs" style={{ color: 'var(--color-sidebar-text, #FFFFFF)', opacity: 0.7 }}>
            {temaGlobal?.reporte_pie_pagina || 'Gobierno del Estado de México'} {temaGlobal?.reporte_ano_visible !== false ? '• 2025' : ''}
          </p>
        </div>
      </div>
    </div>
  );
}

export default RestablecerPassword;
