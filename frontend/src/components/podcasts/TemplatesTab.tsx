'use client'

import { useMemo } from 'react'
import { AlertCircle, Loader2 } from 'lucide-react'

import { EpisodeProfilesPanel } from '@/components/podcasts/EpisodeProfilesPanel'
import { SpeakerProfilesPanel } from '@/components/podcasts/SpeakerProfilesPanel'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { useEpisodeProfiles, useSpeakerProfiles } from '@/lib/hooks/use-podcasts'
import { useModels } from '@/lib/hooks/use-models'
import { Model } from '@/lib/types/models'

function modelsByProvider(models: Model[], type: Model['type']) {
  return models
    .filter((model) => model.type === type)
    .reduce<Record<string, string[]>>((acc, model) => {
      if (!acc[model.provider]) {
        acc[model.provider] = []
      }
      acc[model.provider].push(model.name)
      return acc
    }, {})
}

export function TemplatesTab() {
  const {
    episodeProfiles,
    isLoading: loadingEpisodeProfiles,
    error: episodeProfilesError,
  } = useEpisodeProfiles()

  const {
    speakerProfiles,
    usage,
    isLoading: loadingSpeakerProfiles,
    error: speakerProfilesError,
  } = useSpeakerProfiles(episodeProfiles)

  const {
    data: models = [],
    isLoading: loadingModels,
    error: modelsError,
  } = useModels()

  const languageModelOptions = useMemo(
    () => modelsByProvider(models, 'language'),
    [models]
  )
  const ttsModelOptions = useMemo(
    () => modelsByProvider(models, 'text_to_speech'),
    [models]
  )

  const isLoading = loadingEpisodeProfiles || loadingSpeakerProfiles || loadingModels
  const hasError = episodeProfilesError || speakerProfilesError || modelsError

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h2 className="text-xl font-semibold">Templates workspace</h2>
        <p className="text-sm text-muted-foreground">
          Build reusable episode and speaker configurations for fast podcast production.
        </p>
      </div>

      {hasError ? (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Failed to load templates data</AlertTitle>
          <AlertDescription>
            Ensure the API is running and try again. Some sections may be incomplete.
          </AlertDescription>
        </Alert>
      ) : null}

      {isLoading ? (
        <div className="flex items-center gap-3 rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading templates…
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
          <EpisodeProfilesPanel
            episodeProfiles={episodeProfiles}
            speakerProfiles={speakerProfiles}
            modelOptions={languageModelOptions}
          />
          <SpeakerProfilesPanel
            speakerProfiles={speakerProfiles}
            usage={usage}
            modelOptions={ttsModelOptions}
          />
        </div>
      )}
    </div>
  )
}
