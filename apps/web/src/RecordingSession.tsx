import { useEffect, useRef, useState } from 'react'
import { Button, Surface } from '@repwise/ui'

import { negotiateRecorderFormat, stopStream } from './cameraCapabilities'

type RecordingState =
  | { kind: 'ready' }
  | { kind: 'countdown'; seconds: number }
  | { kind: 'recording' }
  | { kind: 'exit_confirm' }
  | { kind: 'interrupted'; reason: string; file: File }
  | { kind: 'review'; file: File }
  | { kind: 'error'; message: string }

export function RecordingSession({
  countdownSeconds = 3,
  onUseRecording = () => undefined,
}: {
  countdownSeconds?: number
  onUseRecording?: (file: File) => void
}) {
  const [state, setState] = useState<RecordingState>({ kind: 'ready' })
  const [elapsed, setElapsed] = useState(0)
  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const stopModeRef = useRef<'review' | 'interrupted' | 'discard'>('review')
  const interruptionRef = useRef('Recording was interrupted.')
  const previewUrlRef = useRef<string | null>(null)

  useEffect(
    () => () => {
      stopStream(streamRef.current)
      if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current)
    },
    [],
  )

  useEffect(() => {
    if (state.kind !== 'countdown') return
    if (state.seconds === 0) {
      // Function declarations are hoisted; the timer always uses the current render.
      // eslint-disable-next-line react-hooks/immutability
      void beginRecording()
      return
    }
    const timer = window.setTimeout(
      () => setState({ kind: 'countdown', seconds: state.seconds - 1 }),
      1000,
    )
    return () => window.clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state])

  useEffect(() => {
    if (state.kind !== 'recording') return
    const timer = window.setInterval(
      () => setElapsed((current) => current + 0.25),
      250,
    )
    return () => window.clearInterval(timer)
  }, [state])

  useEffect(() => {
    const onVisibility = () => {
      // Function declarations are hoisted; the listener is replaced each render.
      // eslint-disable-next-line react-hooks/immutability
      if (document.hidden) interrupt('The app moved to the background.')
    }
    document.addEventListener('visibilitychange', onVisibility)
    return () => document.removeEventListener('visibilitychange', onVisibility)
  })

  async function ensureStream() {
    if (streamRef.current) return streamRef.current
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder)
      throw new Error('Camera recording is unavailable in this browser.')
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: false,
      video: { facingMode: 'environment' },
    })
    stream
      .getVideoTracks()
      .forEach((track) =>
        track.addEventListener('ended', () =>
          interrupt('The camera connection ended.'),
        ),
      )
    streamRef.current = stream
    if (videoRef.current) {
      videoRef.current.srcObject = stream
      await videoRef.current.play()
    }
    return stream
  }

  async function startCountdown() {
    try {
      await ensureStream()
      setState({ kind: 'countdown', seconds: countdownSeconds })
    } catch (error) {
      setState({
        kind: 'error',
        message:
          error instanceof Error ? error.message : 'Camera could not start.',
      })
    }
  }

  async function beginRecording() {
    try {
      const stream = await ensureStream()
      const mimeType = negotiateRecorderFormat(MediaRecorder.isTypeSupported)
      if (!mimeType)
        throw new Error('No compatible recording format was found.')
      chunksRef.current = []
      const recorder = new MediaRecorder(stream, { mimeType })
      recorderRef.current = recorder
      recorder.addEventListener('dataavailable', (event) => {
        if (event.data.size) chunksRef.current.push(event.data)
      })
      recorder.addEventListener('stop', finalizeRecording, { once: true })
      recorder.start(250)
      setElapsed(0)
      setState({ kind: 'recording' })
    } catch (error) {
      setState({
        kind: 'error',
        message:
          error instanceof Error ? error.message : 'Recording could not start.',
      })
    }
  }

  function finalizeRecording() {
    const recorder = recorderRef.current
    recorderRef.current = null
    if (stopModeRef.current === 'discard') {
      chunksRef.current = []
      setState({ kind: 'ready' })
      return
    }
    const blob = new Blob(chunksRef.current, {
      type: recorder?.mimeType || 'video/webm',
    })
    const file = new File([blob], `repwise-${Date.now()}.webm`, {
      type: blob.type,
    })
    if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current)
    previewUrlRef.current = URL.createObjectURL(file)
    if (videoRef.current) {
      videoRef.current.srcObject = null
      videoRef.current.src = previewUrlRef.current
    }
    setState(
      stopModeRef.current === 'interrupted'
        ? { kind: 'interrupted', reason: interruptionRef.current, file }
        : { kind: 'review', file },
    )
  }

  function stop(mode: 'review' | 'interrupted' | 'discard', reason?: string) {
    const recorder = recorderRef.current
    if (!recorder || recorder.state === 'inactive') return
    stopModeRef.current = mode
    if (reason) interruptionRef.current = reason
    recorder.stop()
  }

  function interrupt(reason: string) {
    stop('interrupted', reason)
  }

  const reviewing = state.kind === 'review' || state.kind === 'interrupted'

  return (
    <div className="recording-session">
      <header>
        <p className="report__eyebrow">Bodyweight squat · Side view</p>
        <h1>Record your set</h1>
      </header>
      <div className="recording-session__layout">
        <section className="recording-preview" aria-label="Recording preview">
          <video
            ref={videoRef}
            muted={!reviewing}
            playsInline
            controls={reviewing}
            aria-label="Set recording"
          />
          {state.kind === 'countdown' && (
            <strong className="recording-countdown" aria-live="assertive">
              {state.seconds}
            </strong>
          )}
          {state.kind === 'recording' && (
            <div className="recording-indicator">
              <span />
              Recording <time>{elapsed.toFixed(1)} s</time>
            </div>
          )}
        </section>
        <Surface className="recording-controls" aria-live="polite">
          {state.kind === 'ready' && (
            <>
              <h2>Ready to record</h2>
              <p>
                Your practice repetition is excluded. Record one continuous set.
              </p>
              <Button fullWidth onClick={() => void startCountdown()}>
                Start countdown
              </Button>
            </>
          )}
          {state.kind === 'countdown' && (
            <>
              <h2>Get into position</h2>
              <p>Recording starts after the countdown.</p>
              <Button
                fullWidth
                variant="secondary"
                onClick={() => setState({ kind: 'ready' })}
              >
                Cancel countdown
              </Button>
            </>
          )}
          {state.kind === 'recording' && (
            <>
              <h2>Recording</h2>
              <p>Keep your full movement in view.</p>
              <Button fullWidth onClick={() => stop('review')}>
                Stop recording
              </Button>
              <Button
                fullWidth
                variant="quiet"
                onClick={() => setState({ kind: 'exit_confirm' })}
              >
                Exit recording
              </Button>
            </>
          )}
          {state.kind === 'exit_confirm' && (
            <>
              <h2>Leave this recording?</h2>
              <p>Save the footage for review or discard it explicitly.</p>
              <Button
                fullWidth
                onClick={() =>
                  stop('interrupted', 'You ended the recording early.')
                }
              >
                Save and review
              </Button>
              <Button
                fullWidth
                variant="danger"
                onClick={() => stop('discard')}
              >
                Discard recording
              </Button>
            </>
          )}
          {state.kind === 'interrupted' && (
            <>
              <h2>Recording interrupted</h2>
              <p>
                {state.reason} Your captured footage is available to review.
              </p>
              <Button fullWidth onClick={() => onUseRecording(state.file)}>
                Use recovered recording
              </Button>
              <Button
                fullWidth
                variant="secondary"
                onClick={() => setState({ kind: 'ready' })}
              >
                Record again
              </Button>
            </>
          )}
          {state.kind === 'review' && (
            <>
              <h2>Review your set</h2>
              <p>Use this recording or discard it and record again.</p>
              <Button fullWidth onClick={() => onUseRecording(state.file)}>
                Use this recording
              </Button>
              <Button
                fullWidth
                variant="danger"
                onClick={() => {
                  chunksRef.current = []
                  setState({ kind: 'ready' })
                }}
              >
                Discard and record again
              </Button>
            </>
          )}
          {state.kind === 'error' && (
            <>
              <h2>Recording unavailable</h2>
              <p role="alert">{state.message}</p>
              <Button fullWidth onClick={() => setState({ kind: 'ready' })}>
                Try again
              </Button>
            </>
          )}
        </Surface>
      </div>
    </div>
  )
}
