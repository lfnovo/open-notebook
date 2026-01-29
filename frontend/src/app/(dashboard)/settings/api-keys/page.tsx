'use client'

import { useMemo } from 'react'
import { AppShell } from '@/components/layout/AppShell'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { RefreshCw, ChevronLeft, Key } from 'lucide-react'
import Link from 'next/link'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useApiKeysStatus, useEnvStatus } from '@/lib/hooks/use-api-keys'
import {
  MigrationBanner,
  ProviderCard,
  SimpleKeyForm,
  UrlKeyForm,
  AzureKeyForm,
  OpenAICompatibleForm,
  VertexKeyForm,
  type ModelType,
} from '@/components/settings'

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

export default function ApiKeysPage() {
  const { t } = useTranslation()
  const { data: status, isLoading: statusLoading, error: statusError, refetch: refetchStatus } = useApiKeysStatus()
  const { data: envStatus, isLoading: envLoading, refetch: refetchEnv } = useEnvStatus()

  const handleRefresh = () => {
    refetchStatus()
    refetchEnv()
  }

  // Count environment variables that could be migrated
  const envKeysCount = useMemo(() => {
    if (!envStatus) return 0
    return Object.values(envStatus).filter(Boolean).length
  }, [envStatus])

  if (statusLoading || envLoading) {
    return (
      <AppShell>
        <div className="flex items-center justify-center min-h-[60vh]">
          <LoadingSpinner size="lg" />
        </div>
      </AppShell>
    )
  }

  if (statusError || !status) {
    return (
      <AppShell>
        <div className="p-6">
          <Alert variant="destructive">
            <AlertTitle>{t.common.error}</AlertTitle>
            <AlertDescription>
              {statusError instanceof Error ? statusError.message : t.apiKeys.loadFailed}
            </AlertDescription>
          </Alert>
        </div>
      </AppShell>
    )
  }

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

          {/* Migration Banner */}
          <MigrationBanner envKeysCount={envKeysCount} />

          {/* Provider Cards */}
          <div className="grid gap-4">
            {/* Simple providers */}
            {PROVIDER_CONFIG.simple.map((provider) => (
              <ProviderCard
                key={provider}
                name={provider}
                displayName={PROVIDER_DISPLAY_NAMES[provider] || provider}
                isConfigured={status.configured[provider] ?? false}
                source={status.source[provider]}
                supportedTypes={PROVIDER_SUPPORTED_TYPES[provider]}
              >
                <SimpleKeyForm
                  provider={provider}
                  isConfigured={status.configured[provider] ?? false}
                  source={status.source[provider]}
                  placeholder={API_KEY_PLACEHOLDERS[provider]}
                  defaultUrl={DEFAULT_URLS[provider]}
                  docsUrl={PROVIDER_DOCS[provider]}
                />
              </ProviderCard>
            ))}

            {/* URL-based providers */}
            {PROVIDER_CONFIG.urlBased.map((provider) => (
              <ProviderCard
                key={provider}
                name={provider}
                displayName={PROVIDER_DISPLAY_NAMES[provider] || provider}
                isConfigured={status.configured[provider] ?? false}
                source={status.source[provider]}
                supportedTypes={PROVIDER_SUPPORTED_TYPES[provider]}
              >
                <UrlKeyForm
                  provider={provider}
                  isConfigured={status.configured[provider] ?? false}
                  source={status.source[provider]}
                  defaultUrl={DEFAULT_URLS[provider]}
                />
              </ProviderCard>
            ))}

            {/* Azure OpenAI */}
            <ProviderCard
              name="azure"
              displayName={PROVIDER_DISPLAY_NAMES.azure}
              isConfigured={status.configured.azure ?? false}
              source={status.source.azure}
              supportedTypes={PROVIDER_SUPPORTED_TYPES.azure}
            >
              <AzureKeyForm
                isConfigured={status.configured.azure ?? false}
                source={status.source.azure}
              />
            </ProviderCard>

            {/* Google Vertex AI */}
            <ProviderCard
              name="vertex"
              displayName={PROVIDER_DISPLAY_NAMES.vertex}
              isConfigured={status.configured.vertex ?? false}
              source={status.source.vertex}
              supportedTypes={PROVIDER_SUPPORTED_TYPES.vertex}
            >
              <VertexKeyForm
                isConfigured={status.configured.vertex ?? false}
                source={status.source.vertex}
              />
            </ProviderCard>

            {/* OpenAI Compatible */}
            <ProviderCard
              name="openai_compatible"
              displayName={PROVIDER_DISPLAY_NAMES.openai_compatible}
              isConfigured={status.configured.openai_compatible ?? false}
              source={status.source.openai_compatible}
              supportedTypes={PROVIDER_SUPPORTED_TYPES.openai_compatible}
            >
              <OpenAICompatibleForm
                isConfigured={status.configured.openai_compatible ?? false}
                source={status.source.openai_compatible}
              />
            </ProviderCard>
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
    </AppShell>
  )
}
