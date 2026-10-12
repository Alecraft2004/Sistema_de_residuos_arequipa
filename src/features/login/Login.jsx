import { useRef, useState } from 'react'
import { IconChevronRight, IconMapPin, IconRecycle, IconSparkles } from '@tabler/icons-react'
import './styles/leaves.css'
import './styles/login-background.css'
import './styles/login-typography.css'
import './styles/login-redesign.css'

const leafTiming = [[-9.6, 8.2], [-3.4, 7.1], [-12.8, 9.4], [-6.7, 6.8], [-15.1, 8.9], [-1.9, 7.7], [-11.2, 6.5], [-5.5, 9.1], [-14.4, 7.2], [-8.3, 8.6], [-16.7, 6.9], [-4.1, 9.7], [-13.5, 7.5], [-7.8, 8.1]]

export default function Login({ onSubmit }) {
  const [usuario, setUsuario] = useState(''), [clave, setClave] = useState(''), [error, setError] = useState(''), [busy, setBusy] = useState(false), leavesRef = useRef(null)
  const submit = async (event) => { event.preventDefault(); setBusy(true); setError(''); try { await onSubmit({ usuario, clave }) } catch (loginError) { setError(loginError.message) } finally { setBusy(false) } }
  const resetLeaves = () => leavesRef.current?.querySelectorAll('.leaf-sway').forEach((leaf) => { leaf.style.setProperty('--push-x', '0px'); leaf.style.setProperty('--push-y', '0px'); leaf.style.setProperty('--turn', '0deg') })
  const sweepLeaves = (event) => {
    if (event.target.closest('.login-surface')) { resetLeaves(); return }
    leavesRef.current?.querySelectorAll('.leaf-sway').forEach((leaf) => {
      const box = leaf.parentElement.getBoundingClientRect(), x = box.left + box.width / 2, y = box.top + box.height / 2, dx = x - event.clientX, dy = y - event.clientY, distance = Math.hypot(dx, dy), range = 210
      if (distance >= range) { leaf.style.setProperty('--push-x', '0px'); leaf.style.setProperty('--push-y', '0px'); leaf.style.setProperty('--turn', '0deg'); return }
      const strength = (1 - distance / range) * 48, angle = Math.atan2(dy, dx)
      leaf.style.setProperty('--push-x', `${Math.cos(angle) * strength}px`); leaf.style.setProperty('--push-y', `${Math.sin(angle) * strength * .45}px`); leaf.style.setProperty('--turn', `${(event.clientX - x) * .22}deg`)
    })
  }
  return <main className="login-shell" onPointerMove={sweepLeaves} onPointerLeave={resetLeaves}>
    <div className="falling-leaves" ref={leavesRef} aria-hidden="true">{leafTiming.map(([delay, duration], leaf) => <span className={`leaf-particle leaf-${leaf}`} style={{ animationDelay: `${delay}s`, animationDuration: `${duration}s` }} key={leaf}><span className="leaf-sway"><img src="/assets/falling-leaf.png" className="falling-leaf" alt="" /></span></span>)}</div>
    <section className="login-surface glass">
      <aside className="login-intro">
        <div className="intro-brand"><img className="login-brand-mark" src="/assets/aqpredict-logo-mint.png" alt="AQPredict Residuos" /><span>AQPredict<br />Residuos</span></div>
        <div className="intro-copy"><p className="eyebrow">Centro de operaciones</p><h1>La ciudad avisa antes de desbordarse.</h1><p>Anticipa zonas críticas y convierte datos de campo en rutas de recolección más oportunas.</p></div>
        <div className="access-points"><span><IconRecycle size={18} />Registro</span><span><IconSparkles size={18} />Predicción</span><span><IconMapPin size={18} />Ruta</span></div>
      </aside>
      <form className="login-card" onSubmit={submit}>
        <div className="login-status"><i /><span>Sistema disponible</span></div>
        <p className="eyebrow">Acceso de operación</p><h2>Iniciar sesión</h2><p className="muted">Continúa con tus credenciales.</p>
        <label>Usuario<input value={usuario} onChange={(event) => setUsuario(event.target.value)} autoComplete="username" required /></label>
        <label>Contraseña<input type="password" value={clave} onChange={(event) => setClave(event.target.value)} autoComplete="current-password" required /></label>
        {error && <p className="form-error">{error}</p>}
        <button className="primary wide" disabled={busy}>{busy ? 'Ingresando...' : 'Entrar al centro'}<IconChevronRight size={18} /></button>
      </form>
    </section>
  </main>
}
