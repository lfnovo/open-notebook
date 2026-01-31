'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Check, X, MessageSquare, Code, Mic, Volume2, Layers } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { ConfigList } from './ConfigList'
import { ProviderCredential } from '@/lib/api/api-keys'

export type ModelType = 'language' | 'embedding' | 'text_to_speech' | 'speech_to_text'

interface ProviderCardProps {
  name: string
  displayName: string
  /** Legacy mode: single config status */
  isConfigured?: boolean
  source?: string
  supportedTypes?: ModelType[]
  /** Legacy mode: form component */
  children?: React.ReactNode
  /** New mode: list of configurations */
  configs?: ProviderCredential[]
  onAddConfig?: () => void
  onEditConfig?: (configId: string) => void
  isLoading?: boolean
}

const TYPE_ICONS: Record<ModelType, React.ReactNode> = {
  language: <MessageSquare className="h-3 w-3" />,
  embedding: <Code className="h-3 w-3" />,
  text_to_speech: <Volume2 className="h-3 w-3" />,
  speech_to_text: <Mic className="h-3 w-3" />,
}

const TYPE_COLORS: Record<ModelType, string> = {
  language: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  embedding: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
  text_to_speech: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  speech_to_text: 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300',
}

export function ProviderCard({
  name,
  displayName,
  isConfigured = false,
  source,
  supportedTypes,
  children,
  configs,
  onAddConfig,
  onEditConfig,
  isLoading = false,
}: ProviderCardProps) {
  const { t } = useTranslation()

  const typeLabels: Record<ModelType, string> = {
    language: t.apiKeys.typeLanguage,
    embedding: t.apiKeys.typeEmbedding,
    text_to_speech: t.apiKeys.typeTts,
    speech_to_text: t.apiKeys.typeStt,
  }

  const hasConfigs = configs && configs.length > 0
  const configCount = configs?.length || 0

  // Determine if provider is configured (either legacy or new mode)
  const providerConfigured = isConfigured || hasConfigs

  return (
    <Card className={!providerConfigured ? 'opacity-80' : undefined}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 flex-wrap">
            <CardTitle className="flex items-center gap-2 text-lg capitalize">
              {displayName}
            </CardTitle>
            {supportedTypes && supportedTypes.length > 0 && (
              <div className="flex items-center gap-1">
                {supportedTypes.map((type) => (
                  <Badge
                    key={type}
                    variant="secondary"
                    className={`text-xs gap-1 ${TYPE_COLORS[type]}`}
                    title={typeLabels[type]}
                  >
                    {TYPE_ICONS[type]}
                    <span className="hidden sm:inline">{typeLabels[type]}</span>
                  </Badge>
                ))}
              </div>
            )}
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {/* Source badge */}
            {source && providerConfigured && (
              <Badge variant="outline" className="text-xs">
                {source === 'database' ? t.apiKeys.sourceDatabase : t.apiKeys.sourceEnvironment}
              </Badge>
            )}

            {/* Config count badge (new multi-config mode) */}
            {hasConfigs && (
              <Badge variant="secondary" className="text-xs gap-1">
                <Layers className="h-3 w-3" />
                {t.apiKeys.configsCount.replace('{count}', configCount.toString())}
              </Badge>
            )}

            {/* Status badge */}
            {providerConfigured ? (
              <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100 dark:bg-emerald-900/30 dark:text-emerald-300">
                <Check className="mr-1 h-3 w-3" />
                {hasConfigs ? t.apiKeys.configuredMultiple : t.apiKeys.configured}
              </Badge>
            ) : (
              <Badge variant="outline" className="text-muted-foreground border-dashed">
                <X className="mr-1 h-3 w-3" />
                {t.apiKeys.notConfigured}
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* New multi-config mode */}
        {hasConfigs ? (
          <ConfigList
            provider={name}
            providerDisplayName={displayName}
            configs={configs}
            onAddConfig={onAddConfig || (() => {})}
            onEditConfig={onEditConfig || (() => {})}
            isLoading={isLoading}
          />
        ) : (
          /* Legacy single-config mode */
          children
        )}
      </CardContent>
    </Card>
  )
}
