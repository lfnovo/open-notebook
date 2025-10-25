/**
 * @jest-environment jsdom
 */

import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { 
  useSources, 
  useSource, 
  useCreateSource, 
  useUpdateSource,
  useDeleteSource,
  useSourceStatus,
  useRetrySource
} from '@/lib/hooks/use-sources'
import { sourcesApi } from '@/lib/api/sources'
import { 
  createMockSource, 
  createMockCreateSourceRequest,
  createMockUpdateSourceRequest,
  mockSources,
  mockStatuses,
} from '@/__mocks__/mock-data'
import React from 'react'
import { vi } from 'vitest'

// Mock the API module
vi.mock('@/lib/api/sources')

// Mock the toast hook
const mockToast = vi.fn()
vi.mock('@/lib/hooks/use-toast', () => ({
  useToast: () => ({
    toast: mockToast,
  }),
}))

describe('use-sources hooks', () => {
  let queryClient: QueryClient

  // Helper to wrap hooks with QueryClient provider
  const createWrapper = () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    )
    return wrapper
  }

  beforeEach(() => {
    // Create a fresh QueryClient for each test
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })
    
    // Clear all mocks
  vi.clearAllMocks()
  })

  afterEach(() => {
    // Clean up
    queryClient.clear()
  })

  describe('useSources', () => {
    it('should fetch sources for a notebook', async () => {
      const notebookId = 'notebook-1'
      const mockData = mockSources.multiple
      
      // Mock the API call
  ;(sourcesApi.list as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockData)

      const { result } = renderHook(
        () => useSources(notebookId),
        { wrapper: createWrapper() }
      )

      // Initially loading
      expect(result.current.isLoading).toBe(true)

      // Wait for the query to resolve
      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      // Check the data
      expect(result.current.data).toEqual(mockData)
      expect(sourcesApi.list).toHaveBeenCalledWith({ notebook_id: notebookId })
    })

    it('should not fetch if notebookId is undefined', () => {
  ;(sourcesApi.list as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([])

      const { result } = renderHook(
        () => useSources(undefined),
        { wrapper: createWrapper() }
      )

      // Should not call the API
      expect(result.current.isLoading).toBe(false)
      expect(result.current.data).toBeUndefined()
      expect(sourcesApi.list).not.toHaveBeenCalled()
    })

    it('should handle API errors gracefully', async () => {
      const notebookId = 'notebook-1'
      const error = new Error('Network error')
      
  ;(sourcesApi.list as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(error)

      const { result } = renderHook(
        () => useSources(notebookId),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })

      expect(result.current.error).toBe(error)
    })

    it('should refetch when notebookId changes', async () => {
      const mockData1 = [createMockSource({ id: 'source-1' })]
      const mockData2 = [createMockSource({ id: 'source-2' })]
      
      ;(sourcesApi.list as unknown as ReturnType<typeof vi.fn>)
        .mockResolvedValueOnce(mockData1)
        .mockResolvedValueOnce(mockData2)

      const { result, rerender } = renderHook(
        ({ notebookId }) => useSources(notebookId),
        {
          wrapper: createWrapper(),
          initialProps: { notebookId: 'notebook-1' },
        }
      )

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })
      expect(result.current.data).toEqual(mockData1)

      // Change the notebook ID
      rerender({ notebookId: 'notebook-2' })

      await waitFor(() => {
        expect(result.current.data).toEqual(mockData2)
      })

      expect(sourcesApi.list).toHaveBeenCalledTimes(2)
    })
  })

  describe('useSource', () => {
    it('should fetch a single source by ID', async () => {
      const sourceId = 'source-1'
      const mockData = createMockSource({ id: sourceId })
      
  ;(sourcesApi.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockData)

      const { result } = renderHook(
        () => useSource(sourceId),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(result.current.data).toEqual(mockData)
      expect(sourcesApi.get).toHaveBeenCalledWith(sourceId)
    })
  })

  describe('useCreateSource', () => {
    it('should create a source successfully', async () => {
      const mockRequest = createMockCreateSourceRequest()
      const mockResponse = createMockSource()
      
  ;(sourcesApi.create as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse)

      const { result } = renderHook(
        () => useCreateSource(),
        { wrapper: createWrapper() }
      )

      // Trigger the mutation
      result.current.mutate(mockRequest)

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(sourcesApi.create).toHaveBeenCalledWith(mockRequest)
      expect(mockToast).toHaveBeenCalledWith({
        title: 'Success',
        description: 'Source added successfully',
      })
    })

    it('should show different message for async processing', async () => {
      const mockRequest = createMockCreateSourceRequest({ async_processing: true })
      const mockResponse = createMockSource()
      
  ;(sourcesApi.create as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse)

      const { result } = renderHook(
        () => useCreateSource(),
        { wrapper: createWrapper() }
      )

      result.current.mutate(mockRequest)

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(mockToast).toHaveBeenCalledWith({
        title: 'Source Queued',
        description: 'Source submitted for background processing. You can monitor progress in the sources list.',
      })
    })

    it('should handle creation errors', async () => {
      const mockRequest = createMockCreateSourceRequest()
      const error = new Error('Failed to create')
      
  ;(sourcesApi.create as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(error)

      const { result } = renderHook(
        () => useCreateSource(),
        { wrapper: createWrapper() }
      )

      result.current.mutate(mockRequest)

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })

      expect(mockToast).toHaveBeenCalledWith({
        title: 'Error',
        description: 'Failed to add source',
        variant: 'destructive',
      })
    })

    it('should invalidate relevant queries after success', async () => {
      const mockRequest = createMockCreateSourceRequest({ 
        notebooks: ['notebook-1', 'notebook-2'] 
      })
      const mockResponse = createMockSource()
      
      ;(sourcesApi.create as jest.Mock).mockResolvedValue(mockResponse)

      // Spy on invalidateQueries
  const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const { result } = renderHook(
        () => useCreateSource(),
        { wrapper: createWrapper() }
      )

      result.current.mutate(mockRequest)

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      // Verify queries were invalidated
      expect(invalidateSpy).toHaveBeenCalled()
    })
  })

  describe('useUpdateSource', () => {
    it('should update a source successfully', async () => {
      const sourceId = 'source-1'
      const mockRequest = createMockUpdateSourceRequest()
      const mockResponse = createMockSource({ id: sourceId })
      
  ;(sourcesApi.update as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse)

      const { result } = renderHook(
        () => useUpdateSource(),
        { wrapper: createWrapper() }
      )

      result.current.mutate({ id: sourceId, data: mockRequest })

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(sourcesApi.update).toHaveBeenCalledWith(sourceId, mockRequest)
      expect(mockToast).toHaveBeenCalledWith({
        title: 'Success',
        description: 'Source updated successfully',
      })
    })

    it('should handle update errors', async () => {
      const sourceId = 'source-1'
      const mockRequest = createMockUpdateSourceRequest()
      const error = new Error('Update failed')
      
  ;(sourcesApi.update as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(error)

      const { result } = renderHook(
        () => useUpdateSource(),
        { wrapper: createWrapper() }
      )

      result.current.mutate({ id: sourceId, data: mockRequest })

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })

      expect(mockToast).toHaveBeenCalledWith({
        title: 'Error',
        description: 'Failed to update source',
        variant: 'destructive',
      })
    })
  })

  describe('useDeleteSource', () => {
    it('should delete a source successfully', async () => {
      const sourceId = 'source-1'
      
  ;(sourcesApi.delete as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(undefined)

      const { result } = renderHook(
        () => useDeleteSource(),
        { wrapper: createWrapper() }
      )

      result.current.mutate(sourceId)

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(sourcesApi.delete).toHaveBeenCalledWith(sourceId)
      expect(mockToast).toHaveBeenCalledWith({
        title: 'Success',
        description: 'Source deleted successfully',
      })
    })

    it('should handle deletion errors', async () => {
      const sourceId = 'source-1'
      const error = new Error('Delete failed')
      
  ;(sourcesApi.delete as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(error)

      const { result } = renderHook(
        () => useDeleteSource(),
        { wrapper: createWrapper() }
      )

      result.current.mutate(sourceId)

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })

      expect(mockToast).toHaveBeenCalledWith({
        title: 'Error',
        description: 'Failed to delete source',
        variant: 'destructive',
      })
    })
  })

  describe('useSourceStatus', () => {
    it('should fetch source status', async () => {
      const sourceId = 'source-1'
      const mockStatus = mockStatuses.running
      
  ;(sourcesApi.status as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockStatus)

      const { result } = renderHook(
        () => useSourceStatus(sourceId),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(result.current.data).toEqual(mockStatus)
      expect(sourcesApi.status).toHaveBeenCalledWith(sourceId)
    })

    it('should not fetch when enabled is false', () => {
      const sourceId = 'source-1'
      
  ;(sourcesApi.status as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockStatuses.running)

      const { result } = renderHook(
        () => useSourceStatus(sourceId, false),
        { wrapper: createWrapper() }
      )

      expect(result.current.isLoading).toBe(false)
      expect(sourcesApi.status).not.toHaveBeenCalled()
    })

    it('should handle 404 errors without retrying', async () => {
      const sourceId = 'source-1'
      const error = { response: { status: 404 } }
      
  ;(sourcesApi.status as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(error)

      const { result } = renderHook(
        () => useSourceStatus(sourceId),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })

      // Should only be called once (no retries on 404)
      expect(sourcesApi.status).toHaveBeenCalledTimes(1)
    })
  })

  describe('useRetrySource', () => {
    it('should retry a failed source', async () => {
      const sourceId = 'source-1'
      const mockResponse = { success: true }
      
  ;(sourcesApi.retry as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse)

      const { result } = renderHook(
        () => useRetrySource(),
        { wrapper: createWrapper() }
      )

      result.current.mutate(sourceId)

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(sourcesApi.retry).toHaveBeenCalledWith(sourceId)
      expect(mockToast).toHaveBeenCalledWith({
        title: 'Source Retry Queued',
        description: 'The source has been requeued for processing.',
      })
    })

    it('should handle retry errors', async () => {
      const sourceId = 'source-1'
      const error = new Error('Retry failed')
      
  ;(sourcesApi.retry as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(error)

      const { result } = renderHook(
        () => useRetrySource(),
        { wrapper: createWrapper() }
      )

      result.current.mutate(sourceId)

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })

      expect(mockToast).toHaveBeenCalledWith({
        title: 'Retry Failed',
        description: 'Failed to retry source processing. Please try again.',
        variant: 'destructive',
      })
    })
  })
})
