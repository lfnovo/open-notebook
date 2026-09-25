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

    it('sets dir=rtl and lang=ar for Arabic locale', async () => {
      const i18n = getI18n()
      await i18n.changeLanguage('ar')
      render(<TestWrapper><></></TestWrapper>)
      await waitFor(() => expect(document.documentElement.lang).toBe('ar'))
      expect(document.documentElement.dir).toBe('rtl')
    })
  })

  describe('Language change LTR -> RTL', () => {
    it('updates dir and lang when language changes from en-US to ar', async () => {
      const i18n = getI18n()
      // Start with English
      await i18n.changeLanguage('en-US')
      render(<TestWrapper><></></TestWrapper>)
      await waitFor(() => expect(document.documentElement.lang).toBe('en-US'))
      expect(document.documentElement.dir).toBe('ltr')

      // Change to Arabic
      await act(async () => {
        await i18n.changeLanguage('ar')
      })
      await waitFor(() => expect(document.documentElement.lang).toBe('ar'))
      expect(document.documentElement.dir).toBe('rtl')
    })
  })

  describe('Language change RTL -> LTR', () => {
    it('updates dir and lang when language changes from ar to en-US', async () => {
      const i18n = getI18n()
      await i18n.changeLanguage('ar')
      render(<TestWrapper><></></TestWrapper>)
      await waitFor(() => expect(document.documentElement.lang).toBe('ar'))
      expect(document.documentElement.dir).toBe('rtl')

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
        new CustomEvent(I18N_LANGUAGE_CHANGE_END, { detail: { language: 'ar' } })
      )

      await waitFor(() => expect(document.documentElement.lang).toBe('ar'))
      expect(document.documentElement.dir).toBe('rtl')
    })

    it('responds to multiple sequential language changes', async () => {
      render(<TestWrapper><></></TestWrapper>)
      await waitFor(() => expect(document.documentElement.lang).toBe('en-US'))

      // en-US -> ar
      i18nEvents.dispatchEvent(
        new CustomEvent(I18N_LANGUAGE_CHANGE_END, { detail: { language: 'ar' } })
      )
      await waitFor(() => expect(document.documentElement.lang).toBe('ar'))
      expect(document.documentElement.dir).toBe('rtl')

      // ar -> en-US
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
        new CustomEvent(I18N_LANGUAGE_CHANGE_END, { detail: { language: 'ar' } })
      )
      await waitFor(() => expect(document.documentElement.lang).toBe('ar'))
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
      const addEventListenerSpy = vi.spyOn(i18nEvents, 'addEventListener')
      const { rerender } = render(<TestWrapper><></></TestWrapper>)
      await waitFor(() => expect(document.documentElement.lang).toBe('en-US'))

      // Re-render multiple times
      rerender(<TestWrapper><></></TestWrapper>)
      rerender(<TestWrapper><></></TestWrapper>)
      rerender(<TestWrapper><></></TestWrapper>)
      await waitFor(() => expect(document.documentElement.lang).toBe('en-US'))

      expect(addEventListenerSpy).toHaveBeenCalledTimes(1) // initial mount only

      // Fire event - should only trigger once per re-render cycle
      i18nEvents.dispatchEvent(
        new CustomEvent(I18N_LANGUAGE_CHANGE_END, { detail: { language: 'ar' } })
      )
      await waitFor(() => expect(document.documentElement.lang).toBe('ar'))
      expect(document.documentElement.dir).toBe('rtl')
      
      addEventListenerSpy.mockRestore()
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
        new CustomEvent(I18N_LANGUAGE_CHANGE_END, { detail: { language: 'en-US' } })
      )
      await waitFor(() => expect(document.documentElement.lang).toBe('en-US'))
      expect(document.documentElement.dir).toBe('ltr')
    })
  })
})