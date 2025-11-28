/**
 * Selector de Centro para usuarios admin/farmacia/vista
 * 
 * Permite filtrar datos por centro específico o ver todos (global).
 * Solo se muestra a usuarios con roles privilegiados.
 * Los usuarios de centro están forzados a su centro asignado.
 */

import { useState, useEffect } from 'react';
import { FaBuilding } from 'react-icons/fa';
import { centrosAPI } from '../services/api';
import { usePermissions } from '../hooks/usePermissions';

const CentroSelector = ({ onCentroChange, selectedValue = '', className = '' }) => {
  const { permisos, getRolPrincipal } = usePermissions();
  const [centros, setCentros] = useState([]);
  const [loading, setLoading] = useState(true);

  // Solo mostrar a usuarios con acceso global
  const rolPrincipal = getRolPrincipal();
  const puedeVerGlobal = ['ADMIN', 'FARMACIA', 'VISTA'].includes(rolPrincipal) || permisos?.isSuperuser;
  
  useEffect(() => {
    if (!puedeVerGlobal) {
      setLoading(false);
      return;
    }
    
    const fetchCentros = async () => {
      try {
        const response = await centrosAPI.getAll({ 
          page_size: 100, 
          ordering: 'nombre',
          activo: true 
        });
        const centrosData = response.data.results || response.data || [];
        setCentros(centrosData);
      } catch (error) {
        console.error('Error al cargar centros:', error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchCentros();
  }, [puedeVerGlobal]);

  const handleChange = (e) => {
    const value = e.target.value;
    // Encontrar el nombre del centro seleccionado
    const centroSeleccionado = centros.find(c => String(c.id) === value);
    const nombreCentro = centroSeleccionado ? centroSeleccionado.nombre : '';
    onCentroChange?.(value === '' ? null : value, nombreCentro); // null = global, ID string = centro específico
  };

  // No renderizar si el usuario no tiene acceso global
  if (!puedeVerGlobal) {
    return null;
  }

  if (loading) {
    return (
      <div className={`centro-selector ${className}`}>
        <div className="animate-pulse bg-gray-200 h-10 w-48 rounded"></div>
      </div>
    );
  }

  return (
    <div className={`centro-selector flex items-center gap-2 ${className}`}>
      <label className="text-sm font-medium text-gray-700 flex items-center gap-1">
        <FaBuilding className="text-guinda" />
        Centro:
      </label>
      <select
        value={selectedValue || ''}
        onChange={handleChange}
        className="px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-guinda focus:border-guinda text-sm min-w-[200px]"
      >
        <option value="">
          🌐 Todos los centros
        </option>
        {centros.map((centro) => (
          <option key={centro.id} value={String(centro.id)}>
            {centro.nombre}
          </option>
        ))}
      </select>
    </div>
  );
};

export default CentroSelector;
