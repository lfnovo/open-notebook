'use client'

import { useEffect, useRef } from 'react'
import { AppShell } from '@/components/layout/AppShell'
import { ProviderStatus } from './components/ProviderStatus'
import { ModelTypeSection } from './components/ModelTypeSection'
import { DefaultModelsSection } from './components/DefaultModelsSection'
import { useModels, useModelDefaults, useProviders, useSyncOllamaModels } from '@/lib/hooks/use-models'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { RefreshCw, Download } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function ModelsPage() {
  const { data: models, isLoading: modelsLoading, refetch: refetchModels } = useModels()
  const { data: defaults, isLoading: defaultsLoading, refetch: refetchDefaults } = useModelDefaults()
  const { data: providers, isLoading: providersLoading, refetch: refetchProviders } = useProviders()
  const syncOllama = useSyncOllamaModels()
  const hasSynced = useRef(false)

  // Auto-sync Ollama models once when both providers and models are loaded
  // This ensures authentication is working before attempting sync
  useEffect(() => {
    if (providers?.available.includes('ollama') && models !== undefined && !hasSynced.current) {
      hasSynced.current = true
      syncOllama.mutate()
    }
  }, [providers, models, syncOllama])

  const handleRefresh = () => {
    refetchModels()
    refetchDefaults()
    refetchProviders()
  }

  const handleSyncOllama = () => {
    syncOllama.mutate()
  }

  if (modelsLoading || defaultsLoading || providersLoading) {
    return (
      <AppShell>
        <div className="flex items-center justify-center min-h-[60vh]">
          <LoadingSpinner size="lg" />
        </div>
      </AppShell>
    )
  }

  if (!models || !defaults || !providers) {
    return (
      <AppShell>
        <div className="p-6">
          <div className="text-center py-12">
            <p className="text-muted-foreground">Failed to load models data</p>
          </div>
        </div>
      </AppShell>
    )
  }

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto">
        <div className="p-6 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">Model Management</h1>
              <p className="text-muted-foreground mt-1">
                Configure AI models for different purposes across Open Notebook
              </p>
            </div>
            <div className="flex gap-2">
              {providers.available.includes('ollama') && (
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={handleSyncOllama}
                  disabled={syncOllama.isPending}
                >
                  <Download className="h-4 w-4 mr-2" />
                  {syncOllama.isPending ? 'Syncing...' : 'Sync Ollama'}
                </Button>
              )}
              <Button variant="outline" size="sm" onClick={handleRefresh}>
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
        </div>

        <div className="grid gap-6">
          {/* Provider Status */}
          <ProviderStatus providers={providers} />

          {/* Default Models */}
          <DefaultModelsSection models={models} defaults={defaults} />

          {/* Model Types */}
          <div className="grid gap-6 lg:grid-cols-2">
            <ModelTypeSection 
              type="language" 
              models={models} 
              providers={providers}
              isLoading={modelsLoading}
            />
            <ModelTypeSection 
              type="embedding" 
              models={models} 
              providers={providers}
              isLoading={modelsLoading}
            />
            <ModelTypeSection 
              type="text_to_speech" 
              models={models} 
              providers={providers}
              isLoading={modelsLoading}
            />
            <ModelTypeSection 
              type="speech_to_text" 
              models={models} 
              providers={providers}
              isLoading={modelsLoading}
            />
          </div>
        </div>
        </div>
      </div>
    </AppShell>
  )
}
