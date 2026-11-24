import { useState } from 'react'
import { IconDatabase, IconMapPin, IconRecycle, IconRefresh, IconSparkles } from '@tabler/icons-react'
import { Chip, Empty, PageTitle, PanelHeader } from '../../shared/ui.jsx'
import RealMap from './RealMap.jsx'

const number = (value) => value == null ? '-' : new Intl.NumberFormat('es-PE', { maximumFractionDigits: 2 }).format(value)
const priorityLabel = (value) => value === 'Alta' ? 'Atención prioritaria' : value === 'Media' ? 'Seguimiento' : value === 'Baja' ? 'Monitoreo' : 'Sin datos'

export default function Dashboard({ data, loading, selectedZone, setSelectedZone, onRefresh, onNavigate }) {
  const [mapMode, setMapMode] = useState('priority')
  const dashboard = data.diagnosticDashboard
  const summary = dashboard?.resumen
  const priorities = dashboard?.principales_prioridades || []
  const totalDistricts = dashboard?.total_distritos ?? summary?.total_distritos ?? 0
  const metrics = [
    ['Distritos evaluados', totalDistricts || '-', IconMapPin],
    ['Prioridad alta', dashboard?.distribucion_prioridades?.alta ?? '-', IconSparkles],
    ['Distritos con áreas OEFA', summary?.distritos_con_areas_oefa ?? '-', IconRecycle],
    ['Con predicción MINAM', summary?.distritos_con_prediccion_minam ?? '-', IconDatabase],
  ]

  return <>
    <PageTitle eyebrow="Centro de operaciones" title="Panel de control" text="Diagnóstico territorial de residuos sólidos en Arequipa" action={<button className="refresh" onClick={onRefresh} disabled={loading}><IconRefresh size={17} />{loading ? 'Actualizando...' : 'Actualizar datos'}</button>} />
    <div className="metrics">{metrics.map(([label, value, Icon]) => <article className="metric glass" key={label}><div className="metric-top"><span>{label}</span><Icon size={19} /></div><strong>{value}</strong><span className="change">Diagnóstico territorial</span></article>)}</div>
    <div className="dashboard-grid">
      <article className="panel glass">
        <PanelHeader title="Mapa de diagnóstico territorial" text="Distritos oficiales enriquecidos con predicción MINAM, valorización y registros OEFA" action={<div className="map-head-actions"><div className="map-mode-control" role="group" aria-label="Tipo de visualización del mapa"><button className={mapMode === 'priority' ? 'active' : ''} type="button" onClick={() => setMapMode('priority')}>Prioridad</button><button className={mapMode === 'generation' ? 'active heat' : ''} type="button" onClick={() => setMapMode('generation')}>Generación</button></div><button className="link-button" onClick={() => onNavigate('priorizacion')}>Ver prioridades</button></div>} />
        <RealMap geoJson={data.diagnosticMap} selectedDistrict={selectedZone} onSelect={setSelectedZone} mapMode={mapMode} />
        <div className="legend"><span className="low">Baja</span><span className="mid">Media</span><span className="high">Alta</span></div>
      </article>
      <aside className="panel glass">
        <PanelHeader title="Distritos prioritarios" text="Clasificación orientativa por generación proyectada y presencia OEFA" action={<button className="link-button" onClick={() => onNavigate('priorizacion')}>Ver todos</button>} />
        {priorities.length ? <div className="critical-list">{priorities.slice(0, 6).map((item, index) => <button className="critical" type="button" key={item.ubigeo || `${item.distrito}-${index}`} onClick={() => setSelectedZone(item)}><b className="rank">{String(index + 1).padStart(2, '0')}</b><div><b>{item.distrito}</b><small>{item.provincia}</small></div><div className="kg"><b>{number(item.generacion_predicha)} t/año</b><Chip priority={item.prioridad_operativa || item.prioridad}>
  {priorityLabel(item.prioridad_operativa || item.prioridad)}
</Chip></div></button>)}</div> : <Empty text="No hay información territorial disponible. Revisa el estado del módulo MINAM y las fuentes." />}
      </aside>
    </div>
    <p className="map-caption">La prioridad es orientativa; no representa una predicción de acumulación ni una ruta física de recolección.</p>
  </>
}
