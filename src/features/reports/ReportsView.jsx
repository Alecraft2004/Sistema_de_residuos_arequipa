import { useMemo, useState } from 'react'
import { IconAdjustmentsHorizontal, IconChartBar, IconDownload, IconFileSpreadsheet, IconMapPin, IconRefresh, IconScale } from '@tabler/icons-react'
import { Empty, PageTitle, PanelHeader } from '../../shared/ui.jsx'
import { formatKg } from '../../shared/format.js'
import { exportReportToExcel } from './exportReport.js'
import './reports.css'
const colors = ['#b9ef81', '#5bd49b', '#61c7d8', '#f6bc58']
const toDateInput = (value) => {
  if (!value) return ''
  if (/^\d{4}-\d{2}-\d{2}/.test(value)) return value.slice(0, 10)
  const [day, month, year] = String(value).split('/')
  return year && month && day ? `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}` : ''
}
export default function ReportsView({ summary, residues, prioritization }) {
  const [filters, setFilters] = useState({ zone: '', district: '', priority: '', from: '', to: '' })
  const priorityByZone = useMemo(() => Object.fromEntries((prioritization?.prioridades || []).map((item) => [item.zona, item.prioridad])), [prioritization])
  const zones = useMemo(() => [...new Set(residues.map((row) => row.Zona))].sort(), [residues])
  const districts = useMemo(() => [...new Set(residues.map((row) => row.Distrito))].sort(), [residues])
  const rows = residues.filter((row) => {
    const recordDate = toDateInput(row.Fecha)
    return (!filters.zone || row.Zona === filters.zone) && (!filters.district || row.Distrito === filters.district) && (!filters.priority || priorityByZone[row.Zona] === filters.priority) && (!filters.from || recordDate >= filters.from) && (!filters.to || recordDate <= filters.to)
  })
  const latest = rows.slice(0, 7).reverse()
  const maxVolume = Math.max(...latest.map((row) => Number(row['Cantidad (kg)']) || 0), 1)
  const byDistrict = Object.entries(rows.reduce((groups, row) => ({ ...groups, [row.Distrito]: (groups[row.Distrito] || 0) + (Number(row['Cantidad (kg)']) || 0) }), {})).sort(([, a], [, b]) => b - a).slice(0, 4)
  const maxDistrict = Math.max(...byDistrict.map(([, value]) => value), 1)
  const total = rows.reduce((sum, row) => sum + (Number(row['Cantidad (kg)']) || 0), 0)
  const activeFilters = Object.values(filters).filter(Boolean).length
  const resetFilters = () => setFilters({ zone: '', district: '', priority: '', from: '', to: '' })
  const filterDescription = [filters.zone && `Zona: ${filters.zone}`, filters.district && `Distrito: ${filters.district}`, filters.priority && `Prioridad: ${filters.priority}`, filters.from && `Desde: ${filters.from}`, filters.to && `Hasta: ${filters.to}`].filter(Boolean).join(' | ') || 'Sin filtros aplicados'
  const handleExport = () => exportReportToExcel({ summary: { ...summary, residuos_registrados_kg: total }, residues: rows, districtRows: byDistrict, filterDescription })

  return <>
    <PageTitle eyebrow="Seguimiento" title="Reportes" text="Analiza el volumen registrado y exporta el resultado exacto de los filtros aplicados." action={<button className="export-excel" type="button" onClick={handleExport} disabled={!rows.length}><IconFileSpreadsheet size={19} />Exportar Excel<IconDownload size={16} /></button>} />
    <section className="report-filters glass" aria-label="Filtros de reportes"><div className="filters-heading"><IconAdjustmentsHorizontal size={18} /><div><b>Filtros del reporte</b><span>{activeFilters ? `${activeFilters} filtro${activeFilters > 1 ? 's' : ''} aplicado${activeFilters > 1 ? 's' : ''}` : 'Todos los registros disponibles'}</span></div></div><div className="filters-grid"><label>Zona<select value={filters.zone} onChange={(event) => setFilters({ ...filters, zone: event.target.value })}><option value="">Todas las zonas</option>{zones.map((zone) => <option key={zone} value={zone}>{zone}</option>)}</select></label><label>Distrito<select value={filters.district} onChange={(event) => setFilters({ ...filters, district: event.target.value })}><option value="">Todos los distritos</option>{districts.map((district) => <option key={district} value={district}>{district}</option>)}</select></label><label>Prioridad actual<select value={filters.priority} onChange={(event) => setFilters({ ...filters, priority: event.target.value })}><option value="">Todas las prioridades</option><option value="Alta">Alta</option><option value="Media">Media</option><option value="Baja">Baja</option></select></label><label>Desde<input type="date" value={filters.from} onChange={(event) => setFilters({ ...filters, from: event.target.value })} /></label><label>Hasta<input type="date" value={filters.to} onChange={(event) => setFilters({ ...filters, to: event.target.value })} /></label><button className="clear-filters" type="button" onClick={resetFilters} disabled={!activeFilters}><IconRefresh size={16} />Limpiar</button></div></section>
    <div className="report-filter-note">Vista actual: <b>{filterDescription}</b></div>
    <div className="report-kpis"><article><IconScale /><span>Volumen filtrado</span><strong>{formatKg(total)} kg</strong></article><article><IconMapPin /><span>Distritos con registros</span><strong>{byDistrict.length}</strong></article><article><IconChartBar /><span>Registros analizados</span><strong>{rows.length}</strong></article></div>
    {rows.length ? <div className="reports-layout"><article className="panel glass report-volume"><PanelHeader title="Volumen por registro" text="Kilogramos de los registros seleccionados" /><div className="volume-chart">{latest.map((row, index) => { const value = Number(row['Cantidad (kg)']) || 0; return <div className="volume-column" key={`${row.Fecha}-${row.Hora}-${index}`}><span className="volume-value">{formatKg(value)}<small>kg</small></span><div className="volume-track"><div className="volume-bar" style={{ height: `${Math.max(8, value / maxVolume * 100)}%`, background: `linear-gradient(180deg,${colors[index % colors.length]},#35c28e)` }} /></div><span className="volume-label">{row.Hora?.slice(0, 5) || row.Fecha}</span></div>})}</div><div className="chart-key"><span><i />Cada barra representa una medición filtrada.</span><b>Máximo: {formatKg(maxVolume)} kg</b></div></article><article className="panel glass district-chart"><PanelHeader title="Comparación por distrito" text="Volumen acumulado según el filtro actual" /><div className="district-bars">{byDistrict.map(([district, value], index) => <div className="district-row" key={district}><div><b>{district}</b><span>{formatKg(value)} kg</span></div><div className="district-track"><i style={{ width: `${value / maxDistrict * 100}%`, background: colors[index % colors.length] }} /></div></div>)}</div></article><aside className="panel glass report-numbers"><h2>Calidad del modelo</h2><p>Indicadores del modelo predictivo actual.</p><div><small>Exactitud</small><strong>{summary?.metricas_modelo?.exactitud ?? '-'}%</strong></div><div><small>Coeficiente R²</small><strong>{summary?.metricas_modelo?.r2 ?? '-'}</strong></div><div><small>Última lectura</small><strong>{latest.at(-1)?.Fecha || '-'}</strong></div></aside></div> : <div className="panel glass"><Empty text="No hay registros que coincidan con los filtros seleccionados." /></div>}
  </>
}
