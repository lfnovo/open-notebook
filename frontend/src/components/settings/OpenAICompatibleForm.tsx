'use client'

import { useState } from 'react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Eye, EyeOff, Loader2, Trash2, Plug, RefreshCw, Check, X } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useSetApiKey, useDeleteApiKey, useTestConnection, useSyncModels, useProviderModelCount } from '@/lib/hooks/use-api-keys'

interface OpenAICompatibleFormProps {
  isConfigured: boolean
  source?: string
}

type ServiceType = 'llm' | 'embedding' | 'stt' | 'tts'

/**
 * Form for OpenAI-compatible providers with per-service configuration
 */
export function OpenAICompatibleForm({ isConfigured, source }: OpenAICompatibleFormProps) {
  const { t } = useTranslation()
  const [apiKey, setApiKey] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [serviceType, setServiceType] = useState<ServiceType>('llm')
  const [showKey, setShowKey] = useState(false)
  const setKey = useSetApiKey()
  const deleteKey = useDeleteApiKey()
  const { testConnection, isPending: isTestPending, testResults } = useTestConnection()
  const syncModels = useSyncModels()
  const { data: modelCount } = useProviderModelCount('openai_compatible')

  const handleSave = () => {
    if (!apiKey.trim() || !baseUrl.trim()) return
    setKey.mutate(
      {
        provider: 'openai_compatible',
        data: {
          api_key: apiKey.trim(),
          base_url: baseUrl.trim(),
          service_type: serviceType,
        },
      },
      {
        onSuccess: () => {
          setApiKey('')
          setBaseUrl('')
          setShowKey(false)
        },
      }
    )
  }

  const handleDelete = () => {
    deleteKey.mutate({ provider: 'openai_compatible', serviceType })
  }

  const handleTestConnection = () => {
    testConnection('openai_compatible')
  }

  const handleSyncModels = () => {
    syncModels.mutate('openai_compatible')
  }

  const isFromEnv = source === 'environment'
  const isPending = setKey.isPending || deleteKey.isPending
  const testResult = testResults['openai_compatible']
  const totalModels = modelCount?.total || 0

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        {t.apiKeys.openaiCompatibleHint}
      </p>

      <div className="space-y-2">
        <Label htmlFor="compat-service">{t.apiKeys.serviceType}</Label>
        <Select value={serviceType} onValueChange={(v) => setServiceType(v as ServiceType)}>
          <SelectTrigger id="compat-service">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="llm">{t.apiKeys.serviceLlm}</SelectItem>
            <SelectItem value="embedding">{t.apiKeys.serviceEmbedding}</SelectItem>
            <SelectItem value="stt">{t.apiKeys.serviceStt}</SelectItem>
            <SelectItem value="tts">{t.apiKeys.serviceTts}</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label htmlFor="compat-url">{t.models.baseUrl}</Label>
        <Input
          id="compat-url"
          type="url"
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
          placeholder={t.apiKeys.baseUrlPlaceholder}
          disabled={isPending}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="compat-key">{t.models.apiKey}</Label>
        <div className="relative">
          <Input
            id="compat-key"
            type={showKey ? 'text' : 'password'}
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={isConfigured ? '••••••••••••' : t.apiKeys.enterApiKey}
            disabled={isPending}
            className="pr-10"
            autoComplete="off"
          />
          <button
            type="button"
            onClick={() => setShowKey(!showKey)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            tabIndex={-1}
          >
            {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
      </div>

      <div className="flex gap-2">
        <Button
          onClick={handleSave}
          disabled={!apiKey.trim() || !baseUrl.trim() || isPending}
          className="flex-1"
        >
          {setKey.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              {t.common.saving}
            </>
          ) : (
            t.common.save
          )}
        </Button>
        {isConfigured && !isFromEnv && (
          <Button
            variant="outline"
            onClick={handleDelete}
            disabled={isPending}
            className="text-destructive hover:bg-destructive hover:text-destructive-foreground"
          >
            {deleteKey.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Trash2 className="h-4 w-4" />
            )}
          </Button>
        )}
      </div>

      {isFromEnv && (
        <p className="text-xs text-muted-foreground">
          {t.apiKeys.fromEnvironmentHint}
        </p>
      )}

      {/* Actions when configured */}
      {isConfigured && (
        <div className="flex items-center gap-2 pt-2 border-t">
          <Button
            variant="outline"
            size="sm"
            onClick={handleTestConnection}
            disabled={isTestPending}
            className="gap-1.5"
          >
            {isTestPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : testResult?.success ? (
              <Check className="h-3.5 w-3.5 text-emerald-500" />
            ) : testResult?.success === false ? (
              <X className="h-3.5 w-3.5 text-destructive" />
            ) : (
              <Plug className="h-3.5 w-3.5" />
            )}
            {isTestPending ? t.apiKeys.testing : t.apiKeys.testConnection}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleSyncModels}
            disabled={syncModels.isPending}
            className="gap-1.5"
          >
            {syncModels.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <RefreshCw className="h-3.5 w-3.5" />
            )}
            {syncModels.isPending ? t.apiKeys.syncing : t.apiKeys.syncModels}
          </Button>
          {totalModels > 0 && (
            <Badge variant="secondary" className="ml-auto">
              {t.apiKeys.modelsConfigured.replace('{count}', totalModels.toString())}
            </Badge>
          )}
        </div>
      )}
    </div>
  )
}
