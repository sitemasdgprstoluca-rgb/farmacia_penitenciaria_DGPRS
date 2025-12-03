import { useContext } from 'react';
import { PermissionContext } from '../context/contexts';

/**
 * Hook para acceder al contexto de permisos.
 * 
 * NOTA: Ahora retorna un objeto seguro con permisos vacíos si el contexto no está montado,
 * en lugar de lanzar una excepción. Esto evita romper la UI en tests o componentes
 * que se renderizan antes de que el PermissionProvider esté listo.
 */
export function usePermissions() {
  const context = useContext(PermissionContext);
  
  // Si no hay contexto, retornar un objeto seguro con valores por defecto
  // Esto evita romper la UI y permite que los componentes se degraden gracefully
  if (!context) {
    console.warn('usePermissions: PermissionContext no disponible, usando valores por defecto');
    return {
      permisos: {},
      user: null,
      loading: true,
      verificarPermiso: () => false,
      getRolPrincipal: () => 'SIN_ROL',
      recargarUsuario: async () => {},
      logout: () => {},
    };
  }
  
  return context;
}
