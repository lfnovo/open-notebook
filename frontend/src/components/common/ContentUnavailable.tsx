'use client'

import { AlertCircle, FileQuestion } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/common/EmptyState'
import { useTranslation } from '@/lib/hooks/use-translation'

interface ContentUnavailableProps {
  /**
   * 'not-found' — the item was deleted or no longer exists (HTTP 404).
   * 'error' — the item could not be loaded (network/server failure).
   */
  variant: 'not-found' | 'error'
  onClose?: () => void
}

/**
 * Shared friendly state for content that cannot be displayed.
 *
 * Used by the source, note and insight dialogs so that dangling references
 * (e.g. citations in old chat messages pointing at deleted items) render the
 * exact same explanation everywhere instead of a blank dialog or a raw error.
 */
export function ContentUnavailable({ variant, onClose }: ContentUnavailableProps) {
  const { t } = useTranslation()
  const notFound = variant === 'not-found'

  return (
    <div
      className="flex h-full flex-col justify-center px-6"
      data-testid="content-unavailable"
    >
      <EmptyState
        icon={notFound ? FileQuestion : AlertCircle}
        title={
          notFound
            ? t('common.contentUnavailable.notFoundTitle')
            : t('common.contentUnavailable.errorTitle')
        }
        description={
          notFound
            ? t('common.contentUnavailable.notFoundDescription')
            : t('common.contentUnavailable.errorDescription')
        }
        action={
          onClose && (
            <Button variant="outline" size="sm" onClick={onClose}>
              {t('common.close')}
            </Button>
          )
        }
      />
    </div>
  )
}
