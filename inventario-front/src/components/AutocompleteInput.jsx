import { useState, useEffect } from "react";
import { FaSearch } from "react-icons/fa";

const AutocompleteInput = ({
  apiCall,
  value,
  onChange,
  placeholder,
  displayField = "clave",
  searchField = "search",
}) => {
  const [sugerencias, setSugerencias] = useState([]);
  const [mostrarSugerencias, setMostrarSugerencias] = useState(false);
  const [cargando, setCargando] = useState(false);

  useEffect(() => {
    if (!value || value.length < 2) {
      setSugerencias([]);
      return;
    }

    const timeout = setTimeout(async () => {
      setCargando(true);
      try {
        const response = await apiCall({ [searchField]: value, page_size: 10 });
        setSugerencias(response.data.results || response.data || []);
        setMostrarSugerencias(true);
      } catch (error) {
        console.error("Error en autocomplete:", error);
      } finally {
        setCargando(false);
      }
    }, 300);

    return () => clearTimeout(timeout);
  }, [value, apiCall, searchField]);

  return (
    <div className="relative">
      <div className="relative">
        <FaSearch className="absolute left-3 top-3 text-gray-400" />
        <input
          type="text"
          value={value}
          onChange={(e) => onChange((e.target.value || "").toUpperCase())}
          placeholder={placeholder}
          className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
          onFocus={() => sugerencias.length > 0 && setMostrarSugerencias(true)}
        />
      </div>

      {mostrarSugerencias && sugerencias.length > 0 && (
        <div className="absolute z-10 w-full mt-1 bg-white border rounded-lg shadow-lg max-h-60 overflow-y-auto">
          {sugerencias.map((item) => (
            <div
              key={item.id}
              onClick={() => {
                onChange(item[displayField]);
                setMostrarSugerencias(false);
              }}
              className="px-4 py-2 hover:bg-gray-100 cursor-pointer"
            >
              <span className="font-semibold">{item[displayField]}</span>
              {item.descripcion && (
                <span className="text-sm text-gray-600 ml-2">- {item.descripcion}</span>
              )}
            </div>
          ))}
        </div>
      )}

      {cargando && (
        <div className="absolute right-3 top-3">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600" />
        </div>
      )}
    </div>
  );
};

export default AutocompleteInput;
