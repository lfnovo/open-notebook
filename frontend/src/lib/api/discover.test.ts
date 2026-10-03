import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('@/lib/api/client', () => ({
  default: { post: vi.fn() },
}))

import apiClient from '@/lib/api/client'
import { discoverApi } from './discover'
import type { DiscoverSourcesResponse } from '@/lib/types/discover'

describe('discoverApi.discoverSources', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('POSTs the payload to /sources/discover and returns the body', async () => {
    const payload: DiscoverSourcesResponse = {
      query: 'quantum computing',
      provider: 'tavily',
      notebook_id: 'notebook:1',
      created_count: 1,
      skipped_count: 0,
      results: [
        {
          title: 'A',
          url: 'https://a.example/',
          snippet: 'excerpt',
          score: 0.9,
          source_id: 'source:1',
          status: 'created',
          error: null,
        },
      ],
    }
    vi.mocked(apiClient.post).mockResolvedValue({ data: payload })

    const result = await discoverApi.discoverSources({
      query: 'quantum computing',
      notebook_id: 'notebook:1',
      limit: 5,
      dry_run: false,
    })

    expect(apiClient.post).toHaveBeenCalledWith('/sources/discover', {
      query: 'quantum computing',
      notebook_id: 'notebook:1',
      limit: 5,
      dry_run: false,
    })
    expect(result).toEqual(payload)
  })
})
