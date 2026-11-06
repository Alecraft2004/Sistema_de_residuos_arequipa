import * as XLSX from 'xlsx'

const cleanValue = (value) => value ?? '-'

export function exportReportToExcel({ summary, residues, districtRows, filterDescription = 'Sin filtros aplicados' }) {
  const total = summary?.residuos_registrados_kg || 0
  const now = new Date()
  const dateLabel = now.toLocaleDateString('es-PE').replaceAll('/', '-')

  const summaryRows = [
    ['Reporte AQPredict Residuos', ''],
    ['Generado el', now.toLocaleString('es-PE')],
    ['Filtros aplicados', filterDescription],
    [],
    ['Indicador', 'Valor'],
    ['Volumen acumulado (kg)', total],
    ['Distritos con registros', districtRows.length],
    ['Registros analizados', residues.length],
    ['Exactitud del modelo (%)', cleanValue(summary?.metricas_modelo?.exactitud)],
    ['Coeficiente R²', cleanValue(summary?.metricas_modelo?.r2)],
  ]

  const districts = districtRows.map(([district, amount]) => ({
    Distrito: district,
    'Volumen acumulado (kg)': amount,
  }))

  const workbook = XLSX.utils.book_new()
  const summarySheet = XLSX.utils.aoa_to_sheet(summaryRows)
  const registersSheet = XLSX.utils.json_to_sheet(residues)
  const districtsSheet = XLSX.utils.json_to_sheet(districts)

  summarySheet['!cols'] = [{ wch: 31 }, { wch: 24 }]
  registersSheet['!cols'] = Object.keys(residues[0] || {}).map((key) => ({ wch: Math.max(key.length + 3, 18) }))
  districtsSheet['!cols'] = [{ wch: 25 }, { wch: 28 }]

  XLSX.utils.book_append_sheet(workbook, summarySheet, 'Resumen')
  XLSX.utils.book_append_sheet(workbook, registersSheet, 'Registros')
  XLSX.utils.book_append_sheet(workbook, districtsSheet, 'Por distrito')
  XLSX.writeFile(workbook, `AQPredict-reporte-${dateLabel}.xlsx`)
}
