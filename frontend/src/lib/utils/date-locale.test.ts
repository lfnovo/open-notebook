import { describe, expect, it } from 'vitest'
import { enUS, it as itLocale } from 'date-fns/locale'

import { languages } from '@/lib/locales'
import { getDateLocale } from './date-locale'

describe('getDateLocale', () => {
  it('formats Italian dates in Italian', () => {
    expect(getDateLocale('it-IT')).toBe(itLocale)
  })

  it('has a date locale for every registered language', () => {
    for (const { code } of languages) {
      if (code === 'en-US') continue
      expect(getDateLocale(code), code).not.toBe(enUS)
    }
  })

  it('falls back to English for unknown codes', () => {
    expect(getDateLocale('xx-XX')).toBe(enUS)
  })
})
