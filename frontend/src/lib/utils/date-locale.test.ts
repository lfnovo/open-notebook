import { describe, expect, it } from 'vitest'
import { enUS, it as itLocale } from 'date-fns/locale'

import { languages } from '@/lib/locales'
import { formatDate, formatDateTime, getDateLocale } from './date-locale'

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

describe('formatDateTime / formatDate', () => {
  const date = new Date(2026, 10, 14, 15, 4)

  it('follows the UI language, not the browser locale', () => {
    expect(formatDate(date, 'en-US')).toBe('Nov 14, 2026')
    expect(formatDate(date, 'pt-BR')).toBe('14 nov 2026')
    expect(formatDateTime(date, 'en-US')).toBe('Nov 14, 2026, 3:04 PM')
    expect(formatDateTime(date, 'de-DE')).toContain('15:04')
  })

  it('returns an empty string for missing or invalid dates', () => {
    expect(formatDateTime(undefined, 'en-US')).toBe('')
    expect(formatDateTime('', 'en-US')).toBe('')
    expect(formatDate('not a date', 'en-US')).toBe('')
  })
})
