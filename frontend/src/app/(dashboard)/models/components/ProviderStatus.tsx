'use client'

import { useMemo, useState } from 'react'
import Link from 'next/link'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Check, X, Settings } from 'lucide-react'
import { ProviderAvailability } from '@/lib/types/models'
import { useTranslation } from '@/lib/hooks/use-translation'

interface ProviderStatusProps {
  providers: ProviderAvailability
}

export function ProviderStatus({ providers }: ProviderStatusProps) {
  const { t } = useTranslation()
  // Combine all providers, with available ones first
  const allProviders = useMemo(
    () => [
      ...providers.available.map((p) => ({ name: p, available: true })),
      ...providers.unavailable.map((p) => ({ name: p, available: false })),
    ],
    [providers.available, providers.unavailable],
  )

  const [expanded, setExpanded] = useState(false)

  const visibleProviders = useMemo(() => {
    if (expanded) {
      return allProviders
    }
    return allProviders.slice(0, 6)
  }, [allProviders, expanded])

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle>{t.models.aiProviders}</CardTitle>
            <CardDescription>
              {t.models.providerConfigDesc}
              <span className="ml-1">
                {t.models.configuredCount
                  .replace('{count}', providers.available.length.toString())
                  .replace('{total}', allProviders.length.toString())}
              </span>
            </CardDescription>
          </div>
          <Button variant="outline" size="sm" asChild>
            <Link href="/settings/api-keys">
              <Settings className="h-4 w-4 mr-2" />
              {t.models.configure}
            </Link>
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid gap-2 sm:grid-cols-2">
          {visibleProviders.map((provider) => {
            const supportedTypes = providers.supported_types[provider.name] ?? []

            return (
              <div
                key={provider.name}
                className={`flex items-center gap-3 rounded-lg border px-4 py-3 transition-colors ${
                  provider.available ? 'bg-card' : 'bg-muted/40'
                }`}
              >
                <div className={`flex items-center justify-center rounded-full p-1.5 ${
                  provider.available
                    ? 'bg-emerald-100 text-emerald-600 dark:bg-emerald-900/20 dark:text-emerald-300'
                    : 'bg-muted-foreground/10 text-muted-foreground'
                }`}>
                  {provider.available ? (
                    <Check className="h-3.5 w-3.5" />
                  ) : (
                    <X className="h-3.5 w-3.5" />
                  )}
                </div>

                <div className="flex min-w-0 flex-1 items-center justify-between gap-3">
                  <span
                    className={`truncate text-sm font-medium capitalize ${
                      !provider.available ? 'text-muted-foreground' : 'text-foreground'
                    }`}
                  >
                    {provider.name}
                  </span>

                   {provider.available ? (
                    <div className="flex flex-wrap items-center justify-end gap-1">
                      {supportedTypes.length > 0 ? (
                        supportedTypes.map((type) => (
                          <Badge key={type} variant="secondary" className="text-xs font-medium">
                            {(t.models as Record<string, string>)[type] || type.replace('_', ' ')}
                          </Badge>
                        ))
                      ) : (
                        <Badge variant="outline" className="text-xs">{t.models.noModels}</Badge>
                      )}
                    </div>
                  ) : (
                    <Badge variant="outline" className="text-xs text-muted-foreground border-dashed">
                      {t.models.notConfigured}
                    </Badge>
                  )}
                </div>
              </div>
            )
          })}
        </div>

         {allProviders.length > 6 ? (
          <div className="mt-4 flex justify-center">
            <button
              type="button"
              onClick={() => setExpanded((prev) => !prev)}
              className="text-sm font-medium text-primary hover:underline"
            >
              {expanded 
                ? t.models.seeLess 
                : t.models.seeAll.replace('{count}', allProviders.length.toString())}
            </button>
          </div>
        ) : null}

         <div className="mt-6 pt-4 border-t">
          <a
            href="https://github.com/lfnovo/open-notebook/blob/main/docs/5-CONFIGURATION/ai-providers.md"
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-primary hover:underline"
          >
            {t.models.learnMore}
          </a>
        </div>
      </CardContent>
    </Card>
  )
}
