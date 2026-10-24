'use client'

import { useState } from 'react'
import { Download, ExternalLink, Trash2 } from 'lucide-react'

import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useTranslation } from '@/lib/hooks/use-translation'
import type { Artifact, ArtifactFormat } from '@/lib/types/artifacts'

const STATUS_CLASSES: Record<string, string> = {
  pending: 'bg-muted text-muted-foreground',
  running: 'bg-gold-tint text-gold-deep',
  processing: 'bg-gold-tint text-gold-deep',
  submitted: 'bg-gold-tint text-gold-deep',
  completed: 'bg-fern-tint text-fern-deep',
  failed: 'bg-destructive-tint text-destructive',
  error: 'bg-destructive-tint text-destructive',
  unknown: 'bg-muted text-muted-foreground',
}

const STATUS_LABELS: Record<string, string> = {
  pending: 'artifacts.statusPending',
  running: 'artifacts.statusRunning',
  processing: 'artifacts.statusRunning',
  submitted: 'artifacts.statusRunning',
  completed: 'artifacts.statusCompleted',
  failed: 'artifacts.statusFailed',
  error: 'artifacts.statusFailed',
  unknown: 'artifacts.statusUnknown',
}

function statusOf(artifact: Artifact): string {
  return artifact.job_status ?? 'unknown'
}

function downloadHref(artifact: Artifact, format: ArtifactFormat): string {
  if (!artifact.download_url) return '#'
  return `${artifact.download_url}?format=${format}`
}

function formatDate(value?: string | null): string {
  if (!value) return '-'
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? '-' : parsed.toLocaleDateString()
}

interface ArtifactListProps {
  artifacts: Artifact[]
  onDelete: (artifactId: string) => void
  deletingId?: string | null
}

export function ArtifactList({
  artifacts,
  onDelete,
  deletingId = null,
}: ArtifactListProps) {
  const { t } = useTranslation()
  const [pendingDelete, setPendingDelete] = useState<Artifact | null>(null)

  if (artifacts.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">{t('artifacts.emptyState')}</p>
    )
  }

  return (
    <div className="space-y-3">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-muted-foreground">
              <th className="py-2 pr-3 font-medium">{t('artifacts.colTitle')}</th>
              <th className="py-2 pr-3 font-medium">{t('artifacts.colKind')}</th>
              <th className="py-2 pr-3 font-medium">{t('artifacts.colStatus')}</th>
              <th className="py-2 pr-3 font-medium">{t('artifacts.colCreated')}</th>
              <th className="py-2 font-medium" />
            </tr>
          </thead>
          <tbody>
            {artifacts.map((artifact) => {
              const status = statusOf(artifact)
              return (
                <tr key={artifact.id} className="border-t border-border align-top">
                  <td className="py-2 pr-3">
                    <div className="font-medium">{artifact.title}</div>
                    {artifact.note_id && (
                      <a
                        className="inline-flex items-center gap-1 text-xs text-teal hover:underline"
                        href={`/notebooks/${artifact.notebook_id}`}
                      >
                        {t('artifacts.openNote')}
                        <ExternalLink className="h-3 w-3 shrink-0" aria-hidden="true" />
                      </a>
                    )}
                  </td>
                  <td className="py-2 pr-3 text-muted-foreground">
                    {artifact.kind === 'deck'
                      ? t('artifacts.kindDeck')
                      : t('artifacts.kindReport')}
                  </td>
                  <td className="py-2 pr-3">
                    <Badge
                      className={STATUS_CLASSES[status] ?? STATUS_CLASSES.unknown}
                      title={artifact.error_message ?? undefined}
                    >
                      {t(STATUS_LABELS[status] ?? STATUS_LABELS.unknown)}
                    </Badge>
                  </td>
                  <td className="py-2 pr-3 text-muted-foreground">
                    {formatDate(artifact.created)}
                  </td>
                  <td className="py-2">
                    <div className="flex flex-wrap items-center justify-end gap-2">
                      {artifact.files.length === 0 ? (
                        <span className="text-xs text-muted-foreground">
                          {t('artifacts.noFileYet')}
                        </span>
                      ) : (
                        artifact.files.map((format) => (
                          <a
                            key={format}
                            className="inline-flex items-center gap-1 text-xs text-teal hover:underline"
                            href={downloadHref(artifact, format as ArtifactFormat)}
                          >
                            <Download className="h-3 w-3 shrink-0" aria-hidden="true" />
                            {t('artifacts.download')} {format.toUpperCase()}
                          </a>
                        ))
                      )}
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        aria-label={t('artifacts.delete')}
                        disabled={deletingId === artifact.id}
                        onClick={() => setPendingDelete(artifact)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <ConfirmDialog
        open={pendingDelete !== null}
        onOpenChange={(open) => {
          if (!open) setPendingDelete(null)
        }}
        title={t('artifacts.deleteTitle')}
        description={t('artifacts.deleteDesc')}
        confirmText={t('artifacts.delete')}
        confirmVariant="destructive"
        isLoading={deletingId !== null && deletingId === pendingDelete?.id}
        onConfirm={() => {
          if (pendingDelete) onDelete(pendingDelete.id)
          setPendingDelete(null)
        }}
      />
    </div>
  )
}
