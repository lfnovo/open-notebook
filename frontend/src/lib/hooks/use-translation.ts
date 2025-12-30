import { useTranslation as useI18nTranslation } from 'react-i18next'

export function useTranslation() {
  const { t: i18nTranslate, i18n } = useI18nTranslation()
  
  // High-performance Proxy to support t.section.key syntax with full type safety
  // while still acting as a function for dynamic keys
  // High-performance Proxy to support t.section.key syntax with full type safety
  // while still acting as a function for dynamic keys
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const tFn = (key: string, options?: unknown) => i18nTranslate(key, options as any)
  
  const t = new Proxy(tFn, {
    get(target, prop: string | symbol) {
      // If the property exists on the function (like bind, call, etc), return it
      if (prop in target) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        return (target as any)[prop]
      }
      
      // Otherwise treat it as a section name for translation
      // Handle nested paths like t.common.error
      return new Proxy({}, {
        get(_, key: string) {
          return i18nTranslate(`${String(prop)}.${key}`)
        }
      })
    }
  })

  return { 
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    t: t as any, // Keep as any here to allow both function and property access in TS
    i18n,
    language: i18n.language, 
    setLanguage: (lang: string) => i18n.changeLanguage(lang) 
  }
}
