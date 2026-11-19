import { useEffect, useState } from 'react'
import { divIcon } from 'leaflet'
import { Circle, MapContainer, Marker, Polyline, TileLayer, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import './real-map.css'

const zoneCoordinates = {
  'Centro Histórico': [-16.3989, -71.5369],
  'San Lázaro': [-16.3957, -71.5298],
  'Mercado San Camilo': [-16.4042, -71.5332],
  'La Libertad': [-16.354, -71.567],
  Zamácola: [-16.3452, -71.563],
  'Ciudad Municipal': [-16.3387, -71.5593],
  'Mariscal Cáceres': [-16.431, -71.511],
  'Miguel Grau': [-16.425, -71.505],
  'Guardia Civil': [-16.4236, -71.4965],
  'La Melgar': [-16.4308, -71.5248],
  'Simón Bolívar': [-16.426, -71.5203],
  'Alto Misti': [-16.3897, -71.526],
  'Tomasa Tito Condemayta': [-16.3892, -71.52],
  Antiquilla: [-16.3903, -71.548],
  'Pampa de Camarones': [-16.3858, -71.554],
  'Buenos Aires': [-16.366, -71.545],
  'Francisco Bolognesi': [-16.3712, -71.5402],
  'Ciudad Mi Trabajo': [-16.47, -71.53],
  Lara: [-16.461, -71.535],
  Atalaya: [-16.409, -71.508],
  'Generalísimo San Martín': [-16.4037, -71.51],
  Independencia: [-16.367, -71.526],
  Apurímac: [-16.36, -71.522],
  'Andrés Avelino Cáceres': [-16.454, -71.572],
  'Tingo Grande': [-16.471, -71.559],
  Huaranguillo: [-16.429, -71.568],
  Arancota: [-16.442, -71.579],
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
