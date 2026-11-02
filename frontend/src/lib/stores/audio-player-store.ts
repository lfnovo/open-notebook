import { create } from 'zustand'

import type { PodcastEpisode } from '@/lib/types/podcasts'

export const SKIP_SECONDS = 15

/** The track the global player is bound to. Audio fields are used to load an authenticated blob. */
export interface PlayerEpisode {
  id: string
  name: string
  notebookId?: string
  audio_url?: PodcastEpisode['audio_url']
  audio_file?: PodcastEpisode['audio_file']
}

interface AudioPlayerState {
  episode: PlayerEpisode | null
  isPlaying: boolean
  currentTime: number
  duration: number
  playbackRate: number
  /** Bumped by seek/skip so the <audio> element knows to apply `currentTime`. */
  seekNonce: number

  play: (episode?: PlayerEpisode) => void
  pause: () => void
  toggle: (episode?: PlayerEpisode) => void
  seek: (seconds: number) => void
  skip: (deltaSeconds: number) => void
  setRate: (rate: number) => void
  stop: () => void

  // Reported by the <audio> element (not user intents)
  syncTime: (currentTime: number) => void
  syncDuration: (duration: number) => void
  ended: () => void
}

const idle = {
  episode: null,
  isPlaying: false,
  currentTime: 0,
  duration: 0,
}

const clamp = (value: number, max: number) =>
  Math.min(Math.max(0, value), max > 0 ? max : Number.POSITIVE_INFINITY)

// Playback state is intentionally not persisted across reloads.
export const useAudioPlayerStore = create<AudioPlayerState>()((set, get) => ({
  ...idle,
  playbackRate: 1,
  seekNonce: 0,

  play: (episode) => {
    const current = get().episode
    if (!episode || (current && current.id === episode.id)) {
      if (current) set({ isPlaying: true })
      return
    }
    set({ episode, isPlaying: true, currentTime: 0, duration: 0 })
  },

  pause: () => set({ isPlaying: false }),

  toggle: (episode) => {
    const { episode: current, isPlaying } = get()
    if (episode && current?.id !== episode.id) {
      get().play(episode)
    } else if (current) {
      set({ isPlaying: !isPlaying })
    }
  },

  seek: (seconds) =>
    set((s) =>
      s.episode
        ? { currentTime: clamp(seconds, s.duration), seekNonce: s.seekNonce + 1 }
        : s
    ),

  skip: (delta) => get().seek(get().currentTime + delta),

  setRate: (rate) => set({ playbackRate: rate }),

  stop: () => set({ ...idle }),

  syncTime: (currentTime) => set({ currentTime }),
  syncDuration: (duration) => set({ duration: Number.isFinite(duration) ? duration : 0 }),
  ended: () => set((s) => ({ isPlaying: false, currentTime: 0, seekNonce: s.seekNonce + 1 })),
}))
