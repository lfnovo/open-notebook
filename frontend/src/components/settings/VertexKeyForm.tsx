'use client'

import { useState } from 'react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Loader2, Trash2, Plug, RefreshCw, Check, X, ExternalLink } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useSetApiKey, useDeleteApiKey, useTestConnection, useSyncModels, useProviderModelCount } from '@/lib/hooks/use-api-keys'

interface VertexKeyFormProps {
  isConfigured: boolean
  source?: string
}

/**
 * Form for Google Vertex AI configuration
 * Requires project ID, location, and service account credentials path
 */
export function VertexKeyForm({ isConfigured, source }: VertexKeyFormProps) {
  const { t } = useTranslation()
  const [project, setProject] = useState('')
  const [location, setLocation] = useState('')
  const [credentialsPath, setCredentialsPath] = useState('')
  const setKey = useSetApiKey()
  const deleteKey = useDeleteApiKey()
  const { testConnection, isPending: isTestPending, testResults } = useTestConnection()
  const syncModels = useSyncModels()
  const { data: modelCount } = useProviderModelCount('vertex')

  const handleSave = () => {
    // Validate required fields
    if (!project.trim() || !location.trim() || !credentialsPath.trim()) {
      return
    }

    setKey.mutate(
      {
        provider: 'vertex',
        data: {
          vertex_project: project.trim(),
          vertex_location: location.trim(),
          vertex_credentials_path: credentialsPath.trim(),
        },
      },
      {
        onSuccess: () => {
          setProject('')
          setLocation('')
          setCredentialsPath('')
        },
      }
    )
  }

  const handleDelete = () => {
    deleteKey.mutate({ provider: 'vertex' })
  }

  const handleTestConnection = () => {
    testConnection('vertex')
  }

  const handleSyncModels = () => {
    syncModels.mutate('vertex')
  }

  const isFromEnv = source === 'environment'
  const isPending = setKey.isPending || deleteKey.isPending
  const testResult = testResults['vertex']
  const totalModels = modelCount?.total || 0

  return (
    <div className="space-y-4">
      <div className="p-3 bg-muted/50 rounded-md text-sm text-muted-foreground">
        <p>{t.apiKeys.vertexConfigNote || 'Google Vertex AI requires a GCP project and service account. Configure via environment variables for best security.'}</p>
        <a
          href="https://cloud.google.com/vertex-ai/docs/start/cloud-environment"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-primary hover:underline mt-2"
        >
          {t.apiKeys.learnMore}
          <ExternalLink className="h-3 w-3" />
        </a>
      </div>

      <div className="space-y-2">
        <Label htmlFor="vertex-project">{t.apiKeys.vertexProject || 'GCP Project ID'}</Label>
        <Input
          id="vertex-project"
          type="text"
          value={project}
          onChange={(e) => setProject(e.target.value)}
          placeholder={isConfigured ? '••••••••••••' : 'my-gcp-project'}
          disabled={isPending || isFromEnv}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="vertex-location">{t.apiKeys.vertexLocation || 'Region'}</Label>
        <Input
          id="vertex-location"
          type="text"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          placeholder={isConfigured ? '••••••••••••' : 'us-central1'}
          disabled={isPending || isFromEnv}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="vertex-credentials">{t.apiKeys.vertexCredentials || 'Service Account JSON Path'}</Label>
        <Input
          id="vertex-credentials"
          type="text"
          value={credentialsPath}
          onChange={(e) => setCredentialsPath(e.target.value)}
          placeholder={isConfigured ? '••••••••••••' : '/path/to/service-account.json'}
          disabled={isPending || isFromEnv}
        />
        <p className="text-xs text-muted-foreground">
          {t.apiKeys.vertexCredentialsHint || 'Path to your Google Cloud service account JSON file inside the container.'}
        </p>
      </div>

      {!isFromEnv && (
        <div className="flex gap-2">
          <Button
            onClick={handleSave}
            disabled={!project.trim() || !location.trim() || !credentialsPath.trim() || isPending}
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
          {isConfigured && (
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
      )}

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
