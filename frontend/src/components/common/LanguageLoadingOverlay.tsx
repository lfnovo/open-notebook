'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import { useTranslation as useI18nTranslation } from 'react-i18next'
import { Loader2 } from 'lucide-react'

/**
 * LanguageLoadingOverlay - Shows a brief loading overlay during language switches
 * to provide a smoother UX and hide the flash caused by re-rendering.
 * 
 * IMPORTANT: This component intentionally uses react-i18next directly instead of
 * our custom useTranslation hook to avoid Proxy-related issues during the
 * language change transition period.
 */
export function LanguageLoadingOverlay() {
  const { i18n, t } = useI18nTranslation()
  const [isChanging, setIsChanging] = useState(false)

  const timerRef = useRef<NodeJS.Timeout | null>(null)

  const handleLanguageChanging = useCallback(() => {
    console.log('[i18n] Language changing started')
    setIsChanging(true)
    
    // Safety timeout: ensure we don't get stuck forever (reduced to 1.5s for faster recovery)
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => {
      setIsChanging(false)
      console.warn('[i18n] Language switch timed out after 1.5s, forcing overlay removal')
    }, 1500)
  }, [])

  const handleLanguageChanged = useCallback((lng: string) => {
    console.log('[i18n] Language changed to:', lng)
    // Immediately hide the overlay on language change success
    if (timerRef.current) clearTimeout(timerRef.current)
    // Small delay to let React re-render with new translations
    timerRef.current = setTimeout(() => {
      setIsChanging(false)
    }, 100)
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

  // Use react-i18next's t() directly - this is safe during language transitions
  // because react-i18next handles the loading state internally
  const loadingText = t('common.loading', { defaultValue: '加载中...' })

  return (
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-background/80 backdrop-blur-sm transition-opacity duration-200"
      style={{ opacity: isChanging ? 1 : 0 }}
      onClick={() => {
        console.log('[i18n] Overlay clicked, forcing hide')
        setIsChanging(false)
      }}
    >
      <div className="flex flex-col items-center gap-3">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="text-sm text-muted-foreground">{loadingText}</span>
      </div>
    </div>
  )
}
