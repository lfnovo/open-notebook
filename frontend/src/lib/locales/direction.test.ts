import { describe, it, expect } from 'vitest'
import { getDirection, isRTLLocale } from './index'

describe('getDirection', () => {
  // Arabic variants
  it('returns rtl for ar-YE', () => expect(getDirection('ar-YE')).toBe('rtl'))
  it('returns rtl for ar-SA', () => expect(getDirection('ar-SA')).toBe('rtl'))
  it('returns rtl for ar', () => expect(getDirection('ar')).toBe('rtl'))
  it('returns rtl for AR (case insensitive)', () => expect(getDirection('AR')).toBe('rtl'))

  // Hebrew variants
  it('returns rtl for he-IL', () => expect(getDirection('he-IL')).toBe('rtl'))
  it('returns rtl for he', () => expect(getDirection('he')).toBe('rtl'))
  it('returns rtl for HE (case insensitive)', () => expect(getDirection('HE')).toBe('rtl'))

  // Persian variants
  it('returns rtl for fa-IR', () => expect(getDirection('fa-IR')).toBe('rtl'))
  it('returns rtl for fa', () => expect(getDirection('fa')).toBe('rtl'))
  it('returns rtl for FA (case insensitive)', () => expect(getDirection('FA')).toBe('rtl'))

  // Urdu variants
  it('returns rtl for ur-PK', () => expect(getDirection('ur-PK')).toBe('rtl'))
  it('returns rtl for ur', () => expect(getDirection('ur')).toBe('rtl'))
  it('returns rtl for UR (case insensitive)', () => expect(getDirection('UR')).toBe('rtl'))

  // LTR locales
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
  it('returns ltr for ca-ES', () => expect(getDirection('ca-ES')).toBe('ltr'))
  it('returns ltr for bn-IN', () => expect(getDirection('bn-IN')).toBe('ltr'))
  it('returns ltr for it-IT', () => expect(getDirection('it-IT')).toBe('ltr'))
  it('returns ltr for zh-TW', () => expect(getDirection('zh-TW')).toBe('ltr'))
})

describe('isRTLLocale', () => {
  it('returns true for ar-YE', () => expect(isRTLLocale('ar-YE')).toBe(true))
  it('returns true for he-IL', () => expect(isRTLLocale('he-IL')).toBe(true))
  it('returns true for fa-IR', () => expect(isRTLLocale('fa-IR')).toBe(true))
  it('returns true for ur-PK', () => expect(isRTLLocale('ur-PK')).toBe(true))
  it('returns false for en-US', () => expect(isRTLLocale('en-US')).toBe(false))
  it('returns false for zh-CN', () => expect(isRTLLocale('zh-CN')).toBe(false))
  it('returns false for fr-FR', () => expect(isRTLLocale('fr-FR')).toBe(false))
})