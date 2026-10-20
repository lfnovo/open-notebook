// Keep this function self-contained: the head script embeds it before the
// client bundle loads so startup and the browser detector use the same rules.
export function resolveLanguage(preference: string, available: readonly string[]): string {
  try {
    const code = Intl.getCanonicalLocales(preference)[0]
    const parts = code.split('-')
    const script = parts.length > 2 && parts[parts.length - 2] !== 'x'
      ? parts.slice(0, -1).join('-') : ''
    // The registry uses regional tags for the two Chinese writing systems.
    const chineseVariant = parts[0] === 'zh'
      ? parts[1] === 'Hant' ? 'zh-TW' : parts[1] === 'Hans' ? 'zh-CN' : ''
      : ''
    const match = [code, script, chineseVariant, parts[0]].find(candidate => available.includes(candidate))
    if (match) return match

    // A bare language can use its only registered variant. Do not guess when
    // multiple variants exist (for example Simplified and Traditional Chinese).
    if (parts.length === 1) {
      const variants = available.filter(candidate => candidate.split('-')[0] === code)
      if (variants.length === 1) return variants[0]
    }
  } catch {
    // Invalid or unavailable preferences use the registered English fallback.
  }
  return 'en-US'
}

// Like resolveLanguage, this is embedded in the head script and must not
// reference module state. Only Arabic among the registered UI locales is RTL.
export function languageToDirection(language: string): 'rtl' | 'ltr' {
  return language.split('-')[0] === 'ar' ? 'rtl' : 'ltr'
}
