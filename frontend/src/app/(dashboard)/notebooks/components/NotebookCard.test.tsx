import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createInstance } from 'i18next'
import { I18nextProvider, initReactI18next } from 'react-i18next'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { resources } from '@/lib/locales'
import { NotebookResponse } from '@/lib/types/api'
import { NotebookCard } from './NotebookCard'

vi.unmock('@/lib/hooks/use-translation')

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

afterEach(() => queryClient.clear())

async function renderNotebook(language = 'en-US') {
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
        <NotebookCard notebook={notebook} />
      </I18nextProvider>
    </QueryClientProvider>
  )
}

describe('NotebookCard action menu', () => {
  it.each([
    ['en-US', 'Actions'],
    ['zh-CN', '快捷操作'],
  ])('has a localized accessible name in %s', async (language, label) => {
    await renderNotebook(language)

    expect(screen.getByRole('button', { name: label })).toBeInTheDocument()
  })

  it('opens with Enter and restores focus after Escape', async () => {
    await renderNotebook()
    const trigger = screen.getByRole('button', { name: 'Actions' })

    trigger.focus()
    fireEvent.keyDown(trigger, { key: 'Enter', code: 'Enter' })

    const menu = await screen.findByRole('menu', { name: 'Actions' })
    expect(within(menu).getByRole('menuitem', { name: 'Archive' })).toBeInTheDocument()

    fireEvent.keyDown(menu, { key: 'Escape', code: 'Escape' })

    await waitFor(() => {
      expect(screen.queryByRole('menu')).not.toBeInTheDocument()
      expect(trigger).toHaveFocus()
    })
  })
})
