import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { FaUser, FaLock, FaSignInAlt, FaSpinner, FaEye, FaEyeSlash, FaShieldAlt, FaFingerprint } from 'react-icons/fa';
import { authAPI } from '../services/api';
import { usePermissions } from '../hooks/usePermissions';
import { useTheme } from '../hooks/useTheme';
import { setAccessToken, clearTokens } from '../services/tokenManager';

// 🎨 Componente de partículas flotantes animadas
const FloatingParticles = () => (
  <div className="absolute inset-0 overflow-hidden pointer-events-none">
    {[...Array(20)].map((_, i) => (
      <div
        key={i}
        className="absolute rounded-full bg-white/10 animate-float"
        style={{
          width: `${Math.random() * 10 + 5}px`,
          height: `${Math.random() * 10 + 5}px`,
          left: `${Math.random() * 100}%`,
          top: `${Math.random() * 100}%`,
          animationDelay: `${Math.random() * 5}s`,
          animationDuration: `${Math.random() * 10 + 10}s`,
        }}
      />
    ))}
  </div>
);

// 🌟 Componente de anillos concéntricos animados
const AnimatedRings = () => (
  <div className="absolute inset-0 flex items-center justify-center pointer-events-none overflow-hidden">
    {[...Array(3)].map((_, i) => (
      <div
        key={i}
        className="absolute rounded-full border border-white/5 animate-pulse-ring"
        style={{
          width: `${(i + 1) * 300}px`,
          height: `${(i + 1) * 300}px`,
          animationDelay: `${i * 0.5}s`,
        }}
      />
    ))}
  </div>
);

// ✨ Input con efectos premium
const PremiumInput = ({ icon: Icon, label, error, ...props }) => {
  const [isFocused, setIsFocused] = useState(false);
  
  return (
    <div className="group">
      <label 
        className={`block text-xs font-bold uppercase tracking-wider mb-2 transition-all duration-300 ${
          isFocused ? 'text-theme-primary' : 'text-gray-500'
        }`}
      >
        {label}
      </label>
      <div className="relative">
        <div className={`absolute left-0 top-0 bottom-0 w-12 flex items-center justify-center rounded-l-xl transition-all duration-300 ${
          isFocused 
            ? 'bg-theme-gradient text-white' 
            : 'bg-gray-100 text-gray-400'
        }`}>
          <Icon size={16} />
        </div>
        <input
          {...props}
          onFocus={(e) => { setIsFocused(true); props.onFocus?.(e); }}
          onBlur={(e) => { setIsFocused(false); props.onBlur?.(e); }}
          className={`w-full pl-14 pr-4 py-4 bg-gray-50 border-2 rounded-xl transition-all duration-300 text-gray-800 placeholder-gray-400 ${
            isFocused 
              ? 'border-theme-primary ring-4 ring-theme-primary/10 bg-white shadow-lg' 
              : 'border-gray-200 hover:border-gray-300'
          } ${error ? 'border-red-400 ring-4 ring-red-100' : ''}`}
          style={{
            '--tw-ring-color': isFocused ? 'rgba(147, 32, 67, 0.15)' : 'transparent', /* Pantone 7420C */
          }}
        />
        {props.type === 'password' && props.togglePassword && (
          <button
            type="button"
            onClick={props.togglePassword}
            className={`absolute right-4 top-1/2 -translate-y-1/2 transition-all duration-300 ${
              isFocused ? 'text-theme-primary' : 'text-gray-400 hover:text-gray-600'
            }`}
            tabIndex={-1}
          >
            {props.showPassword ? <FaEyeSlash size={18} /> : <FaEye size={18} />}
          </button>
        )}
      </div>
    </div>
  );
};

function Login() {
  const [credentials, setCredentials] = useState({ username: '', password: '' });
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [mounted, setMounted] = useState(false);
  const navigate = useNavigate();
  const { recargarUsuario } = usePermissions();
  const { temaGlobal, logoLoginUrl, nombreSistema } = useTheme();

  // Animación de entrada
  useEffect(() => {
    const timer = setTimeout(() => setMounted(true), 100);
    return () => clearTimeout(timer);
  }, []);

  const persistSession = (user, accessToken) => {
    if (accessToken) {
      setAccessToken(accessToken);
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

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage('');
    setLoading(true);

    try {
      await loginWithBackend(credentials);
      await recargarUsuario();
      toast.success('Inicio de sesión exitoso');
      navigate('/dashboard');
    } catch (error) {
      clearTokens();
      localStorage.removeItem('user');
      
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
      } else {
        setErrorMessage('Error al conectar con el servidor');
        toast.error('No fue posible iniciar sesión');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex relative overflow-hidden">
      {/* 🎨 Fondo con gradiente dinámico del tema - Colores Pantone Institucionales */}
      <div 
        className="absolute inset-0 transition-all duration-1000"
        style={{
          background: `
            radial-gradient(ellipse at 20% 20%, rgba(155, 126, 76, 0.15) 0%, transparent 50%),
            radial-gradient(ellipse at 80% 80%, rgba(0,0,0,0.25) 0%, transparent 50%),
            linear-gradient(135deg, 
              var(--color-primary, #932043) 0%, 
              var(--color-primary-hover, #632842) 50%, 
              ${temaGlobal?.color_primario_hover || '#632842'} 100%
            )
          `,
        }}
      />
      
      {/* Efectos visuales de fondo */}
      <FloatingParticles />
      <AnimatedRings />
      
      {/* 📱 Layout de dos columnas en desktop */}
      <div className="relative z-10 w-full flex flex-col lg:flex-row min-h-screen">
        
        {/* 🖼️ Panel Izquierdo - Branding (visible en lg+) */}
        <div className={`hidden lg:flex lg:w-1/2 xl:w-3/5 flex-col justify-center items-center p-12 transition-all duration-1000 ${
          mounted ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-10'
        }`}>
          <div className="max-w-lg text-center space-y-8">
            {/* Logo grande con efecto glassmorphism */}
            <div className="relative group">
              <div className="absolute -inset-4 bg-white/10 rounded-3xl blur-xl group-hover:bg-white/20 transition-all duration-500" />
              <div className="relative bg-white/10 backdrop-blur-xl rounded-3xl p-8 border border-white/20 shadow-2xl">
                <img 
                  src={logoLoginUrl || "/logo-sistema.png"} 
                  alt="Logo del Sistema" 
                  className="h-48 w-auto mx-auto object-contain filter drop-shadow-2xl transition-transform duration-500 group-hover:scale-105"
                  onError={(e) => { e.target.src = "/logo-sistema.png"; }}
                />
              </div>
            </div>
            
            {/* Título con efecto de texto */}
            <div className="space-y-4">
              <h1 className="text-4xl xl:text-5xl font-black text-white leading-tight tracking-tight">
                {nombreSistema || temaGlobal?.reporte_titulo_institucion || 'Sistema de Farmacia'}
                <span className="block text-2xl xl:text-3xl font-light mt-2 text-white/80">
                  Penitenciaria
                </span>
              </h1>
              
              {/* Línea decorativa con dorado institucional Pantone 7504C */}
              <div 
                className="h-1 w-32 mx-auto rounded-full" 
                style={{ background: 'linear-gradient(90deg, transparent, var(--pantone-7504c, #9B7E4C), var(--pantone-467c, #C9A876), var(--pantone-7504c, #9B7E4C), transparent)' }}
              />
              
              <p className="text-lg text-white/70 font-light max-w-md mx-auto">
                Gestión integral de medicamentos e insumos para centros penitenciarios
              </p>
            </div>
            
            {/* Características destacadas */}
            <div className="grid grid-cols-3 gap-4 pt-8">
              {[
                { icon: FaShieldAlt, label: 'Seguro' },
                { icon: FaFingerprint, label: 'Trazable' },
                { icon: FaUser, label: 'Rol-Based' },
              ].map(({ icon: Icon, label }) => (
                <div key={label} className="flex flex-col items-center gap-2 text-white/60 hover:text-white/90 transition-colors">
                  <div className="w-12 h-12 rounded-xl bg-white/10 flex items-center justify-center backdrop-blur-sm border border-white/10">
                    <Icon size={20} />
                  </div>
                  <span className="text-xs font-medium">{label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
        
        {/* 📝 Panel Derecho - Formulario de Login */}
        <div className={`w-full lg:w-1/2 xl:w-2/5 flex items-center justify-center p-4 sm:p-8 transition-all duration-1000 delay-300 ${
          mounted ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-10'
        }`}>
          <div className="w-full max-w-md">
            
            {/* Logo móvil (visible solo en < lg) */}
            <div className="lg:hidden text-center mb-8">
              <div className="inline-block bg-white/10 backdrop-blur-xl rounded-2xl p-4 border border-white/20 shadow-xl mb-4">
                <img 
                  src={logoLoginUrl || "/logo-sistema.png"} 
                  alt="Logo" 
                  className="h-24 w-auto mx-auto object-contain"
                  onError={(e) => { e.target.src = "/logo-sistema.png"; }}
                />
              </div>
              <h1 className="text-2xl font-bold text-white">
                {nombreSistema || 'Sistema de Farmacia'}
              </h1>
            </div>
            
            {/* Card del formulario con glassmorphism */}
            <div className="relative group">
              {/* Glow effect */}
              <div className="absolute -inset-1 bg-gradient-to-r from-white/20 via-white/10 to-white/20 rounded-3xl blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
              
              <div className="relative bg-white/95 backdrop-blur-2xl rounded-3xl shadow-2xl overflow-hidden border border-white/50">
                {/* Header del formulario */}
                <div 
                  className="bg-theme-gradient px-8 py-6 relative overflow-hidden"
                >
                  <div className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/10 to-white/0 animate-shimmer" />
                  <div className="relative flex items-center gap-4">
                    <div className="w-14 h-14 rounded-2xl bg-white/20 backdrop-blur-sm flex items-center justify-center border border-white/30 shadow-lg">
                      <FaSignInAlt className="text-white text-xl" />
                    </div>
                    <div>
                      <h2 className="text-xl font-bold text-white">Bienvenido</h2>
                      <p className="text-white/70 text-sm">Ingresa tus credenciales para continuar</p>
                    </div>
                  </div>
                </div>
                
                {/* Cuerpo del formulario */}
                <div className="p-8">
                  <form onSubmit={handleSubmit} className="space-y-6">
                    {/* Mensaje de error con animación */}
                    {errorMessage && (
                      <div className="animate-shake rounded-xl bg-gradient-to-r from-red-50 to-rose-50 border border-red-200 px-4 py-3 flex items-center gap-3 shadow-sm">
                        <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0">
                          <span className="text-red-500 text-sm">⚠️</span>
                        </div>
                        <p className="text-sm text-red-700 font-medium">{errorMessage}</p>
                      </div>
                    )}

                    {/* Input de usuario */}
                    <PremiumInput
                      icon={FaUser}
                      label="Usuario o correo electrónico"
                      type="text"
                      value={credentials.username}
                      onChange={(e) => setCredentials({ ...credentials, username: e.target.value })}
                      placeholder="ejemplo@correo.com"
                      required
                      autoComplete="username"
                    />

                    {/* Input de contraseña */}
                    <PremiumInput
                      icon={FaLock}
                      label="Contraseña"
                      type={showPassword ? "text" : "password"}
                      value={credentials.password}
                      onChange={(e) => setCredentials({ ...credentials, password: e.target.value })}
                      placeholder="••••••••••"
                      required
                      autoComplete="current-password"
                      showPassword={showPassword}
                      togglePassword={() => setShowPassword(!showPassword)}
                    />

                    {/* Link olvidé contraseña */}
                    <div className="flex justify-end">
                      <Link 
                        to="/recuperar-password" 
                        className="text-sm font-medium text-theme-primary hover:text-theme-primary-hover transition-colors hover:underline underline-offset-4"
                      >
                        ¿Olvidaste tu contraseña?
                      </Link>
                    </div>

                    {/* Botón de submit premium */}
                    <button
                      type="submit"
                      disabled={loading}
                      className="relative w-full overflow-hidden text-white py-4 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed font-bold shadow-xl transition-all duration-300 transform hover:scale-[1.02] hover:shadow-2xl active:scale-[0.98] group bg-theme-gradient"
                    >
                      {/* Efecto de brillo */}
                      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700" />
                      
                      <span className="relative flex items-center justify-center gap-3">
                        {loading ? (
                          <>
                            <FaSpinner className="animate-spin" size={18} />
                            <span>Verificando credenciales...</span>
                          </>
                        ) : (
                          <>
                            <FaSignInAlt size={18} />
                            <span>Iniciar Sesión</span>
                          </>
                        )}
                      </span>
                    </button>
                  </form>
                </div>
              </div>
            </div>
            
            {/* Footer institucional */}
            <div className={`mt-8 text-center space-y-2 transition-all duration-1000 delay-500 ${
              mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
            }`}>
              <p className="text-white font-semibold text-sm">
                {temaGlobal?.reporte_subtitulo || 'Gobierno del Estado de México'}
              </p>
              <p className="text-white/60 text-xs">
                {temaGlobal?.reporte_pie_pagina || 'Subsecretaría de Seguridad'} 
                {temaGlobal?.reporte_ano_visible !== false && ` • ${new Date().getFullYear()}`}
              </p>
              <div className="flex items-center justify-center gap-2 pt-2">
                <div className="h-px w-8 bg-gradient-to-r from-transparent to-white/30" />
                <span className="text-white/40 text-xs">Sistema Seguro</span>
                <div className="h-px w-8 bg-gradient-to-r from-white/30 to-transparent" />
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* 🎨 Estilos de animaciones */}
      <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0) rotate(0deg); opacity: 0.5; }
          50% { transform: translateY(-20px) rotate(180deg); opacity: 0.8; }
        }
        
        @keyframes pulse-ring {
          0% { transform: scale(0.8); opacity: 0.5; }
          50% { transform: scale(1); opacity: 0.2; }
          100% { transform: scale(0.8); opacity: 0.5; }
        }
        
        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
        
        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          10%, 30%, 50%, 70%, 90% { transform: translateX(-4px); }
          20%, 40%, 60%, 80% { transform: translateX(4px); }
        }
        
        .animate-float {
          animation: float linear infinite;
        }
        
        .animate-pulse-ring {
          animation: pulse-ring 4s ease-in-out infinite;
        }
        
        .animate-shimmer {
          animation: shimmer 3s ease-in-out infinite;
        }
        
        .animate-shake {
          animation: shake 0.5s ease-in-out;
        }
        
        /* Colores usando variables CSS del tema (respeta Personalizar Tema) */
        /* Fallbacks: Pantone 7420C (#932043) y Pantone 504C (#632842) */
        .text-theme-primary {
          color: var(--color-primary, #932043);
        }
        
        .text-theme-primary-hover {
          color: var(--color-primary-hover, #632842);
        }
        
        .border-theme-primary {
          border-color: var(--color-primary, #932043);
        }
        
        .ring-theme-primary\\/10 {
          --tw-ring-color: rgba(147, 32, 67, 0.1); /* Pantone 7420C */
        }
        
        /* Colores dorados institucionales Pantone */
        .text-pantone-gold {
          color: var(--pantone-7504c, #9B7E4C);
        }
        
        .border-pantone-gold {
          border-color: var(--pantone-467c, #C9A876);
        }
      `}</style>
    </div>
  );
}

export default Login;
