import { useCallback, useEffect, useRef, useState } from 'react'
import { IconX } from '@tabler/icons-react'
import './styles/App.css'
import Login from './features/login/Login.jsx'
import AppSidebar from './features/layout/AppSidebar.jsx'
import Topbar from './features/layout/Topbar.jsx'
import ActivityPanel from './features/layout/ActivityPanel.jsx'
import { navItems } from './features/layout/navigation.js'
import Dashboard from './features/dashboard/Dashboard.jsx'
import ResidueForm from './features/residues/ResidueForm.jsx'
import History from './features/history/History.jsx'
import PredictionOverview from './features/prediction/PredictionOverview.jsx'
import Prioritization from './features/prioritization/Prioritization.jsx'
import Reports from './features/reports/ReportsView.jsx'
import Administration from './features/administration/Administration.jsx'
import MinamKdd from './features/minam/MinamKdd.jsx'
import { api } from './services/api.js'
import ConfirmModal from './shared/ConfirmModal.jsx'

const emptyData = {
  zones: [], summary: null, residues: [], predictions: [], prioritization: null,
  diagnosticDashboard: null, diagnosticMap: null, diagnosticPrioritization: null,
  territorialPlan: null, backendStatus: null, minamModelState: null, sourceSummaries: null,
}

export default function AppContainer() {
  const [page, setPage] = useState('inicio'), [menuOpen, setMenuOpen] = useState(false)
  const [token, setToken] = useState(() => sessionStorage.getItem('aq_token') || '')
  const [user, setUser] = useState(() => JSON.parse(sessionStorage.getItem('aq_user') || 'null'))
  const [data, setData] = useState(emptyData), [loading, setLoading] = useState(false), [error, setError] = useState(''), [selectedZone, setSelectedZone] = useState(null), [pendingAction, setPendingAction] = useState(null), [activitiesOpen, setActivitiesOpen] = useState(false)
  const confirmedButton = useRef(null)

  const clearSession = useCallback(() => {
    sessionStorage.removeItem('aq_token')
    sessionStorage.removeItem('aq_user')
    setToken('')
    setUser(null)
    setData(emptyData)
    setPage('inicio')
  }, [])

  const refreshData = useCallback(async () => {
    if (!token) return
    setLoading(true)
    setError('')

    const requests = await Promise.allSettled([
      api('/zonas', { token }),
      api('/reportes/resumen', { token }),
      api('/residuos', { token }),
      api('/predicciones', { token }),
      api('/priorizacion', { token }),
      api('/diagnostico/dashboard', { token }),
      api('/diagnostico/mapa', { token }),
      api('/diagnostico/priorizacion', { token }),
      api('/diagnostico/plan-atencion', { token }),
      api('/health'),
      api('/kdd/minam/modelo/estado', { token }),
      api('/fuentes/oefa/resumen', { token }),
      api('/fuentes/valorizacion/resumen?tipo=organica&anio=2024&departamento=Arequipa', { token }),
      api('/fuentes/valorizacion/resumen?tipo=inorganica&anio=2024&departamento=Arequipa', { token }),
      api('/fuentes/rutas/resumen', { token }),
    ])

    const value = (index, fallback) => requests[index].status === 'fulfilled' ? requests[index].value : fallback
    const unauthorized = requests.some((item) => item.status === 'rejected' && item.reason?.status === 401)
    if (unauthorized) {
      clearSession()
      setError('La sesión expiró. Inicia sesión nuevamente.')
      setLoading(false)
      return
    }

    const nextData = {
      zones: value(0, []),
      summary: value(1, null),
      residues: value(2, []),
      predictions: value(3, []),
      prioritization: value(4, null),
      diagnosticDashboard: value(5, null),
      diagnosticMap: value(6, null),
      diagnosticPrioritization: value(7, null),
      territorialPlan: value(8, null),
      backendStatus: value(9, null),
      minamModelState: value(10, null),
      sourceSummaries: {
        oefa: value(11, null),
        valorizacionOrganica: value(12, null),
        valorizacionInorganica: value(13, null),
        rutas: value(14, null),
      },
    }
    setData(nextData)

    const firstPriority = nextData.diagnosticPrioritization?.resultados?.[0]
      || nextData.diagnosticDashboard?.principales_prioridades?.[0]
      || null
    setSelectedZone((current) => current || firstPriority)

    const failed = requests
      .map((item, index) => item.status === 'rejected' ? index : -1)
      .filter((index) => index >= 0)
    if (failed.length) {
      const hasDiagnosticFailure = failed.some((index) => index >= 5 && index <= 8)
      setError(hasDiagnosticFailure
        ? 'Algunos servicios territoriales no respondieron. Los módulos disponibles siguen operativos; revisa la API y los artefactos MINAM.'
        : 'Algunos módulos no pudieron actualizarse. Puedes reintentar sin perder la información que sí cargó.')
    }
    setLoading(false)
  }, [token, clearSession])

  useEffect(() => {
    const timer = window.setTimeout(() => { void refreshData() }, 0)
    return () => window.clearTimeout(timer)
  }, [refreshData])

  const logout = () => clearSession()
  const sessionExpired = () => clearSession()
  const navigate = (target) => { setPage(target); setMenuOpen(false) }
  const requestConfirmation = (event) => {
    const button = event.target.closest('button')
    if (!button || confirmedButton.current === button) { confirmedButton.current = null; return }
    if (!button.matches('.primary, .refresh, .logout, .link-button')) return
    event.preventDefault()
    event.stopPropagation()
    const label = button.textContent.trim().replace(/\s+/g, ' ')
    setPendingAction({ button, label })
  }
  const confirmAction = () => {
    const button = pendingAction?.button
    setPendingAction(null)
    if (button) { confirmedButton.current = button; button.click() }
  }

  if (!token || !user) return <Login onSubmit={async (credentials) => {
    const { access_token, usuario } = await api('/auth/login', { method: 'POST', body: credentials })
    sessionStorage.setItem('aq_token', access_token)
    sessionStorage.setItem('aq_user', JSON.stringify(usuario))
    setToken(access_token)
    setUser(usuario)
  }} />

  const currentLabel = navItems.find(([id]) => id === page)?.[1] || 'Panel de control'
  return <>
    <div className="app-shell" onClickCapture={requestConfirmation}>
      <AppSidebar items={navItems} page={page} menuOpen={menuOpen} onNavigate={navigate} user={user} onLogout={logout} />
      {menuOpen && <button className="sidebar-scrim" aria-label="Cerrar menú" onClick={() => setMenuOpen(false)} />}
      <div className="main-area">
        <Topbar label={currentLabel} user={user} onOpenMenu={() => setMenuOpen(true)} onOpenActivities={() => setActivitiesOpen(true)} activityCount={data.residues.length + data.predictions.length} />
        <main className="content">
          {error && <div className="notice error"><IconX size={18} />{error}<button onClick={refreshData}>Reintentar</button></div>}
          {page === 'inicio' && <Dashboard data={data} loading={loading} selectedZone={selectedZone} setSelectedZone={setSelectedZone} onRefresh={refreshData} onNavigate={navigate} />}
          {page === 'registro' && <ResidueForm zones={data.zones} token={token} user={user} onSaved={refreshData} />}
          {page === 'historial' && <History rows={data.residues} />}
          {page === 'prediccion' && (
  <PredictionOverview
    geoJson={data.diagnosticMap}
    prioritization={data.diagnosticPrioritization}
    loading={loading}
    onRefresh={refreshData}
  />
)}
          {page === 'priorizacion' && <Prioritization prioritization={data.diagnosticPrioritization} territorialPlan={data.territorialPlan} loading={loading} onRefresh={refreshData} />}
          {page === 'reportes' && <Reports summary={data.summary} residues={data.residues} diagnosticSummary={data.diagnosticDashboard?.resumen} diagnosticPrioritization={data.diagnosticPrioritization} sourceSummaries={data.sourceSummaries} />}
          {page === 'minam' && <MinamKdd token={token} onSessionExpired={sessionExpired} />}
          {page === 'administracion' && <Administration user={user} backendStatus={data.backendStatus} modelState={data.minamModelState} token={token} onImported={refreshData} />}
        </main>
      </div>
    </div>
    <ActivityPanel open={activitiesOpen} onClose={() => setActivitiesOpen(false)} residues={data.residues} predictions={data.predictions} prioritization={data.prioritization} />
    <ConfirmModal open={Boolean(pendingAction)} title={`¿${pendingAction?.label || 'Confirmar acción'}?`} message="Verifica la información antes de continuar. Esta acción se ejecutará en el sistema." confirmLabel="Sí, continuar" onConfirm={confirmAction} onClose={() => setPendingAction(null)} />
  </>
}
