'use client'

import { useMemo, useState } from 'react'

import { AppShell } from '@/components/layout/AppShell'
import { ModuleList } from './components/ModuleList'
import { Button } from '@/components/ui/button'
import { Plus, RefreshCw } from 'lucide-react'
import { useModules } from '@/lib/hooks/use-modules'
import { CreateModuleDialog } from '@/components/modules/CreateModuleDialog'
import { Input } from '@/components/ui/input'
import { useTranslation } from '@/lib/hooks/use-translation'

export default function ModulesPage() {
  const { t } = useTranslation()
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const { data: modules, isLoading, refetch } = useModules(false)
  const { data: archivedModules } = useModules(true)

  const normalizedQuery = searchTerm.trim().toLowerCase()

  const filteredActive = useMemo(() => {
    if (!modules) {
      return undefined
    }
    if (!normalizedQuery) {
      return modules
    }
    return modules.filter((module) =>
      module.name.toLowerCase().includes(normalizedQuery)
    )
  }, [modules, normalizedQuery])

  const filteredArchived = useMemo(() => {
    if (!archivedModules) {
      return undefined
    }
    if (!normalizedQuery) {
      return archivedModules
    }
    return archivedModules.filter((module) =>
      module.name.toLowerCase().includes(normalizedQuery)
    )
  }, [archivedModules, normalizedQuery])

  const hasArchived = (archivedModules?.length ?? 0) > 0
  const isSearching = normalizedQuery.length > 0

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto">
        <div className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-2xl font-bold">{t.modules.title}</h1>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
            <Input
              id="module-search"
              name="module-search"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder={t.modules.searchPlaceholder}
              autoComplete="off"
              aria-label={t.common.accessibility?.searchModules || "Search modules"}
              className="w-full sm:w-64"
            />
            <Button onClick={() => setCreateDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              {t.modules.newModule}
            </Button>
          </div>
        </div>
        
        <div className="space-y-8">
          <ModuleList 
            modules={filteredActive} 
            isLoading={isLoading}
            title={t.modules.activeModules}
            emptyTitle={isSearching ? t.common.noMatches : undefined}
            emptyDescription={isSearching ? t.common.tryDifferentSearch : undefined}
            onAction={!isSearching ? () => setCreateDialogOpen(true) : undefined}
            actionLabel={!isSearching ? t.modules.newModule : undefined}
          />
          
          {hasArchived && (
            <ModuleList 
              modules={filteredArchived} 
              isLoading={false}
              title={t.modules.archivedModules}
              collapsible
              emptyTitle={isSearching ? t.common.noMatches : undefined}
              emptyDescription={isSearching ? t.common.tryDifferentSearch : undefined}
            />
          )}
        </div>
        </div>
      </div>

      <CreateModuleDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
      />
    </AppShell>
  )
}