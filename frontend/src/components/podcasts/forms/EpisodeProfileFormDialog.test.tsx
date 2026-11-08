import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { EpisodeProfile, SpeakerProfile } from '@/lib/types/podcasts'
import { EpisodeProfileFormDialog } from './EpisodeProfileFormDialog'

// useTranslation is mocked globally in setup.ts (t returns the key string)

const updateMutateAsync = vi.fn()

vi.mock('@/lib/hooks/use-podcasts', () => ({
  useCreateEpisodeProfile: () => ({ isPending: false, mutateAsync: vi.fn() }),
  useUpdateEpisodeProfile: () => ({ isPending: false, mutateAsync: updateMutateAsync }),
  useLanguages: () => ({ data: [] }),
}))

vi.mock('@/lib/hooks/use-models', () => ({
  useModels: () => ({ data: [], isLoading: false }),
}))

const speaker = { id: 'speaker_profile:1', name: 'Hosts' } as SpeakerProfile

const profile: EpisodeProfile = {
  id: 'episode_profile:1',
  name: 'Tech',
  description: '',
  speaker_config: 'speaker_profile:1',
  outline_llm: 'model:a',
  transcript_llm: 'model:b',
  language: null,
  default_briefing: 'Brief',
  num_segments: 5,
  max_tokens: null,
  audio_gap_ms: 0,
}

function renderEdit(initialData: EpisodeProfile) {
  render(
    <EpisodeProfileFormDialog
      mode="edit"
      open
      onOpenChange={vi.fn()}
      speakerProfiles={[speaker]}
      initialData={initialData}
    />,
  )
  return screen.getByLabelText('podcasts.audioGapMs') as HTMLInputElement
}

function submit() {
  fireEvent.submit(screen.getByLabelText('podcasts.audioGapMs').closest('form')!)
}

describe('EpisodeProfileFormDialog pause between turns', () => {
  beforeEach(() => updateMutateAsync.mockReset())

  it('keeps 0 (no pause) rather than treating it as unset', async () => {
    const input = renderEdit(profile)
    expect(input).toHaveValue(0)

    submit()

    await waitFor(() => expect(updateMutateAsync).toHaveBeenCalled())
    expect(updateMutateAsync.mock.calls[0][0].payload.audio_gap_ms).toBe(0)
  })

  it('sends null when left blank so the default applies', async () => {
    const input = renderEdit(profile)
    fireEvent.change(input, { target: { value: '' } })

    submit()

    await waitFor(() => expect(updateMutateAsync).toHaveBeenCalled())
    expect(updateMutateAsync.mock.calls[0][0].payload.audio_gap_ms).toBeNull()
  })

  it('rejects a negative value', async () => {
    const input = renderEdit(profile)
    fireEvent.change(input, { target: { value: '-1' } })

    submit()

    expect(await screen.findByText('podcasts.audioGapMsNonNegative')).toBeInTheDocument()
    expect(updateMutateAsync).not.toHaveBeenCalled()
  })
})
