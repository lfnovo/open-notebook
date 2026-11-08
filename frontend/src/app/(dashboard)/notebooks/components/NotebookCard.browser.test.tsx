import { act, cleanup, render } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createInstance } from 'i18next'
import { I18nextProvider, initReactI18next } from 'react-i18next'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { page, userEvent } from 'vitest/browser'
import { resources } from '@/lib/locales'
import { NotebookResponse } from '@/lib/types/api'
import { NotebookCard } from './NotebookCard'
import '@/app/globals.css'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock('@/lib/api/notebooks', () => ({
  notebooksApi: {
    update: vi.fn(),
    deletePreview: vi.fn(),
    delete: vi.fn(),
  },
}))

const notebook: NotebookResponse = {
  id: 'notebook:research',
  name: 'Research',
  description: 'Research notes',
  archived: false,
  created: '2026-01-01T00:00:00Z',
  updated: '2026-01-02T00:00:00Z',
  source_count: 0,
  note_count: 0,
}

let queryClient: QueryClient

beforeEach(() => {
  queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
})

afterEach(() => {
  cleanup()
  queryClient.clear()
  document.documentElement.classList.remove('dark')
})

describe('NotebookCard keyboard visibility', () => {
  it.each([
    { theme: 'light', language: 'en-US', label: 'Actions', width: 1280, height: 720 },
    { theme: 'dark', language: 'zh-CN', label: '快捷操作', width: 390, height: 844 },
  ])('shows card actions on keyboard focus in the $theme theme', async ({ theme, language, label, width, height }) => {
    await page.viewport(width, height)
    document.documentElement.classList.toggle('dark', theme === 'dark')
    const i18n = createInstance()
    await i18n.use(initReactI18next).init({
      resources,
      lng: language,
      fallbackLng: false,
      interpolation: { escapeValue: false },
      react: { useSuspense: false },
    })

    render(
      <QueryClientProvider client={queryClient}>
        <I18nextProvider i18n={i18n}>
          <button>Start keyboard navigation</button>
          <NotebookCard notebook={notebook} />
        </I18nextProvider>
      </QueryClientProvider>
    )

    // Park the pointer outside the card so hover cannot hide a focus regression.
    await page.getByRole('button', { name: 'Start keyboard navigation' }).click()
    const trigger = page.getByRole('button', { name: label, exact: true })
    await expect.element(trigger).toHaveStyle({ opacity: '0' })

    await userEvent.tab()
    await expect.element(trigger).toHaveFocus()
    await expect.element(trigger).toHaveStyle({ opacity: '1' })

    await act(async () => {
      await userEvent.keyboard('{Enter}')
    })
    await expect.element(page.getByRole('menu', { name: label })).toBeVisible()
    await act(async () => {
      await userEvent.keyboard('{Escape}')
    })
    await expect.element(trigger).toHaveFocus()
    await expect.element(trigger).toHaveStyle({ opacity: '1' })
  })
})
