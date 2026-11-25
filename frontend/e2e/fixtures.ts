import { test as base, expect } from '@playwright/test'
import type { NotebookResponse, NoteResponse, SourceDetailResponse } from '../src/lib/types/api'
import type { SourceInsightResponse } from '../src/lib/api/insights'

export const notebook: NotebookResponse = {
  id: 'notebook:modal-navigation',
  name: 'Modal navigation notebook',
  description: 'Browser regression fixtures',
  archived: false,
  created: '2026-01-01T00:00:00Z',
  updated: '2026-01-01T00:00:00Z',
  source_count: 1,
  note_count: 1,
}

export const source: SourceDetailResponse = {
  id: 'source:modal-navigation',
  title: 'Modal navigation source',
  full_text: 'Source content for the modal navigation regression.',
  asset: null,
  embedded: false,
  embedded_chunks: 0,
  insights_count: 1,
  created: notebook.created,
  updated: notebook.updated,
  notebooks: [notebook.id],
  status: 'completed',
}

export const note = {
  id: 'note:modal-navigation',
  title: 'Modal navigation note',
  content: 'Note content for the modal navigation regression.',
  note_type: 'human',
  created: notebook.created,
  updated: notebook.updated,
} satisfies NoteResponse

export const insight = {
  id: 'source_insight:modal-navigation',
  source_id: source.id,
  insight_type: 'summary',
  content: 'Insight content for the modal navigation regression.',
  created: notebook.created,
  updated: notebook.updated,
} satisfies SourceInsightResponse

export const notebookPath = `/notebooks/${notebook.id}`

// Only HTTP responses are replaced. The application, App Router, providers and
// Radix dialogs run in the browser without the Vitest setup's module mocks.
export const test = base.extend({
  page: async ({ page }, runTest) => {
    const errors: string[] = []
    const unexpectedRequests: string[] = []
    page.on('pageerror', error => errors.push(error.message))
    await page.addInitScript(() => {
      localStorage.setItem('auth-storage', JSON.stringify({
        state: { isAuthenticated: true, token: 'not-required', lastAuthCheck: Date.now() },
        version: 0,
      }))
      localStorage.setItem('i18nextLng', 'en-US')
    })

    const responses: Record<string, unknown> = {
      '/api/config': { version: 'browser-test', hasUpdate: false, dbStatus: 'online' },
      '/api/auth/status': { auth_enabled: false },
      '/api/credentials/status': {
        configured: {}, source: {}, encryption_configured: true, encryption_key_is_default: false,
      },
      '/api/credentials/env-status': {},
      '/api/notebooks': [notebook],
      [`/api/notebooks/${notebook.id}`]: notebook,
      [`/api/notebooks/${notebook.id}/notes`]: [note],
      '/api/notes': [note],
      [`/api/notes/${note.id}`]: note,
      '/api/sources': [source],
      [`/api/sources/${source.id}`]: source,
      [`/api/sources/${source.id}/insights`]: [insight],
      [`/api/insights/${insight.id}`]: insight,
      [`/api/sources/${source.id}/status`]: { status: 'completed', message: 'Ready' },
      [`/api/sources/${source.id}/chat/sessions`]: [],
      '/api/chat/sessions': [],
      '/api/chat/context': { context: { sources: [], notes: [] }, token_count: 0, char_count: 0 },
      '/api/recently-viewed': [],
      '/api/transformations': [],
      '/api/episode-profiles': [],
      '/api/settings': {},
      '/api/models': [],
      '/api/models/defaults': {},
    }
    await page.route('**/api/**', async route => {
      const request = route.request()
      const url = new URL(request.url())
      const pathname = decodeURIComponent(url.pathname).replace(/\/$/, '')
      // During an insight/source history transition, Radix's exiting source
      // content can briefly receive the insight id. That source does not exist.
      if (pathname === `/api/sources/${insight.id}` || pathname === `/api/sources/${insight.id}/insights`) {
        await route.fulfill({ status: 404, json: { detail: 'Source not found' } })
        return
      }
      if (!Object.hasOwn(responses, pathname)) {
        unexpectedRequests.push(`${request.method()} ${pathname}`)
        await route.fulfill({ status: 404, json: { detail: 'Unexpected browser test request' } })
        return
      }
      const json = pathname === '/api/notebooks' && url.searchParams.get('archived') === 'true'
        ? [] : responses[pathname]
      await route.fulfill({ json })
    })

    await runTest(page)
    expect(unexpectedRequests, 'All API requests must have an explicit fixture').toEqual([])
    expect(errors, 'The real application must render without browser errors').toEqual([])
  },
})

export { expect }
