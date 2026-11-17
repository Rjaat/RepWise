import axe from 'axe-core'
import { fireEvent, render, screen } from '@testing-library/react'

import { RecordingSession } from './RecordingSession'

class FakeRecorder extends EventTarget {
  static isTypeSupported = () => true
  state: RecordingState = 'inactive'
  mimeType: string

  constructor(_stream: MediaStream, options?: MediaRecorderOptions) {
    super()
    this.mimeType = options?.mimeType ?? 'video/webm'
  }

  start() {
    this.state = 'recording'
  }

  stop() {
    this.state = 'inactive'
    const data = new Event('dataavailable')
    Object.defineProperty(data, 'data', { value: new Blob(['video']) })
    this.dispatchEvent(data)
    this.dispatchEvent(new Event('stop'))
  }
}

function installCamera() {
  const track = new EventTarget() as EventTarget & MediaStreamTrack
  track.stop = vi.fn()
  const stream = {
    getTracks: () => [track],
    getVideoTracks: () => [track],
  } as unknown as MediaStream
  Object.defineProperty(navigator, 'mediaDevices', {
    configurable: true,
    value: { getUserMedia: vi.fn().mockResolvedValue(stream) },
  })
  Object.defineProperty(window, 'MediaRecorder', {
    configurable: true,
    value: FakeRecorder,
  })
  vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue()
  Object.defineProperty(URL, 'createObjectURL', {
    configurable: true,
    value: vi.fn().mockReturnValue('blob:recording'),
  })
  Object.defineProperty(URL, 'revokeObjectURL', {
    configurable: true,
    value: vi.fn(),
  })
  return track
}

describe('RecordingSession', () => {
  afterEach(() => {
    Object.defineProperty(document, 'hidden', {
      configurable: true,
      value: false,
    })
    vi.restoreAllMocks()
  })
  it('records, reviews, and hands off captured footage', async () => {
    installCamera()
    const onUse = vi.fn()
    render(<RecordingSession countdownSeconds={0} onUseRecording={onUse} />)
    fireEvent.click(screen.getByRole('button', { name: 'Start countdown' }))
    expect(
      await screen.findByRole('heading', { name: 'Recording' }),
    ).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Stop recording' }))
    expect(
      screen.getByRole('heading', { name: 'Review your set' }),
    ).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Use this recording' }))
    expect(onUse).toHaveBeenCalledWith(expect.any(File))
  })

  it('preserves footage when backgrounding or camera track loss interrupts', async () => {
    const track = installCamera()
    render(<RecordingSession countdownSeconds={0} />)
    fireEvent.click(screen.getByRole('button', { name: 'Start countdown' }))
    await screen.findByRole('heading', { name: 'Recording' })
    Object.defineProperty(document, 'hidden', {
      configurable: true,
      value: true,
    })
    document.dispatchEvent(new Event('visibilitychange'))
    expect(
      await screen.findByText(/moved to the background/i),
    ).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Record again' }))
    Object.defineProperty(document, 'hidden', {
      configurable: true,
      value: false,
    })
    fireEvent.click(screen.getByRole('button', { name: 'Start countdown' }))
    await screen.findByRole('heading', { name: 'Recording' })
    track.dispatchEvent(new Event('ended'))
    expect(
      await screen.findByText(/camera connection ended/i),
    ).toBeInTheDocument()
  })

  it('requires explicit save or discard when exiting an active recording', async () => {
    installCamera()
    render(<RecordingSession countdownSeconds={0} />)
    fireEvent.click(screen.getByRole('button', { name: 'Start countdown' }))
    await screen.findByRole('heading', { name: 'Recording' })
    fireEvent.click(screen.getByRole('button', { name: 'Exit recording' }))
    expect(
      screen.getByRole('button', { name: 'Save and review' }),
    ).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Discard recording' }))
    expect(
      screen.getByRole('heading', { name: 'Ready to record' }),
    ).toBeInTheDocument()
  })

  it('has no detectable accessibility violations', async () => {
    const { container } = render(<RecordingSession />)
    expect((await axe.run(container)).violations).toEqual([])
  })
})
