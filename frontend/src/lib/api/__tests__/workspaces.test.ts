import { describe, it, expect, vi, beforeEach } from 'vitest'
import { workspacesApi } from '../workspaces'
import { apiClient } from '../client'

vi.mock('../client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

describe('workspacesApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('list calls GET /workspaces', async () => {
    const mockResponse = { data: [] }
    vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

    const result = await workspacesApi.list()

    expect(apiClient.get).toHaveBeenCalledWith('/workspaces')
    expect(result).toBe(mockResponse)
  })

  it('create calls POST /workspaces with body', async () => {
    const body = { name: 'Test Workspace', description: 'A test', visibility: 'private' }
    const mockResponse = { data: { id: '1', ...body } }
    vi.mocked(apiClient.post).mockResolvedValue(mockResponse)

    const result = await workspacesApi.create(body)

    expect(apiClient.post).toHaveBeenCalledWith('/workspaces', body)
    expect(result).toBe(mockResponse)
  })

  it('delete calls DELETE /workspaces/{id}', async () => {
    const mockResponse = { data: null }
    vi.mocked(apiClient.delete).mockResolvedValue(mockResponse)

    const result = await workspacesApi.delete('ws-123')

    expect(apiClient.delete).toHaveBeenCalledWith('/workspaces/ws-123')
    expect(result).toBe(mockResponse)
  })

  it('get calls GET /workspaces/{id}', async () => {
    const mockResponse = { data: { id: 'ws-123', name: 'Test' } }
    vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

    const result = await workspacesApi.get('ws-123')

    expect(apiClient.get).toHaveBeenCalledWith('/workspaces/ws-123')
    expect(result).toBe(mockResponse)
  })

  it('getMembers calls GET /workspaces/{id}/members', async () => {
    const mockResponse = { data: [] }
    vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

    const result = await workspacesApi.getMembers('ws-123')

    expect(apiClient.get).toHaveBeenCalledWith('/workspaces/ws-123/members')
    expect(result).toBe(mockResponse)
  })

  it('inviteMember calls POST /workspaces/{id}/members', async () => {
    const body = { user_id: 'user-1', role: 'editor' }
    const mockResponse = { data: { id: 'm-1', ...body } }
    vi.mocked(apiClient.post).mockResolvedValue(mockResponse)

    const result = await workspacesApi.inviteMember('ws-123', body)

    expect(apiClient.post).toHaveBeenCalledWith('/workspaces/ws-123/members', body)
    expect(result).toBe(mockResponse)
  })

  it('removeMember calls DELETE /workspaces/{id}/members/{memberId}', async () => {
    const mockResponse = { data: null }
    vi.mocked(apiClient.delete).mockResolvedValue(mockResponse)

    const result = await workspacesApi.removeMember('ws-123', 'm-1')

    expect(apiClient.delete).toHaveBeenCalledWith('/workspaces/ws-123/members/m-1')
    expect(result).toBe(mockResponse)
  })
})
