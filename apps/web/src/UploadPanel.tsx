import { useEffect, useRef, useState } from 'react'
import { Button, StatusBadge, Surface } from '@repwise/ui'

import { browserUploadClient, type UploadClient } from './uploadApi'

const MAX_BYTES = 250 * 1024 * 1024
const ACCEPTED_TYPES = ['video/mp4', 'video/quicktime', 'video/webm']

type UploadState =
  | { kind: 'empty' }
  | { kind: 'review'; file: File; previewUrl: string }
  | { kind: 'uploading'; file: File; previewUrl: string; progress: number }
  | { kind: 'error'; file: File; previewUrl: string; message: string }
  | { kind: 'complete'; file: File; previewUrl: string; jobId: string }

function formatBytes(bytes: number): string {
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function UploadPanel({
  client = browserUploadClient,
}: {
  client?: UploadClient
}) {
  const [state, setState] = useState<UploadState>({ kind: 'empty' })
  const [validationMessage, setValidationMessage] = useState('')
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => () => abortRef.current?.abort(), [])

  function selectFile(file: File | undefined) {
    setValidationMessage('')
    if (!file) return
    if (!ACCEPTED_TYPES.includes(file.type)) {
      setValidationMessage('Choose an MP4, QuickTime or WebM video.')
      return
    }
    if (file.size > MAX_BYTES) {
      setValidationMessage('Choose a video smaller than 250 MB.')
      return
    }
    if ('previewUrl' in state) URL.revokeObjectURL(state.previewUrl)
    setState({ kind: 'review', file, previewUrl: URL.createObjectURL(file) })
  }

  async function startUpload() {
    if (!('file' in state)) return
    const { file, previewUrl } = state
    const controller = new AbortController()
    abortRef.current = controller
    setState({ kind: 'uploading', file, previewUrl, progress: 0 })
    try {
      const ticket = await client.upload(
        file,
        (progress) => {
          setState((current) =>
            current.kind === 'uploading' ? { ...current, progress } : current,
          )
        },
        controller.signal,
      )
      if (!ticket.analysis_job_id) throw new Error('Analysis was not queued.')
      setState({
        kind: 'complete',
        file,
        previewUrl,
        jobId: ticket.analysis_job_id,
      })
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        setState({ kind: 'review', file, previewUrl })
      } else {
        setState({
          kind: 'error',
          file,
          previewUrl,
          message:
            error instanceof Error ? error.message : 'The upload failed.',
        })
      }
    } finally {
      abortRef.current = null
    }
  }

  const hasFile = 'file' in state

  return (
    <div className="upload-flow">
      <header className="upload-flow__header">
        <p className="upload-flow__eyebrow">Analyse a set</p>
        <h1>Upload your squat video</h1>
        <p>
          Use one continuous side-view set with one person fully visible. Your
          video stays private and uploads only when you choose Analyse video.
        </p>
      </header>
      <ol aria-label="Upload steps" className="upload-steps">
        <li className="upload-steps__done">Exercise</li>
        <li className="upload-steps__done">Capture</li>
        <li aria-current="step">Review</li>
      </ol>
      <div className="upload-flow__layout">
        <Surface aria-labelledby="upload-heading" className="upload-panel">
          <div className="upload-panel__heading">
            <div>
              <h2 id="upload-heading">Video</h2>
              <p>MP4, MOV or WebM · one set · up to 3 minutes and 250 MB</p>
            </div>
            {hasFile && state.kind !== 'uploading' && (
              <label className="upload-panel__replace" htmlFor="video-file">
                Replace video
              </label>
            )}
          </div>
          {!hasFile ? (
            <div className="upload-drop-zone">
              <p className="upload-drop-zone__title">
                Choose a video to review
              </p>
              <p>
                Your file remains on this device until you start the upload.
              </p>
              <label className="upload-file-button" htmlFor="video-file">
                Browse files
              </label>
            </div>
          ) : (
            <div className="upload-preview">
              <video
                aria-label="Selected video preview"
                controls
                src={state.previewUrl}
              />
              <div className="upload-preview__meta">
                <strong>{state.file.name}</strong>
                <span>{formatBytes(state.file.size)}</span>
              </div>
            </div>
          )}
          <input
            accept="video/mp4,video/quicktime,video/webm,.mov"
            className="upload-file-input"
            id="video-file"
            onChange={(event) => selectFile(event.target.files?.[0])}
            type="file"
          />
          {validationMessage && (
            <p className="upload-alert upload-alert--error" role="alert">
              {validationMessage}
            </p>
          )}
          {state.kind === 'uploading' && (
            <div aria-live="polite" className="upload-progress">
              <div className="upload-progress__label">
                <span>Uploading securely</span>
                <strong>{state.progress}%</strong>
              </div>
              <progress max="100" value={state.progress}>
                {state.progress}%
              </progress>
            </div>
          )}
          {state.kind === 'error' && (
            <div className="upload-alert upload-alert--error" role="alert">
              <strong>Upload paused</strong>
              <span>{state.message} Your selected video is still here.</span>
            </div>
          )}
          {state.kind === 'complete' && (
            <div className="upload-alert upload-alert--success" role="status">
              <strong>Upload complete</strong>
              <span>
                You can leave this page. Processing will continue in History.
              </span>
            </div>
          )}
        </Surface>
        <aside className="upload-summary" aria-labelledby="assessment-heading">
          <StatusBadge>Side view required</StatusBadge>
          <label className="upload-summary__exercise" htmlFor="exercise">
            Exercise
            <select defaultValue="bodyweight-squat" id="exercise">
              <option value="bodyweight-squat">Bodyweight squat</option>
            </select>
          </label>
          <h2 id="assessment-heading">Bodyweight squat</h2>
          <p>
            We will first check whether the video is suitable before assessing
            reps.
          </p>
          <h3>Candidate measurements</h3>
          <ul>
            <li>Rep count and phase timing</li>
            <li>Visible depth consistency</li>
            <li>Return to standing</li>
          </ul>
          <p className="upload-summary__limit">
            Frontal knee tracking, internal loading and precise 3D mechanics are
            not available from this view.
          </p>
          <div className="upload-summary__privacy">
            <strong>Private by default</strong>
            <span>Cloud processing starts only after confirmation.</span>
          </div>
          {state.kind === 'uploading' ? (
            <Button
              fullWidth
              onClick={() => abortRef.current?.abort()}
              variant="secondary"
            >
              Cancel upload
            </Button>
          ) : state.kind === 'complete' ? (
            <Button disabled fullWidth>
              Processing video
            </Button>
          ) : (
            <Button disabled={!hasFile} fullWidth onClick={startUpload}>
              {state.kind === 'error' ? 'Try upload again' : 'Analyse video'}
            </Button>
          )}
        </aside>
      </div>
    </div>
  )
}
