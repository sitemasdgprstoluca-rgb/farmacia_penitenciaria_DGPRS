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
    let nombreCentro = '';
    if (value === 'central') {
      nombreCentro = 'Farmacia Central';
    } else if (value === 'todos') {
      nombreCentro = 'Todos los centros';
    } else {
      const centroSeleccionado = centros.find(c => String(c.id) === value);
      nombreCentro = centroSeleccionado ? centroSeleccionado.nombre : '';
    }
    onCentroChange?.(value, nombreCentro);
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
      <label className="text-sm font-medium text-gray-600 flex items-center gap-1.5 whitespace-nowrap">
        <FaBuilding style={{ color: 'var(--color-primary, #9F2241)' }} />
        Centro:
      </label>
      <select
        value={selectedValue}
        onChange={handleChange}
        className="px-3 py-2 border border-gray-200 rounded-xl shadow-sm text-sm min-w-[200px] bg-white
          focus:ring-2 focus:border-transparent transition-all appearance-none cursor-pointer
          hover:border-gray-300 font-medium text-gray-700"
        style={{ 
          focusRingColor: 'var(--color-primary, #9F2241)',
          backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%236B7280' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E")`,
          backgroundRepeat: 'no-repeat',
          backgroundPosition: 'right 10px center',
          paddingRight: '30px'
        }}
      >
        <option value="central">
          🏥 Farmacia Central
        </option>
        <option value="todos">
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
