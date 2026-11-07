'use client'

import { ExternalLink } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { useTranslation } from '@/lib/hooks/use-translation'
import type {
  DiscoveredSource,
  DiscoveredSourceStatus,
} from '@/lib/types/discover'

const STATUS_CLASSES: Record<DiscoveredSourceStatus, string> = {
  candidate: 'bg-muted text-muted-foreground',
  created: 'bg-fern-tint text-fern-deep',
  skipped: 'bg-gold-tint text-gold-deep',
  error: 'bg-destructive-tint text-destructive',
}

const STATUS_LABELS: Record<DiscoveredSourceStatus, string> = {
  candidate: 'discover.statusCandidate',
  created: 'discover.statusCreated',
  skipped: 'discover.statusSkipped',
  error: 'discover.statusError',
}

function hostOf(url: string): string {
  try {
    return new URL(url).hostname
  } catch {
    return url
  }
}

interface DiscoverResultsProps {
  results: DiscoveredSource[]
  createdCount: number
  skippedCount: number
  notebookId: string
}

export function DiscoverResults({
  results,
  createdCount,
  skippedCount,
  notebookId,
}: DiscoverResultsProps) {
  const { t } = useTranslation()

  if (results.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">{t('discover.emptyState')}</p>
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-muted-foreground">
          {t('discover.summary', { created: createdCount, skipped: skippedCount })}
        </p>
        <a
          className="text-sm text-teal hover:underline"
          href={`/notebooks/${notebookId}`}
        >
          {t('discover.openNotebook')}
        </a>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-muted-foreground">
              <th className="py-2 pr-3 font-medium">{t('discover.colTitle')}</th>
              <th className="py-2 pr-3 font-medium">{t('discover.colUrl')}</th>
              <th className="py-2 pr-3 font-medium">{t('discover.colScore')}</th>
              <th className="py-2 font-medium">{t('discover.colStatus')}</th>
            </tr>
          </thead>
          <tbody>
            {results.map((result) => (
              <tr key={result.url} className="border-t border-border align-top">
                <td className="py-2 pr-3">
                  <a
                    className="inline-flex items-center gap-1 hover:underline"
                    href={result.url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {result.title || result.url}
                    <ExternalLink className="h-3 w-3 shrink-0" aria-hidden="true" />
                  </a>
                </td>
                <td className="py-2 pr-3 text-muted-foreground">
                  {hostOf(result.url)}
                </td>
                <td className="py-2 pr-3 text-muted-foreground">
                  {result.score.toFixed(2)}
                </td>
                <td className="py-2">
                  <Badge
                    className={STATUS_CLASSES[result.status]}
                    title={result.error ?? undefined}
                  >
                    {t(STATUS_LABELS[result.status])}
                  </Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
