/**
 * Mock data and helpers for testing API interactions
 */

import { 
  SourceListResponse, 
  SourceStatusResponse,
  CreateSourceRequest,
  UpdateSourceRequest,
  NotebookResponse,
  CreateNotebookRequest,
  UpdateNotebookRequest,
} from '@/lib/types/api'

/**
 * Factory function to create mock source data with sensible defaults
 */
export function createMockSource(overrides?: Partial<SourceListResponse>): SourceListResponse {
  return {
    id: 'source-1',
    title: 'Test Source',
    insights_count: 5,
    topics: ['testing', 'typescript'],
    created: '2024-01-01T00:00:00Z',
    updated: '2024-01-01T00:00:00Z',
    embedded: true,
    embedded_chunks: 10,
    asset: {
      url: 'https://example.com/source',
    },
    ...overrides,
  }
}

/**
 * Factory for creating mock source status responses
 */
export function createMockSourceStatus(
  overrides?: Partial<SourceStatusResponse>
): SourceStatusResponse {
  return {
    status: 'completed',
    message: 'Processing completed successfully',
    processing_info: {
      progress: 100,
      current_step: 'completed',
      total_steps: 3,
    },
    ...overrides,
  }
}

/**
 * Factory for creating mock create source requests
 */
export function createMockCreateSourceRequest(
  overrides?: Partial<CreateSourceRequest>
): CreateSourceRequest {
  return {
    title: 'New Test Source',
    type: 'link',
    notebook_id: 'notebook-1',
    url: 'https://example.com/new-source',
    async_processing: false,
    ...overrides,
  }
}

/**
 * Factory for creating mock update source requests
 */
export function createMockUpdateSourceRequest(
  overrides?: Partial<UpdateSourceRequest>
): UpdateSourceRequest {
  return {
    title: 'Updated Source',
    ...overrides,
  }
}

/**
 * Mock source lists for different scenarios
 */
export const mockSources = {
  // Empty list
  empty: [] as SourceListResponse[],

  // Single source
  single: [createMockSource()],

  // Multiple sources with different statuses
  multiple: [
    createMockSource({ 
      id: 'source-1', 
      title: 'Completed Source',
      status: 'completed' 
    }),
    createMockSource({ 
      id: 'source-2', 
      title: 'Processing Source',
      status: 'running',
      command_id: 'cmd-123' 
    }),
    createMockSource({ 
      id: 'source-3', 
      title: 'Failed Source',
      status: 'failed' 
    }),
  ],

  // Sources with different types
  mixedTypes: [
    createMockSource({ 
      id: 'source-1',
      asset: { url: 'https://example.com' }
    }),
    createMockSource({ 
      id: 'source-2',
      asset: { file_path: '/uploads/test.pdf' }
    }),
    createMockSource({ 
      id: 'source-3',
      asset: null
    }),
  ],
}

/**
 * Mock status responses for different states
 */
export const mockStatuses = {
  new: createMockSourceStatus({
    status: 'new',
    message: 'Preparing to process',
    processing_info: { progress: 0, current_step: 'initializing', total_steps: 3 },
  }),
  queued: createMockSourceStatus({
    status: 'queued',
    message: 'Waiting in queue',
    processing_info: { progress: 0, current_step: 'queued', total_steps: 3 },
  }),
  running: createMockSourceStatus({
    status: 'running',
    message: 'Processing source',
    processing_info: { progress: 50, current_step: 'processing', total_steps: 3 },
  }),
  completed: createMockSourceStatus({
    status: 'completed',
    message: 'Processing completed successfully',
    processing_info: { progress: 100, current_step: 'completed', total_steps: 3 },
  }),
  failed: createMockSourceStatus({
    status: 'failed',
    message: 'Processing failed: Network error',
    processing_info: { progress: 30, current_step: 'failed', total_steps: 3 },
  }),
}

/**
 * Notebook mock factories
 */
export function createMockNotebook(
  overrides?: Partial<NotebookResponse>
): NotebookResponse {
  return {
    id: 'notebook-1',
    name: 'My Notebook',
    description: 'Test notebook description',
    archived: false,
    created: '2024-01-01T00:00:00Z',
    updated: '2024-01-02T00:00:00Z',
    source_count: 3,
    note_count: 2,
    ...overrides,
  }
}

export function createMockCreateNotebookRequest(
  overrides?: Partial<CreateNotebookRequest>
): CreateNotebookRequest {
  return {
    name: 'New Notebook',
    description: 'Optional description',
    ...overrides,
  }
}

export function createMockUpdateNotebookRequest(
  overrides?: Partial<UpdateNotebookRequest>
): UpdateNotebookRequest {
  return {
    name: 'Updated Notebook',
    description: 'Updated description',
    archived: false,
    ...overrides,
  }
}

export const mockNotebooks = {
  empty: [] as NotebookResponse[],
  single: [createMockNotebook()],
  multiple: [
    createMockNotebook({ id: 'nb-1', name: 'Alpha Research', updated: '2024-01-03T00:00:00Z' }),
    createMockNotebook({ id: 'nb-2', name: 'Beta Findings', updated: '2024-01-04T00:00:00Z' }),
    createMockNotebook({ id: 'nb-3', name: 'Gamma Notes', updated: '2024-01-05T00:00:00Z' }),
  ],
  archived: [
    createMockNotebook({ id: 'nb-9', name: 'Zeta Archive', archived: true }),
  ],
}
