/**
 * ImportadorModerno - Componente reutilizable para importación de datos desde Excel
 * 
 * Características:
 * - Drag & drop + selección de archivo
 * - Validación previa (extensión, tamaño, columnas)
 * - Vista previa de datos con errores resaltados
 * - Barra de progreso durante importación
 * - Reporte de errores descargable
 * - Guía integrada en UI (sin archivos .md)
 * 
 * @version 2.0.0 - Febrero 2026
 */
import { useState, useRef, useCallback } from 'react';
import { toast } from 'react-hot-toast';
import ExcelJS from 'exceljs';
import {
  FaCloudUploadAlt,
  FaDownload,
  FaFileExcel,
  FaTimes,
  FaCheckCircle,
  FaExclamationTriangle,
  FaExclamationCircle,
  FaInfoCircle,
  FaSpinner,
  FaFileDownload,
  FaEye,
  FaChevronDown,
  FaChevronUp,
  FaChevronLeft,
  FaChevronRight,
  FaTrash,
  FaSync,
  FaList
} from 'react-icons/fa';

// Constantes de validación
const MAX_FILE_SIZE_MB = 10;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;
const ALLOWED_EXTENSIONS = ['.xlsx', '.xls'];
const ROWS_PER_PAGE = 25; // Paginación en lugar de límite fijo
const PLANTILLA_VERSION = '2.1.0';

/**
 * Configuraciones por tipo de importación
 */
const IMPORT_CONFIGS = {
  lotes: {
    titulo: 'Lotes de Inventario',
    descripcion: 'Importar lotes de productos al almacén',
    columnasRequeridas: ['Clave Producto', 'Nombre Producto', 'Presentación', 'Número Lote', 'Fecha Caducidad', 'Cantidad Inicial'],
    columnasOpcionales: ['Cantidad Contrato Lote', 'Cantidad Contrato Global', 'Fecha Entrega', 'Precio Unitario', 'Número Contrato', 'Marca', 'Activo'],
    formatos: {
      'Fecha Caducidad': 'YYYY-MM-DD o DD/MM/YYYY',
      'Fecha Entrega': 'YYYY-MM-DD o DD/MM/YYYY',
      'Cantidad Inicial': 'Número entero positivo',
      'Cantidad Contrato Lote': 'Número entero positivo (opcional) - esperado para este lote',
      'Cantidad Contrato Global': 'Número entero positivo (opcional) - total contratado por clave',
      'Precio Unitario': 'Número decimal (ej: 15.50)',
      'Presentación': 'Texto exacto del catálogo (ej: CAJA CON 14 TABLETAS)',
      'Activo': 'Activo / Inactivo'
    },
    sinonimosCols: {
      'clave producto': ['clave', 'codigo', 'sku', 'key', 'clave producto'],
      'nombre producto': ['nombre', 'articulo', 'descripcion', 'nombre producto'],
      'presentacion': ['presentacion', 'presentación', 'pres', 'envase', 'empaque'],
      'numero lote': ['lote', 'numero lote', 'num lote', 'batch', 'número lote'],
      'fecha caducidad': ['caducidad', 'vencimiento', 'fecha caducidad', 'expiracion'],
      'fecha entrega': ['fecha entrega', 'entrega', 'fecha de entrega', 'fecha recepcion', 'recepcion', 'fecha de recepcion', 'fec recepcion', 'fecha fabricacion', 'fabricacion', 'elaboracion', 'fecha elaboracion', 'fec fab', 'fecha recepción'],
      'cantidad inicial': ['cantidad', 'cantidad inicial', 'cant', 'stock', 'existencia', 'qty'],
      'cantidad contrato lote': ['cant contrato lote', 'cantidad contrato lote', 'cant lote', 'contrato lote'],
      'cantidad contrato global': ['cant contrato global', 'cantidad contrato global', 'contrato global', 'cant ccg']
    },
    limites: {
      maxFilas: 5000,
      maxTamanio: '10 MB'
    },
    pasos: [
      { numero: 1, titulo: 'Descargar plantilla', descripcion: 'Descarga la plantilla v2.1 con el campo Presentación obligatorio' },
      { numero: 2, titulo: 'Llenar datos', descripcion: 'Completa tus datos. ⚠️ La Presentación DEBE coincidir con el catálogo' },
      { numero: 3, titulo: 'Importar', descripcion: 'El sistema validará Clave + Nombre + Presentación' }
    ],
    ejemploRegistro: {
      'Clave Producto': '702.2',
      'Nombre Producto': 'TRIMETOPRIMA/SULFAMETOXAZOL',
      'Presentación': 'CAJA CON 14 TABLETAS',
      'Número Lote': 'LOT-2026-001',
      'Fecha Caducidad': '2027-12-31',
      'Cantidad Inicial': 100,
      'Cantidad Contrato Lote': 100,
      'Cantidad Contrato Global': 1000,
      'Precio Unitario': 15.50
    }
  },
  productos: {
    titulo: 'Catálogo de Productos',
    descripcion: 'Importar productos al catálogo',
    columnasRequeridas: ['Clave', 'Nombre', 'Presentación', 'Controlado'],
    columnasOpcionales: ['Nombre Comercial', 'Unidad', 'Stock Mínimo', 'Categoría', 'Sustancia Activa', 'Concentración', 'Vía Admin', 'Requiere Receta', 'Estado'],
    formatos: {
      'Presentación': 'Texto (ej: CAJA CON 14 TABLETAS, FRASCO 120ML)',
      'Stock Mínimo': 'Número entero',
      'Requiere Receta': 'Sí / No',
      'Controlado': 'Sí / No',
      'Estado': 'Activo / Inactivo'
    },
    sinonimosCols: {
      'clave': ['clave', 'codigo', 'sku'],
      'nombre': ['nombre', 'descripcion', 'producto'],
      'presentacion': ['presentacion', 'presentación', 'forma farmaceutica', 'forma', 'envase']
    },
    limites: {
      maxFilas: 2000,
      maxTamanio: '10 MB'
    },
    pasos: [
      { numero: 1, titulo: 'Descargar plantilla', descripcion: 'Descarga la plantilla con el formato correcto' },
      { numero: 2, titulo: 'Llenar datos', descripcion: 'Completa los productos. ⚠️ Presentación es OBLIGATORIA' },
      { numero: 3, titulo: 'Importar', descripcion: 'Sube el archivo y el sistema validará los datos' }
    ],
    ejemploRegistro: {
      'Clave': 'MED001',
      'Nombre': 'Paracetamol 500mg',
      'Presentación': 'CAJA CON 20 TABLETAS',
      'Unidad': 'CAJA',
      'Stock Mínimo': 50,
      'Controlado': 'No'
    }
  },
  usuarios: {
    titulo: 'Usuarios del Sistema',
    descripcion: 'Importar usuarios para acceso al sistema',
    columnasRequeridas: ['Username', 'Email', 'Nombre', 'Apellidos', 'Password', 'Rol'],
    columnasOpcionales: ['Centro ID', 'Adscripción', 'Teléfono', 'Activo'],
    formatos: {
      'Username': '3-150 caracteres, único',
      'Email': 'Formato válido, único',
      'Password': 'Mínimo 8 caracteres',
      'Rol': 'farmacia_admin, centro_admin, medico, enfermero, almacenista, auditor',
      'Activo': 'Si / No'
    },
    sinonimosCols: {
      'username': ['username', 'usuario', 'user'],
      'email': ['email', 'correo', 'mail'],
      'nombre': ['nombre', 'first_name', 'nombres'],
      'apellidos': ['apellidos', 'last_name', 'apellido']
    },
    limites: {
      maxFilas: 500,
      maxTamanio: '5 MB'
    },
    pasos: [
      { numero: 1, titulo: 'Descargar plantilla', descripcion: 'Obtén la plantilla con roles disponibles' },
      { numero: 2, titulo: 'Llenar datos', descripcion: 'Completa usuarios con contraseñas seguras' },
      { numero: 3, titulo: 'Importar', descripcion: 'Los usuarios recibirán acceso inmediato' }
    ],
    ejemploRegistro: {
      'Username': 'jperez',
      'Email': 'jperez@ejemplo.com',
      'Nombre': 'Juan',
      'Apellidos': 'Pérez García',
      'Rol': 'medico'
    }
  },
  pacientes: {
    titulo: 'Pacientes PPL',
    descripcion: 'Importar población privada de libertad',
    columnasRequeridas: ['NUC', 'Nombre', 'Apellido Paterno'],
    columnasOpcionales: ['Apellido Materno', 'Fecha Nacimiento', 'Sexo', 'Dormitorio', 'Estatus', 'Centro'],
    formatos: {
      'NUC': 'Número Único de Control',
      'Fecha Nacimiento': 'YYYY-MM-DD',
      'Sexo': '1 = Masculino, 2 = Femenino',
      'Estatus': 'activo / inactivo / trasladado / liberado'
    },
    sinonimosCols: {
      'nuc': ['nuc', 'numero unico', 'id'],
      'nombre': ['nombre', 'nombres', 'first_name'],
      'apellido paterno': ['apellido paterno', 'paterno', 'primer apellido']
    },
    limites: {
      maxFilas: 10000,
      maxTamanio: '10 MB'
    },
    pasos: [
      { numero: 1, titulo: 'Descargar plantilla', descripcion: 'Plantilla con campos del censo' },
      { numero: 2, titulo: 'Llenar datos', descripcion: 'Completa datos de PPL' },
      { numero: 3, titulo: 'Importar', descripcion: 'El sistema validará NUCs duplicados' }
    ],
    ejemploRegistro: {
      'NUC': '12345678',
      'Nombre': 'Juan',
      'Apellido Paterno': 'Pérez',
      'Sexo': '1'
    }
  }
};

/**
 * Formatea un valor de celda para mostrar en UI
 * Evita el error de React al intentar renderizar objetos Date directamente
 */
const formatearCelda = (valor) => {
  if (valor === null || valor === undefined || valor === '') {
    return '';
  }
  // Si es objeto Date, formatear como string
  if (valor instanceof Date) {
    if (isNaN(valor.getTime())) return '(fecha inválida)';
    // Formato YYYY-MM-DD
    return valor.toISOString().split('T')[0];
  }
  // Si es objeto con propiedad result (fórmula de Excel), usar el resultado
  if (typeof valor === 'object' && valor !== null) {
    if (valor.result !== undefined) return formatearCelda(valor.result);
    if (valor.text !== undefined) return valor.text;
    if (valor.richText) return valor.richText.map(rt => rt.text).join('');
    // Otros objetos: convertir a string
    return JSON.stringify(valor);
  }
  return String(valor);
};

/**
 * Normaliza un header para comparación
 */
const normalizarHeader = (header) => {
  if (!header) return '';
  return String(header)
    .toLowerCase()
    .trim()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '') // Quitar acentos
    .replace(/[^a-z0-9\s]/g, '')
    .replace(/\s+/g, ' ');
};

/**
 * Verifica si una columna coincide con algún sinónimo
 */
const columnaCoincide = (header, columnaBuscada, sinonimos) => {
  const headerNorm = normalizarHeader(header);
  const columnaKey = normalizarHeader(columnaBuscada);
  
  // Coincidencia directa
  if (headerNorm === columnaKey || headerNorm.includes(columnaKey) || columnaKey.includes(headerNorm)) {
    return true;
  }
  
  // Buscar en sinónimos
  if (sinonimos && sinonimos[columnaKey]) {
    return sinonimos[columnaKey].some(sin => {
      const sinNorm = normalizarHeader(sin);
      return headerNorm === sinNorm || headerNorm.includes(sinNorm) || sinNorm.includes(headerNorm);
    });
  }
  
  return false;
};

/**
 * Componente principal del importador
 */
const ImportadorModerno = ({
  tipo = 'lotes',
  onImportar,
  onDescargarPlantilla,
  onCerrar, // Callback para cerrar el modal
  permiteImportar = true,
  className = ''
}) => {
  const config = IMPORT_CONFIGS[tipo] || IMPORT_CONFIGS.lotes;
  
  // Estados
  const [archivo, setArchivo] = useState(null);
  const [arrastrando, setArrastrando] = useState(false);
  const [validando, setValidando] = useState(false);
  const [importando, setImportando] = useState(false);
  const [progreso, setProgreso] = useState(0);
  const [preview, setPreview] = useState(null);
  const [erroresValidacion, setErroresValidacion] = useState([]);
  const [resultadoImportacion, setResultadoImportacion] = useState(null);
  const [mostrarGuia, setMostrarGuia] = useState(false);
  const [mostrarFormatos, setMostrarFormatos] = useState(false);
  const [mostrarTodosErrores, setMostrarTodosErrores] = useState(false);
  const [mostrarTodosActualizados, setMostrarTodosActualizados] = useState(false);
  // Paginación para vista previa
  const [paginaActual, setPaginaActual] = useState(1);
  
  const inputRef = useRef(null);
  const dropZoneRef = useRef(null);

  /**
   * Maneja la selección de archivo
   */
  const handleArchivoSeleccionado = useCallback(async (file) => {
    if (!file) return;
    
    setErroresValidacion([]);
    setPreview(null);
    setResultadoImportacion(null);
    
    // Validar extensión
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setErroresValidacion([{
        tipo: 'critico',
        mensaje: `Extensión no permitida: ${ext}`,
        detalle: `Use archivos ${ALLOWED_EXTENSIONS.join(' o ')}`
      }]);
      return;
    }
    
    // Validar tamaño
    if (file.size > MAX_FILE_SIZE_BYTES) {
      setErroresValidacion([{
        tipo: 'critico',
        mensaje: `Archivo muy grande: ${(file.size / 1024 / 1024).toFixed(2)} MB`,
        detalle: `Tamaño máximo: ${MAX_FILE_SIZE_MB} MB`
      }]);
      return;
    }
    
    setArchivo(file);
    setValidando(true);
    
    try {
      // Leer y validar contenido con ExcelJS
      const data = await file.arrayBuffer();
      const workbook = new ExcelJS.Workbook();
      await workbook.xlsx.load(data);
      
      const worksheet = workbook.worksheets[0];
      if (!worksheet) {
        setErroresValidacion([{
          tipo: 'critico',
          mensaje: 'Archivo vacío o sin hojas',
          detalle: 'El archivo Excel debe tener al menos una hoja con datos'
        }]);
        setValidando(false);
        return;
      }
      
      // Convertir hoja a array de arrays
      const jsonData = [];
      worksheet.eachRow({ includeEmpty: false }, (row, rowNumber) => {
        const rowData = [];
        row.eachCell({ includeEmpty: true }, (cell, colNumber) => {
          // Expandir array si es necesario
          while (rowData.length < colNumber - 1) rowData.push('');
          // Formatear el valor para evitar objetos Date crudos
          rowData.push(formatearCelda(cell.value));
        });
        jsonData.push(rowData);
      });
      
      if (jsonData.length < 2) {
        setErroresValidacion([{
          tipo: 'critico',
          mensaje: 'Archivo vacío o sin datos',
          detalle: 'El archivo debe tener encabezados y al menos una fila de datos'
        }]);
        setValidando(false);
        return;
      }
      
      // Detectar fila de encabezados (puede estar en fila 1, 2 o hasta 6)
      let headerRowIndex = 0;
      const buscarKeywords = ['clave', 'nombre', 'lote', 'producto', 'nuc', 'username'];
      
      for (let i = 0; i < Math.min(10, jsonData.length); i++) {
        const row = jsonData[i];
        const rowText = row.map(c => normalizarHeader(c)).join(' ');
        if (buscarKeywords.some(kw => rowText.includes(kw))) {
          headerRowIndex = i;
          break;
        }
      }
      
      const headers = jsonData[headerRowIndex].map(h => String(h || '').trim());
      const numColumnasRequeridas = config.columnasRequeridas.length;
      
      // Filtrar filas vacías o con muy pocos datos (menos de la mitad de columnas requeridas)
      const dataRows = jsonData.slice(headerRowIndex + 1).filter(row => {
        // Contar celdas con datos reales (no vacíos)
        const celdasConDatos = row.filter(cell => 
          cell !== '' && cell !== null && cell !== undefined && String(cell).trim() !== ''
        ).length;
        // Una fila válida debe tener al menos la mitad de las columnas requeridas con datos
        // o al menos 2 celdas con datos (lo que sea mayor)
        const minCeldas = Math.max(2, Math.floor(numColumnasRequeridas / 2));
        return celdasConDatos >= minCeldas;
      });
      
      // Filtrar filas de ejemplo y separadores
      const dataRowsSinEjemplos = dataRows.filter(row => {
        const rowText = row.join(' ').toLowerCase();
        // Ignorar filas de ejemplo, separadores o instrucciones
        if (rowText.includes('[ejemplo]') || rowText.includes('eliminar') || 
            rowText.includes('---') || rowText.includes('***')) {
          return false;
        }
        return true;
      });
      
      // Validar columnas requeridas
      const errores = [];
      const columnasEncontradas = [];
      const columnasFaltantes = [];
      
      config.columnasRequeridas.forEach(colReq => {
        const encontrada = headers.some(h => columnaCoincide(h, colReq, config.sinonimosCols));
        if (encontrada) {
          columnasEncontradas.push(colReq);
        } else {
          columnasFaltantes.push(colReq);
          errores.push({
            tipo: 'critico',
            mensaje: `Falta columna requerida: ${colReq}`,
            detalle: 'Esta columna es obligatoria para la importación'
          });
        }
      });
      
      // Detectar columnas opcionales encontradas
      if (config.columnasOpcionales) {
        config.columnasOpcionales.forEach(colOpt => {
          const encontrada = headers.some(h => columnaCoincide(h, colOpt, config.sinonimosCols));
          if (encontrada) {
            columnasEncontradas.push(colOpt);
          }
        });
      }
      
      // Validar filas de datos
      const erroresPorFila = [];
      const filasValidas = [];
      const filasDuplicadas = [];
      const keysVistos = new Set();
      
      dataRowsSinEjemplos.forEach((row, idx) => {
        const filaNum = headerRowIndex + idx + 2; // +2 porque Excel es 1-indexed y saltamos header
        const erroresFila = [];
        
        // Construir objeto de la fila
        const rowObj = {};
        headers.forEach((h, i) => {
          rowObj[h] = row[i];
        });
        
        // Validar campos vacíos requeridos
        config.columnasRequeridas.forEach(colReq => {
          const headerCol = headers.find(h => columnaCoincide(h, colReq, config.sinonimosCols));
          if (headerCol) {
            const valor = rowObj[headerCol];
            if (valor === '' || valor === null || valor === undefined) {
              erroresFila.push({
                columna: colReq,
                mensaje: `Campo vacío en columna "${colReq}"`
              });
            }
          }
        });
        
        // Detectar duplicados (usando primeras columnas como key)
        const keyFields = headers.slice(0, Math.min(3, headers.length));
        const key = keyFields.map(h => String(rowObj[h] || '').toLowerCase().trim()).join('|');
        if (key && key !== '||' && keysVistos.has(key)) {
          filasDuplicadas.push(filaNum);
        } else if (key && key !== '||') {
          keysVistos.add(key);
        }
        
        if (erroresFila.length > 0) {
          erroresPorFila.push({ fila: filaNum, errores: erroresFila, datos: rowObj });
        } else {
          filasValidas.push({ fila: filaNum, datos: rowObj });
        }
      });
      
      // Agregar advertencias de duplicados
      if (filasDuplicadas.length > 0) {
        errores.push({
          tipo: 'advertencia',
          mensaje: `${filasDuplicadas.length} posibles duplicados detectados`,
          detalle: `Filas: ${filasDuplicadas.slice(0, 10).join(', ')}${filasDuplicadas.length > 10 ? '...' : ''}`
        });
      }
      
      // Agregar resumen de errores de filas (agrupado para mejor legibilidad)
      if (erroresPorFila.length > 0) {
        // Agrupar errores por tipo de error
        const erroresPorTipo = {};
        erroresPorFila.forEach(({ fila, errores: errs }) => {
          errs.forEach(e => {
            const key = e.columna;
            if (!erroresPorTipo[key]) {
              erroresPorTipo[key] = [];
            }
            erroresPorTipo[key].push(fila);
          });
        });
        
        // Mostrar resumen agrupado
        Object.entries(erroresPorTipo).forEach(([columna, filas]) => {
          const filasStr = filas.slice(0, 5).join(', ') + (filas.length > 5 ? ` (+${filas.length - 5} más)` : '');
          errores.push({
            tipo: 'error',
            mensaje: `${filas.length} fila(s) sin "${columna}"`,
            detalle: `Filas: ${filasStr}`
          });
        });
      }
      
      // Crear preview con TODAS las filas (paginación se aplica en render)
      const previewData = {
        headers,
        rows: dataRowsSinEjemplos.map((row, idx) => ({
          numero: headerRowIndex + idx + 2,
          datos: row,
          tieneError: erroresPorFila.some(e => e.fila === headerRowIndex + idx + 2),
          esDuplicado: filasDuplicadas.includes(headerRowIndex + idx + 2)
        })),
        totalFilas: dataRowsSinEjemplos.length,
        filasValidas: filasValidas.length,
        filasConError: erroresPorFila.length,
        filasDuplicadas: filasDuplicadas.length,
        columnasEncontradas,
        columnasFaltantes,
        headerRowIndex,
        erroresPorFila // Guardar errores detallados para mostrar al usuario
      };
      
      setPreview(previewData);
      setErroresValidacion(errores);
      
    } catch (error) {
      console.error('Error al leer archivo:', error);
      setErroresValidacion([{
        tipo: 'critico',
        mensaje: 'Error al leer el archivo',
        detalle: error.message || 'El archivo puede estar corrupto o en formato incorrecto'
      }]);
    } finally {
      setValidando(false);
    }
  }, [config]);

  /**
   * Maneja el drag & drop
   */
  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setArrastrando(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setArrastrando(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setArrastrando(false);
    
    const files = e.dataTransfer?.files;
    if (files && files.length > 0) {
      handleArchivoSeleccionado(files[0]);
    }
  }, [handleArchivoSeleccionado]);

  /**
   * Ejecuta la importación
   */
  const ejecutarImportacion = useCallback(async () => {
    if (!archivo || !onImportar) return;
    
    const tieneCriticos = erroresValidacion.some(e => e.tipo === 'critico');
    if (tieneCriticos) {
      toast.error('Corrija los errores críticos antes de importar');
      return;
    }
    
    setImportando(true);
    setProgreso(0);
    setResultadoImportacion(null);
    
    // Simular progreso inicial
    const intervalId = setInterval(() => {
      setProgreso(prev => Math.min(prev + 5, 90));
    }, 200);
    
    try {
      const formData = new FormData();
      formData.append('file', archivo);
      
      const resultado = await onImportar(formData);
      
      clearInterval(intervalId);
      setProgreso(100);
      
      // Procesar resultado
      const res = resultado?.data || resultado;
      setResultadoImportacion({
        exitoso: res.exitosa !== false && !res.error,
        mensaje: res.mensaje || (res.exitosa ? 'Importación completada' : 'Error en importación'),
        creados: res.creados || res.total_creados || 0,
        actualizados: res.actualizados || res.total_actualizados || 0,
        errores: res.errores || res.total_errores || 0,
        omitidos: res.omitidos || 0,
        detalleErrores: res.detalle_errores || res.errores_detalle || [],
        detalleActualizados: res.detalle_actualizados || []
      });
      
      if (res.exitosa !== false && !res.error) {
        toast.success(`Importación completada: ${res.creados || 0} creados`);
        // ISS-INV-003: Mostrar alertas de contrato global excedido
        if (res.alertas_contrato_global && res.alertas_contrato_global.length > 0) {
          setTimeout(() => {
            res.alertas_contrato_global.forEach(alerta => {
              toast(alerta, { icon: '⚠️', duration: 10000 });
            });
          }, 500);
        }
      } else {
        toast.error(res.mensaje || 'Error durante la importación');
      }
      
    } catch (error) {
      clearInterval(intervalId);
      console.error('Error en importación:', error);
      
      const errorMsg = error.response?.data?.mensaje || 
                       error.response?.data?.error || 
                       error.message || 
                       'Error de conexión';
      
      setResultadoImportacion({
        exitoso: false,
        mensaje: errorMsg,
        creados: 0,
        actualizados: 0,
        errores: 1,
        detalleErrores: [{ mensaje: errorMsg }]
      });
      
      toast.error(errorMsg);
    } finally {
      setImportando(false);
    }
  }, [archivo, erroresValidacion, onImportar]);

  /**
   * Descarga reporte de errores como Excel con mejor diseño
   */
  const descargarReporteErrores = useCallback(async () => {
    const tieneErrores = resultadoImportacion?.detalleErrores?.length > 0;
    const tieneActualizados = resultadoImportacion?.detalleActualizados?.length > 0;
    
    if (!tieneErrores && !tieneActualizados) return;
    
    try {
      const workbook = new ExcelJS.Workbook();
      workbook.creator = 'Sistema de Farmacia Penitenciaria';
      workbook.created = new Date();
      
      // ========= HOJA DE ERRORES =========
      if (tieneErrores) {
        const wsErrores = workbook.addWorksheet('Errores de Importación', {
          properties: { tabColor: { argb: 'FF9F2241' } }
        });
        
        // Título principal
        wsErrores.mergeCells('A1:E1');
        const titleCell = wsErrores.getCell('A1');
        titleCell.value = `📋 REPORTE DE ERRORES - Importación de ${config.titulo}`;
        titleCell.font = { bold: true, size: 16, color: { argb: 'FF9F2241' } };
        titleCell.alignment = { horizontal: 'center', vertical: 'middle' };
        wsErrores.getRow(1).height = 30;
        
        // Fecha y resumen
        wsErrores.mergeCells('A2:E2');
        const dateCell = wsErrores.getCell('A2');
        dateCell.value = `Fecha: ${new Date().toLocaleDateString('es-MX')} ${new Date().toLocaleTimeString('es-MX')}`;
        dateCell.font = { size: 10, color: { argb: 'FF666666' } };
        
        // Resumen de resultados
        wsErrores.mergeCells('A3:E3');
        const summaryCell = wsErrores.getCell('A3');
        summaryCell.value = `Total errores: ${resultadoImportacion.detalleErrores.length} | Creados: ${resultadoImportacion.creados || 0} | Actualizados: ${resultadoImportacion.actualizados || 0}`;
        summaryCell.font = { size: 11, bold: true };
        summaryCell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFFFF3CD' } };
        
        // Espacio
        wsErrores.getRow(4).height = 10;
        
        // Headers de la tabla
        const headerRow = wsErrores.getRow(5);
        const headers = ['#', 'Fila Excel', 'Campo', 'Valor', 'Descripción del Error'];
        headers.forEach((h, i) => {
          const cell = headerRow.getCell(i + 1);
          cell.value = h;
          cell.font = { bold: true, color: { argb: 'FFFFFFFF' } };
          cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF9F2241' } };
          cell.alignment = { horizontal: 'center', vertical: 'middle' };
          cell.border = {
            top: { style: 'thin' }, bottom: { style: 'thin' },
            left: { style: 'thin' }, right: { style: 'thin' }
          };
        });
        headerRow.height = 25;
        
        // Anchos de columna
        wsErrores.getColumn(1).width = 6;
        wsErrores.getColumn(2).width = 12;
        wsErrores.getColumn(3).width = 20;
        wsErrores.getColumn(4).width = 25;
        wsErrores.getColumn(5).width = 60;
        
        // Datos de errores
        resultadoImportacion.detalleErrores.forEach((error, idx) => {
          const row = wsErrores.getRow(6 + idx);
          row.getCell(1).value = idx + 1;
          row.getCell(2).value = error.fila || '-';
          row.getCell(3).value = error.campo || '-';
          row.getCell(4).value = error.valor || '-';
          row.getCell(5).value = error.mensaje || error.error || 'Error desconocido';
          
          const fillColor = idx % 2 === 0 ? 'FFFFFFFF' : 'FFF8F8F8';
          row.eachCell((cell) => {
            cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: fillColor } };
            cell.border = {
              top: { style: 'thin', color: { argb: 'FFE0E0E0' } },
              bottom: { style: 'thin', color: { argb: 'FFE0E0E0' } },
              left: { style: 'thin', color: { argb: 'FFE0E0E0' } },
              right: { style: 'thin', color: { argb: 'FFE0E0E0' } }
            };
            cell.alignment = { vertical: 'middle', wrapText: true };
          });
          row.getCell(1).alignment = { horizontal: 'center', vertical: 'middle' };
          row.getCell(2).alignment = { horizontal: 'center', vertical: 'middle' };
        });
        
        const footerRow = 6 + resultadoImportacion.detalleErrores.length + 1;
        wsErrores.mergeCells(`A${footerRow}:E${footerRow}`);
        const footerCell = wsErrores.getCell(`A${footerRow}`);
        footerCell.value = '💡 Corrija los errores en su archivo original y vuelva a importar.';
        footerCell.font = { italic: true, size: 10, color: { argb: 'FF666666' } };
      }
      
      // ========= HOJA DE ACTUALIZADOS =========
      if (tieneActualizados) {
        const wsActualizados = workbook.addWorksheet('Productos Actualizados', {
          properties: { tabColor: { argb: 'FFFFC107' } }
        });
        
        // Título
        wsActualizados.mergeCells('A1:D1');
        const titleCellAct = wsActualizados.getCell('A1');
        titleCellAct.value = `🔄 PRODUCTOS ACTUALIZADOS - Importación de ${config.titulo}`;
        titleCellAct.font = { bold: true, size: 16, color: { argb: 'FFB45309' } };
        titleCellAct.alignment = { horizontal: 'center', vertical: 'middle' };
        wsActualizados.getRow(1).height = 30;
        
        // Fecha
        wsActualizados.mergeCells('A2:D2');
        const dateCellAct = wsActualizados.getCell('A2');
        dateCellAct.value = `Fecha: ${new Date().toLocaleDateString('es-MX')} ${new Date().toLocaleTimeString('es-MX')}`;
        dateCellAct.font = { size: 10, color: { argb: 'FF666666' } };
        
        // Info
        wsActualizados.mergeCells('A3:D3');
        const infoCellAct = wsActualizados.getCell('A3');
        infoCellAct.value = `Total productos actualizados: ${resultadoImportacion.detalleActualizados.length} (ya existían en el catálogo)`;
        infoCellAct.font = { size: 11, bold: true };
        infoCellAct.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFFEF3C7' } };
        
        wsActualizados.getRow(4).height = 10;
        
        // Headers
        const headerRowAct = wsActualizados.getRow(5);
        ['#', 'Fila Excel', 'Clave', 'Nombre del Producto'].forEach((h, i) => {
          const cell = headerRowAct.getCell(i + 1);
          cell.value = h;
          cell.font = { bold: true, color: { argb: 'FFFFFFFF' } };
          cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFB45309' } };
          cell.alignment = { horizontal: 'center', vertical: 'middle' };
          cell.border = {
            top: { style: 'thin' }, bottom: { style: 'thin' },
            left: { style: 'thin' }, right: { style: 'thin' }
          };
        });
        headerRowAct.height = 25;
        
        wsActualizados.getColumn(1).width = 6;
        wsActualizados.getColumn(2).width = 12;
        wsActualizados.getColumn(3).width = 15;
        wsActualizados.getColumn(4).width = 60;
        
        // Datos
        resultadoImportacion.detalleActualizados.forEach((item, idx) => {
          const row = wsActualizados.getRow(6 + idx);
          row.getCell(1).value = idx + 1;
          row.getCell(2).value = item.fila || '-';
          row.getCell(3).value = item.clave || '-';
          row.getCell(4).value = item.nombre || '-';
          
          const fillColor = idx % 2 === 0 ? 'FFFFFFFF' : 'FFFEFCE8';
          row.eachCell((cell) => {
            cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: fillColor } };
            cell.border = {
              top: { style: 'thin', color: { argb: 'FFE0E0E0' } },
              bottom: { style: 'thin', color: { argb: 'FFE0E0E0' } },
              left: { style: 'thin', color: { argb: 'FFE0E0E0' } },
              right: { style: 'thin', color: { argb: 'FFE0E0E0' } }
            };
            cell.alignment = { vertical: 'middle', wrapText: true };
          });
          row.getCell(1).alignment = { horizontal: 'center', vertical: 'middle' };
          row.getCell(2).alignment = { horizontal: 'center', vertical: 'middle' };
        });
        
        const footerRowAct = 6 + resultadoImportacion.detalleActualizados.length + 1;
        wsActualizados.mergeCells(`A${footerRowAct}:D${footerRowAct}`);
        const footerCellAct = wsActualizados.getCell(`A${footerRowAct}`);
        footerCellAct.value = 'ℹ️ Estos productos ya existían en el catálogo y sus datos fueron actualizados con la información del Excel.';
        footerCellAct.font = { italic: true, size: 10, color: { argb: 'FF666666' } };
      }
      
      // Generar archivo
      const buffer = await workbook.xlsx.writeBuffer();
      const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Reporte_Importacion_${tipo}_${new Date().toISOString().split('T')[0]}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
      
      toast.success('Reporte descargado');
    } catch (error) {
      console.error('Error al generar reporte:', error);
      toast.error('Error al generar el reporte');
    }
  }, [resultadoImportacion, tipo, config.titulo]);

  /**
   * Reinicia el importador
   */
  const reiniciar = useCallback(() => {
    setArchivo(null);
    setPreview(null);
    setErroresValidacion([]);
    setResultadoImportacion(null);
    setProgreso(0);
    setPaginaActual(1);
    setMostrarTodosErrores(false);
    setMostrarTodosActualizados(false);
    if (inputRef.current) inputRef.current.value = '';
  }, []);

  const tieneCriticos = erroresValidacion.some(e => e.tipo === 'critico');
  const puedeImportar = archivo && !tieneCriticos && !importando && !validando && permiteImportar;
  
  // Cálculos de paginación
  const totalPaginas = preview ? Math.ceil(preview.rows.length / ROWS_PER_PAGE) : 1;
  const filasPaginadas = preview 
    ? preview.rows.slice((paginaActual - 1) * ROWS_PER_PAGE, paginaActual * ROWS_PER_PAGE)
    : [];

  return (
    <div className={`bg-white rounded-2xl modal-elevated overflow-hidden flex flex-col max-h-[90vh] ${className}`}>
      {/* Header elevado */}
      <div className="px-6 py-5 modal-header-elevated flex-shrink-0 rounded-t-2xl">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="modal-icon-badge">
              <FaFileExcel className="text-white text-lg" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white tracking-wide flex items-center gap-2">
                Importar {config.titulo}
              </h2>
              <p className="text-white/60 text-xs mt-0.5">{config.descripcion}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="px-2.5 py-1 rounded-lg bg-white/15 text-xs font-semibold backdrop-blur-sm text-white">v{PLANTILLA_VERSION}</span>
            {onCerrar && (
              <button
                onClick={onCerrar}
                className="p-1.5 rounded-lg hover:bg-white/20 transition-colors text-white"
                title="Cerrar importador"
              >
                <FaTimes size={18} />
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="p-6 overflow-y-auto flex-1">
        {/* Pasos del proceso - Guía integrada */}
        <div className="mb-6">
          <button 
            onClick={() => setMostrarGuia(!mostrarGuia)}
            className="flex items-center gap-2 text-sm font-medium text-theme-primary hover:text-theme-secondary transition"
          >
            <FaInfoCircle />
            ¿Cómo funciona? 
            {mostrarGuia ? <FaChevronUp /> : <FaChevronDown />}
          </button>
          
          {mostrarGuia && (
            <div className="mt-4 p-4 bg-blue-50 rounded-xl border border-blue-200">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {config.pasos.map((paso) => (
                  <div key={paso.numero} className="flex gap-3">
                    <div className="flex-shrink-0 w-8 h-8 bg-theme-primary text-white rounded-full flex items-center justify-center font-bold text-sm">
                      {paso.numero}
                    </div>
                    <div>
                      <h4 className="font-semibold text-gray-800 text-sm">{paso.titulo}</h4>
                      <p className="text-xs text-gray-600 mt-1">{paso.descripcion}</p>
                    </div>
                  </div>
                ))}
              </div>
              
              {/* Ejemplo de registro correcto */}
              <div className="mt-4 pt-4 border-t border-blue-200">
                <h4 className="font-semibold text-gray-800 text-sm mb-2 flex items-center gap-2">
                  <FaEye /> Ejemplo de registro correcto:
                </h4>
                <div className="bg-white rounded-lg p-3 text-xs overflow-x-auto">
                  <table className="min-w-full">
                    <thead>
                      <tr>
                        {Object.keys(config.ejemploRegistro).map(key => (
                          <th key={key} className="px-2 py-1 text-left font-semibold text-gray-700 border-b">
                            {key}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        {Object.values(config.ejemploRegistro).map((val, i) => (
                          <td key={i} className="px-2 py-1 text-gray-600">{val}</td>
                        ))}
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
              
              {/* Límites */}
              <div className="mt-3 flex flex-wrap gap-4 text-xs text-gray-600">
                <span>📊 Máx. {config.limites.maxFilas.toLocaleString()} filas</span>
                <span>📁 Máx. {config.limites.maxTamanio}</span>
                <span>📄 Formatos: .xlsx, .xls</span>
              </div>
            </div>
          )}
        </div>

        {/* Columnas y formatos */}
        <div className="mb-6">
          <button 
            onClick={() => setMostrarFormatos(!mostrarFormatos)}
            className="flex items-center gap-2 text-sm font-medium text-gray-600 hover:text-gray-800 transition"
          >
            <FaFileExcel />
            Ver columnas y formatos requeridos
            {mostrarFormatos ? <FaChevronUp /> : <FaChevronDown />}
          </button>
          
          {mostrarFormatos && (
            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Columnas requeridas */}
              <div className="p-4 bg-red-50 rounded-xl border border-red-200">
                <h4 className="font-semibold text-red-800 text-sm mb-2 flex items-center gap-2">
                  <FaExclamationCircle /> Columnas Obligatorias
                </h4>
                <ul className="space-y-1">
                  {config.columnasRequeridas.map(col => (
                    <li key={col} className="text-xs text-red-700 flex items-start gap-2">
                      <span className="text-red-500">•</span>
                      <span><strong>{col}</strong> {config.formatos[col] && <span className="text-red-500">({config.formatos[col]})</span>}</span>
                    </li>
                  ))}
                </ul>
              </div>
              
              {/* Columnas opcionales */}
              <div className="p-4 bg-gray-50 rounded-xl border border-gray-200">
                <h4 className="font-semibold text-gray-700 text-sm mb-2">Columnas Opcionales</h4>
                <ul className="space-y-1">
                  {config.columnasOpcionales.map(col => (
                    <li key={col} className="text-xs text-gray-600 flex items-start gap-2">
                      <span className="text-gray-400">•</span>
                      <span>{col} {config.formatos[col] && <span className="text-gray-400">({config.formatos[col]})</span>}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>

        {/* Botón descargar plantilla */}
        <div className="mb-6 flex flex-wrap gap-3">
          <button
            onClick={onDescargarPlantilla}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition font-medium text-sm"
          >
            <FaDownload /> Descargar plantilla actualizada
          </button>
          
          {archivo && (
            <button
              onClick={reiniciar}
              className="flex items-center gap-2 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition font-medium text-sm"
            >
              <FaTrash /> Limpiar
            </button>
          )}
        </div>

        {/* Zona de carga (Drag & Drop) */}
        {!resultadoImportacion && (
          <div
            ref={dropZoneRef}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
            className={`
              border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all
              ${arrastrando 
                ? 'border-theme-primary bg-theme-primary/5' 
                : archivo 
                  ? 'border-green-400 bg-green-50' 
                  : 'border-gray-300 hover:border-theme-primary hover:bg-gray-50'
              }
            `}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".xlsx,.xls"
              onChange={(e) => handleArchivoSeleccionado(e.target.files?.[0])}
              className="hidden"
            />
            
            {validando ? (
              <div className="flex flex-col items-center">
                <FaSpinner className="animate-spin text-4xl text-theme-primary mb-3" />
                <p className="text-gray-600">Validando archivo...</p>
              </div>
            ) : archivo ? (
              <div className="flex flex-col items-center">
                <FaFileExcel className="text-4xl text-green-500 mb-3" />
                <p className="text-gray-800 font-medium">{archivo.name}</p>
                <p className="text-gray-500 text-sm mt-1">
                  {(archivo.size / 1024 / 1024).toFixed(2)} MB
                </p>
                <p className="text-gray-400 text-xs mt-2">
                  Click o arrastra otro archivo para reemplazar
                </p>
              </div>
            ) : (
              <div className="flex flex-col items-center">
                <FaCloudUploadAlt className="text-5xl text-gray-400 mb-3" />
                <p className="text-gray-600 font-medium">
                  Arrastra tu archivo Excel aquí
                </p>
                <p className="text-gray-400 text-sm mt-1">
                  o click para seleccionar
                </p>
                <p className="text-gray-400 text-xs mt-3">
                  Formatos: .xlsx, .xls | Máximo: {MAX_FILE_SIZE_MB}MB
                </p>
              </div>
            )}
          </div>
        )}

        {/* Errores de validación - Agrupados con lista expandible */}
        {erroresValidacion.length > 0 && (
          <div className="mt-4 space-y-2">
            {erroresValidacion.slice(0, mostrarTodosErrores ? erroresValidacion.length : 3).map((error, idx) => (
              <div 
                key={idx}
                className={`
                  p-3 rounded-lg flex items-start gap-3 text-sm
                  ${error.tipo === 'critico' 
                    ? 'bg-red-50 border border-red-200 text-red-800' 
                    : error.tipo === 'error'
                      ? 'bg-orange-50 border border-orange-200 text-orange-800'
                      : 'bg-yellow-50 border border-yellow-200 text-yellow-800'
                  }
                `}
              >
                {error.tipo === 'critico' 
                  ? <FaExclamationCircle className="text-red-500 mt-0.5 flex-shrink-0" />
                  : error.tipo === 'error'
                    ? <FaExclamationTriangle className="text-orange-500 mt-0.5 flex-shrink-0" />
                    : <FaInfoCircle className="text-yellow-500 mt-0.5 flex-shrink-0" />
                }
                <div className="flex-1">
                  <p className="font-medium">{error.mensaje}</p>
                  {error.detalle && <p className="text-xs opacity-80 mt-1">{error.detalle}</p>}
                </div>
              </div>
            ))}
            
            {/* Botón para ver más/menos errores */}
            {erroresValidacion.length > 3 && (
              <button
                onClick={() => setMostrarTodosErrores(!mostrarTodosErrores)}
                className="w-full py-2 px-4 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm font-medium text-gray-600 flex items-center justify-center gap-2 transition"
              >
                <FaList />
                {mostrarTodosErrores 
                  ? 'Ocultar errores' 
                  : `Ver todos los errores (${erroresValidacion.length})`
                }
                {mostrarTodosErrores ? <FaChevronUp /> : <FaChevronDown />}
              </button>
            )}
          </div>
        )}

        {/* Lista detallada de filas con error - expandible */}
        {preview && preview.erroresPorFila && preview.erroresPorFila.length > 0 && !resultadoImportacion && (
          <div className="mt-4 border border-red-200 rounded-lg overflow-hidden">
            <button
              onClick={() => setMostrarTodosErrores(!mostrarTodosErrores)}
              className="w-full px-4 py-3 bg-red-50 text-red-800 font-medium text-sm flex items-center justify-between hover:bg-red-100 transition"
            >
              <span className="flex items-center gap-2">
                <FaList /> Detalle de {preview.erroresPorFila.length} filas con errores
              </span>
              {mostrarTodosErrores ? <FaChevronUp /> : <FaChevronDown />}
            </button>
            
            {mostrarTodosErrores && (
              <div className="max-h-60 overflow-y-auto bg-white">
                {preview.erroresPorFila.map((item, idx) => (
                  <div key={idx} className="px-4 py-2 border-b last:border-b-0 text-sm">
                    <span className="font-mono font-bold text-red-600">Fila {item.fila}:</span>
                    <span className="ml-2 text-gray-700">
                      {item.errores.map(e => e.mensaje).join(', ')}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Vista previa de datos */}
        {preview && !resultadoImportacion && (
          <div className="mt-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-gray-800 flex items-center gap-2">
                <FaEye /> Vista previa
              </h3>
              <div className="flex gap-4 text-sm">
                <span className="text-gray-600">
                  Total: <strong>{preview.totalFilas}</strong>
                </span>
                <span className="text-green-600">
                  Válidas: <strong>{preview.filasValidas}</strong>
                </span>
                {preview.filasConError > 0 && (
                  <span className="text-red-600">
                    Con error: <strong>{preview.filasConError}</strong>
                  </span>
                )}
                {preview.filasDuplicadas > 0 && (
                  <span className="text-yellow-600">
                    Duplicadas: <strong>{preview.filasDuplicadas}</strong>
                  </span>
                )}
              </div>
            </div>
            
            {/* Encabezados de columnas detectadas */}
            <div className="mb-3 p-3 bg-gray-50 rounded-lg border">
              <div className="flex flex-wrap gap-2 text-xs">
                <span className="font-semibold text-gray-700">Columnas detectadas:</span>
                {preview.headers.filter(h => h && h.trim()).map((h, i) => {
                  const esRequerida = preview.columnasEncontradas.some(ce => columnaCoincide(h, ce, config.sinonimosCols));
                  const falta = preview.columnasFaltantes.some(cf => normalizarHeader(cf) === normalizarHeader(h));
                  return (
                    <span 
                      key={i}
                      className={`px-2 py-1 rounded-full ${
                        falta ? 'bg-red-100 text-red-700' :
                        esRequerida ? 'bg-green-100 text-green-700 font-medium' :
                        'bg-gray-200 text-gray-600'
                      }`}
                    >
                      {h}
                      {esRequerida && ' ✓'}
                    </span>
                  );
                })}
              </div>
              {preview.columnasFaltantes.length > 0 && (
                <div className="mt-2 text-xs text-red-600">
                  <strong>Faltan:</strong> {preview.columnasFaltantes.join(', ')}
                </div>
              )}
            </div>
            
            {/* Tabla de preview - con paginación */}
            <div className="border rounded-lg overflow-hidden">
              {/* Header fijo fuera del scroll */}
              <div className="overflow-x-auto bg-gray-100">
                <table className="min-w-full text-xs" style={{ tableLayout: 'auto' }}>
                  <thead>
                    <tr>
                      <th className="px-3 py-2 text-left font-bold text-gray-700 border-r bg-gray-100 whitespace-nowrap" style={{ minWidth: '60px' }}>#</th>
                      {preview.headers.map((h, i) => (
                        <th 
                          key={i} 
                          className={`
                            px-3 py-2 text-left font-bold border-r whitespace-nowrap
                            ${preview.columnasFaltantes.some(cf => normalizarHeader(cf) === normalizarHeader(h)) 
                              ? 'bg-red-100 text-red-800' 
                              : preview.columnasEncontradas.some(ce => columnaCoincide(h, ce, config.sinonimosCols))
                                ? 'bg-green-100 text-green-800'
                                : 'bg-gray-100 text-gray-700'
                            }
                          `}
                          style={{ minWidth: '120px' }}
                        >
                          {h || '(vacío)'}
                        </th>
                      ))}
                    </tr>
                  </thead>
                </table>
              </div>
              {/* Body con scroll horizontal */}
              <div className="overflow-x-auto" style={{ maxHeight: '320px', overflowY: 'auto' }}>
                <table className="min-w-full text-xs" style={{ tableLayout: 'auto' }}>
                  <tbody>
                    {filasPaginadas.map((row, rowIdx) => (
                      <tr 
                        key={rowIdx}
                        className={`
                          border-b
                          ${row.tieneError 
                            ? 'bg-red-50' 
                            : row.esDuplicado 
                              ? 'bg-yellow-50' 
                              : rowIdx % 2 === 0 ? 'bg-white' : 'bg-gray-50'
                          }
                        `}
                      >
                        <td className="px-3 py-1.5 text-gray-500 border-r font-mono bg-gray-50 whitespace-nowrap" style={{ minWidth: '60px' }}>
                          <span className="font-bold">{row.numero}</span>
                          {row.tieneError && <FaExclamationCircle className="inline ml-1 text-red-500" title="Fila con errores" />}
                          {row.esDuplicado && <FaExclamationTriangle className="inline ml-1 text-yellow-500" title="Posible duplicado" />}
                        </td>
                        {row.datos.map((cell, cellIdx) => {
                          const valorFormateado = formatearCelda(cell);
                          const estaVacio = !valorFormateado || valorFormateado.trim() === '';
                          return (
                            <td 
                              key={cellIdx} 
                              className={`px-3 py-1.5 border-r whitespace-nowrap ${
                                estaVacio ? 'text-gray-300 italic' : 'text-gray-700'
                              }`}
                              style={{ minWidth: '120px', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis' }}
                              title={valorFormateado}
                            >
                              {estaVacio ? '—' : valorFormateado}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              
              {/* Paginación elegante */}
              {totalPaginas > 1 && (
                <div className="px-4 py-3 bg-gray-50 border-t flex items-center justify-between">
                  <div className="text-xs text-gray-600">
                    Mostrando {((paginaActual - 1) * ROWS_PER_PAGE) + 1}-{Math.min(paginaActual * ROWS_PER_PAGE, preview.totalFilas)} de {preview.totalFilas} filas
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => setPaginaActual(1)}
                      disabled={paginaActual === 1}
                      className="px-2 py-1 rounded text-xs font-medium text-gray-600 hover:bg-gray-200 disabled:opacity-40 disabled:cursor-not-allowed"
                      title="Primera página"
                    >
                      ««
                    </button>
                    <button
                      onClick={() => setPaginaActual(p => Math.max(1, p - 1))}
                      disabled={paginaActual === 1}
                      className="p-1.5 rounded hover:bg-gray-200 disabled:opacity-40 disabled:cursor-not-allowed"
                      title="Página anterior"
                    >
                      <FaChevronLeft className="text-gray-600" size={12} />
                    </button>
                    
                    {/* Números de página */}
                    <div className="flex items-center gap-1 mx-2">
                      {Array.from({ length: Math.min(5, totalPaginas) }, (_, i) => {
                        let pageNum;
                        if (totalPaginas <= 5) {
                          pageNum = i + 1;
                        } else if (paginaActual <= 3) {
                          pageNum = i + 1;
                        } else if (paginaActual >= totalPaginas - 2) {
                          pageNum = totalPaginas - 4 + i;
                        } else {
                          pageNum = paginaActual - 2 + i;
                        }
                        return (
                          <button
                            key={pageNum}
                            onClick={() => setPaginaActual(pageNum)}
                            className={`w-7 h-7 rounded text-xs font-medium transition ${
                              paginaActual === pageNum
                                ? 'bg-theme-primary text-white'
                                : 'text-gray-600 hover:bg-gray-200'
                            }`}
                          >
                            {pageNum}
                          </button>
                        );
                      })}
                    </div>
                    
                    <button
                      onClick={() => setPaginaActual(p => Math.min(totalPaginas, p + 1))}
                      disabled={paginaActual === totalPaginas}
                      className="p-1.5 rounded hover:bg-gray-200 disabled:opacity-40 disabled:cursor-not-allowed"
                      title="Página siguiente"
                    >
                      <FaChevronRight className="text-gray-600" size={12} />
                    </button>
                    <button
                      onClick={() => setPaginaActual(totalPaginas)}
                      disabled={paginaActual === totalPaginas}
                      className="px-2 py-1 rounded text-xs font-medium text-gray-600 hover:bg-gray-200 disabled:opacity-40 disabled:cursor-not-allowed"
                      title="Última página"
                    >
                      »»
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Progreso de importación */}
        {importando && (
          <div className="mt-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700">Importando...</span>
              <span className="text-sm font-medium text-theme-primary">{progreso}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
              <div 
                className="h-full bg-theme-gradient rounded-full transition-all duration-300"
                style={{ width: `${progreso}%` }}
              />
            </div>
            <p className="text-xs text-gray-500 mt-2 text-center">
              No cierre esta ventana. El proceso puede tardar según el volumen de datos.
            </p>
          </div>
        )}

        {/* Resultado de importación */}
        {resultadoImportacion && (
          <div className={`
            mt-6 p-6 rounded-xl border-2
            ${resultadoImportacion.exitoso 
              ? 'bg-green-50 border-green-300' 
              : 'bg-red-50 border-red-300'
            }
          `}>
            <div className="flex items-start gap-4">
              {resultadoImportacion.exitoso 
                ? <FaCheckCircle className="text-3xl text-green-500 flex-shrink-0" />
                : <FaExclamationCircle className="text-3xl text-red-500 flex-shrink-0" />
              }
              <div className="flex-1">
                <h3 className={`font-bold text-lg ${resultadoImportacion.exitoso ? 'text-green-800' : 'text-red-800'}`}>
                  {resultadoImportacion.exitoso ? 'Importación Exitosa' : 'Error en Importación'}
                </h3>
                <p className={`text-sm mt-1 ${resultadoImportacion.exitoso ? 'text-green-700' : 'text-red-700'}`}>
                  {resultadoImportacion.mensaje}
                </p>
                
                {/* Resumen de conteos */}
                <div className="flex flex-wrap gap-4 mt-4">
                  {resultadoImportacion.creados > 0 && (
                    <div className="px-4 py-2 bg-green-100 rounded-lg">
                      <span className="text-green-800 font-bold text-lg">{resultadoImportacion.creados}</span>
                      <span className="text-green-700 text-sm ml-2">creados</span>
                    </div>
                  )}
                  {resultadoImportacion.actualizados > 0 && (
                    <div className="px-4 py-2 bg-blue-100 rounded-lg">
                      <span className="text-blue-800 font-bold text-lg">{resultadoImportacion.actualizados}</span>
                      <span className="text-blue-700 text-sm ml-2">actualizados</span>
                    </div>
                  )}
                  {resultadoImportacion.errores > 0 && (
                    <div className="px-4 py-2 bg-red-100 rounded-lg">
                      <span className="text-red-800 font-bold text-lg">{resultadoImportacion.errores}</span>
                      <span className="text-red-700 text-sm ml-2">con error</span>
                    </div>
                  )}
                  {resultadoImportacion.omitidos > 0 && (
                    <div className="px-4 py-2 bg-gray-100 rounded-lg">
                      <span className="text-gray-800 font-bold text-lg">{resultadoImportacion.omitidos}</span>
                      <span className="text-gray-700 text-sm ml-2">omitidos</span>
                    </div>
                  )}
                </div>
                
                {/* Botones de acción */}
                <div className="flex flex-wrap gap-3 mt-4">
                  {(resultadoImportacion.detalleErrores?.length > 0 || resultadoImportacion.detalleActualizados?.length > 0) && (
                    <button
                      onClick={descargarReporteErrores}
                      className={`flex items-center gap-2 px-4 py-2 text-white rounded-lg transition text-sm font-medium ${
                        resultadoImportacion.detalleErrores?.length > 0 
                          ? 'bg-red-600 hover:bg-red-700' 
                          : 'bg-amber-600 hover:bg-amber-700'
                      }`}
                    >
                      <FaFileDownload /> 
                      {resultadoImportacion.detalleErrores?.length > 0 && resultadoImportacion.detalleActualizados?.length > 0 
                        ? `Descargar reporte completo (${resultadoImportacion.detalleErrores.length} errores, ${resultadoImportacion.detalleActualizados.length} actualizados)`
                        : resultadoImportacion.detalleErrores?.length > 0 
                          ? `Descargar reporte de errores (${resultadoImportacion.detalleErrores.length})`
                          : `Descargar reporte de actualizados (${resultadoImportacion.detalleActualizados.length})`
                      }
                    </button>
                  )}
                  <button
                    onClick={reiniciar}
                    className="flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition text-sm font-medium"
                  >
                    <FaSync /> Nueva importación
                  </button>
                </div>
                
                {/* Lista de errores detallados */}
                {resultadoImportacion.detalleErrores?.length > 0 && (
                  <div className="mt-6 bg-white rounded-xl border border-red-200 overflow-hidden">
                    {/* Header de la sección de errores */}
                    <button
                      onClick={() => setMostrarTodosErrores(!mostrarTodosErrores)}
                      className="w-full px-4 py-3 bg-red-100 flex items-center justify-between hover:bg-red-150 transition"
                    >
                      <div className="flex items-center gap-2">
                        <FaExclamationTriangle className="text-red-500" />
                        <span className="font-semibold text-red-800">
                          Detalle de errores ({resultadoImportacion.detalleErrores.length})
                        </span>
                      </div>
                      {mostrarTodosErrores ? <FaChevronUp className="text-red-500" /> : <FaChevronDown className="text-red-500" />}
                    </button>
                    
                    {/* Lista de errores */}
                    {mostrarTodosErrores && (
                      <div className="max-h-80 overflow-y-auto">
                        {resultadoImportacion.detalleErrores.map((error, idx) => (
                          <div 
                            key={idx} 
                            className={`px-4 py-3 border-b border-red-100 last:border-b-0 ${idx % 2 === 0 ? 'bg-white' : 'bg-red-50/30'}`}
                          >
                            <div className="flex items-start gap-3">
                              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-red-100 text-red-600 text-xs font-bold flex items-center justify-center">
                                {idx + 1}
                              </span>
                              <div className="flex-1 min-w-0">
                                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
                                  {error.fila && (
                                    <span className="text-gray-600">
                                      <span className="text-gray-400">Fila:</span> <strong>{error.fila}</strong>
                                    </span>
                                  )}
                                  {error.campo && (
                                    <span className="text-gray-600">
                                      <span className="text-gray-400">Campo:</span> <strong className="text-blue-600">{error.campo}</strong>
                                    </span>
                                  )}
                                  {error.valor !== undefined && error.valor !== null && error.valor !== '' && (
                                    <span className="text-gray-600">
                                      <span className="text-gray-400">Valor:</span> <code className="bg-gray-100 px-1 rounded text-xs">{String(error.valor).substring(0, 50)}{String(error.valor).length > 50 ? '...' : ''}</code>
                                    </span>
                                  )}
                                </div>
                                <p className="text-red-700 text-sm mt-1 font-medium">
                                  ⚠️ {error.mensaje || error.error || 'Error desconocido'}
                                </p>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                    
                    {/* Resumen cuando está colapsado */}
                    {!mostrarTodosErrores && (
                      <div className="px-4 py-3 text-sm text-red-700">
                        <p>
                          Click para ver los {resultadoImportacion.detalleErrores.length} error(es) detallados. 
                          También puede descargar el reporte completo en Excel.
                        </p>
                      </div>
                    )}
                  </div>
                )}
                
                {/* Lista de productos actualizados (duplicados) */}
                {resultadoImportacion.detalleActualizados?.length > 0 && (
                  <div className="mt-6 bg-white rounded-xl border border-amber-200 overflow-hidden">
                    {/* Header de la sección de actualizados */}
                    <button
                      onClick={() => setMostrarTodosActualizados(!mostrarTodosActualizados)}
                      className="w-full px-4 py-3 bg-amber-100 flex items-center justify-between hover:bg-amber-150 transition"
                    >
                      <div className="flex items-center gap-2">
                        <FaSync className="text-amber-600" />
                        <span className="font-semibold text-amber-800">
                          Productos actualizados ({resultadoImportacion.detalleActualizados.length})
                        </span>
                      </div>
                      {mostrarTodosActualizados ? <FaChevronUp className="text-amber-500" /> : <FaChevronDown className="text-amber-500" />}
                    </button>
                    
                    {/* Lista de actualizados */}
                    {mostrarTodosActualizados && (
                      <div className="max-h-80 overflow-y-auto">
                        {resultadoImportacion.detalleActualizados.map((item, idx) => (
                          <div 
                            key={idx} 
                            className={`px-4 py-3 border-b border-amber-100 last:border-b-0 ${idx % 2 === 0 ? 'bg-white' : 'bg-amber-50/30'}`}
                          >
                            <div className="flex items-start gap-3">
                              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-amber-100 text-amber-700 text-xs font-bold flex items-center justify-center">
                                {idx + 1}
                              </span>
                              <div className="flex-1 min-w-0">
                                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
                                  {item.fila && (
                                    <span className="text-gray-600">
                                      <span className="text-gray-400">Fila:</span> <strong>{item.fila}</strong>
                                    </span>
                                  )}
                                  {item.clave && (
                                    <span className="text-gray-600">
                                      <span className="text-gray-400">Clave:</span> <strong className="text-blue-600">{item.clave}</strong>
                                    </span>
                                  )}
                                  {item.nombre && (
                                    <span className="text-gray-600 truncate max-w-xs">
                                      <span className="text-gray-400">Nombre:</span> <strong>{item.nombre}</strong>
                                    </span>
                                  )}
                                </div>
                                <p className="text-amber-700 text-sm mt-1">
                                  🔄 {item.mensaje || 'Producto existente actualizado'}
                                </p>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                    
                    {/* Resumen cuando está colapsado */}
                    {!mostrarTodosActualizados && (
                      <div className="px-4 py-3 text-sm text-amber-700">
                        <p>
                          Click para ver los {resultadoImportacion.detalleActualizados.length} producto(s) que ya existían y fueron actualizados.
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Botón de importar */}
        {!resultadoImportacion && archivo && !importando && (
          <div className="mt-6 flex justify-end">
            <button
              onClick={ejecutarImportacion}
              disabled={!puedeImportar}
              className={`
                flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-white transition-all
                ${puedeImportar 
                  ? 'btn-elevated-primary !px-6 !py-3 !text-base' 
                  : 'bg-gray-400 cursor-not-allowed'
                }
              `}
            >
              <FaCloudUploadAlt />
              Importar {preview?.filasValidas || 0} registros
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default ImportadorModerno;
