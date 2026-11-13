import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import i18n from '@/lib/i18n'
import { languages } from '@/lib/locales'
import { I18nProvider } from '@/components/providers/I18nProvider'
import { LanguageToggle } from './LanguageToggle'

vi.unmock('@/lib/hooks/use-translation')

beforeEach(async () => {
  await i18n.changeLanguage('en-US')
})

afterEach(() => {
  cleanup()
  localStorage.clear()
  document.documentElement.lang = 'en'
  document.documentElement.dir = 'ltr'
})

async function openMenu() {
  fireEvent.keyDown(screen.getByRole('button'), { key: 'ArrowDown' })
  await screen.findByRole('menu')
}

describe('LanguageToggle', () => {
  it('offers every registered language, including Arabic', async () => {
    render(<LanguageToggle />)
    await openMenu()

    expect(screen.getAllByRole('menuitem')).toHaveLength(languages.length)
    expect(screen.getByRole('menuitem', { name: 'العربية' })).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: 'Italiano' })).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: 'Français' })).toBeInTheDocument()
  })

  it('selects Arabic outside Settings and restores LTR when selecting French', async () => {
    render(<I18nProvider><LanguageToggle /></I18nProvider>)
    await openMenu()
    fireEvent.click(screen.getByRole('menuitem', { name: 'العربية' }))

    await waitFor(() => {
      expect(i18n.language).toBe('ar-SA')
      expect(document.documentElement).toHaveAttribute('lang', 'ar-SA')
      expect(document.documentElement).toHaveAttribute('dir', 'rtl')
    })

    await openMenu()
    expect(screen.getByRole('menu')).toHaveAttribute('dir', 'rtl')
    expect(screen.getByRole('menuitem', { name: 'العربية' })).toHaveClass('bg-accent')
    fireEvent.click(screen.getByRole('menuitem', { name: 'Français' }))

    await waitFor(() => {
      expect(i18n.language).toBe('fr-FR')
      expect(document.documentElement).toHaveAttribute('lang', 'fr-FR')
      expect(document.documentElement).toHaveAttribute('dir', 'ltr')
    })
    await openMenu()
    expect(screen.getByRole('menu')).toHaveAttribute('dir', 'ltr')
  })

  // he-IL has no bundle and resolves to en-US; the names must not depend on that.
  it.each(['fr-FR', 'ar-SA', 'he-IL'])('lists every language by its native name in the %s UI', async (language) => {
    await act(async () => { await i18n.changeLanguage(language) })
    render(<LanguageToggle />)
    await openMenu()

    expect(screen.getAllByRole('menuitem').map((item) => item.textContent)).toEqual(
      languages.map(({ label }) => label),
    )
  })

  it.each(['zh-TW', 'zh-Hant'])('keeps the Traditional Chinese selection distinct for %s', async (language) => {
    await act(async () => { await i18n.changeLanguage(language) })
    render(<LanguageToggle />)
    await openMenu()

    expect(screen.getByRole('menuitem', { name: '繁體中文' })).toHaveClass('bg-accent')
    expect(screen.getByRole('menuitem', { name: '简体中文' })).not.toHaveClass('bg-accent')
  })
})
