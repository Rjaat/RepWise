const API_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8010'

export function App() {
  return (
    <main className="shell">
      <section aria-labelledby="repwise-heading" className="status-panel">
        <p className="eyebrow">RepWise development environment</p>
        <h1 id="repwise-heading">Understand your form. Improve every rep.</h1>
        <p>
          The product shell is running. Exercise analysis stays unavailable
          until its evidence and release gates are implemented.
        </p>
        <a href={`${API_URL}/health`}>Check API health</a>
      </section>
    </main>
  )
}
