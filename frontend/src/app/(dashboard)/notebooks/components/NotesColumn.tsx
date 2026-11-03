'use client'

import { useState, useMemo, useRef } from 'react'
import { NoteResponse } from '@/lib/types/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Plus,
  StickyNote,
  Bot,
  User,
  MoreVertical,
  Trash2,
  ListChecks,
  ChevronDown,
  Paperclip,
  FileText,
  Download,
  Upload,
} from 'lucide-react'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { EmptyState } from '@/components/common/EmptyState'
import { Badge } from '@/components/ui/badge'
import { NoteEditorDialog } from './NoteEditorDialog'
import { NoteFileViewer } from './NoteFileViewer'
import { NotebookPodcasts } from './NotebookPodcasts'
import { getDateLocale } from '@/lib/utils/date-locale'
import { formatDistanceToNow } from 'date-fns'
import { ContextToggle } from '@/components/common/ContextToggle'
import type { NoteContextMode } from '../[id]/page'
import type { NoteContextDefault } from '@/lib/utils/source-context'
import { useDeleteNote, useUploadNoteFile } from '@/lib/hooks/use-notes'
import { useToast } from '@/lib/hooks/use-toast'
import {
  NOTE_FILE_EXTENSIONS,
  formatFileSize,
  isDraggingFiles,
  isSupportedNoteFile,
  saveNoteFile,
} from '@/lib/utils/note-files'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { CollapsibleColumn, createCollapseButton } from '@/components/notebooks/CollapsibleColumn'
import { useNotebookColumnsStore } from '@/lib/stores/notebook-columns-store'
import { useTranslation } from '@/lib/hooks/use-translation'

interface NotesColumnProps {
  notes?: NoteResponse[]
  isLoading: boolean
  notebookId: string
  contextSelections?: Record<string, NoteContextMode>
  onContextModeChange?: (noteId: string, mode: NoteContextMode) => void
  onBulkContextModeChange?: (action: NoteContextDefault) => void
}

export function NotesColumn({
  notes,
  isLoading,
  notebookId,
  contextSelections,
  onContextModeChange,
  onBulkContextModeChange
}: NotesColumnProps) {
  const { t, language } = useTranslation()
  const [editorOpen, setEditorOpen] = useState(false)
  const [editingNote, setEditingNote] = useState<NoteResponse | undefined>()
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [noteToDelete, setNoteToDelete] = useState<string | null>(null)

  const [viewerNote, setViewerNote] = useState<NoteResponse | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [uploading, setUploading] = useState(0)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const deleteNote = useDeleteNote()
  const uploadFile = useUploadNoteFile()
  const { toast } = useToast()

  // Collapsible column state
  const { notesCollapsed, toggleNotes } = useNotebookColumnsStore()
  const notesLabel = t('common.notes')
  const collapseButton = useMemo(
    () => createCollapseButton(toggleNotes, notesLabel),
    [toggleNotes, notesLabel]
  )

  const handleDeleteClick = (noteId: string) => {
    setNoteToDelete(noteId)
    setDeleteDialogOpen(true)
  }

  const handleOpenEditor = (note?: NoteResponse) => {
    setEditingNote(note)
    setEditorOpen(true)
  }

  // Dropped or picked files become notes one at a time (extraction can be slow
  // for big PDFs); the upload hook reports each failure itself.
  const handleFiles = async (files: File[]) => {
    const supported = files.filter(isSupportedNoteFile)
    const skipped = files.length - supported.length
    if (skipped > 0) {
      toast({
        title: t('noteFiles.unsupportedTitle'),
        description: t('noteFiles.unsupportedDesc', { types: NOTE_FILE_EXTENSIONS.join(' ') }),
        variant: 'destructive',
      })
    }
    if (supported.length === 0) return

    setUploading((n) => n + supported.length)
    let added = 0
    for (const file of supported) {
      try {
        await uploadFile.mutateAsync({ notebookId, file })
        added += 1
      } catch {
        // Error toast is handled by the hook.
      } finally {
        setUploading((n) => n - 1)
      }
    }
    if (added > 0) {
      toast({ title: t('common.success'), description: t('noteFiles.added', { count: added }) })
    }
  }

  const handleDownloadFile = async (note: NoteResponse) => {
    if (!note.attachment) return
    try {
      await saveNoteFile(note.id, note.attachment.name, note.attachment.type)
    } catch {
      toast({ title: t('common.error'), description: t('noteFiles.loadFailed'), variant: 'destructive' })
    }
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
      <CollapsibleColumn
        isCollapsed={notesCollapsed}
        onToggle={toggleNotes}
        collapsedIcon={StickyNote}
        collapsedLabel={notesLabel}
      >
        <Card
          className={`relative h-full flex flex-col flex-1 overflow-hidden ${isDragging ? 'ring-2 ring-ring' : ''}`}
          onDragEnter={(event) => {
            if (!isDraggingFiles(event)) return
            event.preventDefault()
            setIsDragging(true)
          }}
          onDragOver={(event) => {
            if (!isDraggingFiles(event)) return
            event.preventDefault()
            event.dataTransfer.dropEffect = 'copy'
            setIsDragging(true)
          }}
          onDragLeave={(event) => {
            // Ignore leaves into a child element; only clear when the pointer exits the card.
            if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
              setIsDragging(false)
            }
          }}
          onDrop={(event) => {
            if (!isDraggingFiles(event)) return
            event.preventDefault()
            setIsDragging(false)
            void handleFiles(Array.from(event.dataTransfer.files))
          }}
        >
          {isDragging && (
            <div
              className="pointer-events-none absolute inset-0 z-10 flex flex-col items-center justify-center gap-2 rounded-[inherit] bg-background/80 backdrop-blur-sm"
              data-testid="notes-drop-overlay"
            >
              <Upload className="h-8 w-8 text-teal" aria-hidden />
              <p className="text-sm font-medium">{t('noteFiles.dropHint')}</p>
              <p className="text-xs text-muted-foreground">{NOTE_FILE_EXTENSIONS.join(' ')}</p>
            </div>
          )}
          <CardHeader className="pb-3 flex-shrink-0">
            <div className="flex items-center justify-between gap-2">
              <CardTitle className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.13em] text-muted-foreground">
                <span aria-hidden className="h-3.5 w-[3px] rounded-full bg-gold" />
                {notesLabel}
              </CardTitle>
              <div className="flex items-center gap-2">
                {onBulkContextModeChange && notes && notes.length > 0 && (
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="sm" className="text-muted-foreground" title={t('sources.bulkContext')}>
                        <ListChecks className="h-4 w-4" />
                        <ChevronDown className="h-4 w-4 ml-1" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => onBulkContextModeChange('include')}>
                        {t('sources.includeAllInContext')}
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => onBulkContextModeChange('exclude')}>
                        {t('sources.excludeAllFromContext')}
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  hidden
                  accept={NOTE_FILE_EXTENSIONS.join(',')}
                  data-testid="notes-file-input"
                  onChange={(event) => {
                    const files = Array.from(event.target.files ?? [])
                    event.target.value = ''
                    void handleFiles(files)
                  }}
                />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => fileInputRef.current?.click()}
                  title={t('noteFiles.addFile')}
                  aria-label={t('noteFiles.addFile')}
                >
                  <Paperclip className="h-4 w-4" />
                </Button>
                <Button size="sm" onClick={() => handleOpenEditor()}>
                  <Plus className="h-4 w-4 mr-2" />
                  {t('common.writeNote')}
                </Button>
                {collapseButton}
              </div>
            </div>
          </CardHeader>

          <CardContent className="flex-1 overflow-y-auto min-h-0">
            {uploading > 0 && (
              <div className="mb-2 flex items-center gap-2 rounded-md border border-dashed p-3 text-sm text-muted-foreground" role="status">
                <LoadingSpinner />
                {t('noteFiles.adding', { count: uploading })}
              </div>
            )}
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <LoadingSpinner />
              </div>
            ) : !notes || notes.length === 0 ? (
              <EmptyState
                icon={StickyNote}
                title={t('notebooks.noNotesYet')}
                description={t('sources.createFirstNote') + ' ' + t('noteFiles.emptyHint')}
              />
            ) : (
              <div className="space-y-2">
                {notes.map((note) => (
                  <div
                    key={note.id}
                    className="p-3 border rounded-md bg-card shadow-none card-hover group relative cursor-pointer"
                    onClick={() => (note.attachment ? setViewerNote(note) : handleOpenEditor(note))}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        {note.attachment ? (
                          <>
                            <FileText className="h-4 w-4 text-sage" />
                            <Badge variant="secondary" className="text-xs uppercase">
                              {note.attachment.name.split('.').pop()}
                            </Badge>
                          </>
                        ) : (
                          <>
                            {note.note_type === 'ai' ? (
                              <Bot className="h-4 w-4 text-teal" />
                            ) : (
                              <User className="h-4 w-4 text-muted-foreground" />
                            )}
                            <Badge variant="secondary" className="text-xs">
                              {note.note_type === 'ai' ? t('common.aiGenerated') : t('common.human')}
                            </Badge>
                          </>
                        )}
                      </div>

                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground whitespace-nowrap">
                          {formatDistanceToNow(new Date(note.updated), { 
                            addSuffix: true,
                            locale: getDateLocale(language)
                          })}
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
                            {note.attachment && (
                              <DropdownMenuItem
                                onClick={(e) => {
                                  e.stopPropagation()
                                  void handleDownloadFile(note)
                                }}
                              >
                                <Download className="h-4 w-4 mr-2" />
                                {t('noteFiles.download')}
                              </DropdownMenuItem>
                            )}
                            <DropdownMenuItem
                              onClick={(e) => {
                                e.stopPropagation()
                                handleDeleteClick(note.id)
                              }}
                              className="text-destructive focus:text-destructive"
                            >
                              <Trash2 className="h-4 w-4 mr-2" />
                              {t('notebooks.deleteNote')}
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                    </div>

                    {note.title && (
                      <h4 className={`text-sm font-medium break-all ${note.attachment ? 'mb-1' : 'mb-2'}`}>
                        {note.title}
                      </h4>
                    )}

                    {note.attachment && (
                      <p className="text-xs text-muted-foreground">{formatFileSize(note.attachment.size)}</p>
                    )}

                    {note.content && (
                      <p className="text-sm text-muted-foreground line-clamp-3 break-all">
                        {note.content}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}

            <NotebookPodcasts notebookId={notebookId} />
          </CardContent>
        </Card>
      </CollapsibleColumn>

      <NoteEditorDialog
        open={editorOpen}
        onOpenChange={(open) => {
          setEditorOpen(open)
          if (!open) {
            setEditingNote(undefined)
          }
        }}
        notebookId={notebookId}
        note={editingNote}
      />

      <NoteFileViewer
        note={viewerNote}
        open={viewerNote !== null}
        onOpenChange={(open) => {
          if (!open) setViewerNote(null)
        }}
      />

      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title={t('notebooks.deleteNote')}
        description={t('notebooks.deleteNoteConfirm')}
        confirmText={t('common.delete')}
        onConfirm={handleDeleteConfirm}
        isLoading={deleteNote.isPending}
        confirmVariant="destructive"
      />
    </>
  )
}
