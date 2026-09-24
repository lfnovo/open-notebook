'use client'

import { useEffect } from 'react'
import { useTranslation as useI18nTranslation } from 'react-i18next'
import { DirectionProvider as RadixDirectionProvider } from '@radix-ui/react-direction'
import { i18nEvents, I18N_LANGUAGE_CHANGE_END } from '@/lib/i18n-events'
import { getDirection, LanguageCode } from '@/lib/locales'

export function DirectionProvider({ children }: { children: React.ReactNode }) {
  const { i18n } = useI18nTranslation()
  const currentLocale = i18n.language as LanguageCode
  const currentDir = getDirection(currentLocale)

  // Sync direction and lang on language change
  useEffect(() => {
    const handleLanguageChangeEnd = (event: CustomEvent<{ language: string }>) => {
      const locale = event.detail.language as LanguageCode
      const dir = getDirection(locale)
      document.documentElement.dir = dir
      document.documentElement.lang = locale
    }

    i18nEvents.addEventListener(I18N_LANGUAGE_CHANGE_END, handleLanguageChangeEnd as EventListener)

    return () => {
      i18nEvents.removeEventListener(I18N_LANGUAGE_CHANGE_END, handleLanguageChangeEnd as EventListener)
    }
  }, [])

  // Initial sync on mount (handles case where script ran but React hydration hasn't synced yet)
  useEffect(() => {
    document.documentElement.dir = currentDir
    document.documentElement.lang = currentLocale
  }, [currentDir, currentLocale])

  return (
    <RadixDirectionProvider dir={currentDir}>
      {children}
    </RadixDirectionProvider>
  )
}
