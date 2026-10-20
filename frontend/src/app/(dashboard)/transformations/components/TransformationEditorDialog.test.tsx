import { ReactNode } from 'react'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { Transformation } from '@/lib/types/transformations'
import { TransformationEditorDialog } from './TransformationEditorDialog'

// Radix Select measures its trigger via ResizeObserver, which jsdom lacks.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal('ResizeObserver', ResizeObserverStub)

const updateMutateAsync = vi.fn()

const transformation: Transformation = {
  id: 'transformation:t1',
  name: 'summary',
  title: 'Summary',
  description: 'old description',
  prompt: 'Summarize',
  apply_default: false,
  model_id: null,
  created: '2026-01-01T00:00:00Z',
  updated: '2026-01-02T00:00:00Z',
}

vi.mock('@/lib/hooks/use-transformations', () => ({
  useTransformation: () => ({ data: transformation, isLoading: false }),
  useCreateTransformation: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdateTransformation: () => ({ mutateAsync: updateMutateAsync, isPending: false }),
  TRANSFORMATION_QUERY_KEYS: { transformation: (id: string) => ['transformations', id] },
}))

vi.mock('@/lib/hooks/use-models', () => ({
  useModels: () => ({ data: [], isLoading: false }),
}))

vi.mock('@/components/ui/markdown-editor', () => ({
  MarkdownEditor: ({ value, onChange }: { value: string; onChange: (v: string) => void }) => (
    <textarea aria-label="prompt" value={value} onChange={(e) => onChange(e.target.value)} />
  ),
}))

function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>
}

describe('TransformationEditorDialog', () => {
  beforeEach(() => {
    updateMutateAsync.mockReset()
    updateMutateAsync.mockResolvedValue(transformation)
  })

  // A cleared description used to be sent as `undefined`, i.e. dropped from
  // the update, so the old text came back after a refresh (#1396).
  it('sends an empty description when the description is cleared', async () => {
    render(
      <TransformationEditorDialog open onOpenChange={vi.fn()} transformation={transformation} />,
      { wrapper }
    )

    const description = await screen.findByDisplayValue('old description')
    fireEvent.change(description, { target: { value: '' } })
    fireEvent.submit(description.closest('form')!)

    await waitFor(() => expect(updateMutateAsync).toHaveBeenCalled())
    expect(updateMutateAsync.mock.calls[0][0]).toMatchObject({
      id: 'transformation:t1',
      data: { description: '', title: 'Summary', name: 'summary' },
    })
  })
})
