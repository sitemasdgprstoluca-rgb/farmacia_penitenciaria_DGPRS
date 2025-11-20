import { useState, useEffect } from 'react';
import { reportesAPI } from '../services/api'; // -o. CORREGIDO: Usa API centralizada
import { toast } from 'react-hot-toast';
import {
  FaCalendar,
  FaWarehouse,
  FaExclamationTriangle,
  FaChartLine,
  FaDownload,
} from 'react-icons/fa';
import PageHeader from '../components/PageHeader';
import {
  generarReporteInventarioDev,
  generarReporteMovimientosDev,
  generarReporteCaducidadesDev,
  XLSX_MIME,
  PDF_MIME
} from '../utils/reportExport';

const MOCK_PRECARGA = {
  productos: Array.from({ length: 111 }).map((_, index) => ({ id: index + 1 })),
  centros: Array.from({ length: 11 }).map((_, index) => ({ id: index + 1 })),
  lotes: Array.from({ length: 60 }).map((_, index) => ({ id: index + 1 })),
};

const isDevSession = () => false;

const obtenerExtension = (formato) => (formato === 'pdf' ? 'pdf' : 'xlsx');

const descargarBlob = (data, nombreBase, formato, contentType) => {
  const type = contentType || (formato === 'pdf' ? PDF_MIME : XLSX_MIME);
  const blob = new Blob([data], { type });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `${nombreBase}.${obtenerExtension(formato)}`);
  document.body.appendChild(link);
  link.click();
  link.remove();
};

const Reportes = () => {
  const [loading, setLoading] = useState(false);
  const [precarga, setPrecarga] = useState({ productos: [], centros: [], lotes: [] });
  
  // Filtros para reportes
  const [filtrosInventario, setFiltrosInventario] = useState({
    formato: 'excel'
  });
  
  const [filtrosMovimientos, setFiltrosMovimientos] = useState({
    fecha_inicio: '',
    fecha_fin: '',
    formato: 'excel'
  });
  
  const [filtrosCaducidades, setFiltrosCaducidades] = useState({
    dias: '30',
    formato: 'excel'
  });

  useEffect(() => {
    cargarPrecarga();
  }, []);

  const cargarPrecarga = async () => {
    try {
      if (isDevSession()) {
        setPrecarga(MOCK_PRECARGA);
        return;
      }
      const response = await reportesAPI.precarga();
      setPrecarga(response.data);
    } catch (error) {
      console.error('Error al cargar precarga:', error);
      if (isDevSession()) {
        setPrecarga(MOCK_PRECARGA);
      }
    }
  };

  const descargarInventario = async () => {
    setLoading(true);
    try {
      if (isDevSession()) {
        await generarReporteInventarioDev(filtrosInventario.formato);
        toast.success('Reporte de inventario descargado');
        return;
      }
      const response = await reportesAPI.inventario(filtrosInventario);
      descargarBlob(
        response.data,
        `inventario_${new Date().toISOString().split('T')[0]}`,
        filtrosInventario.formato,
        response.headers['content-type']
      );
      toast.success('Reporte de inventario descargado');
    } catch (error) {
      toast.error('Error al generar reporte de inventario');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const descargarMovimientos = async () => {
    if (!filtrosMovimientos.fecha_inicio || !filtrosMovimientos.fecha_fin) {
      toast.error('Seleccione rango de fechas');
      return;
    }

    setLoading(true);
    try {
      if (isDevSession()) {
        await generarReporteMovimientosDev(filtrosMovimientos);
        toast.success('Reporte de movimientos descargado');
        return;
      }
      const response = await reportesAPI.movimientos(filtrosMovimientos);
      descargarBlob(
        response.data,
        `movimientos_${filtrosMovimientos.fecha_inicio}_${filtrosMovimientos.fecha_fin}`,
        filtrosMovimientos.formato,
        response.headers['content-type']
      );
      toast.success('Reporte de movimientos descargado');
    } catch (error) {
      toast.error('Error al generar reporte de movimientos');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const descargarCaducidades = async () => {
    setLoading(true);
    try {
      if (isDevSession()) {
        await generarReporteCaducidadesDev(filtrosCaducidades);
        toast.success('Reporte de caducidades descargado');
        return;
      }
      const response = await reportesAPI.caducidades(filtrosCaducidades);
      descargarBlob(
        response.data,
        `caducidades_${filtrosCaducidades.dias}dias_${new Date().toISOString().split('T')[0]}`,
        filtrosCaducidades.formato,
        response.headers['content-type']
      );
      toast.success('Reporte de caducidades descargado');
    } catch (error) {
      toast.error('Error al generar reporte de caducidades');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const resumenTotales = `Productos: ${precarga.productos.length || 0} | Lotes: ${precarga.lotes.length || 0} | Centros: ${precarga.centros.length || 0}`;

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        icon={FaChartLine}
        title="Reportes del Sistema"
        subtitle="Genera reportes personalizados en Excel o PDF"
        badge={resumenTotales}
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Reporte de Inventario */}
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center gap-3 mb-4">
            <div className="bg-blue-100 p-3 rounded-lg">
              <FaWarehouse className="text-2xl text-blue-600" />
            </div>
            <div>
              <h2 className="text-lg font-bold">Reporte de Inventario</h2>
              <p className="text-sm text-gray-600">Inventario actual completo</p>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Formato</label>
              <select
                value={filtrosInventario.formato}
                onChange={(e) => setFiltrosInventario({...filtrosInventario, formato: e.target.value})}
                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="excel">Excel (.xlsx)</option>
                <option value="pdf">PDF</option>
              </select>
            </div>

            <button
              onClick={descargarInventario}
              disabled={loading}
              className="w-full bg-blue-600 text-white px-4 py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  Generando...
                </>
              ) : (
                <>
                  <FaDownload /> Descargar Inventario
                </>
              )}
            </button>
          </div>

          <div className="mt-4 p-3 bg-blue-50 rounded-lg">
            <p className="text-sm text-blue-800">
              <strong>Incluye:</strong> Stock actual, valor de inventario, lotes activos, nivel de stock
            </p>
          </div>
        </div>

        {/* Reporte de Movimientos */}
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center gap-3 mb-4">
            <div className="bg-green-100 p-3 rounded-lg">
              <FaChartLine className="text-2xl text-green-600" />
            </div>
            <div>
              <h2 className="text-lg font-bold">Reporte de Movimientos</h2>
              <p className="text-sm text-gray-600">Movimientos por periodo</p>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Fecha Inicio</label>
              <input
                type="date"
                value={filtrosMovimientos.fecha_inicio}
                onChange={(e) => setFiltrosMovimientos({...filtrosMovimientos, fecha_inicio: e.target.value})}
                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Fecha Fin</label>
              <input
                type="date"
                value={filtrosMovimientos.fecha_fin}
                onChange={(e) => setFiltrosMovimientos({...filtrosMovimientos, fecha_fin: e.target.value})}
                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500"
              />
            </div>            <div>
              <label className="block text-sm font-medium mb-2">Formato</label>
              <select
                value={filtrosMovimientos.formato}
                onChange={(e) => setFiltrosMovimientos({...filtrosMovimientos, formato: e.target.value})}
                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500"
              >
                <option value="excel">Excel (.xlsx)</option>
                <option value="pdf">PDF</option>
              </select>
            </div>

            <button
              onClick={descargarMovimientos}
              disabled={loading}
              className="w-full bg-green-600 text-white px-4 py-3 rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  Generando...
                </>
              ) : (
                <>
                  <FaDownload /> Descargar Movimientos
                </>
              )}
            </button>
          </div>

          <div className="mt-4 p-3 bg-green-50 rounded-lg">
            <p className="text-sm text-green-800">
              <strong>Incluye:</strong> Tipo de movimiento, cantidad, usuario, centro, fecha
            </p>
          </div>
        </div>

        {/* Reporte de Caducidades */}
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center gap-3 mb-4">
            <div className="bg-orange-100 p-3 rounded-lg">
              <FaExclamationTriangle className="text-2xl text-orange-600" />
            </div>
            <div>
              <h2 className="text-lg font-bold">Reporte de Caducidades</h2>
              <p className="text-sm text-gray-600">Lotes príximos a vencer</p>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Días de Anticipación</label>
              <select
                value={filtrosCaducidades.dias}
                onChange={(e) => setFiltrosCaducidades({...filtrosCaducidades, dias: e.target.value})}
                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-orange-500"
              >
                <option value="7">7 días</option>
                <option value="15">15 días</option>
                <option value="30">30 días</option>
                <option value="60">60 días</option>
                <option value="90">90 días</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Formato</label>
              <select
                value={filtrosCaducidades.formato}
                onChange={(e) => setFiltrosCaducidades({...filtrosCaducidades, formato: e.target.value})}
                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-orange-500"
              >
                <option value="excel">Excel (.xlsx)</option>
                <option value="pdf">PDF</option>
              </select>
            </div>

            <button
              onClick={descargarCaducidades}
              disabled={loading}
              className="w-full bg-orange-600 text-white px-4 py-3 rounded-lg hover:bg-orange-700 disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  Generando...
                </>
              ) : (
                <>
                  <FaDownload /> Descargar Caducidades
                </>
              )}
            </button>
          </div>

          <div className="mt-4 p-3 bg-orange-50 rounded-lg">
            <p className="text-sm text-orange-800">
              <strong>Incluye:</strong> Lote, producto, días restantes, alerta, cantidad, proveedor
            </p>
          </div>
        </div>

        {/* Información del Sistema */}
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center gap-3 mb-4">
            <div className="bg-purple-100 p-3 rounded-lg">
              <FaCalendar className="text-2xl text-purple-600" />
            </div>
            <div>
              <h2 className="text-lg font-bold">Información del Sistema</h2>
              <p className="text-sm text-gray-600">Datos disponibles</p>
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
              <span className="text-sm font-medium">Productos Activos</span>
              <span className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm font-bold">
                {precarga.productos.length}
              </span>
            </div>
            <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
              <span className="text-sm font-medium">Lotes Registrados</span>
              <span className="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-bold">
                {precarga.lotes.length}
              </span>
            </div>
            <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
              <span className="text-sm font-medium">Centros Activos</span>
              <span className="bg-purple-100 text-purple-800 px-3 py-1 rounded-full text-sm font-bold">
                {precarga.centros.length}
              </span>
            </div>
          </div>

          <div className="mt-4 p-3 bg-purple-50 rounded-lg">
            <p className="text-xs text-purple-800">
              Los reportes se generan en tiempo real con los datos mís recientes del sistema.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Reportes;














