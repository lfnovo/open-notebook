import { useTranslation as useI18nTranslation } from 'react-i18next'
import { TranslationKeys } from '@/lib/locales'

export function useTranslation() {
  const { t, i18n } = useI18nTranslation()
  
  // High-performance Proxy to support t.section.key syntax with full type safety
  const translatedProxy = new Proxy({} as TranslationKeys, {
    get(_, section: string) {
      return new Proxy({}, {
        get(_, key: string) {
          return t(`${section}.${key}`)
        }
      })
    }
  })

  return { 
    t: translatedProxy, 
    i18n,
    language: i18n.language, 
    setLanguage: (lang: string) => i18n.changeLanguage(lang) 
  }
}
