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
  const isFormData = typeof FormData !== 'undefined' && body instanceof FormData
  try {
    response = await fetch(`${API_URL}${path}`, {
      method,
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(body && !isFormData ? { 'Content-Type': 'application/json' } : {}),
      },
      body: body ? (isFormData ? body : JSON.stringify(body)) : undefined,
    })
  } catch {
    throw new ApiError('No se pudo conectar con el servidor. Verifica que el backend esté activo e intenta nuevamente.', 0)
  }
  const contentType = response.headers.get('content-type') || ''
  const payload = contentType.includes('application/json')
    ? await response.json().catch(() => ({}))
    : await response.text().catch(() => '')
  if (response.status >= 500) throw new ApiError('El servidor presentó un problema temporal. Intenta nuevamente en unos momentos.', response.status)
  if (!response.ok) {
    const rawDetail = payload && typeof payload === 'object' ? payload.detail : payload
    const detail = Array.isArray(rawDetail)
      ? rawDetail.map((item) => item.msg || item.message).filter(Boolean).join(', ')
      : rawDetail
    throw new ApiError(detail || 'No se pudo completar la solicitud.', response.status)
  }
  return payload
}
