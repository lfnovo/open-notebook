import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { TransformationsList } from './TransformationsList'
import { Transformation } from '@/lib/types/transformations'

// useTranslation is mocked globally in setup.ts (t returns the key string)

vi.mock('./TransformationEditorDialog', () => ({
  TransformationEditorDialog: ({ open }: { open: boolean }) =>
    open ? <div data-testid="transformation-editor-dialog" /> : null,
}))

vi.mock('./TransformationCard', () => ({
  TransformationCard: () => <div data-testid="transformation-card" />,
}))

const mockTransformation: Transformation = {
  id: 'transformation:1',
  name: 'summarize',
  title: 'Summarize',
  description: 'Summarize the content',
  prompt: 'Summarize this',
  apply_default: false,
  model_id: null,
  created: '2026-01-01T00:00:00Z',
  updated: '2026-01-01T00:00:00Z',
}

describe('TransformationsList', () => {
  it('opens the editor dialog from the empty state create button', () => {
    render(<TransformationsList transformations={[]} isLoading={false} />)

    fireEvent.click(screen.getByText('transformations.createNew'))

    expect(screen.getByTestId('transformation-editor-dialog')).toBeInTheDocument()
  })

  it('opens the editor dialog from the list header create button', () => {
    render(<TransformationsList transformations={[mockTransformation]} isLoading={false} />)

    fireEvent.click(screen.getByText('transformations.createNew'))

    expect(screen.getByTestId('transformation-editor-dialog')).toBeInTheDocument()
  })
})
