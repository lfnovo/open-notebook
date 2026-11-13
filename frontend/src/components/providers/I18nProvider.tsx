'use client'

import React, { useEffect, useLayoutEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { DirectionProvider } from '@radix-ui/react-direction'
import '@/lib/i18n'
import { languageToDirection } from '@/lib/language-resolution'
import { LanguageLoadingOverlay } from '@/components/common/LanguageLoadingOverlay'

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [mounted, setMounted] = useState(false)
  const { i18n, ready } = useTranslation()
  const language = i18n.resolvedLanguage || i18n.language || 'en-US'
  const direction = languageToDirection(language)

  useLayoutEffect(() => {
    if (!ready) return
    // Describe the language actually rendered, including translation fallbacks.
    document.documentElement.lang = language
    document.documentElement.dir = direction
  }, [language, direction, ready])

  useEffect(() => {
    setMounted(true)
  }, [])

  // The server cannot read the saved preference. Render the same neutral
  // placeholder on the server and first client pass; hidden children would
  // still hydrate with mismatched translations and Radix direction.
  if (!mounted || !ready) return null

  return (
    // Radix controls and portals use context, not the document's dir attribute.
    <DirectionProvider dir={direction}>
      <LanguageLoadingOverlay />
      {children}
    </DirectionProvider>
  )
}
