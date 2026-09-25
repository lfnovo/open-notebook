import { render, screen, waitFor, act, fireEvent } from '@testing-library/react'
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

const renderColumn = async (locale = 'en-US', props = {}) => {
  const i18n = getI18n()
  
  await act(async () => {
    await i18n.changeLanguage(locale)
    window.dispatchEvent(new CustomEvent('I18N_LANGUAGE_CHANGE_END'))
  })

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

describe('CollapsibleColumn RTL', () => {
  describe('Expanded state', () => {
    it('renders content in LTR', async () => {
      await renderColumn('en-US')
      expect(screen.getByTestId('content')).toHaveTextContent('Column Content')
    })

    it('renders content in RTL', async () => {
      await renderColumn('ar')
      expect(screen.getByTestId('content')).toHaveTextContent('Column Content')
    })
  })

  describe('Collapsed state', () => {
    it('shows collapsed label', async () => {
      await renderColumn('en-US', { isCollapsed: true, collapsedLabel: 'Test Column' })
      const label = screen.getByText('Test Column')
      expect(label).toBeInTheDocument()
    })
  })

  describe('Tooltip side', () => {
    it('shows tooltip on right in LTR', async () => {
      await renderColumn('en-US', { isCollapsed: true, collapsedLabel: 'Test Tooltip' })
      const button = screen.getByRole('button', { name: /Expand Test Tooltip/i })
      
      fireEvent.mouseEnter(button)
      const tooltipContent = await screen.findByText('Expand Test Tooltip')
      // @radix-ui/react-tooltip injects data-side on the closest tooltip content element
      expect(tooltipContent.closest('[data-side]')).toHaveAttribute('data-side', 'right')
    })

    it('shows tooltip on left in RTL', async () => {
      await renderColumn('ar', { isCollapsed: true, collapsedLabel: 'Test Tooltip' })
      const button = screen.getByRole('button', { name: /Expand Test Tooltip/i })
      
      fireEvent.mouseEnter(button)
      const tooltipContent = await screen.findByText('Expand Test Tooltip')
      expect(tooltipContent.closest('[data-side]')).toHaveAttribute('data-side', 'left')
    })
  })
})
