'use client'

import { useMemo } from 'react'
import { AlertCircle, Lightbulb, Loader2 } from 'lucide-react'

import { EpisodeProfilesPanel } from '@/components/podcasts/EpisodeProfilesPanel'
import { SpeakerProfilesPanel } from '@/components/podcasts/SpeakerProfilesPanel'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { useEpisodeProfiles, useSpeakerProfiles } from '@/lib/hooks/use-podcasts'
import { useModels } from '@/lib/hooks/use-models'
import { Model } from '@/lib/types/models'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'

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

      <Accordion type="single" collapsible className="w-full">
        <AccordionItem 
          value="overview" 
          className="overflow-hidden rounded-xl border border-border bg-muted/40 px-4"
        >
          <AccordionTrigger className="gap-2 py-4 text-left text-sm font-semibold">
            <div className="flex items-center gap-2">
              <Lightbulb className="h-4 w-4 text-primary" />
              How templates power podcast generation
            </div>
          </AccordionTrigger>
          <AccordionContent className="text-sm text-muted-foreground">
            <div className="space-y-4">
              <p className="text-muted-foreground/90">
                Templates split the podcast workflow into two reusable building blocks. Mix and match
                them whenever you generate a new episode.
              </p>

              <div className="space-y-2">
                <h4 className="font-medium text-foreground">Episode profiles set the format</h4>
                <ul className="list-disc space-y-1 pl-5">
                  <li>Outline the number of segments and how the story flows</li>
                  <li>Pick the language models used for briefing, outlining, and script writing</li>
                  <li>Store default briefings so every episode starts with a consistent tone</li>
                </ul>
              </div>

              <div className="space-y-2">
                <h4 className="font-medium text-foreground">Speaker profiles bring voices to life</h4>
                <ul className="list-disc space-y-1 pl-5">
                  <li>Choose the text-to-speech provider and model</li>
                  <li>Capture personality, backstory, and pronunciation notes per speaker</li>
                  <li>Reuse the same host or guest voices across different episode formats</li>
                </ul>
              </div>

              <div className="space-y-2">
                <h4 className="font-medium text-foreground">Recommended workflow</h4>
                <ol className="list-decimal space-y-1 pl-5">
                  <li>Create speaker profiles for each voice you need</li>
                  <li>Build episode profiles that reference those speakers by name</li>
                  <li>Generate podcasts by selecting the episode profile that fits the story</li>
                </ol>
                <p className="text-xs text-muted-foreground/80">
                  Episode profiles reference speaker profiles by name, so starting with speakers avoids
                  missing voice assignments later.
                </p>
              </div>
            </div>
          </AccordionContent>
        </AccordionItem>
      </Accordion>

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
        <div className="grid gap-6 lg:grid-cols-2">
          <SpeakerProfilesPanel
            speakerProfiles={speakerProfiles}
            usage={usage}
            modelOptions={ttsModelOptions}
          />
          <EpisodeProfilesPanel
            episodeProfiles={episodeProfiles}
            speakerProfiles={speakerProfiles}
            modelOptions={languageModelOptions}
          />
        </div>
      )}
    </div>
  )
}
