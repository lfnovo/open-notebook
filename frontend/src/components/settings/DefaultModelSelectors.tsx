'use client'

import { useState, useEffect, useId } from 'react'
import { useForm } from 'react-hook-form'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { Loader2, X, AlertCircle, Wand2 } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useUpdateModelDefaults, useAutoAssignDefaults } from '@/lib/hooks/use-models'
import { Model, ModelDefaults } from '@/lib/types/models'
import { ModelType } from '@/lib/providers'
import { EmbeddingModelChangeDialog } from './EmbeddingModelChangeDialog'

interface DefaultConfig {
  key: keyof ModelDefaults
  label: string
  description: string
  modelType: ModelType
  required?: boolean
  /** When unset, this default falls back to the chat default (see open_notebook/ai/models.py). */
  fallsBackToChat?: boolean
  id: string
}

// Radix Select reserves "" for "no selection", so the clear option needs a sentinel.
const NONE_VALUE = '__none__'

interface DefaultModelSelectProps {
  config: DefaultConfig
  available: Model[]
  currentValue?: string
  onChange: (key: keyof ModelDefaults, value: string) => void
  showDescription?: boolean
}

function DefaultModelSelect({
  config,
  available,
  currentValue,
  onChange,
  showDescription,
}: DefaultModelSelectProps) {
  const { t } = useTranslation()
  const isValid = currentValue && available.some(m => m.id === currentValue)

  return (
    <div className="space-y-1">
      <Label htmlFor={config.id} className="text-xs">
        {config.label}
        {config.required && <span className="text-destructive ml-0.5">*</span>}
      </Label>
      <div className="flex gap-1">
        <Select
          value={currentValue || (config.required ? "" : NONE_VALUE)}
          onValueChange={(v) => onChange(config.key, v === NONE_VALUE ? "" : v)}
        >
          <SelectTrigger
            id={config.id}
            className={`h-8 text-xs ${config.required && !isValid && available.length > 0 ? 'border-destructive' : ''}`}
          >
            <SelectValue placeholder={
              config.required && !isValid && available.length > 0
                ? t('models.requiredModelPlaceholder')
                : t('models.selectModelPlaceholder')
            } />
          </SelectTrigger>
          <SelectContent>
            {!config.required && (
              <SelectItem value={NONE_VALUE}>
                <span className="text-muted-foreground">
                  {config.fallsBackToChat ? t('models.noneFallbackToChat') : t('models.noneOption')}
                </span>
              </SelectItem>
            )}
            {available.sort((a, b) => a.name.localeCompare(b.name)).map(model => (
              <SelectItem key={model.id} value={model.id}>
                <div className="flex items-center justify-between w-full">
                  <span>{model.name}</span>
                  <span className="text-xs text-muted-foreground ml-2">{model.provider}</span>
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {!config.required && currentValue && (
          <Button variant="ghost" size="icon" onClick={() => onChange(config.key, "")} className="h-8 w-8 shrink-0">
            <X className="h-3 w-3" />
          </Button>
        )}
      </div>
      {showDescription && (
        <p className="text-[10px] text-muted-foreground leading-tight">{config.description}</p>
      )}
    </div>
  )
}

interface DefaultModelSelectorsProps {
  models: Model[]
  defaults: ModelDefaults
}

export function DefaultModelSelectors({
  models,
  defaults,
}: DefaultModelSelectorsProps) {
  const { t } = useTranslation()
  const updateDefaults = useUpdateModelDefaults()
  const autoAssign = useAutoAssignDefaults()
  const { setValue, watch } = useForm<ModelDefaults>({ defaultValues: defaults })
  const generatedId = useId()

  const [showEmbeddingDialog, setShowEmbeddingDialog] = useState(false)
  const [pendingEmbeddingChange, setPendingEmbeddingChange] = useState<{
    key: keyof ModelDefaults; value: string; oldModelId?: string; newModelId?: string
  } | null>(null)

  useEffect(() => {
    if (defaults) {
      Object.entries(defaults).forEach(([key, value]) => {
        setValue(key as keyof ModelDefaults, value)
      })
    }
  }, [defaults, setValue])

  const primaryConfigs: DefaultConfig[] = [
    { key: 'default_chat_model', label: t('models.chatModelLabel'), description: t('models.chatModelDesc'), modelType: 'language', required: true, id: `${generatedId}-chat` },
    { key: 'default_embedding_model', label: t('models.embeddingModelLabel'), description: t('models.embeddingModelDesc'), modelType: 'embedding', required: true, id: `${generatedId}-embed` },
    { key: 'default_text_to_speech_model', label: t('models.ttsModelLabel'), description: t('models.ttsModelDesc'), modelType: 'text_to_speech', id: `${generatedId}-tts` },
    { key: 'default_speech_to_text_model', label: t('models.sttModelLabel'), description: t('models.sttModelDesc'), modelType: 'speech_to_text', id: `${generatedId}-stt` },
  ]

  const advancedConfigs: DefaultConfig[] = [
    { key: 'default_transformation_model', label: t('models.transformationModelLabel'), description: t('models.transformationModelDesc'), modelType: 'language', fallsBackToChat: true, id: `${generatedId}-transform` },
    { key: 'default_tools_model', label: t('models.toolsModelLabel'), description: t('models.toolsModelDesc'), modelType: 'language', fallsBackToChat: true, id: `${generatedId}-tools` },
    { key: 'large_context_model', label: t('models.largeContextModelLabel'), description: t('models.largeContextModelDesc'), modelType: 'language', id: `${generatedId}-large` },
  ]

  const defaultConfigs = [...primaryConfigs, ...advancedConfigs]

  const handleChange = (key: keyof ModelDefaults, value: string) => {
    if (key === 'default_embedding_model') {
      const current = defaults[key]
      if (current && current !== value) {
        setPendingEmbeddingChange({ key, value, oldModelId: current, newModelId: value })
        setShowEmbeddingDialog(true)
        return
      }
    }
    updateDefaults.mutate({ [key]: value || null })
  }

  const handleConfirmEmbeddingChange = () => {
    if (pendingEmbeddingChange) {
      updateDefaults.mutate({ [pendingEmbeddingChange.key]: pendingEmbeddingChange.value || null })
      setPendingEmbeddingChange(null)
    }
  }

  const getModelsForType = (type: ModelType) => models.filter(m => m.type === type)

  const missingRequired = defaultConfigs
    .filter(c => {
      if (!c.required) return false
      const value = defaults[c.key]
      if (!value) return true
      return !models.filter(m => m.type === c.modelType).some(m => m.id === value)
    })
    .map(c => c.label)

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('models.defaultAssignments')}</CardTitle>
        <CardDescription>{t('models.defaultAssignmentsDesc')}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {missingRequired.length > 0 && (
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="flex items-center justify-between gap-4">
              <span>{t('models.missingRequiredModels', { models: missingRequired.join(', ') })}</span>
              <Button
                variant="outline" size="sm"
                onClick={() => autoAssign.mutate()}
                disabled={autoAssign.isPending}
                className="shrink-0 gap-1.5"
              >
                {autoAssign.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Wand2 className="h-3.5 w-3.5" />}
                {autoAssign.isPending ? t('models.autoAssigning') : t('models.autoAssign')}
              </Button>
            </AlertDescription>
          </Alert>
        )}

        {/* Primary models: Chat, Embedding, TTS, STT */}
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {primaryConfigs.map(config => (
            <DefaultModelSelect
              key={config.key}
              config={config}
              available={getModelsForType(config.modelType)}
              currentValue={watch(config.key) || undefined}
              onChange={handleChange}
            />
          ))}
        </div>

        {/* Advanced models: Transformation, Tools, Large Context */}
        <div className="border-t pt-3">
          <p className="text-xs text-muted-foreground mb-3">{t('navigation.advanced')}</p>
            <div className="grid gap-3 sm:grid-cols-3">
              {advancedConfigs.map(config => (
                <DefaultModelSelect
                  key={config.key}
                  config={config}
                  available={getModelsForType(config.modelType)}
                  currentValue={watch(config.key) || undefined}
                  onChange={handleChange}
                  showDescription
                />
              ))}
            </div>
        </div>
      </CardContent>

      <EmbeddingModelChangeDialog
        open={showEmbeddingDialog}
        onOpenChange={(open) => { if (!open) { setPendingEmbeddingChange(null); setShowEmbeddingDialog(false) } }}
        onConfirm={handleConfirmEmbeddingChange}
        oldModelName={pendingEmbeddingChange?.oldModelId ? models.find(m => m.id === pendingEmbeddingChange.oldModelId)?.name : undefined}
        newModelName={pendingEmbeddingChange?.newModelId ? models.find(m => m.id === pendingEmbeddingChange.newModelId)?.name : undefined}
      />
    </Card>
  )
}
