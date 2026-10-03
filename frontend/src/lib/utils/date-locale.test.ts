import { format, formatDistanceStrict } from 'date-fns'
import { describe, expect, it } from 'vitest'
import { getDateLocale } from './date-locale'

describe('Saudi Arabic dates', () => {
  it('formats dates and distances with the Saudi locale', () => {
    const locale = getDateLocale('ar-SA')
    expect(locale.code).toBe('ar-SA')
    expect(format(new Date(2026, 8, 20), 'MMMM', { locale })).toBe('سبتمبر')
    expect(formatDistanceStrict(new Date(2026, 8, 20, 12, 2), new Date(2026, 8, 20, 12), { locale })).toBe('دقيقتين')
  })
})
