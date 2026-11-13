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
    expect(screen.getByRole('link', { name: 'Check API health' })).toHaveAttribute(
      'href',
      'http://127.0.0.1:8010/health',
    )
  })
})
