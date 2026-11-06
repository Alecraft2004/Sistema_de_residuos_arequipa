import { useEffect, useState } from 'react'
import { divIcon } from 'leaflet'
import { Circle, MapContainer, Marker, Polyline, TileLayer, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import './real-map.css'

const zoneCoordinates = {
  'Centro Histórico': [-16.3989, -71.5369],
  'La Libertad': [-16.354, -71.567],
  Zamácola: [-16.3452, -71.563],
  'Mariscal Cáceres': [-16.431, -71.511],
  'Miguel Grau': [-16.425, -71.505],
}
const baseMunicipal = [-16.3988, -71.535]
const priorityTone = (priority) => priority === 'Alta' ? 'high' : priority === 'Media' ? 'mid' : 'low'
const heatColor = (priority) => priority === 'Alta' ? '#ff766f' : priority === 'Media' ? '#f1bb4f' : '#62d9a0'
const markerIcon = (priority, active = false) => divIcon({ className: 'aq-map-marker-wrap', html: `<span class="aq-map-marker ${priorityTone(priority)} ${active ? 'is-active' : ''}"></span>`, iconSize: [30, 30], iconAnchor: [15, 30] })

function FlyToZone({ coordinates, active }) {
  const map = useMap()
  useEffect(() => {
    if (active && coordinates) map.flyTo(coordinates, 14, { animate: true, duration: .72 })
  }, [active, coordinates, map])
  return null
}

export default function RealMap({ priorities, route, selectedZone, onSelect, mapMode }) {
  const [clickedZone, setClickedZone] = useState(null)
  const routePoints = (route?.zonas || []).map((zone) => zoneCoordinates[zone.zona]).filter(Boolean)
  const activeRoute = routePoints.length ? [baseMunicipal, ...routePoints, baseMunicipal] : []
  const selectedCoordinates = zoneCoordinates[selectedZone?.zona]
  const selectZone = (zone) => { setClickedZone(zone.zona); onSelect(zone) }

  return <div className="real-map-shell">
    <MapContainer center={[-16.397, -71.535]} zoom={12} scrollWheelZoom className="real-map" aria-label="Mapa real de zonas de recolección en Arequipa">
      <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      <FlyToZone coordinates={selectedCoordinates} active={Boolean(clickedZone)} />
      {mapMode === 'route' && activeRoute.length > 1 && <Polyline positions={activeRoute} pathOptions={{ color: '#b9ef81', weight: 4, opacity: .82, dashArray: '9 8' }} />}
      {mapMode === 'heat' && priorities.filter((zone) => zoneCoordinates[zone.zona]).map((zone) => <Circle key={`heat-${zone.zona}`} center={zoneCoordinates[zone.zona]} radius={360 + Math.min(750, Number(zone.cantidad_estimada_kg || 0) * .55)} pathOptions={{ color: heatColor(zone.prioridad), fillColor: heatColor(zone.prioridad), fillOpacity: .28, opacity: .72, weight: 2 }} eventHandlers={{ click: () => selectZone(zone) }} />)}
      {priorities.filter((zone) => zoneCoordinates[zone.zona]).map((zone) => <Marker key={zone.zona} position={zoneCoordinates[zone.zona]} icon={markerIcon(zone.prioridad, selectedZone?.zona === zone.zona)} eventHandlers={{ click: () => selectZone(zone) }} />)}
      <Marker position={baseMunicipal} icon={divIcon({ className: 'aq-map-marker-wrap', html: '<span class="aq-map-base">M</span>', iconSize: [32, 32], iconAnchor: [16, 16] })} />
    </MapContainer>
    <span className="map-caption">Mapa operativo de Arequipa · OpenStreetMap</span>
    {selectedZone && <div className="map-zone-pop" key={clickedZone || selectedZone.zona}><small>Zona seleccionada</small><b>{selectedZone.zona}</b><span>{selectedZone.distrito}</span><dl><div><dt>Estimado</dt><dd>{Number(selectedZone.cantidad_estimada_kg).toLocaleString('es-PE')} kg</dd></div><div><dt>Prioridad</dt><dd>{selectedZone.prioridad}</dd></div></dl></div>}
  </div>
}
