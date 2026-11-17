import axe from 'axe-core'
import { render, screen } from '@testing-library/react'

import { App } from './App'

describe('App', () => {
  it('shows the private side-view upload flow without invented analysis data', () => {
    render(<App />)

    expect(
      screen.getByRole('heading', {
        name: 'Upload your squat video',
      }),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Analyse video' })).toBeDisabled()
    expect(screen.getByText('Private by default')).toBeInTheDocument()
    expect(screen.getByText(/Frontal knee tracking/)).toBeInTheDocument()
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

  it('renders the evidence report route', () => {
    window.history.pushState({}, '', '/reports/sample')
    render(<App />)
    expect(
      screen.getByRole('heading', { name: 'Bodyweight squat report' }),
    ).toBeInTheDocument()
    window.history.pushState({}, '', '/')
  })
})
