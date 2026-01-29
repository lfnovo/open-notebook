'use client'

import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { AlertTriangle, ArrowRight, Loader2 } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useMigrateApiKeys } from '@/lib/hooks/use-api-keys'

interface MigrationBannerProps {
  envKeysCount: number
}

export function MigrationBanner({ envKeysCount }: MigrationBannerProps) {
  const { t } = useTranslation()
  const migrate = useMigrateApiKeys()

  if (envKeysCount === 0) {
    return null
  }

  return (
    <Alert className="border-amber-500/50 bg-amber-50 dark:bg-amber-950/20">
      <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
      <AlertTitle className="text-amber-800 dark:text-amber-200">
        {t.apiKeys.migrationAvailable}
      </AlertTitle>
      <AlertDescription className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <span className="text-amber-700 dark:text-amber-300">
          {t.apiKeys.migrationDescription.replace('{count}', envKeysCount.toString())}
        </span>
        <Button
          variant="outline"
          size="sm"
          onClick={() => migrate.mutate()}
          disabled={migrate.isPending}
          className="shrink-0 border-amber-500 text-amber-700 hover:bg-amber-100 dark:border-amber-400 dark:text-amber-300 dark:hover:bg-amber-900/30"
        >
          {migrate.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              {t.apiKeys.migrating}
            </>
          ) : (
            <>
              {t.apiKeys.migrateToDatabase}
              <ArrowRight className="ml-2 h-4 w-4" />
            </>
          )}
        </Button>
      </AlertDescription>
    </Alert>
  )
}
