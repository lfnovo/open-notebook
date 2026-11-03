'use client'

import { useEffect, useState } from 'react'
import { Download } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { MarkdownRenderer } from '@/components/ui/markdown-renderer'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { notesApi } from '@/lib/api/notes'
import { useNote } from '@/lib/hooks/use-notes'
import { useTranslation } from '@/lib/hooks/use-translation'
import type { NoteResponse } from '@/lib/types/api'
import { formatFileSize, noteFileKind, saveNoteFile } from '@/lib/utils/note-files'

interface NoteFileViewerProps {
  note: NoteResponse | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

/**
 * Pop-up viewer for a note created from a file. PDFs and HTML show the original
 * (fetched with auth into a blob so the request carries the token); DOCX, text
 * and Markdown show the text extracted from the file. HTML is rendered in a
 * fully sandboxed iframe, so scripts in the file can never run.
 */
export function NoteFileViewer({ note, open, onOpenChange }: NoteFileViewerProps) {
  const { t } = useTranslation()
  const attachment = note?.attachment ?? null
  const kind = attachment ? noteFileKind(attachment.type) : null
  const showsOriginal = kind === 'pdf' || kind === 'html'

  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)
  const noteId = note?.id
  const attachmentType = attachment?.type

  useEffect(() => {
    if (!open || !noteId || !attachmentType || !showsOriginal) return
    let cancelled = false
    let url: string | null = null
    setBlobUrl(null)
    setFailed(false)
    notesApi
      .fetchFile(noteId)
      .then((data) => {
        if (cancelled) return
        // Force the type we expect rather than trusting the response.
        url = URL.createObjectURL(new Blob([data], { type: attachmentType }))
        setBlobUrl(url)
      })
      .catch(() => {
        if (!cancelled) setFailed(true)
      })
    return () => {
      cancelled = true
      if (url) URL.revokeObjectURL(url)
    }
  }, [open, noteId, attachmentType, showsOriginal])

  const { data: fullNote, isError: textFailed } = useNote(noteId, {
    enabled: open && !!attachment && !showsOriginal,
  })

  const handleDownload = async () => {
    if (!note || !attachment) return
    try {
      await saveNoteFile(note.id, attachment.name, attachment.type)
    } catch {
      setFailed(true)
    }
  }

  if (!note || !attachment) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex h-[85vh] max-w-5xl flex-col gap-3">
        <DialogHeader className="pr-8">
          <div className="flex items-center justify-between gap-3">
            <DialogTitle className="truncate">{attachment.name}</DialogTitle>
            <Button variant="outline" size="sm" onClick={handleDownload}>
              <Download className="mr-2 h-4 w-4" />
              {t('noteFiles.download')}
            </Button>
          </div>
          <DialogDescription>
            {t('noteFiles.meta', { size: formatFileSize(attachment.size) })}
          </DialogDescription>
        </DialogHeader>

        <div className="min-h-0 flex-1 overflow-hidden rounded-md border bg-card">
          {failed || textFailed ? (
            <p role="alert" className="p-6 text-sm text-destructive">
              {t('noteFiles.loadFailed')}
            </p>
          ) : showsOriginal ? (
            blobUrl ? (
              <iframe
                src={blobUrl}
                title={attachment.name}
                // Empty sandbox: no scripts, no same-origin access. Not applied to PDFs
                // because browsers refuse to show their built-in PDF viewer in a sandbox
                // (a PDF cannot run page scripts in our origin).
                {...(kind === 'html' ? { sandbox: '' } : {})}
                className="h-full w-full bg-white"
              />
            ) : (
              <div className="flex h-full items-center justify-center">
                <LoadingSpinner />
              </div>
            )
          ) : fullNote ? (
            <div className="h-full overflow-y-auto p-6">
              <div className="prose prose-sm dark:prose-invert max-w-none break-words">
                <MarkdownRenderer>{fullNote.content ?? ''}</MarkdownRenderer>
              </div>
            </div>
          ) : (
            <div className="flex h-full items-center justify-center">
              <LoadingSpinner />
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
