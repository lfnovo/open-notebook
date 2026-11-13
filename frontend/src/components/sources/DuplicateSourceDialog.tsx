'use client'

import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import { useTranslation } from '@/lib/hooks/use-translation'
import type { DuplicateSourceInfo } from '@/lib/types/api'

interface DuplicateSourceDialogProps {
  open: boolean
  matches: DuplicateSourceInfo[]
  onCancel: () => void
  onProceed: () => void
}

/**
 * Duplicate-source warning (#257): lists already-existing sources that match
 * the candidate (title, filename, date, excerpt) and offers Cancel vs
 * Proceed-anyway. Never auto-overwrites.
 */
export function DuplicateSourceDialog({
  open,
  matches,
  onCancel,
  onProceed,
}: DuplicateSourceDialogProps) {
  const { t } = useTranslation()

  return (
    <AlertDialog open={open} onOpenChange={(next) => !next && onCancel()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{t('sources.duplicateTitle')}</AlertDialogTitle>
          <AlertDialogDescription>
            {t('sources.duplicateDesc')}
          </AlertDialogDescription>
        </AlertDialogHeader>

        <ul className="max-h-60 space-y-3 overflow-y-auto py-1">
          {matches.map((match) => (
            <li key={match.id} className="rounded-md border p-3">
              <p className="text-sm font-medium">
                {match.title || match.filename || match.url || match.id}
              </p>
              <p className="text-xs text-muted-foreground">
                {[match.filename, match.url].filter(Boolean).join(' · ')}
              </p>
              {(match.created || match.updated) && (
                <p className="text-xs text-muted-foreground">
                  {new Date(match.created || match.updated || '').toLocaleString()}
                </p>
              )}
              {match.excerpt && (
                <p className="mt-1 line-clamp-3 text-xs text-muted-foreground">
                  {match.excerpt}
                </p>
              )}
            </li>
          ))}
        </ul>

        <AlertDialogFooter>
          <AlertDialogCancel>
            {t('common.cancel')}
          </AlertDialogCancel>
          <Button onClick={onProceed}>{t('sources.duplicateProceed')}</Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
