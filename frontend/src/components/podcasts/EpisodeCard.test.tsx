import { afterEach, beforeEach, describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, within } from '@testing-library/react'

import { EpisodeCard, episodeAudioFilename } from './EpisodeCard'
import apiClient from '@/lib/api/client'
import { resolvePodcastAssetUrl } from '@/lib/api/podcasts'
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

describe('EpisodeCard download', () => {
  const AUDIO_URL = '/api/podcasts/episodes/episode:1/audio'
  const BLOB_URL = 'blob:http://localhost/audio-1'

  beforeEach(() => {
    vi.mocked(resolvePodcastAssetUrl).mockImplementation(async (path) =>
      path ? `http://localhost:5055${path}` : undefined
    )
    vi.mocked(apiClient.get).mockResolvedValue({ data: new Blob(['mp3']) })
    URL.createObjectURL = vi.fn(() => BLOB_URL)
    URL.revokeObjectURL = vi.fn()
  })

  afterEach(() => {
    vi.mocked(resolvePodcastAssetUrl).mockReset()
    vi.mocked(resolvePodcastAssetUrl).mockImplementation(async () => undefined)
    vi.mocked(apiClient.get).mockReset()
  })

  it('offers the fetched audio as a named mp3 download', async () => {
    render(
      <EpisodeCard
        episode={makeEpisode({ name: 'AI: news / week 3', audio_url: AUDIO_URL })}
        onDelete={vi.fn()}
      />
    )

    const link = await screen.findByRole('link', { name: 'podcasts.downloadEpisode' })
    expect(link).toHaveAttribute('href', BLOB_URL)
    expect(link).toHaveAttribute('download', 'AI news week 3.mp3')
    expect(link).toHaveTextContent('common.download')
    expect(apiClient.get).toHaveBeenCalledWith('http://localhost:5055' + AUDIO_URL, {
      responseType: 'blob',
    })
  })

  it('also shows the download control in the Details dialog', async () => {
    render(
      <EpisodeCard episode={makeEpisode({ audio_url: AUDIO_URL })} onDelete={vi.fn()} />
    )
    await screen.findByRole('link', { name: 'podcasts.downloadEpisode' })

    fireEvent.click(screen.getByText('podcasts.details'))

    const dialog = await screen.findByRole('dialog')
    const link = await within(dialog).findByRole('link', { name: 'podcasts.downloadEpisode' })
    expect(link).toHaveAttribute('download', 'Test Episode.mp3')
  })

  it('has no download control when the episode has no audio', async () => {
    render(<EpisodeCard episode={makeEpisode({ job_status: 'running' })} onDelete={vi.fn()} />)

    await vi.waitFor(() => expect(resolvePodcastAssetUrl).toHaveBeenCalled())
    expect(screen.queryByRole('link', { name: 'podcasts.downloadEpisode' })).not.toBeInTheDocument()
  })

  it('has no download control when the audio cannot be fetched', async () => {
    vi.mocked(apiClient.get).mockRejectedValue(new Error('network'))
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})

    try {
      render(
        <EpisodeCard episode={makeEpisode({ audio_url: AUDIO_URL })} onDelete={vi.fn()} />
      )

      expect(await screen.findByText('podcasts.audioUnavailable')).toBeInTheDocument()
      expect(screen.queryByRole('link', { name: 'podcasts.downloadEpisode' })).not.toBeInTheDocument()
    } finally {
      consoleError.mockRestore()
    }
  })

  it('ignores audio that arrives after the episode changed', async () => {
    let resolveOld: (value: { data: Blob }) => void = () => {}
    vi.mocked(apiClient.get)
      .mockImplementationOnce(() => new Promise((resolve) => { resolveOld = resolve }))
      .mockResolvedValueOnce({ data: new Blob(['new']) })
    vi.mocked(URL.createObjectURL).mockImplementation(
      (blob) => (blob instanceof Blob && blob.size === 3 ? 'blob:new' : 'blob:old')
    )

    const { rerender } = render(
      <EpisodeCard episode={makeEpisode({ audio_url: AUDIO_URL })} onDelete={vi.fn()} />
    )
    await vi.waitFor(() => expect(apiClient.get).toHaveBeenCalledTimes(1))

    rerender(
      <EpisodeCard
        episode={makeEpisode({ audio_url: '/api/podcasts/episodes/episode:2/audio' })}
        onDelete={vi.fn()}
      />
    )
    const link = await screen.findByRole('link', { name: 'podcasts.downloadEpisode' })
    expect(link).toHaveAttribute('href', 'blob:new')

    resolveOld({ data: new Blob(['old audio']) })
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(screen.getByRole('link', { name: 'podcasts.downloadEpisode' })).toHaveAttribute('href', 'blob:new')
    expect(URL.createObjectURL).toHaveBeenCalledTimes(1)
  })
})

describe('episodeAudioFilename', () => {
  it('keeps a plain episode name', () => {
    expect(episodeAudioFilename('Weekly digest')).toBe('Weekly digest.mp3')
  })

  it('removes characters that are not allowed in file names', () => {
    expect(episodeAudioFilename('Q&A: "LLMs" <2026>?')).toBe('Q&A LLMs 2026.mp3')
  })

  it('prefixes names that Windows reserves for devices', () => {
    expect(episodeAudioFilename('CON')).toBe('_CON.mp3')
    expect(episodeAudioFilename('nul.backup')).toBe('_nul.backup.mp3')
    expect(episodeAudioFilename('Com1')).toBe('_Com1.mp3')
    expect(episodeAudioFilename('Console talk')).toBe('Console talk.mp3')
  })

  it('falls back when nothing usable is left', () => {
    expect(episodeAudioFilename('')).toBe('podcast-episode.mp3')
    expect(episodeAudioFilename(null)).toBe('podcast-episode.mp3')
    expect(episodeAudioFilename('...')).toBe('podcast-episode.mp3')
  })
})
