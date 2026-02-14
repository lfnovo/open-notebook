/**
 * Tests for NoteEditorDialog component.
 *
 * These tests verify:
 * - Modal renders correctly with title and content fields
 * - Form validation for empty content
 * - Dialog close behavior
 * - Update note mutation when editing
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { enUS } from '@/lib/locales/en-US'

import { NoteEditorDialog } from './NoteEditorDialog'
import { useNote, useCreateNote, useUpdateNote } from '@/lib/hooks/use-notes'
import { useQueryClient } from '@tanstack/react-query'

// Mock the hooks - these are also mocked in setup.ts
vi.mock('@/lib/hooks/use-notes')
vi.mock('@/lib/api/query-client')
vi.mock('@tanstack/react-query')

// Mock useTranslation - must be mocked before component import
const mockT = vi.fn((key?: string) => {
  if (!key) return enUS
  const parts = key.split('.')
  let value: any = enUS
  for (const part of parts) {
    if (value && typeof value === 'object' && part in value) {
      value = value[part]
    } else {
      return key
    }
  }
  return value
})

vi.mock('@/lib/hooks/use-translation', () => ({
  useTranslation: () => ({
    t: new Proxy(mockT, {
      get: (target: any, prop: string | symbol) => {
        if (typeof prop !== 'string') return undefined
        const parts = prop.split('.')
        let value: any = enUS
        for (const part of parts) {
          if (value && typeof value === 'object' && part in value) {
            value = value[part]
          } else {
            return prop
          }
        }
        return value
      },
    }),
    language: 'en-US',
    setLanguage: vi.fn(),
  }),
}))

describe('NoteEditorDialog', () => {
  const defaultProps = {
    open: true,
    onOpenChange: vi.fn(),
    notebookId: 'notebook:123',
  }

  beforeEach(() => {
    vi.clearAllMocks()

    // Mock useQueryClient
    vi.mocked(useQueryClient).mockReturnValue({
      invalidateQueries: vi.fn(),
      setQueryData: vi.fn(),
      getQueryData: vi.fn(),
    })

    // Mock useNote hook
    vi.mocked(useNote).mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    })

    // Mock useCreateNote hook
    vi.mocked(useCreateNote).mockReturnValue({
      mutate: vi.fn(),
      mutateAsync: vi.fn().mockResolvedValue(undefined),
      isPending: false,
      isSuccess: false,
      error: null,
    })

    // Mock useUpdateNote hook
    vi.mocked(useUpdateNote).mockReturnValue({
      mutate: vi.fn(),
      mutateAsync: vi.fn().mockResolvedValue(undefined),
      isPending: false,
      isSuccess: false,
      error: null,
    })
  })

  it('should render title and content fields', () => {
    render(<NoteEditorDialog {...defaultProps} />)

    // Title field shows "Untitled Note" when not editing (button with emptyText)
    expect(screen.getByText(/untitled note/i)).toBeInTheDocument()
    // Content field - the flex-1 container should exist
    const contentContainer = screen.getByRole('dialog').querySelector('.flex-1.min-h-0')
    expect(contentContainer).toBeTruthy()
    // Create note button is present (find by role to avoid matching the hidden title)
    expect(screen.getByRole('button', { name: /create note/i })).toBeInTheDocument()
  })

  it('should show loading state when fetching note', () => {
    vi.mocked(useNote).mockReturnValue({
      data: null,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    })

    render(
      <NoteEditorDialog {...defaultProps} note={{ id: 'note:1', title: 'Test', content: 'Content' }} />
    )

    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })

  it('should show error message when content is empty', async () => {
    render(<NoteEditorDialog {...defaultProps} />)

    // Get the form by class and submit it without filling content
    const form = document.querySelector('.flex.flex-1.min-h-0.flex-col') as HTMLFormElement
    expect(form).toBeTruthy()
    fireEvent.submit(form)

    // Wait for validation error to appear
    await waitFor(() => {
      expect(screen.getByText(/content is required/i)).toBeInTheDocument()
    })
  })

  it('should call updateNote when editing an existing note', async () => {
    vi.mocked(useNote).mockReturnValue({
      data: { id: 'note:1', title: 'Test', content: 'Existing content' },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    })

    const mutateAsyncMock = vi.fn().mockResolvedValue(undefined)
    vi.mocked(useUpdateNote).mockReturnValue({
      mutate: vi.fn(),
      mutateAsync: mutateAsyncMock,
      isPending: false,
      isSuccess: false,
      error: null,
    })

    render(
      <NoteEditorDialog {...defaultProps} note={{ id: 'note:1', title: 'Test', content: 'Existing content' }} />
    )

    // Get the form by class and submit it
    const form = document.querySelector('.flex.flex-1.min-h-0.flex-col') as HTMLFormElement
    expect(form).toBeTruthy()
    fireEvent.submit(form)

    // Check that the mutateAsync was called
    await waitFor(() => {
      expect(mutateAsyncMock).toHaveBeenCalled()
    })
  })

  it('should close dialog when cancel is clicked', () => {
    const onOpenChange = vi.fn()
    render(<NoteEditorDialog {...defaultProps} onOpenChange={onOpenChange} />)

    const cancelBtn = screen.getByText(/cancel/i)
    fireEvent.click(cancelBtn)

    expect(onOpenChange).toHaveBeenCalledWith(false)
  })
})
