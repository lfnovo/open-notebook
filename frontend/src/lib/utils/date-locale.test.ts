import { format, formatDistanceStrict } from 'date-fns'
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

describe('Saudi Arabic dates', () => {
  it('formats dates and distances with the Saudi locale', () => {
    const locale = getDateLocale('ar-SA')
    expect(locale.code).toBe('ar-SA')
    expect(format(new Date(2026, 8, 20), 'MMMM', { locale })).toBe('سبتمبر')
    expect(formatDistanceStrict(new Date(2026, 8, 20, 12, 2), new Date(2026, 8, 20, 12), { locale })).toBe('دقيقتين')
  })
})
