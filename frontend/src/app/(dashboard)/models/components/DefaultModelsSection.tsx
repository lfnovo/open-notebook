'use client'

import { useEffect, useState, useId } from 'react'
import { useForm } from 'react-hook-form'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { ModelDefaults, Model } from '@/lib/types/models'
import { useUpdateModelDefaults, useAutoAssignDefaults } from '@/lib/hooks/use-models'
import { AlertCircle, X, Wand2, Loader2 } from 'lucide-react'
import { EmbeddingModelChangeDialog } from './EmbeddingModelChangeDialog'
import { useTranslation } from '@/lib/hooks/use-translation'

interface DefaultModelsSectionProps {
  models: Model[]
  defaults: ModelDefaults
}

export function DefaultModelsSection({ models, defaults }: DefaultModelsSectionProps) {
  const { t } = useTranslation()
  const updateDefaults = useUpdateModelDefaults()
  const autoAssign = useAutoAssignDefaults()
  const { setValue, watch } = useForm<ModelDefaults>({
    defaultValues: defaults
  })

  interface DefaultConfig {
    key: keyof ModelDefaults
    label: string
    description: string
    modelType: 'language' | 'embedding' | 'text_to_speech' | 'speech_to_text'
    required?: boolean
    id: string
  }

  const generatedId = useId()

  const defaultConfigs: DefaultConfig[] = [
    {
      key: 'default_chat_model',
      label: t.models.chatModelLabel,
      description: t.models.chatModelDesc,
      modelType: 'language',
      required: true,
      id: `${generatedId}-chat`,
    },
    {
      key: 'default_transformation_model',
      label: t.models.transformationModelLabel,
      description: t.models.transformationModelDesc,
      modelType: 'language',
      required: true,
      id: `${generatedId}-transformation`,
    },
    {
      key: 'default_tools_model',
      label: t.models.toolsModelLabel,
      description: t.models.toolsModelDesc,
      modelType: 'language',
      id: `${generatedId}-tools`,
    },
    {
      key: 'large_context_model',
      label: t.models.largeContextModelLabel,
      description: t.models.largeContextModelDesc,
      modelType: 'language',
      id: `${generatedId}-large-context`,
    },
    {
      key: 'default_embedding_model',
      label: t.models.embeddingModelLabel,
      description: t.models.embeddingModelDesc,
      modelType: 'embedding',
      required: true,
      id: `${generatedId}-embedding`,
    },
    {
      key: 'default_text_to_speech_model',
      label: t.models.ttsModelLabel,
      description: t.models.ttsModelDesc,
      modelType: 'text_to_speech',
      id: `${generatedId}-tts`,
    },
    {
      key: 'default_speech_to_text_model',
      label: t.models.sttModelLabel,
      description: t.models.sttModelDesc,
      modelType: 'speech_to_text',
      id: `${generatedId}-stt`,
    },
  ]

  // State for embedding model change dialog
  const [showEmbeddingDialog, setShowEmbeddingDialog] = useState(false)
  const [pendingEmbeddingChange, setPendingEmbeddingChange] = useState<{
    key: keyof ModelDefaults
    value: string
    oldModelId?: string
    newModelId?: string
  } | null>(null)

  // Update form when defaults change
  useEffect(() => {
    if (defaults) {
      Object.entries(defaults).forEach(([key, value]) => {
        setValue(key as keyof ModelDefaults, value)
      })
    }
  }, [defaults, setValue])

  const handleChange = (key: keyof ModelDefaults, value: string) => {
    // Special handling for embedding model changes
    if (key === 'default_embedding_model') {
      const currentEmbeddingModel = defaults[key]

      // Only show dialog if there's an existing embedding model and it's changing
      if (currentEmbeddingModel && currentEmbeddingModel !== value) {
        setPendingEmbeddingChange({
          key,
          value,
          oldModelId: currentEmbeddingModel,
          newModelId: value
        })
        setShowEmbeddingDialog(true)
        return
      }
    }

    // For all other changes or new embedding model assignment
    const newDefaults = { [key]: value || null }
    updateDefaults.mutate(newDefaults)
  }

  const handleConfirmEmbeddingChange = () => {
    if (pendingEmbeddingChange) {
      const newDefaults = {
        [pendingEmbeddingChange.key]: pendingEmbeddingChange.value || null
      }
      updateDefaults.mutate(newDefaults)
      setPendingEmbeddingChange(null)
    }
  }

  const handleCancelEmbeddingChange = () => {
    setPendingEmbeddingChange(null)
    setShowEmbeddingDialog(false)
  }

  const getModelsForType = (type: 'language' | 'embedding' | 'text_to_speech' | 'speech_to_text') => {
    return models.filter(model => model.type === type)
  }

  const missingRequired = defaultConfigs
    .filter(config => {
      if (!config.required) return false
      const value = defaults[config.key]
      if (!value) return true
      // Check if the model still exists
      const modelsOfType = models.filter(m => m.type === config.modelType)
      return !modelsOfType.some(m => m.id === value)
    })
    .map(config => config.label)

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t.models.defaultAssignments}</CardTitle>
        <CardDescription>
          {t.models.defaultAssignmentsDesc}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {missingRequired.length > 0 && (
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="flex items-center justify-between gap-4">
              <span>{t.models.missingRequiredModels.replace('{models}', missingRequired.join(', '))}</span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => autoAssign.mutate()}
                disabled={autoAssign.isPending}
                className="shrink-0 gap-1.5"
              >
                {autoAssign.isPending ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Wand2 className="h-3.5 w-3.5" />
                )}
                {autoAssign.isPending ? t.models.autoAssigning : t.models.autoAssign}
              </Button>
            </AlertDescription>
          </Alert>
        )}

        <div className="grid gap-6 md:grid-cols-2">
          {defaultConfigs.map((config) => {
            const availableModels = getModelsForType(config.modelType)
            const currentValue = watch(config.key) || undefined
            
            // Check if the current value exists in available models
            const isValidModel = currentValue && availableModels.some(m => m.id === currentValue)

            return (
              <div key={config.key} className="space-y-2">
                <Label htmlFor={config.id}>
                  {config.label}
                  {config.required && <span className="text-destructive ml-1">*</span>}
                </Label>
                <div className="flex gap-2">
                  <Select
                    value={currentValue || ""}
                    onValueChange={(value) => handleChange(config.key, value)}
                  >
                    <SelectTrigger 
                      id={config.id}
                      className={
                        config.required && !isValidModel && availableModels.length > 0
                          ? 'border-destructive' 
                          : ''
                      }
                    >
                      <SelectValue placeholder={
                        config.required && !isValidModel && availableModels.length > 0 
                          ? t.models.requiredModelPlaceholder
                          : t.models.selectModelPlaceholder
                      } />
                    </SelectTrigger>
                    <SelectContent>
                      {availableModels.sort((a, b) => a.name.localeCompare(b.name)).map((model) => (
                        <SelectItem key={model.id} value={model.id}>
                          <div className="flex items-center justify-between w-full">
                            <span>{model.name}</span>
                            <span className="text-xs text-muted-foreground ml-2">
                              {model.provider}
                            </span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {!config.required && currentValue && (
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleChange(config.key, "")}
                      className="h-10 w-10"
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  )}
                </div>
                <p className="text-xs text-muted-foreground">{config.description}</p>
              </div>
            )
          })}
        </div>

        <div className="pt-4 border-t">
          <a
            href="https://github.com/lfnovo/open-notebook/blob/main/docs/5-CONFIGURATION/ai-providers.md"
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-primary hover:underline"
          >
            {t.models.whichModelToChoose}
          </a>
        </div>
      </CardContent>

      {/* Embedding Model Change Dialog */}
      <EmbeddingModelChangeDialog
        open={showEmbeddingDialog}
        onOpenChange={(open) => {
          if (!open) {
            handleCancelEmbeddingChange()
          }
        }}
        onConfirm={handleConfirmEmbeddingChange}
        oldModelName={
          pendingEmbeddingChange?.oldModelId
            ? models.find(m => m.id === pendingEmbeddingChange.oldModelId)?.name
            : undefined
        }
        newModelName={
          pendingEmbeddingChange?.newModelId
            ? models.find(m => m.id === pendingEmbeddingChange.newModelId)?.name
            : undefined
        }
      />
    </Card>
  )
}