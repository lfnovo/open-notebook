import { describe, it, expect, beforeEach } from 'vitest'

import { useAudioPlayerStore, type PlayerEpisode } from './audio-player-store'

const a: PlayerEpisode = { id: 'episode:a', name: 'A', notebookId: 'notebook:1' }
const b: PlayerEpisode = { id: 'episode:b', name: 'B' }
const s = () => useAudioPlayerStore.getState()

describe('audio-player-store', () => {
  beforeEach(() => s().stop())

  it('play sets the track and switches to another one, resetting progress', () => {
    s().play(a)
    expect(s().episode?.id).toBe('episode:a')
    expect(s().isPlaying).toBe(true)
    s().syncDuration(100)
    s().syncTime(40)
    s().play(b)
    expect(s().episode?.id).toBe('episode:b')
    expect(s().currentTime).toBe(0)
    expect(s().duration).toBe(0)
    expect(s().isPlaying).toBe(true)
  })

  it('playing the current episode again resumes without resetting', () => {
    s().play(a)
    s().syncTime(12)
    s().pause()
    s().play(a)
    expect(s().isPlaying).toBe(true)
    expect(s().currentTime).toBe(12)
  })

  it('toggle flips play state and switches track for another episode', () => {
    s().play(a)
    s().toggle()
    expect(s().isPlaying).toBe(false)
    s().toggle()
    expect(s().isPlaying).toBe(true)
    s().toggle(b)
    expect(s().episode?.id).toBe('episode:b')
    expect(s().isPlaying).toBe(true)
  })

  it('skip and seek clamp to [0, duration]', () => {
    s().play(a)
    s().syncDuration(100)
    s().syncTime(5)
    s().skip(-15)
    expect(s().currentTime).toBe(0)
    s().seek(90)
    s().skip(15)
    expect(s().currentTime).toBe(100)
    expect(s().seekNonce).toBeGreaterThan(0)
  })

  it('seek is a no-op without a track', () => {
    s().seek(30)
    expect(s().currentTime).toBe(0)
  })

  it('ended resets to paused at 0, stop clears the track', () => {
    s().play(a)
    s().syncTime(50)
    s().ended()
    expect(s().isPlaying).toBe(false)
    expect(s().currentTime).toBe(0)
    expect(s().episode?.id).toBe('episode:a')
    s().stop()
    expect(s().episode).toBeNull()
  })
})
