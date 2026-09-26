import { render, screen, fireEvent, act, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
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

import { i18nEvents, I18N_LANGUAGE_CHANGE_END } from '@/lib/i18n-events'

const renderRadioGroup = async (locale = 'en-US', props = {}) => {
  const i18n = getI18n()
  
  await act(async () => {
    await i18n.changeLanguage(locale)
    i18nEvents.dispatchEvent(new CustomEvent(I18N_LANGUAGE_CHANGE_END, { detail: { language: locale } }))
  })

  return render(
    <I18nProvider>
      <RadioGroup {...props} data-testid="radio-group" dir={locale.startsWith('ar') ? 'rtl' : 'ltr'}>
        <RadioGroupItem value="option1" id="option1" aria-label="Option 1" />
        <RadioGroupItem value="option2" id="option2" aria-label="Option 2" />
        <RadioGroupItem value="option3" id="option3" aria-label="Option 3" />
      </RadioGroup>
    </I18nProvider>
  )
}

describe('RadioGroup RTL', () => {
  describe('LTR (English)', () => {
    it('ArrowRight moves to next item', async () => {
      await renderRadioGroup('en-US', { defaultValue: 'option1' })
      const firstItem = screen.getByRole('radio', { name: /Option 1/i })
      firstItem.focus()
      fireEvent.keyDown(firstItem, { key: 'ArrowRight', code: 'ArrowRight', bubbles: true })
      
      const secondItem = screen.getByRole('radio', { name: /Option 2/i })
      await waitFor(() => expect(secondItem).toBeChecked())
    })
  })

  describe('RTL (Arabic)', () => {
    it('ArrowRight moves to previous item (cycles to last)', async () => {
      await renderRadioGroup('ar-YE', { defaultValue: 'option1' })
      const firstItem = screen.getByRole('radio', { name: /Option 1/i })
      firstItem.focus()
      fireEvent.keyDown(firstItem, { key: 'ArrowRight', code: 'ArrowRight', bubbles: true })
      
      const thirdItem = screen.getByRole('radio', { name: /Option 3/i })
      await waitFor(() => expect(thirdItem).toBeChecked())
    })

    it('ArrowLeft moves to next item', async () => {
      await renderRadioGroup('ar-YE', { defaultValue: 'option1' })
      const firstItem = screen.getByRole('radio', { name: /Option 1/i })
      firstItem.focus()
      fireEvent.keyDown(firstItem, { key: 'ArrowLeft', code: 'ArrowLeft', bubbles: true })
      
      const secondItem = screen.getByRole('radio', { name: /Option 2/i })
      await waitFor(() => expect(secondItem).toBeChecked())
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