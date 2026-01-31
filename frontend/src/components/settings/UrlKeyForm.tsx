'use client'

import { useState } from 'react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Loader2, Trash2, Plug, RefreshCw, Check, X } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useSetApiKey, useDeleteApiKey, useTestConnection, useSyncModels, useProviderModelCount } from '@/lib/hooks/use-api-keys'
import { Badge } from '@/components/ui/badge'

interface UrlKeyFormProps {
  provider: string
  isConfigured: boolean
  source?: string
  defaultUrl?: string
}

/**
 * Form for providers that need a base URL (Ollama, etc.)
 */
export function UrlKeyForm({ provider, isConfigured, source, defaultUrl }: UrlKeyFormProps) {
  const { t } = useTranslation()
  const [baseUrl, setBaseUrl] = useState('')
  const setKey = useSetApiKey()
  const deleteKey = useDeleteApiKey()
  const { testConnection, isPending: isTestPending, testResults } = useTestConnection()
  const syncModels = useSyncModels()
  const { data: modelCount } = useProviderModelCount(provider)

  const handleSave = () => {
    if (!baseUrl.trim()) return
    setKey.mutate(
      { provider, data: { base_url: baseUrl.trim() } },
      {
        onSuccess: () => {
          setBaseUrl('')
        },
      }
    )
  }

  const handleDelete = () => {
    deleteKey.mutate({ provider })
  }

  const handleTestConnection = () => {
    testConnection(provider)
  }

  const handleSyncModels = () => {
    syncModels.mutate(provider)
  }

  const isFromEnv = source === 'environment'
  const isPending = setKey.isPending || deleteKey.isPending
  const testResult = testResults[provider]
  const totalModels = modelCount?.total || 0

  return (
    <div className="space-y-3">
      <div className="space-y-2">
        <Label htmlFor={`${provider}-url`}>{t.models.baseUrl}</Label>
        <div className="flex gap-2">
          <Input
            id={`${provider}-url`}
            type="url"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder={isConfigured ? '••••••••' : (defaultUrl || t.apiKeys.enterBaseUrl)}
            disabled={isPending}
            className="flex-1"
          />
          <Button
            onClick={handleSave}
            disabled={!baseUrl.trim() || isPending}
          >
            {setKey.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
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
      </div>

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
