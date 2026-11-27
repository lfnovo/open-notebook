import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('@/lib/api/client', () => ({
  default: { post: vi.fn(), get: vi.fn(), delete: vi.fn() },
}))

import apiClient from '@/lib/api/client'
import { artifactsApi } from './artifacts'

describe('artifactsApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('POSTs the payload to /artifacts and returns the ids', async () => {
    const payload = {
      command_id: 'command:1',
      artifact_id: 'generated_artifact:1',
      status: 'submitted',
    }
    vi.mocked(apiClient.post).mockResolvedValue({ data: payload })

    const result = await artifactsApi.generateArtifact({
      notebook_id: 'notebook:1',
      kind: 'report',
      formats: ['md'],
    })

    expect(apiClient.post).toHaveBeenCalledWith('/artifacts', {
      notebook_id: 'notebook:1',
      kind: 'report',
      formats: ['md'],
    })
    expect(result).toEqual(payload)
  })

  it('scopes GET /artifacts to a notebook when one is given', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: [] })

    await artifactsApi.listArtifacts('notebook:1')

    expect(apiClient.get).toHaveBeenCalledWith('/artifacts', {
      params: { notebook_id: 'notebook:1' },
    })
  })

  it('lists every artifact when no notebook is given', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: [] })

    await artifactsApi.listArtifacts()

    expect(apiClient.get).toHaveBeenCalledWith('/artifacts', { params: undefined })
  })

  it('DELETEs one artifact by id', async () => {
    vi.mocked(apiClient.delete).mockResolvedValue({ data: { message: 'ok' } })

    await artifactsApi.deleteArtifact('generated_artifact:1')

    expect(apiClient.delete).toHaveBeenCalledWith('/artifacts/generated_artifact:1')
  })
})
