import { format } from 'date-fns'
import { zhCN, enUS, zhTW, ptBR, ja, it, fr, ru, bn, ca, es, de, pl, tr, Locale } from 'date-fns/locale'

/**
 * Mapping of language codes to date-fns locales.
 * Add new languages here as needed.
 */
const LOCALE_MAP: Record<string, Locale> = {
  'zh-CN': zhCN,
  'zh-TW': zhTW,
  'en-US': enUS,
  'pt-BR': ptBR,
  'ja-JP': ja,
  'it-IT': it,
  'fr-FR': fr,
  'ru-RU': ru,
  'bn-IN': bn,
  'ca-ES': ca,
  'es-ES': es,
  'de-DE': de,
  'pl-PL': pl,
  'tr-TR': tr,
}

/**
 * Get the date-fns locale for a given language code.
 * Falls back to English (en-US) if the language is not found.
 * 
 * @param language - The language code (e.g., 'zh-CN', 'en-US')
 * @returns The corresponding date-fns Locale object
 */
export function getDateLocale(language: string): Locale {
  return LOCALE_MAP[language] || enUS
}

/**
 * Format an absolute date and time in the UI language (not the browser's),
 * e.g. "Nov 14, 2026, 3:04 PM". Returns '' for a missing or invalid date.
 */
export function formatDateTime(value: string | number | Date | null | undefined, language: string): string {
  return formatWith(value, language, 'PPp')
}

/** Format an absolute date in the UI language, e.g. "Nov 14, 2026". */
export function formatDate(value: string | number | Date | null | undefined, language: string): string {
  return formatWith(value, language, 'PP')
}

function formatWith(value: string | number | Date | null | undefined, language: string, pattern: string): string {
  if (value === null || value === undefined || value === '') return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return format(date, pattern, { locale: getDateLocale(language) })
}
