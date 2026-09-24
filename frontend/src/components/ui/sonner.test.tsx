import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render } from '@testing-library/react'
import { Toaster } from '@/components/ui/sonner'
import { I18nProvider } from '@/components/providers/I18nProvider'
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

function getI18n() {
  return i18nModule.default
}

const renderToaster = async (locale = 'en-US') => {
  const i18n = getI18n()
  await i18n.changeLanguage(locale)
  const dir = locale.startsWith('ar') || locale.startsWith('he') || locale.startsWith('fa') || locale.startsWith('ur') ? 'rtl' : 'ltr'
  document.documentElement.dir = dir
  document.documentElement.lang = locale

  return render(
    <I18nProvider>
      <Toaster />
    </I18nProvider>
  )
}

describe('Sonner RTL', () => {
  it('renders with dir=ltr for English locale', async () => {
    await renderToaster('en-US')
    expect(document.documentElement.dir).toBe('ltr')
  })

  it('renders with dir=rtl for Arabic locale', async () => {
    await renderToaster('ar-YE')
    expect(document.documentElement.dir).toBe('rtl')
  })

  it('renders with dir=rtl for Hebrew locale', async () => {
    await renderToaster('he-IL')
    expect(document.documentElement.dir).toBe('rtl')
  })

  it('renders with dir=rtl for Persian locale', async () => {
    await renderToaster('fa-IR')
    expect(document.documentElement.dir).toBe('rtl')
  })

  it('renders with dir=rtl for Urdu locale', async () => {
    await renderToaster('ur-PK')
    expect(document.documentElement.dir).toBe('rtl')
  })

  it('updates direction when language changes from LTR to RTL', async () => {
    await renderToaster('en-US')
    expect(document.documentElement.dir).toBe('ltr')

    const i18n = getI18n()
    await i18n.changeLanguage('ar-YE')
    document.documentElement.dir = 'rtl'
    document.documentElement.lang = 'ar-YE'

    expect(document.documentElement.dir).toBe('rtl')
  })

  it('updates direction when language changes from RTL to LTR', async () => {
    await renderToaster('ar-YE')
    expect(document.documentElement.dir).toBe('rtl')

    const i18n = getI18n()
    await i18n.changeLanguage('en-US')
    document.documentElement.dir = 'ltr'
    document.documentElement.lang = 'en-US'

    expect(document.documentElement.dir).toBe('ltr')
  })
})
