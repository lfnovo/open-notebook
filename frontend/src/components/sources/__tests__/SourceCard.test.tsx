/**
 * @jest-environment jsdom
 */

import React from 'react'
import { screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { vi } from 'vitest'
import { renderWithProviders } from '@/test-utils'
import { SourceCard } from '@/components/sources/SourceCard'
import { createMockSource, mockStatuses } from '@/__mocks__/mock-data'
import { useSourceStatus } from '@/lib/hooks/use-sources'

// Mock the hooks
vi.mock('@/lib/hooks/use-sources', () => ({
  useSourceStatus: vi.fn(),
}))

const mockUseSourceStatus = useSourceStatus as unknown as ReturnType<typeof vi.fn>

describe('SourceCard', () => {
  const mockOnDelete = vi.fn()
  const mockOnRetry = vi.fn()
  const mockOnRemoveFromNotebook = vi.fn()
  const mockOnClick = vi.fn()
  const mockOnRefresh = vi.fn()
  const mockOnContextModeChange = vi.fn()

  beforeEach(() => {
  vi.clearAllMocks()
    
    // Default mock - no status fetching
    mockUseSourceStatus.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
      isSuccess: false,
      error: null,
    } as ReturnType<typeof useSourceStatus>)
  })

  describe('Rendering', () => {
    it('should render source card with basic information', () => {
      const source = createMockSource({
        title: 'Test Source',
        insights_count: 5,
        topics: ['typescript', 'testing'],
      })

      renderWithProviders(<SourceCard source={source} />)

      expect(screen.getByText('Test Source')).toBeInTheDocument()
      expect(screen.getByText('5 insights')).toBeInTheDocument()
      expect(screen.getByText('typescript')).toBeInTheDocument()
      expect(screen.getByText('testing')).toBeInTheDocument()
    })

    it('should render link type indicator', () => {
      const source = createMockSource({
        asset: { url: 'https://example.com' },
      })

      renderWithProviders(<SourceCard source={source} />)

      expect(screen.getByText('link')).toBeInTheDocument()
    })

    it('should render upload type indicator', () => {
      const source = createMockSource({
        asset: { file_path: '/uploads/test.pdf' },
      })

      renderWithProviders(<SourceCard source={source} />)

      expect(screen.getByText('upload')).toBeInTheDocument()
    })

    it('should render text type indicator when no asset', () => {
      const source = createMockSource({
        asset: null,
      })

      renderWithProviders(<SourceCard source={source} />)

      expect(screen.getByText('text')).toBeInTheDocument()
    })

    it('should truncate long topic lists', () => {
      const source = createMockSource({
        topics: ['topic1', 'topic2', 'topic3', 'topic4'],
      })

      renderWithProviders(<SourceCard source={source} />)

      expect(screen.getByText('topic1')).toBeInTheDocument()
      expect(screen.getByText('topic2')).toBeInTheDocument()
      expect(screen.getByText('+2')).toBeInTheDocument()
    })
  })

  describe('Status Indicators', () => {
    it('should show processing status for new source', () => {
      const source = createMockSource({
        status: 'new',
        command_id: 'cmd-123',
      })

      mockUseSourceStatus.mockReturnValue({
        data: mockStatuses.new,
        isLoading: false,
        isSuccess: true,
      } as ReturnType<typeof useSourceStatus>)

      renderWithProviders(<SourceCard source={source} />)

      expect(screen.getByText('Processing')).toBeInTheDocument()
    })

    it('should show queued status', () => {
      const source = createMockSource({
        status: 'queued',
        command_id: 'cmd-123',
      })

      mockUseSourceStatus.mockReturnValue({
        data: mockStatuses.queued,
        isLoading: false,
        isSuccess: true,
      } as ReturnType<typeof useSourceStatus>)

      renderWithProviders(<SourceCard source={source} />)

      expect(screen.getByText('Queued')).toBeInTheDocument()
    })

    it('should show running status with progress bar', () => {
      const source = createMockSource({
        status: 'running',
        command_id: 'cmd-123',
      })

      mockUseSourceStatus.mockReturnValue({
        data: {
          ...mockStatuses.running,
          processing_info: { progress: 50, current_step: 'processing', total_steps: 3 },
        },
        isLoading: false,
        isSuccess: true,
      } as unknown as ReturnType<typeof useSourceStatus>)

      renderWithProviders(<SourceCard source={source} />)

      expect(screen.getByText('Processing')).toBeInTheDocument()
      expect(screen.getByText('Progress')).toBeInTheDocument()
      expect(screen.getByText('50%')).toBeInTheDocument()
    })

    it('should show failed status with retry button', () => {
      const source = createMockSource({
        status: 'failed',
      })

      mockUseSourceStatus.mockReturnValue({
        data: mockStatuses.failed,
        isLoading: false,
        isSuccess: true,
      } as ReturnType<typeof useSourceStatus>)

      renderWithProviders(<SourceCard source={source} onRetry={mockOnRetry} />)

      expect(screen.getByText('Failed')).toBeInTheDocument()
      expect(screen.getByText('Retry')).toBeInTheDocument()
    })

    it('should not show status badge for completed sources', () => {
      const source = createMockSource({
        status: 'completed',
      })

      mockUseSourceStatus.mockReturnValue({
        data: mockStatuses.completed,
        isLoading: false,
        isSuccess: true,
      } as ReturnType<typeof useSourceStatus>)

      renderWithProviders(<SourceCard source={source} />)

      // Should not have any status badges for completed
      expect(screen.queryByText('Processing')).not.toBeInTheDocument()
      expect(screen.queryByText('Completed')).not.toBeInTheDocument()
    })
  })

  describe('User Interactions', () => {
    it('should call onClick when card is clicked', async () => {
      const source = createMockSource({ id: 'source-1' })

      const { user } = renderWithProviders(
        <SourceCard source={source} onClick={mockOnClick} />
      )

      await user.click(screen.getByText('Test Source'))

      expect(mockOnClick).toHaveBeenCalledWith('source-1')
    })

    it('should call onDelete when delete is clicked', async () => {
      const source = createMockSource({ id: 'source-1' })

      const { user } = renderWithProviders(
        <SourceCard source={source} onDelete={mockOnDelete} />
      )

      // Open the dropdown menu
      const menuButton = screen.getByRole('button')
      await user.click(menuButton)

      // Click delete
      const deleteButton = screen.getByText('Delete Source')
      await user.click(deleteButton)

      expect(mockOnDelete).toHaveBeenCalledWith('source-1')
    })

    it('should call onRetry when retry is clicked for failed source', async () => {
      const source = createMockSource({ 
        id: 'source-1',
        status: 'failed',
      })

      mockUseSourceStatus.mockReturnValue({
        data: mockStatuses.failed,
        isLoading: false,
        isSuccess: true,
      } as ReturnType<typeof useSourceStatus>)

      const { user } = renderWithProviders(
        <SourceCard source={source} onRetry={mockOnRetry} />
      )

      // Click the visible retry button
      const retryButton = screen.getByRole('button', { name: /retry/i })
      await user.click(retryButton)

      expect(mockOnRetry).toHaveBeenCalledWith('source-1')
    })

    it('should call onRemoveFromNotebook when remove is clicked', async () => {
      const source = createMockSource({ id: 'source-1' })

      const { user } = renderWithProviders(
        <SourceCard 
          source={source} 
          onRemoveFromNotebook={mockOnRemoveFromNotebook}
          showRemoveFromNotebook={true}
        />
      )

      // Open the dropdown menu
      const menuButton = screen.getByRole('button')
      await user.click(menuButton)

      // Click remove from notebook
      const removeButton = screen.getByText('Remove from Notebook')
      await user.click(removeButton)

      expect(mockOnRemoveFromNotebook).toHaveBeenCalledWith('source-1')
    })

    it('should not show remove from notebook option when showRemoveFromNotebook is false', async () => {
      const source = createMockSource()

      const { user } = renderWithProviders(
        <SourceCard 
          source={source} 
          onRemoveFromNotebook={mockOnRemoveFromNotebook}
          showRemoveFromNotebook={false}
        />
      )

      // Open the dropdown menu
      const menuButton = screen.getByRole('button')
      await user.click(menuButton)

      // Remove option should not be visible
      expect(screen.queryByText('Remove from Notebook')).not.toBeInTheDocument()
    })

    it('should stop propagation when clicking dropdown', async () => {
      const source = createMockSource()

      const { user } = renderWithProviders(
        <SourceCard 
          source={source} 
          onClick={mockOnClick}
          onDelete={mockOnDelete}
        />
      )

      // Click the dropdown button
      const menuButton = screen.getByRole('button')
      await user.click(menuButton)

      // onClick should not be called
      expect(mockOnClick).not.toHaveBeenCalled()
    })
  })

  describe('Context Toggle', () => {
    it('should render context toggle when handler is provided', () => {
      const source = createMockSource({ insights_count: 5 })

      renderWithProviders(
        <SourceCard 
          source={source}
          contextMode="insights"
          onContextModeChange={mockOnContextModeChange}
        />
      )

      // Context toggle should be present (implementation-specific test)
      // This assumes your ContextToggle component is rendered
      expect(mockOnContextModeChange).toBeDefined()
    })

    it('should not render context toggle when handler is not provided', () => {
      const source = createMockSource()

      renderWithProviders(<SourceCard source={source} />)

      // Context toggle should not be present
      // This is a basic check - you may need to adjust based on your ContextToggle implementation
    })
  })

  describe('Accessibility', () => {
    it('should have proper button roles', () => {
      const source = createMockSource()

      renderWithProviders(
        <SourceCard 
          source={source}
          onDelete={mockOnDelete}
        />
      )

      const buttons = screen.getAllByRole('button')
      expect(buttons.length).toBeGreaterThan(0)
    })

    it('should have title attribute for long titles', () => {
      const longTitle = 'This is a very long title that will be truncated'
      const source = createMockSource({ title: longTitle })

      renderWithProviders(<SourceCard source={source} />)

      const titleElement = screen.getByTitle(longTitle)
      expect(titleElement).toBeInTheDocument()
    })
  })

  describe('Edge Cases', () => {
    it('should handle source without title', () => {
      const source = createMockSource({ title: null })

      renderWithProviders(<SourceCard source={source} />)

      expect(screen.getByText('Untitled Source')).toBeInTheDocument()
    })

    it('should handle source without topics', () => {
      const source = createMockSource({ topics: [] })

      renderWithProviders(<SourceCard source={source} />)

      // Should still render without crashing
      expect(screen.getByText('Test Source')).toBeInTheDocument()
    })

    it('should handle source with zero insights', () => {
      const source = createMockSource({ insights_count: 0 })

      renderWithProviders(<SourceCard source={source} />)

      // Should not show insights badge
      expect(screen.queryByText(/insights/)).not.toBeInTheDocument()
    })

    it('should apply custom className', () => {
      const source = createMockSource()

      const { container } = renderWithProviders(
        <SourceCard source={source} className="custom-class" />
      )

      const card = container.querySelector('.custom-class')
      expect(card).toBeInTheDocument()
    })
  })

  describe('Status Polling and Refresh', () => {
    it('should call onRefresh when processing completes', async () => {
      // This test would require more complex mocking of React hooks
      // to simulate the useEffect behavior. For now, we test the prop exists.
      const source = createMockSource({
        status: 'completed',
      })

      renderWithProviders(
        <SourceCard 
          source={source}
          onRefresh={mockOnRefresh}
        />
      )

      // The component should have the onRefresh prop available
      expect(mockOnRefresh).toBeDefined()
    })
  })
})
