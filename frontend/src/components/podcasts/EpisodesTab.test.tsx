import { describe, it, expect, vi } from 'vitest'
import { render, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { EpisodesTab } from './EpisodesTab'
import { podcastsApi } from '@/lib/api/podcasts'
import type { PodcastEpisode } from '@/lib/types/podcasts'

// useTranslation is mocked globally in setup.ts (t returns the key string)

vi.mock('@/lib/api/client', () => ({
  default: { get: vi.fn() },
}))

vi.mock('@/lib/api/podcasts', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/podcasts')>('@/lib/api/podcasts')
  return {
    ...actual,
    resolvePodcastAssetUrl: vi.fn(async () => undefined),
    podcastsApi: {
      ...actual.podcastsApi,
      listEpisodes: vi.fn(),
      deleteEpisode: vi.fn(),
      retryEpisode: vi.fn(),
    },
  }
})

function makeRunningEpisode(): PodcastEpisode {
  return {
    id: 'episode:1',
    name: 'Test Episode',
    episode_profile: {
      id: 'episode_profile:1',
      name: 'default',
      description: '',
      speaker_config: null,
      default_briefing: '',
      num_segments: 5,
    },
    speaker_profile: {
      id: 'speaker_profile:1',
      name: 'default',
      description: '',
      speakers: [],
    },
    briefing: 'briefing',
    job_status: 'running',
    audio_url: null,
    audio_file: null,
    created: new Date().toISOString(),
  }
}

function renderTab() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <EpisodesTab />
    </QueryClientProvider>
  )
}

describe('EpisodesTab', () => {
  // Regression test for the live-production crash: navigating to /podcasts while
  // an episode is running/pending threw "NotFoundError: Failed to execute
  // 'insertBefore' on 'Node'" roughly every 15s (the usePodcastEpisodes()
  // refetchInterval), caught by the root ErrorBoundary.
  //
  // Root cause: EpisodesTab polls every 15s while any episode is
  // running/pending/submitted, and every poll toggles `isFetching`, which
  // swaps the refresh button's icon (Loader2 <-> RefreshCcw) - a structural
  // DOM child change - even when the episode data itself hasn't changed.
  // Chrome's built-in page translator rewrites in-place any text node it has
  // translated by wrapping it in an injected <font> element, detaching the
  // original text node from its parent. React still holds a reference to that
  // now-detached node as an insertBefore sibling for the next commit, so the
  // very next poll-driven re-render throws
  // "NotFoundError: ... insertBefore ... not a child of this node" the moment
  // Chrome has translated the page (confirmed live via
  // document.documentElement.classList containing "translated-ltr" and
  // injected <font> tags, and reproduced against a local dev server pointed
  // at the same production API).
  //
  // jsdom has no page-translation engine, so it can't reproduce the DOM
  // mutation Chrome performs - this test can only assert the mitigation
  // (translate="no" / .notranslate on the auto-polling subtree) stays in
  // place, which is what actually prevents Chrome from touching these nodes.
  // See EpisodesTab.tsx for the full explanation and
  // https://github.com/facebook/react/issues/11538 for the underlying,
  // still-open React/Chrome-Translate incompatibility.
  it('opts the auto-polling subtree out of page translation', async () => {
    vi.mocked(podcastsApi.listEpisodes).mockResolvedValue([makeRunningEpisode()])

    const { container } = renderTab()

    await act(async () => {
      await Promise.resolve()
    })

    const guarded = container.querySelector('[translate="no"]')
    expect(guarded).not.toBeNull()
    expect(guarded).toHaveClass('notranslate')
    // The refresh button (whose icon child swaps between Loader2 and
    // RefreshCcw on every poll tick) must live inside the guarded subtree.
    const refreshButton = Array.from(container.querySelectorAll('button')).find((b) =>
      b.textContent?.includes('common.refresh')
    )
    expect(refreshButton).toBeDefined()
    expect(guarded?.contains(refreshButton as Node)).toBe(true)
  })

  it('re-renders across multiple poll cycles (unchanged running episode) without throwing', async () => {
    vi.mocked(podcastsApi.listEpisodes).mockResolvedValue([makeRunningEpisode()])

    const errors: unknown[] = []
    const origError = console.error
    console.error = (...args: unknown[]) => {
      errors.push(args)
      origError(...args)
    }

    vi.useFakeTimers()
    try {
      renderTab()

      await act(async () => {
        await vi.advanceTimersByTimeAsync(0)
      })

      for (let i = 0; i < 3; i++) {
        await act(async () => {
          await vi.advanceTimersByTimeAsync(15_000)
        })
      }
    } finally {
      vi.useRealTimers()
      console.error = origError
    }

    expect(errors).toEqual([])
  })
})
