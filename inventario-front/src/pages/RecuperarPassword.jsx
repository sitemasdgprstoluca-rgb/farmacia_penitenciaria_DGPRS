import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { FaEnvelope, FaArrowLeft, FaPaperPlane, FaSpinner, FaCheckCircle, FaShieldAlt, FaLock } from 'react-icons/fa';
import { passwordResetAPI } from '../services/api';
import { useTheme } from '../hooks/useTheme';

// 🎨 Partículas flotantes (mismas del Login)
const FloatingParticles = () => {
  const particles = Array.from({ length: 20 }, (_, i) => ({
    id: i,
    size: Math.random() * 4 + 2,
    left: Math.random() * 100,
    delay: Math.random() * 5,
    duration: Math.random() * 10 + 15,
    color: i % 3 === 0 ? '#C9A876' : 'rgba(255,255,255,0.4)',
  }));

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {particles.map((p) => (
        <div
          key={p.id}
          className="absolute rounded-full animate-float"
          style={{
            width: p.size,
            height: p.size,
            left: `${p.left}%`,
            top: '100%',
            backgroundColor: p.color,
            animationDelay: `${p.delay}s`,
            animationDuration: `${p.duration}s`,
            boxShadow: p.color === '#C9A876' ? '0 0 6px rgba(201, 168, 118, 0.5)' : 'none',
          }}
        />
      ))}
    </div>
  );
};

// 🔵 Anillos animados
const AnimatedRings = () => (
  <div className="absolute inset-0 overflow-hidden pointer-events-none">
    {[1, 2, 3].map((i) => (
      <div
        key={i}
        className="absolute rounded-full border border-[#C9A876]/20 animate-pulse-ring"
        style={{
          width: `${200 + i * 150}px`,
          height: `${200 + i * 150}px`,
          left: '50%',
          top: '50%',
          transform: 'translate(-50%, -50%)',
          animationDelay: `${i * 0.5}s`,
        }}
      />
    ))}
  </div>
);

function RecuperarPassword() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [enviado, setEnviado] = useState(false);
  const [debugInfo, setDebugInfo] = useState(null);
  const [mounted, setMounted] = useState(false);
  const [exiting, setExiting] = useState(false);
  const navigate = useNavigate();
  const { temaGlobal, logoLoginUrl, nombreSistema } = useTheme();

  // Animación de entrada
  useEffect(() => {
    const timer = setTimeout(() => setMounted(true), 100);
    return () => clearTimeout(timer);
  }, []);

  // Navegación con transición suave
  const navigateWithTransition = (path) => {
    setExiting(true);
    setTimeout(() => navigate(path), 300);
  };

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
    <div className={`min-h-screen w-full flex transition-all duration-300 ${
      exiting ? 'opacity-0 scale-95' : 'opacity-100 scale-100'
    }`}>
      {/* ========================================= */}
      {/* 📋 PANEL IZQUIERDO - Formulario */}
      {/* ========================================= */}
      <div className={`w-full lg:w-1/2 flex flex-col justify-center items-center p-8 lg:p-16 bg-white transition-all duration-500 ${
        mounted && !exiting ? 'opacity-100 translate-x-0' : exiting ? 'opacity-0 translate-x-10' : 'opacity-0 translate-x-10'
      }`}>
        <div className="w-full max-w-md">
          {/* Logo para móvil */}
          <div className="lg:hidden mb-8 text-center">
            <img 
              src={logoLoginUrl || "/logo-sistema.png"} 
              alt="Logo" 
              className="h-16 mx-auto mb-4"
              onError={(e) => { e.target.src = "/logo-sistema.png"; }}
            />
          </div>
          
          {/* Icono y título */}
          <div className="text-center mb-8">
            <div 
              className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg"
              style={{ 
                background: `linear-gradient(135deg, var(--color-primary, #932043) 0%, var(--color-primary-hover, #632842) 100%)` 
              }}
            >
              <FaLock className="text-white text-2xl" />
            </div>
            <h1 className="text-3xl font-black text-gray-800 mb-2">
              {enviado ? '¡Correo Enviado!' : 'Recuperar Contraseña'}
            </h1>
            <p className="text-gray-500">
              {enviado 
                ? 'Revisa tu bandeja de entrada' 
                : 'Ingresa tu correo para restablecer tu contraseña'
              }
            </p>
          </div>
          
          {!enviado ? (
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Input de correo con estilo premium */}
              <div className="space-y-2">
                <label className="block text-sm font-bold text-gray-600 uppercase tracking-wide">
                  Correo electrónico
                </label>
                <div className="relative group">
                  <div className="absolute left-4 top-1/2 -translate-y-1/2 transition-all duration-300">
                    <FaEnvelope 
                      className="text-gray-400 group-focus-within:text-[var(--color-primary)] transition-colors" 
                      style={{ '--color-primary': temaGlobal?.color_primario || '#932043' }}
                    />
                  </div>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full pl-12 pr-4 py-4 bg-gray-50 border-2 border-gray-100 rounded-xl text-gray-800 placeholder-gray-400 transition-all duration-300 focus:bg-white focus:border-[var(--color-primary)] focus:ring-4 focus:ring-[var(--color-primary)]/10 focus:outline-none"
                    style={{ 
                      '--color-primary': temaGlobal?.color_primario || '#932043',
                    }}
                    placeholder="tu.correo@ejemplo.com"
                    required
                  />
                </div>
              </div>

              {/* Botón enviar */}
              <button
                type="submit"
                disabled={loading}
                className="relative w-full py-4 rounded-xl text-white font-bold text-lg shadow-xl transition-all duration-300 transform hover:scale-[1.02] hover:shadow-2xl active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none overflow-hidden group"
                style={{ 
                  background: `linear-gradient(135deg, var(--color-primary, #932043) 0%, var(--color-primary-hover, #632842) 100%)` 
                }}
              >
                <span className="relative z-10 flex items-center justify-center gap-3">
                  {loading ? (
                    <>
                      <FaSpinner className="animate-spin" />
                      Enviando...
                    </>
                  ) : (
                    <>
                      <FaPaperPlane />
                      Enviar enlace de recuperación
                    </>
                  )}
                </span>
                <div className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/20 to-white/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700" />
              </button>
            </form>
          ) : (
            /* Estado: Correo enviado */
            <div className="text-center py-6">
              <div className="w-20 h-20 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-6 shadow-lg">
                <FaCheckCircle className="text-emerald-500 text-4xl" />
              </div>
              
              <p className="text-gray-600 mb-6 leading-relaxed">
                Si el correo <span className="font-bold text-gray-800">{email}</span> está registrado, 
                recibirás un enlace para restablecer tu contraseña.
              </p>
              
              <p className="text-sm text-gray-400 mb-6">
                No olvides revisar tu carpeta de spam.
              </p>
              
              {/* Debug info para desarrollo */}
              {debugInfo && (
                <div className="mt-6 p-4 bg-amber-50 border border-amber-200 rounded-xl text-left">
                  <p className="text-xs text-amber-700 font-bold mb-2">
                    ⚠️ Modo desarrollo (email no configurado):
                  </p>
                  <p className="text-xs text-gray-600 break-all">
                    <strong>URL:</strong> {debugInfo.url}
                  </p>
                  <a 
                    href={debugInfo.url}
                    className="inline-block mt-2 text-sm font-medium hover:underline"
                    style={{ color: 'var(--color-primary, #932043)' }}
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
                className="mt-4 text-gray-500 hover:text-gray-700 font-medium transition-colors"
              >
                ← Enviar a otro correo
              </button>
            </div>
          )}

          {/* Link volver */}
          <div className="mt-8 pt-6 border-t border-gray-100 text-center">
            <button 
              type="button"
              onClick={() => navigateWithTransition('/login')}
              className="inline-flex items-center gap-2 font-medium transition-all duration-300 hover:opacity-80 hover:-translate-x-1"
              style={{ color: 'var(--color-primary, #932043)' }}
            >
              <FaArrowLeft className="transition-transform duration-300" />
              Volver al inicio de sesión
            </button>
          </div>
        </div>
      </div>
      
      {/* ========================================= */}
      {/* 🎨 PANEL DERECHO - Branding (solo desktop) */}
      {/* ========================================= */}
      <div className={`hidden lg:flex lg:w-1/2 relative overflow-hidden transition-all duration-500 delay-100 ${
        mounted && !exiting ? 'opacity-100 translate-x-0' : exiting ? 'opacity-0 -translate-x-10' : 'opacity-0 -translate-x-10'
      }`}>
        {/* Fondo gradiente */}
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
            
            {/* Logo directo sin contenedor */}
            <div className="relative group mb-4">
              <img 
                src={logoLoginUrl || "/logo-sistema.png"} 
                alt="Logo del Sistema" 
                className="h-32 xl:h-40 w-auto mx-auto object-contain transition-transform duration-500 group-hover:scale-105 drop-shadow-2xl"
                onError={(e) => { e.target.src = "/logo-sistema.png"; }}
              />
            </div>
            
            {/* Título principal */}
            <div className="space-y-3">
              <h2 className="text-3xl xl:text-4xl font-black text-white leading-tight tracking-tight drop-shadow-lg">
                {nombreSistema || temaGlobal?.reporte_titulo_institucion || 'Sistema de Farmacia Penitenciaria'}
              </h2>
              
              {/* Línea decorativa dorada */}
              <div className="flex items-center justify-center gap-4 py-4">
                <div className="h-0.5 w-16 bg-gradient-to-r from-transparent via-[#C9A876] to-[#C9A876] rounded-full" />
                <div className="w-3 h-3 rounded-full bg-[#C9A876] shadow-lg shadow-[#C9A876]/50" />
                <div className="h-0.5 w-16 bg-gradient-to-l from-transparent via-[#C9A876] to-[#C9A876] rounded-full" />
              </div>
            </div>
            
            {/* Mensaje descriptivo */}
            <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-6 border border-white/10">
              <h3 className="text-lg font-semibold text-white mb-2">
                Recuperación Segura
              </h3>
              <p className="text-white/60 text-sm leading-relaxed">
                Tu seguridad es nuestra prioridad. Recibirás un enlace único 
                y temporal para restablecer tu contraseña de forma segura.
              </p>
            </div>
            
            {/* Características */}
            <div className="flex justify-center gap-6 pt-4">
              {[
                { icon: FaShieldAlt, label: 'Seguro' },
                { icon: FaEnvelope, label: 'Email' },
                { icon: FaLock, label: 'Privado' },
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
      </div>
      
      {/* 🎨 Estilos de animaciones */}
      <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0) rotate(0deg); opacity: 0.5; }
          50% { transform: translateY(-20px) rotate(180deg); opacity: 0.8; }
        }
        
        @keyframes pulse-ring {
          0% { transform: translate(-50%, -50%) scale(0.8); opacity: 0.5; }
          50% { transform: translate(-50%, -50%) scale(1); opacity: 0.2; }
          100% { transform: translate(-50%, -50%) scale(0.8); opacity: 0.5; }
        }
        
        .animate-float {
          animation: float linear infinite;
        }
        
        .animate-pulse-ring {
          animation: pulse-ring 4s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
}

export default RecuperarPassword;
