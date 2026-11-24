
import { useMemo } from 'react'
import { GeoJSON, MapContainer, TileLayer } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import './real-map.css'

const priorityColor = (priority) => {
  if (priority === 'Alta') return '#ef746d'
  if (priority === 'Media') return '#eab84d'
  if (priority === 'Baja') return '#63c99a'
  return '#9aa5ad'
}

const formatNumber = (value) =>
  value == null
    ? 'Sin datos'
    : new Intl.NumberFormat('es-PE', {
        maximumFractionDigits: 2,
      }).format(value)

export default function RealMap({
  geoJson,
  selectedDistrict,
  onSelect,
  mapMode,
}) {
  const mapData = useMemo(
    () => geoJson?.type === 'FeatureCollection' ? geoJson : null,
    [geoJson],
  )

  const styleFeature = (feature) => {
    const properties = feature?.properties || {}
    const diagnostic = properties.diagnostico || {}
    const priority =
      diagnostic.prioridad_operativa || diagnostic.prioridad

    const selected =
      String(properties.ubigeo || '') ===
      String(selectedDistrict?.ubigeo || '')

    const fillColor =
      mapMode === 'generation'
        ? diagnostic.generacion_predicha == null
          ? '#9aa5ad'
          : '#55b8a5'
        : priorityColor(priority)

    return {
      color: selected ? '#ffffff' : '#263b3b',
      weight: selected ? 2.5 : 0.8,
      opacity: 0.9,
      fillColor,
      fillOpacity: selected ? 0.78 : 0.48,
    }
  }

  const onEachFeature = (feature, layer) => {
    const properties = feature?.properties || {}
    const diagnostic = properties.diagnostico || {}

    const district = properties.distrito || 'Distrito'
    const province = properties.provincia || ''
    const ubigeo = properties.ubigeo

    const priority =
      diagnostic.prioridad_operativa ||
      diagnostic.prioridad ||
      'Sin datos'

    const generation = diagnostic.generacion_predicha

    layer.bindPopup(`
      <strong>${district}</strong><br/>
      ${province}<br/>
      UBIGEO: ${ubigeo || '-'}<br/>
      Prioridad: ${priority}<br/>
      Generación proyectada: ${
        generation == null
          ? 'Sin datos'
          : `${formatNumber(generation)} t/año`
      }
    `)

    layer.on({
      click: () => {
        if (!diagnostic) return

        onSelect?.({
          ...diagnostic,
          distrito: diagnostic.distrito || district,
          provincia: diagnostic.provincia || province,
          ubigeo: diagnostic.ubigeo || ubigeo,
        })
      },
    })
  }

  return (
    <div className="real-map-shell">
      <MapContainer
        center={[-16.4, -71.55]}
        zoom={8}
        scrollWheelZoom
        className="real-map"
        aria-label="Mapa de diagnóstico territorial de Arequipa"
      >
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {mapData && (
          <GeoJSON
            key={`${mapData.name || 'diagnostico'}-${mapData.anio_valorizacion || ''}`}
            data={mapData}
            style={styleFeature}
            onEachFeature={onEachFeature}
          />
        )}
      </MapContainer>

      <span className="map-caption">
        {mapData
          ? `${mapData.total_distritos || mapData.features.length} distritos · Diagnóstico territorial MINAM / OEFA / valorización`
          : 'Cartografía distrital no disponible'}
      </span>

      {selectedDistrict && (
        <div className="map-zone-pop" key={selectedDistrict.ubigeo}>
          <small>Distrito seleccionado</small>
          <b>{selectedDistrict.distrito || 'Sin nombre'}</b>
          <span>
            {selectedDistrict.provincia || 'Provincia no disponible'}
            {' · '}UBIGEO {selectedDistrict.ubigeo || '-'}
          </span>

          <dl>
            <div>
              <dt>Generación proyectada</dt>
              <dd>
                {selectedDistrict.generacion_predicha == null
                  ? 'Sin datos'
                  : `${formatNumber(selectedDistrict.generacion_predicha)} t/año`}
              </dd>
            </div>

            <div>
              <dt>Prioridad operativa</dt>
              <dd>
                {selectedDistrict.prioridad_operativa ||
                  selectedDistrict.prioridad ||
                  'Sin datos'}
              </dd>
            </div>

            <div>
              <dt>Áreas OEFA</dt>
              <dd>
                {selectedDistrict.areas_degradadas_oefa ?? 'Sin datos'}
              </dd>
            </div>
          </dl>
        </div>
      )}
    </div>
  )
}
