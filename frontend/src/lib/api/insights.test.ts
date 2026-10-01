import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import apiClient from './client'
import { insightsApi } from './insights'

vi.mock('./client', () => ({
  default: {
    get: vi.fn(),
  },
}))

const mockGet = vi.mocked(apiClient.get)

describe('insightsApi.waitForCommand', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('keeps polling while a command remains pending', async () => {
    mockGet.mockImplementation(async () => ({
      data: {
        job_id: 'job-1',
        status: mockGet.mock.calls.length > 120 ? 'completed' : 'running',
      },
    }))

    await expect(
      insightsApi.waitForCommand('job-1', { intervalMs: 0 })
    ).resolves.toMatchObject({ status: 'completed' })
    expect(mockGet).toHaveBeenCalledTimes(121)
  })

  it('stops polling when aborted', async () => {
    const controller = new AbortController()
    mockGet.mockResolvedValue({ data: { job_id: 'job-1', status: 'running' } })

    const polling = insightsApi.waitForCommand('job-1', {
      intervalMs: 60_000,
      signal: controller.signal,
    })
    await vi.waitFor(() => expect(mockGet).toHaveBeenCalledTimes(1))

    controller.abort()

    await expect(polling).resolves.toBeNull()
    expect(mockGet).toHaveBeenCalledTimes(1)
  })

  it('stops polling when the job is unknown', async () => {
    mockGet.mockResolvedValue({ data: { job_id: 'job-1', status: 'unknown' } })

    await expect(
      insightsApi.waitForCommand('job-1', { intervalMs: 0 })
    ).resolves.toMatchObject({ status: 'unknown' })
    expect(mockGet).toHaveBeenCalledTimes(1)
  })

  it('stops polling when the job reports an error', async () => {
    const controller = new AbortController()
    mockGet.mockResolvedValue({ data: { job_id: 'job-1', status: 'error' } })
    const abort = setTimeout(() => controller.abort(), 20)

    const status = await insightsApi.waitForCommand('job-1', {
      intervalMs: 1,
      signal: controller.signal,
    })
    clearTimeout(abort)

    expect(status).toMatchObject({ status: 'error' })
    expect(mockGet).toHaveBeenCalledTimes(1)
  })

  it('stops after three consecutive status errors', async () => {
    const statusError = Object.assign(new Error('status unavailable'), {
      config: { headers: { Authorization: 'Bearer secret' } },
    })
    const errorLog = vi.spyOn(console, 'error').mockImplementation(() => undefined)
    mockGet.mockRejectedValue(statusError)

    await expect(
      insightsApi.waitForCommand('job-1', { intervalMs: 0 })
    ).resolves.toBeNull()
    expect(mockGet).toHaveBeenCalledTimes(3)
    expect(errorLog).toHaveBeenNthCalledWith(1, 'Error checking command status')
    expect(errorLog).toHaveBeenNthCalledWith(2, 'Error checking command status')
    expect(errorLog).toHaveBeenNthCalledWith(3, 'Error checking command status')
  })
})
