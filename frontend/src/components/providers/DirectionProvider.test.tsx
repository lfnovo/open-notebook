import { render, waitFor, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { DirectionProvider } from '@/components/providers/DirectionProvider'
import { I18nProvider } from '@/components/providers/I18nProvider'
import { i18nEvents, I18N_LANGUAGE_CHANGE_END } from '@/lib/i18n-events'
import * as i18nModule from '@/lib/i18n'

// Reset document.dir/lang before each test
beforeEach(() => {
  document.documentElement.dir = 'ltr'
  document.documentElement.lang = 'en-US'
  vi.clearAllMocks()
})

afterEach(() => {
  document.documentElement.dir = 'ltr'
  document.documentElement.lang = 'en-US'
})

// Helper to get i18n instance
function getI18n() {
  return i18nModule.default
}

describe('DirectionProvider', () => {
  const TestWrapper = ({ children }: { children: React.ReactNode }) => (
    <I18nProvider>
      <DirectionProvider>
        {children}
      </DirectionProvider>
    </I18nProvider>
  )

  describe('Initial direction', () => {
    it('sets dir=ltr and lang=en-US for English locale', async () => {
      render(<TestWrapper><></></TestWrapper>)
      // Wait for I18nProvider to mount and initialize
      await waitFor(() => expect(document.documentElement.lang).toBe('en-US'))
      expect(document.documentElement.dir).toBe('ltr')
    })

    it('sets dir=rtl and lang=ar-YE for Arabic locale', async () => {
      const i18n = getI18n()
      await i18n.changeLanguage('ar-YE')
      render(<TestWrapper><></></TestWrapper>)
      await waitFor(() => expect(document.documentElement.lang).toBe('ar-YE'))
      expect(document.documentElement.dir).toBe('rtl')
    })

    it('sets dir=rtl and lang=he-IL for Hebrew locale', async () => {
      const i18n = getI18n()
      await i18n.changeLanguage('he-IL')
      render(<TestWrapper><></></TestWrapper>)
      await waitFor(() => expect(document.documentElement.lang).toBe('he-IL'))
      expect(document.documentElement.dir).toBe('rtl')
    })

    it('sets dir=rtl and lang=fa-IR for Persian locale', async () => {
      const i18n = getI18n()
      await i18n.changeLanguage('fa-IR')
      render(<TestWrapper><></></TestWrapper>)
      await waitFor(() => expect(document.documentElement.lang).toBe('fa-IR'))
      expect(document.documentElement.dir).toBe('rtl')
    })

    it('sets dir=rtl and lang=ur-PK for Urdu locale', async () => {
      const i18n = getI18n()
      await i18n.changeLanguage('ur-PK')
      render(<TestWrapper><></></TestWrapper>)
      await waitFor(() => expect(document.documentElement.lang).toBe('ur-PK'))
      expect(document.documentElement.dir).toBe('rtl')
    })
  })

  describe('Language change LTR -> RTL', () => {
    it('updates dir and lang when language changes from en-US to ar-YE', async () => {
      const i18n = getI18n()
      // Start with English
      await i18n.changeLanguage('en-US')
      render(<TestWrapper><></></TestWrapper>)
      await waitFor(() => expect(document.documentElement.lang).toBe('en-US'))
      expect(document.documentElement.dir).toBe('ltr')

      // Change to Arabic
      await act(async () => {
        await i18n.changeLanguage('ar-YE')
      })
      await waitFor(() => expect(document.documentElement.lang).toBe('ar-YE'))
      expect(document.documentElement.dir).toBe('rtl')
    })

    it('updates dir and lang when language changes from en-US to he-IL', async () => {
      const i18n = getI18n()
      await i18n.changeLanguage('en-US')
      render(<TestWrapper><></></TestWrapper>)
      await waitFor(() => expect(document.documentElement.lang).toBe('en-US'))

      await act(async () => {
        await i18n.changeLanguage('he-IL')
      })
      await waitFor(() => expect(document.documentElement.lang).toBe('he-IL'))
      expect(document.documentElement.dir).toBe('rtl')
    })
  })

  describe('Language change RTL -> LTR', () => {
    it('updates dir and lang when language changes from ar-YE to en-US', async () => {
      const i18n = getI18n()
      await i18n.changeLanguage('ar-YE')
      render(<TestWrapper><></></TestWrapper>)
      await waitFor(() => expect(document.documentElement.lang).toBe('ar-YE'))
      expect(document.documentElement.dir).toBe('rtl')

      await act(async () => {
        await i18n.changeLanguage('en-US')
      })
      await waitFor(() => expect(document.documentElement.lang).toBe('en-US'))
      expect(document.documentElement.dir).toBe('ltr')
    })

    it('updates dir and lang when language changes from he-IL to en-US', async () => {
      const i18n = getI18n()
      await i18n.changeLanguage('he-IL')
      render(<TestWrapper><></></TestWrapper>)
      await waitFor(() => expect(document.documentElement.lang).toBe('he-IL'))

      await act(async () => {
        await i18n.changeLanguage('en-US')
      })
      await waitFor(() => expect(document.documentElement.lang).toBe('en-US'))
      expect(document.documentElement.dir).toBe('ltr')
    })
  })

  describe('Event-driven sync', () => {
    it('responds to i18n:language-change-end event', async () => {
      render(<TestWrapper><></></TestWrapper>)
      await waitFor(() => expect(document.documentElement.lang).toBe('en-US'))
      expect(document.documentElement.dir).toBe('ltr')

      // Fire the actual event that DirectionProvider listens to
      i18nEvents.dispatchEvent(
        new CustomEvent(I18N_LANGUAGE_CHANGE_END, { detail: { language: 'ar-YE' } })
      )

      await waitFor(() => expect(document.documentElement.lang).toBe('ar-YE'))
      expect(document.documentElement.dir).toBe('rtl')
    })

    it('responds to multiple sequential language changes', async () => {
      render(<TestWrapper><></></TestWrapper>)
      await waitFor(() => expect(document.documentElement.lang).toBe('en-US'))

      // en-US -> ar-YE
      i18nEvents.dispatchEvent(
        new CustomEvent(I18N_LANGUAGE_CHANGE_END, { detail: { language: 'ar-YE' } })
      )
      await waitFor(() => expect(document.documentElement.lang).toBe('ar-YE'))
      expect(document.documentElement.dir).toBe('rtl')

      // ar-YE -> he-IL
      i18nEvents.dispatchEvent(
        new CustomEvent(I18N_LANGUAGE_CHANGE_END, { detail: { language: 'he-IL' } })
      )
      await waitFor(() => expect(document.documentElement.lang).toBe('he-IL'))
      expect(document.documentElement.dir).toBe('rtl')

      // he-IL -> en-US
      i18nEvents.dispatchEvent(
        new CustomEvent(I18N_LANGUAGE_CHANGE_END, { detail: { language: 'en-US' } })
      )
      await waitFor(() => expect(document.documentElement.lang).toBe('en-US'))
      expect(document.documentElement.dir).toBe('ltr')
    })
  })

  describe('Cleanup', () => {
    it('unsubscribes from events on unmount', async () => {
      const { unmount } = render(<TestWrapper><></></TestWrapper>)
      await waitFor(() => expect(document.documentElement.lang).toBe('en-US'))

      // Fire event while mounted - should work
      i18nEvents.dispatchEvent(
        new CustomEvent(I18N_LANGUAGE_CHANGE_END, { detail: { language: 'ar-YE' } })
      )
      await waitFor(() => expect(document.documentElement.lang).toBe('ar-YE'))
      expect(document.documentElement.dir).toBe('rtl')

      // Unmount
      unmount()

      // Fire event after unmount - should NOT change direction
      i18nEvents.dispatchEvent(
        new CustomEvent(I18N_LANGUAGE_CHANGE_END, { detail: { language: 'en-US' } })
      )
      // Direction should remain RTL since listener was removed
      await waitFor(() => expect(document.documentElement.dir).toBe('rtl'))
    })

    it('does not create duplicate event listeners', async () => {
      const { rerender } = render(<TestWrapper><></></TestWrapper>)
      await waitFor(() => expect(document.documentElement.lang).toBe('en-US'))

      // Re-render multiple times
      rerender(<TestWrapper><></></TestWrapper>)
      rerender(<TestWrapper><></></TestWrapper>)
      rerender(<TestWrapper><></></TestWrapper>)
      await waitFor(() => expect(document.documentElement.lang).toBe('en-US'))

      // Fire event - should only trigger once per re-render cycle
      i18nEvents.dispatchEvent(
        new CustomEvent(I18N_LANGUAGE_CHANGE_END, { detail: { language: 'ar-YE' } })
      )
      await waitFor(() => expect(document.documentElement.lang).toBe('ar-YE'))
      expect(document.documentElement.dir).toBe('rtl')
    })
  })

  describe('External dir mutations', () => {
    it('keeps an externally-set dir until the next language change re-syncs from the locale', async () => {
      render(<TestWrapper><></></TestWrapper>)
      await waitFor(() => expect(document.documentElement.lang).toBe('en-US'))
      expect(document.documentElement.dir).toBe('ltr')

      // Directly mutate document.dir (simulating external change).
      // DirectionProvider only writes dir on mount and on language changes,
      // so the external value is left alone until the next sync.
      document.documentElement.dir = 'rtl'
      expect(document.documentElement.dir).toBe('rtl')

      i18nEvents.dispatchEvent(
        new CustomEvent(I18N_LANGUAGE_CHANGE_END, { detail: { language: 'he-IL' } })
      )
      await waitFor(() => expect(document.documentElement.lang).toBe('he-IL'))
      expect(document.documentElement.dir).toBe('rtl')

      i18nEvents.dispatchEvent(
        new CustomEvent(I18N_LANGUAGE_CHANGE_END, { detail: { language: 'en-US' } })
      )
      await waitFor(() => expect(document.documentElement.lang).toBe('en-US'))
      expect(document.documentElement.dir).toBe('ltr')
    })
  })
})