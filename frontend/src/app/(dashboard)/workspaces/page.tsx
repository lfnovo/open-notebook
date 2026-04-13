'use client'

import { useState } from 'react'
import { AppShell } from '@/components/layout/AppShell'
import { useWorkspaces } from '@/lib/hooks/use-workspaces'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Plus, RefreshCw, FolderOpen } from 'lucide-react'
import { CreateWorkspaceDialog } from '@/components/workspaces/CreateWorkspaceDialog'
import { WorkspaceCard } from '@/components/workspaces/WorkspaceCard'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { EmptyState } from '@/components/common/EmptyState'

export default function WorkspacesPage() {
  const [createOpen, setCreateOpen] = useState(false)
  const [search, setSearch] = useState('')
  const { data: workspaces, isLoading, refetch } = useWorkspaces()

  const filtered = workspaces?.filter(ws =>
    ws.name.toLowerCase().includes(search.toLowerCase())
  ) ?? []

  return (
    <AppShell>
      <div className="flex flex-col gap-6 p-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Workspaces</h1>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="icon" onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4" />
            </Button>
            <Button onClick={() => setCreateOpen(true)}>
              <Plus className="h-4 w-4 mr-2" /> New Workspace
            </Button>
          </div>
        </div>
        <Input
          placeholder="Search workspaces..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="max-w-sm"
        />
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <LoadingSpinner />
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={FolderOpen}
            title="No workspaces"
            description="Create a workspace to get started."
            action={
              <Button onClick={() => setCreateOpen(true)}>
                <Plus className="h-4 w-4 mr-2" /> New Workspace
              </Button>
            }
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filtered.map(ws => (
              <WorkspaceCard key={ws.id} workspace={ws} />
            ))}
          </div>
        )}
      </div>
      <CreateWorkspaceDialog open={createOpen} onOpenChange={setCreateOpen} />
    </AppShell>
  )
}
