import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { FaUser, FaLock, FaSignInAlt, FaSpinner, FaEye, FaEyeSlash, FaShieldAlt, FaRoute } from 'react-icons/fa';
import { authAPI } from '../services/api';
import { usePermissions } from '../hooks/usePermissions';
import { useTheme } from '../hooks/useTheme';
import { setAccessToken, clearTokens } from '../services/tokenManager';

// 🎨 Componente de partículas flotantes animadas - MÁS VISIBLES
const FloatingParticles = () => (
  <div className="absolute inset-0 overflow-hidden pointer-events-none">
    {[...Array(30)].map((_, i) => (
      <div
        key={i}
        className="absolute rounded-full animate-float"
        style={{
          width: `${Math.random() * 12 + 6}px`,
          height: `${Math.random() * 12 + 6}px`,
          left: `${Math.random() * 100}%`,
          top: `${Math.random() * 100}%`,
          animationDelay: `${Math.random() * 5}s`,
          animationDuration: `${Math.random() * 8 + 8}s`,
          background: i % 3 === 0 
            ? 'rgba(201, 168, 118, 0.4)' // Dorado
            : i % 3 === 1 
              ? 'rgba(255, 255, 255, 0.3)' // Blanco
              : 'rgba(255, 255, 255, 0.15)', // Blanco suave
          boxShadow: i % 3 === 0 
            ? '0 0 10px rgba(201, 168, 118, 0.5)' 
            : '0 0 8px rgba(255, 255, 255, 0.3)',
        }}
      />
    ))}
  </div>
);

// 🌟 Componente de anillos concéntricos animados - MÁS VISIBLES
const AnimatedRings = () => (
  <div className="absolute inset-0 flex items-center justify-center pointer-events-none overflow-hidden">
    {[...Array(4)].map((_, i) => (
      <div
        key={i}
        className="absolute rounded-full animate-pulse-ring"
        style={{
          width: `${(i + 1) * 250}px`,
          height: `${(i + 1) * 250}px`,
          animationDelay: `${i * 0.7}s`,
          border: i % 2 === 0 
            ? '2px solid rgba(201, 168, 118, 0.25)' // Dorado
            : '1px solid rgba(255, 255, 255, 0.15)', // Blanco
          boxShadow: i % 2 === 0 
            ? '0 0 20px rgba(201, 168, 118, 0.15), inset 0 0 20px rgba(201, 168, 118, 0.05)' 
            : 'none',
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
    <div className="min-h-screen w-full flex relative overflow-hidden bg-gray-50">
      
      {/* 📱 Layout: Formulario izquierda, Branding derecha */}
      <div className="relative z-10 w-full flex flex-col lg:flex-row min-h-screen">
        
        {/* ═══════════════════════════════════════════════════════════════════
            📝 PANEL IZQUIERDO - Formulario (fondo claro)
            ═══════════════════════════════════════════════════════════════════ */}
        <div className={`w-full lg:w-[45%] xl:w-[40%] flex flex-col justify-center items-center p-6 sm:p-8 lg:p-12 bg-white transition-all duration-1000 ${
          mounted ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-10'
        }`}>
          <div className="w-full max-w-md">
            
            {/* Header del formulario */}
            <div className="text-center mb-10">
              <h1 className="text-3xl sm:text-4xl font-bold text-gray-800">
                Iniciar Sesión
              </h1>
              <p className="text-gray-500 text-sm mt-3">
                Ingresa tus credenciales para acceder al sistema
              </p>
            </div>
            
            {/* Formulario */}
            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Mensaje de error */}
              {errorMessage && (
                <div className="animate-shake rounded-xl bg-red-50 border border-red-200 px-4 py-3 flex items-center gap-3">
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

              {/* Botón de submit */}
              <button
                type="submit"
                disabled={loading}
                className="relative w-full overflow-hidden text-white py-4 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed font-bold shadow-lg transition-all duration-300 transform hover:scale-[1.02] hover:shadow-xl active:scale-[0.98] group bg-theme-gradient"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700" />
                
                <span className="relative flex items-center justify-center gap-3">
                  {loading ? (
                    <>
                      <FaSpinner className="animate-spin" size={18} />
                      <span>Verificando...</span>
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
            
            {/* Footer en móvil */}
            <div className="lg:hidden mt-8 pt-6 border-t border-gray-100 text-center">
              <p className="text-gray-600 font-medium text-sm">
                {temaGlobal?.reporte_subtitulo || 'Gobierno del Estado de México'}
              </p>
              <p className="text-gray-400 text-xs mt-1">
                {temaGlobal?.reporte_pie_pagina || 'Subsecretaría de Seguridad'} · {new Date().getFullYear()}
              </p>
            </div>
          </div>
        </div>
        
        {/* ═══════════════════════════════════════════════════════════════════
            🎨 PANEL DERECHO - Branding (gradiente institucional)
            ═══════════════════════════════════════════════════════════════════ */}
        <div className={`hidden lg:flex lg:w-[55%] xl:w-[60%] relative overflow-hidden transition-all duration-1000 delay-200 ${
          mounted ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-10'
        }`}>
          {/* Fondo con gradiente */}
          <div 
            className="absolute inset-0"
            style={{
              background: `
                radial-gradient(ellipse at 30% 20%, rgba(155, 126, 76, 0.2) 0%, transparent 50%),
                radial-gradient(ellipse at 70% 80%, rgba(0,0,0,0.3) 0%, transparent 50%),
                linear-gradient(135deg, 
                  var(--color-primary, #932043) 0%, 
                  var(--color-primary-hover, #632842) 60%, 
                  ${temaGlobal?.color_primario_hover || '#4a1a2e'} 100%
                )
              `,
            }}
          />
          
          {/* Efectos visuales */}
          <FloatingParticles />
          <AnimatedRings />
          
          {/* Contenido del branding */}
          <div className="relative z-10 flex flex-col justify-center items-center p-12 xl:p-16 w-full">
            <div className="max-w-lg text-center space-y-8">
              
              {/* Logo con fondo que resalta */}
              <div className="relative group mb-4">
                <div className="absolute inset-0 bg-white/20 rounded-3xl blur-xl scale-110 group-hover:bg-white/30 transition-all duration-500" />
                <div className="relative bg-white/95 backdrop-blur-sm rounded-2xl p-6 shadow-2xl">
                  <img 
                    src={logoLoginUrl || "/logo-sistema.png"} 
                    alt="Logo del Sistema" 
                    className="h-32 xl:h-40 w-auto mx-auto object-contain transition-transform duration-500 group-hover:scale-105"
                    onError={(e) => { e.target.src = "/logo-sistema.png"; }}
                  />
                </div>
              </div>
              
              {/* Título principal - Sin duplicación */}
              <div className="space-y-3">
                <h2 className="text-3xl xl:text-4xl font-black text-white leading-tight tracking-tight drop-shadow-lg">
                  {nombreSistema || temaGlobal?.reporte_titulo_institucion || 'Sistema de Farmacia Penitenciaria'}
                </h2>
                
                {/* Línea decorativa dorada más visible */}
                <div className="flex items-center justify-center gap-4 py-4">
                  <div className="h-0.5 w-16 bg-gradient-to-r from-transparent via-[#C9A876] to-[#C9A876] rounded-full" />
                  <div className="w-3 h-3 rounded-full bg-[#C9A876] shadow-lg shadow-[#C9A876]/50 animate-pulse" />
                  <div className="h-0.5 w-16 bg-gradient-to-l from-transparent via-[#C9A876] to-[#C9A876] rounded-full" />
                </div>
              </div>
              
              {/* Mensaje descriptivo - Estilo card sutil */}
              <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-6 border border-white/10">
                <h3 className="text-lg font-semibold text-white mb-2">
                  Gestión Integral de Medicamentos
                </h3>
                <p className="text-white/60 text-sm leading-relaxed">
                  Control de inventario, trazabilidad completa y distribución 
                  eficiente de medicamentos e insumos para centros penitenciarios.
                </p>
              </div>
              
              {/* Características */}
              <div className="flex justify-center gap-6 pt-4">
                {[
                  { icon: FaShieldAlt, label: 'Seguro' },
                  { icon: FaRoute, label: 'Trazable' },
                  { icon: FaUser, label: 'Rol-Based' },
                ].map(({ icon: Icon, label }) => (
                  <div key={label} className="flex flex-col items-center gap-2 group">
                    <div className="w-12 h-12 rounded-xl bg-white/10 flex items-center justify-center transition-all duration-300 group-hover:bg-white/20 group-hover:scale-110">
                      <Icon size={20} className="text-white/60 group-hover:text-white transition-colors" />
                    </div>
                    <span className="text-xs text-white/50 group-hover:text-white/70 transition-colors">{label}</span>
                  </div>
                ))}
              </div>
              
              {/* Footer institucional */}
              <div className="pt-8 border-t border-white/10">
                <p className="text-white/80 font-medium text-sm">
                  {temaGlobal?.reporte_subtitulo || 'Gobierno del Estado de México'}
                </p>
                <p className="text-white/40 text-xs mt-1">
                  {temaGlobal?.reporte_pie_pagina || 'Subsecretaría de Seguridad'} · {new Date().getFullYear()}
                </p>
              </div>
            </div>
          </div>
          
          {/* Decoración esquina inferior */}
          <div className="absolute bottom-0 right-0 w-64 h-64 opacity-10">
            <div className="absolute bottom-0 right-0 w-full h-full bg-white rounded-tl-full" />
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
