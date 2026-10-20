import { act, cleanup, render } from '@testing-library/react'
import { renderToString } from 'react-dom/server'
import { hydrateRoot } from 'react-dom/client'
import { createInstance } from 'i18next'
import LanguageDetector from 'i18next-browser-languagedetector'
import { I18nextProvider, useTranslation } from 'react-i18next'
import { afterEach, expect, it, vi } from 'vitest'
import { resources } from '@/lib/locales'
import { languageScript } from '@/lib/language-script'
import { languageDetection } from '@/lib/language-detection'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { I18nProvider } from './I18nProvider'

afterEach(() => {
  cleanup()
  localStorage.clear()
  document.documentElement.lang = 'en-US'
  document.documentElement.dir = 'ltr'
})

it('preserves bootstrap metadata while detection is pending, then applies the detected locale', async () => {
  localStorage.setItem('i18nextLng', 'ar-SA')
  new Function(languageScript)()
  let finishDetection!: (language: string) => void
  const client = createInstance().use({
    type: 'languageDetector',
    async: true,
    detect(callback: (language: string) => void) { finishDetection = callback },
  })
  const initialized = client.init({
    resources, fallbackLng: 'en-US', react: { useSuspense: false },
  })
  const { container } = render(
    <I18nextProvider i18n={client}><I18nProvider><TranslatedTabs /></I18nProvider></I18nextProvider>
  )
  expect(container).toBeEmptyDOMElement()
  expect(document.documentElement).toHaveAttribute('lang', 'ar-SA')
  expect(document.documentElement).toHaveAttribute('dir', 'rtl')

  await act(async () => {
    finishDetection('fr-FR')
    await initialized
  })
  expect(container.querySelector('[role="tab"]')).toHaveTextContent(resources['fr-FR'].translation.sources.title)
  expect(container.querySelector('[data-slot="tabs"]')).toHaveAttribute('dir', 'ltr')
  expect(document.documentElement).toHaveAttribute('lang', 'fr-FR')
  expect(document.documentElement).toHaveAttribute('dir', 'ltr')
})

function TranslatedTabs() {
  const { t } = useTranslation()
  return (
    <Tabs defaultValue="sources">
      <TabsList>
        <TabsTrigger value="sources">{t('sources.title')}</TabsTrigger>
        <TabsTrigger value="notes">{t('common.notes')}</TabsTrigger>
      </TabsList>
    </Tabs>
  )
}

it.each(['ar-SA', 'ar'])('hydrates the empty server placeholder before mounting saved %s content', async (language) => {
  const server = createInstance()
  await server.init({ resources, lng: 'en-US', fallbackLng: 'en-US' })
  const serverMarkup = renderToString(
    <I18nextProvider i18n={server}><I18nProvider><TranslatedTabs /></I18nProvider></I18nextProvider>
  )
  localStorage.setItem('i18nextLng', language)
  new Function(languageScript)()
  const client = createInstance().use(LanguageDetector)
  await client.init({
    resources, fallbackLng: 'en-US',
    detection: languageDetection,
  })
  const container = document.createElement('div')
  container.innerHTML = serverMarkup
  document.body.appendChild(container)
  const onRecoverableError = vi.fn()
  let root: ReturnType<typeof hydrateRoot> | undefined
  try {
    await act(async () => {
      root = hydrateRoot(container,
        <I18nextProvider i18n={client}><I18nProvider><TranslatedTabs /></I18nProvider></I18nextProvider>,
        { onRecoverableError },
      )
    })
    expect(onRecoverableError).not.toHaveBeenCalled()
    // The empty SSR result is intentional: translated text and Radix controls
    // mount only after hydration, when the saved locale is ready.
    expect(serverMarkup).toBe('')
    expect(container.querySelector('[role="tab"]')).toHaveTextContent(resources['ar-SA'].translation.sources.title)
    expect(container.querySelector('[data-slot="tabs"]')).toHaveAttribute('dir', 'rtl')
    expect(document.documentElement).toHaveAttribute('lang', 'ar-SA')
    expect(document.documentElement).toHaveAttribute('dir', 'rtl')
  } finally {
    await act(async () => { root?.unmount() })
    container.remove()
  }
})
