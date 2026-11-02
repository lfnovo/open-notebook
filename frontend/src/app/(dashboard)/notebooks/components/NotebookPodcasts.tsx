'use client'

import { useState } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { Mic, Plus } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { EpisodeProgress, isEpisodeInProgress } from '@/components/podcasts/EpisodeProgress'
import { GeneratePodcastDialog } from '@/components/podcasts/GeneratePodcastDialog'
import { EpisodePlayButton } from '@/components/player/EpisodePlayButton'
import { usePodcastEpisodes } from '@/lib/hooks/use-podcasts'
import { useTranslation } from '@/lib/hooks/use-translation'
import { FAILED_EPISODE_STATUSES, type PodcastEpisode } from '@/lib/types/podcasts'
import { getDateLocale } from '@/lib/utils/date-locale'

function NotebookEpisodeItem({ episode }: { episode: PodcastEpisode }) {
  const { t, language } = useTranslation()
  const completed = episode.job_status === 'completed'
  const inProgress = isEpisodeInProgress(episode.job_status)
  const failed = !!episode.job_status && FAILED_EPISODE_STATUSES.includes(episode.job_status)

  const created = episode.created
    ? formatDistanceToNow(new Date(episode.created), {
        addSuffix: true,
        locale: getDateLocale(language),
      })
    : null

  return (
    <div className="space-y-2 rounded-md border bg-card p-3" data-testid="notebook-episode">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h4 className="truncate text-sm font-medium">{episode.name}</h4>
          {created ? (
            <p className="text-xs text-muted-foreground">{t('podcasts.created', { time: created })}</p>
          ) : null}
        </div>
        {failed ? (
          <Badge variant="outline" className="border-destructive/30 bg-destructive-tint text-xs uppercase text-destructive">
            {t('podcasts.failedLabel')}
          </Badge>
        ) : inProgress ? (
          <Badge variant="outline" className="border-warn/30 bg-warn-tint text-xs uppercase text-warn">
            {t('podcasts.processingLabel')}
          </Badge>
        ) : null}
      </div>

      <EpisodeProgress status={episode.job_status} progress={episode.progress} />

      {completed && (episode.audio_url || episode.audio_file) ? (
        <EpisodePlayButton
          episode={{
            id: episode.id,
            name: episode.name,
            notebookId: episode.notebook_id ?? undefined,
            audio_url: episode.audio_url,
            audio_file: episode.audio_file,
          }}
        />
      ) : null}
    </div>
  )
}

export function NotebookPodcasts({ notebookId }: { notebookId: string }) {
  const { t } = useTranslation()
  const [dialogOpen, setDialogOpen] = useState(false)
  // Polls while any episode is in progress (see usePodcastEpisodes).
  const { episodes, isLoading } = usePodcastEpisodes({ notebookId })

  return (
    <section className="mt-6 space-y-3" aria-label={t('podcasts.notebookPodcasts')}>
      <div className="flex items-center justify-between gap-2">
        <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.13em] text-muted-foreground">
          <Mic className="h-3.5 w-3.5" />
          {t('podcasts.notebookPodcasts')}
        </h3>
        <Button size="sm" variant="outline" onClick={() => setDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          {t('podcasts.generateBtn')}
        </Button>
      </div>

      {isLoading ? null : episodes.length === 0 ? (
        <p className="rounded-md border border-dashed p-4 text-center text-sm text-muted-foreground">
          {t('podcasts.noNotebookPodcasts')}
        </p>
      ) : (
        <div className="space-y-2">
          {episodes.map((episode) => (
            <NotebookEpisodeItem key={episode.id} episode={episode} />
          ))}
        </div>
      )}

      <GeneratePodcastDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        defaultNotebookId={notebookId}
      />
    </section>
  )
}
