import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
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
const secondSpeaker: SpeakerProfile = { ...speaker, id: 'speaker:two', name: 'Zebra speaker' }
const secondEpisode: EpisodeProfile = { ...episode, id: 'episode:two', name: 'Zebra episode' }
const panels = [
  {
    name: 'episode', second: secondEpisode, duplicate: duplicateEpisode,
    render: (multiple = false) => (
      <EpisodeProfilesPanel
        episodeProfiles={multiple ? [secondEpisode, episode] : [episode]}
        speakerProfiles={[speaker]}
      />
    ),
  },
  {
    name: 'speaker', second: secondSpeaker, duplicate: duplicateSpeaker,
    render: (multiple = false) => (
      <SpeakerProfilesPanel
        speakerProfiles={multiple ? [secondSpeaker, speaker] : [speaker]}
        usage={{}}
      />
    ),
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

  it.each(['pointer', 'Enter'])('duplicates the second profile using %s', (input) => {
    // Input order differs from display order: both panels sort profiles by name.
    render(panel.render(true))
    const card = screen.getByText(panel.second.name).closest<HTMLElement>('[data-slot="card"]')!
    const trigger = within(card).getByRole('button', { name: i18n.t('common.actions') })
    const triggers = screen.getAllByRole('button', { name: i18n.t('common.actions') })
    expect(triggers).toHaveLength(2)
    expect(triggers[1]).toBe(trigger)

    if (input === 'Enter') {
      fireEvent.keyDown(trigger, { key: 'Enter' })
    } else {
      // Radix opens on pointerdown; jsdom has no native PointerEvent.
      fireEvent(trigger, new MouseEvent('pointerdown', { bubbles: true, button: 0, ctrlKey: false }))
    }
    expect(screen.getByRole('menu')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('menuitem', { name: i18n.t('podcasts.duplicate') }))
    expect(panel.duplicate).toHaveBeenCalledExactlyOnceWith(panel.second.id)
  })
})
