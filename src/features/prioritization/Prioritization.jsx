import { IconRefresh } from '@tabler/icons-react'
import { Chip, Empty, PageTitle } from '../../shared/ui.jsx'

const number = (value) => value == null ? 'Sin datos' : `${new Intl.NumberFormat('es-PE', { maximumFractionDigits: 2 }).format(value)} t/año`

export default function Prioritization({ prioritization, territorialPlan, loading, onRefresh }) {
  const rows = prioritization?.resultados || []
  return <>
    <PageTitle eyebrow="Decisión territorial" title="Priorización distrital" text="Orden orientativo según el percentil de generación proyectada y la presencia de áreas degradadas OEFA." action={<button className="refresh" onClick={onRefresh}><IconRefresh size={16} />{loading ? 'Actualizando...' : 'Actualizar'}</button>} />
    {prioritization?.metodologia && <p className="map-caption">{prioritization.metodologia}</p>}
    {territorialPlan?.alcance && <p className="map-caption">{territorialPlan.alcance}</p>}
    {territorialPlan?.criterio && <p className="muted">{territorialPlan.criterio}</p>}
    <div className="priority-list">
      {rows.length ? rows.map((row, index) => <article className="priority-item glass" key={row.ubigeo}>
        <span className="number">{String(index + 1).padStart(2, '0')}</span>
        <div><b>{row.distrito}</b><small>{row.provincia} · UBIGEO {row.ubigeo} · Generación proyectada: {number(row.generacion_predicha)}</small><small>Percentil: {row.percentil_generacion == null ? 'Sin datos' : `${row.percentil_generacion}%`} · Áreas OEFA: {row.areas_degradadas_oefa ?? 0}</small></div>
        <Chip priority={row.prioridad_operativa}>{row.prioridad_operativa || 'Sin datos'}</Chip>
      </article>) : <Empty text="No hay resultados de priorización disponibles." />}
    </div>
  </>
}
