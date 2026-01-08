import ExcelJS from 'exceljs';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

// Obtener colores del tema desde CSS variables (set by ThemeProvider)
const getThemeColors = () => {
  const root = document.documentElement;
  const getVar = (name, fallback) =>
    getComputedStyle(root).getPropertyValue(name).trim() || fallback;
  
  return {
    primary: getVar('--color-primary', '#9F2241'),
    primaryHover: getVar('--color-primary-hover', '#6B1839'),
    secondary: getVar('--color-secondary', '#6B1839'),
    text: getVar('--color-text-primary', '#1F2937'),
    textSecondary: getVar('--color-text-secondary', '#6b7280'),
    // Colores específicos de reportes
    reporteEncabezado: getVar('--color-reporte-encabezado', '#632842'),
    reporteTextoEncabezado: getVar('--color-reporte-texto-encabezado', '#FFFFFF'),
    reporteFilasAlternas: getVar('--color-reporte-filas-alternas', '#F5F5F5'),
  };
};

// Obtener configuración del tema para reportes
const getThemeConfig = () => {
  const root = document.documentElement;
  const getVar = (name, fallback) =>
    getComputedStyle(root).getPropertyValue(name).trim() || fallback;
  
  return {
    nombreInstitucion: getVar('--tema-nombre-institucion', 'Sistema de Farmacia Penitenciaria'),
    subtitulo: getVar('--tema-subtitulo', 'Gobierno del Estado de México'),
    piePagina: getVar('--tema-pie-pagina', ''),
    anoVisible: getVar('--tema-ano-visible', new Date().getFullYear().toString()),
  };
};

// Convertir hex a RGB array para jsPDF
const hexToRgb = (hex) => {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result
    ? [parseInt(result[1], 16), parseInt(result[2], 16), parseInt(result[3], 16)]
    : [159, 34, 65]; // fallback guinda
};

const XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
const PDF_MIME = 'application/pdf';

const hexToARGB = (hex) => `FF${hex.replace('#', '').toUpperCase()}`;

const triggerDownload = (blob, fileName) => {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', fileName);
  document.body.appendChild(link);
  link.click();
  link.remove();
};

const addFooter = (sheet, columnCount, colors, config) => {
  sheet.addRow([]);
  const lastRowNumber = sheet.lastRow.number;
  sheet.mergeCells(lastRowNumber, 1, lastRowNumber, columnCount);
  const footerCell = sheet.getCell(`A${lastRowNumber}`);
  // Usar texto del tema o fallback
  const footerText = config.piePagina || `${config.nombreInstitucion} - ${config.subtitulo}`;
  footerCell.value = footerText;
  footerCell.font = {
    italic: true,
    size: 12,
    color: { argb: hexToARGB(colors.secondary) },
  };
  footerCell.alignment = { horizontal: 'center' };
};

export const createExcelReport = async ({ title, subtitle, columns, rows, fileName }) => {
  // Obtener colores y config del tema
  const colors = getThemeColors();
  const config = getThemeConfig();
  
  const workbook = new ExcelJS.Workbook();
  workbook.created = new Date();
  const sheet = workbook.addWorksheet('Reporte');

  sheet.mergeCells(1, 1, 1, columns.length);
  const titleCell = sheet.getCell(1, 1);
  titleCell.value = title;
  titleCell.fill = {
    type: 'gradient',
    gradient: 'angle',
    degree: 45,
    stops: [
      { position: 0, color: { argb: hexToARGB(colors.primary) } },
      { position: 1, color: { argb: hexToARGB(colors.secondary) } },
    ],
  };
  titleCell.font = { size: 18, bold: true, color: { argb: 'FFFFFFFF' } };
  titleCell.alignment = { horizontal: 'center', vertical: 'middle' };
  sheet.getRow(1).height = 34;

  if (subtitle) {
    sheet.mergeCells(2, 1, 2, columns.length);
    const subtitleCell = sheet.getCell(2, 1);
    subtitleCell.value = subtitle;
    subtitleCell.font = { size: 12, color: { argb: hexToARGB(colors.textSecondary) } };
    subtitleCell.alignment = { horizontal: 'center' };
    sheet.getRow(2).height = 20;
  }

  sheet.addRow([]);

  const headerRow = sheet.addRow(columns.map((col) => col.header));
  headerRow.eachCell((cell) => {
    cell.fill = {
      type: 'pattern',
      pattern: 'solid',
      fgColor: { argb: hexToARGB(colors.primary) },
    };
    cell.font = { bold: true, color: { argb: 'FFFFFFFF' } };
    cell.alignment = { horizontal: 'center', vertical: 'middle' };
    cell.border = {
      top: { style: 'thin', color: { argb: 'FFFFFFFF' } },
      left: { style: 'thin', color: { argb: 'FFFFFFFF' } },
      bottom: { style: 'thin', color: { argb: 'FFFFFFFF' } },
      right: { style: 'thin', color: { argb: 'FFFFFFFF' } },
    };
  });

  rows.forEach((row, index) => {
    const rowValues = columns.map((col) =>
      typeof col.value === 'function' ? col.value(row, index) : row[col.key] ?? ''
    );
    const excelRow = sheet.addRow(rowValues);
    excelRow.eachCell((cell) => {
      cell.border = {
        top: { style: 'hair', color: { argb: 'FFDDDDDD' } },
        left: { style: 'hair', color: { argb: 'FFDDDDDD' } },
        bottom: { style: 'hair', color: { argb: 'FFDDDDDD' } },
        right: { style: 'hair', color: { argb: 'FFDDDDDD' } },
      };
    });
  });

  columns.forEach((col, index) => {
    sheet.getColumn(index + 1).width = col.width || 20;
  });

  addFooter(sheet, columns.length, colors, config);

  const buffer = await workbook.xlsx.writeBuffer();
  const blob = new Blob([buffer], { type: XLSX_MIME });
  triggerDownload(blob, `${fileName}.xlsx`);
};

const createPdfReport = ({ title, subtitle, columns, rows, fileName, orientation = 'landscape' }) => {
  // Obtener colores y config del tema
  const colors = getThemeColors();
  const config = getThemeConfig();
  const primaryRgb = hexToRgb(colors.primary);
  const secondaryRgb = hexToRgb(colors.secondary);
  const textRgb = hexToRgb(colors.text);
  
  const doc = new jsPDF(orientation, 'pt', 'a4');
  const pageWidth = doc.internal.pageSize.getWidth();
  
  // Encabezado con color primario del tema
  doc.setFillColor(...primaryRgb);
  doc.rect(0, 0, pageWidth, 60, 'F');
  doc.setFontSize(18);
  doc.setTextColor(255, 255, 255);
  doc.text(title, 40, 38);
  if (subtitle) {
    doc.setFontSize(11);
    doc.setTextColor(249, 230, 235);
    doc.text(subtitle, 40, 52);
  }

  autoTable(doc, {
    startY: 80,
    head: [columns.map((col) => col.header)],
    body: rows.map((row, index) =>
      columns.map((col) =>
        typeof col.value === 'function' ? col.value(row, index) : row[col.key] ?? ''
      )
    ),
    styles: { 
      fontSize: 8, 
      cellPadding: 4, 
      textColor: textRgb,
      overflow: 'linebreak',  // IMPORTANTE: ajustar texto con saltos de línea
      cellWidth: 'wrap',      // Permitir que las celdas se expandan verticalmente
    },
    headStyles: { 
      fillColor: primaryRgb, 
      textColor: [255, 255, 255],
      fontStyle: 'bold',
      halign: 'center',
    },
    alternateRowStyles: { fillColor: hexToRgb(colors.reporteFilasAlternas) },
    margin: { left: 30, right: 30 },
    tableWidth: 'auto',
    // Configuración para columnas específicas que pueden tener texto largo
    columnStyles: {
      // Permitir que las columnas con texto largo se ajusten
    },
    didParseCell: function(data) {
      // Asegurar que el texto nunca se trunque
      if (data.cell.text && data.cell.text.length > 0) {
        data.cell.styles.cellWidth = 'wrap';
      }
    },
  });

  // Pie de página con texto del tema
  const footerText = config.piePagina || `${config.nombreInstitucion} - ${config.subtitulo}`;
  doc.setFontSize(10);
  doc.setTextColor(...secondaryRgb);
  doc.text(
    footerText,
    40,
    doc.internal.pageSize.getHeight() - 24
  );

  const blob = doc.output('blob');
  blob.name = `${fileName}.pdf`;
  triggerDownload(blob, `${fileName}.pdf`);
};

const BASE_INVENTARIO = [
  { clave: 'MED-001', descripcion: 'Ibuprofeno 400mg tabletas', unidad: 'CAJA', stock: 120, valor: 4500, centro: 'Almacén Central' },
  { clave: 'MED-015', descripcion: 'Amoxicilina 875mg', unidad: 'FRASCO', stock: 85, valor: 6125, centro: 'Almacén Central' },
  { clave: 'MED-024', descripcion: 'Metformina 850mg', unidad: 'CAJA', stock: 200, valor: 7800, centro: 'Penal de Toluca' },
  { clave: 'MED-041', descripcion: 'Alcohol etílico 70%', unidad: 'GALÓN', stock: 45, valor: 2250, centro: 'Penal Nezahualcóyotl' },
  { clave: 'MED-057', descripcion: 'Paracetamol 500mg', unidad: 'CAJA', stock: 310, valor: 9300, centro: 'Almacén Central' },
];

const BASE_MOVIMIENTOS = [
  { fecha: '2025-11-15', folio: 'MOV-0251', tipo: 'Entrada', producto: 'MED-001 Ibuprofeno 400mg', cantidad: 250, centro: 'Almacén Central', usuario: 'Administrador' },
  { fecha: '2025-11-16', folio: 'MOV-0252', tipo: 'Salida', producto: 'MED-041 Alcohol 70%', cantidad: 40, centro: 'Penal Nezahualcóyotl', usuario: 'Administrador' },
  { fecha: '2025-11-18', folio: 'MOV-0253', tipo: 'Salida', producto: 'MED-024 Metformina 850mg', cantidad: 150, centro: 'Penal de Toluca', usuario: 'Administrador' },
  { fecha: '2025-11-19', folio: 'MOV-0254', tipo: 'Entrada', producto: 'MED-057 Paracetamol 500mg', cantidad: 300, centro: 'Almacén Central', usuario: 'Administrador' },
  { fecha: '2025-11-21', folio: 'MOV-0255', tipo: 'Ajuste', producto: 'MED-015 Amoxicilina 875mg', cantidad: -10, centro: 'Almacén Central', usuario: 'Administrador' },
];

const BASE_CADUCIDADES = [
  { lote: 'L-2024-010', producto: 'MED-057 Paracetamol 500mg', centro: 'Almacén Central', dias: 18, fecha_caducidad: '2025-12-10', estado: 'Crítico' },
  { lote: 'L-2024-011', producto: 'MED-024 Metformina 850mg', centro: 'Penal de Toluca', dias: 45, fecha_caducidad: '2026-01-05', estado: 'Próximo' },
  { lote: 'L-2024-012', producto: 'MED-001 Ibuprofeno 400mg', centro: 'Almacén Central', dias: 5, fecha_caducidad: '2025-11-26', estado: 'Crítico' },
  { lote: 'L-2023-201', producto: 'MED-041 Alcohol 70%', centro: 'Penal Nezahualcóyotl', dias: -12, fecha_caducidad: '2025-11-07', estado: 'Vencido' },
];

const formatSubtitle = (text) =>
  `${text}  Generado ${new Date().toLocaleDateString('es-MX', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })}`;

export const generarReporteInventarioDev = async (formato = 'excel') => {
  const payload = {
    title: 'Reporte de Inventario',
    subtitle: formatSubtitle('Productos activos y valor estimado'),
    columns: [
      { header: '#', value: (_, index) => index + 1, width: 6 },
      { header: 'Clave', key: 'clave', width: 14 },
      { header: 'Descripción', key: 'descripcion', width: 40 },
      { header: 'Unidad', key: 'unidad', width: 12 },
      { header: 'Inventario', key: 'stock', width: 10 },
      { header: 'Valor estimado', value: (row) => `$${row.valor.toFixed(2)}`, width: 18 },
      { header: 'Centro', key: 'centro', width: 24 },
    ],
    rows: BASE_INVENTARIO,
    fileName: `inventario_${new Date().toISOString().split('T')[0]}`,
  };

  if (formato === 'pdf') {
    createPdfReport(payload);
  } else {
    await createExcelReport(payload);
  }
};

export const generarReporteMovimientosDev = async ({ formato = 'excel', fecha_inicio, fecha_fin }) => {
  const rango =
    fecha_inicio && fecha_fin
      ? `Del ${fecha_inicio} al ${fecha_fin}`
      : 'Sin rango definido';
  const payload = {
    title: 'Reporte de Movimientos',
    subtitle: formatSubtitle(rango),
    columns: [
      { header: '#', value: (_, index) => index + 1, width: 6 },
      { header: 'Fecha', key: 'fecha', width: 18 },
      { header: 'Folio', key: 'folio', width: 16 },
      { header: 'Tipo', key: 'tipo', width: 16 },
      { header: 'Producto', key: 'producto', width: 36 },
      { header: 'Cantidad', key: 'cantidad', width: 14 },
      { header: 'Centro', key: 'centro', width: 24 },
      { header: 'Usuario', key: 'usuario', width: 22 },
    ],
    rows: BASE_MOVIMIENTOS,
    fileName: `movimientos_${fecha_inicio || 'sin_fecha'}_${fecha_fin || 'sin_fecha'}`,
  };

  if (formato === 'pdf') {
    createPdfReport(payload);
  } else {
    await createExcelReport(payload);
  }
};

export const generarReporteCaducidadesDev = async ({ formato = 'excel', dias }) => {
  const payload = {
    title: 'Reporte de Caducidades',
    subtitle: formatSubtitle(`Lotes con vencimiento en ${dias || 30} días`),
    columns: [
      { header: '#', value: (_, index) => index + 1, width: 6 },
      { header: 'Lote', key: 'lote', width: 16 },
      { header: 'Producto', key: 'producto', width: 36 },
      { header: 'Centro', key: 'centro', width: 26 },
      { header: 'Días restantes', key: 'dias', width: 16 },
      { header: 'Fecha caducidad', key: 'fecha_caducidad', width: 20 },
      { header: 'Estado', key: 'estado', width: 14 },
    ],
    rows: BASE_CADUCIDADES,
    fileName: `caducidades_${dias || 30}dias_${new Date().toISOString().split('T')[0]}`,
  };

  if (formato === 'pdf') {
    createPdfReport(payload);
  } else {
    await createExcelReport(payload);
  }
};

export { XLSX_MIME, PDF_MIME };
