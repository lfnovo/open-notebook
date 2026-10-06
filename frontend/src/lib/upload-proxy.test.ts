import { describe, it, expect } from 'vitest'
import { filesTooLargeForProxy, uploadsUseFrontendProxy } from './upload-proxy'
import { PROXY_MAX_UPLOAD_BYTES, PROXY_MAX_UPLOAD_MB } from './upload-limits'

const ORIGIN = 'https://notebook.example.com'

function fileOfSize(name: string, bytes: number): File {
  const file = new File(['x'], name)
  Object.defineProperty(file, 'size', { value: bytes })
  return file
}

describe('uploadsUseFrontendProxy', () => {
  it('is true for an empty or relative API URL (the /api/* rewrite)', () => {
    expect(uploadsUseFrontendProxy('', ORIGIN)).toBe(true)
    expect(uploadsUseFrontendProxy('/', ORIGIN)).toBe(true)
  })

  it("is true when the API URL is the frontend's own origin", () => {
    expect(uploadsUseFrontendProxy(ORIGIN, ORIGIN)).toBe(true)
    expect(uploadsUseFrontendProxy(`${ORIGIN}/`, ORIGIN)).toBe(true)
  })

  it('is false when the API is called directly', () => {
    expect(uploadsUseFrontendProxy('https://notebook.example.com:5055', ORIGIN)).toBe(false)
    expect(uploadsUseFrontendProxy('http://localhost:5055', 'http://localhost:8502')).toBe(false)
  })

  it('is false for a URL it cannot parse', () => {
    expect(uploadsUseFrontendProxy('http://', ORIGIN)).toBe(false)
  })
})

describe('filesTooLargeForProxy', () => {
  const big = fileOfSize('lecture.mp3', 150 * 1024 * 1024)
  const atLimit = fileOfSize('exact.mp3', PROXY_MAX_UPLOAD_BYTES)
  const small = fileOfSize('notes.pdf', 2 * 1024 * 1024)

  it('keeps the limit in one place, matching next.config.ts', () => {
    expect(PROXY_MAX_UPLOAD_MB).toBe(100)
    expect(PROXY_MAX_UPLOAD_BYTES).toBe(100 * 1024 * 1024)
  })

  it('through the rewrite: returns the files over the limit', () => {
    expect(filesTooLargeForProxy([big, atLimit, small], '', ORIGIN)).toEqual([big])
    expect(filesTooLargeForProxy([big], ORIGIN, ORIGIN)).toEqual([big])
  })

  it('direct to the API: returns nothing, the API answers with its own 413', () => {
    expect(filesTooLargeForProxy([big], 'http://localhost:5055', 'http://localhost:8502')).toEqual([])
  })
})
