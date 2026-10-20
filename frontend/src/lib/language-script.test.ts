import { createInstance } from 'i18next'
import LanguageDetector from 'i18next-browser-languagedetector'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { resources } from './locales'
import { languageScript } from './language-script'
import { languageDetection } from './language-detection'

beforeEach(() => {
  localStorage.clear()
  document.documentElement.lang = 'en-US'
  document.documentElement.dir = 'ltr'
  vi.spyOn(navigator, 'languages', 'get').mockReturnValue(['en-US'])
})

afterEach(() => {
  vi.restoreAllMocks()
  localStorage.clear()
  document.documentElement.lang = 'en-US'
  document.documentElement.dir = 'ltr'
})

async function detectLanguage() {
  // A fresh instance actually initializes from the browser detector, rather
  // than inheriting an already-selected language from the shared singleton.
  const instance = createInstance().use(LanguageDetector)
  await instance.init({
    resources,
    fallbackLng: 'en-US',
    detection: languageDetection,
  })
  return instance.resolvedLanguage
}

describe('document language before hydration', () => {
  it.each([
    ['zh-Hant', 'zh-TW'], ['zh-Hans', 'zh-CN'],
    ['zh-Hant-HK', 'zh-TW'], ['zh-Hans-SG', 'zh-CN'],
  ])('resolves Chinese script preference %s to %s on startup and detection', async (preference, language) => {
    for (const source of ['saved', 'browser']) {
      localStorage.clear()
      vi.spyOn(navigator, 'languages', 'get').mockReturnValue(source === 'browser' ? [preference] : ['en-US'])
      if (source === 'saved') localStorage.setItem('i18nextLng', preference)
      new Function(languageScript)()
      expect(document.documentElement.lang).toBe(language)
      expect(document.documentElement.dir).toBe('ltr')
      expect(await detectLanguage()).toBe(language)
    }
  })
  it.each([['ar', 'ar-SA', 'rtl'], ['fr', 'fr-FR', 'ltr']])(
    'uses the available translation for regionless %s', async (saved, language, direction) => {
      localStorage.setItem('i18nextLng', saved)
      new Function(languageScript)()
      expect(document.documentElement.lang).toBe(language)
      expect(document.documentElement.dir).toBe(direction)
      expect(await detectLanguage()).toBe(language)
    },
  )
  it.each([...Object.keys(resources), 'ar', 'fr', 'zh', 'ar-sa', 'ar-EG', 'he-IL', 'fr-CA', 'zh-Hant', 'ar-SA-x-test', 'invalid_language'])(
    'matches the real detector and translation fallback for saved %s', async (saved) => {
      localStorage.setItem('i18nextLng', saved)
      new Function(languageScript)()
      const beforeHydration = document.documentElement.lang
      const beforeDirection = document.documentElement.dir

      expect(beforeHydration).toBe(await detectLanguage())
      expect(beforeDirection).toBe(beforeHydration.startsWith('ar') ? 'rtl' : 'ltr')
    },
  )

  it('sets Arabic direction before any provider renders', () => {
    localStorage.setItem('i18nextLng', 'ar-SA')
    new Function(languageScript)()
    expect(document.documentElement).toHaveAttribute('lang', 'ar-SA')
    expect(document.documentElement).toHaveAttribute('dir', 'rtl')
  })

  it.each(['ar-SA', 'ar'])('uses browser preference %s when nothing is saved', async (language) => {
    vi.spyOn(navigator, 'languages', 'get').mockReturnValue([language, 'en-US'])
    new Function(languageScript)()
    expect(document.documentElement.lang).toBe(await detectLanguage())
    expect(document.documentElement.dir).toBe('rtl')
  })

  it('still applies the browser preference before hydration when storage is denied', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new DOMException('Storage unavailable', 'SecurityError')
    })
    vi.spyOn(navigator, 'languages', 'get').mockReturnValue(['ar-SA'])
    new Function(languageScript)()
    expect(document.documentElement.lang).toBe('ar-SA')
    expect(document.documentElement.dir).toBe('rtl')
  })
})
