import { IconBell, IconChartDots3, IconClipboardCheck, IconMapRoute, IconX } from '@tabler/icons-react'
import './activity-panel.css'

const activityDate = (row) => {
  const date = row?.Fecha
  if (!date) return null
  const time = row?.Hora || '00:00'
  const parsed = new Date(`${date}T${time}`)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

const timeAgo = (date) => {
  if (!date) return 'Actividad reciente'
  const minutes = Math.max(0, Math.round((Date.now() - date.getTime()) / 60000))
  if (minutes < 1) return 'Hace unos instantes'
  if (minutes < 60) return `Hace ${minutes} min`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `Hace ${hours} h`
  return date.toLocaleDateString('es-PE', { day: 'numeric', month: 'short' })
}

export default function ActivityPanel({ open, onClose, residues = [], predictions = [], prioritization }) {
  const activities = [
    ...residues.map((row) => ({
      id: `record-${row.Fecha}-${row.Hora}-${row.Zona}`,
      type: 'Registro de campo',
      title: `${row.Zona} · ${row.Distrito}`,
      text: `${row['Cantidad (kg)']} kg registrados para recolección.`,
      date: activityDate(row),
      icon: IconClipboardCheck,
      tone: 'record',
    })),
    ...predictions.map((row) => ({
      id: `prediction-${row.Fecha}-${row.Hora}-${row.Zona}`,
      type: 'Predicción generada',
      title: `${row.Zona} · prioridad ${String(row.Prioridad || '').toLowerCase()}`,
      text: `${row['Estimación (kg)']} kg estimados para ${row.Distrito}.`,
      date: activityDate(row),
      icon: IconChartDots3,
      tone: 'prediction',
    })),
  ].sort((first, second) => (second.date?.getTime() || 0) - (first.date?.getTime() || 0)).slice(0, 8)

  const routeActivity = prioritization?.ruta_sugerida?.zonas?.length ? {
    title: 'Ruta sugerida actualizada',
    text: `${prioritization.ruta_sugerida.zonas.length} zonas priorizadas para la próxima salida.`,
    icon: IconMapRoute,
  } : null
  const RouteIcon = routeActivity?.icon

  return <>
    <button className={`activity-scrim ${open ? 'is-open' : ''}`} aria-label="Cerrar actividades" onClick={onClose} />
    <aside className={`activity-panel ${open ? 'is-open' : ''}`} aria-hidden={!open} aria-label="Actividad reciente">
      <div className="activity-panel-head"><div><p className="eyebrow">Bitácora del sistema</p><h2>Actividad reciente</h2><span>Últimas operaciones registradas</span></div><button className="activity-close" type="button" onClick={onClose} aria-label="Cerrar panel"><IconX size={19} /></button></div>
      <div className="activity-list">
        {routeActivity && <article className="activity-item activity-route"><div className="activity-icon"><RouteIcon size={18} /></div><div><small>{routeActivity.title}</small><b>{routeActivity.text}</b><span>Estado operativo actual</span></div></article>}
        {activities.length ? activities.map((activity) => { const Icon = activity.icon; return <article className="activity-item" key={activity.id}><div className={`activity-icon ${activity.tone}`}><Icon size={18} /></div><div><small>{activity.type}</small><b>{activity.title}</b><span>{activity.text}</span><time>{timeAgo(activity.date)}</time></div></article> }) : <div className="activity-empty"><IconBell size={27} /><b>Aún no hay actividad registrada</b><span>Los nuevos registros y predicciones aparecerán aquí.</span></div>}
      </div>
    </aside>
  </>
}
