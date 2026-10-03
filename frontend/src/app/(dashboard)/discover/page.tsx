'use client'

import { useState } from 'react'

import { DiscoverForm, DiscoverFormValues } from '@/components/discover/DiscoverForm'
import { DiscoverResults } from '@/components/discover/DiscoverResults'
import { AppShell } from '@/components/layout/AppShell'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useDiscoverSources } from '@/lib/hooks/use-discover'
import { useNotebooks } from '@/lib/hooks/use-notebooks'
import { useTranslation } from '@/lib/hooks/use-translation'
import type { DiscoverSourcesResponse } from '@/lib/types/discover'

export default function DiscoverPage() {
  const { t } = useTranslation()
  const { data: notebooks } = useNotebooks()
  const discover = useDiscoverSources()
  const [result, setResult] = useState<DiscoverSourcesResponse | null>(null)

  function handleSubmit(values: DiscoverFormValues) {
    setResult(null)
    discover.mutate(
      {
        query: values.query,
        notebook_id: values.notebookId,
        limit: values.limit,
        dry_run: values.dryRun,
      },
      { onSuccess: (data) => setResult(data) }
    )
  }

  return (
    <AppShell>
      <div className="mx-auto w-full max-w-3xl flex-1 overflow-y-auto space-y-6 p-6">
        <header className="space-y-1">
          <h1 className="font-display text-2xl font-semibold">
            {t('discover.title')}
          </h1>
          <p className="text-sm text-muted-foreground">{t('discover.subtitle')}</p>
        </header>

        <Card>
          <CardHeader>
            <CardTitle>{t('discover.title')}</CardTitle>
          </CardHeader>
          <CardContent>
            <DiscoverForm
              notebooks={(notebooks ?? []).map((notebook) => ({
                id: notebook.id,
                name: notebook.name,
              }))}
              submitting={discover.isPending}
              onSubmit={handleSubmit}
            />
          </CardContent>
        </Card>

        {result && (
          <Card>
            <CardContent className="pt-6">
              <DiscoverResults
                results={result.results}
                createdCount={result.created_count}
                skippedCount={result.skipped_count}
                notebookId={result.notebook_id}
              />
            </CardContent>
          </Card>
        )}
      </div>
    </AppShell>
  )
}
