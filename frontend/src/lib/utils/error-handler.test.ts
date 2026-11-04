import { describe, it, expect } from 'vitest'
import { AxiosError, AxiosHeaders, type InternalAxiosRequestConfig } from 'axios'
import { getLogSafeErrorMessage } from './error-handler'

const BEARER_TOKEN = 'Bearer secret-token'

/** Mirrors what the request interceptor leaves on a rejected request config. */
function axiosConfigWithAuth(): InternalAxiosRequestConfig {
  return {
    url: '/notebooks/nb:1/chat',
    method: 'post',
    baseURL: 'http://localhost:5055/api',
    headers: new AxiosHeaders({
      'Content-Type': 'application/json',
      Authorization: BEARER_TOKEN,
    }),
  } as InternalAxiosRequestConfig
}

function realAxiosError(status: number, detail: unknown): AxiosError {
  const config = axiosConfigWithAuth()
  return new AxiosError(
    `Request failed with status code ${status}`,
    'ERR_BAD_RESPONSE',
    config,
    { headers: config.headers },
    {
      status,
      statusText: 'Internal Server Error',
      data: { detail },
      headers: new AxiosHeaders(),
      config,
    },
  )
}

describe('getLogSafeErrorMessage', () => {
  it('never leaks the Authorization header of an axios error', () => {
    const result = getLogSafeErrorMessage(realAxiosError(500, 'Chat generation failed'))

    expect(result).not.toContain('secret-token')
    expect(result).not.toContain('Bearer')
    expect(result).not.toContain('Authorization')
    expect(result).toBe('HTTP 500: Chat generation failed')
  })

  it('never leaks the Authorization header of an axios-shaped error object', () => {
    const error = {
      isAxiosError: true,
      message: 'Request failed with status code 401',
      config: {
        url: '/notebooks',
        headers: { Authorization: BEARER_TOKEN },
      },
      response: { status: 401, data: { detail: 'Invalid password' } },
    }

    const result = getLogSafeErrorMessage(error)

    expect(result).not.toContain('secret-token')
    expect(result).not.toContain('Bearer')
    expect(result).not.toContain('Authorization')
    expect(result).toBe('HTTP 401: Invalid password')
  })

  it('prefixes the HTTP status when the axios error carries a response', () => {
    expect(getLogSafeErrorMessage(realAxiosError(404, 'Source not found'))).toBe(
      'HTTP 404: Source not found',
    )
  })

  it('omits the prefix for network errors and non-axios errors', () => {
    const networkError = new AxiosError('Network Error', 'ERR_NETWORK', axiosConfigWithAuth())

    expect(getLogSafeErrorMessage(networkError)).toBe('Network Error')
    expect(getLogSafeErrorMessage(new Error('boom'))).toBe('boom')
  })

  it('truncates to 200 characters by default, marking the cut', () => {
    const result = getLogSafeErrorMessage(realAxiosError(500, 'x'.repeat(5000)))

    expect(result).toHaveLength(200)
    expect(result.endsWith('...')).toBe(true)
    expect(result.startsWith('HTTP 500: xxx')).toBe(true)
  })

  it('truncates to a custom maxLength', () => {
    expect(getLogSafeErrorMessage('y'.repeat(50), 10)).toBe('yyyyyyy...')
    expect(getLogSafeErrorMessage('y'.repeat(50), 10)).toHaveLength(10)
  })

  it('leaves messages shorter than maxLength untouched', () => {
    expect(getLogSafeErrorMessage('short message', 200)).toBe('short message')
  })

  it('stays within maxLength even when it cannot fit the ellipsis', () => {
    expect(getLogSafeErrorMessage('y'.repeat(50), 2)).toHaveLength(2)
    expect(getLogSafeErrorMessage('y'.repeat(50), 0)).toBe('')
    expect(getLogSafeErrorMessage('y'.repeat(50), -5)).toBe('')
  })

  it('does not throw for any input shape', () => {
    const fallback = 'An unexpected error occurred'

    expect(getLogSafeErrorMessage(undefined)).toBe(fallback)
    expect(getLogSafeErrorMessage(null)).toBe(fallback)
    expect(getLogSafeErrorMessage({})).toBe(fallback)
    expect(getLogSafeErrorMessage(42)).toBe(fallback)
    expect(getLogSafeErrorMessage('plain string failure')).toBe('plain string failure')
    expect(getLogSafeErrorMessage({ detail: 'plain object detail' })).toBe('plain object detail')
  })

  it('falls back to the generic message when detail is not a string', () => {
    const fallback = 'An unexpected error occurred'

    expect(getLogSafeErrorMessage({ detail: { loc: ['body'], msg: 'invalid' } })).toBe(fallback)
    expect(getLogSafeErrorMessage(realAxiosError(422, [{ msg: 'invalid' }]))).toBe(
      `HTTP 422: ${fallback}`,
    )
  })
})
