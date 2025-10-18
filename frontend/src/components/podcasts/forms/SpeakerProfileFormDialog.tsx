'use client'

import { useCallback, useEffect, useMemo } from 'react'
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

const speakerConfigSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  voice_id: z.string().min(1, 'Voice ID is required'),
  backstory: z.string().min(1, 'Backstory is required'),
  personality: z.string().min(1, 'Personality is required'),
})

const speakerProfileSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  description: z.string().optional(),
  tts_provider: z.string().min(1, 'Provider is required'),
  tts_model: z.string().min(1, 'Model is required'),
  speakers: z
    .array(speakerConfigSchema)
    .min(1, 'At least one speaker is required')
    .max(4, 'You can configure up to 4 speakers'),
})

export type SpeakerProfileFormValues = z.infer<typeof speakerProfileSchema>

interface SpeakerProfileFormDialogProps {
  mode: 'create' | 'edit'
  open: boolean
  onOpenChange: (open: boolean) => void
  modelOptions: Record<string, string[]>
  initialData?: SpeakerProfile
}

const EMPTY_SPEAKER = {
  name: '',
  voice_id: '',
  backstory: '',
  personality: '',
}

export function SpeakerProfileFormDialog({
  mode,
  open,
  onOpenChange,
  modelOptions,
  initialData,
}: SpeakerProfileFormDialogProps) {
  const createProfile = useCreateSpeakerProfile()
  const updateProfile = useUpdateSpeakerProfile()

  const providers = useMemo(() => Object.keys(modelOptions), [modelOptions])

  const getDefaults = useCallback((): SpeakerProfileFormValues => {
    const firstProvider = providers[0] ?? ''
    const firstModel = firstProvider ? modelOptions[firstProvider]?.[0] ?? '' : ''

    if (initialData) {
      return {
        name: initialData.name,
        description: initialData.description ?? '',
        tts_provider: initialData.tts_provider,
        tts_model: initialData.tts_model,
        speakers: initialData.speakers?.map((speaker) => ({ ...speaker })) ?? [{ ...EMPTY_SPEAKER }],
      }
    }

    return {
      name: '',
      description: '',
      tts_provider: firstProvider,
      tts_model: firstModel,
      speakers: [{ ...EMPTY_SPEAKER }],
    }
  }, [initialData, modelOptions, providers])

  const {
    control,
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm<SpeakerProfileFormValues>({
    resolver: zodResolver(speakerProfileSchema),
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

  const provider = watch('tts_provider')
  const currentModel = watch('tts_model')
  const availableModels = useMemo(
    () => modelOptions[provider] ?? [],
    [modelOptions, provider]
  )

  const speakersArrayError = (
    errors.speakers as FieldErrorsImpl<{ root?: { message?: string } }> | undefined
  )?.root?.message

  useEffect(() => {
    if (!open) {
      return
    }
    reset(getDefaults())
  }, [open, reset, getDefaults])

  useEffect(() => {
    if (!provider) {
      return
    }
    const models = modelOptions[provider] ?? []
    if (models.length === 0) {
      setValue('tts_model', '')
      return
    }
    if (!models.includes(currentModel)) {
      setValue('tts_model', models[0])
    }
  }, [provider, currentModel, modelOptions, setValue])

  const onSubmit = async (values: SpeakerProfileFormValues) => {
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
  const disableSubmit = isSubmitting || providers.length === 0
  const isEdit = mode === 'edit'

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? 'Edit Speaker Profile' : 'Create Speaker Profile'}
          </DialogTitle>
          <DialogDescription>
            Configure text-to-speech settings and define up to four speakers.
          </DialogDescription>
        </DialogHeader>

        {providers.length === 0 ? (
          <Alert className="bg-amber-50 text-amber-900">
            <AlertTitle>No text-to-speech models available</AlertTitle>
            <AlertDescription>
              Add TTS models in the Models section before creating a speaker profile.
            </AlertDescription>
          </Alert>
        ) : null}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6 pt-2">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="name">Profile name *</Label>
              <Input id="name" placeholder="Weekly show host" {...register('name')} />
              {errors.name ? (
                <p className="text-xs text-red-600">{errors.name.message}</p>
              ) : null}
            </div>

            <div className="space-y-2">
              <Label htmlFor="tts_provider">Provider *</Label>
              <Controller
                control={control}
                name="tts_provider"
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select provider" />
                    </SelectTrigger>
                    <SelectContent>
                      {providers.map((option) => (
                        <SelectItem key={option} value={option}>
                          <span className="capitalize">{option}</span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
              {errors.tts_provider ? (
                <p className="text-xs text-red-600">{errors.tts_provider.message}</p>
              ) : null}
            </div>

            <div className="space-y-2">
              <Label htmlFor="tts_model">Model *</Label>
              <Controller
                control={control}
                name="tts_model"
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select model" />
                    </SelectTrigger>
                    <SelectContent>
                      {availableModels.map((model) => (
                        <SelectItem key={model} value={model}>
                          {model}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
              {errors.tts_model ? (
                <p className="text-xs text-red-600">{errors.tts_model.message}</p>
              ) : null}
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                rows={3}
                placeholder="Notes about tone, brand, or usage"
                {...register('description')}
              />
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                  Speakers
                </h3>
                <p className="text-xs text-muted-foreground">
                  Configure between one and four voices for this profile.
                </p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => append({ ...EMPTY_SPEAKER })}
                disabled={fields.length >= 4}
              >
                <Plus className="mr-2 h-4 w-4" /> Add speaker
              </Button>
            </div>
            <Separator />

            {fields.map((field, index) => (
              <div key={field.id} className="rounded-lg border p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-semibold">Speaker {index + 1}</p>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => remove(index)}
                    disabled={fields.length <= 1}
                    className="text-destructive"
                  >
                    <Trash2 className="mr-2 h-4 w-4" /> Remove
                  </Button>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Name *</Label>
                    <Input
                      {...register(`speakers.${index}.name` as const)}
                      placeholder="Host 1"
                    />
                    {errors.speakers?.[index]?.name ? (
                      <p className="text-xs text-red-600">
                        {errors.speakers[index]?.name?.message}
                      </p>
                    ) : null}
                  </div>
                  <div className="space-y-2">
                    <Label>Voice ID *</Label>
                    <Input
                      {...register(`speakers.${index}.voice_id` as const)}
                      placeholder="voice_123"
                    />
                    {errors.speakers?.[index]?.voice_id ? (
                      <p className="text-xs text-red-600">
                        {errors.speakers[index]?.voice_id?.message}
                      </p>
                    ) : null}
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Backstory *</Label>
                  <Textarea
                    rows={3}
                    placeholder="Short biography or context for the speaker"
                    {...register(`speakers.${index}.backstory` as const)}
                  />
                  {errors.speakers?.[index]?.backstory ? (
                    <p className="text-xs text-red-600">
                      {errors.speakers[index]?.backstory?.message}
                    </p>
                  ) : null}
                </div>
                <div className="space-y-2">
                  <Label>Personality *</Label>
                  <Textarea
                    rows={3}
                    placeholder="Describe style and tone"
                    {...register(`speakers.${index}.personality` as const)}
                  />
                  {errors.speakers?.[index]?.personality ? (
                    <p className="text-xs text-red-600">
                      {errors.speakers[index]?.personality?.message}
                    </p>
                  ) : null}
                </div>
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
              Cancel
            </Button>
            <Button type="submit" disabled={disableSubmit}>
              {isSubmitting
                ? isEdit
                  ? 'Saving…'
                  : 'Creating…'
                : isEdit
                  ? 'Save changes'
                  : 'Create profile'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
