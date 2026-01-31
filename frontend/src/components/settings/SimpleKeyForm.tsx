'use client'

import { useState } from 'react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Eye, EyeOff, Loader2, Trash2, Plug, RefreshCw, Check, X, ExternalLink, Copy, CheckCheck } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useSetApiKey, useDeleteApiKey, useTestConnection, useSyncModels, useProviderModelCount } from '@/lib/hooks/use-api-keys'
import { Badge } from '@/components/ui/badge'

interface SimpleKeyFormProps {
  provider: string
  isConfigured: boolean
  source?: string
  placeholder?: string
  /** Default API base URL for this provider (shown as reference) */
  defaultUrl?: string
  /** URL to documentation for getting API keys */
  docsUrl?: string
}

/**
 * Form for providers that need an API key.
 * Shows the default API URL for reference and a link to get API keys.
 */
export function SimpleKeyForm({ provider, isConfigured, source, placeholder, defaultUrl, docsUrl }: SimpleKeyFormProps) {
  const { t } = useTranslation()
  const [apiKey, setApiKey] = useState('')
  const [showKey, setShowKey] = useState(false)
  const [copied, setCopied] = useState(false)
  const setKey = useSetApiKey()
  const deleteKey = useDeleteApiKey()
  const { testConnection, isPending: isTestPending, testResults } = useTestConnection()
  const syncModels = useSyncModels()
  const { data: modelCount } = useProviderModelCount(provider)

  const handleCopyUrl = () => {
    if (defaultUrl) {
      navigator.clipboard.writeText(defaultUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const handleSave = () => {
    if (!apiKey.trim()) return
    setKey.mutate(
      { provider, data: { api_key: apiKey.trim() } },
      {
        onSuccess: () => {
          setApiKey('')
          setShowKey(false)
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
      {/* Default API URL (for reference) */}
      {defaultUrl && (
        <div className="space-y-1.5">
          <Label className="text-xs text-muted-foreground">{t.apiKeys.apiEndpoint}</Label>
          <div className="flex gap-2">
            <Input
              value={defaultUrl}
              readOnly
              className="text-xs font-mono bg-muted/50 text-muted-foreground"
            />
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCopyUrl}
              className="shrink-0"
              title={t.common.copy}
            >
              {copied ? <CheckCheck className="h-4 w-4 text-emerald-500" /> : <Copy className="h-4 w-4" />}
            </Button>
          </div>
        </div>
      )}

      {/* API Key Input */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label htmlFor={`${provider}-key`}>{t.models.apiKey}</Label>
          {docsUrl && (
            <a
              href={docsUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-primary hover:underline flex items-center gap-1"
            >
              {t.apiKeys.getApiKey}
              <ExternalLink className="h-3 w-3" />
            </a>
          )}
        </div>
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Input
              id={`${provider}-key`}
              type={showKey ? 'text' : 'password'}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={isConfigured ? '••••••••••••' : (placeholder || t.apiKeys.enterApiKey)}
              disabled={isPending}
              className="pr-10"
              autoComplete="off"
            />
            <button
              type="button"
              onClick={() => setShowKey(!showKey)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              tabIndex={-1}
              aria-label={showKey ? 'Hide API key' : 'Show API key'}
            >
              {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          <Button
            onClick={handleSave}
            disabled={!apiKey.trim() || isPending}
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
