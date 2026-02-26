import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { FaLock, FaCheck, FaArrowLeft, FaExclamationTriangle, FaSpinner, FaEye, FaEyeSlash, FaShieldAlt } from 'react-icons/fa';
import { passwordResetAPI } from '../services/api';
import { useTheme } from '../hooks/useTheme';

function RestablecerPassword() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token');
  const uid = searchParams.get('uid');
  const { temaGlobal, logoLoginUrl, nombreSistema } = useTheme();

  const [loading, setLoading] = useState(true);
  const [validToken, setValidToken] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [userEmail, setUserEmail] = useState('');
  
  const [formData, setFormData] = useState({
    new_password: '',
    confirm_password: ''
  });
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [countdown, setCountdown] = useState(10);
  const [hasNavigated, setHasNavigated] = useState(false);
  const [passwordStrength, setPasswordStrength] = useState(0);

  useEffect(() => {
    const validateToken = async () => {
      if (!token || !uid) {
        setErrorMessage('No se proporcionó un enlace válido');
        setLoading(false);
        return;
      }

      try {
        const response = await passwordResetAPI.validate({ token, uid });
        if (response.data.valid) {
          setValidToken(true);
          if (response.data.email) {
            setUserEmail(response.data.email);
          }
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
  }, [token, uid]);

  // Countdown automático con protección contra navegación múltiple
  useEffect(() => {
    if (success && countdown > 0 && !hasNavigated) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    } else if (success && countdown === 0 && !hasNavigated) {
      setHasNavigated(true);
      navigate('/login', { replace: true });
    }
  }, [success, countdown, navigate, hasNavigated]);

  const calculatePasswordStrength = (password) => {
    let strength = 0;
    if (password.length >= 8) strength += 20;
    if (password.length >= 12) strength += 10;
    if (/[a-z]/.test(password)) strength += 20;
    if (/[A-Z]/.test(password)) strength += 20;
    if (/[0-9]/.test(password)) strength += 15;
    if (/[^A-Za-z0-9]/.test(password)) strength += 15;
    return Math.min(strength, 100);
  };

  const getStrengthLabel = (strength) => {
    if (strength < 40) return { label: 'Débil', color: 'bg-red-500' };
    if (strength < 70) return { label: 'Media', color: 'bg-yellow-500' };
    return { label: 'Fuerte', color: 'bg-green-500' };
  };

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
        uid,
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
    const { name, value } = e.target;
    setFormData({
      ...formData,
      [name]: value
    });
    
    if (name === 'new_password') {
      setPasswordStrength(calculatePasswordStrength(value));
    }
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
        {/* Header */}
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
            {success ? '¡Contraseña Actualizada!' : 'Nueva Contraseña'}
          </h1>
          <p style={{ color: 'var(--color-sidebar-text, #FFFFFF)', opacity: 0.9 }} className="text-lg">
            {nombreSistema || 'Sistema de Farmacia Penitenciaria'}
          </p>
        </div>

        {/* Card principal */}
        <div
          className="bg-white rounded-2xl shadow-2xl p-8 mb-6 border-t-4"
          style={{ borderTopColor: 'var(--color-primary, #9F2241)' }}
        >
          {/* Token inválido */}
          {!validToken && !success && (
            <div className="text-center py-4">
              <div className="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <FaExclamationTriangle className="text-red-600 text-3xl" />
              </div>
              <h3 className="text-2xl font-bold text-gray-800 mb-3">Enlace no válido</h3>
              <p className="text-gray-600 mb-6">{errorMessage}</p>
              <Link
                to="/recuperar-password"
                className="inline-flex items-center gap-2 text-white py-3 px-6 rounded-xl font-bold shadow-lg transition-all transform hover:scale-105"
                style={{ background: 'linear-gradient(135deg, var(--color-primary, #9F2241) 0%, var(--color-primary-hover, #6B1839) 100%)' }}
              >
                Solicitar nuevo enlace
              </Link>
            </div>
          )}

          {/* Formulario de nueva contraseña */}
          {validToken && !success && (
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Usuario identificado */}
              {userEmail && (
                <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border-l-4 border-blue-500 p-4 rounded-r-xl">
                  <p className="text-sm text-gray-600 mb-1">Restableciendo contraseña para:</p>
                  <p className="font-bold text-gray-800 flex items-center gap-2">
                    <FaShieldAlt className="text-blue-600" />
                    {userEmail}
                  </p>
                </div>
              )}
              
              <p className="text-gray-600 text-center">
                Ingresa tu nueva contraseña. Debe tener al menos 8 caracteres.
              </p>

              {/* Campo Nueva Contraseña */}
              <div>
                <label className="block text-sm font-bold mb-2" style={{ color: 'var(--color-primary-hover, #6B1839)' }}>
                  Nueva contraseña
                </label>
                <div className="relative">
                  <FaLock className="absolute left-4 top-4 text-gray-400" />
                  <input
                    type={showNewPassword ? "text" : "password"}
                    name="new_password"
                    value={formData.new_password}
                    onChange={handleChange}
                    className="w-full pl-12 pr-12 py-3.5 border-2 border-gray-200 rounded-xl transition-all focus:border-transparent focus:ring-4 focus:outline-none"
                    style={{ '--tw-ring-color': 'rgba(159, 34, 65, 0.2)' }}
                    placeholder="Mínimo 8 caracteres"
                    minLength={8}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowNewPassword(!showNewPassword)}
                    className="absolute right-4 top-4 text-gray-400 hover:text-gray-600 transition-colors"
                    tabIndex={-1}
                  >
                    {showNewPassword ? <FaEyeSlash size={18} /> : <FaEye size={18} />}
                  </button>
                </div>
                
                {/* Indicador de fortaleza */}
                {formData.new_password && (
                  <div className="mt-3 bg-gray-50 rounded-lg p-4 border border-gray-200">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-semibold text-gray-700">Fortaleza de contraseña:</span>
                      <span className={`text-sm font-bold ${
                        passwordStrength < 40 ? 'text-red-600' : 
                        passwordStrength < 70 ? 'text-yellow-600' : 
                        'text-green-600'
                      }`}>
                        {getStrengthLabel(passwordStrength).label}
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden mb-3">
                      <div 
                        className={`h-full transition-all duration-300 ${getStrengthLabel(passwordStrength).color}`}
                        style={{ width: `${passwordStrength}%` }}
                      />
                    </div>
                    <div className="space-y-1.5 text-xs text-gray-600">
                      <div className={`flex items-center gap-2 ${formData.new_password.length >= 8 ? 'text-green-600 font-semibold' : ''}`}>
                        <span className="text-base">{formData.new_password.length >= 8 ? '✓' : '○'}</span>
                        <span>Mínimo 8 caracteres</span>
                      </div>
                      <div className={`flex items-center gap-2 ${/[A-Z]/.test(formData.new_password) && /[a-z]/.test(formData.new_password) ? 'text-green-600 font-semibold' : ''}`}>
                        <span className="text-base">{/[A-Z]/.test(formData.new_password) && /[a-z]/.test(formData.new_password) ? '✓' : '○'}</span>
                        <span>Mayúsculas y minúsculas</span>
                      </div>
                      <div className={`flex items-center gap-2 ${/[0-9]/.test(formData.new_password) ? 'text-green-600 font-semibold' : ''}`}>
                        <span className="text-base">{/[0-9]/.test(formData.new_password) ? '✓' : '○'}</span>
                        <span>Al menos un número</span>
                      </div>
                      <div className={`flex items-center gap-2 ${/[^A-Za-z0-9]/.test(formData.new_password) ? 'text-green-600 font-semibold' : ''}`}>
                        <span className="text-base">{/[^A-Za-z0-9]/.test(formData.new_password) ? '✓' : '○'}</span>
                        <span>Caracteres especiales (!@#$%^&*)</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Campo Confirmar Contraseña */}
              <div>
                <label className="block text-sm font-bold mb-2" style={{ color: 'var(--color-primary-hover, #6B1839)' }}>
                  Confirmar contraseña
                </label>
                <div className="relative">
                  <FaLock className="absolute left-4 top-4 text-gray-400" />
                  <input
                    type={showConfirmPassword ? "text" : "password"}
                    name="confirm_password"
                    value={formData.confirm_password}
                    onChange={handleChange}
                    className="w-full pl-12 pr-12 py-3.5 border-2 border-gray-200 rounded-xl transition-all focus:border-transparent focus:ring-4 focus:outline-none"
                    style={{ '--tw-ring-color': 'rgba(159, 34, 65, 0.2)' }}
                    placeholder="Repite la contraseña"
                    minLength={8}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-4 top-4 text-gray-400 hover:text-gray-600 transition-colors"
                    tabIndex={-1}
                  >
                    {showConfirmPassword ? <FaEyeSlash size={18} /> : <FaEye size={18} />}
                  </button>
                </div>
              </div>

              {/* Mensaje de error si no coinciden */}
              {formData.new_password && formData.confirm_password && 
               formData.new_password !== formData.confirm_password && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl flex items-center gap-2">
                  <FaExclamationTriangle />
                  <span className="text-sm font-semibold">Las contraseñas no coinciden</span>
                </div>
              )}

              {/* Botón Submit */}
              <button
                type="submit"
                disabled={submitting || formData.new_password !== formData.confirm_password}
                className="w-full text-white py-4 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 font-bold text-lg shadow-xl transition-all transform hover:scale-105 hover:shadow-2xl active:scale-95"
                style={{ background: 'linear-gradient(135deg, var(--color-primary, #9F2241) 0%, var(--color-primary-hover, #6B1839) 100%)' }}
              >
                {submitting ? (
                  <>
                    <FaSpinner className="animate-spin" />
                    Guardando cambios...
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

          {/* Pantalla de Éxito */}
          {success && (
            <div className="text-center py-6">
              {/* Ícono de éxito animado */}
              <div className="relative inline-flex items-center justify-center mb-6">
                <div className="absolute w-24 h-24 bg-green-500 rounded-full opacity-20 animate-ping"></div>
                <div className="relative w-24 h-24 bg-gradient-to-br from-green-400 to-green-600 rounded-full flex items-center justify-center shadow-2xl">
                  <FaCheck className="text-white text-4xl" />
                </div>
              </div>
              
              <h3 className="text-2xl font-bold text-gray-800 mb-3">¡Contraseña actualizada exitosamente!</h3>
              <p className="text-gray-600 mb-6 text-lg">
                Tu contraseña ha sido restablecida. Ya puedes iniciar sesión con tu nueva contraseña.
              </p>
              
              {/* Información de seguridad */}
              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-5 mb-6 text-left">
                <h4 className="font-bold text-gray-800 mb-4 flex items-center gap-2 text-lg">
                  <FaShieldAlt className="text-blue-600" />
                  Detalles de seguridad
                </h4>
                <ul className="space-y-3 text-sm text-gray-700">
                  <li className="flex items-start gap-3">
                    <FaCheck className="text-green-600 mt-0.5 flex-shrink-0 text-base" />
                    <span>Tu contraseña se ha encriptado y almacenado de forma segura</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <FaCheck className="text-green-600 mt-0.5 flex-shrink-0 text-base" />
                    <span>Esta acción ha sido registrada en el log de auditoría del sistema</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <FaCheck className="text-green-600 mt-0.5 flex-shrink-0 text-base" />
                    <span>El enlace de recuperación ha sido invalidado automáticamente</span>
                  </li>
                  {userEmail && (
                    <li className="flex items-start gap-3">
                      <FaCheck className="text-green-600 mt-0.5 flex-shrink-0 text-base" />
                      <span>Confirmación enviada a <strong>{userEmail}</strong></span>
                    </li>
                  )}
                </ul>
              </div>
              
              {/* Recomendaciones de seguridad */}
              <div className="bg-gradient-to-r from-yellow-50 to-orange-50 border border-yellow-200 rounded-xl p-5 mb-6 text-left">
                <h4 className="font-bold text-gray-800 mb-4 flex items-center gap-2 text-lg">
                  <FaExclamationTriangle className="text-yellow-600" />
                  Recomendaciones de seguridad
                </h4>
                <ul className="space-y-3 text-sm text-gray-700">
                  <li className="flex items-start gap-3">
                    <span className="text-yellow-600 font-bold flex-shrink-0 text-base">•</span>
                    <span>No compartas tu contraseña con nadie, incluso si dicen ser del soporte técnico</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="text-yellow-600 font-bold flex-shrink-0 text-base">•</span>
                    <span>Se recomienda cambiar tu contraseña cada 90 días</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="text-yellow-600 font-bold flex-shrink-0 text-base">•</span>
                    <span>No uses la misma contraseña en otros sistemas o sitios web</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="text-yellow-600 font-bold flex-shrink-0 text-base">•</span>
                    <span>Utiliza contraseñas únicas y complejas para mayor seguridad</span>
                  </li>
                </ul>
              </div>
              
              {/* Botón con protección contra navegación múltiple */}
              <button
                onClick={() => {
                  if (!hasNavigated) {
                    setHasNavigated(true);
                    navigate('/login', { replace: true });
                  }
                }}
                disabled={hasNavigated}
                className="w-full inline-flex items-center justify-center gap-3 text-white py-4 px-6 rounded-xl font-bold text-lg transition-all transform hover:scale-105 shadow-xl hover:shadow-2xl mb-5 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                style={{ background: 'linear-gradient(135deg, var(--color-primary, #9F2241) 0%, var(--color-primary-hover, #6B1839) 100%)' }}
              >
                {hasNavigated ? (
                  <>
                    <FaSpinner className="animate-spin text-xl" />
                    Redirigiendo al login...
                  </>
                ) : (
                  <>
                    <FaArrowLeft className="text-xl" />
                    Ir a iniciar sesión ahora
                  </>
                )}
              </button>
              
              {/* Contador con diseño mejorado */}
              <div className="bg-gray-100 rounded-xl p-4 border border-gray-300">
                <p className="text-gray-700 text-sm flex items-center justify-center gap-2">
                  <span>Redirigiendo automáticamente en</span>
                  <span className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-blue-700 text-white font-bold text-lg shadow-lg">
                    {countdown}
                  </span>
                  <span>segundos...</span>
                </p>
              </div>
            </div>
          )}

          {/* Link volver al login (solo si no está en éxito) */}
          {!success && (
            <div className="mt-6 pt-6 border-t border-gray-100 text-center">
              <Link 
                to="/login" 
                className="text-gray-600 hover:text-gray-800 font-medium flex items-center justify-center gap-2 transition-colors"
              >
                <FaArrowLeft />
                Volver al inicio de sesión
              </Link>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="text-center mt-6 text-white text-sm space-y-1">
          <p className="font-bold text-base">{nombreSistema || 'Sistema de Control de Abasto'}</p>
          <p className="font-semibold">{temaGlobal?.reporte_subtitulo || 'Subsecretaría de Seguridad'}</p>
          <p className="text-xs" style={{ color: 'var(--color-sidebar-text, #FFFFFF)', opacity: 0.8 }}>
            {temaGlobal?.reporte_pie_pagina || 'Gobierno del Estado de México'} {temaGlobal?.reporte_ano_visible !== false ? '• 2025' : ''}
          </p>
        </div>
      </div>
    </div>
  );
}

export default RestablecerPassword;
