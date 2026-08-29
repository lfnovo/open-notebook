import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { NextRequest } from 'next/server'
import { GET } from './route'

/**
 * Host and X-Forwarded-Proto are client-controlled. Behind a reverse proxy
 * that forwards them untrusted, an unvalidated value here could redirect
 * the browser's subsequent API traffic (including the auth bearer token)
 * to an attacker-chosen host - see lib/api/client.ts for how apiUrl is
 * used app-wide once fetched.
 */
describe('GET /config', () => {
  const originalEnv = process.env

  beforeEach(() => {
    process.env = { ...originalEnv }
    delete process.env.API_URL
    delete process.env.NEXT_PUBLIC_API_URL
  })

  afterEach(() => {
    process.env = originalEnv
  })

  function makeRequest(headers: Record<string, string>) {
    return new NextRequest('http://ignored.example/config', { headers })
  }

  it('uses API_URL env var when explicitly set, ignoring headers', async () => {
    process.env.API_URL = 'https://configured.example.com'
    const request = makeRequest({ host: 'evil.example.com', 'x-forwarded-proto': 'https' })

    const response = await GET(request)
    const body = await response.json()

    expect(body.apiUrl).toBe('https://configured.example.com')
  })

  it('uses a relative path for a named Host header (not a same-host :5055 guess)', async () => {
    const request = makeRequest({ host: 'notebook.example.com', 'x-forwarded-proto': 'https' })

    const response = await GET(request)
    const body = await response.json()

    expect(body.apiUrl).toBe('')
  })

  it('uses a relative path for a named Host header with a port', async () => {
    const request = makeRequest({ host: 'notebook.example.com:3000' })

    const response = await GET(request)
    const body = await response.json()

    expect(body.apiUrl).toBe('')
  })

  it('accepts a bare IPv4 Host header', async () => {
    const request = makeRequest({ host: '192.168.1.50' })

    const response = await GET(request)
    const body = await response.json()

    expect(body.apiUrl).toBe('http://192.168.1.50:5055')
  })

  it('never trusts an X-Forwarded-Proto value other than http/https, even for an IP-literal host', async () => {
    const request = makeRequest({ host: '192.168.1.50', 'x-forwarded-proto': 'javascript' })

    const response = await GET(request)
    const body = await response.json()

    expect(body.apiUrl).toBe('http://192.168.1.50:5055')
  })

  it('accepts a bracketed IPv6 literal Host header', async () => {
    const request = makeRequest({ host: '[2001:db8::1]' })

    const response = await GET(request)
    const body = await response.json()

    expect(body.apiUrl).toBe('http://[2001:db8::1]:5055')
  })

  it('strips the port from a bracketed IPv6 Host header and keeps the brackets', async () => {
    const request = makeRequest({ host: '[::1]:3000' })

    const response = await GET(request)
    const body = await response.json()

    expect(body.apiUrl).toBe('http://[::1]:5055')
  })

  it('falls back to a relative path for a bracketed IPv6 literal with trailing junk', async () => {
    const request = makeRequest({ host: '[::1]@evil.example.com' })

    const response = await GET(request)
    const body = await response.json()

    expect(body.apiUrl).toBe('')
  })

  it('falls back to a relative path for an unclosed IPv6 bracket', async () => {
    const request = makeRequest({ host: '[::1' })

    const response = await GET(request)
    const body = await response.json()

    expect(body.apiUrl).toBe('')
  })

  it('falls back to a relative path for a path-like payload inside IPv6 brackets', async () => {
    const request = makeRequest({ host: '[::1]/../../attacker' })

    const response = await GET(request)
    const body = await response.json()

    expect(body.apiUrl).toBe('')
  })

  it('falls back to a relative path for a Host header containing a path-like payload', async () => {
    const request = makeRequest({ host: 'evil.example.com/../../attacker' })

    const response = await GET(request)
    const body = await response.json()

    expect(body.apiUrl).toBe('')
  })

  it('falls back to a relative path for a Host header containing an @ (userinfo confusion)', async () => {
    const request = makeRequest({ host: 'legit.example.com@evil.example.com' })

    const response = await GET(request)
    const body = await response.json()

    expect(body.apiUrl).toBe('')
  })

  it('falls back to a relative path for a Host header with embedded whitespace', async () => {
    const request = makeRequest({ host: 'evil.example.com foo' })

    const response = await GET(request)
    const body = await response.json()

    expect(body.apiUrl).toBe('')
  })

  it('never trusts an X-Forwarded-Proto value other than http/https (named host, relative path)', async () => {
    const request = makeRequest({
      host: 'notebook.example.com',
      'x-forwarded-proto': 'javascript',
    })

    const response = await GET(request)
    const body = await response.json()

    expect(body.apiUrl).toBe('')
  })

  it('falls back to a relative path when no Host header is present', async () => {
    const request = makeRequest({})

    const response = await GET(request)
    const body = await response.json()

    expect(body.apiUrl).toBe('')
  })
})
