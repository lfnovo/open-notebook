'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Plus, Check, X } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { Credential } from '@/lib/api/credentials'
import { Model, ModelDefaults } from '@/lib/types/models'
import {
  PROVIDER_DISPLAY_NAMES,
  PROVIDER_MODALITIES,
  TYPE_ICONS,
  TYPE_COLORS,
  TYPE_COLOR_INACTIVE,
  TYPE_LABELS,
} from '@/lib/providers'
import { CredentialFormDialog } from './CredentialFormDialog'
import { CredentialItem } from './CredentialItem'

interface ProviderSectionProps {
  provider: string
  credentials: Credential[]
  models: Model[]
  defaults: ModelDefaults | null
  allCredentials: Credential[]
  encryptionReady: boolean
}

export function ProviderSection({
  provider,
  credentials,
  models,
  defaults,
  allCredentials,
  encryptionReady,
}: ProviderSectionProps) {
  const { t } = useTranslation()
  const [addOpen, setAddOpen] = useState(false)

  const displayName = PROVIDER_DISPLAY_NAMES[provider] || provider
  const modalities = PROVIDER_MODALITIES[provider] || ['language']
  const hasCredentials = credentials.length > 0

  // Models linked to any credential of this provider
  const providerModels = models.filter(m =>
    credentials.some(c => c.id === m.credential)
  )
  const activeTypes = new Set(providerModels.map(m => m.type))

  return (
    <Card className={!hasCredentials ? 'opacity-80' : undefined}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 flex-wrap">
            <CardTitle className="text-lg capitalize">{displayName}</CardTitle>
            <div className="flex items-center gap-1">
              {modalities.map((type) => (
                <Badge
                  key={type}
                  variant="secondary"
                  className={`text-xs gap-1 ${activeTypes.has(type) ? TYPE_COLORS[type] : TYPE_COLOR_INACTIVE}`}
                >
                  {TYPE_ICONS[type]}
                  <span className="hidden sm:inline">{TYPE_LABELS[type]}</span>
                </Badge>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {hasCredentials ? (
              <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100 dark:bg-emerald-900/30 dark:text-emerald-300">
                <Check className="mr-1 h-3 w-3" />
                {t('apiKeys.configured')}
              </Badge>
            ) : (
              <Badge variant="outline" className="text-muted-foreground border-dashed">
                <X className="mr-1 h-3 w-3" />
                {t('apiKeys.notConfigured')}
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        {credentials.map(cred => (
          <CredentialItem
            key={cred.id}
            credential={cred}
            models={models}
            defaults={defaults}
            allCredentials={allCredentials}
          />
        ))}

        <Button
          variant="outline"
          size="sm"
          onClick={() => setAddOpen(true)}
          className="w-full gap-2"
          disabled={!encryptionReady}
        >
          <Plus className="h-4 w-4" />
          {t('apiKeys.addConfig')}
        </Button>
      </CardContent>

      {addOpen && (
        <CredentialFormDialog
          open={addOpen}
          onOpenChange={setAddOpen}
          provider={provider}
        />
      )}
    </Card>
  )
}
