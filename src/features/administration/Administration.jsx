import { IconLeaf, IconLock, IconServer } from '@tabler/icons-react'
import ETLManager from './ETLManager.jsx'
import { Chip, PageTitle } from '../../shared/ui.jsx'

export default function Administration({ user, backendStatus, modelState, token, onImported }) {
  const apiReady = backendStatus?.estado === 'ok'
  const modelReady = modelState?.disponible === true
  return <>
    <PageTitle eyebrow="Configuración" title="Administración" text="Consulta la sesión y el estado reportado por los servicios del backend." />
    <div className="admin-grid">
      <article className="admin-card glass"><IconLock /><h3>Sesión actual</h3><p>Usuario autenticado en la plataforma.</p><div className="role"><span>Cuenta</span><b>{user?.usuario || '-'}</b></div><div className="role"><span>Rol</span><b>{user?.rol || '-'}</b></div></article>
      <article className="admin-card glass"><IconServer /><h3>Estado de API</h3><p>Disponibilidad del endpoint de salud del backend.</p><div className="role"><span>API REST</span><Chip priority={apiReady ? 'Baja' : 'Alta'}>{apiReady ? 'Disponible' : 'No verificada'}</Chip></div><div className="role"><span>Respuesta</span><b>{backendStatus?.servicio || backendStatus?.estado || 'Sin respuesta'}</b></div></article>
      <article className="admin-card glass"><IconLeaf /><h3>Modelo MINAM</h3><p>Estado real informado por el servicio de predicción.</p><div className="role"><span>Modelo</span><b>{modelState?.nombre_modelo || 'No disponible'}</b></div><div className="role"><span>Estado</span><Chip priority={modelReady ? 'Baja' : 'Alta'}>{modelReady ? 'Disponible' : 'No disponible'}</Chip></div><div className="role"><span>Próximo año</span><b>{modelState?.proximo_anio_prediccion ?? '-'}</b></div></article>
    </div>
    <ETLManager token={token} isAdmin={user?.rol === 'Administrador'} onImported={onImported} />
  </>
}
