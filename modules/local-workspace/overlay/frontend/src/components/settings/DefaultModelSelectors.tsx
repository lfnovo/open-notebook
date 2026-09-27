'use client'

import { useId, useState } from 'react'
import {
  AlertCircle, Check, CheckCircle2, ChevronDown, Database, FileStack,
  Loader2, MessageSquare, Mic, SlidersHorizontal, Sparkles, Volume2, Wand2, Wrench, X,
  type LucideIcon,
} from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useUpdateModelDefaults, useAutoAssignDefaults } from '@/lib/hooks/use-models'
import { Model, ModelDefaults } from '@/lib/types/models'
import { ModelType } from '@/lib/providers'
import { cn } from '@/lib/utils'
import { EmbeddingModelChangeDialog } from './EmbeddingModelChangeDialog'

interface DefaultConfig {
  key: keyof ModelDefaults
  label: string
  description: string
  modelType: ModelType
  required?: boolean
  fallsBackToChat?: boolean
  icon: LucideIcon
  id: string
}

const NONE_VALUE = '__none__'

function DefaultModelSelect({ config, models, value, chatModelName, disabled, onChange, compact = false }: {
  config: DefaultConfig
  models: Model[]
  value?: string | null
  chatModelName?: string
  disabled: boolean
  onChange: (key: keyof ModelDefaults, value: string) => void
  compact?: boolean
}) {
  const { t } = useTranslation()
  const available = models.filter(model => model.type === config.modelType)
    .sort((a, b) => a.name.localeCompare(b.name))
  const selected = available.find(model => model.id === value)
  const invalid = Boolean(value && !selected)
  const missing = Boolean(config.required && !selected)
  const Icon = config.icon
  const emptyHint = !value && !config.required
    ? config.fallsBackToChat
      ? chatModelName ? t('models.usingChatModelHint', { model: chatModelName }) : t('models.noneFallbackToChat')
      : t(config.modelType === 'text_to_speech' ? 'models.ttsUnsetHint' : 'models.sttUnsetHint')
    : null

  return (
    <div className={cn(
      'min-w-0 rounded-xl border bg-background/60 p-4 transition-colors sm:p-5',
      'focus-within:border-primary/50 focus-within:bg-primary/[0.025]',
      compact && 'grid gap-4 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] sm:items-center',
      (invalid || missing) && 'border-amber-500/40'
    )}>
      <div className={cn('flex min-w-0 items-start gap-3', !compact && 'mb-4')}>
        <span className={cn('flex size-10 shrink-0 items-center justify-center rounded-xl border',
          config.required ? 'border-primary/15 bg-primary/10 text-primary' : 'border-border/70 bg-muted/60 text-muted-foreground')}>
          <Icon className="size-[18px]" aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <Label htmlFor={config.id} className="text-sm font-semibold leading-5">
              {config.label}{config.required && <span className="ms-1 text-primary" aria-hidden="true">*</span>}
            </Label>
            {!config.required && <span className="text-xs text-muted-foreground">{t('common.optional')}</span>}
          </div>
          <p id={`${config.id}-description`} className="text-xs leading-relaxed text-muted-foreground">{config.description}</p>
        </div>
      </div>
      <div className="min-w-0 space-y-2">
        <div className="flex min-w-0 items-center gap-2">
          <Select value={value || (config.required ? '' : NONE_VALUE)}
            disabled={disabled || available.length === 0}
            onValueChange={next => onChange(config.key, next === NONE_VALUE ? '' : next)}>
            <SelectTrigger id={config.id} aria-required={config.required}
              aria-invalid={invalid || missing}
              aria-describedby={`${config.id}-description ${config.id}-hint`}
              className="min-h-14 w-full min-w-0 flex-1 rounded-lg border-border bg-background px-3.5 py-2 text-start shadow-none hover:border-primary/50 data-[size=default]:h-auto dark:bg-background/50">
              <SelectValue className="min-w-0 flex-1" aria-label={selected?.name}>
                <span className="block min-w-0 flex-1 overflow-hidden text-start">
                  <span className="block truncate text-sm font-medium" title={selected?.name || undefined}>
                    {selected?.name || (invalid ? t('apiKeys.notConfigured') : available.length === 0
                      ? t('models.noModels') : !config.required ? t(config.fallsBackToChat ? 'models.noneFallbackToChat' : 'models.noneOption') : t('models.requiredModelPlaceholder'))}
                  </span>
                  {selected && <span className="mt-0.5 block truncate text-xs font-normal text-muted-foreground">{selected.provider}</span>}
                </span>
              </SelectValue>
            </SelectTrigger>
            <SelectContent className="max-w-[calc(100vw-2rem)] rounded-xl p-1 shadow-xl">
              {!config.required && <SelectItem value={NONE_VALUE} className="min-h-11 rounded-lg">
                {t(config.fallsBackToChat ? 'models.noneFallbackToChat' : 'models.noneOption')}
              </SelectItem>}
              {available.map(model => <SelectItem key={model.id} value={model.id} textValue={model.name} className="min-h-14 rounded-lg py-2">
                <span className="block min-w-0 py-0.5">
                  <span className="block break-all text-sm font-medium">{model.name}</span>
                  <span className="block text-xs text-muted-foreground">{model.provider}</span>
                </span>
              </SelectItem>)}
            </SelectContent>
          </Select>
          {!config.required && value && <Button type="button" variant="ghost" size="icon" disabled={disabled}
            onClick={() => onChange(config.key, '')}
            aria-label={t('models.assignmentClear', { model: config.label })}
            title={t('models.assignmentClear', { model: config.label })}
            className="size-11 shrink-0 rounded-lg border border-border/60 bg-muted/20 text-muted-foreground hover:bg-destructive/10 hover:text-destructive">
            <X className="size-4" aria-hidden="true" />
          </Button>}
        </div>
        <p id={`${config.id}-hint`} className={cn('text-xs leading-relaxed', invalid ? 'text-amber-700 dark:text-amber-300' : 'text-muted-foreground')}>
          {invalid ? t('models.assignmentUnavailable') : emptyHint}
        </p>
      </div>
    </div>
  )
}

export function DefaultModelSelectors({ models, defaults }: { models: Model[]; defaults: ModelDefaults }) {
  const { t } = useTranslation()
  const id = useId()
  const update = useUpdateModelDefaults()
  const autoAssign = useAutoAssignDefaults()
  const [advancedOpen, setAdvancedOpen] = useState(false)
  const [embeddingChange, setEmbeddingChange] = useState<{ oldId: string; newId: string } | null>(null)
  const busy = update.isPending || autoAssign.isPending
  const primary: DefaultConfig[] = [
    { key: 'default_chat_model', label: t('models.chatModelLabel'), description: t('models.chatModelDesc'), modelType: 'language', required: true, icon: MessageSquare, id: `${id}-chat` },
    { key: 'default_embedding_model', label: t('models.embeddingModelLabel'), description: t('models.embeddingModelDesc'), modelType: 'embedding', required: true, icon: Database, id: `${id}-embedding` },
    { key: 'default_text_to_speech_model', label: t('models.ttsModelLabel'), description: t('models.ttsModelDesc'), modelType: 'text_to_speech', icon: Volume2, id: `${id}-tts` },
    { key: 'default_speech_to_text_model', label: t('models.sttModelLabel'), description: t('models.sttModelDesc'), modelType: 'speech_to_text', icon: Mic, id: `${id}-stt` },
  ]
  const advanced: DefaultConfig[] = [
    { key: 'default_transformation_model', label: t('models.transformationModelLabel'), description: t('models.transformationModelDesc'), modelType: 'language', fallsBackToChat: true, icon: Sparkles, id: `${id}-transform` },
    { key: 'default_tools_model', label: t('models.toolsModelLabel'), description: t('models.toolsModelDesc'), modelType: 'language', fallsBackToChat: true, icon: Wrench, id: `${id}-tools` },
    { key: 'large_context_model', label: t('models.largeContextModelLabel'), description: t('models.largeContextModelDesc'), modelType: 'language', fallsBackToChat: true, icon: FileStack, id: `${id}-large` },
  ]
  const all = [...primary, ...advanced]
  const isConfigured = (config: DefaultConfig) => models.some(model => model.id === defaults[config.key] && model.type === config.modelType)
  const configured = all.filter(isConfigured).length
  const missing = primary.filter(config => config.required && !isConfigured(config))
  const chatModelName = models.find(model => model.id === defaults.default_chat_model && model.type === 'language')?.name
  const handleChange = (key: keyof ModelDefaults, value: string) => {
    if (busy || (defaults[key] || '') === value) return
    if (key === 'default_embedding_model' && defaults[key]) {
      setEmbeddingChange({ oldId: defaults[key], newId: value })
      return
    }
    autoAssign.reset()
    update.mutate({ [key]: value || null })
  }
  const renderSelect = (config: DefaultConfig, compact = false) => <DefaultModelSelect key={config.key}
    config={config} models={models} value={defaults[config.key]} chatModelName={chatModelName}
    disabled={busy} onChange={handleChange} compact={compact} />

  return (
    <Card className="gap-0 overflow-hidden rounded-2xl border-border/80 py-0 shadow-sm" aria-labelledby={`${id}-title`}>
      <CardHeader className="flex flex-col gap-4 border-b border-border/60 bg-gradient-to-br from-primary/[0.055] via-transparent to-transparent p-5 sm:p-6">
        <div className="flex w-full flex-wrap items-start justify-between gap-4">
          <div className="flex min-w-0 items-start gap-3.5">
            <span className="flex size-11 shrink-0 items-center justify-center rounded-xl border border-primary/20 bg-primary/10 text-primary">
              <SlidersHorizontal className="size-5" aria-hidden="true" />
            </span>
            <div className="min-w-0 space-y-1.5">
              <CardTitle id={`${id}-title`} className="text-lg font-semibold tracking-tight">{t('models.defaultAssignments')}</CardTitle>
              <CardDescription className="max-w-xl text-sm leading-relaxed">{t('models.defaultAssignmentsDesc')}</CardDescription>
            </div>
          </div>
          <span className="inline-flex shrink-0 items-center gap-2 rounded-full border bg-background/70 px-3 py-1.5 text-xs font-medium">
            {missing.length ? <AlertCircle className="size-3.5 text-amber-600 dark:text-amber-400" aria-hidden="true" /> : <CheckCircle2 className="size-3.5 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />}
            <span className="tabular-nums">{configured} / {all.length}</span>
            <span className="text-muted-foreground">{t('apiKeys.configured')}</span>
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-5 p-5 sm:p-6">
        {missing.length > 0 && <Alert className="border-amber-500/30 bg-amber-500/5">
          <AlertCircle className="size-4" />
          <AlertDescription className="flex flex-wrap items-center justify-between gap-3">
            <span>{t('models.missingRequiredModels', { models: missing.map(config => config.label).join(', ') })}</span>
            <Button type="button" variant="outline" disabled={busy} onClick={() => { update.reset(); autoAssign.mutate() }} className="min-h-11 shrink-0 gap-2">
              {autoAssign.isPending ? <Loader2 className="size-4 animate-spin motion-reduce:animate-none" aria-hidden="true" /> : <Wand2 className="size-4" aria-hidden="true" />}
              {t(autoAssign.isPending ? 'models.autoAssigning' : 'models.autoAssign')}
            </Button>
          </AlertDescription>
        </Alert>}
        <div className="grid min-w-0 gap-3 sm:grid-cols-2 sm:gap-4">{primary.map(config => renderSelect(config))}</div>
        <div className="rounded-xl border border-border/80">
          <button type="button" aria-expanded={advancedOpen} aria-controls={`${id}-advanced`} onClick={() => setAdvancedOpen(open => !open)}
            className="flex min-h-16 w-full items-center justify-between gap-4 rounded-xl p-4 text-start transition-colors hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background">
            <span className="flex min-w-0 items-center gap-3">
              <Wrench className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
              <span className="min-w-0"><span className="block text-sm font-semibold">{t('navigation.advanced')}</span>
                <span className="mt-1 block text-xs leading-relaxed text-muted-foreground">{advanced.map(config => config.label).join(' · ')}</span>
              </span>
            </span>
            <ChevronDown className={cn('size-4 shrink-0 text-muted-foreground transition-transform motion-reduce:transition-none', advancedOpen && 'rotate-180')} aria-hidden="true" />
          </button>
          <div id={`${id}-advanced`} hidden={!advancedOpen} className="space-y-3 border-t border-border/60 p-3 sm:p-4">
            {advanced.map(config => renderSelect(config, true))}
          </div>
        </div>
      </CardContent>
      <div role="status" aria-live="polite" aria-atomic="true" className="flex min-h-12 items-center gap-2 border-t border-border/60 bg-muted/20 px-5 py-3 text-xs text-muted-foreground sm:px-6">
        {busy ? <Loader2 className="size-3.5 animate-spin motion-reduce:animate-none" aria-hidden="true" /> : update.isError || autoAssign.isError ? <AlertCircle className="size-3.5 text-destructive" aria-hidden="true" /> : <Check className="size-3.5" aria-hidden="true" />}
        {busy ? t('common.saving') : update.isError || autoAssign.isError ? t('models.assignmentSaveFailed') : update.isSuccess || autoAssign.isSuccess ? t('models.configSaveSuccess') : t('models.assignmentAutoSave')}
      </div>
      <EmbeddingModelChangeDialog open={Boolean(embeddingChange)} onOpenChange={open => { if (!open) setEmbeddingChange(null) }}
        onConfirm={() => {
          if (embeddingChange && !busy) { autoAssign.reset(); update.mutate({ default_embedding_model: embeddingChange.newId }) }
          setEmbeddingChange(null)
        }}
        oldModelName={models.find(model => model.id === embeddingChange?.oldId)?.name}
        newModelName={models.find(model => model.id === embeddingChange?.newId)?.name} />
    </Card>
  )
}
