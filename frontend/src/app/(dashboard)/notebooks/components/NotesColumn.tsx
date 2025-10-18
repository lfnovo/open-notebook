'use client'

import { useState } from 'react'
import { NoteResponse } from '@/lib/types/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Plus, StickyNote, Bot, User } from 'lucide-react'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { EmptyState } from '@/components/common/EmptyState'
import { Badge } from '@/components/ui/badge'
import { NoteEditorDialog } from './NoteEditorDialog'
import { formatDistanceToNow } from 'date-fns'
import { ContextToggle } from '@/components/common/ContextToggle'
import { ContextMode } from '../[id]/page'

interface NotesColumnProps {
  notes?: NoteResponse[]
  isLoading: boolean
  notebookId: string
  contextSelections?: Record<string, ContextMode>
  onContextModeChange?: (noteId: string, mode: ContextMode) => void
}

export function NotesColumn({
  notes,
  isLoading,
  notebookId,
  contextSelections,
  onContextModeChange
}: NotesColumnProps) {
  const [showAddDialog, setShowAddDialog] = useState(false)
  const [editingNote, setEditingNote] = useState<NoteResponse | null>(null)

  return (
    <>
      <Card className="h-full flex flex-col flex-1 overflow-hidden">
        <CardHeader className="pb-3 flex-shrink-0">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">Notes</CardTitle>
            <Button
              size="sm"
              onClick={() => {
                setEditingNote(null)
                setShowAddDialog(true)
              }}
            >
              <Plus className="h-4 w-4 mr-2" />
              Write Note
            </Button>
          </div>
        </CardHeader>

        <CardContent className="flex-1 overflow-y-auto min-h-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <LoadingSpinner />
            </div>
          ) : !notes || notes.length === 0 ? (
            <EmptyState
              icon={StickyNote}
              title="No notes yet"
              description="Create your first note to capture insights and observations."
            />
          ) : (
            <div className="space-y-3">
              {notes.map((note) => (
                <div
                  key={note.id}
                  className="p-3 border rounded-lg card-hover group relative cursor-pointer"
                  onClick={() => setEditingNote(note)}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {note.note_type === 'ai' ? (
                        <Bot className="h-4 w-4 text-primary" />
                      ) : (
                        <User className="h-4 w-4 text-muted-foreground" />
                      )}
                      <Badge variant={note.note_type === 'ai' ? 'default' : 'secondary'} className="text-xs">
                        {note.note_type === 'ai' ? 'AI Generated' : 'Human'}
                      </Badge>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">
                        {formatDistanceToNow(new Date(note.updated), { addSuffix: true })}
                      </span>

                      {/* Context toggle - only show if handler provided */}
                      {onContextModeChange && contextSelections?.[note.id] && (
                        <div onClick={(event) => event.stopPropagation()}>
                          <ContextToggle
                            mode={contextSelections[note.id]}
                            hasInsights={false}
                            onChange={(mode) => onContextModeChange(note.id, mode)}
                          />
                        </div>
                      )}
                    </div>
                  </div>
                  
                  {note.title && (
                    <h4 className="text-sm font-medium mb-2">{note.title}</h4>
                  )}
                  
                  {note.content && (
                    <p className="text-sm text-muted-foreground line-clamp-3">
                      {note.content}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <NoteEditorDialog
        open={showAddDialog || Boolean(editingNote)}
        onOpenChange={(open) => {
          if (!open) {
            setShowAddDialog(false)
            setEditingNote(null)
          } else {
            setShowAddDialog(true)
          }
        }}
        notebookId={notebookId}
        note={editingNote ?? undefined}
      />
    </>
  )
}
