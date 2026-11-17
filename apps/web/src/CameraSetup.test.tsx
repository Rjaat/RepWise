import axe from 'axe-core'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'

import { CameraSetup } from './CameraSetup'

function cameraStream(deviceId = 'camera-1') {
  return {
    getTracks: () => [{ stop: vi.fn() }],
    getVideoTracks: () => [{ getSettings: () => ({ deviceId }) }],
  } as unknown as MediaStream
}

describe('CameraSetup', () => {
  const originalMediaRecorder = window.MediaRecorder
  const originalMediaDevices = navigator.mediaDevices

  afterEach(() => {
    Object.defineProperty(window, 'MediaRecorder', {
      configurable: true,
      value: originalMediaRecorder,
    })
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: originalMediaDevices,
    })
  })

  it('requests camera access, negotiates recording, and switches devices', async () => {
    const getUserMedia = vi.fn().mockResolvedValue(cameraStream())
    const enumerateDevices = vi.fn().mockResolvedValue([
      { kind: 'videoinput', deviceId: 'camera-1', label: 'Rear camera' },
      { kind: 'videoinput', deviceId: 'camera-2', label: 'Front camera' },
      { kind: 'audioinput', deviceId: 'mic', label: 'Microphone' },
    ])
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: { getUserMedia, enumerateDevices },
    })
    Object.defineProperty(window, 'MediaRecorder', {
      configurable: true,
      value: { isTypeSupported: (type: string) => type.includes('vp8') },
    })
    vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue()
    const telemetry = vi.fn()
    render(<CameraSetup onTelemetry={telemetry} />)

    fireEvent.click(screen.getByRole('button', { name: 'Use camera' }))
    expect(await screen.findByText('Recording supported')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Camera'), {
      target: { value: 'camera-2' },
    })

    await waitFor(() => expect(getUserMedia).toHaveBeenCalledTimes(2))
    expect(getUserMedia.mock.calls[1][0].video.deviceId.exact).toBe('camera-2')
    expect(telemetry).toHaveBeenCalledWith(
      expect.objectContaining({ event: 'camera_ready', cameraCount: 2 }),
    )
  })

  it('explains permission recovery and unsupported browsers', async () => {
    const getUserMedia = vi
      .fn()
      .mockRejectedValue(new DOMException('denied', 'NotAllowedError'))
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: { getUserMedia },
    })
    Object.defineProperty(window, 'MediaRecorder', {
      configurable: true,
      value: function Recorder() {},
    })
    const { rerender } = render(<CameraSetup />)
    fireEvent.click(screen.getByRole('button', { name: 'Use camera' }))
    expect(
      await screen.findByText('Camera access is blocked'),
    ).toBeInTheDocument()

    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: undefined,
    })
    rerender(<CameraSetup />)
    fireEvent.click(screen.getByRole('button', { name: 'Try camera again' }))
    expect(
      await screen.findByText('Camera capture is unavailable'),
    ).toBeInTheDocument()
  })

  it('has no detectable accessibility violations', async () => {
    const { container } = render(<CameraSetup />)
    expect((await axe.run(container)).violations).toEqual([])
  })
})
