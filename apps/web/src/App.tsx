import { AppShell } from '@repwise/ui'

import { UploadPanel } from './UploadPanel'
import { EvidenceReport } from './EvidenceReport'
import { CameraSetup } from './CameraSetup'

const navigation = [
  { href: '/', label: 'Overview' },
  { href: '/analyse', label: 'Analyse', isCurrent: true },
  { href: '/exercises', label: 'Exercises' },
  { href: '/history', label: 'History' },
]

export function App() {
  const isReport = window.location.pathname.startsWith('/reports/')
  const isCapture = window.location.pathname.startsWith('/capture')
  return (
    <AppShell navigation={navigation}>
      {isReport ? (
        <EvidenceReport />
      ) : isCapture ? (
        <CameraSetup />
      ) : (
        <UploadPanel />
      )}
    </AppShell>
  )
}
