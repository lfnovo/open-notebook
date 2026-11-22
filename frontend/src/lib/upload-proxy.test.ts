import { describe, it, expect, vi } from 'vitest'
import {
  apiSharesPageOrigin,
  filesTooLargeForProxy,
  FRONTEND_PROXY_PROBE_PATH,
  uploadsUseFrontendProxy,
} from './upload-proxy'
import { PROXY_MAX_UPLOAD_BYTES, PROXY_MAX_UPLOAD_MB } from './upload-limits'
import { GET } from '../app/api/frontend-proxy/route'

const ORIGIN = 'https://notebook.example.com'

function fileOfSize(name: string, bytes: number): File {
  const file = new File(['x'], name)
  Object.defineProperty(file, 'size', { value: bytes })
  return file
}

function probeAnswering(status: number) {
  return vi.fn().mockResolvedValue(new Response('{}', { status }))
}

describe('apiSharesPageOrigin', () => {
  it('is true for an empty or relative API URL', () => {
    expect(apiSharesPageOrigin('', ORIGIN)).toBe(true)
    expect(apiSharesPageOrigin('/', ORIGIN)).toBe(true)
  })

  it("is true when the API URL is the frontend's own origin", () => {
    expect(apiSharesPageOrigin(ORIGIN, ORIGIN)).toBe(true)
    expect(apiSharesPageOrigin(`${ORIGIN}/`, ORIGIN)).toBe(true)
  })

  it('is false for another origin or a URL it cannot parse', () => {
    expect(apiSharesPageOrigin('https://notebook.example.com:5055', ORIGIN)).toBe(false)
    expect(apiSharesPageOrigin('http://localhost:5055', 'http://localhost:8502')).toBe(false)
    expect(apiSharesPageOrigin('http://', ORIGIN)).toBe(false)
  })
})

describe('uploadsUseFrontendProxy', () => {
  it('same origin and the frontend answers the probe: through the rewrite', async () => {
    const fetchFn = probeAnswering(200)
    expect(await uploadsUseFrontendProxy(ORIGIN, ORIGIN, fetchFn)).toBe(true)
    expect(fetchFn).toHaveBeenCalledWith(`${ORIGIN}${FRONTEND_PROXY_PROBE_PATH}`, { cache: 'no-store' })
  })

  it('same origin but /api/ routed straight to the API (it answers 404): direct', async () => {
    expect(await uploadsUseFrontendProxy(ORIGIN, ORIGIN, probeAnswering(404))).toBe(false)
  })

  it('probe fails: treated as direct, the API keeps the last word', async () => {
    const fetchFn = vi.fn().mockRejectedValue(new TypeError('network'))
    expect(await uploadsUseFrontendProxy('', ORIGIN, fetchFn)).toBe(false)
  })

  it('another origin: direct, without probing', async () => {
    const fetchFn = probeAnswering(200)
    expect(await uploadsUseFrontendProxy('http://localhost:5055', 'http://localhost:8502', fetchFn)).toBe(false)
    expect(fetchFn).not.toHaveBeenCalled()
  })
})

describe('frontend-proxy probe route', () => {
  it('reports the rewrite limit', async () => {
    expect(await GET().json()).toEqual({ maxUploadMb: PROXY_MAX_UPLOAD_MB })
  })
})

describe('filesTooLargeForProxy', () => {
  const big = fileOfSize('lecture.mp3', 150 * 1024 * 1024)
  const atLimit = fileOfSize('exact.mp3', PROXY_MAX_UPLOAD_BYTES)
  const justUnder = fileOfSize('under.mp3', PROXY_MAX_UPLOAD_BYTES - 2 * 1024 * 1024)
  const small = fileOfSize('notes.pdf', 2 * 1024 * 1024)

  it('keeps the limit in one place, matching next.config.ts', () => {
    expect(PROXY_MAX_UPLOAD_MB).toBe(100)
    expect(PROXY_MAX_UPLOAD_BYTES).toBe(100 * 1024 * 1024)
  })

  it('returns the files over the limit', () => {
    expect(filesTooLargeForProxy([big, justUnder, small])).toEqual([big])
  })

  it('a file of exactly the limit is rejected, the multipart body would exceed it', () => {
    expect(filesTooLargeForProxy([atLimit])).toEqual([atLimit])
  })
})
