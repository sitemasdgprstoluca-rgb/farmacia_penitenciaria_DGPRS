/**
 * ResponsiveModal - Modal adaptativo para móvil y desktop
 * 
 * Features:
 * - En desktop: modal centrado con animación
 * - En móvil (<768px): modal pantalla completa
 * - Header fijo, body scrolleable
 * - Cierre con X, backdrop, o Escape
 */

import { useEffect, useCallback } from 'react';
import { FaTimes } from 'react-icons/fa';
import { useIsMobile } from './ResponsiveTable';

/**
 * ResponsiveModal Component
 * 
 * @param {Boolean} isOpen - Controla visibilidad del modal
 * @param {Function} onClose - Callback al cerrar
 * @param {String} title - Título del modal
 * @param {React.ReactNode} children - Contenido del modal
 * @param {String} size - Tamaño: 'sm' | 'md' | 'lg' | 'xl' | 'full'
 * @param {React.ReactNode} footer - Contenido del footer (botones)
 * @param {Boolean} closeOnBackdrop - Si cierra al clickear backdrop
 * @param {Boolean} showCloseButton - Mostrar botón X
 */
const ResponsiveModal = ({
  isOpen,
  onClose,
  title,
  children,
  size = 'md',
  footer,
  closeOnBackdrop = true,
  showCloseButton = true,
  className = '',
}) => {
  const isMobile = useIsMobile();

  // Cerrar con Escape
  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Escape' && isOpen) {
      onClose();
    }
  }, [isOpen, onClose]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  // Bloquear scroll del body cuando está abierto
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  // Determinar ancho según size (solo aplica en desktop)
  const sizeClasses = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
    full: 'max-w-6xl',
  };

  const handleBackdropClick = (e) => {
    if (closeOnBackdrop && e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center"
      onClick={handleBackdropClick}
    >
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/50 backdrop-blur-sm transition-opacity duration-300"
        style={{ animation: 'fadeIn 0.2s ease-out' }}
      />

      {/* Modal Container */}
      <div 
        className={`
          relative z-10 flex flex-col bg-white
          ${isMobile 
            ? 'w-full h-full' 
            : `${sizeClasses[size]} w-full mx-4 rounded-2xl shadow-2xl max-h-[90vh]`
          }
          ${className}
        `}
        style={{ 
          animation: isMobile 
            ? 'slideUp 0.3s ease-out' 
            : 'scaleIn 0.2s ease-out',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div 
          className={`
            flex items-center justify-between gap-4 px-4 sm:px-6 py-4
            ${isMobile ? '' : 'rounded-t-2xl'}
          `}
          style={{
            background: 'linear-gradient(135deg, var(--color-primary, #932043) 0%, var(--color-primary-hover, #632842) 100%)',
            minHeight: isMobile ? '60px' : '56px',
          }}
        >
          <h2 
            className="text-lg font-bold truncate"
            style={{ color: 'white' }}
          >
            {title}
          </h2>
          
          {showCloseButton && (
            <button
              onClick={onClose}
              className="flex items-center justify-center w-10 h-10 rounded-full transition-colors hover:bg-white/20"
              style={{ color: 'white' }}
              aria-label="Cerrar"
            >
              <FaTimes size={18} />
            </button>
          )}
        </div>

        {/* Body - Scrolleable */}
        <div 
          className="flex-1 overflow-y-auto p-4 sm:p-6"
          style={{ 
            WebkitOverflowScrolling: 'touch',
          }}
        >
          {children}
        </div>

        {/* Footer */}
        {footer && (
          <div 
            className={`
              px-4 sm:px-6 py-4 flex flex-wrap gap-2 justify-end
              ${isMobile ? 'pb-safe' : 'rounded-b-2xl'}
            `}
            style={{
              borderTop: '1px solid var(--color-border, #e7e5e4)',
              paddingBottom: isMobile ? 'max(1rem, env(safe-area-inset-bottom))' : '1rem',
            }}
          >
            {footer}
          </div>
        )}
      </div>

      {/* Keyframes para animaciones */}
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes scaleIn {
          from { 
            opacity: 0;
            transform: scale(0.95);
          }
          to { 
            opacity: 1;
            transform: scale(1);
          }
        }
        @keyframes slideUp {
          from { 
            opacity: 0;
            transform: translateY(100%);
          }
          to { 
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  );
};

export default ResponsiveModal;
