import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'

import { UploadPanel } from './UploadPanel'
import type { UploadClient, UploadTicket } from './uploadApi'

const completeTicket: UploadTicket = {
  upload_id: 'upload-1',
  status: 'completed',
  upload_url: null,
  analysis_job_id: 'job-1',
}

function videoFile(name = 'squat.mp4', type = 'video/mp4', size = 1024) {
  const file = new File(['video'], name, { type })
  Object.defineProperty(file, 'size', { value: size })
  return file
}

beforeEach(() => {
  vi.stubGlobal('URL', {
    ...URL,
    createObjectURL: vi.fn(() => 'blob:preview'),
    revokeObjectURL: vi.fn(),
  })
})

afterEach(() => vi.unstubAllGlobals())

it('reviews a valid file and reports real upload progress', async () => {
  let finishUpload: ((ticket: UploadTicket) => void) | undefined
  const client: UploadClient = {
    upload: vi.fn((_file, onProgress) => {
      onProgress(64)
      return new Promise<UploadTicket>((resolve) => {
        finishUpload = resolve
      })
    }),
  }
  render(<UploadPanel client={client} />)

  fireEvent.change(screen.getByLabelText('Browse files'), {
    target: { files: [videoFile()] },
  })
  expect(screen.getByLabelText('Selected video preview')).toHaveAttribute(
    'src',
    'blob:preview',
  )

  fireEvent.click(screen.getByRole('button', { name: 'Analyse video' }))
  expect(await screen.findAllByText('64%')).toHaveLength(2)
  finishUpload?.(completeTicket)
  expect(await screen.findByText('Upload complete')).toBeInTheDocument()
  expect(
    screen.getByRole('button', { name: 'Processing video' }),
  ).toBeDisabled()
})

it('rejects unsupported and oversized files without losing recovery guidance', () => {
  render(<UploadPanel />)
  const input = screen.getByLabelText('Browse files')

  fireEvent.change(input, {
    target: { files: [videoFile('photo.jpg', 'image/jpeg')] },
  })
  expect(screen.getByRole('alert')).toHaveTextContent('Choose an MP4')

  fireEvent.change(input, {
    target: {
      files: [videoFile('large.mp4', 'video/mp4', 250 * 1024 * 1024 + 1)],
    },
  })
  expect(screen.getByRole('alert')).toHaveTextContent('smaller than 250 MB')
})

it('cancels an active upload and keeps the selected file for retry', async () => {
  const client: UploadClient = {
    upload: vi.fn(
      (_file, _onProgress, signal) =>
        new Promise<UploadTicket>((_resolve, reject) => {
          signal.addEventListener('abort', () =>
            reject(new DOMException('Cancelled', 'AbortError')),
          )
        }),
    ),
  }
  render(<UploadPanel client={client} />)
  fireEvent.change(screen.getByLabelText('Browse files'), {
    target: { files: [videoFile()] },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Analyse video' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Cancel upload' }))

  await waitFor(() =>
    expect(screen.getByRole('button', { name: 'Analyse video' })).toBeEnabled(),
  )
  expect(screen.getByText('squat.mp4')).toBeInTheDocument()
})

it('preserves a failed selection and offers an explicit retry', async () => {
  const client: UploadClient = {
    upload: vi
      .fn()
      .mockRejectedValueOnce(new Error('Connection lost.'))
      .mockResolvedValue(completeTicket),
  }
  render(<UploadPanel client={client} />)
  fireEvent.change(screen.getByLabelText('Browse files'), {
    target: { files: [videoFile()] },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Analyse video' }))

  expect(await screen.findByRole('alert')).toHaveTextContent('Connection lost')
  fireEvent.click(screen.getByRole('button', { name: 'Try upload again' }))
  expect(await screen.findByText('Upload complete')).toBeInTheDocument()
})
