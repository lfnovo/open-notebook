import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act, waitFor } from '@testing-library/react'
import { Toaster } from '@/components/ui/sonner'
import { I18nProvider } from '@/components/providers/I18nProvider'
import * as i18nModule from '@/lib/i18n'

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

const renderToaster = async (locale = 'en-US') => {
  const i18n = getI18n()
  await i18n.changeLanguage(locale)
  
  // Dispatch custom event that components use to update direction
  act(() => {
    window.dispatchEvent(new CustomEvent('I18N_LANGUAGE_CHANGE_END'))
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
    expect(region.getAttribute('dir')).toBeNull()
  })

  it('renders with dir=rtl for Arabic locale', async () => {
    await renderToaster('ar-YE')
    const region = screen.getByRole('region')
    expect(region.getAttribute('dir')).toBe('rtl')
  })


  it('updates direction when language changes from LTR to RTL', async () => {
    await renderToaster('en-US')
    const region = screen.getByRole('region')
    expect(region.getAttribute('dir')).toBeNull()

    const i18n = getI18n()
    await act(async () => {
      await i18n.changeLanguage('ar-YE')
      window.dispatchEvent(new CustomEvent('I18N_LANGUAGE_CHANGE_END'))
    })

    await waitFor(() => {
      expect(region.getAttribute('dir')).toBe('rtl')
    })
  })

  it('updates direction when language changes from RTL to LTR', async () => {
    await renderToaster('ar-YE')
    const region = screen.getByRole('region')
    expect(region.getAttribute('dir')).toBe('rtl')

    const i18n = getI18n()
    await act(async () => {
      await i18n.changeLanguage('en-US')
      window.dispatchEvent(new CustomEvent('I18N_LANGUAGE_CHANGE_END'))
    })

    await waitFor(() => {
      expect(region.getAttribute('dir')).toBeNull()
    })
  })
})
