'use client'

import { useEffect, useMemo, useState } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { ChevronDown, Trash2 } from 'lucide-react'

import { resolvePodcastAssetUrl } from '@/lib/api/podcasts'
import {
  EpisodeStatus,
  PodcastEpisode,
  SpeakerVoiceConfig,
} from '@/lib/types/podcasts'
import { cn } from '@/lib/utils'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'

interface EpisodeCardProps {
  episode: PodcastEpisode
  onDelete: (episodeId: string) => Promise<void> | void
  deleting?: boolean
}

const STATUS_META: Record<
  EpisodeStatus | 'unknown',
  { label: string; className: string }
> = {
  running: {
    label: 'Processing',
    className: 'bg-amber-100 text-amber-800 border-amber-200',
  },
  processing: {
    label: 'Processing',
    className: 'bg-amber-100 text-amber-800 border-amber-200',
  },
  completed: {
    label: 'Completed',
    className: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  },
  failed: {
    label: 'Failed',
    className: 'bg-red-100 text-red-800 border-red-200',
  },
  error: {
    label: 'Failed',
    className: 'bg-red-100 text-red-800 border-red-200',
  },
  pending: {
    label: 'Pending',
    className: 'bg-sky-100 text-sky-800 border-sky-200',
  },
  submitted: {
    label: 'Pending',
    className: 'bg-sky-100 text-sky-800 border-sky-200',
  },
  unknown: {
    label: 'Unknown',
    className: 'bg-muted text-muted-foreground border-transparent',
  },
}

function StatusBadge({ status }: { status?: EpisodeStatus | null }) {
  const meta = STATUS_META[status ?? 'unknown']
  return (
    <Badge
      variant="outline"
      className={cn('uppercase tracking-wide', meta.className)}
    >
      {meta.label}
    </Badge>
  )
}

function SectionToggle({
  title,
  defaultOpen = false,
  children,
}: {
  title: string
  defaultOpen?: boolean
  children: React.ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-foreground">{title}</p>
        <CollapsibleTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 w-7 p-0 transition-transform"
          >
            <ChevronDown
              className={cn('h-4 w-4', open ? 'rotate-180' : 'rotate-0')}
            />
          </Button>
        </CollapsibleTrigger>
      </div>
      <CollapsibleContent className="pt-3 text-sm text-muted-foreground">
        {children}
      </CollapsibleContent>
    </Collapsible>
  )
}

function renderSpeaker(speaker: SpeakerVoiceConfig, index: number) {
  return (
    <div key={speaker.name + index} className="rounded-md border bg-muted/30 p-3">
      <p className="text-sm font-medium text-foreground">{speaker.name}</p>
      <p className="text-xs text-muted-foreground">Voice ID: {speaker.voice_id}</p>
      <Separator className="my-3" />
      <p className="text-xs text-muted-foreground whitespace-pre-wrap">
        <span className="font-semibold">Backstory:</span> {speaker.backstory}
      </p>
      <Separator className="my-3" />
      <p className="text-xs text-muted-foreground whitespace-pre-wrap">
        <span className="font-semibold">Personality:</span> {speaker.personality}
      </p>
    </div>
  )
}

export function EpisodeCard({ episode, onDelete, deleting }: EpisodeCardProps) {
  const directAudioUrl = useMemo(
    () => resolvePodcastAssetUrl(episode.audio_url ?? episode.audio_file),
    [episode.audio_file, episode.audio_url]
  )

  const [audioSrc, setAudioSrc] = useState<string | undefined>(directAudioUrl)
  const [audioError, setAudioError] = useState<string | null>(null)

  useEffect(() => {
    let revokeUrl: string | undefined
    setAudioError(null)

    // If backend exposed a protected endpoint, fetch it with auth headers
    const loadProtectedAudio = async () => {
      if (!directAudioUrl || !episode.audio_url) {
        setAudioSrc(directAudioUrl)
        return
      }

      try {
        let token: string | undefined
        if (typeof window !== 'undefined') {
          const raw = window.localStorage.getItem('auth-storage')
          if (raw) {
            try {
              const parsed = JSON.parse(raw)
              token = parsed?.state?.token
            } catch (error) {
              console.error('Failed to parse auth storage', error)
            }
          }
        }

        const headers: HeadersInit = {}
        if (token) {
          headers.Authorization = `Bearer ${token}`
        }

        const response = await fetch(directAudioUrl, { headers })
        if (!response.ok) {
          throw new Error(`Audio request failed with status ${response.status}`)
        }

        const blob = await response.blob()
        revokeUrl = URL.createObjectURL(blob)
        setAudioSrc(revokeUrl)
      } catch (error) {
        console.error('Unable to load podcast audio', error)
        setAudioError('Audio unavailable')
        setAudioSrc(undefined)
      }
    }

    void loadProtectedAudio()

    return () => {
      if (revokeUrl) {
        URL.revokeObjectURL(revokeUrl)
      }
    }
  }, [directAudioUrl, episode.audio_url])

  const createdLabel = episode.created
    ? formatDistanceToNow(new Date(episode.created), {
        addSuffix: true,
      })
    : null

  const handleDelete = () => {
    void onDelete(episode.id)
  }

  return (
    <Card className="shadow-sm">
      <CardHeader className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="space-y-1">
          <CardTitle className="text-lg font-semibold">{episode.name}</CardTitle>
          <CardDescription className="text-sm text-muted-foreground">
            Profile: {episode.episode_profile?.name ?? 'Unknown'}
          </CardDescription>
          {createdLabel && (
            <p className="text-xs text-muted-foreground">Created {createdLabel}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={episode.job_status} />
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="ghost" size="sm" className="text-destructive">
                <Trash2 className="mr-2 h-4 w-4" />
                Delete
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete episode?</AlertDialogTitle>
                <AlertDialogDescription>
                  This will remove “{episode.name}” and its audio file permanently.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={handleDelete} disabled={deleting}>
                  {deleting ? 'Deleting…' : 'Delete'}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {audioSrc ? (
          <div>
            <p className="text-sm font-medium text-foreground mb-2">Audio Preview</p>
            <audio controls preload="none" src={audioSrc} className="w-full" />
          </div>
        ) : audioError ? (
          <p className="text-sm text-destructive">{audioError}</p>
        ) : null}

        <SectionToggle title="Episode Profile">
          <dl className="grid gap-2 text-sm leading-relaxed md:grid-cols-2">
            <div>
              <dt className="font-medium text-foreground">Outline Model</dt>
              <dd>
                {episode.episode_profile?.outline_provider ?? '—'} /
                {' '}
                {episode.episode_profile?.outline_model ?? '—'}
              </dd>
            </div>
            <div>
              <dt className="font-medium text-foreground">Transcript Model</dt>
              <dd>
                {episode.episode_profile?.transcript_provider ?? '—'} /
                {' '}
                {episode.episode_profile?.transcript_model ?? '—'}
              </dd>
            </div>
            <div>
              <dt className="font-medium text-foreground">Segments</dt>
              <dd>{episode.episode_profile?.num_segments ?? '—'}</dd>
            </div>
            <div className="md:col-span-2">
              <dt className="font-medium text-foreground">Briefing Template</dt>
              <dd className="text-sm text-muted-foreground whitespace-pre-wrap">
                {episode.episode_profile?.default_briefing ?? '—'}
              </dd>
            </div>
          </dl>
        </SectionToggle>

        <SectionToggle title="Speaker Profile">
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Provider: {episode.speaker_profile?.tts_provider ?? '—'} /{' '}
              {episode.speaker_profile?.tts_model ?? '—'}
            </p>
            <div className="grid gap-3 md:grid-cols-2">
              {episode.speaker_profile?.speakers?.map(renderSpeaker) ?? null}
            </div>
          </div>
        </SectionToggle>

        {episode.briefing ? (
          <SectionToggle title="Briefing Used" defaultOpen>
            <pre className="whitespace-pre-wrap rounded-md border bg-muted/30 p-4 text-xs leading-relaxed text-muted-foreground">
              {episode.briefing}
            </pre>
          </SectionToggle>
        ) : null}

        {episode.transcript && Object.keys(episode.transcript).length > 0 ? (
          <SectionToggle title="Transcript JSON">
            <ScrollArea className="max-h-64 rounded-md border bg-muted/10">
              <pre className="whitespace-pre text-xs leading-relaxed p-4">
                {JSON.stringify(episode.transcript, null, 2)}
              </pre>
            </ScrollArea>
          </SectionToggle>
        ) : null}

        {episode.outline && Object.keys(episode.outline).length > 0 ? (
          <SectionToggle title="Outline JSON">
            <ScrollArea className="max-h-64 rounded-md border bg-muted/10">
              <pre className="whitespace-pre text-xs leading-relaxed p-4">
                {JSON.stringify(episode.outline, null, 2)}
              </pre>
            </ScrollArea>
          </SectionToggle>
        ) : null}
      </CardContent>
    </Card>
  )
}
