import { useCallback, useEffect, useState } from 'react'
import { IconDatabase, IconFileCheck, IconRefresh, IconUpload } from '@tabler/icons-react'
import { ApiError, api } from '../../services/api.js'

const PROFILES = [
  { value: 'MINAM_GENERACION_ANUAL', label: 'MINAM · Generación anual' },
  { value: 'OEFA_AREAS_DEGRADADAS', label: 'OEFA · Áreas degradadas' },
]

export default function ETLManager({ token, isAdmin, onImported }) {
  const [profile, setProfile] = useState(PROFILES[0].value)
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [history, setHistory] = useState([])
  const [stats, setStats] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const loadETL = useCallback(async () => {
    try {
      const [historyData, statsData] = await Promise.all([
        api('/etl/importaciones?pagina=1&tamano=8', { token }),
        api('/etl/estadisticas', { token }),
      ])
      setHistory(historyData.items || [])
      setStats(statsData)
    } catch (requestError) {
      setError(requestError.message || 'No se pudo consultar el historial ETL.')
    }
  }, [token])

  useEffect(() => {
  let cancelled = false

  const loadInitialETL = async () => {
    try {
      const [historyData, statsData] = await Promise.all([
        api('/etl/importaciones?pagina=1&tamano=8', { token }),
        api('/etl/estadisticas', { token }),
      ])

      if (cancelled) return

      setHistory(historyData.items || [])
      setStats(statsData)
    } catch (requestError) {
      if (!cancelled) {
        setError(requestError.message || 'No se pudo consultar el historial ETL.')
      }
    }
  }

  void loadInitialETL()

  return () => {
    cancelled = true
  }
}, [token])

  const sendFile = async (endpoint) => {
    if (!file) return
    const body = new FormData()
    body.append('archivo', file)
    body.append('perfil_fuente', profile)
    setBusy(true)
    setError('')
    setMessage('')
    try {
      const result = await api(endpoint, { token, method: 'POST', body })
      if (endpoint === '/etl/validar') {
        setPreview(result)
        setMessage('Validación completada. Revisa las filas válidas y rechazadas antes de importar.')
      } else {
        setPreview(null)
        setFile(null)
        setMessage(`Importación #${result.id} registrada correctamente.`)
        await loadETL()
        onImported?.()
      }
    } catch (requestError) {
      setError(requestError.message || 'No se pudo procesar el archivo.')
      if (requestError instanceof ApiError && requestError.status === 409) setPreview(null)
    } finally {
      setBusy(false)
    }
  }

  return <section className="admin-card glass etl-manager">
    <div className="etl-heading"><IconDatabase /><div><h3>Integración ETL de fuentes oficiales</h3><p>Valida los archivos antes de importarlos. La importación requiere rol Administrador.</p></div><button className="refresh" type="button" onClick={loadETL}><IconRefresh size={16} />Actualizar</button></div>
    {stats && <div className="etl-stats">
      <div><small>Importaciones</small><b>{stats.total_importaciones}</b></div>
      <div><small>Completadas</small><b>{stats.importaciones_completadas}</b></div>
      <div><small>Fallidas</small><b>{stats.importaciones_fallidas}</b></div>
      <div><small>Filas rechazadas</small><b>{stats.registros_rechazados}</b></div>
    </div>}
    {isAdmin ? <>
      <div className="etl-form">
        <label>Perfil de fuente<select value={profile} onChange={(event) => { setProfile(event.target.value); setPreview(null) }}>{PROFILES.map((item) => <option value={item.value} key={item.value}>{item.label}</option>)}</select></label>
        <label>Archivo CSV o XLSX<input type="file" accept=".csv,.xlsx" onChange={(event) => { setFile(event.target.files?.[0] || null); setPreview(null) }} /></label>
        <div className="etl-actions"><button type="button" className="secondary" disabled={!file || busy} onClick={() => sendFile('/etl/validar')}><IconFileCheck size={16} />{busy ? 'Procesando...' : 'Validar archivo'}</button><button type="button" className="primary" disabled={!file || !preview || busy || preview.filas_validas === 0} onClick={() => sendFile('/etl/importar')}><IconUpload size={16} />Importar datos</button></div>
      </div>
    </> : <p className="muted">Tu cuenta puede consultar el historial ETL, pero no ejecutar importaciones.</p>}
    {error && <p className="etl-message error">{error}</p>}
    {message && <p className="etl-message">{message}</p>}
    {preview && <div className="etl-preview">
      <b>{preview.entidad} · {preview.nombre_archivo}</b>
      <div className="etl-stats"><div><small>Total de filas</small><b>{preview.total_filas}</b></div><div><small>Válidas</small><b>{preview.filas_validas}</b></div><div><small>Rechazadas</small><b>{preview.filas_rechazadas}</b></div></div>
      {!!preview.columnas_faltantes?.length && <p>Columnas faltantes: {preview.columnas_faltantes.join(', ')}</p>}
      {!!preview.columnas_no_reconocidas?.length && <p>Columnas no reconocidas: {preview.columnas_no_reconocidas.join(', ')}</p>}
      {!!preview.muestra_rechazos?.length && <details><summary>Ver muestra de rechazos ({preview.muestra_rechazos.length})</summary>{preview.muestra_rechazos.slice(0, 5).map((row) => <p key={row.numero_fila}>Fila {row.numero_fila}: {row.motivo}</p>)}</details>}
    </div>}
    <div className="etl-history"><b>Importaciones recientes</b>{history.length ? history.map((item) => <div className="etl-history-row" key={item.id}><span>#{item.id} · {item.nombre_archivo}</span><small>{item.estado} · {item.total_filas_validas}/{item.total_filas_procesadas} válidas</small></div>) : <p className="muted">No hay importaciones registradas.</p>}</div>
  </section>
}
