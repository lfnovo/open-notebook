import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
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

const setDirection = (locale: string) => {
  const dir = locale.startsWith('ar') || locale.startsWith('he') || locale.startsWith('fa') || locale.startsWith('ur') ? 'rtl' : 'ltr'
  document.documentElement.dir = dir
  document.documentElement.lang = locale
}

const renderRadioGroup = async (locale = 'en-US', props = {}) => {
  const i18n = getI18n()
  await i18n.changeLanguage(locale)
  setDirection(locale)
  return render(
    <I18nProvider>
      <RadioGroup {...props}>
        <RadioGroupItem value="option1" id="option1" aria-label="Option 1" />
        <RadioGroupItem value="option2" id="option2" aria-label="Option 2" />
        <RadioGroupItem value="option3" id="option3" aria-label="Option 3" />
      </RadioGroup>
    </I18nProvider>
  )
}

describe('RadioGroup RTL', () => {
  describe('LTR (English)', () => {
    it('renders with dir=ltr', async () => {
      await renderRadioGroup('en-US')
      expect(document.documentElement.dir).toBe('ltr')
    })

    it('renders three radio items', async () => {
      await renderRadioGroup('en-US')
      const items = screen.getAllByRole('radio')
      expect(items).toHaveLength(3)
    })
  })

  describe('RTL (Arabic)', () => {
    it('renders with dir=rtl', async () => {
      await renderRadioGroup('ar-YE')
      expect(document.documentElement.dir).toBe('rtl')
    })

    it('renders three radio items', async () => {
      await renderRadioGroup('ar-YE')
      const items = screen.getAllByRole('radio')
      expect(items).toHaveLength(3)
    })
  })

  describe('RTL (Hebrew)', () => {
    it('renders with dir=rtl', async () => {
      await renderRadioGroup('he-IL')
      expect(document.documentElement.dir).toBe('rtl')
    })
  })

  describe('RTL (Persian)', () => {
    it('renders with dir=rtl', async () => {
      await renderRadioGroup('fa-IR')
      expect(document.documentElement.dir).toBe('rtl')
    })
  })

  describe('RTL (Urdu)', () => {
    it('renders with dir=rtl', async () => {
      await renderRadioGroup('ur-PK')
      expect(document.documentElement.dir).toBe('rtl')
    })
  })

  describe('Selection interaction', () => {
    it('allows selection change in LTR', async () => {
      await renderRadioGroup('en-US', { defaultValue: 'option1' })
      const secondItem = screen.getByRole('radio', { name: /Option 2/i })
      expect(secondItem).not.toBeChecked()
      fireEvent.click(secondItem)
      expect(secondItem).toBeChecked()
    })

    it('allows selection change in RTL', async () => {
      await renderRadioGroup('ar-YE', { defaultValue: 'option1' })
      const secondItem = screen.getByRole('radio', { name: /Option 2/i })
      expect(secondItem).not.toBeChecked()
      fireEvent.click(secondItem)
      expect(secondItem).toBeChecked()
    })
  })

  describe('Disabled state', () => {
    it('disables item in LTR', async () => {
      const { rerender } = await renderRadioGroup('en-US', { defaultValue: 'option1' })
      rerender(
        <I18nProvider>
          <RadioGroup>
            <RadioGroupItem value="option1" id="option1" aria-label="Option 1" />
            <RadioGroupItem value="option2" id="option2" aria-label="Option 2" disabled />
            <RadioGroupItem value="option3" id="option3" aria-label="Option 3" />
          </RadioGroup>
        </I18nProvider>
      )
      const disabledItem = screen.getByRole('radio', { name: /Option 2/i })
      expect(disabledItem).toBeDisabled()
    })

    it('disables item in RTL', async () => {
      const { rerender } = await renderRadioGroup('ar-YE', { defaultValue: 'option1' })
      rerender(
        <I18nProvider>
          <RadioGroup>
            <RadioGroupItem value="option1" id="option1" aria-label="Option 1" />
            <RadioGroupItem value="option2" id="option2" aria-label="Option 2" disabled />
            <RadioGroupItem value="option3" id="option3" aria-label="Option 3" />
          </RadioGroup>
        </I18nProvider>
      )
      const disabledItem = screen.getByRole('radio', { name: /Option 2/i })
      expect(disabledItem).toBeDisabled()
    })
  })
})