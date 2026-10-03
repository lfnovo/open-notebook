import { resources } from './locales'
import { resolveLanguage } from './language-resolution'

export const languageDetection = {
  order: ['localStorage', 'navigator'],
  caches: ['localStorage'],
  convertDetectedLanguage: (preference: string) => resolveLanguage(preference, Object.keys(resources)),
}
