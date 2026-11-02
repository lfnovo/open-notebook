'use client'

import { useEffect, useRef } from 'react'
import Link from 'next/link'
import { toast } from 'sonner'
import { Pause, Play, RotateCcw, RotateCw, X } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { formatTime } from '@/components/player/format-time'
import { PLAYER_LABELS } from '@/components/player/player-labels'
import { useEpisodeAudio } from '@/lib/hooks/use-episode-audio'
import { useTranslation } from '@/lib/hooks/use-translation'
import { SKIP_SECONDS, useAudioPlayerStore } from '@/lib/stores/audio-player-store'

/**
 * The single app-level <audio> + mini-player bar. Mounted once in the
 * dashboard layout so playback survives client-side navigation.
 */
export function GlobalAudioPlayer() {
  const { t } = useTranslation()
  const episode = useAudioPlayerStore((s) => s.episode)
  const isPlaying = useAudioPlayerStore((s) => s.isPlaying)
  const currentTime = useAudioPlayerStore((s) => s.currentTime)
  const duration = useAudioPlayerStore((s) => s.duration)
  const playbackRate = useAudioPlayerStore((s) => s.playbackRate)
  const seekNonce = useAudioPlayerStore((s) => s.seekNonce)
  const { toggle, pause, play, seek, skip, stop, syncTime, syncDuration, ended } =
    useAudioPlayerStore.getState()

  const audioRef = useRef<HTMLAudioElement>(null)
  // Latest currentTime for the seek effect without re-running it on every tick.
  const timeRef = useRef(currentTime)
  timeRef.current = currentTime

  const { audioSrc, audioError } = useEpisodeAudio(episode ?? {}, !!episode)
  const hasTrack = !!episode

  // Failed load -> toast + reset
  useEffect(() => {
    if (audioError) {
      toast.error(audioError)
      stop()
    }
  }, [audioError, stop])

  // Intent -> element
  useEffect(() => {
    const el = audioRef.current
    if (!el || !audioSrc) return
    if (isPlaying) {
      const p = el.play()
      if (p && typeof p.catch === 'function') {
        p.catch((err: unknown) => {
          if (err instanceof DOMException && err.name === 'AbortError') return
          console.error('Unable to start podcast audio', err)
          pause()
        })
      }
    } else {
      el.pause()
    }
  }, [isPlaying, audioSrc, pause])

  useEffect(() => {
    if (audioRef.current) audioRef.current.playbackRate = playbackRate
  }, [playbackRate, audioSrc])

  // seek/skip/ended -> element
  useEffect(() => {
    const el = audioRef.current
    if (el && seekNonce > 0) el.currentTime = timeRef.current
  }, [seekNonce])

  // Fixed bar must not cover page content: AppShell subtracts this offset.
  useEffect(() => {
    if (!hasTrack) return
    const root = document.documentElement
    root.style.setProperty('--player-offset', '4rem')
    return () => {
      root.style.removeProperty('--player-offset')
    }
  }, [hasTrack])

  // OS media keys / lock screen
  useEffect(() => {
    if (!episode || typeof navigator === 'undefined' || !('mediaSession' in navigator)) return
    const ms = navigator.mediaSession
    try {
      if (typeof MediaMetadata !== 'undefined') {
        ms.metadata = new MediaMetadata({ title: episode.name, artist: 'Open Notebook' })
      }
      ms.setActionHandler('play', () => play())
      ms.setActionHandler('pause', () => pause())
      ms.setActionHandler('seekbackward', () => skip(-SKIP_SECONDS))
      ms.setActionHandler('seekforward', () => skip(SKIP_SECONDS))
    } catch {
      // some browsers lack individual actions
    }
    return () => {
      try {
        ;(['play', 'pause', 'seekbackward', 'seekforward'] as const).forEach((a) =>
          ms.setActionHandler(a, null)
        )
        ms.metadata = null
      } catch {
        // ignore
      }
    }
  }, [episode, play, pause, skip])

  useEffect(() => {
    if (typeof navigator === 'undefined' || !('mediaSession' in navigator)) return
    navigator.mediaSession.playbackState = hasTrack ? (isPlaying ? 'playing' : 'paused') : 'none'
  }, [hasTrack, isPlaying])

  if (!episode) return null

  const loading = !audioSrc
  const href = episode.notebookId ? `/notebooks/${encodeURIComponent(episode.notebookId)}` : null

  return (
    <div
      role="region"
      aria-label={PLAYER_LABELS.player}
      className="fixed inset-x-0 bottom-0 z-50 flex h-16 items-center gap-2 border-t bg-card px-3 shadow-lg sm:gap-3 sm:px-4"
      data-testid="mini-player"
    >
      <audio
        key={episode.id}
        ref={audioRef}
        src={audioSrc}
        preload="auto"
        onTimeUpdate={(e) => syncTime(e.currentTarget.currentTime)}
        onLoadedMetadata={(e) => syncDuration(e.currentTarget.duration)}
        onDurationChange={(e) => syncDuration(e.currentTarget.duration)}
        onEnded={() => ended()}
        onError={() => {
          if (!audioSrc) return
          toast.error(t('podcasts.audioUnavailable'))
          stop()
        }}
      />

      <div className="min-w-0 flex-1 sm:flex-none sm:basis-64">
        {href ? (
          <Link href={href} className="block truncate text-sm font-medium hover:underline">
            {episode.name}
          </Link>
        ) : (
          <span className="block truncate text-sm font-medium">{episode.name}</span>
        )}
      </div>

      <div className="flex items-center gap-1">
        <Button type="button" variant="ghost" size="icon" className="h-8 w-8"
          aria-label={PLAYER_LABELS.back15} onClick={() => skip(-SKIP_SECONDS)}>
          <RotateCcw className="h-4 w-4" />
        </Button>
        <Button type="button" size="icon" className="h-9 w-9 rounded-full"
          aria-label={isPlaying ? PLAYER_LABELS.pause : PLAYER_LABELS.play}
          disabled={loading && !isPlaying} onClick={() => toggle()}>
          {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
        </Button>
        <Button type="button" variant="ghost" size="icon" className="h-8 w-8"
          aria-label={PLAYER_LABELS.forward15} onClick={() => skip(SKIP_SECONDS)}>
          <RotateCw className="h-4 w-4" />
        </Button>
      </div>

      <div className="hidden flex-1 items-center gap-2 sm:flex">
        <span className="w-12 text-right text-xs tabular-nums text-muted-foreground">
          {formatTime(currentTime)}
        </span>
        <input
          type="range"
          aria-label={PLAYER_LABELS.seek}
          className="h-1.5 flex-1 cursor-pointer accent-fern"
          min={0}
          max={duration || 0}
          step={1}
          value={Math.min(currentTime, duration || 0)}
          disabled={!duration}
          onChange={(e) => seek(Number(e.target.value))}
        />
        <span className="w-12 text-xs tabular-nums text-muted-foreground">
          {formatTime(duration)}
        </span>
      </div>

      <Button type="button" variant="ghost" size="icon" className="h-8 w-8"
        aria-label={t('common.close')} onClick={() => stop()}>
        <X className="h-4 w-4" />
      </Button>
    </div>
  )
}
