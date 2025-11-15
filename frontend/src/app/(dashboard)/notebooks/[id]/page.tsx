'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { AppShell } from '@/components/layout/AppShell'
import { NotebookHeader } from '../components/NotebookHeader'
import { SourcesColumn } from '../components/SourcesColumn'
import { NotesColumn } from '../components/NotesColumn'
import { ChatColumn } from '../components/ChatColumn'
import { useNotebook } from '@/lib/hooks/use-notebooks'
import { useSources } from '@/lib/hooks/use-sources'
import { useNotes } from '@/lib/hooks/use-notes'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { useNotebookColumnsStore } from '@/lib/stores/notebook-columns-store'
import { cn } from '@/lib/utils'

export type ContextMode = 'off' | 'insights' | 'full'

export interface ContextSelections {
  sources: Record<string, ContextMode>
  notes: Record<string, ContextMode>
}

export default function NotebookPage() {
  const params = useParams()

  // Ensure the notebook ID is properly decoded from URL
  const notebookId = decodeURIComponent(params.id as string)

  const { data: notebook, isLoading: notebookLoading } = useNotebook(notebookId)
  const { data: sources, isLoading: sourcesLoading, refetch: refetchSources } = useSources(notebookId)
  const { data: notes, isLoading: notesLoading } = useNotes(notebookId)

  // Get collapse states for dynamic layout
  const { sourcesCollapsed, notesCollapsed } = useNotebookColumnsStore()

  // Context selection state
  const [contextSelections, setContextSelections] = useState<ContextSelections>({
    sources: {},
    notes: {}
  })

  // Initialize default selections when sources/notes load
  useEffect(() => {
    if (sources && sources.length > 0) {
      setContextSelections(prev => {
        const newSourceSelections = { ...prev.sources }
        sources.forEach(source => {
          // Only set default if not already set
          if (!(source.id in newSourceSelections)) {
            // Default to 'insights' if has insights, otherwise 'full'
            newSourceSelections[source.id] = source.insights_count > 0 ? 'insights' : 'full'
          }
        })
        return { ...prev, sources: newSourceSelections }
      })
    }
  }, [sources])

  useEffect(() => {
    if (notes && notes.length > 0) {
      setContextSelections(prev => {
        const newNoteSelections = { ...prev.notes }
        notes.forEach(note => {
          // Only set default if not already set
          if (!(note.id in newNoteSelections)) {
            // Notes default to 'full'
            newNoteSelections[note.id] = 'full'
          }
        })
        return { ...prev, notes: newNoteSelections }
      })
    }
  }, [notes])

  // Handler to update context selection
  const handleContextModeChange = (itemId: string, mode: ContextMode, type: 'source' | 'note') => {
    setContextSelections(prev => ({
      ...prev,
      [type === 'source' ? 'sources' : 'notes']: {
        ...(type === 'source' ? prev.sources : prev.notes),
        [itemId]: mode
      }
    }))
  }

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
      <div className="flex flex-col flex-1 min-h-0">
        <div className="flex-shrink-0 p-6 pb-0">
          <NotebookHeader notebook={notebook} />
        </div>

        <div className="flex-1 p-6 pt-6 overflow-hidden">
          {/* Dynamic layout based on collapse states */}
          <div className={cn(
            'h-full min-h-0 gap-6 transition-all duration-150',
            // Mobile: stack vertically
            'flex flex-col',
            // Desktop: horizontal layout
            'lg:flex-row'
          )}>
            {/* Sources Column */}
            <div className={cn(
              'transition-all duration-150',
              // Mobile: full width
              'w-full',
              // Desktop: fixed 1/3 width when expanded, minimal when collapsed
              sourcesCollapsed ? 'lg:w-12 lg:flex-shrink-0' : 'lg:flex-none lg:basis-1/3'
            )}>
              <SourcesColumn
                sources={sources}
                isLoading={sourcesLoading}
                notebookId={notebookId}
                notebookName={notebook?.name}
                onRefresh={refetchSources}
                contextSelections={contextSelections.sources}
                onContextModeChange={(sourceId, mode) => handleContextModeChange(sourceId, mode, 'source')}
              />
            </div>

            {/* Notes Column */}
            <div className={cn(
              'transition-all duration-150',
              // Mobile: full width
              'w-full',
              // Desktop: fixed 1/3 width when expanded, minimal when collapsed
              notesCollapsed ? 'lg:w-12 lg:flex-shrink-0' : 'lg:flex-none lg:basis-1/3'
            )}>
              <NotesColumn
                notes={notes}
                isLoading={notesLoading}
                notebookId={notebookId}
                contextSelections={contextSelections.notes}
                onContextModeChange={(noteId, mode) => handleContextModeChange(noteId, mode, 'note')}
              />
            </div>

            {/* Chat Column - always expanded, takes remaining space */}
            <div className={cn(
              'transition-all duration-150',
              // Mobile: full width
              'w-full',
              // Desktop: flex-1 to take remaining space
              'lg:flex-1'
            )}>
              <ChatColumn
                notebookId={notebookId}
                contextSelections={contextSelections}
              />
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  )
}
