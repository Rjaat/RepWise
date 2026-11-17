import { AppShell } from '@repwise/ui'

import { UploadPanel } from './UploadPanel'

const navigation = [
  { href: '/', label: 'Overview' },
  { href: '/analyse', label: 'Analyse', isCurrent: true },
  { href: '/exercises', label: 'Exercises' },
  { href: '/history', label: 'History' },
]

export function App() {
  return (
    <AppShell navigation={navigation}>
      <UploadPanel />
    </AppShell>
  )
}
