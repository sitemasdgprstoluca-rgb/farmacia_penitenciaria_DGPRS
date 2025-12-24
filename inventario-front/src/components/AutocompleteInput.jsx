import { useState, useEffect, useRef, useCallback } from 'react';
import { FaSpinner, FaSearch, FaTimes } from 'react-icons/fa';

/**
 * Componente de autocompletado con búsqueda en API
 * 
 * @param {Function} apiCall - Función de API que retorna una promesa con los resultados
 * @param {string} value - Valor actual del input
 * @param {Function} onChange - Callback cuando cambia el valor
 * @param {string} placeholder - Placeholder del input
 * @param {string} displayField - Campo a mostrar en las sugerencias (ej: 'clave', 'numero_lote')
 * @param {string} searchField - Nombre del parámetro de búsqueda para la API (ej: 'search')
 * @param {string} secondaryField - Campo secundario opcional para mostrar (ej: 'descripcion')
 * @param {number} minChars - Mínimo de caracteres para iniciar búsqueda (default: 2)
 * @param {number} debounceMs - Tiempo de espera antes de buscar (default: 300ms)
 * @param {boolean} showClearButton - Muestra botón de limpiar (default: true)
 */
function AutocompleteInput({
  apiCall,
  value,
  onChange,
  placeholder = '',
  displayField = 'nombre',
  searchField = 'search',
  secondaryField = 'descripcion',
  minChars = 2,
  debounceMs = 300,
  className = '',
  showClearButton = true,
}) {
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const inputRef = useRef(null);
  const suggestionsRef = useRef(null);
  const debounceRef = useRef(null);

  // Búsqueda con debounce
  const searchItems = useCallback(async (searchTerm) => {
    if (!searchTerm || searchTerm.length < minChars) {
      setSuggestions([]);
      return;
    }

    setLoading(true);
    try {
      const response = await apiCall({ [searchField]: searchTerm, page_size: 10 });
      const items = response.data?.results || response.data || [];
      setSuggestions(items);
      setShowSuggestions(items.length > 0);
    } catch (error) {
      console.error('Error en búsqueda:', error);
      setSuggestions([]);
    } finally {
      setLoading(false);
    }
  }, [apiCall, searchField, minChars]);

  // Manejar cambio de input
  const handleInputChange = (e) => {
    const newValue = e.target.value;
    onChange(newValue);
    setSelectedIndex(-1);

    // Cancelar búsqueda anterior
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    // Programar nueva búsqueda
    debounceRef.current = setTimeout(() => {
      searchItems(newValue);
    }, debounceMs);
  };

  // Limpiar valor
  const handleClear = () => {
    onChange('');
    setSuggestions([]);
    setShowSuggestions(false);
    setSelectedIndex(-1);
    inputRef.current?.focus();
  };

  // Seleccionar una sugerencia
  const handleSelectSuggestion = (item) => {
    const selectedValue = item[displayField] || '';
    onChange(selectedValue);
    setSuggestions([]);
    setShowSuggestions(false);
    setSelectedIndex(-1);
    inputRef.current?.focus();
  };

  // Navegación con teclado
  const handleKeyDown = (e) => {
    if (!showSuggestions || suggestions.length === 0) return;

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
      default:
        break;
    }
  };

  // Cerrar sugerencias al hacer clic fuera
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        inputRef.current && 
        !inputRef.current.contains(event.target) &&
        suggestionsRef.current && 
        !suggestionsRef.current.contains(event.target)
      ) {
        setShowSuggestions(false);
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

  return (
    <div className="relative">
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={() => {
            if (suggestions.length > 0) {
              setShowSuggestions(true);
            }
          }}
          placeholder={placeholder}
          className={`w-full px-4 py-2 pr-16 border-2 border-gray-400 rounded-lg focus:ring-2 focus:ring-guinda focus:border-guinda transition-colors ${className}`}
          autoComplete="off"
        />
        <div className="absolute right-3 top-1/2 transform -translate-y-1/2 flex items-center gap-1">
          {loading ? (
            <FaSpinner className="animate-spin text-gray-400" />
          ) : (
            <>
              {showClearButton && value && (
                <button
                  type="button"
                  onClick={handleClear}
                  className="p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
                  title="Limpiar"
                >
                  <FaTimes className="w-3 h-3" />
                </button>
              )}
              <FaSearch className="text-gray-400" />
            </>
          )}
        </div>
      </div>

      {/* Lista de sugerencias */}
      {showSuggestions && suggestions.length > 0 && (
        <ul
          ref={suggestionsRef}
          className="absolute z-50 w-full mt-1 bg-white border-2 border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto"
        >
          {suggestions.map((item, index) => (
            <li
              key={item.id || index}
              onClick={() => handleSelectSuggestion(item)}
              className={`px-4 py-2 cursor-pointer hover:bg-blue-50 transition-colors ${
                index === selectedIndex ? 'bg-blue-100' : ''
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
          ))}
        </ul>
      )}
    </div>
  );
}

export default AutocompleteInput;
