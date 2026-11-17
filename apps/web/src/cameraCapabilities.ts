export const RECORDER_FORMATS = [
  'video/webm;codecs=vp9,opus',
  'video/webm;codecs=vp8,opus',
  'video/webm',
  'video/mp4',
] as const

export type CameraFailure =
  | 'permission_denied'
  | 'device_missing'
  | 'device_busy'
  | 'unsupported'
  | 'unknown'

export function negotiateRecorderFormat(
  isSupported: (mimeType: string) => boolean,
): string | null {
  return RECORDER_FORMATS.find(isSupported) ?? null
}

export function classifyCameraError(error: unknown): CameraFailure {
  if (!(error instanceof DOMException)) return 'unknown'
  if (error.name === 'NotAllowedError' || error.name === 'SecurityError')
    return 'permission_denied'
  if (error.name === 'NotFoundError' || error.name === 'OverconstrainedError')
    return 'device_missing'
  if (error.name === 'NotReadableError' || error.name === 'AbortError')
    return 'device_busy'
  if (error.name === 'TypeError') return 'unsupported'
  return 'unknown'
}

export function stopStream(stream: MediaStream | null) {
  stream?.getTracks().forEach((track) => track.stop())
}
