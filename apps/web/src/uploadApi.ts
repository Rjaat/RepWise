const API_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8010'
const INTERNAL_USER_ID = import.meta.env.VITE_INTERNAL_USER_ID ?? ''

export interface UploadTicket {
  upload_id: string
  status: 'initiated' | 'completed' | 'cancelled'
  upload_url: string | null
  analysis_job_id: string | null
}

export interface UploadClient {
  upload(
    file: File,
    onProgress: (percent: number) => void,
    signal: AbortSignal,
  ): Promise<UploadTicket>
}

async function sha256(file: File): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', await file.arrayBuffer())
  return Array.from(new Uint8Array(digest), (byte) =>
    byte.toString(16).padStart(2, '0'),
  ).join('')
}

async function apiRequest(path: string, init: RequestInit): Promise<Response> {
  if (!INTERNAL_USER_ID)
    throw new Error('Upload identity is not configured for this environment.')
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { Authorization: `Bearer ${INTERNAL_USER_ID}`, ...init.headers },
  })
  if (!response.ok) {
    const body = (await response.json()) as { message?: string }
    throw new Error(body.message ?? 'The upload request failed.')
  }
  return response
}

function putFile(
  url: string,
  file: File,
  onProgress: (percent: number) => void,
  signal: AbortSignal,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest()
    request.open('PUT', url)
    request.setRequestHeader('Content-Type', file.type)
    request.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable)
        onProgress(Math.round((event.loaded / event.total) * 100))
    })
    request.addEventListener('load', () => {
      if (request.status >= 200 && request.status < 300) resolve()
      else reject(new Error('Storage rejected the video upload.'))
    })
    request.addEventListener('error', () =>
      reject(new Error('The connection was interrupted during upload.')),
    )
    request.addEventListener('abort', () =>
      reject(new DOMException('Cancelled', 'AbortError')),
    )
    signal.addEventListener('abort', () => request.abort(), { once: true })
    request.send(file)
  })
}

export const browserUploadClient: UploadClient = {
  async upload(file, onProgress, signal) {
    const checksum = await sha256(file)
    const initiated = await apiRequest('/v1/uploads', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Idempotency-Key': crypto.randomUUID(),
      },
      body: JSON.stringify({
        filename: file.name,
        content_type: file.type,
        size_bytes: file.size,
        sha256: checksum,
      }),
      signal,
    })
    const ticket = (await initiated.json()) as UploadTicket
    if (!ticket.upload_url) throw new Error('The upload URL is unavailable.')
    try {
      await putFile(ticket.upload_url, file, onProgress, signal)
      const completed = await apiRequest(
        `/v1/uploads/${ticket.upload_id}/complete`,
        { method: 'POST', signal },
      )
      return (await completed.json()) as UploadTicket
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        try {
          await apiRequest(`/v1/uploads/${ticket.upload_id}`, {
            method: 'DELETE',
          })
        } catch {
          // Cancellation remains recoverable; server cleanup can retry separately.
        }
      }
      throw error
    }
  },
}
