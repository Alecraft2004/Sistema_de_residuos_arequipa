import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { IconAlertTriangle, IconChartBar, IconCheck, IconDatabase, IconMapPin, IconRefresh, IconSearch, IconServer } from '@tabler/icons-react'
import { ApiError, api } from '../../services/api.js'
import { Empty, PageTitle, PanelHeader } from '../../shared/ui.jsx'
import './minam.css'

const INITIAL_FILTERS = { departamento: '', provincia: '', distrito: '' }
const formatNumber = (value) => typeof value === 'number' ? new Intl.NumberFormat('es-PE', { maximumFractionDigits: 2 }).format(value) : value ?? '-'
const isObject = (value) => value && typeof value === 'object' && !Array.isArray(value)

function ApiState({ state, onRetry }) {
  if (state.kind === 'loading') return <div className="minam-state"><IconRefresh className="spin" size={20} />Cargando información del modelo...</div>
  if (state.kind === 'auth') return <div className="minam-state minam-state-error"><IconAlertTriangle size={20} />{state.message}</div>
  if (state.kind === 'error') return <div className="minam-state minam-state-error"><IconAlertTriangle size={20} /><span>{state.message}</span>{onRetry && <button className="minam-button secondary" onClick={onRetry}>Reintentar</button>}</div>
  return null
}

function MetricObject({ title, value }) {
  return <article className="minam-metric-block"><h3>{title}</h3><MetricValue value={value} /></article>
}

function MetricValue({ value }) {
  if (Array.isArray(value)) return <div className="minam-metric-list">{value.map((item, index) => <div className="minam-metric-entry" key={index}><MetricValue value={item} /></div>)}</div>
  if (isObject(value)) return <div className="minam-metric-fields">{Object.entries(value).map(([key, item]) => <div className="minam-metric-row" key={key}><span>{key.replaceAll('_', ' ')}</span><MetricValue value={item} /></div>)}</div>
  return <b>{formatNumber(value)}</b>
}

function SummaryCard({ icon: Icon, label, value, tone = '' }) {
  return <article className={`minam-summary-card ${tone}`}><Icon size={20} /><span>{label}</span><strong>{value ?? '-'}</strong></article>
}

export default function MinamKdd({ token, onSessionExpired }) {
  const [modelState, setModelState] = useState({ kind: 'loading' })
  const [metrics, setMetrics] = useState(null)
  const [predictions, setPredictions] = useState([])
  const [arequipa, setArequipa] = useState([])
  const [evaluation, setEvaluation] = useState([])
  const [filters, setFilters] = useState(INITIAL_FILTERS)
  const [ubigeo, setUbigeo] = useState('')
  const [ubigeoResult, setUbigeoResult] = useState(null)
  const [loadError, setLoadError] = useState('')
  const [loadingPredictions, setLoadingPredictions] = useState(false)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const predictionsRequest = useRef(0)

  const handleError = useCallback((error) => {
    if (error instanceof ApiError && error.status === 401) {
      onSessionExpired()
      return 'Sesión expirada. Vuelve a iniciar sesión para consultar el módulo MINAM.'
    }
    return error.message || 'No se pudo consultar el módulo MINAM.'
  }, [onSessionExpired])

  const loadBaseData = useCallback(async () => {
    setModelState({ kind: 'loading' })
    setLoadError('')
    try {
      const state = await api('/kdd/minam/modelo/estado', { token })
      setModelState({ kind: state.disponible === false ? 'unavailable' : 'ready', data: state })
      if (state.disponible === false) {
        setMetrics(null)
        setArequipa([])
        setEvaluation([])
        setPredictions([])
        return
      }
      const [metricData, arequipaData, evaluationData] = await Promise.all([
        api('/kdd/minam/modelo/metricas', { token }),
        api('/kdd/minam/predicciones/arequipa', { token }),
        api('/kdd/minam/evaluacion/2024', { token }),
      ])
      setMetrics(metricData)
      setArequipa(Array.isArray(arequipaData) ? arequipaData : [])
      setEvaluation(Array.isArray(evaluationData) ? evaluationData : [])
    } catch (error) {
      const message = handleError(error)
      setModelState({ kind: 'error' })
      setLoadError(message)
    }
  }, [handleError, token])

  const loadPredictions = useCallback(async () => {
    const requestId = predictionsRequest.current + 1
    predictionsRequest.current = requestId
    setLoadingPredictions(true)
    try {
      const params = new URLSearchParams(Object.entries(filters).filter(([, value]) => value))
      const result = await api(`/kdd/minam/predicciones${params.toString() ? `?${params}` : ''}`, { token })
      if (requestId !== predictionsRequest.current) return
      setPredictions(Array.isArray(result) ? result : [])
    } catch (error) {
      if (requestId !== predictionsRequest.current) return
      setLoadError(handleError(error))
      setPredictions([])
    } finally {
      if (requestId === predictionsRequest.current) setLoadingPredictions(false)
    }
  }, [filters, handleError, token])

  useEffect(() => {
    const timer = window.setTimeout(() => { void loadBaseData() }, 0)
    return () => window.clearTimeout(timer)
  }, [loadBaseData])
  useEffect(() => {
    const timer = window.setTimeout(() => { void loadPredictions() }, 0)
    return () => window.clearTimeout(timer)
  }, [loadPredictions])

  const departments = useMemo(() => [...new Set(predictions.map((item) => item.departamento).filter(Boolean))].sort(), [predictions])
  const provinces = useMemo(() => [...new Set(predictions.filter((item) => !filters.departamento || item.departamento === filters.departamento).map((item) => item.provincia).filter(Boolean))].sort(), [filters.departamento, predictions])
  const districts = useMemo(() => [...new Set(predictions.filter((item) => (!filters.departamento || item.departamento === filters.departamento) && (!filters.provincia || item.provincia === filters.provincia)).map((item) => item.distrito).filter(Boolean))].sort(), [filters.departamento, filters.provincia, predictions])
  const statusData = modelState.data

  const updateFilter = (key, value) => {
    setFilters((current) => ({ ...current, [key]: value, ...(key === 'departamento' ? { provincia: '', distrito: '' } : {}), ...(key === 'provincia' ? { distrito: '' } : {}) }))
  }
  const searchUbigeo = async (event) => {
    event.preventDefault()
    const value = ubigeo.trim()
    if (!value) return
    setLoadingDetail(true); setUbigeoResult(null); setLoadError('')
    try {
      setUbigeoResult(await api(`/kdd/minam/predicciones/${encodeURIComponent(value)}`, { token }))
    } catch (error) {
      setLoadError(handleError(error))
    } finally {
      setLoadingDetail(false)
    }
  }

  return <>
    <PageTitle eyebrow="Inteligencia de datos" title="KDD / ML MINAM" text={statusData?.metodologia || "Consulta el modelo predictivo MINAM y su evaluación histórica."} action={<button className="refresh" onClick={loadBaseData}><IconRefresh size={17} />Actualizar módulo</button>} />
    {loadError && <div className="notice error"><IconAlertTriangle size={18} />{loadError}<button onClick={() => setLoadError('')}>Cerrar</button></div>}
    {modelState.kind === 'loading' && <ApiState state={modelState} />}
    {modelState.kind === 'error' && <ApiState state={{ kind: 'error', message: loadError || 'El modelo no está disponible.' }} onRetry={loadBaseData} />}
    {modelState.kind === 'unavailable' && <div className="minam-unavailable"><IconAlertTriangle size={21} /><div><b>Modelo no disponible</b><span>{statusData?.mensaje || 'El backend no reporta un modelo disponible.'}</span></div></div>}
    {modelState.kind !== 'loading' && modelState.kind !== 'error' && <main className="minam-page">
      <section className="minam-summary">
        <SummaryCard icon={IconServer} label="Estado" value={statusData?.disponible ? 'Disponible' : 'No disponible'} tone={statusData?.disponible ? 'success' : 'warning'} />
        <SummaryCard icon={IconDatabase} label="Modelo" value={statusData?.nombre_modelo} />
        <SummaryCard icon={IconChartBar} label="Año histórico" value={statusData?.ultimo_anio_historico} />
        <SummaryCard icon={IconMapPin} label="Año de predicción" value={statusData?.proximo_anio_prediccion} tone="future" />
      </section>
      <section className="minam-model-note glass"><IconCheck size={18} /><div><b>Metodología: {statusData?.metodologia || '-'}</b><span>La predicción futura utiliza el valor real de generación municipal del último año histórico; no representa aprendizaje de tendencias.</span></div></section>
      <div className="minam-grid">
        <section className="panel glass"><PanelHeader title="Métricas de evaluación" text="Resultados reportados por el backend para 2024." /><div className="minam-metrics">{metrics ? Object.entries(metrics).map(([key, value]) => <MetricObject key={key} title={key.replaceAll('_', ' ')} value={value} />) : <Empty text="No hay métricas disponibles." />}</div></section>
        <section className="panel glass"><PanelHeader title="Predicción por UBIGEO" text="Consulta el detalle territorial de un código." /><form className="minam-ubigeo-form" onSubmit={searchUbigeo}><input value={ubigeo} onChange={(event) => setUbigeo(event.target.value)} placeholder="Ingrese UBIGEO" aria-label="UBIGEO" /><button className="minam-button minam-submit" disabled={loadingDetail || !ubigeo.trim()}><IconSearch size={17} />{loadingDetail ? 'Consultando...' : 'Consultar'}</button></form>{ubigeoResult ? <PredictionCard item={ubigeoResult} /> : <p className="minam-hint">La consulta mostrará generación real, predicción y metodología.</p>}</section>
      </div>
      <section className="panel glass"><PanelHeader title="Predicciones nacionales" text="Predicción futura 2025 por departamento, provincia y distrito." action={loadingPredictions && <span className="minam-loading">Actualizando...</span>} /><div className="minam-filters"><label>Departamento<select value={filters.departamento} onChange={(event) => updateFilter('departamento', event.target.value)}><option value="">Todos</option>{departments.map((item) => <option key={item}>{item}</option>)}</select></label><label>Provincia<select value={filters.provincia} onChange={(event) => updateFilter('provincia', event.target.value)}><option value="">Todas</option>{provinces.map((item) => <option key={item}>{item}</option>)}</select></label><label>Distrito<select value={filters.distrito} onChange={(event) => updateFilter('distrito', event.target.value)}><option value="">Todos</option>{districts.map((item) => <option key={item}>{item}</option>)}</select></label></div><PredictionTable rows={predictions} empty="No hay predicciones para los filtros seleccionados." /></section>
      <section className="panel glass"><PanelHeader title="Indicadores de Arequipa" text="Predicciones territoriales devueltas por el endpoint específico." /><PredictionTable rows={arequipa} empty="No hay datos de Arequipa disponibles." /></section>
      <section className="panel glass"><PanelHeader title="Evaluación histórica 2024" text="Resultados históricos, separados de la predicción futura." /><EvaluationTable rows={evaluation} /></section>
    </main>}
  </>
}

function PredictionCard({ item }) {
  return <div className="minam-detail"><div><span>{item.departamento} / {item.provincia} / {item.distrito}</span><b>UBIGEO {item.ubigeo}</b></div><div><small>Generación real {item.anio_historico}</small><strong>{formatNumber(item.generacion_real_ultimo_anio)}</strong></div><div><small>Predicción {item.anio_objetivo}</small><strong>{formatNumber(item.generacion_predicha)}</strong></div><small>{item.tipo_modelo} · {item.metodologia}</small></div>
}

function PredictionTable({ rows, empty }) {
  if (!rows.length) return <Empty text={empty} />
  return <div className="minam-table-wrap"><table className="data-table minam-table"><thead><tr><th>UBIGEO</th><th>Departamento</th><th>Provincia</th><th>Distrito</th><th>Año histórico</th><th>Año objetivo</th><th>Generación real</th><th>Predicción</th></tr></thead><tbody>{rows.map((item) => <tr key={`${item.ubigeo}-${item.anio_objetivo}`}><td>{item.ubigeo}</td><td>{item.departamento}</td><td>{item.provincia}</td><td>{item.distrito}</td><td>{item.anio_historico}</td><td>{item.anio_objetivo}</td><td>{formatNumber(item.generacion_real_ultimo_anio)}</td><td><b>{formatNumber(item.generacion_predicha)}</b></td></tr>)}</tbody></table></div>
}

function EvaluationTable({ rows }) {
  if (!rows.length) return <Empty text="No hay evaluación histórica disponible." />
  return <div className="minam-table-wrap"><table className="data-table minam-table"><thead><tr><th>UBIGEO</th><th>Departamento</th><th>Provincia</th><th>Distrito</th><th>Año</th><th>Generación real</th><th>Predicción</th><th>Error absoluto</th><th>Error %</th><th>Resultado</th></tr></thead><tbody>{rows.map((item) => <tr key={`${item.ubigeo}-${item.anio_objetivo}`}><td>{item.ubigeo}</td><td>{item.departamento}</td><td>{item.provincia}</td><td>{item.distrito}</td><td>{item.anio_objetivo}</td><td>{formatNumber(item.generacion_real)}</td><td>{formatNumber(item.generacion_predicha)}</td><td>{formatNumber(item.error_absoluto)}</td><td>{formatNumber(item.error_porcentual)}</td><td>{item.resultado || '-'}</td></tr>)}</tbody></table></div>
}
