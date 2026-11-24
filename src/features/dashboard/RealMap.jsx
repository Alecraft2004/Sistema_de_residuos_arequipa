
import { useEffect, useState } from 'react'
import { divIcon } from 'leaflet'
import L from 'leaflet'
import {
  Circle,
  GeoJSON,
  MapContainer,
  Marker,
  Polyline,
  TileLayer,
  useMap,
} from 'react-leaflet'

import { api } from '../../services/api.js'
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

const priorityTone = (priority) =>
  priority === 'Alta' ? 'high' : priority === 'Media' ? 'mid' : 'low'

const heatColor = (priority) =>
  priority === 'Alta'
    ? '#ff766f'
    : priority === 'Media'
      ? '#f1bb4f'
      : '#62d9a0'

const markerIcon = (priority, active = false) =>
  divIcon({
    className: 'aq-map-marker-wrap',
    html: `<span class="aq-map-marker ${priorityTone(priority)} ${active ? 'is-active' : ''}"></span>`,
    iconSize: [30, 30],
    iconAnchor: [15, 30],
  })

const formatNumber = (value) =>
  new Intl.NumberFormat('es-PE', {
    maximumFractionDigits: 2,
  }).format(value)

function FlyToZone({ coordinates, active }) {
  const map = useMap()

  useEffect(() => {
    if (active && coordinates) {
      map.flyTo(coordinates, 14, {
        animate: true,
        duration: 0.72,
      })
    }
  }, [active, coordinates, map])

  return null
}

function FitDistricts({ data }) {
  const map = useMap()

  useEffect(() => {
    if (!data?.features?.length) return

    const bounds = L.geoJSON(data).getBounds()

    if (bounds.isValid()) {
      map.fitBounds(bounds, {
        padding: [20, 20],
      })
    }
  }, [data, map])

  return null
}

export default function RealMap({
  token,
  priorities = [],
  route,
  selectedZone,
  onSelect,
  mapMode,
}) {
  const [clickedZone, setClickedZone] = useState(null)
  const [year, setYear] = useState(2024)
  const [geoData, setGeoData] = useState(null)
  const [loadingMinam, setLoadingMinam] = useState(false)
  const [minamError, setMinamError] = useState('')

  const routePoints = (route?.zonas || [])
    .map((zone) => zoneCoordinates[zone.zona])
    .filter(Boolean)

  const activeRoute = routePoints.length
    ? [baseMunicipal, ...routePoints, baseMunicipal]
    : []

  const selectedCoordinates = zoneCoordinates[selectedZone?.zona]

  const selectZone = (zone) => {
    setClickedZone(zone.zona)
    onSelect(zone)
  }

  // Consultar cartografía y generación histórica MINAM
  useEffect(() => {
    if (mapMode !== 'minam' || !token) return

    let active = true

    const loadMinam = async () => {
      setLoadingMinam(true)
      setMinamError('')

      try {
        const result = await api(
          `/territorio/distritos/generacion?anio=${year}&departamento=AREQUIPA`,
          { token }
        )

        if (active) {
          setGeoData(result)
        }
      } catch (error) {
        if (active) {
          setMinamError(error.message)
        }
      } finally {
        if (active) {
          setLoadingMinam(false)
        }
      }
    }

    loadMinam()

    return () => {
      active = false
    }
  }, [mapMode, token, year])

  // Escala de colores según generación real
  const values = (geoData?.features || [])
  .map((feature) => feature.properties.generacion_real)
  .filter((value) => Number.isFinite(value))
  .sort((a, b) => a - b)

const quantile = (percentage) => {
  if (!values.length) return 0

  const index = Math.floor((values.length - 1) * percentage)
  return values[index]
}

const breaks = [
  quantile(0.25),
  quantile(0.50),
  quantile(0.75),
]

const generationColor = (value) => {
  if (value == null) return '#a1a1aa'
  if (value <= breaks[0]) return '#d9f0d3'
  if (value <= breaks[1]) return '#91cf8a'
  if (value <= breaks[2]) return '#4cae50'

  return '#126b35'
}

  const districtStyle = (feature) => ({
    fillColor: generationColor(feature.properties.generacion_real),
    weight: 1,
    color: '#ffffff',
    fillOpacity: 0.75,
  })

  const districtPopup = (feature, layer) => {
    const properties = feature.properties
    layer.bindTooltip(properties.distrito, {
  sticky: true,
  direction: 'top',
})

    const generation =
      properties.generacion_real == null
        ? 'Sin información'
        : `${formatNumber(properties.generacion_real)} toneladas/año`

    layer.bindPopup(`
      <div style="min-width:180px">
        <strong>${properties.distrito}</strong><br/>
        <span>${properties.provincia}</span>
        <hr/>
        <b>Generación ${properties.anio}</b><br/>
        ${generation}
      </div>
    `)
  }

  return (
    <div className="real-map-shell">

      {mapMode === 'minam' && (
        <div className="minam-map-controls">
          <label htmlFor="minam-year">
            Año histórico:
          </label>

          <select
            id="minam-year"
            value={year}
            onChange={(event) => setYear(Number(event.target.value))}
          >
            {[2019, 2020, 2021, 2022, 2023, 2024].map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>

          <span>
            {loadingMinam
              ? 'Cargando...'
              : `${geoData?.total ?? 0} distritos`}
          </span>
        </div>
      )}

      <MapContainer
        center={[-16.397, -71.535]}
        zoom={12}
        scrollWheelZoom
        className="real-map"
        aria-label="Mapa de residuos sólidos de Arequipa"
      >
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {mapMode === 'minam' && geoData && (
          <>
            <FitDistricts data={geoData} />

            <GeoJSON
              key={`minam-${year}`}
              data={geoData}
              style={districtStyle}
              onEachFeature={districtPopup}
            />
          </>
        )}

        {mapMode !== 'minam' && (
          <>
            <FlyToZone
              coordinates={selectedCoordinates}
              active={Boolean(clickedZone)}
            />

            {mapMode === 'route' && activeRoute.length > 1 && (
              <Polyline
                positions={activeRoute}
                pathOptions={{
                  color: '#b9ef81',
                  weight: 4,
                  opacity: 0.82,
                  dashArray: '9 8',
                }}
              />
            )}

            {mapMode === 'heat' &&
              priorities
                .filter((zone) => zoneCoordinates[zone.zona])
                .map((zone) => (
                  <Circle
                    key={`heat-${zone.zona}`}
                    center={zoneCoordinates[zone.zona]}
                    radius={
                      360 +
                      Math.min(
                        750,
                        Number(zone.cantidad_estimada_kg || 0) * 0.55
                      )
                    }
                    pathOptions={{
                      color: heatColor(zone.prioridad),
                      fillColor: heatColor(zone.prioridad),
                      fillOpacity: 0.28,
                      opacity: 0.72,
                      weight: 2,
                    }}
                    eventHandlers={{
                      click: () => selectZone(zone),
                    }}
                  />
                ))}

            {priorities
              .filter((zone) => zoneCoordinates[zone.zona])
              .map((zone) => (
                <Marker
                  key={zone.zona}
                  position={zoneCoordinates[zone.zona]}
                  icon={markerIcon(
                    zone.prioridad,
                    selectedZone?.zona === zone.zona
                  )}
                  eventHandlers={{
                    click: () => selectZone(zone),
                  }}
                />
              ))}

            <Marker
              position={baseMunicipal}
              icon={divIcon({
                className: 'aq-map-marker-wrap',
                html: '<span class="aq-map-base">M</span>',
                iconSize: [32, 32],
                iconAnchor: [16, 16],
              })}
            />
          </>
        )}
      </MapContainer>

      {mapMode === 'minam' && (
        <div className="minam-map-footer">
          {loadingMinam && (
            <span>Consultando información MINAM...</span>
          )}

          {minamError && (
            <span className="minam-map-error">
              {minamError}
            </span>
          )}

          {geoData && (
            <div className="minam-map-legend">
  <span>Generación baja</span>
  <span style={{ color: '#d9f0d3' }}>■</span>

  <span>Media-baja</span>
  <span style={{ color: '#91cf8a' }}>■</span>

  <span>Media-alta</span>
  <span style={{ color: '#4cae50' }}>■</span>

  <span>Alta</span>
  <span style={{ color: '#126b35' }}>■</span>

  <span>Sin datos</span>
  <span style={{ color: '#a1a1aa' }}>■</span>
</div>
          )}
        </div>
      )}

      <span className="map-caption">
        {mapMode === 'minam'
          ? 'Generación municipal histórica · Fuente: MINAM'
          : 'Mapa operativo de Arequipa · OpenStreetMap'}
      </span>

      {mapMode !== 'minam' && selectedZone && (
        <div
          className="map-zone-pop"
          key={clickedZone || selectedZone.zona}
        >
          <small>Zona seleccionada</small>
          <b>{selectedZone.zona}</b>
          <span>{selectedZone.distrito}</span>

          <dl>
            <div>
              <dt>Estimado</dt>
              <dd>
                {Number(selectedZone.cantidad_estimada_kg).toLocaleString('es-PE')} kg
              </dd>
            </div>

            <div>
              <dt>Prioridad</dt>
              <dd>{selectedZone.prioridad}</dd>
            </div>
          </dl>
        </div>
      )}
    </div>
  )
}
