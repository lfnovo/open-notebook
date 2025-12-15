'use client'

import { useState, useMemo, useRef, useCallback, useEffect } from 'react'
import { SourceListResponse } from '@/lib/types/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Plus, FileText, Link2, ChevronDown, Loader2 } from 'lucide-react'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { EmptyState } from '@/components/common/EmptyState'
import { AddSourceDialog } from '@/components/sources/AddSourceDialog'
import { AddExistingSourceDialog } from '@/components/sources/AddExistingSourceDialog'
import { SourceCard } from '@/components/sources/SourceCard'
import { useDeleteSource, useRetrySource, useRemoveSourceFromNotebook } from '@/lib/hooks/use-sources'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { useModalManager } from '@/lib/hooks/use-modal-manager'
import { ContextMode } from '../[id]/page'
import { CollapsibleColumn, createCollapseButton } from '@/components/notebooks/CollapsibleColumn'
import { useNotebookColumnsStore } from '@/lib/stores/notebook-columns-store'

interface SourcesColumnProps {
  sources?: SourceListResponse[]
  isLoading: boolean
  notebookId: string
  notebookName?: string
  onRefresh?: () => void
  contextSelections?: Record<string, ContextMode>
  onContextModeChange?: (sourceId: string, mode: ContextMode) => void
  // Pagination props
  hasNextPage?: boolean
  isFetchingNextPage?: boolean
  fetchNextPage?: () => void
}

export function SourcesColumn({
  sources,
  isLoading,
  notebookId,
  onRefresh,
  contextSelections,
  onContextModeChange,
  hasNextPage,
  isFetchingNextPage,
  fetchNextPage,
}: SourcesColumnProps) {
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [addDialogOpen, setAddDialogOpen] = useState(false)
  const [addExistingDialogOpen, setAddExistingDialogOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [sourceToDelete, setSourceToDelete] = useState<string | null>(null)
  const [removeDialogOpen, setRemoveDialogOpen] = useState(false)
  const [sourceToRemove, setSourceToRemove] = useState<string | null>(null)

  const { openModal } = useModalManager()
  const deleteSource = useDeleteSource()
  const retrySource = useRetrySource()
  const removeFromNotebook = useRemoveSourceFromNotebook()

  // Collapsible column state
  const { sourcesCollapsed, toggleSources } = useNotebookColumnsStore()
  const collapseButton = useMemo(
    () => createCollapseButton(toggleSources, 'Sources'),
    [toggleSources]
  )

  // Scroll container ref for infinite scroll
  const scrollContainerRef = useRef<HTMLDivElement>(null)

  // Handle scroll for infinite loading
  const handleScroll = useCallback(() => {
    const container = scrollContainerRef.current
    if (!container || !hasNextPage || isFetchingNextPage || !fetchNextPage) return

    const { scrollTop, scrollHeight, clientHeight } = container
    // Load more when user scrolls within 200px of the bottom
    if (scrollHeight - scrollTop - clientHeight < 200) {
      fetchNextPage()
    }
  }, [hasNextPage, isFetchingNextPage, fetchNextPage])

  // Attach scroll listener
  useEffect(() => {
    const container = scrollContainerRef.current
    if (!container) return

    container.addEventListener('scroll', handleScroll)
    return () => container.removeEventListener('scroll', handleScroll)
  }, [handleScroll])
  
  const handleDeleteClick = (sourceId: string) => {
    setSourceToDelete(sourceId)
    setDeleteDialogOpen(true)
  }

  const handleDeleteConfirm = async () => {
    if (!sourceToDelete) return

    try {
      await deleteSource.mutateAsync(sourceToDelete)
      setDeleteDialogOpen(false)
      setSourceToDelete(null)
      onRefresh?.()
    } catch (error) {
      console.error('Failed to delete source:', error)
    }
  }

  const handleRemoveFromNotebook = (sourceId: string) => {
    setSourceToRemove(sourceId)
    setRemoveDialogOpen(true)
  }

  const handleRemoveConfirm = async () => {
    if (!sourceToRemove) return

    try {
      await removeFromNotebook.mutateAsync({
        notebookId,
        sourceId: sourceToRemove
      })
      setRemoveDialogOpen(false)
      setSourceToRemove(null)
    } catch (error) {
      console.error('Failed to remove source from notebook:', error)
      // Error toast is handled by the hook
    }
  }

  const handleRetry = async (sourceId: string) => {
    try {
      await retrySource.mutateAsync(sourceId)
    } catch (error) {
      console.error('Failed to retry source:', error)
    }
  }

  const handleSourceClick = (sourceId: string) => {
    openModal('source', sourceId)
  }

  return (
    <>
      <CollapsibleColumn
        isCollapsed={sourcesCollapsed}
        onToggle={toggleSources}
        collapsedIcon={FileText}
        collapsedLabel="Sources"
      >
        <Card className="h-full flex flex-col flex-1 overflow-hidden">
          <CardHeader className="pb-3 flex-shrink-0">
            <div className="flex items-center justify-between gap-2">
              <CardTitle className="text-lg">Sources</CardTitle>
              <div className="flex items-center gap-2">
                <DropdownMenu open={dropdownOpen} onOpenChange={setDropdownOpen}>
                  <DropdownMenuTrigger asChild>
                    <Button size="sm">
                      <Plus className="h-4 w-4 mr-2" />
                      Add Source
                      <ChevronDown className="h-4 w-4 ml-2" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={() => { setDropdownOpen(false); setAddDialogOpen(true); }}>
                      <Plus className="h-4 w-4 mr-2" />
                      Add New Source
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => { setDropdownOpen(false); setAddExistingDialogOpen(true); }}>
                      <Link2 className="h-4 w-4 mr-2" />
                      Add Existing Source
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
                {collapseButton}
              </div>
            </div>
          </CardHeader>

          <CardContent ref={scrollContainerRef} className="flex-1 overflow-y-auto min-h-0">
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <LoadingSpinner />
              </div>
            ) : !sources || sources.length === 0 ? (
              <EmptyState
                icon={FileText}
                title="No sources yet"
                description="Add your first source to start building your knowledge base."
              />
            ) : (
              <div className="space-y-3">
                {sources.map((source) => (
                  <SourceCard
                    key={source.id}
                    source={source}
                    onClick={handleSourceClick}
                    onDelete={handleDeleteClick}
                    onRetry={handleRetry}
                    onRemoveFromNotebook={handleRemoveFromNotebook}
                    onRefresh={onRefresh}
                    showRemoveFromNotebook={true}
                    contextMode={contextSelections?.[source.id]}
                    onContextModeChange={onContextModeChange
                      ? (mode) => onContextModeChange(source.id, mode)
                      : undefined
                    }
                  />
                ))}
                {/* Loading indicator for infinite scroll */}
                {isFetchingNextPage && (
                  <div className="flex items-center justify-center py-4">
                    <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </CollapsibleColumn>

      <AddSourceDialog
        open={addDialogOpen}
        onOpenChange={setAddDialogOpen}
        defaultNotebookId={notebookId}
      />

      <AddExistingSourceDialog
        open={addExistingDialogOpen}
        onOpenChange={setAddExistingDialogOpen}
        notebookId={notebookId}
        onSuccess={onRefresh}
      />

      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title="Delete Source"
        description="Are you sure you want to delete this source? This action cannot be undone."
        confirmText="Delete"
        onConfirm={handleDeleteConfirm}
        isLoading={deleteSource.isPending}
        confirmVariant="destructive"
      />

      <ConfirmDialog
        open={removeDialogOpen}
        onOpenChange={setRemoveDialogOpen}
        title="Remove Source from Notebook"
        description="Are you sure you want to remove this source from the notebook? The source itself will not be deleted."
        confirmText="Remove"
        onConfirm={handleRemoveConfirm}
        isLoading={removeFromNotebook.isPending}
        confirmVariant="default"
      />
    </>
  )
}
