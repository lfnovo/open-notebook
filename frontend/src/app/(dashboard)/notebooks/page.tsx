'use client'

import { useState } from 'react'

import { AppShell } from '@/components/layout/AppShell'
import { NotebookList } from './components/NotebookList'
import { Button } from '@/components/ui/button'
import { Plus, RefreshCw } from 'lucide-react'
import { useNotebooks } from '@/lib/hooks/use-notebooks'
import { CreateNotebookDialog } from '@/components/notebooks/CreateNotebookDialog'

export default function NotebooksPage() {
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const { data: notebooks, isLoading, refetch } = useNotebooks(false)
  const { data: archivedNotebooks } = useNotebooks(true)

  return (
    <AppShell>
      <div className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-2xl font-bold">Notebooks</h1>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
          <Button onClick={() => setCreateDialogOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            New Notebook
          </Button>
        </div>
        
        <div className="space-y-8">
          <NotebookList 
            notebooks={notebooks} 
            isLoading={isLoading}
            title="Active Notebooks"
          />
          
          {archivedNotebooks && archivedNotebooks.length > 0 && (
            <NotebookList 
              notebooks={archivedNotebooks} 
              isLoading={false}
              title="Archived Notebooks"
              collapsible
            />
          )}
        </div>
      </div>

      <CreateNotebookDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
      />
    </AppShell>
  )
}
