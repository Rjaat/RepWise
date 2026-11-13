import axe from 'axe-core'
import { render, screen } from '@testing-library/react'

import { App } from './App'

describe('App', () => {
  it('shows the RepWise health shell without invented analysis data', () => {
    render(<App />)

    expect(
      screen.getByRole('heading', {
        name: 'Understand your form. Improve every rep.',
      }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: 'Check API health' }),
    ).toHaveAttribute('href', 'http://127.0.0.1:8010/health')
    expect(screen.getByRole('button', { name: 'Analyse a set' })).toBeDisabled()
    expect(screen.getByText('Analysis unavailable')).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: 'Skip to main content' }),
    ).toHaveAttribute('href', '#main-content')
    expect(screen.getAllByRole('navigation')).toHaveLength(2)
  })

  it('has no detectable accessibility violations', async () => {
    const { container } = render(<App />)
    const results = await axe.run(container)
    expect(results.violations).toEqual([])
  })
})
