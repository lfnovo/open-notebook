'use client'

import { useState } from 'react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Eye, EyeOff, Loader2, Trash2, ChevronDown, Plug, RefreshCw, Check, X } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useSetApiKey, useDeleteApiKey, useTestConnection, useSyncModels, useProviderModelCount } from '@/lib/hooks/use-api-keys'

interface AzureKeyFormProps {
  isConfigured: boolean
  source?: string
}

type ServiceType = 'llm' | 'embedding' | 'stt' | 'tts'

/**
 * Form for Azure OpenAI with per-service endpoint configuration
 */
export function AzureKeyForm({ isConfigured, source }: AzureKeyFormProps) {
  const { t } = useTranslation()
  const [apiKey, setApiKey] = useState('')
  const [endpoint, setEndpoint] = useState('')
  const [apiVersion, setApiVersion] = useState('')
  const [showKey, setShowKey] = useState(false)
  const [showEndpoints, setShowEndpoints] = useState(false)
  const [endpoints, setEndpoints] = useState<Record<ServiceType, string>>({
    llm: '',
    embedding: '',
    stt: '',
    tts: '',
  })
  const setKey = useSetApiKey()
  const deleteKey = useDeleteApiKey()
  const { testConnection, isPending: isTestPending, testResults } = useTestConnection()
  const syncModels = useSyncModels()
  const { data: modelCount } = useProviderModelCount('azure')

  const handleSave = () => {
    // Validate required fields
    if (!apiKey.trim() || !endpoint.trim() || !apiVersion.trim()) {
      return
    }

    // Collect all Azure configuration in a single object
    const azureConfig = {
      api_key: apiKey.trim(),
      endpoint: endpoint.trim(),
      api_version: apiVersion.trim(),
      endpoint_llm: endpoints.llm.trim() || undefined,
      endpoint_embedding: endpoints.embedding.trim() || undefined,
      endpoint_stt: endpoints.stt.trim() || undefined,
      endpoint_tts: endpoints.tts.trim() || undefined,
    }

    // Make a single POST call with all data
    setKey.mutate(
      { provider: 'azure', data: azureConfig },
      {
        onSuccess: () => {
          setApiKey('')
          setEndpoint('')
          setApiVersion('')
          setShowKey(false)
          setEndpoints({ llm: '', embedding: '', stt: '', tts: '' })
        },
      }
    )
  }

  const handleDelete = () => {
    deleteKey.mutate({ provider: 'azure' })
  }

  const handleTestConnection = () => {
    testConnection('azure')
  }

  const handleSyncModels = () => {
    syncModels.mutate('azure')
  }

  const isFromEnv = source === 'environment'
  const isPending = setKey.isPending || deleteKey.isPending
  const testResult = testResults['azure']
  const totalModels = modelCount?.total || 0

  const serviceLabels: Record<ServiceType, string> = {
    llm: t.apiKeys.serviceLlm,
    embedding: t.apiKeys.serviceEmbedding,
    stt: t.apiKeys.serviceStt,
    tts: t.apiKeys.serviceTts,
  }

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="azure-key">{t.models.apiKey}</Label>
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Input
              id="azure-key"
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
      </div>

      <div className="space-y-2">
        <Label htmlFor="azure-endpoint">{t.apiKeys.endpoint || 'Endpoint'}</Label>
        <Input
          id="azure-endpoint"
          type="url"
          value={endpoint}
          onChange={(e) => setEndpoint(e.target.value)}
          placeholder="https://your-resource.openai.azure.com/"
          disabled={isPending}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="azure-api-version">{t.apiKeys.apiVersion || 'API Version'}</Label>
        <Input
          id="azure-api-version"
          type="text"
          value={apiVersion}
          onChange={(e) => setApiVersion(e.target.value)}
          placeholder="2024-02-15-preview"
          disabled={isPending}
        />
      </div>

      <Collapsible open={showEndpoints} onOpenChange={setShowEndpoints}>
        <CollapsibleTrigger className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
          <ChevronDown className={`h-4 w-4 transition-transform ${showEndpoints ? 'rotate-180' : ''}`} />
          {t.apiKeys.serviceEndpoints}
        </CollapsibleTrigger>
        <CollapsibleContent className="mt-3 space-y-3">
          <p className="text-xs text-muted-foreground">{t.apiKeys.azureEndpointsHint}</p>
          {(Object.keys(endpoints) as ServiceType[]).map((serviceType) => (
            <div key={serviceType} className="space-y-1">
              <Label htmlFor={`azure-${serviceType}`} className="text-sm">
                {serviceLabels[serviceType]}
              </Label>
              <Input
                id={`azure-${serviceType}`}
                type="url"
                value={endpoints[serviceType]}
                onChange={(e) => setEndpoints({ ...endpoints, [serviceType]: e.target.value })}
                placeholder={t.apiKeys.endpointPlaceholder}
                disabled={isPending}
              />
            </div>
          ))}
        </CollapsibleContent>
      </Collapsible>

      <div className="flex gap-2">
        <Button
          onClick={handleSave}
          disabled={!apiKey.trim() || !endpoint.trim() || !apiVersion.trim() || isPending}
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
