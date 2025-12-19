import { useState, useEffect, useRef, useCallback } from 'react';
import { FaSpinner, FaSearch, FaCheckCircle, FaTimes, FaBox, FaLayerGroup, FaInfoCircle } from 'react-icons/fa';

/**
 * Componente avanzado de autocompletado con búsqueda en API
 * 
 * Características:
 * - Búsqueda en tiempo real con debounce
 * - Navegación por teclado (flechas, Enter, Escape)
 * - Muestra info detallada del producto (nombre, presentación, stock)
 * - Indicador visual cuando hay selección válida
 * - Modo productos con información enriquecida
 * - Soporte para limpiar selección
 * 
 * @param {Function} apiCall - Función de API que retorna una promesa con los resultados
 * @param {string} value - Valor actual del input
 * @param {Function} onChange - Callback cuando cambia el valor
 * @param {Function} onItemSelect - Callback cuando se selecciona un item (recibe el objeto completo)
 * @param {string} placeholder - Placeholder del input
 * @param {string} displayField - Campo principal a mostrar (ej: 'clave', 'numero_lote')
 * @param {string} searchField - Nombre del parámetro de búsqueda para la API (ej: 'search')
 * @param {string} secondaryField - Campo secundario (ej: 'nombre', 'descripcion')
 * @param {string} mode - Modo de visualización: 'product' | 'lote' | 'default'
 * @param {number} minChars - Mínimo de caracteres para iniciar búsqueda (default: 1)
 * @param {number} debounceMs - Tiempo de espera antes de buscar (default: 250ms)
 */
function AutocompleteInput({
  apiCall,
  value,
  onChange,
  onItemSelect,
  placeholder = '',
  displayField = 'nombre',
  searchField = 'search',
  secondaryField = 'descripcion',
  mode = 'default',
  minChars = 1,
  debounceMs = 250,
  className = '',
  disabled = false,
}) {
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [selectedItem, setSelectedItem] = useState(null); // Item seleccionado completo
  const [inputFocused, setInputFocused] = useState(false);
  const inputRef = useRef(null);
  const suggestionsRef = useRef(null);
  const debounceRef = useRef(null);
  const containerRef = useRef(null);

  // Búsqueda con debounce
  const searchItems = useCallback(async (searchTerm) => {
    if (!searchTerm || searchTerm.length < minChars) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    setLoading(true);
    try {
      const response = await apiCall({ [searchField]: searchTerm, page_size: 15 });
      const items = response.data?.results || response.data || [];
      setSuggestions(items);
      setShowSuggestions(items.length > 0);
    } catch (error) {
      console.error('Error en búsqueda:', error);
      setSuggestions([]);
      setShowSuggestions(false);
    } finally {
      setLoading(false);
    }
  }, [apiCall, searchField, minChars]);

  // Manejar cambio de input
  const handleInputChange = (e) => {
    const newValue = e.target.value;
    onChange(newValue);
    setSelectedIndex(-1);
    
    // Si el usuario modifica el texto, limpiar selección
    if (selectedItem && newValue !== selectedItem[displayField]) {
      setSelectedItem(null);
    }

    // Cancelar búsqueda anterior
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    // Programar nueva búsqueda
    debounceRef.current = setTimeout(() => {
      searchItems(newValue);
    }, debounceMs);
  };

  // Seleccionar una sugerencia
  const handleSelectSuggestion = (item) => {
    const selectedValue = item[displayField] || '';
    onChange(selectedValue);
    setSelectedItem(item);
    setSuggestions([]);
    setShowSuggestions(false);
    setSelectedIndex(-1);
    inputRef.current?.focus();
    
    // Callback opcional cuando se selecciona un item
    if (onItemSelect) {
      onItemSelect(item);
    }
  };

  // Limpiar selección
  const handleClear = (e) => {
    e.stopPropagation();
    onChange('');
    setSelectedItem(null);
    setSuggestions([]);
    setShowSuggestions(false);
    inputRef.current?.focus();
    
    if (onItemSelect) {
      onItemSelect(null);
    }
  };

  // Navegación con teclado
  const handleKeyDown = (e) => {
    // Si hay sugerencias visibles, manejar navegación
    if (showSuggestions && suggestions.length > 0) {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex((prev) => 
            prev < suggestions.length - 1 ? prev + 1 : 0
          );
          break;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex((prev) => 
            prev > 0 ? prev - 1 : suggestions.length - 1
          );
          break;
        case 'Enter':
          e.preventDefault();
          if (selectedIndex >= 0 && suggestions[selectedIndex]) {
            handleSelectSuggestion(suggestions[selectedIndex]);
          }
          break;
        case 'Escape':
          setShowSuggestions(false);
          setSelectedIndex(-1);
          break;
        case 'Tab':
          // Seleccionar el primero si hay sugerencias
          if (suggestions.length > 0 && selectedIndex === -1) {
            e.preventDefault();
            handleSelectSuggestion(suggestions[0]);
          }
          break;
        default:
          break;
      }
    }
  };

  // Cerrar sugerencias al hacer clic fuera
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setShowSuggestions(false);
        setInputFocused(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Cleanup del debounce al desmontar
  useEffect(() => {
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, []);

  // Scroll al elemento seleccionado
  useEffect(() => {
    if (selectedIndex >= 0 && suggestionsRef.current) {
      const selectedElement = suggestionsRef.current.children[selectedIndex];
      if (selectedElement) {
        selectedElement.scrollIntoView({ block: 'nearest' });
      }
    }
  }, [selectedIndex]);

  // Renderizar item de sugerencia según el modo
  const renderSuggestionItem = (item, index) => {
    const isSelected = index === selectedIndex;
    
    if (mode === 'product') {
      // Modo producto: mostrar info enriquecida
      const stock = item.stock_actual ?? item.cantidad_actual ?? null;
      const stockColor = stock === null ? 'text-gray-400' : 
                         stock <= 0 ? 'text-red-600' : 
                         stock < 10 ? 'text-amber-600' : 'text-emerald-600';
      
      return (
        <li
          key={item.id || index}
          onClick={() => handleSelectSuggestion(item)}
          className={`px-3 py-3 cursor-pointer transition-all duration-150 border-b border-gray-100 last:border-0 ${
            isSelected ? 'bg-blue-50 border-l-4 border-l-blue-500' : 'hover:bg-gray-50'
          }`}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              {/* Clave y nombre */}
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-violet-100 text-violet-700">
                  {item.clave || item[displayField]}
                </span>
                {item.nombre && (
                  <span className="font-medium text-gray-900 truncate">
                    {item.nombre}
                  </span>
                )}
              </div>
              {/* Presentación y descripción */}
              <div className="mt-1 flex items-center gap-2 text-xs text-gray-500">
                {item.presentacion && (
                  <span className="flex items-center gap-1">
                    <FaBox className="text-gray-400" />
                    {item.presentacion}
                  </span>
                )}
                {item.descripcion && item.descripcion !== item.nombre && (
                  <span className="truncate">{item.descripcion}</span>
                )}
              </div>
            </div>
            {/* Stock */}
            {stock !== null && (
              <div className="flex-shrink-0 text-right">
                <div className={`text-sm font-bold ${stockColor}`}>
                  {stock}
                </div>
                <div className="text-[10px] text-gray-400 uppercase">Stock</div>
              </div>
            )}
          </div>
        </li>
      );
    }
    
    if (mode === 'lote') {
      // Modo lote: mostrar info de lote
      return (
        <li
          key={item.id || index}
          onClick={() => handleSelectSuggestion(item)}
          className={`px-3 py-3 cursor-pointer transition-all duration-150 border-b border-gray-100 last:border-0 ${
            isSelected ? 'bg-blue-50 border-l-4 border-l-blue-500' : 'hover:bg-gray-50'
          }`}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-amber-100 text-amber-700">
                  <FaLayerGroup className="mr-1" />
                  {item.numero_lote || item[displayField]}
                </span>
              </div>
              {item.producto_nombre && (
                <div className="mt-1 text-sm text-gray-700 truncate">
                  {item.producto_nombre}
                </div>
              )}
              {item.fecha_caducidad && (
                <div className="mt-0.5 text-xs text-gray-500">
                  Vence: {new Date(item.fecha_caducidad).toLocaleDateString()}
                </div>
              )}
            </div>
            {item.cantidad_actual !== undefined && (
              <div className="flex-shrink-0 text-right">
                <div className="text-sm font-bold text-blue-600">
                  {item.cantidad_actual}
                </div>
                <div className="text-[10px] text-gray-400 uppercase">Cant.</div>
              </div>
            )}
          </div>
        </li>
      );
    }
    
    // Modo default: simple
    return (
      <li
        key={item.id || index}
        onClick={() => handleSelectSuggestion(item)}
        className={`px-4 py-3 cursor-pointer transition-colors border-b border-gray-100 last:border-0 ${
          isSelected ? 'bg-blue-100' : 'hover:bg-blue-50'
        }`}
      >
        <div className="font-medium text-gray-900">
          {item[displayField]}
        </div>
        {secondaryField && item[secondaryField] && (
          <div className="text-sm text-gray-500 truncate">
            {item[secondaryField]}
          </div>
        )}
      </li>
    );
  };

  // Determinar el estado del input para estilos
  const hasValidSelection = selectedItem !== null && value === selectedItem[displayField];
  const inputBorderClass = hasValidSelection 
    ? 'border-emerald-400 ring-2 ring-emerald-100' 
    : inputFocused 
      ? 'border-blue-400 ring-2 ring-blue-100' 
      : 'border-gray-300';

  return (
    <div ref={containerRef} className="relative">
      {/* Input principal */}
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={() => {
            setInputFocused(true);
            if (suggestions.length > 0) {
              setShowSuggestions(true);
            } else if (value && value.length >= minChars) {
              searchItems(value);
            }
          }}
          placeholder={placeholder}
          disabled={disabled}
          className={`w-full px-4 py-2.5 pr-20 rounded-lg transition-all duration-200 focus:outline-none ${inputBorderClass} ${
            disabled ? 'bg-gray-100 cursor-not-allowed' : 'bg-white'
          } ${className}`}
          autoComplete="off"
        />
        
        {/* Iconos del lado derecho */}
        <div className="absolute right-2 top-1/2 transform -translate-y-1/2 flex items-center gap-1">
          {/* Botón limpiar (si hay valor) */}
          {value && !disabled && (
            <button
              type="button"
              onClick={handleClear}
              className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-colors"
              title="Limpiar búsqueda"
            >
              <FaTimes size={12} />
            </button>
          )}
          
          {/* Indicador de estado */}
          {loading ? (
            <div className="p-1.5 text-blue-500">
              <FaSpinner className="animate-spin" size={16} />
            </div>
          ) : hasValidSelection ? (
            <div className="p-1.5 text-emerald-500" title="Producto seleccionado">
              <FaCheckCircle size={16} />
            </div>
          ) : (
            <div className="p-1.5 text-gray-400">
              <FaSearch size={16} />
            </div>
          )}
        </div>
      </div>

      {/* Hint de búsqueda */}
      {inputFocused && !showSuggestions && !loading && value.length > 0 && value.length < minChars && (
        <div className="absolute z-40 w-full mt-1 px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-500">
          <FaInfoCircle className="inline mr-2" />
          Escribe al menos {minChars} carácter{minChars > 1 ? 'es' : ''} para buscar
        </div>
      )}

      {/* Lista de sugerencias */}
      {showSuggestions && suggestions.length > 0 && (
        <ul
          ref={suggestionsRef}
          className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-xl max-h-72 overflow-y-auto"
          style={{ minWidth: '320px' }}
        >
          {/* Header de resultados */}
          <li className="px-3 py-2 bg-gray-50 border-b border-gray-200 text-xs text-gray-500 font-medium sticky top-0">
            {suggestions.length} resultado{suggestions.length !== 1 ? 's' : ''} encontrado{suggestions.length !== 1 ? 's' : ''}
            <span className="float-right text-gray-400">
              ↑↓ navegar • Enter seleccionar • Tab primero
            </span>
          </li>
          
          {suggestions.map((item, index) => renderSuggestionItem(item, index))}
        </ul>
      )}

      {/* No resultados */}
      {showSuggestions && suggestions.length === 0 && !loading && value.length >= minChars && (
        <div className="absolute z-50 w-full mt-1 px-4 py-3 bg-white border border-gray-200 rounded-lg shadow-lg text-sm text-gray-500 text-center">
          <FaSearch className="inline mr-2 text-gray-400" />
          No se encontraron resultados para "{value}"
        </div>
      )}
    </div>
  );
}

export default AutocompleteInput;
