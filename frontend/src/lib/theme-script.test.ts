import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { getDirection } from '@/lib/locales'

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
})

afterEach(() => {
  global.localStorage = originalLocalStorage
  document.documentElement.dir = 'ltr'
  document.documentElement.lang = 'en-US'
})

describe('directionScript logic (via getDirection)', () => {
  // The directionScript uses the same logic as getDirection
  // We test getDirection directly since it's the core logic

  describe('RTL locales', () => {
    it('returns rtl for ar-YE', () => expect(getDirection('ar-YE')).toBe('rtl'))
    it('returns rtl for ar-SA', () => expect(getDirection('ar-SA')).toBe('rtl'))
    it('returns rtl for ar', () => expect(getDirection('ar')).toBe('rtl'))
    it('returns rtl for he-IL', () => expect(getDirection('he-IL')).toBe('rtl'))
    it('returns rtl for he', () => expect(getDirection('he')).toBe('rtl'))
    it('returns rtl for fa-IR', () => expect(getDirection('fa-IR')).toBe('rtl'))
    it('returns rtl for fa', () => expect(getDirection('fa')).toBe('rtl'))
    it('returns rtl for ur-PK', () => expect(getDirection('ur-PK')).toBe('rtl'))
    it('returns rtl for ur', () => expect(getDirection('ur')).toBe('rtl'))
  })

  describe('LTR locales', () => {
    it('returns ltr for en-US', () => expect(getDirection('en-US')).toBe('ltr'))
    it('returns ltr for en', () => expect(getDirection('en')).toBe('ltr'))
    it('returns ltr for zh-CN', () => expect(getDirection('zh-CN')).toBe('ltr'))
    it('returns ltr for fr-FR', () => expect(getDirection('fr-FR')).toBe('ltr'))
    it('returns ltr for de-DE', () => expect(getDirection('de-DE')).toBe('ltr'))
    it('returns ltr for es-ES', () => expect(getDirection('es-ES')).toBe('ltr'))
    it('returns ltr for ja-JP', () => expect(getDirection('ja-JP')).toBe('ltr'))
    it('returns ltr for ko-KR', () => expect(getDirection('ko-KR')).toBe('ltr'))
    it('returns ltr for pt-BR', () => expect(getDirection('pt-BR')).toBe('ltr'))
    it('returns ltr for ru-RU', () => expect(getDirection('ru-RU')).toBe('ltr'))
    it('returns ltr for tr-TR', () => expect(getDirection('tr-TR')).toBe('ltr'))
    it('returns ltr for pl-PL', () => expect(getDirection('pl-PL')).toBe('ltr'))
  })

  describe('Case insensitivity', () => {
    it('handles uppercase locale codes', () => expect(getDirection('AR-YE')).toBe('rtl'))
    it('handles mixed case locale codes', () => expect(getDirection('Ar-Ye')).toBe('rtl'))
  })
})