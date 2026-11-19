import ExcelJS from 'exceljs'

const COLORS = { night: '06322E', forest: '0A4B40', emerald: '21B77A', lime: 'B9EF81', ink: 'EAF7F1', muted: '9CB9B3', panel: 'EAF5F0', amber: 'F1BB4F', red: 'FF766F' }
const priorityColor = (priority) => priority === 'Alta' ? COLORS.red : priority === 'Media' ? COLORS.amber : COLORS.emerald
const asText = (value) => value ?? '-'

function applyBrandHeader(sheet, title, subtitle) {
  sheet.mergeCells('A1:G1')
  sheet.getCell('A1').value = title
  sheet.getCell('A1').font = { name: 'Aptos Display', size: 20, bold: true, color: { argb: COLORS.ink } }
  sheet.getCell('A1').fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.night } }
  sheet.getCell('A1').alignment = { vertical: 'middle', horizontal: 'left' }
  sheet.getRow(1).height = 35
  sheet.mergeCells('A2:G2')
  sheet.getCell('A2').value = subtitle
  sheet.getCell('A2').font = { name: 'Aptos', size: 10, color: { argb: COLORS.muted } }
  sheet.getCell('A2').fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.night } }
  sheet.getCell('A2').alignment = { vertical: 'middle' }
  sheet.getRow(2).height = 24
}

function styleTable(sheet, tableName) {
  const table = sheet.getTable(tableName)
  table.style = { theme: 'TableStyleMedium4', showRowStripes: true, showFirstColumn: false, showLastColumn: false }
  sheet.views = [{ state: 'frozen', ySplit: 4 }]
}

function fitColumns(sheet, widths) {
  widths.forEach((width, index) => { sheet.getColumn(index + 1).width = width })
}

function saveBrowserFile(buffer, fileName) {
  const url = URL.createObjectURL(new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }))
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  link.click()
  URL.revokeObjectURL(url)
}

export async function exportReportToExcel({ summary, residues, districtRows, priorities = [], filterDescription = 'Sin filtros aplicados' }) {
  const workbook = new ExcelJS.Workbook()
  workbook.creator = 'AQPredict Residuos'
  workbook.created = new Date()
  workbook.modified = new Date()
  const now = new Date()
  const total = summary?.residuos_registrados_kg || 0
  const priorityByZone = Object.fromEntries(priorities.map((item) => [item.zona, item.prioridad]))

  const overview = workbook.addWorksheet('Resumen', { views: [{ showGridLines: false }] })
  applyBrandHeader(overview, 'AQPredict Residuos | Reporte operativo', 'Gestión predictiva de residuos urbanos · Arequipa')
  overview.mergeCells('A4:G4')
  overview.getCell('A4').value = `Generado el ${now.toLocaleString('es-PE')} · ${filterDescription}`
  overview.getCell('A4').font = { name: 'Aptos', size: 10, italic: true, color: { argb: COLORS.forest } }
  overview.getCell('A4').alignment = { wrapText: true, vertical: 'middle' }
  overview.getRow(4).height = 32
  const metrics = [['Volumen filtrado', total, '#,##0 "kg"'], ['Distritos con registros', districtRows.length, '#,##0'], ['Registros analizados', residues.length, '#,##0'], ['Exactitud del modelo', (summary?.metricas_modelo?.exactitud ?? 0) / 100, '0.0%'], ['Coeficiente R²', (summary?.metricas_modelo?.r2 ?? 0) / 100, '0.0%']]
  metrics.forEach(([label, value, format], index) => {
    const row = 6 + index
    overview.getCell(`A${row}`).value = label
    overview.getCell(`A${row}`).font = { name: 'Aptos', bold: true, color: { argb: COLORS.forest } }
    overview.getCell(`A${row}`).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'DDF5E8' } }
    overview.getCell(`B${row}`).value = value
    overview.getCell(`B${row}`).font = { name: 'Aptos', bold: true, color: { argb: COLORS.night } }
    overview.getCell(`B${row}`).numFmt = format
    ;['A', 'B'].forEach((column) => { overview.getCell(`${column}${row}`).border = { bottom: { style: 'thin', color: { argb: 'C3E4D5' } } } })
  })
  overview.getCell('D6').value = 'Resumen por distrito'
  overview.getCell('D6').font = { name: 'Aptos', bold: true, color: { argb: COLORS.ink } }
  overview.getCell('D6').fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.forest } }
  overview.getCell('E6').fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.forest } }
  overview.getCell('D7').value = 'Distrito'
  overview.getCell('E7').value = 'Volumen (kg)'
  ;['D7', 'E7'].forEach((cell) => { overview.getCell(cell).font = { bold: true, color: { argb: COLORS.ink } }; overview.getCell(cell).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.emerald } } })
  districtRows.forEach(([district, amount], index) => { const row = 8 + index; overview.getCell(`D${row}`).value = district; overview.getCell(`E${row}`).value = amount; overview.getCell(`E${row}`).numFmt = '#,##0 "kg"' })
  fitColumns(overview, [29, 20, 4, 24, 20, 4, 4])

  const records = workbook.addWorksheet('Registros', { views: [{ showGridLines: false }] })
  applyBrandHeader(records, 'AQPredict Residuos | Registros filtrados', 'Detalle de las mediciones incluidas en este reporte')
  const recordRows = residues.map((row) => ({ Fecha: asText(row.Fecha), Hora: asText(row.Hora), Distrito: asText(row.Distrito), Zona: asText(row.Zona), 'Cantidad (kg)': Number(row['Cantidad (kg)']) || 0, 'Días sin recolección': Number(row['Días sin recolección']) || 0, Fuente: asText(row.Fuente), 'Prioridad actual': priorityByZone[row.Zona] || 'Sin calcular' }))
  records.addTable({ name: 'TablaRegistros', ref: 'A4', headerRow: true, totalsRow: true, style: { theme: 'TableStyleMedium4', showRowStripes: true }, columns: [{ name: 'Fecha', totalsRowLabel: 'Total' }, { name: 'Hora' }, { name: 'Distrito' }, { name: 'Zona' }, { name: 'Cantidad (kg)', totalsRowFunction: 'sum' }, { name: 'Días sin recolección' }, { name: 'Fuente' }, { name: 'Prioridad actual' }], rows: recordRows.map((row) => Object.values(row)) })
  styleTable(records, 'TablaRegistros')
  records.getColumn(5).numFmt = '#,##0'
  fitColumns(records, [14, 12, 20, 25, 17, 22, 17, 18])

  const districts = workbook.addWorksheet('Por distrito', { views: [{ showGridLines: false }] })
  applyBrandHeader(districts, 'AQPredict Residuos | Comparación por distrito', 'Acumulación registrada en el resultado filtrado')
  const districtDetail = districtRows.map(([district, amount]) => ({ Distrito: district, 'Volumen acumulado (kg)': amount, Participación: total ? amount / total : 0 }))
  districts.addTable({ name: 'TablaDistritos', ref: 'A4', headerRow: true, totalsRow: true, style: { theme: 'TableStyleMedium4', showRowStripes: true }, columns: [{ name: 'Distrito', totalsRowLabel: 'Total' }, { name: 'Volumen acumulado (kg)', totalsRowFunction: 'sum' }, { name: 'Participación' }], rows: districtDetail.map((row) => Object.values(row)) })
  styleTable(districts, 'TablaDistritos')
  districts.getColumn(2).numFmt = '#,##0 "kg"'
  districts.getColumn(3).numFmt = '0.0%'
  fitColumns(districts, [28, 27, 18])

  const zones = workbook.addWorksheet('Zonas priorizadas', { views: [{ showGridLines: false }] })
  applyBrandHeader(zones, 'AQPredict Residuos | Zonas priorizadas', 'Proyección operativa actual para las zonas monitoreadas')
  const priorityRows = priorities.map((item) => ({ Distrito: asText(item.distrito), Zona: asText(item.zona), 'Estimación (kg)': Number(item.cantidad_estimada_kg) || 0, Nivel: asText(item.nivel), Prioridad: asText(item.prioridad), Recomendación: asText(item.recomendacion) }))
  zones.addTable({ name: 'TablaPrioridades', ref: 'A4', headerRow: true, style: { theme: 'TableStyleMedium4', showRowStripes: true }, columns: [{ name: 'Distrito' }, { name: 'Zona' }, { name: 'Estimación (kg)' }, { name: 'Nivel' }, { name: 'Prioridad' }, { name: 'Recomendación' }], rows: priorityRows.map((row) => Object.values(row)) })
  styleTable(zones, 'TablaPrioridades')
  zones.getColumn(3).numFmt = '#,##0 "kg"'
  zones.getColumn(5).eachCell((cell, rowNumber) => { if (rowNumber > 4) { cell.font = { bold: true, color: { argb: priorityColor(cell.value) } } } })
  fitColumns(zones, [21, 25, 19, 16, 15, 48])

  const dateLabel = now.toLocaleDateString('es-PE').replaceAll('/', '-')
  saveBrowserFile(await workbook.xlsx.writeBuffer(), `AQPredict-reporte-${dateLabel}.xlsx`)
}
