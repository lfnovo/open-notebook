import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act, waitFor } from '@testing-library/react'
import { Toaster } from '@/components/ui/sonner'
import { I18nProvider } from '@/components/providers/I18nProvider'
import * as i18nModule from '@/lib/i18n'

vi.mock('sonner', () => ({
  Toaster: vi.fn(({ dir }) => <div data-testid="mock-sonner" dir={dir} role="region" />)
}))

beforeEach(() => {
  document.documentElement.dir = 'ltr'
  document.documentElement.lang = 'en-US'
  vi.clearAllMocks()
})

afterEach(() => {
  document.documentElement.dir = 'ltr'
  document.documentElement.lang = 'en-US'
})

function getI18n() {
  return i18nModule.default
}

import { i18nEvents, I18N_LANGUAGE_CHANGE_END } from '@/lib/i18n-events'

const renderToaster = async (locale = 'en-US') => {
  const i18n = getI18n()
  await i18n.changeLanguage(locale)
  
  // Dispatch custom event that components use to update direction
  act(() => {
    i18nEvents.dispatchEvent(new CustomEvent(I18N_LANGUAGE_CHANGE_END, { detail: { language: locale } }))
  })

  return render(
    <I18nProvider>
      <Toaster />
    </I18nProvider>
  )
}

describe('Sonner RTL', () => {
  it('renders with dir=ltr for English locale', async () => {
    await renderToaster('en-US')
    const region = screen.getByRole('region')
    await waitFor(() => expect(region.getAttribute('dir')).toBe('ltr'))
  })

  it('renders with dir=rtl for Arabic locale', async () => {
    await renderToaster('ar-YE')
    const region = screen.getByRole('region')
    await waitFor(() => expect(region.getAttribute('dir')).toBe('rtl'))
  })


  it('updates direction when language changes from LTR to RTL', async () => {
    await renderToaster('en-US')
    const region = screen.getByRole('region')
    await waitFor(() => expect(region.getAttribute('dir')).toBe('ltr'))

    const i18n = getI18n()
    await act(async () => {
      await i18n.changeLanguage('ar-YE')
      i18nEvents.dispatchEvent(new CustomEvent(I18N_LANGUAGE_CHANGE_END, { detail: { language: 'ar-YE' } }))
    })

    await waitFor(() => {
      expect(region.getAttribute('dir')).toBe('rtl')
    })
  })

  it('updates direction when language changes from RTL to LTR', async () => {
    await renderToaster('ar-YE')
    const region = screen.getByRole('region')
    await waitFor(() => expect(region.getAttribute('dir')).toBe('rtl'))

    const i18n = getI18n()
    await act(async () => {
      await i18n.changeLanguage('en-US')
      i18nEvents.dispatchEvent(new CustomEvent(I18N_LANGUAGE_CHANGE_END, { detail: { language: 'en-US' } }))
    })

    await waitFor(() => {
      expect(region.getAttribute('dir')).toBe('ltr')
    })
  })
})
