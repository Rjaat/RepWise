import { AppShell, Button, StatusBadge, Surface } from '@repwise/ui'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8010'
const navigation = [
  { href: '/', label: 'Overview', isCurrent: true },
  { href: '/analyse', label: 'Analyse' },
  { href: '/exercises', label: 'Exercises' },
  { href: '/history', label: 'History' },
]

export function App() {
  return (
    <AppShell navigation={navigation}>
      <div className="development-page">
        <header className="development-page__header">
          <p className="development-page__eyebrow">Engineering foundation</p>
          <h1>Understand your form. Improve every rep.</h1>
          <p className="development-page__lede">
            RepWise is building evidence-linked exercise analysis. Analysis
            stays unavailable until its exercise-specific validation and release
            gates pass.
          </p>
        </header>
        <Surface aria-labelledby="foundation-status">
          <div className="development-page__status-row">
            <StatusBadge tone="success">Web shell ready</StatusBadge>
            <StatusBadge>Analysis unavailable</StatusBadge>
          </div>
          <h2 className="development-page__scope-title" id="foundation-status">
            Foundation status
          </h2>
          <p>
            The application shell and API health contract are ready. No sample
            metrics or form claims are shown as real user analysis.
          </p>
          <div className="development-page__actions">
            <a
              className="development-page__api-link"
              href={`${API_URL}/health`}
            >
              Check API health
            </a>
            <Button disabled>Analyse a set</Button>
          </div>
        </Surface>
        <Surface aria-labelledby="privacy-scope" tone="dark">
          <h2 className="development-page__scope-title" id="privacy-scope">
            Private movement studio
          </h2>
          <p className="development-page__scope-copy">
            Future recordings will be private by default. Upload, retention and
            research choices will remain explicit and separate.
          </p>
        </Surface>
      </div>
    </AppShell>
  )
}
