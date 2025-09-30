'use client'

import { useParams, useRouter } from 'next/navigation'
import { AppShell } from '@/components/layout/AppShell'
import { NotebookHeader } from '../components/NotebookHeader'
import { SourcesColumn } from '../components/SourcesColumn'
import { NotesColumn } from '../components/NotesColumn'
import { ChatColumn } from '../components/ChatColumn'
import { useNotebook } from '@/lib/hooks/use-notebooks'
import { useSources } from '@/lib/hooks/use-sources'
import { useNotes } from '@/lib/hooks/use-notes'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'

export default function NotebookPage() {
  const params = useParams()
  const router = useRouter()
  
  // Ensure the notebook ID is properly decoded from URL
  const notebookId = decodeURIComponent(params.id as string)

  const { data: notebook, isLoading: notebookLoading, refetch } = useNotebook(notebookId)
  const { data: sources, isLoading: sourcesLoading, refetch: refetchSources } = useSources(notebookId)
  const { data: notes, isLoading: notesLoading } = useNotes(notebookId)

  if (notebookLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (!notebook) {
    return (
      <AppShell>
        <div className="p-6">
          <h1 className="text-2xl font-bold mb-4">Notebook Not Found</h1>
          <p className="text-muted-foreground">The requested notebook could not be found.</p>
        </div>
      </AppShell>
    )
  }

  return (
    <AppShell>
      <div className="p-6 space-y-6">
        <NotebookHeader notebook={notebook} />
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-8rem)]">
          <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-6">
            <SourcesColumn
              sources={sources}
              isLoading={sourcesLoading}
              notebookId={notebookId}
              notebookName={notebook?.name}
              onRefresh={refetchSources}
            />
            <NotesColumn 
              notes={notes} 
              isLoading={notesLoading}
              notebookId={notebookId}
            />
          </div>
          
          <ChatColumn notebookId={notebookId} />
        </div>
      </div>
    </AppShell>
  )
}