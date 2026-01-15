'use client'

import { useCallback, useEffect, useMemo } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

import { EpisodeProfile, SpeakerProfile } from '@/lib/types/podcasts'
import {
  useCreateEpisodeProfile,
  useUpdateEpisodeProfile,
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
import { TranslationKeys } from '@/lib/locales'

const episodeProfileSchema = (t: TranslationKeys) => z.object({
  name: z.string().min(1, t.podcasts.nameRequired || 'Name is required'),
  description: z.string().optional(),
  speaker_config: z.string().min(1, t.podcasts.profileRequired || 'Speaker profile is required'),
  outline_provider: z.string().min(1, t.podcasts.outlineProviderRequired || 'Outline provider is required'),
  outline_model: z.string().min(1, t.podcasts.outlineModelRequired || 'Outline model is required'),
  transcript_provider: z.string().min(1, t.podcasts.transcriptProviderRequired || 'Transcript provider is required'),
  transcript_model: z.string().min(1, t.podcasts.transcriptModelRequired || 'Transcript model is required'),
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
  modelOptions: Record<string, string[]>
  initialData?: EpisodeProfile
}

export function EpisodeProfileFormDialog({
  mode,
  open,
  onOpenChange,
  speakerProfiles,
  modelOptions,
  initialData,
}: EpisodeProfileFormDialogProps) {
  const { t } = useTranslation()
  const createProfile = useCreateEpisodeProfile()
  const updateProfile = useUpdateEpisodeProfile()

  const providers = useMemo(() => Object.keys(modelOptions), [modelOptions])

  const getDefaults = useCallback((): EpisodeProfileFormValues => {
    const firstSpeaker = speakerProfiles[0]?.name ?? ''
    const firstProvider = providers[0] ?? ''
    const firstModel = firstProvider ? modelOptions[firstProvider]?.[0] ?? '' : ''

    if (initialData) {
      return {
        name: initialData.name,
        description: initialData.description ?? '',
        speaker_config: initialData.speaker_config,
        outline_provider: initialData.outline_provider,
        outline_model: initialData.outline_model,
        transcript_provider: initialData.transcript_provider,
        transcript_model: initialData.transcript_model,
        default_briefing: initialData.default_briefing,
        num_segments: initialData.num_segments,
      }
    }

    return {
      name: '',
      description: '',
      speaker_config: firstSpeaker,
      outline_provider: firstProvider,
      outline_model: firstModel,
      transcript_provider: firstProvider,
      transcript_model: firstModel,
      default_briefing: '',
      num_segments: 5,
    }
  }, [initialData, modelOptions, providers, speakerProfiles])

  const {
    control,
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm<EpisodeProfileFormValues>({
    resolver: zodResolver(episodeProfileSchema(t)),
    defaultValues: getDefaults(),
  })

  const outlineProvider = watch('outline_provider')
  const outlineModel = watch('outline_model')
  const transcriptProvider = watch('transcript_provider')
  const transcriptModel = watch('transcript_model')
  const availableOutlineModels = modelOptions[outlineProvider] ?? []
  const availableTranscriptModels = modelOptions[transcriptProvider] ?? []

  useEffect(() => {
    if (!open) {
      return
    }
    reset(getDefaults())
  }, [open, reset, getDefaults])

  useEffect(() => {
    if (!outlineProvider) {
      return
    }
    const models = modelOptions[outlineProvider] ?? []
    if (models.length === 0) {
      setValue('outline_model', '')
      return
    }
    if (!models.includes(outlineModel)) {
      setValue('outline_model', models[0])
    }
  }, [outlineProvider, outlineModel, modelOptions, setValue])

  useEffect(() => {
    if (!transcriptProvider) {
      return
    }
    const models = modelOptions[transcriptProvider] ?? []
    if (models.length === 0) {
      setValue('transcript_model', '')
      return
    }
    if (!models.includes(transcriptModel)) {
      setValue('transcript_model', models[0])
    }
  }, [transcriptProvider, transcriptModel, modelOptions, setValue])

  const onSubmit = async (values: EpisodeProfileFormValues) => {
    const payload = {
      ...values,
      description: values.description ?? '',
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
  const disableSubmit =
    isSubmitting || speakerProfiles.length === 0 || providers.length === 0
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

        {providers.length === 0 ? (
          <Alert className="bg-amber-50 text-amber-900 border-amber-200">
            <AlertTitle>{t.podcasts.noLanguageModelsAvailable}</AlertTitle>
            <AlertDescription>
              {t.podcasts.noLanguageModelsDesc}
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
            <div className="grid gap-4 md:grid-cols-2">
              <Controller
                control={control}
                name="outline_provider"
                render={({ field }) => (
                  <div className="space-y-2">
                    <Label htmlFor="outline_provider">{t.models.provider} *</Label>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <SelectTrigger id="outline_provider">
                        <SelectValue placeholder={t.models.selectProviderPlaceholder} />
                      </SelectTrigger>
                      <SelectContent title={t.models.provider}>
                        {providers.map((provider) => (
                          <SelectItem key={provider} value={provider}>
                            <span className="capitalize">{provider}</span>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {errors.outline_provider ? (
                      <p className="text-xs text-red-600">
                        {errors.outline_provider.message}
                      </p>
                    ) : null}
                  </div>
                )}
              />

              <Controller
                control={control}
                name="outline_model"
                render={({ field }) => (
                  <div className="space-y-2">
                    <Label htmlFor="outline_model">{t.common.model} *</Label>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <SelectTrigger id="outline_model">
                        <SelectValue placeholder={t.models.selectModelPlaceholder} />
                      </SelectTrigger>
                      <SelectContent title={t.common.model}>
                        {availableOutlineModels.map((model) => (
                          <SelectItem key={model} value={model}>
                            {model}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {errors.outline_model ? (
                      <p className="text-xs text-red-600">
                        {errors.outline_model.message}
                      </p>
                    ) : null}
                  </div>
                )}
              />
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                {t.podcasts.transcriptGeneration}
              </h3>
              <Separator className="mt-2" />
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <Controller
                control={control}
                name="transcript_provider"
                render={({ field }) => (
                  <div className="space-y-2">
                    <Label htmlFor="transcript_provider">{t.models.provider} *</Label>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <SelectTrigger id="transcript_provider">
                        <SelectValue placeholder={t.models.selectProviderPlaceholder} />
                      </SelectTrigger>
                      <SelectContent title={t.models.provider}>
                        {providers.map((provider) => (
                          <SelectItem key={provider} value={provider}>
                            <span className="capitalize">{provider}</span>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {errors.transcript_provider ? (
                      <p className="text-xs text-red-600">
                        {errors.transcript_provider.message}
                      </p>
                    ) : null}
                  </div>
                )}
              />

              <Controller
                control={control}
                name="transcript_model"
                render={({ field }) => (
                  <div className="space-y-2">
                    <Label htmlFor="transcript_model">{t.common.model} *</Label>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <SelectTrigger id="transcript_model">
                        <SelectValue placeholder={t.models.selectModelPlaceholder} />
                      </SelectTrigger>
                      <SelectContent title={t.common.model}>
                        {availableTranscriptModels.map((model) => (
                          <SelectItem key={model} value={model}>
                            {model}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {errors.transcript_model ? (
                      <p className="text-xs text-red-600">
                        {errors.transcript_model.message}
                      </p>
                    ) : null}
                  </div>
                )}
              />
            </div>
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
