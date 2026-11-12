import { useMemo, useState } from 'react'
import { IconChartLine, IconChartPie, IconChartBar, IconInfoCircle } from '@tabler/icons-react'
import { formatKg } from '../../shared/format.js'
import './interactive-charts.css'

const priorityMeta = {
  Alta: { color: '#ff766f', label: 'Atención inmediata' },
  Media: { color: '#f1bb4f', label: 'Siguiente turno' },
  Baja: { color: '#62d9a0', label: 'Seguimiento programado' },
}

export default function InteractiveCharts({ priorities, residues, onSelectZone }) {
  const [hovered, setHovered] = useState(null)
  const trend = useMemo(() => residues.slice(0, 8).reverse().map((row, index) => ({ id: `${row.Fecha}-${row.Hora}-${index}`, zone: row.Zona, amount: Number(row['Cantidad (kg)']) || 0, label: row.Hora?.slice(0, 5) || row.Fecha })), [residues])
  const maxTrend = Math.max(...trend.map((item) => item.amount), 1)
  const points = trend.map((item, index) => ({ ...item, x: trend.length === 1 ? 50 : 8 + index * 84 / (trend.length - 1), y: 87 - item.amount / maxTrend * 68 }))
  const priorityCounts = ['Alta', 'Media', 'Baja'].map((priority) => ({ priority, count: priorities.filter((item) => item.prioridad === priority).length }))
  const zoneBars = priorities.slice(0, 5)
  const maxZone = Math.max(...zoneBars.map((item) => Number(item.cantidad_estimada_kg) || 0), 1)
  const selected = hovered ? priorities.find((item) => item.zona === hovered.zone) : null

  return <section className="interactive-charts" aria-label="Análisis operativo interactivo">
    <div className="charts-heading"><div><p className="eyebrow">Análisis operativo</p><h2>Indicadores interactivos</h2><span>Pasa el cursor o selecciona una zona para explorar sus valores.</span></div><span className="charts-hint"><IconInfoCircle size={15} />Datos actualizados con el panel</span></div>
    <div className="charts-grid">
      <article className="chart-card trend-card"><div className="chart-card-head"><div><IconChartLine size={19} /><h3>Tendencia de registros</h3></div><span>Últimas mediciones</span></div>{trend.length ? <><div className="trend-visual"><svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-label="Tendencia de residuos registrados"><defs><linearGradient id="trendFill" x1="0" x2="0" y1="0" y2="1"><stop stopColor="#5bd49b" stopOpacity=".46" /><stop offset="1" stopColor="#5bd49b" stopOpacity="0" /></linearGradient></defs><path d={`M ${points.map((point) => `${point.x},${point.y}`).join(' L ')} L ${points.at(-1)?.x || 0},100 L ${points[0]?.x || 0},100 Z`} fill="url(#trendFill)" /><polyline points={points.map((point) => `${point.x},${point.y}`).join(' ')} fill="none" stroke="#b9ef81" strokeWidth="1.35" vectorEffect="non-scaling-stroke" />{points.map((point) => <circle key={point.id} cx={point.x} cy={point.y} r="2.7" className={hovered?.id === point.id ? 'is-hovered' : ''} onMouseEnter={() => setHovered(point)} onFocus={() => setHovered(point)} onClick={() => { const zone = priorities.find((item) => item.zona === point.zone); if (zone) onSelectZone(zone) }} tabIndex="0" />)}</svg>{hovered && <div className="chart-tooltip"><b>{hovered.zone}</b><span>{formatKg(hovered.amount)} kg · {hovered.label}</span></div>}</div><div className="trend-axis">{points.map((point) => <span key={point.id}>{point.label}</span>)}</div></> : <p className="chart-empty">Registra mediciones para visualizar la tendencia.</p>}</article>
      <article className="chart-card priority-card"><div className="chart-card-head"><div><IconChartPie size={19} /><h3>Prioridad operativa</h3></div><span>Zonas proyectadas</span></div><div className="priority-rings">{priorityCounts.map(({ priority, count }) => <button key={priority} type="button" className={`priority-ring ${priority.toLowerCase()}`} onClick={() => { const zone = priorities.find((item) => item.prioridad === priority); if (zone) onSelectZone(zone) }}><span style={{ '--chart-color': priorityMeta[priority].color, '--progress': `${priorities.length ? count / priorities.length * 100 : 0}%` }}><b>{count}</b></span><strong>{priority}</strong><small>{priorityMeta[priority].label}</small></button>)}</div></article>
      <article className="chart-card zone-card"><div className="chart-card-head"><div><IconChartBar size={19} /><h3>Acumulación por zona</h3></div><span>Proyección actual</span></div><div className="zone-chart">{zoneBars.map((zone) => <button type="button" className="zone-bar" key={zone.zona} onMouseEnter={() => setHovered({ zone: zone.zona, amount: zone.cantidad_estimada_kg })} onFocus={() => setHovered({ zone: zone.zona, amount: zone.cantidad_estimada_kg })} onClick={() => onSelectZone(zone)}><span><b>{zone.zona}</b><em>{formatKg(zone.cantidad_estimada_kg)} kg</em></span><i><i style={{ width: `${Number(zone.cantidad_estimada_kg) / maxZone * 100}%`, background: priorityMeta[zone.prioridad]?.color }} /></i></button>)}</div>{selected && <p className="zone-insight">Zona activa: <b>{selected.zona}</b> · prioridad {selected.prioridad?.toLowerCase()}.</p>}</article>
    </div>
  </section>
}
