'use client'

import { useState } from 'react'
import { NoteResponse } from '@/lib/types/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Plus, StickyNote, Bot, User, MoreVertical, Trash2 } from 'lucide-react'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { EmptyState } from '@/components/common/EmptyState'
import { Badge } from '@/components/ui/badge'
import { NoteEditorDialog } from './NoteEditorDialog'
import { formatDistanceToNow } from 'date-fns'
import { ContextToggle } from '@/components/common/ContextToggle'
import { ContextMode } from '../[id]/page'
import { useDeleteNote } from '@/lib/hooks/use-notes'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'

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
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [noteToDelete, setNoteToDelete] = useState<string | null>(null)

  const deleteNote = useDeleteNote()

  const handleDeleteClick = (noteId: string) => {
    setNoteToDelete(noteId)
    setDeleteDialogOpen(true)
  }

  const handleDeleteConfirm = async () => {
    if (!noteToDelete) return

    try {
      await deleteNote.mutateAsync(noteToDelete)
      setDeleteDialogOpen(false)
      setNoteToDelete(null)
    } catch (error) {
      console.error('Failed to delete note:', error)
    }
  }

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
                      <Badge variant="secondary" className="text-xs">
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

                      {/* Ellipsis menu for delete action */}
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-48">
                          <DropdownMenuItem
                            onClick={(e) => {
                              e.stopPropagation()
                              handleDeleteClick(note.id)
                            }}
                            className="text-red-600 focus:text-red-600"
                          >
                            <Trash2 className="h-4 w-4 mr-2" />
                            Delete Note
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
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

      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title="Delete Note"
        description="Are you sure you want to delete this note? This action cannot be undone."
        confirmText="Delete"
        onConfirm={handleDeleteConfirm}
        isLoading={deleteNote.isPending}
        confirmVariant="destructive"
      />
    </>
  )
}
