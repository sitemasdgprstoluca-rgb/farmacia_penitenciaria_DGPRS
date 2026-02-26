import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { FaLock, FaCheck, FaArrowLeft, FaExclamationTriangle, FaSpinner, FaEye, FaEyeSlash, FaShieldAlt } from 'react-icons/fa';
import { passwordResetAPI } from '../services/api';
import { useTheme } from '../hooks/useTheme';
import './RestablecerPassword.css';

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
        <div className="text-center">
          <div className="relative inline-flex items-center justify-center mb-6">
            <div className="absolute w-24 h-24 bg-white/20 rounded-full animate-ping"></div>
            <div className="relative w-20 h-20 bg-white/10 backdrop-blur-lg rounded-full flex items-center justify-center border-2 border-white/30 shadow-2xl">
              <FaSpinner className="animate-spin h-10 w-10 text-white" />
            </div>
          </div>
          <p className="text-white text-lg font-semibold drop-shadow-lg">Verificando enlace de seguridad...</p>
          <p className="text-white/70 text-sm mt-2 drop-shadow">Un momento por favor</p>
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
        {/* Header ultra-moderno con glassmorphism */}
        <div className="text-center mb-8 animate-fade-in">
          <div className="relative inline-flex items-center justify-center mb-6">
            <div className="absolute w-24 h-24 bg-white/10 rounded-full animate-pulse"></div>
            <div className="relative w-20 h-20 bg-white/20 backdrop-blur-xl rounded-full flex items-center justify-center shadow-2xl border border-white/30 transition-all duration-500 hover:scale-110">
              <span className="text-5xl animate-bounce-slow">{success ? '✅' : '🔐'}</span>
            </div>
          </div>
          <h1 className="text-5xl font-black text-white mb-3 drop-shadow-2xl tracking-tight leading-tight animate-slide-down">
            {success ? '¡Contraseña Actualizada!' : 'Nueva Contraseña'}
          </h1>
          <p className="text-white text-xl drop-shadow-lg font-semibold mb-2 animate-slide-up">
            {nombreSistema || 'Sistema de Farmacia Penitenciaria'}
          </p>
          <p className="text-white/80 text-base drop-shadow-md font-medium animate-fade-in-delay">
            {temaGlobal?.reporte_subtitulo || 'Subsecretaría de Seguridad'}
          </p>
        </div>

        {/* Card principal ultra-premium con glassmorphism */}
        <div
          className="bg-white/95 backdrop-blur-xl rounded-3xl shadow-2xl p-8 mb-6 border-t-4 transition-all duration-500 hover:shadow-[0_25px_50px_-12px_rgba(0,0,0,0.25)] hover:scale-[1.01] animate-slide-up"
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
              {/* Usuario identificado - Design premium */}
              {userEmail && (
                <div className="bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 border-l-4 border-blue-500 p-5 rounded-r-2xl shadow-lg hover:shadow-xl transition-all duration-300 animate-slide-right">
                  <p className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-3 flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse"></span>
                    Restableciendo contraseña para
                  </p>
                  <p className="font-extrabold text-gray-800 flex items-center gap-3 text-lg tracking-tight">
                    <span className="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full flex items-center justify-center shadow-lg animate-pulse-slow">
                      <FaShieldAlt className="text-white text-base" />
                    </span>
                    <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-purple-600">{userEmail}</span>
                  </p>
                </div>
              )}
              
              <div className="bg-gradient-to-r from-gray-50 to-gray-100 border-2 border-gray-200 rounded-2xl p-5 text-center shadow-sm">
                <p className="text-gray-700 font-semibold text-base flex items-center justify-center gap-2">
                  <FaLock className="text-gray-400" />
                  <span>Ingresa tu nueva contraseña. Debe tener <strong className="text-gray-900">al menos 8 caracteres</strong>.</span>
                </p>
              </div>

              {/* Campo Nueva Contraseña - Ultra premium */}
              <div className="space-y-2">
                <label className="block text-sm font-extrabold mb-3 tracking-wide" style={{ color: 'var(--color-primary-hover, #6B1839)' }}>
                  Nueva contraseña
                </label>
                <div className="relative group">
                  <div className="absolute -inset-0.5 bg-gradient-to-r from-pink-600 to-purple-600 rounded-2xl opacity-0 group-focus-within:opacity-20 blur transition duration-500"></div>
                  <div className="relative">
                    <FaLock className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-blue-500 transition-colors duration-300" />
                    <input
                      type={showNewPassword ? "text" : "password"}
                      name="new_password"
                      value={formData.new_password}
                      onChange={handleChange}
                      className="w-full pl-12 pr-12 py-4 border-2 border-gray-200 rounded-2xl transition-all duration-300 focus:border-transparent focus:ring-4 focus:outline-none bg-white hover:border-gray-300 shadow-sm focus:shadow-lg"
                      style={{ '--tw-ring-color': 'rgba(159, 34, 65, 0.15)' }}
                      placeholder="●●●●●●●●"
                      minLength={8}
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowNewPassword(!showNewPassword)}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-700 transition-all duration-300 hover:scale-110 active:scale-95"
                      tabIndex={-1}
                    >
                      {showNewPassword ? <FaEyeSlash size={20} /> : <FaEye size={20} />}
                    </button>
                  </div>
                </div>
                
                {/* Indicador de fortaleza - Premium animated */}
                {formData.new_password && (
                  <div className="mt-4 bg-gradient-to-br from-gray-50 to-gray-100 rounded-2xl p-5 border-2 border-gray-200 shadow-md animate-slide-down">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-sm font-bold text-gray-800 flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></span>
                        Fortaleza de contraseña
                      </span>
                      <span className={`text-base font-extrabold px-3 py-1 rounded-full ${
                        passwordStrength < 40 ? 'text-red-700 bg-red-100' : 
                        passwordStrength < 70 ? 'text-yellow-700 bg-yellow-100' : 
                        'text-green-700 bg-green-100'
                      } transition-all duration-300 animate-pulse-slow`}>
                        {getStrengthLabel(passwordStrength).label}
                      </span>
                    </div>
                    <div className="relative w-full bg-gray-300 rounded-full h-3 overflow-hidden mb-4 shadow-inner">
                      <div 
                        className={`h-full transition-all duration-500 ease-out ${getStrengthLabel(passwordStrength).color} relative overflow-hidden`}
                        style={{ width: `${passwordStrength}%` }}
                      >
                        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white to-transparent opacity-30 animate-shimmer"></div>
                      </div>
                    </div>
                    <div className="space-y-2.5 text-sm">
                      <div className={`flex items-center gap-3 p-2 rounded-lg transition-all duration-300 ${formData.new_password.length >= 8 ? 'bg-green-50 text-green-700 font-bold scale-105' : 'text-gray-600'}`}>
                        <span className={`text-lg font-bold transition-transform duration-300 ${formData.new_password.length >= 8 ? 'animate-bounce-once' : ''}`}>{formData.new_password.length >= 8 ? '✓' : '○'}</span>
                        <span className="flex-1">Mínimo 8 caracteres</span>
                        {formData.new_password.length >= 8 && <span className="text-xs font-bold px-2 py-0.5 bg-green-200 rounded-full">Cumple</span>}
                      </div>
                      <div className={`flex items-center gap-3 p-2 rounded-lg transition-all duration-300 ${/[A-Z]/.test(formData.new_password) && /[a-z]/.test(formData.new_password) ? 'bg-green-50 text-green-700 font-bold scale-105' : 'text-gray-600'}`}>
                        <span className={`text-lg font-bold transition-transform duration-300 ${/[A-Z]/.test(formData.new_password) && /[a-z]/.test(formData.new_password) ? 'animate-bounce-once' : ''}`}>{/[A-Z]/.test(formData.new_password) && /[a-z]/.test(formData.new_password) ? '✓' : '○'}</span>
                        <span className="flex-1">Mayúsculas y minúsculas</span>
                        {/[A-Z]/.test(formData.new_password) && /[a-z]/.test(formData.new_password) && <span className="text-xs font-bold px-2 py-0.5 bg-green-200 rounded-full">Cumple</span>}
                      </div>
                      <div className={`flex items-center gap-3 p-2 rounded-lg transition-all duration-300 ${/[0-9]/.test(formData.new_password) ? 'bg-green-50 text-green-700 font-bold scale-105' : 'text-gray-600'}`}>
                        <span className={`text-lg font-bold transition-transform duration-300 ${/[0-9]/.test(formData.new_password) ? 'animate-bounce-once' : ''}`}>{/[0-9]/.test(formData.new_password) ? '✓' : '○'}</span>
                        <span className="flex-1">Al menos un número</span>
                        {/[0-9]/.test(formData.new_password) && <span className="text-xs font-bold px-2 py-0.5 bg-green-200 rounded-full">Cumple</span>}
                      </div>
                      <div className={`flex items-center gap-3 p-2 rounded-lg transition-all duration-300 ${/[^A-Za-z0-9]/.test(formData.new_password) ? 'bg-green-50 text-green-700 font-bold scale-105' : 'text-gray-600'}`}>
                        <span className={`text-lg font-bold transition-transform duration-300 ${/[^A-Za-z0-9]/.test(formData.new_password) ? 'animate-bounce-once' : ''}`}>{/[^A-Za-z0-9]/.test(formData.new_password) ? '✓' : '○'}</span>
                        <span className="flex-1">Caracteres especiales (!@#$%^&*)</span>
                        {/[^A-Za-z0-9]/.test(formData.new_password) && <span className="text-xs font-bold px-2 py-0.5 bg-green-200 rounded-full">Cumple</span>}
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Campo Confirmar Contraseña - Ultra premium */}
              <div className="space-y-2">
                <label className="block text-sm font-extrabold mb-3 tracking-wide" style={{ color: 'var(--color-primary-hover, #6B1839)' }}>
                  Confirmar contraseña
                </label>
                <div className="relative group">
                  <div className="absolute -inset-0.5 bg-gradient-to-r from-pink-600 to-purple-600 rounded-2xl opacity-0 group-focus-within:opacity-20 blur transition duration-500"></div>
                  <div className="relative">
                    <FaLock className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-green-500 transition-colors duration-300" />
                    <input
                      type={showConfirmPassword ? "text" : "password"}
                      name="confirm_password"
                      value={formData.confirm_password}
                      onChange={handleChange}
                      className={`w-full pl-12 pr-12 py-4 border-2 rounded-2xl transition-all duration-300 focus:outline-none bg-white hover:border-gray-300 shadow-sm focus:shadow-lg ${
                        formData.confirm_password && formData.new_password === formData.confirm_password
                          ? 'border-green-500 focus:border-green-500 focus:ring-4 focus:ring-green-200'
                          : formData.confirm_password && formData.new_password !== formData.confirm_password
                          ? 'border-red-300 focus:border-red-500 focus:ring-4 focus:ring-red-200'
                          : 'border-gray-200 focus:border-transparent focus:ring-4'
                      }`}
                      style={{ '--tw-ring-color': formData.confirm_password ? 'transparent' : 'rgba(159, 34, 65, 0.15)' }}
                      placeholder="●●●●●●●●"
                      minLength={8}
                      required
                    />
                    {formData.confirm_password && formData.new_password === formData.confirm_password && (
                      <FaCheck className="absolute right-12 top-1/2 -translate-y-1/2 text-green-600 animate-bounce-once" />
                    )}
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-700 transition-all duration-300 hover:scale-110 active:scale-95"
                      tabIndex={-1}
                    >
                      {showConfirmPassword ? <FaEyeSlash size={20} /> : <FaEye size={20} />}
                    </button>
                  </div>
                </div>
              </div>

              {/* Validación visual mejorada */}
              {formData.new_password && formData.confirm_password && formData.new_password !== formData.confirm_password && (
                <div className="bg-gradient-to-r from-red-50 to-pink-50 border-2 border-red-300 text-red-700 px-5 py-4 rounded-2xl flex items-center gap-3 shadow-md animate-shake">
                  <div className="w-10 h-10 bg-red-200 rounded-full flex items-center justify-center flex-shrink-0">
                    <FaExclamationTriangle className="text-red-600" />
                  </div>
                  <div>
                    <p className="text-sm font-bold">Las contraseñas no coinciden</p>
                    <p className="text-xs text-red-600 mt-0.5">Verifica que ambas contraseñas sean idénticas</p>
                  </div>
                </div>
              )}
              
              {/* Confirmación positiva cuando coinciden */}
              {formData.new_password && formData.confirm_password && formData.new_password === formData.confirm_password && passwordStrength >= 70 && (
                <div className="bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-400 text-green-700 px-5 py-4 rounded-2xl flex items-center gap-3 shadow-md animate-slide-down">
                  <div className="w-10 h-10 bg-green-200 rounded-full flex items-center justify-center flex-shrink-0 animate-pulse">
                    <FaCheck className="text-green-600 text-lg" />
                  </div>
                  <div>
                    <p className="text-sm font-bold">¡Contraseña válida y segura!</p>
                    <p className="text-xs text-green-600 mt-0.5">Las contraseñas coinciden perfectamente</p>
                  </div>
                </div>
              )}

              {/* Botón Submit - Ultra premium */}
              <button
                type="submit"
                disabled={submitting || formData.new_password !== formData.confirm_password}
                className="relative w-full text-white py-5 rounded-2xl disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-3 font-black text-xl shadow-2xl transition-all duration-500 transform hover:scale-[1.02] hover:shadow-[0_20px_50px_rgba(159,34,65,0.4)] active:scale-[0.98] overflow-hidden group"
                style={{ background: 'linear-gradient(135deg, var(--color-primary, #9F2241) 0%, var(--color-primary-hover, #6B1839) 100%)' }}
              >
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white to-transparent opacity-0 group-hover:opacity-20 transition-opacity duration-500 group-hover:animate-shimmer"></div>
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

          {/* Pantalla de Éxito con diseño impactante */}
          {success && (
            <div className="text-center py-8">
              {/* Ícono de éxito animado mejorado */}
              <div className="relative inline-flex items-center justify-center mb-8">
                <div className="absolute w-28 h-28 bg-green-500 rounded-full opacity-20 animate-ping"></div>
                <div className="absolute w-32 h-32 bg-green-400 rounded-full opacity-10 animate-pulse"></div>
                <div className="relative w-24 h-24 bg-gradient-to-br from-green-400 via-green-500 to-green-600 rounded-full flex items-center justify-center shadow-2xl">
                  <FaCheck className="text-white text-5xl drop-shadow-lg" />
                </div>
              </div>
              
              <h3 className="text-3xl font-extrabold text-gray-800 mb-4 tracking-tight">¡Contraseña actualizada exitosamente!</h3>
              <p className="text-gray-600 mb-8 text-lg leading-relaxed">
                Tu contraseña ha sido restablecida de forma segura. Ya puedes iniciar sesión con tu nueva contraseña.
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

        {/* Footer moderno con backdrop blur */}
        <div className="text-center mt-8 bg-white/10 backdrop-blur-sm rounded-2xl p-6 border border-white/20 shadow-lg">
          <p className="font-bold text-white text-lg mb-2 drop-shadow">{nombreSistema || 'Sistema de Control de Abasto'}</p>
          <p className="font-semibold text-white/90 text-base mb-1 drop-shadow-sm">{temaGlobal?.reporte_subtitulo || 'Subsecretaría de Seguridad'}</p>
          <p className="text-white/80 text-sm drop-shadow-sm">
            {temaGlobal?.reporte_pie_pagina || 'Gobierno del Estado de México'} {temaGlobal?.reporte_ano_visible !== false ? '• 2025' : ''}
          </p>
        </div>
      </div>
    </div>
  );
}

export default RestablecerPassword;
