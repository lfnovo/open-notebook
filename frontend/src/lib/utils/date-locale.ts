import { zhCN, enUS, zhTW, ptBR, ja, ru, Locale } from 'date-fns/locale'

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
  'ru-RU': ru,
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
