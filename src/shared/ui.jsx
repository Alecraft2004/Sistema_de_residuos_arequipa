import { IconLeaf } from '@tabler/icons-react'
import { priorityClass } from './format.js'
export function PageTitle({ eyebrow, title, text, action }) { return <div className="title-row"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p className="muted">{text}</p></div>{action}</div> }
export function Chip({ children, priority }) { return <span className={`chip ${priorityClass(priority)}`}>{children}</span> }
export function PanelHeader({ title, text, action }) { return <div className="panel-head"><div><h2>{title}</h2><p>{text}</p></div>{action}</div> }
export function Empty({ text }) { return <div className="empty"><IconLeaf size={34} /><b>{text}</b></div> }
export function Field({ label, required, children }) { return <label className="field"><span>{label} {required && <em>*</em>}</span>{children}</label> }
export function GuideItem({ n, title, text }) { return <div><span className="mini-orb">{n}</span><div><b>{title}</b><span>{text}</span></div></div> }
