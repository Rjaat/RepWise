import { AppShell } from '@repwise/ui'

import { UploadPanel } from './UploadPanel'
import { EvidenceReport } from './EvidenceReport'
import { CameraSetup } from './CameraSetup'
import { RecordingSession } from './RecordingSession'
import { GuidedCaptureJourney } from './GuidedCaptureJourney'

const navigation = [
  { href: '/', label: 'Overview' },
  { href: '/analyse', label: 'Analyse', isCurrent: true },
  { href: '/exercises', label: 'Exercises' },
  { href: '/history', label: 'History' },
]

export function App() {
  const isReport = window.location.pathname.startsWith('/reports/')
  const isCapture = window.location.pathname.startsWith('/capture')
  const isRecording = window.location.pathname.startsWith('/record')
  const isGuidedJourney = window.location.pathname.startsWith('/guided-capture')
  return (
    <AppShell navigation={navigation}>
      {isReport ? (
        <EvidenceReport />
      ) : isGuidedJourney ? (
        <GuidedCaptureJourney />
      ) : isRecording ? (
        <RecordingSession />
      ) : isCapture ? (
        <CameraSetup />
      ) : (
        <UploadPanel />
      )}
    </AppShell>
  )
}
