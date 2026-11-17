import axe from 'axe-core'
import { fireEvent, render, screen } from '@testing-library/react'

import { EvidenceReport } from './EvidenceReport'

describe('EvidenceReport', () => {
  it('seeks evidence when selecting a rep and exposes keyboard alternatives', () => {
    render(<EvidenceReport />)
    const video = screen.getByLabelText(
      'Exercise evidence video',
    ) as HTMLVideoElement

    fireEvent.click(screen.getByRole('button', { name: /Rep 2/ }))

    expect(video.currentTime).toBe(6.2)
    expect(screen.getByRole('heading', { name: 'Rep 2' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Previous rep' })).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Next rep' })).toBeEnabled()
  })

  it('renders unavailable metrics as a dash with a reason, never zero', () => {
    render(<EvidenceReport />)

    expect(screen.getByLabelText('Not assessable')).toHaveTextContent('—')
    expect(screen.getByText(/hip was hidden/i)).toBeInTheDocument()
    expect(screen.queryByText('0 °')).not.toBeInTheDocument()
    expect(screen.getByText('2 of 3')).toBeInTheDocument()
  })

  it('has no detectable accessibility violations', async () => {
    const { container } = render(<EvidenceReport />)
    const results = await axe.run(container)
    expect(results.violations).toEqual([])
  })
})
