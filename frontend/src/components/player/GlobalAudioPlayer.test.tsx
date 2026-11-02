import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, act } from '@testing-library/react'

import { GlobalAudioPlayer } from './GlobalAudioPlayer'
import { useAudioPlayerStore } from '@/lib/stores/audio-player-store'

let audioError: string | null = null
vi.mock('@/lib/hooks/use-episode-audio', () => ({
  useEpisodeAudio: (_e: unknown, enabled: boolean) => ({
    audioSrc: enabled && !audioError ? 'blob:audio' : undefined,
    audioError,
  }),
}))
const toastError = vi.fn()
vi.mock('sonner', () => ({ toast: { error: (...a: unknown[]) => toastError(...a) } }))

const ep = { id: 'episode:1', name: 'My Episode', notebookId: 'notebook:7' }

describe('GlobalAudioPlayer', () => {
  const play = vi.fn(() => Promise.resolve())
  const pause = vi.fn()

  beforeEach(() => {
    audioError = null
    toastError.mockClear()
    play.mockClear()
    pause.mockClear()
    HTMLMediaElement.prototype.play = play
    HTMLMediaElement.prototype.pause = pause
    useAudioPlayerStore.getState().stop()
  })
  afterEach(() => useAudioPlayerStore.getState().stop())

  it('renders nothing until something has been played', () => {
    const { container } = render(<GlobalAudioPlayer />)
    expect(container).toBeEmptyDOMElement()
  })

  it('renders the bar with a notebook link and drives the audio element', () => {
    render(<GlobalAudioPlayer />)
    act(() => useAudioPlayerStore.getState().play(ep))
    expect(screen.getByTestId('mini-player')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'My Episode' })).toHaveAttribute(
      'href',
      '/notebooks/notebook%3A7'
    )
    expect(play).toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: 'Pause' }))
    expect(useAudioPlayerStore.getState().isPlaying).toBe(false)
    expect(pause).toHaveBeenCalled()
  })

  it('close stops playback and removes the bar', () => {
    render(<GlobalAudioPlayer />)
    act(() => useAudioPlayerStore.getState().play(ep))
    fireEvent.click(screen.getByRole('button', { name: 'common.close' }))
    expect(screen.queryByTestId('mini-player')).toBeNull()
    expect(useAudioPlayerStore.getState().episode).toBeNull()
  })

  it('resets to paused at 0 when the audio ends', () => {
    const { container } = render(<GlobalAudioPlayer />)
    act(() => useAudioPlayerStore.getState().play(ep))
    act(() => useAudioPlayerStore.getState().syncTime(30))
    fireEvent.ended(container.querySelector('audio')!)
    expect(useAudioPlayerStore.getState()).toMatchObject({ isPlaying: false, currentTime: 0 })
  })

  it('toasts and resets the store when the audio fails to load', () => {
    const { rerender } = render(<GlobalAudioPlayer />)
    act(() => useAudioPlayerStore.getState().play(ep))
    audioError = 'Audio unavailable'
    rerender(<GlobalAudioPlayer />)
    expect(toastError).toHaveBeenCalledWith('Audio unavailable')
    expect(useAudioPlayerStore.getState().episode).toBeNull()
  })
})
