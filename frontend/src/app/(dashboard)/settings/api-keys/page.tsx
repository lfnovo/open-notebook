'use client'

import { useMemo } from 'react'
import { AppShell } from '@/components/layout/AppShell'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert'
import { Key, ShieldAlert } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useModels, useModelDefaults } from '@/lib/hooks/use-models'
import {
  useCredentials,
  useCredentialStatus,
  useEnvStatus,
} from '@/lib/hooks/use-credentials'
import { Credential } from '@/lib/api/credentials'
import { ALL_PROVIDERS } from '@/lib/providers'
import {
  DefaultModelSelectors,
  MigrationBanner,
  ProviderSection,
} from '@/components/settings'

export default function ApiKeysPage() {
  const { t } = useTranslation()

  // Data
  const { data: credentials, isLoading: credentialsLoading } = useCredentials()
  const { data: models, isLoading: modelsLoading } = useModels()
  const { data: defaults, isLoading: defaultsLoading } = useModelDefaults()
  const { data: credentialStatus } = useCredentialStatus()
  const { data: envStatus } = useEnvStatus()

  const encryptionReady = credentialStatus?.encryption_configured ?? true

  // Group credentials by provider
  const credentialsByProvider = useMemo(() => {
    const grouped: Record<string, Credential[]> = {}
    for (const provider of ALL_PROVIDERS) {
      grouped[provider] = []
    }
    if (credentials) {
      for (const cred of credentials) {
        if (!grouped[cred.provider]) grouped[cred.provider] = []
        grouped[cred.provider].push(cred)
      }
    }
    return grouped
  }, [credentials])

  // Providers needing migration
  const providersToMigrate = useMemo(() => {
    if (!envStatus || !credentialStatus) return []
    const providers: string[] = []
    for (const provider in envStatus) {
      if (envStatus[provider] && credentialStatus.source[provider] === 'environment') {
        providers.push(provider)
      }
    }
    return providers
  }, [envStatus, credentialStatus])

  // Sort: configured providers first
  const sortedProviders = useMemo(() => {
    return [...ALL_PROVIDERS].sort((a, b) => {
      const aHas = (credentialsByProvider[a]?.length || 0) > 0 ? 1 : 0
      const bHas = (credentialsByProvider[b]?.length || 0) > 0 ? 1 : 0
      return bHas - aHas
    })
  }, [credentialsByProvider])

  const isLoading = credentialsLoading || modelsLoading || defaultsLoading

  if (isLoading) {
    return (
      <AppShell>
        <div className="flex items-center justify-center min-h-[60vh]">
          <LoadingSpinner size="lg" />
        </div>
      </AppShell>
    )
  }

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto">
        <div className="p-6 space-y-6">
          {/* Header */}
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Key className="h-6 w-6" />
              {t('apiKeys.title')}
            </h1>
            <p className="text-muted-foreground mt-1">{t('apiKeys.description')}</p>
          </div>

          {/* Encryption warning */}
          {!encryptionReady && (
            <Alert className="border-red-500/50 bg-red-50 dark:bg-red-950/20">
              <ShieldAlert className="h-4 w-4 text-red-600 dark:text-red-400" />
              <AlertTitle className="text-red-800 dark:text-red-200">{t('apiKeys.encryptionRequired')}</AlertTitle>
              <AlertDescription className="text-red-700 dark:text-red-300">
                <code className="text-xs bg-red-100 dark:bg-red-900/30 px-1 py-0.5 rounded">
                  {t('apiKeys.encryptionRequiredDescription')}
                </code>
              </AlertDescription>
            </Alert>
          )}

          {/* Migration banner */}
          {encryptionReady && <MigrationBanner providersToMigrate={providersToMigrate} />}

          {/* Default Model Selectors */}
          {models && defaults && (
            <DefaultModelSelectors models={models} defaults={defaults} />
          )}

          {/* Provider Cards */}
          <div className="grid gap-4">
            {sortedProviders.map(provider => (
              <ProviderSection
                key={provider}
                provider={provider}
                credentials={credentialsByProvider[provider] || []}
                models={models || []}
                defaults={defaults || null}
                allCredentials={credentials || []}
                encryptionReady={encryptionReady}
              />
            ))}
          </div>

          {/* Help link */}
          <div className="border-t pt-4">
            <a
              href="https://github.com/lfnovo/open-notebook/blob/main/docs/5-CONFIGURATION/ai-providers.md"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-primary hover:underline"
            >
              {t('apiKeys.learnMore')}
            </a>
          </div>
        </div>
      </div>
    </AppShell>
  )
}
