import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import i18n from '@/lib/i18n'
import { EpisodeProfile, SpeakerProfile } from '@/lib/types/podcasts'
import { EpisodeProfilesPanel } from './EpisodeProfilesPanel'
import { SpeakerProfilesPanel } from './SpeakerProfilesPanel'

vi.unmock('@/lib/hooks/use-translation')

const { duplicateEpisode, duplicateSpeaker } = vi.hoisted(() => ({
  duplicateEpisode: vi.fn(),
  duplicateSpeaker: vi.fn(),
}))

vi.mock('@/lib/hooks/use-models', () => ({ useModels: () => ({ data: [] }) }))
vi.mock('@/lib/hooks/use-podcasts', () => ({
  useDeleteEpisodeProfile: () => ({ mutate: vi.fn(), isPending: false }),
  useDuplicateEpisodeProfile: () => ({ mutate: duplicateEpisode, isPending: false }),
  useDeleteSpeakerProfile: () => ({ mutate: vi.fn(), isPending: false }),
  useDuplicateSpeakerProfile: () => ({ mutate: duplicateSpeaker, isPending: false }),
}))
vi.mock('./forms/EpisodeProfileFormDialog', () => ({ EpisodeProfileFormDialog: () => null }))
vi.mock('./forms/SpeakerProfileFormDialog', () => ({ SpeakerProfileFormDialog: () => null }))

const speaker: SpeakerProfile = {
  id: 'speaker:one', name: 'Speaker', description: '', voice_model: 'model:voice', speakers: [],
}
const episode: EpisodeProfile = {
  id: 'episode:one', name: 'Episode', description: '', speaker_config: speaker.id,
  outline_llm: 'model:text', transcript_llm: 'model:text', default_briefing: '', num_segments: 2,
}
const panels = [
  {
    name: 'episode', id: episode.id, duplicate: duplicateEpisode,
    render: () => <EpisodeProfilesPanel episodeProfiles={[episode]} speakerProfiles={[speaker]} />,
  },
  {
    name: 'speaker', id: speaker.id, duplicate: duplicateSpeaker,
    render: () => <SpeakerProfilesPanel speakerProfiles={[speaker]} usage={{}} />,
  },
]

beforeEach(async () => {
  vi.clearAllMocks()
  await i18n.changeLanguage('en-US')
})
afterEach(cleanup)

describe.each(panels)('$name profile menu', (panel) => {
  // #1403: the real icon-only Radix trigger needs a localized accessible name.
  it.each(['en-US', 'zh-CN'])('has an accessible action name in %s', async (language) => {
    await i18n.changeLanguage(language)
    render(panel.render())

    expect(screen.getByRole('button', { name: i18n.t('common.actions') }))
      .toHaveAttribute('aria-haspopup', 'menu')
  })

  it('keeps the visible edit action available', () => {
    render(panel.render())
    expect(screen.getByRole('button', { name: i18n.t('podcasts.edit') })).toBeEnabled()
  })

  it('opens with Enter and duplicates the selected profile', () => {
    const { container } = render(panel.render())
    const trigger = container.querySelector('button[aria-haspopup="menu"]')!
    fireEvent.keyDown(trigger, { key: 'Enter' })
    expect(screen.getByRole('menu')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('menuitem', { name: i18n.t('podcasts.duplicate') }))
    expect(panel.duplicate).toHaveBeenCalledExactlyOnceWith(panel.id)
  })
})
