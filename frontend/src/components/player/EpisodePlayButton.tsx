'use client'

import { Pause, Play } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { formatTime } from '@/components/player/format-time'
import { PLAYER_LABELS } from '@/components/player/player-labels'
import { useAudioPlayerStore, type PlayerEpisode } from '@/lib/stores/audio-player-store'
import { cn } from '@/lib/utils'

/**
 * Play/pause + progress for one episode, bound to the global audio player.
 * Idle unless the store's current episode is this one.
 */
export function EpisodePlayButton({
  episode,
  className,
}: {
  episode: PlayerEpisode
  className?: string
}) {
  const isCurrent = useAudioPlayerStore((s) => s.episode?.id === episode.id)
  const isPlaying = useAudioPlayerStore((s) => s.episode?.id === episode.id && s.isPlaying)
  const currentTime = useAudioPlayerStore((s) => (s.episode?.id === episode.id ? s.currentTime : 0))
  const duration = useAudioPlayerStore((s) => (s.episode?.id === episode.id ? s.duration : 0))
  const toggle = useAudioPlayerStore((s) => s.toggle)

  const pct = duration > 0 ? Math.min(100, (currentTime / duration) * 100) : 0

  return (
    <div className={cn('flex items-center gap-3', className)} data-testid="episode-play-button">
      <Button
        type="button"
        size="icon"
        variant="outline"
        className="h-9 w-9 flex-shrink-0 rounded-full"
        aria-label={isPlaying ? PLAYER_LABELS.pause : PLAYER_LABELS.play}
        aria-pressed={isPlaying}
        onClick={() => toggle(episode)}
      >
        {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
      </Button>
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted" aria-hidden="true">
        <div className="h-full bg-fern" style={{ width: `${pct}%` }} />
      </div>
      <span className="w-24 flex-shrink-0 text-right text-xs tabular-nums text-muted-foreground">
        {isCurrent ? `${formatTime(currentTime)} / ${formatTime(duration)}` : ''}
      </span>
    </div>
  )
}
