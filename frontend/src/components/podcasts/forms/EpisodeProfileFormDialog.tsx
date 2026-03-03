'use client'

import { useCallback, useEffect } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

import { EpisodeProfile, SpeakerProfile } from '@/lib/types/podcasts'
import {
  useCreateEpisodeProfile,
  useUpdateEpisodeProfile,
  useLanguages,
} from '@/lib/hooks/use-podcasts'
import { useTranslation } from '@/lib/hooks/use-translation'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Separator } from '@/components/ui/separator'
import { ModelSelector } from '@/components/common/ModelSelector'
import { TranslationKeys } from '@/lib/locales'

const episodeProfileSchema = (t: TranslationKeys) => z.object({
  name: z.string().min(1, t.podcasts.nameRequired || 'Name is required'),
  description: z.string().optional(),
  speaker_config: z.string().min(1, t.podcasts.profileRequired || 'Speaker profile is required'),
  outline_llm: z.string().min(1, t.podcasts.outlineModelRequired || 'Outline model is required'),
  transcript_llm: z.string().min(1, t.podcasts.transcriptModelRequired || 'Transcript model is required'),
  language: z.string().nullable().optional(),
  default_briefing: z.string().min(1, t.podcasts.defaultBriefingRequired || 'Default briefing is required'),
  num_segments: z.number()
    .int(t.podcasts.segmentsInteger || 'Must be an integer')
    .min(3, t.podcasts.segmentsMin || 'At least 3 segments')
    .max(20, t.podcasts.segmentsMax || 'Maximum 20 segments'),
})

export type EpisodeProfileFormValues = z.infer<ReturnType<typeof episodeProfileSchema>>

interface EpisodeProfileFormDialogProps {
  mode: 'create' | 'edit'
  open: boolean
  onOpenChange: (open: boolean) => void
  speakerProfiles: SpeakerProfile[]
  initialData?: EpisodeProfile
}

export function EpisodeProfileFormDialog({
  mode,
  open,
  onOpenChange,
  speakerProfiles,
  initialData,
}: EpisodeProfileFormDialogProps) {
  const { t } = useTranslation()
  const createProfile = useCreateEpisodeProfile()
  const updateProfile = useUpdateEpisodeProfile()
  const { data: languages = [] } = useLanguages()

  const getDefaults = useCallback((): EpisodeProfileFormValues => {
    const firstSpeaker = speakerProfiles[0]?.name ?? ''

    if (initialData) {
      return {
        name: initialData.name,
        description: initialData.description ?? '',
        speaker_config: initialData.speaker_config,
        outline_llm: initialData.outline_llm ?? '',
        transcript_llm: initialData.transcript_llm ?? '',
        language: initialData.language ?? null,
        default_briefing: initialData.default_briefing,
        num_segments: initialData.num_segments,
      }
    }

    return {
      name: '',
      description: '',
      speaker_config: firstSpeaker,
      outline_llm: '',
      transcript_llm: '',
      language: null,
      default_briefing: '',
      num_segments: 5,
    }
  }, [initialData, speakerProfiles])

  const {
    control,
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<EpisodeProfileFormValues>({
    resolver: zodResolver(episodeProfileSchema(t)),
    defaultValues: getDefaults(),
  })

  useEffect(() => {
    if (!open) {
      return
    }
    reset(getDefaults())
  }, [open, reset, getDefaults])

  const onSubmit = async (values: EpisodeProfileFormValues) => {
    const payload = {
      ...values,
      description: values.description ?? '',
      language: values.language || null,
    }

    if (mode === 'create') {
      await createProfile.mutateAsync(payload)
    } else if (initialData) {
      await updateProfile.mutateAsync({
        profileId: initialData.id,
        payload,
      })
    }

    onOpenChange(false)
  }

  const isSubmitting = createProfile.isPending || updateProfile.isPending
  const disableSubmit = isSubmitting || speakerProfiles.length === 0
  const isEdit = mode === 'edit'

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? t.podcasts.editEpisodeProfile : t.podcasts.createEpisodeProfile}
          </DialogTitle>
          <DialogDescription>
            {t.podcasts.episodeProfileFormDesc}
          </DialogDescription>
        </DialogHeader>

        {speakerProfiles.length === 0 ? (
          <Alert className="bg-amber-50 text-amber-900 border-amber-200">
            <AlertTitle>{t.podcasts.noSpeakerProfilesAvailable}</AlertTitle>
            <AlertDescription>
              {t.podcasts.noSpeakerProfilesDesc}
            </AlertDescription>
          </Alert>
        ) : null}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6 pt-2">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="name">{t.podcasts.profileName} *</Label>
              <Input id="name" placeholder={t.podcasts.profileNamePlaceholder} {...register('name')} />
              {errors.name ? (
                <p className="text-xs text-red-600">{errors.name.message}</p>
              ) : null}
            </div>

            <div className="space-y-2">
              <Label htmlFor="num_segments">{t.podcasts.segments} *</Label>
              <Input
                id="num_segments"
                type="number"
                min={3}
                max={20}
                {...register('num_segments', { valueAsNumber: true })}
                autoComplete="off"
              />
              {errors.num_segments ? (
                <p className="text-xs text-red-600">{errors.num_segments.message}</p>
              ) : null}
            </div>

            <div className="md:col-span-2 space-y-2">
              <Label htmlFor="description">{t.common.description}</Label>
              <Textarea
                id="description"
                rows={3}
                placeholder={t.podcasts.descriptionPlaceholder}
                {...register('description')}
                autoComplete="off"
              />
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                {t.podcasts.speakerConfig}
              </h3>
              <Separator className="mt-2" />
            </div>
            <Controller
              control={control}
              name="speaker_config"
              render={({ field }) => (
                <div className="space-y-2">
                  <Label htmlFor="speaker_config">{t.podcasts.speakerProfile} *</Label>
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger id="speaker_config">
                      <SelectValue placeholder={t.podcasts.selectSpeakerProfile} />
                    </SelectTrigger>
                    <SelectContent title={t.podcasts.speakerProfile}>
                      {speakerProfiles.map((profile) => (
                        <SelectItem key={profile.id} value={profile.name}>
                          {profile.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {errors.speaker_config ? (
                    <p className="text-xs text-red-600">
                      {errors.speaker_config.message}
                    </p>
                  ) : null}
                </div>
              )}
            />
          </div>

          <div className="space-y-4">
            <div>
              <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                {t.podcasts.outlineGeneration}
              </h3>
              <Separator className="mt-2" />
            </div>
            <Controller
              control={control}
              name="outline_llm"
              render={({ field }) => (
                <div>
                  <ModelSelector
                    label={`${t.podcasts.outlineModel} *`}
                    modelType="language"
                    value={field.value}
                    onChange={field.onChange}
                    placeholder={t.podcasts.selectOutlineModel}
                  />
                  {errors.outline_llm ? (
                    <p className="text-xs text-red-600 mt-1">
                      {errors.outline_llm.message}
                    </p>
                  ) : null}
                </div>
              )}
            />
          </div>

          <div className="space-y-4">
            <div>
              <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                {t.podcasts.transcriptGeneration}
              </h3>
              <Separator className="mt-2" />
            </div>
            <Controller
              control={control}
              name="transcript_llm"
              render={({ field }) => (
                <div>
                  <ModelSelector
                    label={`${t.podcasts.transcriptModel} *`}
                    modelType="language"
                    value={field.value}
                    onChange={field.onChange}
                    placeholder={t.podcasts.selectTranscriptModel}
                  />
                  {errors.transcript_llm ? (
                    <p className="text-xs text-red-600 mt-1">
                      {errors.transcript_llm.message}
                    </p>
                  ) : null}
                </div>
              )}
            />
          </div>

          <div className="space-y-4">
            <div>
              <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                {t.podcasts.podcastLanguage}
              </h3>
              <Separator className="mt-2" />
            </div>
            <Controller
              control={control}
              name="language"
              render={({ field }) => (
                <div className="space-y-2">
                  <Label htmlFor="language">{t.podcasts.language}</Label>
                  <Select
                    value={field.value ?? ''}
                    onValueChange={(v) => field.onChange(v || null)}
                  >
                    <SelectTrigger id="language">
                      <SelectValue placeholder={t.podcasts.languagePlaceholder} />
                    </SelectTrigger>
                    <SelectContent title={t.podcasts.language}>
                      {languages.map((lang) => (
                        <SelectItem key={lang.code} value={lang.code}>
                          {lang.name} ({lang.code})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="default_briefing">{t.podcasts.defaultBriefingTitle} *</Label>
            <Textarea
              id="default_briefing"
              rows={6}
              placeholder={t.podcasts.defaultBriefingPlaceholder}
              {...register('default_briefing')}
            />
            {errors.default_briefing ? (
              <p className="text-xs text-red-600">
                {errors.default_briefing.message}
              </p>
            ) : null}
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              {t.common.cancel}
            </Button>
            <Button type="submit" disabled={disableSubmit}>
              {isSubmitting
                ? t.common.saving
                : isEdit
                  ? t.common.saveChanges
                  : t.podcasts.createProfile}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
