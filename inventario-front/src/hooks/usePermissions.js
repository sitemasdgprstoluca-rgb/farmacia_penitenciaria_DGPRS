import { useContext } from 'react';
import { PermissionContext } from '../context/contexts';

export function usePermissions() {
  const context = useContext(PermissionContext);
  if (!context) {
    throw new Error('usePermissions debe usarse dentro de PermissionProvider');
  }
  return context;
}
