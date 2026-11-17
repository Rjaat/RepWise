import { AppShell } from '@repwise/ui'

import { UploadPanel } from './UploadPanel'
import { EvidenceReport } from './EvidenceReport'

const navigation = [
  { href: '/', label: 'Overview' },
  { href: '/analyse', label: 'Analyse', isCurrent: true },
  { href: '/exercises', label: 'Exercises' },
  { href: '/history', label: 'History' },
]

export function App() {
  const isReport = window.location.pathname.startsWith('/reports/')
  return (
    <AppShell navigation={navigation}>
      {isReport ? <EvidenceReport /> : <UploadPanel />}
    </AppShell>
  )
}
