
import { useMemo, useState } from 'react'
import { IconMapPin, IconRefresh } from '@tabler/icons-react'
import RealMap from '../dashboard/RealMap.jsx'
import { Empty, PageTitle, PanelHeader, Chip } from '../../shared/ui.jsx'

const formatNumber = (value) =>
  value == null
    ? 'Sin datos'
    : new Intl.NumberFormat('es-PE', {
        maximumFractionDigits: 2,
      }).format(value)

export default function PredictionOverview({
  geoJson,
  prioritization,
  loading,
  onRefresh,
}) {
  const results = useMemo(
    () => prioritization?.resultados || [],
    [prioritization],
  )

  const [selectedDistrict, setSelectedDistrict] = useState(null)
  const [mapMode, setMapMode] = useState('priority')

  const selected = selectedDistrict || results[0] || null

  return (
    <>
      <PageTitle
        eyebrow="Inteligencia territorial"
        title="Predicción y diagnóstico territorial"
        text="Visualización de la generación proyectada y las prioridades operativas de los distritos de Arequipa."
        action={
          <button
            className="refresh"
            onClick={onRefresh}
            disabled={loading}
          >
            <IconRefresh size={17} />
            {loading ? 'Actualizando...' : 'Actualizar datos'}
          </button>
        }
      />

      <section className="panel glass">
        <PanelHeader
          title="Mapa territorial de Arequipa"
          text="Diagnóstico basado en la información territorial proporcionada por el backend."
          action={
            <div className="map-mode-control" role="group">
              <button
                type="button"
                className={mapMode === 'priority' ? 'active' : ''}
                onClick={() => setMapMode('priority')}
              >
                Prioridad
              </button>
              <button
                type="button"
                className={mapMode === 'generation' ? 'active' : ''}
                onClick={() => setMapMode('generation')}
              >
                Generación
              </button>
            </div>
          }
        />

        {geoJson?.features?.length ? (
          <RealMap
            geoJson={geoJson}
            selectedDistrict={selected}
            onSelect={setSelectedDistrict}
            mapMode={mapMode}
          />
        ) : (
          <Empty text="No hay cartografía territorial disponible." />
        )}
      </section>

      <section className="panel glass">
        <PanelHeader
          title="Distritos priorizados"
          text="Resultados devueltos por el servicio de diagnóstico territorial."
        />

        {results.length ? (
          <div className="critical-list">
            {results.map((item, index) => (
              <button
                type="button"
                className="critical"
                key={item.ubigeo || `${item.distrito}-${index}`}
                onClick={() => setSelectedDistrict(item)}
              >
                <b className="rank">
                  {String(index + 1).padStart(2, '0')}
                </b>

                <div>
                  <b>{item.distrito || 'Distrito sin nombre'}</b>
                  <small>
                    {item.provincia || 'Provincia no disponible'}
                    {' · '}
                    UBIGEO {item.ubigeo || '-'}
                  </small>
                </div>

                <div className="kg">
                  <b>
                    {formatNumber(item.generacion_predicha)} t/año
                  </b>
                  <Chip priority={item.prioridad_operativa}>
                    {item.prioridad_operativa || 'Sin prioridad'}
                  </Chip>
                </div>
              </button>
            ))}
          </div>
        ) : (
          <Empty text="No hay resultados de priorización disponibles." />
        )}
      </section>

      {selected && (
        <section className="panel glass">
          <PanelHeader
            title="Detalle del distrito seleccionado"
            text="Información disponible en el diagnóstico territorial."
          />

          <div className="minam-detail">
            <div>
              <span>Distrito</span>
              <b>{selected.distrito || '-'}</b>
            </div>
            <div>
              <small>UBIGEO</small>
              <strong>{selected.ubigeo || '-'}</strong>
            </div>
            <div>
              <small>Generación proyectada</small>
              <strong>
                {formatNumber(selected.generacion_predicha)} t/año
              </strong>
            </div>
            <div>
              <small>Áreas degradadas OEFA</small>
              <strong>
                {selected.areas_degradadas_oefa ?? 'Sin datos'}
              </strong>
            </div>
            <div>
              <small>Prioridad operativa</small>
              <strong>
                {selected.prioridad_operativa || 'Sin datos'}
              </strong>
            </div>
            <IconMapPin size={18} />
          </div>
        </section>
      )}
    </>
  )
}
