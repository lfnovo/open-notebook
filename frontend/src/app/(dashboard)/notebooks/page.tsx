'use client'

import { useMemo, useState } from 'react'

import { NotebookList } from './components/NotebookList'
import { Button } from '@/components/ui/button'
import { Plus, RefreshCw } from 'lucide-react'
import { useNotebooks, usePublicNotebooks } from '@/lib/hooks/use-notebooks'
import { CreateNotebookDialog } from '@/components/notebooks/CreateNotebookDialog'
import { Input } from '@/components/ui/input'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useCurrentWorkspace } from '@/lib/hooks/use-workspaces'
import { useAuthStore } from '@/lib/stores/auth-store'
import type { NotebookResponse } from '@/lib/types/api'

const filterNotebooks = (notebooks: NotebookResponse[] | undefined, query: string) => {
  if (!notebooks) {
    return undefined
  }
  if (!query) {
    return notebooks
  }
  return notebooks.filter((notebook) =>
    `${notebook.name} ${notebook.description || ''}`.toLowerCase().includes(query)
  )
}

export default function NotebooksPage() {
  const { t } = useTranslation()
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const {
    data: workspaceNotebooks,
    isLoading: workspaceLoading,
    refetch: refetchWorkspaceNotebooks,
  } = useNotebooks(false)
  const { data: archivedNotebooks, refetch: refetchArchivedNotebooks } = useNotebooks(true)
  const {
    data: publicNotebooks,
    isLoading: publicLoading,
    refetch: refetchPublicNotebooks,
  } = usePublicNotebooks(false)
  const { currentWorkspace, currentWorkspaceId } = useCurrentWorkspace()
  const isSystemAdmin = useAuthStore((state) => state.role === 'admin')

  const normalizedQuery = searchTerm.trim().toLowerCase()
  const currentWorkspaceTitle =
    currentWorkspace?.type === 'personal'
      ? t.notebooks.personalNotebooks
      : t.notebooks.teamNotebooks

  const filteredActive = useMemo(() => {
    return filterNotebooks(workspaceNotebooks, normalizedQuery)
  }, [workspaceNotebooks, normalizedQuery])

  const filteredPublic = useMemo(() => {
    const workspaceNotebookIds = new Set((workspaceNotebooks || []).map((notebook) => notebook.id))
    const scopedPublicNotebooks = publicNotebooks?.filter(
      (notebook) =>
        !workspaceNotebookIds.has(notebook.id) &&
        (!currentWorkspaceId || notebook.workspace_id !== currentWorkspaceId)
    )
    return filterNotebooks(scopedPublicNotebooks, normalizedQuery)
  }, [currentWorkspaceId, publicNotebooks, workspaceNotebooks, normalizedQuery])

  const filteredArchived = useMemo(() => {
    return filterNotebooks(archivedNotebooks, normalizedQuery)
  }, [archivedNotebooks, normalizedQuery])

  const hasArchived = (archivedNotebooks?.length ?? 0) > 0
  const isSearching = normalizedQuery.length > 0
  const isLoading = workspaceLoading || publicLoading
  const hasWorkspaceNotebooks = (filteredActive?.length ?? 0) > 0
  const hasPublicNotebooks = (filteredPublic?.length ?? 0) > 0
  const hasActiveGroups = hasWorkspaceNotebooks || hasPublicNotebooks
  const refreshNotebooks = () => {
    void refetchWorkspaceNotebooks()
    void refetchArchivedNotebooks()
    void refetchPublicNotebooks()
  }

  return (
    <>
      <div className="flex-1 overflow-y-auto">
        <div className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-2xl font-bold">{t.notebooks.title}</h1>
            <Button variant="outline" size="sm" onClick={refreshNotebooks}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
            <Input
              id="notebook-search"
              name="notebook-search"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder={t.notebooks.searchPlaceholder}
              autoComplete="off"
              aria-label={t.common.accessibility?.searchNotebooks || "Search notebooks"}
              className="w-full sm:w-64"
            />
            {!isSystemAdmin && (
              <Button onClick={() => setCreateDialogOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                {t.notebooks.newNotebook}
              </Button>
            )}
          </div>
        </div>
        
        <div className="space-y-8">
          {isLoading ? (
            <NotebookList
              notebooks={undefined}
              isLoading
              title={currentWorkspaceTitle}
            />
          ) : hasActiveGroups ? (
            <>
              {hasWorkspaceNotebooks && (
                <NotebookList
                  notebooks={filteredActive}
                  isLoading={false}
                  title={currentWorkspaceTitle}
                />
              )}

              {hasPublicNotebooks && (
                <NotebookList
                  notebooks={filteredPublic}
                  isLoading={false}
                  title={t.notebooks.publicNotebooks}
                />
              )}
            </>
          ) : (
            <NotebookList
              notebooks={[]}
              isLoading={false}
              title={currentWorkspaceTitle}
              emptyTitle={isSearching ? t.common.noMatches : undefined}
              emptyDescription={isSearching ? t.common.tryDifferentSearch : undefined}
              onAction={!isSearching && !isSystemAdmin ? () => setCreateDialogOpen(true) : undefined}
              actionLabel={!isSearching && !isSystemAdmin ? t.notebooks.newNotebook : undefined}
            />
          )}
          
          {hasArchived && (
            <NotebookList 
              notebooks={filteredArchived} 
              isLoading={false}
              title={t.notebooks.archivedNotebooks}
              collapsible
              emptyTitle={isSearching ? t.common.noMatches : undefined}
              emptyDescription={isSearching ? t.common.tryDifferentSearch : undefined}
            />
          )}
        </div>
        </div>
      </div>

      {!isSystemAdmin && (
        <CreateNotebookDialog
          open={createDialogOpen}
          onOpenChange={setCreateDialogOpen}
        />
      )}
    </>
  )
}
