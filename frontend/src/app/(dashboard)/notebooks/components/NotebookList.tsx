'use client'

import { NotebookResponse } from '@/lib/types/api'
import { NotebookCard } from './NotebookCard'
import { NotebookRow } from './NotebookRow'
import { useNotebookViewStore } from '@/lib/stores/notebook-view-store'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { EmptyState } from '@/components/common/EmptyState'
import { Book, ChevronDown, ChevronRight, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useState } from 'react'
import { useTranslation } from '@/lib/hooks/use-translation'

interface NotebookListProps {
  notebooks?: NotebookResponse[]
  isLoading: boolean
  title: string
  collapsible?: boolean
  emptyTitle?: string
  emptyDescription?: string
  onAction?: () => void
  actionLabel?: string
}

export function NotebookList({ 
  notebooks, 
  isLoading, 
  title, 
  collapsible = false,
  emptyTitle,
  emptyDescription,
  onAction,
  actionLabel,
}: NotebookListProps) {
  const { t } = useTranslation()
  const viewMode = useNotebookViewStore((state) => state.viewMode)
  const [isExpanded, setIsExpanded] = useState(!collapsible)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (!notebooks || notebooks.length === 0) {
    return (
      <EmptyState
        icon={Book}
        title={emptyTitle ?? t('common.noResults')}
        description={emptyDescription ?? t('chat.startByCreating')}
        action={onAction && actionLabel ? (
          <Button onClick={onAction} variant="outline" className="mt-4">
            <Plus className="h-4 w-4 mr-2" />
            {actionLabel}
          </Button>
        ) : undefined}
      />
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        {collapsible && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            {isExpanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </Button>
        )}
        <h2 className="text-lg font-semibold">{title}</h2>
        <span className="text-sm text-muted-foreground">({notebooks.length})</span>
      </div>

      {isExpanded && (
        viewMode === 'list' ? (
          <div className="flex flex-col gap-2">
            {notebooks.map((notebook) => (
              <NotebookRow key={notebook.id} notebook={notebook} />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {notebooks.map((notebook) => (
              <NotebookCard key={notebook.id} notebook={notebook} />
            ))}
          </div>
        )
      )}
    </div>
  )
}
