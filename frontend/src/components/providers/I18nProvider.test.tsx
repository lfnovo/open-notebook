import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import i18n from '@/lib/i18n'
import { arSA } from '@/lib/locales'
import { languageScript } from '@/lib/language-script'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { I18nProvider } from './I18nProvider'

beforeEach(async () => {
  await i18n.changeLanguage('en-US')
  document.documentElement.lang = 'en'
  document.documentElement.dir = 'ltr'
})

afterEach(() => {
  cleanup()
  i18n.removeResourceBundle('ar-EG', 'translation')
  localStorage.clear()
  document.documentElement.lang = 'en'
  document.documentElement.dir = 'ltr'
})

describe('I18nProvider document language', () => {
  it('gives Radix tabs RTL arrow navigation and restores LTR after switching', async () => {
    await i18n.changeLanguage('ar-SA')
    render(
      <I18nProvider>
        <Tabs defaultValue="sources">
          <TabsList>
            <TabsTrigger value="sources">Sources</TabsTrigger>
            <TabsTrigger value="notes">Notes</TabsTrigger>
            <TabsTrigger value="chat">Chat</TabsTrigger>
          </TabsList>
        </Tabs>
      </I18nProvider>,
    )
    const sources = screen.getByRole('tab', { name: 'Sources' })
    const notes = screen.getByRole('tab', { name: 'Notes' })
    expect(sources.closest('[data-slot="tabs"]')).toHaveAttribute('dir', 'rtl')
    act(() => { sources.focus() })
    fireEvent.keyDown(sources, { key: 'ArrowLeft' })
    await waitFor(() => expect(notes).toHaveFocus())
    fireEvent.keyDown(notes, { key: 'ArrowRight' })
    await waitFor(() => expect(sources).toHaveFocus())

    await act(async () => { await i18n.changeLanguage('en-US') })
    expect(sources.closest('[data-slot="tabs"]')).toHaveAttribute('dir', 'ltr')
    fireEvent.keyDown(sources, { key: 'ArrowRight' })
    await waitFor(() => expect(notes).toHaveFocus())
  })

  it('applies a saved Arabic language on mount without visiting Settings', async () => {
    localStorage.setItem('i18nextLng', 'ar-SA')
    // The head script runs before the provider or the language detector mounts.
    new Function(languageScript)()
    expect(document.documentElement).toHaveAttribute('lang', 'ar-SA')
    expect(document.documentElement).toHaveAttribute('dir', 'rtl')
    // Omitting the argument uses the real browser detector's saved preference.
    await i18n.changeLanguage()
    expect(i18n.language).toBe('ar-SA')

    // Verify the provider actively reapplies metadata, independently of the
    // earlier bootstrap script assertions.
    document.documentElement.lang = 'en-US'
    document.documentElement.dir = 'ltr'
    render(<I18nProvider><main>Notebook</main></I18nProvider>)

    expect(document.documentElement).toHaveAttribute('lang', 'ar-SA')
    expect(document.documentElement).toHaveAttribute('dir', 'rtl')
  })

  it('updates metadata before descendant passive effects on mount and switching', async () => {
    const observations: string[][] = []
    function MetadataProbe() {
      const { i18n: instance } = useTranslation()
      const renderedLanguage = instance.resolvedLanguage!
      useEffect(() => {
        observations.push([
          renderedLanguage,
          document.documentElement.lang,
          document.documentElement.dir,
        ])
      }, [renderedLanguage])
      return <main>{instance.t('common.language')}</main>
    }

    await i18n.changeLanguage('ar-SA')
    render(<I18nProvider><MetadataProbe /></I18nProvider>)
    for (const language of ['fr-FR', 'ar-SA', 'en-US']) {
      await act(async () => { await i18n.changeLanguage(language) })
    }

    expect(observations).toHaveLength(4)
    expect(observations.map(([language]) => language)).toEqual(['ar-SA', 'fr-FR', 'ar-SA', 'en-US'])
    for (const [rendered, lang, dir] of observations) {
      expect(lang).toBe(rendered)
      expect(dir).toBe(rendered.startsWith('ar') ? 'rtl' : 'ltr')
    }
  })

  it('updates direction and language when switching Arabic, French, and English', async () => {
    render(<I18nProvider><main>Notebook</main></I18nProvider>)

    for (const [language, direction] of [['ar-SA', 'rtl'], ['fr-FR', 'ltr'], ['en-US', 'ltr']]) {
      await act(async () => { await i18n.changeLanguage(language) })

      expect(document.documentElement).toHaveAttribute('lang', language)
      expect(document.documentElement).toHaveAttribute('dir', direction)
    }
  })

  it('supports another Arabic variant when its translations are available', async () => {
    // A fixture checks the Arabic prefix without exposing an untranslated locale.
    i18n.addResourceBundle('ar-EG', 'translation', arSA)
    await i18n.changeLanguage('ar-EG')

    render(<I18nProvider><main>Notebook</main></I18nProvider>)

    expect(document.documentElement).toHaveAttribute('lang', 'ar-EG')
    expect(document.documentElement).toHaveAttribute('dir', 'rtl')
  })

  it('uses the rendered English fallback for an unsupported RTL preference', async () => {
    await i18n.changeLanguage('he-IL')

    render(<I18nProvider><main>Notebook</main></I18nProvider>)

    expect(document.documentElement).toHaveAttribute('lang', 'en-US')
    expect(document.documentElement).toHaveAttribute('dir', 'ltr')
  })
})
