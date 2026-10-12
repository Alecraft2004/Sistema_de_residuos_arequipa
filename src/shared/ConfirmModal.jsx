import { IconAlertTriangle, IconCheck, IconX } from '@tabler/icons-react'
import '../styles/modal.css'

export default function ConfirmModal({ open, title = '¿Confirmar acción?', message, confirmLabel = 'Confirmar', busy = false, onConfirm, onClose }) {
  if (!open) return null
  return <div className="modal-backdrop" role="presentation"><section className="confirm-modal glass" role="dialog" aria-modal="true" aria-labelledby="confirm-title"><button className="modal-close" type="button" onClick={onClose} disabled={busy} aria-label="Cerrar"><IconX size={19} /></button><div className="modal-icon"><IconAlertTriangle size={24} /></div><p className="eyebrow">Confirmación requerida</p><h2 id="confirm-title">{title}</h2><p>{message}</p><div className="modal-actions"><button className="modal-cancel" type="button" onClick={onClose} disabled={busy}>Cancelar</button><button className="primary" type="button" onClick={onConfirm} disabled={busy}>{busy ? 'Procesando...' : confirmLabel}<IconCheck size={17} /></button></div></section></div>
}
