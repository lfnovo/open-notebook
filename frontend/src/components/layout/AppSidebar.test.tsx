/* eslint-disable @typescript-eslint/no-explicit-any */
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { usePathname } from 'next/navigation'
import { AppSidebar } from './AppSidebar'
import { I18nProvider } from '@/components/providers/I18nProvider'
import { useSidebarStore } from '@/lib/stores/sidebar-store'
import * as i18nModule from '@/lib/i18n'

// Mock Tooltip components to avoid Radix UI async issues in tests
vi.mock('@/components/ui/tooltip', () => ({
  TooltipProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  Tooltip: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  TooltipTrigger: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  TooltipContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

// Reset document.dir/lang before each test
beforeEach(() => {
  document.documentElement.dir = 'ltr'
  document.documentElement.lang = 'en-US'
  vi.clearAllMocks()
  vi.mocked(usePathname).mockReturnValue('/')
})

afterEach(() => {
  document.documentElement.dir = 'ltr'
  document.documentElement.lang = 'en-US'
  vi.mocked(usePathname).mockReturnValue('/')
})

function getI18n() {
  return i18nModule.default
}

const renderSidebar = async (locale = 'en-US', props = {}) => {
  const i18n = getI18n()
  await i18n.changeLanguage(locale)
  return render(
    <I18nProvider>
      <AppSidebar {...props} />
    </I18nProvider>
  )
}

describe('AppSidebar', () => {
  afterEach(() => {
    vi.mocked(usePathname).mockReturnValue('/')
  })

  it('highlights only Models (not Settings) on the Models page', () => {
    vi.mocked(usePathname).mockReturnValue('/settings/models')

    const { container } = render(<AppSidebar />)

    const modelsButton = container.querySelector('a[href="/settings/models"] button')
    const settingsButton = container.querySelector('a[href="/settings"] button')

    expect(modelsButton?.className).toContain('font-semibold')
    expect(settingsButton?.className).toContain('font-medium')
    expect(settingsButton?.className).not.toContain('font-semibold')
  })

  it('renders correctly when expanded', () => {
    render(<AppSidebar />)

    // With mocked t() returning keys, check for translation key strings
    expect(screen.getByText('common.appName')).toBeDefined()
    expect(screen.getByText('navigation.sources')).toBeDefined()
    expect(screen.getByText('navigation.notebooks')).toBeDefined()
  })

  it('uses consistent spacing for expanded footer actions', () => {
    render(<AppSidebar />)

    const themeButton = screen.getByText('common.theme').closest('button')
    const languageButton = screen.getByText('common.language').closest('button')
    const signOutButton = screen.getByRole('button', { name: 'common.signOut' })

    expect(themeButton?.className.split(/\s+/)).toContain('px-3')

    for (const button of [themeButton, languageButton, signOutButton]) {
      expect(button?.className.split(/\s+/)).toContain('gap-2')
    }

    expect(themeButton?.querySelector(':scope > span.relative.size-4')).not.toBeNull()
    expect(signOutButton.className.split(/\s+/)).not.toContain('gap-3')
  })

  it('toggles collapse state when clicking handle', () => {
    const toggleCollapse = vi.fn()
    vi.mocked(useSidebarStore).mockReturnValue({
      isCollapsed: false,
      toggleCollapse,
    } as any)

    render(<AppSidebar />)

    fireEvent.click(screen.getByTestId('sidebar-toggle'))

    expect(toggleCollapse).toHaveBeenCalled()
  })

  it('shows collapsed view when isCollapsed is true', () => {
    vi.mocked(useSidebarStore).mockReturnValue({
      isCollapsed: true,
      toggleCollapse: vi.fn(),
    } as any)

    render(<AppSidebar />)

    // In collapsed mode, app name shouldn't be visible (as text)
    expect(screen.queryByText('common.appName')).toBeNull()
  })

  describe('RTL Support', () => {
    it('renders with dir=ltr for English locale', async () => {
      await renderSidebar('en-US')
      expect(document.documentElement.dir).toBe('ltr')
    })

    it('renders with dir=rtl for Arabic locale', async () => {
      await renderSidebar('ar-YE')
      expect(document.documentElement.dir).toBe('rtl')
    })

    it('renders with dir=rtl for Hebrew locale', async () => {
      await renderSidebar('he-IL')
      expect(document.documentElement.dir).toBe('rtl')
    })

    it('updates direction when language changes from LTR to RTL', async () => {
      const { rerender } = await renderSidebar('en-US')
      expect(document.documentElement.dir).toBe('ltr')

      const i18n = getI18n()
      await act(async () => {
        await i18n.changeLanguage('ar-YE')
      })
      rerender(
        <I18nProvider>
          <AppSidebar />
        </I18nProvider>
      )
      await waitFor(() => expect(document.documentElement.dir).toBe('rtl'))
    })

    it('updates direction when language changes from RTL to LTR', async () => {
      const { rerender } = await renderSidebar('ar-YE')
      expect(document.documentElement.dir).toBe('rtl')

      const i18n = getI18n()
      await act(async () => {
        await i18n.changeLanguage('en-US')
      })
      rerender(
        <I18nProvider>
          <AppSidebar />
        </I18nProvider>
      )
      await waitFor(() => expect(document.documentElement.dir).toBe('ltr'))
    })

    it('collapse button uses ChevronStart in both LTR and RTL', async () => {
      // Test with expanded sidebar
      vi.mocked(useSidebarStore).mockReturnValue({
        isCollapsed: false,
        toggleCollapse: vi.fn(),
      } as any)

      const { rerender } = await renderSidebar('en-US')
      const collapseButtonLTR = screen.getByTestId('sidebar-toggle')
      expect(collapseButtonLTR).toBeInTheDocument()

      const i18n = getI18n()
      await act(async () => {
        await i18n.changeLanguage('ar-YE')
      })
      rerender(
        <I18nProvider>
          <AppSidebar />
        </I18nProvider>
      )
      await waitFor(() => expect(document.documentElement.dir).toBe('rtl'))
      const collapseButtonRTL = screen.getByTestId('sidebar-toggle')
      expect(collapseButtonRTL).toBeInTheDocument()
    })
  })
})
