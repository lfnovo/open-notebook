'use client'

import { useId, useState } from 'react'
import { useForm } from 'react-hook-form'
import { CreateModelRequest, ProviderAvailability } from '@/lib/types/models'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { useCreateModel } from '@/lib/hooks/use-models'
import { Plus } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'

interface AddModelFormProps {
  modelType: 'language' | 'embedding' | 'text_to_speech' | 'speech_to_text'
  providers: ProviderAvailability
}

export function AddModelForm({ modelType, providers }: AddModelFormProps) {
  const { t } = useTranslation()
  const providerSelectId = useId()
  const modelNameInputId = useId()
  const [open, setOpen] = useState(false)
  const createModel = useCreateModel()
  const { register, handleSubmit, formState: { errors }, reset, setValue, watch } = useForm<CreateModelRequest>({
    defaultValues: {
      type: modelType
    }
  })

  // Get available providers that support this model type
  const availableProviders = providers.available.filter(provider =>
    providers.supported_types[provider]?.includes(modelType)
  )

  const onSubmit = async (data: CreateModelRequest) => {
    await createModel.mutateAsync(data)
    reset()
    setOpen(false)
  }

  const getModelTypeName = () => {
    return (t.models as Record<string, string>)[modelType] || modelType.replace(/_/g, ' ')
  }

  const getModelPlaceholder = () => {
    switch (modelType) {
      case 'language':
        return 'e.g., gpt-5-mini, claude, gemini'
      case 'embedding':
        return 'e.g., text-embedding-3-small'
      case 'text_to_speech':
        return 'e.g., tts-gpt-4o-mini-tts, tts-1-hd'
      case 'speech_to_text':
        return 'e.g., whisper-1'
      default:
        return t.models.enterModelName
    }
  }

  if (availableProviders.length === 0) {
    return (
      <div className="text-sm text-muted-foreground">
        {t.models.noProvidersForType.replace('{type}', getModelTypeName())}
      </div>
    )
  }

  const handleOpenChange = (isOpen: boolean) => {
    setOpen(isOpen)
    if (!isOpen) {
      reset()
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button 
          id={`add-model-${modelType}`} 
          name={`add-model-${modelType}`} 
          size="sm"
        >
          <Plus className="h-4 w-4 mr-2" />
          {t.models.addModel}
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {t.models.addSpecificModel.replace('{type}', getModelTypeName())}
          </DialogTitle>
          <DialogDescription>
            {t.models.addSpecificModelDesc.replace('{type}', getModelTypeName())}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <Label htmlFor={providerSelectId}>{t.models.provider}</Label>
            <Select 
              name="provider" 
              onValueChange={(value) => setValue('provider', value)} 
              required
            >
              <SelectTrigger id={providerSelectId}>
                <SelectValue placeholder={t.models.selectProviderPlaceholder} />
              </SelectTrigger>
              <SelectContent>
                {availableProviders.map((provider) => (
                  <SelectItem key={provider} value={provider}>
                    <span className="capitalize">{provider}</span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.provider && (
              <p className="text-sm text-destructive mt-1">{t.models.providerRequired}</p>
            )}
          </div>

          <div>
            <Label htmlFor={modelNameInputId}>{t.models.modelName}</Label>
            <Input
              id={modelNameInputId}
              {...register('name', { required: t.models.modelNameRequired })}
              placeholder={getModelPlaceholder()}
              autoComplete="off"
            />
            {errors.name && (
              <p className="text-sm text-destructive mt-1">{errors.name.message}</p>
            )}
            <p className="text-xs text-muted-foreground mt-1">
              {modelType === 'language' && watch('provider') === 'azure' &&
                t.models.azureHint}
            </p>
          </div>

          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              {t.common.cancel}
            </Button>
            <Button type="submit" disabled={createModel.isPending}>
              {createModel.isPending ? t.models.adding : t.models.addModel}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}