import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

import { EpisodeCard } from './EpisodeCard'
import apiClient from '@/lib/api/client'
import type { PodcastEpisode } from '@/lib/types/podcasts'

// useTranslation is mocked globally in setup.ts (t returns the key string)

vi.mock('@/lib/api/client', () => ({
  default: { get: vi.fn() },
}))

vi.mock('@/lib/api/podcasts', () => ({
  resolvePodcastAssetUrl: vi.fn(async () => undefined),
}))

function makeEpisode(overrides: Partial<PodcastEpisode> = {}): PodcastEpisode {
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
    job_status: 'completed',
    ...overrides,
  }
}

function renderAndOpenDetails(episode: PodcastEpisode) {
  render(<EpisodeCard episode={episode} onDelete={vi.fn()} />)
  fireEvent.click(screen.getByText('podcasts.details'))
}

describe('EpisodeCard model details', () => {
  it('renders API-resolved model display fields for new episodes', () => {
    renderAndOpenDetails(
      makeEpisode({
        episode_profile: {
          id: 'episode_profile:1',
          name: 'modern',
          description: '',
          speaker_config: null,
          default_briefing: '',
          num_segments: 5,
          outline_llm: 'model:outline',
          transcript_llm: 'model:transcript',
          outline_model_provider: 'openai',
          outline_model_name: 'gpt-4o',
          transcript_model_provider: 'anthropic',
          transcript_model_name: 'claude-sonnet',
        },
        speaker_profile: {
          id: 'speaker_profile:1',
          name: 'modern',
          description: '',
          speakers: [],
          voice_model: 'model:voice',
          voice_model_provider: 'elevenlabs',
          voice_model_name: 'eleven_turbo',
        },
      })
    )

    expect(screen.getByText('openai / gpt-4o')).toBeInTheDocument()
    expect(screen.getByText('anthropic / claude-sonnet')).toBeInTheDocument()
    expect(screen.getByText('elevenlabs / eleven_turbo')).toBeInTheDocument()
  })

  it('falls back to legacy snapshot strings for old episodes', () => {
    renderAndOpenDetails(
      makeEpisode({
        episode_profile: {
          id: 'episode_profile:1',
          name: 'legacy',
          description: '',
          speaker_config: null,
          default_briefing: '',
          num_segments: 5,
          outline_provider: 'openai',
          outline_model: 'gpt-3.5-turbo',
          transcript_provider: 'openai',
          transcript_model: 'gpt-4',
        },
        speaker_profile: {
          id: 'speaker_profile:1',
          name: 'legacy',
          description: '',
          speakers: [],
          tts_provider: 'openai',
          tts_model: 'tts-1',
        },
      })
    )

    expect(screen.getByText('openai / gpt-3.5-turbo')).toBeInTheDocument()
    expect(screen.getByText('openai / gpt-4')).toBeInTheDocument()
    expect(screen.getByText('openai / tts-1')).toBeInTheDocument()
  })

  it('degrades to dashes when references are unresolvable and no legacy strings exist', () => {
    renderAndOpenDetails(
      makeEpisode({
        episode_profile: {
          id: 'episode_profile:1',
          name: 'orphaned',
          description: '',
          speaker_config: null,
          default_briefing: '',
          num_segments: 5,
          outline_llm: 'model:deleted',
          transcript_llm: 'model:deleted',
        },
        speaker_profile: {
          id: 'speaker_profile:1',
          name: 'orphaned',
          description: '',
          speakers: [],
          voice_model: 'model:deleted',
        },
      })
    )

    expect(screen.getAllByText('— / —')).toHaveLength(3)
  })
})

describe('EpisodeCard audio loading', () => {
  // Regression test for a live production bug: apiClient's request
  // interceptor prepends its own "/api" baseURL to any request path that
  // isn't a network-absolute URL (scheme+host). episode.audio_url already
  // starts with "/api/..." (PodcastEpisodeResponse), so passing it to
  // apiClient.get() unmodified double-prefixed the request to
  // "/api/api/podcasts/.../audio" - a 404 in relative-path/tunnel deploys
  // where getApiUrl() resolves to "" (confirmed live: the network request
  // Chrome actually sent was exactly that double-prefixed 404 URL). Fixed
  // by stripping the redundant leading "/api" before calling apiClient,
  // matching every other apiClient call in this codebase.
  it('strips the redundant leading /api before calling apiClient for the audio blob', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: new Blob(['audio']) })

    render(
      <EpisodeCard
        episode={makeEpisode({ audio_url: '/api/podcasts/episodes/episode:1/audio' })}
        onDelete={vi.fn()}
      />
    )

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith(
        '/podcasts/episodes/episode:1/audio',
        { responseType: 'blob' }
      )
    })
  })
})
