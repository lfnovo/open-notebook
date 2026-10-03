import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, within } from '@testing-library/react'

import { ArtifactList } from './ArtifactList'
import type { Artifact } from '@/lib/types/artifacts'

// useTranslation is mocked globally in src/test/setup.ts (t returns the key)

function makeArtifact(overrides: Partial<Artifact> = {}): Artifact {
  return {
    id: 'generated_artifact:1',
    notebook_id: 'notebook:1',
    title: 'My report',
    kind: 'report',
    formats: ['md', 'docx'],
    language: 'en',
    sections: 3,
    output_path: 'abc/my-report-report.md',
    note_id: 'note:1',
    created: '2026-09-20T10:00:00Z',
    job_status: 'completed',
    error_message: null,
    download_url: '/api/artifacts/generated_artifact:1/download',
    files: ['md', 'docx'],
    ...overrides,
  }
}

describe('ArtifactList', () => {
  it('renders a row with title, status badge and one download link per format', () => {
    render(<ArtifactList artifacts={[makeArtifact()]} onDelete={() => {}} />)

    expect(screen.getByText('My report')).toBeInTheDocument()
    expect(screen.getByText('artifacts.statusCompleted')).toBeInTheDocument()
    expect(screen.getByText('artifacts.download MD')).toHaveAttribute(
      'href',
      '/api/artifacts/generated_artifact:1/download?format=md'
    )
    expect(screen.getByText('artifacts.download DOCX')).toHaveAttribute(
      'href',
      '/api/artifacts/generated_artifact:1/download?format=docx'
    )
  })

  it('shows the empty state when there are no artifacts', () => {
    render(<ArtifactList artifacts={[]} onDelete={() => {}} />)

    expect(screen.getByText('artifacts.emptyState')).toBeInTheDocument()
  })

  it('hides download links and flags the missing file while generating', () => {
    render(
      <ArtifactList
        artifacts={[
          makeArtifact({
            job_status: 'running',
            files: [],
            download_url: null,
            output_path: null,
          }),
        ]}
        onDelete={() => {}}
      />
    )

    expect(screen.getByText('artifacts.statusRunning')).toBeInTheDocument()
    expect(screen.getByText('artifacts.noFileYet')).toBeInTheDocument()
    expect(screen.queryByText('artifacts.download MD')).not.toBeInTheDocument()
  })

  it('shows the job error as the status badge tooltip when it failed', () => {
    render(
      <ArtifactList
        artifacts={[
          makeArtifact({
            job_status: 'failed',
            error_message: 'no model configured',
          }),
        ]}
        onDelete={() => {}}
      />
    )

    expect(screen.getByText('artifacts.statusFailed')).toHaveAttribute(
      'title',
      'no model configured'
    )
  })

  it('asks for confirmation before deleting', async () => {
    const onDelete = vi.fn()
    render(<ArtifactList artifacts={[makeArtifact()]} onDelete={onDelete} />)

    expect(onDelete).not.toHaveBeenCalled()

    fireEvent.click(screen.getByLabelText('artifacts.delete'))

    const dialog = await screen.findByRole('alertdialog')
    expect(screen.getByText('artifacts.deleteTitle')).toBeInTheDocument()

    fireEvent.click(within(dialog).getByRole('button', { name: 'artifacts.delete' }))

    expect(onDelete).toHaveBeenCalledWith('generated_artifact:1')
  })
})
