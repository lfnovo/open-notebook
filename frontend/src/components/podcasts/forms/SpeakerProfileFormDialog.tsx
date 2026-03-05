'use client'

import { useCallback, useEffect } from 'react'
import { Controller, useFieldArray, useForm } from 'react-hook-form'
import type { FieldErrorsImpl } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Plus, Trash2 } from 'lucide-react'

import { SpeakerProfile } from '@/lib/types/podcasts'
import {
  useCreateSpeakerProfile,
  useUpdateSpeakerProfile,
} from '@/lib/hooks/use-podcasts'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Separator } from '@/components/ui/separator'
import { ModelSelector } from '@/components/common/ModelSelector'

import { TranslationKeys } from '@/lib/locales'
import { useTranslation } from '@/lib/hooks/use-translation'

const speakerConfigSchema = (t: TranslationKeys) => z.object({
  name: z.string().min(1, t.common.nameRequired || 'Name is required'),
  voice_id: z.string().min(1, t.podcasts.voiceIdRequired || 'Voice ID is required'),
  backstory: z.string().min(1, t.podcasts.backstoryRequired || 'Backstory is required'),
  personality: z.string().min(1, t.podcasts.personalityRequired || 'Personality is required'),
  voice_model: z.string().nullable().optional(),
})

const speakerProfileSchema = (t: TranslationKeys) => z.object({
  name: z.string().min(1, t.common.nameRequired || 'Name is required'),
  description: z.string().optional(),
  voice_model: z.string().min(1, t.podcasts.voiceModelRequired || 'Voice model is required'),
  speakers: z
    .array(speakerConfigSchema(t))
    .min(1, t.podcasts.speakerCountMin || 'At least one speaker is required')
    .max(4, t.podcasts.speakerCountMax || 'You can configure up to 4 speakers'),
})

export type SpeakerProfileFormValues = z.infer<ReturnType<typeof speakerProfileSchema>>

interface SpeakerProfileFormDialogProps {
  mode: 'create' | 'edit'
  open: boolean
  onOpenChange: (open: boolean) => void
  initialData?: SpeakerProfile
}

const EMPTY_SPEAKER = {
  name: '',
  voice_id: '',
  backstory: '',
  personality: '',
  voice_model: null as string | null,
}

export function SpeakerProfileFormDialog({
  mode,
  open,
  onOpenChange,
  initialData,
}: SpeakerProfileFormDialogProps) {
  const { t } = useTranslation()
  const createProfile = useCreateSpeakerProfile()
  const updateProfile = useUpdateSpeakerProfile()

  const getDefaults = useCallback((): SpeakerProfileFormValues => {
    if (initialData) {
      return {
        name: initialData.name,
        description: initialData.description ?? '',
        voice_model: initialData.voice_model ?? '',
        speakers: initialData.speakers?.map((speaker) => ({
          ...speaker,
          voice_model: speaker.voice_model ?? null,
        })) ?? [{ ...EMPTY_SPEAKER }],
      }
    }

    return {
      name: '',
      description: '',
      voice_model: '',
      speakers: [{ ...EMPTY_SPEAKER }],
    }
  }, [initialData])

  const {
    control,
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<SpeakerProfileFormValues>({
    resolver: zodResolver(speakerProfileSchema(t)),
    defaultValues: getDefaults(),
  })

  const {
    fields,
    append,
    remove,
  } = useFieldArray({
    control,
    name: 'speakers',
  })

  const speakersArrayError = (
    errors.speakers as FieldErrorsImpl<{ root?: { message?: string } }> | undefined
  )?.root?.message

  useEffect(() => {
    if (!open) {
      return
    }
    reset(getDefaults())
  }, [open, reset, getDefaults])

  const onSubmit = async (values: SpeakerProfileFormValues) => {
    const payload = {
      ...values,
      description: values.description ?? '',
      speakers: values.speakers.map((s) => ({
        ...s,
        voice_model: s.voice_model || null,
      })),
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
  const disableSubmit = isSubmitting
  const isEdit = mode === 'edit'

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? t.podcasts.editSpeakerProfile : t.podcasts.createSpeakerProfile}
          </DialogTitle>
          <DialogDescription>
            {t.podcasts.speakerProfileFormDesc}
          </DialogDescription>
        </DialogHeader>

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
              <Label htmlFor="description">{t.common.description}</Label>
              <Textarea
                id="description"
                rows={3}
                placeholder={t.podcasts.descriptionPlaceholder}
                {...register('description')}
              />
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                {t.podcasts.voiceModel}
              </h3>
              <Separator className="mt-2" />
            </div>
            <Controller
              control={control}
              name="voice_model"
              render={({ field }) => (
                <div>
                  <ModelSelector
                    label={`${t.podcasts.voiceModel} *`}
                    modelType="text_to_speech"
                    value={field.value}
                    onChange={field.onChange}
                    placeholder={t.podcasts.selectVoiceModel}
                  />
                  {errors.voice_model ? (
                    <p className="text-xs text-red-600 mt-1">
                      {errors.voice_model.message}
                    </p>
                  ) : null}
                </div>
              )}
            />
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                  {t.podcasts.speakers}
                </h3>
                <p className="text-xs text-muted-foreground">
                  {t.podcasts.speakersDesc}
                </p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => append({ ...EMPTY_SPEAKER })}
                disabled={fields.length >= 4}
              >
                <Plus className="mr-2 h-4 w-4" /> {t.podcasts.addSpeaker}
              </Button>
            </div>
            <Separator />

            {fields.map((field, index) => (
              <div key={field.id} className="rounded-lg border p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-semibold">
                    {t.podcasts.speakerNumber.replace('{number}', (index + 1).toString())}
                  </p>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => remove(index)}
                    disabled={fields.length <= 1}
                    className="text-destructive"
                  >
                    <Trash2 className="mr-2 h-4 w-4" /> {t.common.remove}
                  </Button>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor={`speaker-name-${index}`}>{t.common.name} *</Label>
                    <Input
                      id={`speaker-name-${index}`}
                      {...register(`speakers.${index}.name` as const)}
                      placeholder={t.podcasts.hostPlaceholder.replace('{number}', (index + 1).toString())}
                      autoComplete="off"
                    />
                    {errors.speakers?.[index]?.name ? (
                      <p className="text-xs text-red-600">
                        {errors.speakers[index]?.name?.message}
                      </p>
                    ) : null}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor={`speaker-voice-${index}`}>{t.podcasts.voiceId} *</Label>
                    <Input
                      id={`speaker-voice-${index}`}
                      {...register(`speakers.${index}.voice_id` as const)}
                      placeholder={t.podcasts.voiceIdPlaceholder}
                      autoComplete="off"
                    />
                    <p className="text-xs text-muted-foreground">{t.podcasts.voiceIdHint}</p>
                    {errors.speakers?.[index]?.voice_id ? (
                      <p className="text-xs text-red-600">
                        {errors.speakers[index]?.voice_id?.message}
                      </p>
                    ) : null}
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor={`speaker-backstory-${index}`}>{t.podcasts.backstory} *</Label>
                  <Textarea
                    id={`speaker-backstory-${index}`}
                    rows={3}
                    placeholder={t.podcasts.backstoryPlaceholder}
                    {...register(`speakers.${index}.backstory` as const)}
                    autoComplete="off"
                  />
                  {errors.speakers?.[index]?.backstory ? (
                    <p className="text-xs text-red-600">
                      {errors.speakers[index]?.backstory?.message}
                    </p>
                  ) : null}
                </div>
                <div className="space-y-2">
                  <Label htmlFor={`speaker-personality-${index}`}>{t.podcasts.personality} *</Label>
                  <Textarea
                    id={`speaker-personality-${index}`}
                    rows={3}
                    placeholder={t.podcasts.personalityPlaceholder}
                    {...register(`speakers.${index}.personality` as const)}
                    autoComplete="off"
                  />
                  {errors.speakers?.[index]?.personality ? (
                    <p className="text-xs text-red-600">
                      {errors.speakers[index]?.personality?.message}
                    </p>
                  ) : null}
                </div>
                <Controller
                  control={control}
                  name={`speakers.${index}.voice_model` as const}
                  render={({ field: vmField }) => (
                    <div>
                      <ModelSelector
                        label={t.podcasts.perSpeakerTtsOverride}
                        modelType="text_to_speech"
                        value={vmField.value ?? ''}
                        onChange={(v) => vmField.onChange(v || null)}
                        placeholder={t.podcasts.useProfileDefault}
                      />
                    </div>
                  )}
                />
              </div>
            ))}

            {speakersArrayError ? (
              <p className="text-xs text-red-600">{speakersArrayError}</p>
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
