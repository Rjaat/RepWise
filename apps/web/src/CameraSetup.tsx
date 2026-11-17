import { useEffect, useRef, useState } from 'react'
import { Button, StatusBadge, Surface } from '@repwise/ui'

import {
  classifyCameraError,
  negotiateRecorderFormat,
  stopStream,
  type CameraFailure,
} from './cameraCapabilities'

type TelemetryEvent = {
  event: 'camera_ready' | 'camera_failed'
  failure?: CameraFailure
  recorderMimeType?: string | null
  cameraCount?: number
}

type CameraState =
  | { kind: 'idle' }
  | { kind: 'requesting' }
  | { kind: 'ready'; recorderMimeType: string | null }
  | { kind: 'failed'; failure: CameraFailure }

type Readiness = {
  ready: boolean
  instruction: string
  checks: {
    full_movement_visible: boolean
    side_view_suitable: boolean
    camera_stable: boolean
  }
}

const failureCopy: Record<CameraFailure, { title: string; message: string }> = {
  permission_denied: {
    title: 'Camera access is blocked',
    message: 'Enable camera access in your browser settings, then try again.',
  },
  device_missing: {
    title: 'No camera was found',
    message: 'Connect a camera or upload a video instead.',
  },
  device_busy: {
    title: 'Camera is in use',
    message: 'Close other apps using the camera, then try again.',
  },
  unsupported: {
    title: 'Camera capture is unavailable',
    message:
      'This browser cannot start guided capture. Upload a video instead.',
  },
  unknown: {
    title: 'Camera could not start',
    message: 'Check the camera connection and try again.',
  },
}

export function CameraSetup({
  onTelemetry = () => undefined,
  readiness,
}: {
  onTelemetry?: (event: TelemetryEvent) => void
  readiness?: Readiness
}) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const [state, setState] = useState<CameraState>({ kind: 'idle' })
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([])
  const [deviceId, setDeviceId] = useState('')

  useEffect(() => () => stopStream(streamRef.current), [])

  async function startCamera(selectedDeviceId?: string) {
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setState({ kind: 'failed', failure: 'unsupported' })
      onTelemetry({ event: 'camera_failed', failure: 'unsupported' })
      return
    }
    setState({ kind: 'requesting' })
    stopStream(streamRef.current)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: selectedDeviceId
          ? { deviceId: { exact: selectedDeviceId } }
          : {
              facingMode: 'environment',
              width: { ideal: 1280 },
              height: { ideal: 720 },
            },
      })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }
      const available = (
        await navigator.mediaDevices.enumerateDevices()
      ).filter((device) => device.kind === 'videoinput')
      setDevices(available)
      const activeDevice =
        stream.getVideoTracks()[0]?.getSettings().deviceId ??
        selectedDeviceId ??
        ''
      setDeviceId(activeDevice)
      const recorderMimeType = negotiateRecorderFormat((mimeType) =>
        MediaRecorder.isTypeSupported(mimeType),
      )
      setState({ kind: 'ready', recorderMimeType })
      onTelemetry({
        event: 'camera_ready',
        recorderMimeType,
        cameraCount: available.length,
      })
    } catch (error) {
      const failure = classifyCameraError(error)
      setState({ kind: 'failed', failure })
      onTelemetry({ event: 'camera_failed', failure })
    }
  }

  const failure = state.kind === 'failed' ? failureCopy[state.failure] : null

  return (
    <div className="camera-setup">
      <header className="camera-setup__header">
        <p className="report__eyebrow">Exercise · Bodyweight squat</p>
        <h1>Set up your side view</h1>
        <p>Place the camera where your full movement can remain visible.</p>
      </header>
      <div className="camera-setup__layout">
        <section className="camera-preview" aria-label="Camera preview">
          <video
            ref={videoRef}
            muted
            playsInline
            aria-label="Live camera preview"
          />
          <span className="camera-preview__corner camera-preview__corner--one" />
          <span className="camera-preview__corner camera-preview__corner--two" />
          {state.kind !== 'ready' && (
            <div className="camera-preview__empty">
              <strong>Camera preview</strong>
              <span>Video stays on this device until you record.</span>
            </div>
          )}
        </section>
        <Surface
          className="camera-instructions"
          aria-labelledby="camera-instruction"
        >
          <StatusBadge>Side view required</StatusBadge>
          <h2 id="camera-instruction">
            {state.kind === 'ready' && readiness
              ? readiness.instruction
              : state.kind === 'ready'
                ? 'Camera connected'
                : 'Connect your camera'}
          </h2>
          <p>
            {state.kind === 'ready'
              ? 'Next, position the phone so your head and feet stay in frame.'
              : 'We will ask for camera access and show the preview before recording.'}
          </p>
          {state.kind === 'ready' && readiness && (
            <ul className="camera-checklist" aria-label="Capture readiness">
              <li data-ready={readiness.checks.full_movement_visible}>
                Full movement visible
              </li>
              <li data-ready={readiness.checks.side_view_suitable}>
                Side view suitable
              </li>
              <li data-ready={readiness.checks.camera_stable}>Camera stable</li>
            </ul>
          )}
          {devices.length > 1 && (
            <label
              className="camera-instructions__device"
              htmlFor="camera-device"
            >
              Camera
              <select
                id="camera-device"
                value={deviceId}
                onChange={(event) => void startCamera(event.target.value)}
              >
                {devices.map((device, index) => (
                  <option key={device.deviceId} value={device.deviceId}>
                    {device.label || `Camera ${index + 1}`}
                  </option>
                ))}
              </select>
            </label>
          )}
          {state.kind === 'ready' && (
            <div className="camera-capability" role="status">
              <strong>
                {state.recorderMimeType
                  ? 'Recording supported'
                  : 'Replay-only mode'}
              </strong>
              <span>
                {state.recorderMimeType ??
                  'No compatible recording format was found.'}
              </span>
            </div>
          )}
          {failure && (
            <div className="upload-alert upload-alert--error" role="alert">
              <strong>{failure.title}</strong>
              <span>{failure.message}</span>
            </div>
          )}
          <Button
            fullWidth
            onClick={() => void startCamera()}
            disabled={
              state.kind === 'requesting' ||
              (state.kind === 'ready' &&
                readiness !== undefined &&
                !readiness.ready)
            }
          >
            {state.kind === 'ready' && readiness?.ready
              ? 'Try one practice rep'
              : state.kind === 'requesting'
                ? 'Connecting camera'
                : state.kind === 'failed'
                  ? 'Try camera again'
                  : 'Use camera'}
          </Button>
          <a className="camera-instructions__upload" href="/analyse">
            Upload a video instead
          </a>
        </Surface>
      </div>
    </div>
  )
}
