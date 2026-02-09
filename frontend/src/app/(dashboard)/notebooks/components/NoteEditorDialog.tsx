'use client'

import { Controller, useForm, useWatch } from 'react-hook-form'
import { useEffect, useState, useRef, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { useCreateNote, useUpdateNote, useNote } from '@/lib/hooks/use-notes'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { MarkdownEditor } from '@/components/ui/markdown-editor'
import { InlineEdit } from '@/components/common/InlineEdit'
import { cn } from "@/lib/utils";
import { useTranslation } from '@/lib/hooks/use-translation'
import { GripHorizontal, GripVertical } from 'lucide-react'

const MODAL_MIN_HEIGHT_PX = 600
const MODAL_DEFAULT_HEIGHT_VH = 80
const MODAL_MAX_HEIGHT_VH = 90

function getDefaultHeightPx(): number {
  if (typeof window === 'undefined') return 600
  const maxPx = Math.floor((MODAL_MAX_HEIGHT_VH / 100) * window.innerHeight)
  const defaultPx = Math.floor((MODAL_DEFAULT_HEIGHT_VH / 100) * window.innerHeight)
  return Math.min(maxPx, Math.max(MODAL_MIN_HEIGHT_PX, defaultPx))
}

function getMaxHeightPx(): number {
  if (typeof window === 'undefined') return 800
  return Math.floor((MODAL_MAX_HEIGHT_VH / 100) * window.innerHeight)
}

const createNoteSchema = z.object({
  title: z.string().optional(),
  content: z.string().min(1, 'Content is required'),
})

type CreateNoteFormData = z.infer<typeof createNoteSchema>

interface NoteEditorDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  notebookId: string
  note?: { id: string; title: string | null; content: string | null }
}

export function NoteEditorDialog({ open, onOpenChange, notebookId, note }: NoteEditorDialogProps) {
  const { t } = useTranslation()
  const createNote = useCreateNote()
  const updateNote = useUpdateNote()
  const queryClient = useQueryClient()
  const isEditing = Boolean(note)

  // Ensure note ID has 'note:' prefix for API calls
  const noteIdWithPrefix = note?.id
    ? (note.id.includes(':') ? note.id : `note:${note.id}`)
    : ''

  const { data: fetchedNote, isLoading: noteLoading } = useNote(noteIdWithPrefix, { enabled: open && !!note?.id })
  const isSaving = isEditing ? updateNote.isPending : createNote.isPending
  const {
    handleSubmit,
    control,
    formState: { errors },
    reset,
    setValue,
  } = useForm<CreateNoteFormData>({
    resolver: zodResolver(createNoteSchema),
    defaultValues: {
      title: '',
      content: '',
    },
  })
  const watchTitle = useWatch({ control, name: 'title' })
  const [isEditorFullscreen, setIsEditorFullscreen] = useState(false)
  const [editorHeight, setEditorHeight] = useState(360)
  const editorContainerRef = useRef<HTMLDivElement>(null)
  const contentRef = useRef<HTMLDivElement>(null)
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 })
  const [modalHeightPx, setModalHeightPx] = useState(() =>
    typeof window !== 'undefined' ? getDefaultHeightPx() : MODAL_MIN_HEIGHT_PX
  )
  const dragRef = useRef({
    isDragging: false,
    startX: 0,
    startY: 0,
    startOffsetX: 0,
    startOffsetY: 0,
    currentX: 0,
    currentY: 0,
  })
  const resizeRef = useRef({
    isResizing: false,
    startY: 0,
    startHeight: 0,
    currentHeight: 0,
  })

  // Default modal size when opening; reset when closing
  useEffect(() => {
    if (open && !isEditorFullscreen) {
      setModalHeightPx(getDefaultHeightPx())
    }
  }, [open, isEditorFullscreen])

  // Measure editor container so the editor can fill available space
  useEffect(() => {
    if (!open || !editorContainerRef.current) return
    const el = editorContainerRef.current
    const ro = new ResizeObserver((entries) => {
      const { height } = entries[0]?.contentRect ?? {}
      if (typeof height === 'number' && height > 0) setEditorHeight(Math.max(200, Math.floor(height)))
    })
    ro.observe(el)
    return () => { ro.disconnect(); }
  }, [open])

  // Drag: use direct DOM updates for smooth movement (no re-renders during drag)
  const handleDragPointerDown = useCallback((e: React.PointerEvent) => {
    if ((e.target as HTMLElement).closest('button, input, [contenteditable="true"]')) return
    e.preventDefault()
    dragRef.current = {
      isDragging: true,
      startX: e.clientX,
      startY: e.clientY,
      startOffsetX: dragOffset.x,
      startOffsetY: dragOffset.y,
      currentX: dragOffset.x,
      currentY: dragOffset.y,
    }
    ;(e.target as HTMLElement).setPointerCapture(e.pointerId)
  }, [dragOffset.x, dragOffset.y])

  const handleResizePointerDown = useCallback((e: React.PointerEvent) => {
    e.preventDefault()
    e.stopPropagation()
    resizeRef.current = {
      isResizing: true,
      startY: e.clientY,
      startHeight: modalHeightPx,
      currentHeight: modalHeightPx,
    }
    ;(e.target as HTMLElement).setPointerCapture(e.pointerId)
  }, [modalHeightPx])

  useEffect(() => {
    if (!open) return
    const onMove = (e: PointerEvent) => {
      const el = contentRef.current
      if (dragRef.current.isDragging && el) {
        const x = dragRef.current.startOffsetX + e.clientX - dragRef.current.startX
        const y = dragRef.current.startOffsetY + e.clientY - dragRef.current.startY
        el.style.transform = `translate(calc(-50% + ${x}px), calc(-50% + ${y}px))`
        dragRef.current.currentX = x
        dragRef.current.currentY = y
      } else if (resizeRef.current.isResizing && el) {
        const deltaY = e.clientY - resizeRef.current.startY
        const maxPx = getMaxHeightPx()
        const h = Math.max(MODAL_MIN_HEIGHT_PX, Math.min(maxPx, resizeRef.current.startHeight + deltaY))
        el.style.height = `${h}px`
        resizeRef.current.currentHeight = h
      }
    }
    const onUp = () => {
      if (dragRef.current.isDragging) {
        setDragOffset({ x: dragRef.current.currentX, y: dragRef.current.currentY })
        dragRef.current.isDragging = false
      }
      if (resizeRef.current.isResizing) {
        setModalHeightPx(resizeRef.current.currentHeight)
        resizeRef.current.isResizing = false
      }
    }
    window.addEventListener('pointermove', onMove)
    window.addEventListener('pointerup', onUp)
    window.addEventListener('pointercancel', onUp)
    return () => {
      window.removeEventListener('pointermove', onMove)
      window.removeEventListener('pointerup', onUp)
      window.removeEventListener('pointercancel', onUp)
    }
  }, [open])

  // Reset position and size when modal closes
  useEffect(() => {
    if (!open) {
      setDragOffset({ x: 0, y: 0 })
      setModalHeightPx(getDefaultHeightPx())
    }
  }, [open])

  useEffect(() => {
    if (!open) {
      reset({ title: '', content: '' })
      return
    }

    const source = fetchedNote ?? note
    const title = source?.title ?? ''
    const content = source?.content ?? ''

    reset({ title, content })
  }, [open, note, fetchedNote, reset])

  useEffect(() => {
    if (!open) return

    const observer = new MutationObserver(() => {
      setIsEditorFullscreen(!!document.querySelector('.w-md-editor-fullscreen'))
    })
    observer.observe(document.body, { subtree: true, attributes: true, attributeFilter: ['class'] })
    return () => observer.disconnect()
  }, [open])

  const onSubmit = async (data: CreateNoteFormData) => {
    if (note) {
      await updateNote.mutateAsync({
        id: noteIdWithPrefix,
        data: {
          title: data.title || undefined,
          content: data.content,
        },
      })
      // Only invalidate notebook-specific queries if we have a notebookId
      if (notebookId) {
        queryClient.invalidateQueries({ queryKey: QUERY_KEYS.notes(notebookId) })
      }
    } else {
      // Creating a note requires a notebookId
      if (!notebookId) {
        console.error('Cannot create note without notebook_id')
        return
      }
      await createNote.mutateAsync({
        title: data.title || undefined,
        content: data.content,
        note_type: 'human',
        notebook_id: notebookId,
      })
    }
    reset()
    onOpenChange(false)
  }

  const handleClose = () => {
    reset()
    setIsEditorFullscreen(false)
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent
        ref={contentRef}
        className={cn(
          "sm:max-w-3xl w-full overflow-hidden p-0 flex flex-col",
          !isEditorFullscreen && "!top-1/2 !left-1/2",
          isEditorFullscreen && "!max-w-screen !max-h-screen border-none w-screen h-screen"
        )}
        style={!isEditorFullscreen ? {
          transform: `translate(calc(-50% + ${dragOffset.x}px), calc(-50% + ${dragOffset.y}px))`,
          height: modalHeightPx,
          minHeight: MODAL_MIN_HEIGHT_PX,
          maxHeight: '90vh',
        } : undefined}
      >
        <DialogTitle className="sr-only">
          {isEditing ? t.sources.editNote : t.sources.createNote}
        </DialogTitle>
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-1 min-h-0 flex-col">
          {isEditing && noteLoading ? (
            <div className="flex-1 flex items-center justify-center py-10">
              <span className="text-sm text-muted-foreground">{t.common.loading}</span>
            </div>
          ) : (
            <>
              <div
                className={cn(
                  "border-b px-6 py-4 flex items-center gap-2 select-none",
                  !isEditorFullscreen && "cursor-grab active:cursor-grabbing"
                )}
                data-drag-handle
                onPointerDown={!isEditorFullscreen ? handleDragPointerDown : undefined}
                role="presentation"
                aria-label="Drag to move dialog"
              >
                {!isEditorFullscreen && (
                  <GripHorizontal className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
                )}
                <InlineEdit
                  id="note-title"
                  name="title"
                  value={watchTitle ?? ''}
                  onSave={(value) => setValue('title', value || '')}
                  placeholder={t.sources.addTitle}
                  emptyText={t.sources.untitledNote}
                  className="text-xl font-semibold flex-1 min-w-0"
                  inputClassName="text-xl font-semibold"
                />
              </div>

              <div
                ref={editorContainerRef}
                className={cn(
                  "flex-1 min-h-0 overflow-y-auto flex flex-col",
                  !isEditorFullscreen && "px-6 py-4"
                )}
              >
                <Controller
                  control={control}
                  name="content"
                  render={({ field }) => (
                    <MarkdownEditor
                      key={note?.id ?? 'new'}
                      textareaId="note-content"
                      value={field.value}
                      onChange={field.onChange}
                      height={editorHeight}
                      placeholder={t.sources.writeNotePlaceholder}
                      className={cn(
                        "w-full flex-1 min-h-[200px] overflow-hidden [&_.w-md-editor]:!static [&_.w-md-editor]:!w-full [&_.w-md-editor]:!h-full [&_.w-md-editor-content]:overflow-y-auto",
                        !isEditorFullscreen && "rounded-md border"
                      )}
                    />
                  )}
                />
                {errors.content && (
                  <p className="text-sm text-red-600 mt-1">{errors.content.message}</p>
                )}
              </div>
            </>
          )}

          <div className="border-t px-6 py-4 flex justify-end gap-2 flex-shrink-0">
            <Button type="button" variant="outline" onClick={handleClose}>
              {t.common.cancel}
            </Button>
            <Button
              type="submit"
              disabled={isSaving || (isEditing && noteLoading)}
            >
              {isSaving
                ? isEditing ? `${t.common.saving}...` : `${t.common.creating}...`
                : isEditing
                  ? t.sources.saveNote
                  : t.sources.createNoteBtn}
            </Button>
          </div>

          {!isEditorFullscreen && (
            <div
              className="absolute bottom-0 left-0 right-0 h-3 cursor-ns-resize flex items-center justify-center group bg-transparent hover:bg-muted/30 transition-colors rounded-b-lg"
              onPointerDown={handleResizePointerDown}
              role="slider"
              aria-label="Resize dialog height"
              aria-valuemin={MODAL_MIN_HEIGHT_PX}
              aria-valuemax={getMaxHeightPx()}
              aria-valuenow={modalHeightPx}
            >
              <GripVertical className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
          )}
        </form>
      </DialogContent>
    </Dialog>
  )
}
