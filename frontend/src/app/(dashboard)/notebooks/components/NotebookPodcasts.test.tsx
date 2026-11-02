import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

import { NotebookPodcasts } from './NotebookPodcasts'
import type { PodcastEpisode } from '@/lib/types/podcasts'
import { useAudioPlayerStore } from '@/lib/stores/audio-player-store'

let episodes: PodcastEpisode[] = []
const usePodcastEpisodes = vi.fn()
vi.mock('@/lib/hooks/use-podcasts', () => ({
  usePodcastEpisodes: (...args: unknown[]) => usePodcastEpisodes(...args),
}))
vi.mock('@/components/podcasts/GeneratePodcastDialog', () => ({
  GeneratePodcastDialog: () => null,
}))

function ep(overrides: Partial<PodcastEpisode>): PodcastEpisode {
  return {
    id: 'episode:1',
    name: 'Ep',
    episode_profile: { id: 'p', name: 'p', description: '', speaker_config: null, default_briefing: '', num_segments: 3 },
    speaker_profile: { id: 's', name: 's', description: '', speakers: [] },
    briefing: '',
    notebook_id: 'notebook:1',
    ...overrides,
  }
}

describe('NotebookPodcasts', () => {
  beforeEach(() => {
    episodes = []
    useAudioPlayerStore.getState().stop()
    usePodcastEpisodes.mockImplementation(() => ({ episodes, isLoading: false }))
  })

  it('scopes the query to the notebook and shows the empty state', () => {
    render(<NotebookPodcasts notebookId="notebook:1" />)
    expect(usePodcastEpisodes).toHaveBeenCalledWith({ notebookId: 'notebook:1' })
    expect(screen.getByText('podcasts.noNotebookPodcasts')).toBeInTheDocument()
  })

  it('shows progress for running episodes and a player for completed ones', () => {
    episodes = [
      ep({ id: 'episode:1', name: 'Running ep', job_status: 'running', progress: 35 }),
      ep({ id: 'episode:2', name: 'Done ep', job_status: 'completed', progress: 100, audio_url: '/api/podcasts/episodes/2/audio' }),
    ]
    const { container } = render(<NotebookPodcasts notebookId="notebook:1" />)
    expect(screen.getByText('Running ep')).toBeInTheDocument()
    expect(screen.getByText('35%')).toBeInTheDocument()
    expect(screen.getAllByTestId('episode-progress')).toHaveLength(1)
    expect(container.querySelectorAll('audio')).toHaveLength(0)
    expect(screen.getAllByTestId('episode-play-button')).toHaveLength(1)
  })

  it('plays through the global store and reflects its playing state', () => {
    episodes = [
      ep({ id: 'episode:2', name: 'Done ep', job_status: 'completed', audio_url: '/a/2' }),
    ]
    render(<NotebookPodcasts notebookId="notebook:1" />)
    fireEvent.click(screen.getByRole('button', { name: 'Play' }))
    const state = useAudioPlayerStore.getState()
    expect(state.episode).toMatchObject({ id: 'episode:2', notebookId: 'notebook:1' })
    expect(state.isPlaying).toBe(true)
    expect(screen.getByRole('button', { name: 'Pause' })).toBeInTheDocument()
  })
})
