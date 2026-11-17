import { fireEvent, render, screen } from '@testing-library/react'

import { GuidedCaptureJourney } from './GuidedCaptureJourney'

class JourneyRecorder extends EventTarget {
  static isTypeSupported = () => true
  state: RecordingState = 'inactive'
  mimeType = 'video/webm'

  start() {
    this.state = 'recording'
  }

  stop() {
    this.state = 'inactive'
    const event = new Event('dataavailable')
    Object.defineProperty(event, 'data', { value: new Blob(['journey']) })
    this.dispatchEvent(event)
    this.dispatchEvent(new Event('stop'))
  }
}

function installJourneyCamera() {
  const createStream = () => {
    const track = new EventTarget() as EventTarget & MediaStreamTrack
    track.stop = vi.fn()
    track.getSettings = () => ({ deviceId: 'camera-1' })
    return {
      getTracks: () => [track],
      getVideoTracks: () => [track],
    } as unknown as MediaStream
  }
  Object.defineProperty(navigator, 'mediaDevices', {
    configurable: true,
    value: {
      getUserMedia: vi.fn().mockImplementation(async () => createStream()),
      enumerateDevices: vi.fn().mockResolvedValue([]),
    },
  })
  Object.defineProperty(window, 'MediaRecorder', {
    configurable: true,
    value: JourneyRecorder,
  })
  Object.defineProperty(URL, 'createObjectURL', {
    configurable: true,
    value: vi.fn().mockReturnValue('blob:journey'),
  })
  Object.defineProperty(URL, 'revokeObjectURL', {
    configurable: true,
    value: vi.fn(),
  })
  vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue()
}

async function completePractice() {
  fireEvent.click(screen.getByRole('button', { name: 'Use camera' }))
  fireEvent.click(
    await screen.findByRole('button', { name: 'Try one practice rep' }),
  )
  fireEvent.click(screen.getByRole('button', { name: 'Finish practice rep' }))
  expect(
    await screen.findByRole('heading', { name: 'Record your set' }),
  ).toBeInTheDocument()
}

describe('GuidedCaptureJourney', () => {
  afterEach(() => {
    Object.defineProperty(document, 'hidden', {
      configurable: true,
      value: false,
    })
    vi.restoreAllMocks()
  })

  it('moves through setup, excluded practice, recording, and report', async () => {
    installJourneyCamera()
    render(<GuidedCaptureJourney countdownSeconds={0} />)
    await completePractice()
    fireEvent.click(screen.getByRole('button', { name: 'Start countdown' }))
    await screen.findByRole('heading', { name: 'Recording' })
    fireEvent.click(screen.getByRole('button', { name: 'Stop recording' }))
    fireEvent.click(screen.getByRole('button', { name: 'Use this recording' }))
    expect(
      await screen.findByRole('heading', { name: 'Bodyweight squat report' }),
    ).toBeInTheDocument()
  })

  it('continues to the report with explicitly recovered footage', async () => {
    installJourneyCamera()
    render(<GuidedCaptureJourney countdownSeconds={0} />)
    await completePractice()
    fireEvent.click(screen.getByRole('button', { name: 'Start countdown' }))
    await screen.findByRole('heading', { name: 'Recording' })
    Object.defineProperty(document, 'hidden', {
      configurable: true,
      value: true,
    })
    document.dispatchEvent(new Event('visibilitychange'))
    fireEvent.click(
      await screen.findByRole('button', { name: 'Use recovered recording' }),
    )
    expect(
      await screen.findByRole('heading', { name: 'Bodyweight squat report' }),
    ).toBeInTheDocument()
  })
})
