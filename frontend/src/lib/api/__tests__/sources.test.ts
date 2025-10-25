/**
 * @jest-environment jsdom
 */

import { sourcesApi } from '@/lib/api/sources'
import apiClient from '@/lib/api/client'
import { vi, expect } from 'vitest'
import { createMockSource, createMockCreateSourceRequest } from '@/__mocks__/mock-data'

// Mock the API client
vi.mock('@/lib/api/client', () => {
  return {
    default: {
      get: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
      patch: vi.fn(),
      delete: vi.fn(),
    },
  }
})

const mockedApiClient = apiClient as unknown as {
  get: ReturnType<typeof vi.fn>
  post: ReturnType<typeof vi.fn>
  put: ReturnType<typeof vi.fn>
  patch: ReturnType<typeof vi.fn>
  delete: ReturnType<typeof vi.fn>
}

describe('sourcesApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('list', () => {
    it('should fetch sources list', async () => {
      const mockData = [createMockSource(), createMockSource({ id: 'source-2' })]
      mockedApiClient.get.mockResolvedValue({ data: mockData })

      const result = await sourcesApi.list()

      expect(mockedApiClient.get).toHaveBeenCalledWith(
        '/sources',
        expect.objectContaining({ params: undefined })
      )
      expect(result).toEqual(mockData)
    })

    it('should fetch sources for a specific notebook', async () => {
      const mockData = [createMockSource()]
      mockedApiClient.get.mockResolvedValue({ data: mockData })

      const result = await sourcesApi.list({ notebook_id: 'notebook-1' })

      expect(mockedApiClient.get).toHaveBeenCalledWith('/sources', {
        params: { notebook_id: 'notebook-1' },
      })
      expect(result).toEqual(mockData)
    })

    it('should handle API errors', async () => {
      const error = new Error('Network error')
      mockedApiClient.get.mockRejectedValue(error)

      await expect(sourcesApi.list()).rejects.toThrow('Network error')
    })
  })

  describe('get', () => {
    it('should fetch a single source', async () => {
      const mockData = createMockSource({ id: 'source-1' })
      mockedApiClient.get.mockResolvedValue({ data: mockData })

      const result = await sourcesApi.get('source-1')

      expect(mockedApiClient.get).toHaveBeenCalledWith('/sources/source-1')
      expect(result).toEqual(mockData)
    })

    it('should handle 404 errors', async () => {
      const error = { response: { status: 404 } }
      mockedApiClient.get.mockRejectedValue(error)

      await expect(sourcesApi.get('nonexistent')).rejects.toEqual(error)
    })
  })

  describe('create', () => {
    it('should create a new source', async () => {
      const mockRequest = createMockCreateSourceRequest()
      const mockResponse = createMockSource()
      mockedApiClient.post.mockResolvedValue({ data: mockResponse })

      const result = await sourcesApi.create(mockRequest)

      expect(mockedApiClient.post).toHaveBeenCalledWith(
        '/sources',
        expect.any(FormData)
      )
      expect(result).toEqual(mockResponse)
    })

    it('should handle validation errors', async () => {
      const mockRequest = createMockCreateSourceRequest()
      const error = {
        response: {
          status: 400,
          data: { detail: 'Invalid URL format' },
        },
      }
      mockedApiClient.post.mockRejectedValue(error)

      await expect(sourcesApi.create(mockRequest)).rejects.toEqual(error)
    })
  })

  describe('update', () => {
    it('should update a source', async () => {
      const mockUpdate = { title: 'Updated Title' }
      const mockResponse = createMockSource({ title: 'Updated Title' })
  mockedApiClient.put.mockResolvedValue({ data: mockResponse })

  const result = await sourcesApi.update('source-1', mockUpdate)

      expect(mockedApiClient.put).toHaveBeenCalledWith('/sources/source-1', mockUpdate)
      expect(result).toEqual(mockResponse)
    })
  })

  describe('delete', () => {
    it('should delete a source', async () => {
      mockedApiClient.delete.mockResolvedValue({ data: undefined })

      await sourcesApi.delete('source-1')

      expect(mockedApiClient.delete).toHaveBeenCalledWith('/sources/source-1')
    })

    it('should handle errors when deleting', async () => {
      const error = {
        response: {
          status: 403,
          data: { detail: 'Permission denied' },
        },
      }
      mockedApiClient.delete.mockRejectedValue(error)

      await expect(sourcesApi.delete('source-1')).rejects.toEqual(error)
    })
  })

  describe('status', () => {
    it('should fetch source processing status', async () => {
      const mockStatus = {
        status: 'running',
        message: 'Processing source',
        processing_info: { progress: 50 },
      }
      mockedApiClient.get.mockResolvedValue({ data: mockStatus })

      const result = await sourcesApi.status('source-1')

      expect(mockedApiClient.get).toHaveBeenCalledWith('/sources/source-1/status')
      expect(result).toEqual(mockStatus)
    })
  })

  describe('retry', () => {
    it('should retry failed source processing', async () => {
      const mockResponse = { success: true }
      mockedApiClient.post.mockResolvedValue({ data: mockResponse })

      const result = await sourcesApi.retry('source-1')

      expect(mockedApiClient.post).toHaveBeenCalledWith('/sources/source-1/retry')
      expect(result).toEqual(mockResponse)
    })
  })

  describe('upload', () => {
    it('should upload a file', async () => {
      const mockFile = new File(['content'], 'test.pdf', { type: 'application/pdf' })
      const mockResponse = createMockSource({
        asset: { file_path: '/uploads/test.pdf' },
      })
      mockedApiClient.post.mockResolvedValue({ data: mockResponse })

      const result = await sourcesApi.upload(mockFile, 'notebook-1')

      expect(mockedApiClient.post).toHaveBeenCalledWith(
        '/sources',
        expect.any(FormData),
        expect.objectContaining({
          headers: { 'Content-Type': 'multipart/form-data' },
        })
      )
      expect(result).toEqual(mockResponse)
    })

    it('should handle upload errors', async () => {
      const mockFile = new File(['content'], 'test.pdf', { type: 'application/pdf' })
      const error = {
        response: {
          status: 413,
          data: { detail: 'File too large' },
        },
      }
      mockedApiClient.post.mockRejectedValue(error)

      await expect(sourcesApi.upload(mockFile, 'notebook-1')).rejects.toEqual(error)
    })
  })
})
