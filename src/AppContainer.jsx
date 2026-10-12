import { useCallback, useEffect, useRef, useState } from 'react'
import { IconX } from '@tabler/icons-react'
import './styles/App.css'
import Login from './features/login/Login.jsx'
import AppSidebar from './features/layout/AppSidebar.jsx'
import Topbar from './features/layout/Topbar.jsx'
import { navItems } from './features/layout/navigation.js'
import Dashboard from './features/dashboard/Dashboard.jsx'
import ResidueForm from './features/residues/ResidueForm.jsx'
import History from './features/history/History.jsx'
import Prediction from './features/prediction/Prediction.jsx'
import Prioritization from './features/prioritization/Prioritization.jsx'
import Reports from './features/reports/ReportsView.jsx'
import Administration from './features/administration/Administration.jsx'
import { api } from './services/api.js'
import ConfirmModal from './shared/ConfirmModal.jsx'

const emptyData = { zones: [], summary: null, residues: [], prioritization: null }

export default function AppContainer() {
  const [page, setPage] = useState('inicio'), [menuOpen, setMenuOpen] = useState(false)
  const [token, setToken] = useState(() => sessionStorage.getItem('aq_token') || '')
  const [user, setUser] = useState(() => JSON.parse(sessionStorage.getItem('aq_user') || 'null'))
  const [data, setData] = useState(emptyData), [loading, setLoading] = useState(false), [error, setError] = useState(''), [selectedZone, setSelectedZone] = useState(null), [pendingAction, setPendingAction] = useState(null)
  const confirmedButton = useRef(null)
  const refreshData = useCallback(async () => {
    if (!token) return
    setLoading(true); setError('')
    try { const [zones, summary, residues, prioritization] = await Promise.all([api('/zonas', { token }), api('/reportes/resumen', { token }), api('/residuos', { token }), api('/priorizacion', { token })]); setData({ zones, summary, residues, prioritization }); setSelectedZone((current) => current || prioritization.prioridades?.[0] || null) } catch (requestError) { setError(requestError.message) } finally { setLoading(false) }
  }, [token])
  useEffect(() => { const timer = window.setTimeout(() => { void refreshData() }, 0); return () => window.clearTimeout(timer) }, [refreshData])
  const logout = () => { sessionStorage.clear(); setToken(''); setUser(null); setData(emptyData); setPage('inicio') }
  const navigate = (target) => { setPage(target); setMenuOpen(false) }
  const requestConfirmation = (event) => {
    const button = event.target.closest('button')
    if (!button || confirmedButton.current === button) { confirmedButton.current = null; return }
    if (!button.matches('.primary, .refresh, .logout, .link-button')) return
    event.preventDefault(); event.stopPropagation()
    const label = button.textContent.trim().replace(/\s+/g, ' ')
    setPendingAction({ button, label })
  }
  const confirmAction = () => { const button = pendingAction?.button; setPendingAction(null); if (button) { confirmedButton.current = button; button.click() } }
  if (!token || !user) return <Login onSubmit={async (credentials) => { const { access_token, usuario } = await api('/auth/login', { method: 'POST', body: credentials }); sessionStorage.setItem('aq_token', access_token); sessionStorage.setItem('aq_user', JSON.stringify(usuario)); setToken(access_token); setUser(usuario) }} />
  const currentLabel = navItems.find(([id]) => id === page)?.[1] || 'Panel de control'
  return <><div className="app-shell" onClickCapture={requestConfirmation}><AppSidebar items={navItems} page={page} menuOpen={menuOpen} onNavigate={navigate} user={user} onLogout={logout} />{menuOpen && <button className="sidebar-scrim" aria-label="Cerrar menú" onClick={() => setMenuOpen(false)} />}<div className="main-area"><Topbar label={currentLabel} user={user} onOpenMenu={() => setMenuOpen(true)} /><main className="content">{error && <div className="notice error"><IconX size={18} />{error}<button onClick={refreshData}>Reintentar</button></div>}{page === 'inicio' && <Dashboard data={data} loading={loading} selectedZone={selectedZone} setSelectedZone={setSelectedZone} onRefresh={refreshData} onNavigate={navigate} />}{page === 'registro' && <ResidueForm zones={data.zones} token={token} user={user} onSaved={refreshData} />}{page === 'historial' && <History rows={data.residues} />}{page === 'prediccion' && <Prediction zones={data.zones} prioritization={data.prioritization} token={token} onSaved={refreshData} />}{page === 'priorizacion' && <Prioritization prioritization={data.prioritization} loading={loading} onRefresh={refreshData} />}{page === 'reportes' && <Reports summary={data.summary} residues={data.residues} />}{page === 'administracion' && <Administration user={user} />}</main></div></div><ConfirmModal open={Boolean(pendingAction)} title={`¿${pendingAction?.label || 'Confirmar acción'}?`} message="Verifica la información antes de continuar. Esta acción se ejecutará en el sistema." confirmLabel="Sí, continuar" onConfirm={confirmAction} onClose={() => setPendingAction(null)} /></>
}
