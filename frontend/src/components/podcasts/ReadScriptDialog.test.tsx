import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

import { ReadScriptDialog, isScriptFile } from './ReadScriptDialog'

// useTranslation is mocked globally in setup.ts (t returns the key string)

const mutateAsync = vi.fn(async () => ({}))

vi.mock('@/lib/hooks/use-podcasts', () => ({
  useSpeakerProfiles: () => ({
    isLoading: false,
    speakerProfiles: [
      {
        id: 'speaker_profile:sp1',
        name: 'velvet_noir',
        description: '',
        voice_model: 'model:tts',
        speakers: [{ name: 'Velvet Noir', voice_id: 'v', backstory: '', personality: '' }],
      },
    ],
  }),
  useReadScriptPodcast: () => ({ mutateAsync, isPending: false }),
}))

vi.mock('@/lib/hooks/use-toast', () => ({ useToast: () => ({ toast: vi.fn() }) }))

// Radix Select is awkward in jsdom; a native select keeps the test on our logic.
vi.mock('@/components/ui/select', () => ({
  Select: ({ value, onValueChange, children }: { value: string; onValueChange: (v: string) => void; children: React.ReactNode }) => (
    <select data-testid="profile-select" value={value} onChange={(e) => onValueChange(e.target.value)}>
      <option value="" />
      {children}
    </select>
  ),
  SelectTrigger: () => null,
  SelectValue: () => null,
  SelectContent: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  SelectItem: ({ value, children }: { value: string; children: React.ReactNode }) => (
    <option value={value}>{children}</option>
  ),
}))

describe('isScriptFile', () => {
  it('accepts txt and md, rejects others', () => {
    expect(isScriptFile(new File(['x'], 'ep.md'))).toBe(true)
    expect(isScriptFile(new File(['x'], 'ep.TXT'))).toBe(true)
    expect(isScriptFile(new File(['x'], 'ep.pdf', { type: 'application/pdf' }))).toBe(false)
  })
})

describe('ReadScriptDialog', () => {
  beforeEach(() => mutateAsync.mockClear())

  it('loads a dropped .md file and submits it with the chosen profile', async () => {
    const onOpenChange = vi.fn()
    render(<ReadScriptDialog open onOpenChange={onOpenChange} />)

    const submit = screen.getByText('podcasts.readScriptSubmit').closest('button')!
    expect(submit).toBeDisabled()

    const file = new File(['# Ep\n\nHello listeners.'], 'Episode One.md', { type: 'text/markdown' })
    // jsdom's File has no text(); browsers do.
    Object.defineProperty(file, 'text', { value: async () => '# Ep\n\nHello listeners.' })
    fireEvent.drop(screen.getByTestId('script-drop-zone'), { dataTransfer: { files: [file] } })

    await waitFor(() =>
      expect(screen.getByLabelText('podcasts.scriptLabel')).toHaveValue('# Ep\n\nHello listeners.')
    )
    expect(screen.getByLabelText('podcasts.episodeName')).toHaveValue('Episode One')

    fireEvent.change(screen.getByTestId('profile-select'), { target: { value: 'speaker_profile:sp1' } })
    expect(submit).not.toBeDisabled()
    fireEvent.click(submit)

    await waitFor(() =>
      expect(mutateAsync).toHaveBeenCalledWith({
        speaker_profile: 'speaker_profile:sp1',
        episode_name: 'Episode One',
        script: '# Ep\n\nHello listeners.',
      })
    )
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('accepts pasted text', () => {
    render(<ReadScriptDialog open onOpenChange={vi.fn()} />)
    fireEvent.change(screen.getByLabelText('podcasts.scriptLabel'), { target: { value: 'Pasted.' } })
    expect(screen.getByLabelText('podcasts.scriptLabel')).toHaveValue('Pasted.')
  })
})
