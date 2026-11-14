const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export async function api(path, { token, method = 'GET', body } = {}) {
  let response
  try {
    response = await fetch(`${API_URL}${path}`, {
      method,
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(body ? { 'Content-Type': 'application/json' } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError('No se pudo conectar con el servidor. Verifica que el backend esté activo e intenta nuevamente.', 0)
  }
  const payload = await response.json().catch(() => ({}))
  if (response.status >= 500) throw new ApiError('El servidor presentó un problema temporal. Intenta nuevamente en unos momentos.', response.status)
  if (!response.ok) {
    const detail = Array.isArray(payload.detail)
      ? payload.detail.map((item) => item.msg || item.message).filter(Boolean).join(', ')
      : payload.detail
    throw new ApiError(detail || 'No se pudo completar la solicitud.', response.status)
  }
  return payload
}
