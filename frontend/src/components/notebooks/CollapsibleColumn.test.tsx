import { render, screen, waitFor, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { CollapsibleColumn } from './CollapsibleColumn'
import { I18nProvider } from '@/components/providers/I18nProvider'
import * as i18nModule from '@/lib/i18n'
import { ChevronLeft } from 'lucide-react'

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

// Helper to set direction before render
const setDirection = (locale: string) => {
  const dir = locale.startsWith('ar') || locale.startsWith('he') || locale.startsWith('fa') || locale.startsWith('ur') ? 'rtl' : 'ltr'
  document.documentElement.dir = dir
  document.documentElement.lang = locale
}

const renderColumn = async (locale = 'en-US', props = {}) => {
  const i18n = getI18n()
  await i18n.changeLanguage(locale)
  setDirection(locale)
  return render(
    <I18nProvider>
      <CollapsibleColumn
        isCollapsed={false}
        onToggle={vi.fn()}
        collapsedIcon={ChevronLeft}
        collapsedLabel="Test Column"
        {...props}
      >
        <div data-testid="content">Column Content</div>
      </CollapsibleColumn>
    </I18nProvider>
  )
}

// Helper to wait for direction to be applied in component
const waitForDirection = async (expectedDir: 'ltr' | 'rtl') => {
  await waitFor(() => {
    expect(document.documentElement.dir).toBe(expectedDir)
  })
  // Wait for component to re-render with updated direction
  await act(async () => {
    await new Promise(resolve => setTimeout(resolve, 0))
  })
}

describe('CollapsibleColumn RTL', () => {
  describe('Expanded state', () => {
    it('renders content in LTR', async () => {
      await renderColumn('en-US')
      await waitForDirection('ltr')
      expect(document.documentElement.dir).toBe('ltr')
      expect(screen.getByTestId('content')).toHaveTextContent('Column Content')
    })

    it('renders content in RTL', async () => {
      await renderColumn('ar-YE')
      await waitForDirection('rtl')
      expect(document.documentElement.dir).toBe('rtl')
      expect(screen.getByTestId('content')).toHaveTextContent('Column Content')
    })
  })

  describe('Collapsed state', () => {
    it('shows collapsed label vertically in LTR', async () => {
      const i18n = getI18n()
      await i18n.changeLanguage('en-US')
      setDirection('en-US')
      render(
        <I18nProvider>
          <CollapsibleColumn
            isCollapsed={true}
            onToggle={vi.fn()}
            collapsedIcon={ChevronLeft}
            collapsedLabel="Test Column"
          >
            <div data-testid="content">Column Content</div>
          </CollapsibleColumn>
        </I18nProvider>
      )
      await waitForDirection('ltr')
      expect(document.documentElement.dir).toBe('ltr')
      const label = screen.getByText('Test Column')
      expect(label).toBeInTheDocument()
      expect(label).toHaveStyle({ writingMode: 'vertical-rl' })
    })

    it('shows collapsed label vertically in RTL', async () => {
      const i18n = getI18n()
      await i18n.changeLanguage('ar-YE')
      setDirection('ar-YE')
      render(
        <I18nProvider>
          <CollapsibleColumn
            isCollapsed={true}
            onToggle={vi.fn()}
            collapsedIcon={ChevronLeft}
            collapsedLabel="اختبار العمود"
          >
            <div data-testid="content">Column Content</div>
          </CollapsibleColumn>
        </I18nProvider>
      )
      await waitForDirection('rtl')
      expect(document.documentElement.dir).toBe('rtl')
      const label = screen.getByText('اختبار العمود')
      expect(label).toBeInTheDocument()
      expect(label).toHaveStyle({ writingMode: 'vertical-rl' })
    })

    it('shows collapsed label vertically for Hebrew', async () => {
      const i18n = getI18n()
      await i18n.changeLanguage('he-IL')
      setDirection('he-IL')
      render(
        <I18nProvider>
          <CollapsibleColumn
            isCollapsed={true}
            onToggle={vi.fn()}
            collapsedIcon={ChevronLeft}
            collapsedLabel="עמודה"
          >
            <div data-testid="content">Column Content</div>
          </CollapsibleColumn>
        </I18nProvider>
      )
      await waitForDirection('rtl')
      expect(document.documentElement.dir).toBe('rtl')
      const label = screen.getByText('עמודה')
      expect(label).toBeInTheDocument()
      expect(label).toHaveStyle({ writingMode: 'vertical-rl' })
    })

    it('shows collapsed label vertically for Persian', async () => {
      const i18n = getI18n()
      await i18n.changeLanguage('fa-IR')
      setDirection('fa-IR')
      render(
        <I18nProvider>
          <CollapsibleColumn
            isCollapsed={true}
            onToggle={vi.fn()}
            collapsedIcon={ChevronLeft}
            collapsedLabel="حجر"
          >
            <div data-testid="content">Column Content</div>
          </CollapsibleColumn>
        </I18nProvider>
      )
      await waitForDirection('rtl')
      expect(document.documentElement.dir).toBe('rtl')
      const label = screen.getByText('حجر')
      expect(label).toBeInTheDocument()
      expect(label).toHaveStyle({ writingMode: 'vertical-rl' })
    })

    it('shows collapsed label vertically for Urdu', async () => {
      const i18n = getI18n()
      await i18n.changeLanguage('ur-PK')
      setDirection('ur-PK')
      render(
        <I18nProvider>
          <CollapsibleColumn
            isCollapsed={true}
            onToggle={vi.fn()}
            collapsedIcon={ChevronLeft}
            collapsedLabel="عمود"
          >
            <div data-testid="content">Column Content</div>
          </CollapsibleColumn>
        </I18nProvider>
      )
      await waitForDirection('rtl')
      expect(document.documentElement.dir).toBe('rtl')
      const label = screen.getByText('عمود')
      expect(label).toBeInTheDocument()
      expect(label).toHaveStyle({ writingMode: 'vertical-rl' })
    })

    it('uses vertical-rl for CJK text regardless of direction', async () => {
      const i18n = getI18n()
      await i18n.changeLanguage('zh-CN')
      setDirection('zh-CN')
      render(
        <I18nProvider>
          <CollapsibleColumn
            isCollapsed={true}
            onToggle={vi.fn()}
            collapsedIcon={ChevronLeft}
            collapsedLabel="测试列"
          >
            <div data-testid="content">Column Content</div>
          </CollapsibleColumn>
        </I18nProvider>
      )
      await waitForDirection('ltr')
      expect(document.documentElement.dir).toBe('ltr')
      const label = screen.getByText('测试列')
      expect(label).toBeInTheDocument()
      expect(label).toHaveStyle({ writingMode: 'vertical-rl' })
    })
  })

  describe('Language switching', () => {
    it('updates writing mode when language changes from LTR to RTL', async () => {
      const { rerender } = await renderColumn('en-US', { isCollapsed: true, collapsedLabel: 'Test' })
      await waitForDirection('ltr')
      expect(document.documentElement.dir).toBe('ltr')

      const i18n = getI18n()
      await act(async () => {
        await i18n.changeLanguage('ar-YE')
      })
      setDirection('ar-YE')
      rerender(
        <I18nProvider>
          <CollapsibleColumn
            isCollapsed={true}
            onToggle={vi.fn()}
            collapsedIcon={ChevronLeft}
            collapsedLabel="اختبار"
          >
            <div data-testid="content">Column Content</div>
          </CollapsibleColumn>
        </I18nProvider>
      )
      await waitForDirection('rtl')
      const label = screen.getByText('اختبار')
      expect(label).toHaveStyle({ writingMode: 'vertical-rl' })
    })

    it('updates writing mode when language changes from RTL to LTR', async () => {
      const { rerender } = await renderColumn('ar-YE', { isCollapsed: true, collapsedLabel: 'اختبار' })
      await waitForDirection('rtl')
      expect(document.documentElement.dir).toBe('rtl')

      const i18n = getI18n()
      await act(async () => {
        await i18n.changeLanguage('en-US')
      })
      setDirection('en-US')
      rerender(
        <I18nProvider>
          <CollapsibleColumn
            isCollapsed={true}
            onToggle={vi.fn()}
            collapsedIcon={ChevronLeft}
            collapsedLabel="Test"
          >
            <div data-testid="content">Column Content</div>
          </CollapsibleColumn>
        </I18nProvider>
      )
      await waitForDirection('ltr')
      const label = screen.getByText('Test')
      expect(label).toHaveStyle({ writingMode: 'vertical-rl' })
    })
  })

  describe('Tooltip side', () => {
    it('shows tooltip on right in LTR', async () => {
      await renderColumn('en-US', { isCollapsed: true })
      await waitForDirection('ltr')
      expect(document.documentElement.dir).toBe('ltr')
    })

    it('shows tooltip on left in RTL', async () => {
      await renderColumn('ar-YE', { isCollapsed: true })
      await waitForDirection('rtl')
      expect(document.documentElement.dir).toBe('rtl')
    })
  })
})
