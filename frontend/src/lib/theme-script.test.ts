import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { directionScript } from '@/lib/theme-script'

// Store original localStorage
const originalLocalStorage = global.localStorage

beforeEach(() => {
  vi.clearAllMocks()
  // Reset localStorage mock
  global.localStorage = {
    ...originalLocalStorage,
    getItem: vi.fn(),
    setItem: vi.fn(),
    removeItem: vi.fn(),
    clear: vi.fn(),
  }
  vi.restoreAllMocks()
  document.documentElement.dir = 'ltr'
  document.documentElement.lang = 'en-US'
})

afterEach(() => {
  global.localStorage = originalLocalStorage
  document.documentElement.dir = 'ltr'
  document.documentElement.lang = 'en-US'
})

function runScript() {
  eval(directionScript)
}

describe('directionScript', () => {
  describe('RTL locales', () => {
    it('sets rtl for ar-YE', () => {
      vi.mocked(localStorage.getItem).mockReturnValue('ar-YE')
      runScript()
      expect(document.documentElement.dir).toBe('rtl')
      expect(document.documentElement.lang).toBe('ar-YE')
    })
    
    it('sets rtl for he-IL', () => {
      vi.mocked(localStorage.getItem).mockReturnValue('he-IL')
      runScript()
      expect(document.documentElement.dir).toBe('rtl')
      expect(document.documentElement.lang).toBe('he-IL')
    })
  })

  describe('LTR locales', () => {
    it('sets ltr for en-US', () => {
      vi.mocked(localStorage.getItem).mockReturnValue('en-US')
      runScript()
      expect(document.documentElement.dir).toBe('ltr')
      expect(document.documentElement.lang).toBe('en-US')
    })
  })

  describe('Fallback', () => {
    it('falls back to navigator.language', () => {
      vi.mocked(localStorage.getItem).mockReturnValue(null)
      vi.stubGlobal('navigator', { language: 'ar-YE' })
      runScript()
      expect(document.documentElement.dir).toBe('rtl')
      expect(document.documentElement.lang).toBe('ar-YE')
      vi.unstubAllGlobals()
    })
  })
})