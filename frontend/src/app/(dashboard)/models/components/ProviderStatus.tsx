'use client'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Check, X } from 'lucide-react'
import { ProviderAvailability } from '@/lib/types/models'

interface ProviderStatusProps {
  providers: ProviderAvailability
}

export function ProviderStatus({ providers }: ProviderStatusProps) {
  // Combine all providers, with available ones first
  const allProviders = [
    ...providers.available.map(p => ({ name: p, available: true })),
    ...providers.unavailable.map(p => ({ name: p, available: false }))
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle>AI Providers</CardTitle>
        <CardDescription>
          Configure providers through environment variables to enable their models. 
          <span className="ml-1">
            {providers.available.length} of {allProviders.length} configured
          </span>
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {allProviders.map((provider) => (
            <div 
              key={provider.name} 
              className={`relative rounded-lg border p-4 transition-opacity ${
                provider.available ? 'bg-card' : 'bg-muted/30 opacity-60'
              }`}
            >
              <div className="flex items-start gap-3">
                <div className={`rounded-full p-1.5 ${
                  provider.available 
                    ? 'bg-green-100 dark:bg-green-900/20' 
                    : 'bg-muted'
                }`}>
                  {provider.available ? (
                    <Check className="h-3.5 w-3.5 text-green-600 dark:text-green-400" />
                  ) : (
                    <X className="h-3.5 w-3.5 text-muted-foreground" />
                  )}
                </div>
                <div className="flex-1 space-y-1">
                  <h4 className={`text-sm font-medium capitalize ${
                    !provider.available ? 'text-muted-foreground' : ''
                  }`}>
                    {provider.name}
                  </h4>
                  {provider.available ? (
                    <div className="flex flex-wrap gap-1">
                      {providers.supported_types[provider.name]?.map((type) => (
                        <Badge key={type} variant="secondary" className="text-xs">
                          {type.replace('_', ' ')}
                        </Badge>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-muted-foreground">Not configured</p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-6 pt-4 border-t">
          <a 
            href="https://github.com/lfnovo/open-notebook/blob/main/docs/models.md" 
            target="_blank" 
            rel="noopener noreferrer"
            className="text-sm text-primary hover:underline"
          >
            Learn how to configure providers →
          </a>
        </div>
      </CardContent>
    </Card>
  )
}