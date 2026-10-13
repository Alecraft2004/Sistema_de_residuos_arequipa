const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

export async function api(path, { token, method = 'GET', body } = {}) {
  let response
  try {
    response = await fetch(`${API_URL}${path}`, { method, headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(body ? { 'Content-Type': 'application/json' } : {}) }, body: body ? JSON.stringify(body) : undefined })
  } catch {
    throw new Error('No se pudo conectar con el servidor. Verifica que el backend esté activo e intenta nuevamente.')
  }
  const payload = await response.json().catch(() => ({}))
  if (response.status >= 500) throw new Error('El servidor presentó un problema temporal. Intenta nuevamente en unos momentos.')
  if (!response.ok) throw new Error(payload.detail || 'No se pudo completar la solicitud.')
  return payload
}
