'use client'

import { useMemo, useState, useEffect } from 'react'
import { AppShell } from '@/components/layout/AppShell'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { RefreshCw, ChevronLeft, Key } from 'lucide-react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import Link from 'next/link'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useProviderConfigs, useProviderConfig, useCreateProviderConfig, useUpdateProviderConfig } from '@/lib/hooks/use-api-keys'
import {
  MigrationBanner,
  ProviderCard,
  SimpleKeyForm,
  UrlKeyForm,
  AzureKeyForm,
  OpenAICompatibleForm,
  VertexKeyForm,
  ConfigForm,
  type ModelType,
} from '@/components/settings'
import { CreateProviderConfigRequest, UpdateProviderConfigRequest, ProviderCredential } from '@/lib/api/api-keys'

// Provider configuration
const PROVIDER_CONFIG = {
  // Simple providers (just API key)
  simple: ['openai', 'anthropic', 'google', 'groq', 'mistral', 'deepseek', 'xai', 'openrouter', 'voyage', 'elevenlabs'],
  // URL-based providers
  urlBased: ['ollama'],
  // Multi-field providers
  complex: ['azure', 'vertex', 'openai_compatible'],
}

// Display names for providers
const PROVIDER_DISPLAY_NAMES: Record<string, string> = {
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  google: 'Google AI',
  groq: 'Groq',
  mistral: 'Mistral AI',
  deepseek: 'DeepSeek',
  xai: 'xAI (Grok)',
  openrouter: 'OpenRouter',
  voyage: 'Voyage AI',
  elevenlabs: 'ElevenLabs',
  ollama: 'Ollama',
  azure: 'Azure OpenAI',
  vertex: 'Google Vertex AI',
  openai_compatible: 'OpenAI Compatible',
}

// Placeholders for API key inputs
const API_KEY_PLACEHOLDERS: Record<string, string> = {
  openai: 'sk-...',
  anthropic: 'sk-ant-...',
  google: 'AIza...',
  groq: 'gsk_...',
  mistral: '',
  deepseek: '',
  xai: 'xai-...',
  openrouter: 'sk-or-...',
  voyage: 'pa-...',
  elevenlabs: '',
  openai_compatible: '',
}

// Default API base URLs for providers (prefilled for reference)
const DEFAULT_URLS: Record<string, string> = {
  openai: 'https://api.openai.com/v1',
  anthropic: 'https://api.anthropic.com',
  google: 'https://generativelanguage.googleapis.com',
  groq: 'https://api.groq.com/openai/v1',
  mistral: 'https://api.mistral.ai/v1',
  deepseek: 'https://api.deepseek.com/v1',
  xai: 'https://api.x.ai/v1',
  openrouter: 'https://openrouter.ai/api/v1',
  voyage: 'https://api.voyageai.com/v1',
  elevenlabs: 'https://api.elevenlabs.io/v1',
  ollama: 'http://localhost:11434',
  openai_compatible: 'http://your-server:port/v1',
}

// Documentation links for getting API keys
const PROVIDER_DOCS: Record<string, string> = {
  openai: 'https://platform.openai.com/api-keys',
  anthropic: 'https://console.anthropic.com/settings/keys',
  google: 'https://aistudio.google.com/app/apikey',
  groq: 'https://console.groq.com/keys',
  mistral: 'https://console.mistral.ai/api-keys/',
  deepseek: 'https://platform.deepseek.com/api_keys',
  xai: 'https://console.x.ai/',
  openrouter: 'https://openrouter.ai/keys',
  voyage: 'https://dash.voyageai.com/api-keys',
  elevenlabs: 'https://elevenlabs.io/app/settings/api-keys',
  ollama: 'https://ollama.com/download',
  azure: 'https://portal.azure.com/#view/Microsoft_Azure_ProjectOxford/CognitiveServicesHub/~/OpenAI',
  vertex: 'https://cloud.google.com/vertex-ai/docs/start/cloud-environment',
  openai_compatible: 'https://github.com/lfnovo/open-notebook/blob/main/docs/5-CONFIGURATION/openai-compatible.md',
}

// Supported model types per provider
const PROVIDER_SUPPORTED_TYPES: Record<string, ModelType[]> = {
  openai: ['language', 'embedding', 'text_to_speech', 'speech_to_text'],
  anthropic: ['language'],
  google: ['language', 'embedding'],
  groq: ['language', 'speech_to_text'],
  mistral: ['language', 'embedding'],
  deepseek: ['language'],
  xai: ['language'],
  openrouter: ['language'],
  voyage: ['embedding'],
  elevenlabs: ['text_to_speech'],
  ollama: ['language', 'embedding'],
  azure: ['language', 'embedding', 'text_to_speech', 'speech_to_text'],
  vertex: ['language', 'embedding'],
  openai_compatible: ['language', 'embedding'],
}

// Provider categories for UI
const PROVIDERS = {
  simple: PROVIDER_CONFIG.simple,
  urlBased: PROVIDER_CONFIG.urlBased,
  complex: PROVIDER_CONFIG.complex,
}

export default function ApiKeysPage() {
  const { t } = useTranslation()

  // Dialog state for adding/editing configurations
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingProvider, setEditingProvider] = useState<string | null>(null)
  const [editingConfig, setEditingConfig] = useState<ProviderCredential | null>(null)
  const [editingConfigId, setEditingConfigId] = useState<string | null>(null)

  // Fetch the config being edited when editingConfigId is set
  const { data: fetchedConfig, isLoading: isLoadingConfig } = useProviderConfig(
    editingProvider || '',
    editingConfigId || ''
  )

  // When config data arrives, set it and open dialog
  useEffect(() => {
    if (fetchedConfig && editingConfigId) {
      setEditingConfig(fetchedConfig)
      setDialogOpen(true)
    }
  }, [fetchedConfig, editingConfigId])

  // Fetch configurations for all providers
  const allConfigs = useMemo(() => {
    const configs: Record<string, ProviderCredential[]> = {}
    // We'll use useProviderConfigs in individual cards
    return configs
  }, [])

  const handleRefresh = () => {
    // Refetch all provider configs
    window.location.reload()
  }

  // Handle add config
  const handleAddConfig = (provider: string) => {
    setEditingProvider(provider)
    setEditingConfig(null)
    setDialogOpen(true)
  }

  // Handle edit config - fetch the config data first, then open dialog
  const handleEditConfig = (provider: string, configId: string) => {
    setEditingProvider(provider)
    setEditingConfigId(configId)
    setEditingConfig(null) // Clear previous config while loading
    // Dialog will open when fetchedConfig arrives (via useEffect above)
  }

  // Handle form submission
  const handleSubmitConfig = (data: CreateProviderConfigRequest | UpdateProviderConfigRequest) => {
    if (!editingProvider) return

    if (editingConfig) {
      // Update existing config
      updateConfig.mutate({
        provider: editingProvider,
        configId: editingConfig.id,
        data: data as UpdateProviderConfigRequest,
      })
    } else {
      // Create new config
      createConfig.mutate({
        provider: editingProvider,
        data: data as CreateProviderConfigRequest,
      })
    }
  }

  const createConfig = useCreateProviderConfig()
  const updateConfig = useUpdateProviderConfig()

  // Close dialog after successful operation
  const isSubmitting = createConfig.isPending || updateConfig.isPending
  if ((createConfig.isSuccess || updateConfig.isSuccess) && dialogOpen) {
    setDialogOpen(false)
    setEditingProvider(null)
    setEditingConfig(null)
    setEditingConfigId(null)
  }

  // Reset edit state when dialog closes without success
  useEffect(() => {
    if (!dialogOpen) {
      setEditingProvider(null)
      setEditingConfig(null)
      setEditingConfigId(null)
    }
  }, [dialogOpen])

  // Render a single provider card with multi-config support
  const renderProviderCard = (provider: string) => {
    const displayName = PROVIDER_DISPLAY_NAMES[provider] || provider
    const defaultUrl = DEFAULT_URLS[provider]
    const docsUrl = PROVIDER_DOCS[provider]
    const placeholder = API_KEY_PLACEHOLDERS[provider]
    const supportedTypes = PROVIDER_SUPPORTED_TYPES[provider]

    // Use the provider configs hook
    const { data: configs, isLoading } = useProviderConfigs(provider)
    const hasConfigs = configs && configs.length > 0
    const isConfigured = hasConfigs  // Only show configured when we have configs

    return (
      <ProviderCard
        key={provider}
        name={provider}
        displayName={displayName}
        isConfigured={isConfigured}
        supportedTypes={supportedTypes}
        configs={hasConfigs ? configs : undefined}
        onAddConfig={() => handleAddConfig(provider)}
        onEditConfig={(configId) => handleEditConfig(provider, configId)}
        isLoading={isLoading}
      >
        {/* Legacy form - shown when no configs exist */}
        {!hasConfigs && (
          <>
            {PROVIDERS.simple.includes(provider) && (
              <SimpleKeyForm
                provider={provider}
                isConfigured={false}
                placeholder={placeholder}
                defaultUrl={defaultUrl}
                docsUrl={docsUrl}
              />
            )}
            {PROVIDERS.urlBased.includes(provider) && (
              <UrlKeyForm
                provider={provider}
                isConfigured={false}
                defaultUrl={defaultUrl}
              />
            )}
            {provider === 'azure' && (
              <AzureKeyForm isConfigured={false} />
            )}
            {provider === 'vertex' && (
              <VertexKeyForm isConfigured={false} />
            )}
            {provider === 'openai_compatible' && (
              <OpenAICompatibleForm isConfigured={false} />
            )}
          </>
        )}
      </ProviderCard>
    )
  }

  // Loading state
  // We'll show individual loading states per card

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto">
        <div className="p-6 space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link href="/settings">
                <Button variant="ghost" size="sm">
                  <ChevronLeft className="h-4 w-4 mr-1" />
                  {t.navigation.settings}
                </Button>
              </Link>
              <div>
                <h1 className="text-2xl font-bold flex items-center gap-2">
                  <Key className="h-6 w-6" />
                  {t.apiKeys.title}
                </h1>
                <p className="text-muted-foreground mt-1">
                  {t.apiKeys.description}
                </p>
              </div>
            </div>
            <Button variant="outline" size="sm" onClick={handleRefresh}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>

          {/* Migration Banner - for legacy support */}
          {/* MigrationBanner can be kept for backward compatibility */}

          {/* Provider Cards */}
          <div className="grid gap-4">
            {/* Simple providers */}
            {PROVIDERS.simple.map((provider) => renderProviderCard(provider))}

            {/* URL-based providers */}
            {PROVIDERS.urlBased.map((provider) => renderProviderCard(provider))}

            {/* Azure OpenAI */}
            {renderProviderCard('azure')}

            {/* Google Vertex AI */}
            {renderProviderCard('vertex')}

            {/* OpenAI Compatible */}
            {renderProviderCard('openai_compatible')}
          </div>

          {/* Help link */}
          <div className="border-t pt-4">
            <a
              href="https://github.com/lfnovo/open-notebook/blob/main/docs/5-CONFIGURATION/ai-providers.md"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-primary hover:underline"
            >
              {t.apiKeys.learnMore}
            </a>
          </div>
        </div>
      </div>

      {/* Config Form Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              {editingConfig
                ? t.apiKeys.editConfig.replace('{provider}', PROVIDER_DISPLAY_NAMES[editingProvider || ''] || editingProvider || '')
                : t.apiKeys.addConfig.replace('{provider}', PROVIDER_DISPLAY_NAMES[editingProvider || ''] || editingProvider || '')}
            </DialogTitle>
          </DialogHeader>
          {editingProvider && (
            <>
              {isLoadingConfig ? (
                <div className="flex items-center justify-center py-8">
                  <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <ConfigForm
                  provider={editingProvider}
                  providerDisplayName={PROVIDER_DISPLAY_NAMES[editingProvider] || editingProvider}
                  config={editingConfig}
                  onSubmit={handleSubmitConfig}
                  onCancel={() => {
                    setDialogOpen(false)
                    setEditingProvider(null)
                    setEditingConfig(null)
                    setEditingConfigId(null)
                  }}
                  isSubmitting={isSubmitting}
                  defaultUrl={DEFAULT_URLS[editingProvider]}
                />
              )}
            </>
          )}
        </DialogContent>
      </Dialog>
    </AppShell>
  )
}
