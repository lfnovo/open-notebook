'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import { useTranslation as useI18nTranslation } from 'react-i18next'
import { useTranslation } from '@/lib/hooks/use-translation'
import { Loader2 } from 'lucide-react'

/**
 * LanguageLoadingOverlay - Shows a brief loading overlay during language switches
 * to provide a smoother UX and hide the flash caused by re-rendering.
 */
export function LanguageLoadingOverlay() {
  const { i18n } = useI18nTranslation()
  const { t } = useTranslation()
  const [isChanging, setIsChanging] = useState(false)

  const timerRef = useRef<NodeJS.Timeout | null>(null)

  const handleLanguageChanging = useCallback(() => {
    setIsChanging(true)
    
    // Safety timeout: ensure we don't get stuck forever
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => {
      setIsChanging(false)
      console.warn('i18n: Language switch timed out, forcing overlay removal')
    }, 2000)
  }, [])

  const handleLanguageChanged = useCallback(() => {
    // Add a small delay to ensure the UI has fully updated
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => {
      setIsChanging(false)
    }, 150)
  }, [])

  useEffect(() => {
    i18n.on('languageChanging', handleLanguageChanging)
    i18n.on('languageChanged', handleLanguageChanged)

    return () => {
      i18n.off('languageChanging', handleLanguageChanging)
      i18n.off('languageChanged', handleLanguageChanged)
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [i18n, handleLanguageChanging, handleLanguageChanged])

  if (!isChanging) return null

  return (
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-background/80 backdrop-blur-sm transition-opacity duration-200"
      style={{ opacity: isChanging ? 1 : 0 }}
      onClick={() => setIsChanging(false)} // Emergency override: click to hide
    >
      <div className="flex flex-col items-center gap-3">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="text-sm text-muted-foreground">{t('common.loading')}</span>
      </div>
    </div>
  )
}
