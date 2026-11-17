import {
  classifyCameraError,
  negotiateRecorderFormat,
  stopStream,
} from './cameraCapabilities'

describe('camera capabilities', () => {
  it('selects the first supported recorder format and degrades when none match', () => {
    expect(negotiateRecorderFormat((type) => type.includes('vp8'))).toContain(
      'vp8',
    )
    expect(negotiateRecorderFormat(() => false)).toBeNull()
  })

  it.each([
    ['NotAllowedError', 'permission_denied'],
    ['SecurityError', 'permission_denied'],
    ['NotFoundError', 'device_missing'],
    ['OverconstrainedError', 'device_missing'],
    ['NotReadableError', 'device_busy'],
    ['AbortError', 'device_busy'],
    ['TypeError', 'unsupported'],
    ['OtherError', 'unknown'],
  ])('classifies %s as %s', (name, expected) => {
    expect(classifyCameraError(new DOMException('failure', name))).toBe(
      expected,
    )
  })

  it('classifies non-browser failures and stops every stream track', () => {
    expect(classifyCameraError(new Error('failure'))).toBe('unknown')
    const tracks = [{ stop: vi.fn() }, { stop: vi.fn() }]
    stopStream({ getTracks: () => tracks } as unknown as MediaStream)
    stopStream(null)
    expect(tracks.every((track) => track.stop.mock.calls.length === 1)).toBe(
      true,
    )
  })
})
