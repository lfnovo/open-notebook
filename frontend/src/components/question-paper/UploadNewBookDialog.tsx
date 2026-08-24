'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { questionPaperApi } from '@/lib/api/question-paper'
import { QUESTION_PAPER_KEYS } from '@/lib/hooks/use-question-paper'
import { useTranslation } from '@/lib/hooks/use-translation'
import type { LibraryBook } from '@/lib/types/question-paper'

export function suggestedDisplayName(bookName: string, year: string, grade: string) {
  const name = bookName.trim()
  const yr = year.trim()
  const gr = grade.trim()
  if (!name || !yr || !gr) return ''
  return `${name} ${yr} - Grade ${gr}`
}

interface UploadNewBookDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  defaultGrade?: string
  onUploaded: (book: LibraryBook) => void
}

export function UploadNewBookDialog({
  open,
  onOpenChange,
  defaultGrade = '',
  onUploaded,
}: UploadNewBookDialogProps) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [bookName, setBookName] = useState('')
  const [year, setYear] = useState('')
  const [grade, setGrade] = useState(defaultGrade)
  const [subject, setSubject] = useState('')
  const [edition, setEdition] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [displayTouched, setDisplayTouched] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)

  const suggestion = useMemo(
    () => suggestedDisplayName(bookName, year, grade),
    [bookName, year, grade],
  )

  useEffect(() => {
    if (open) setGrade((prev) => prev || defaultGrade)
  }, [open, defaultGrade])

  useEffect(() => {
    if (!displayTouched) setDisplayName(suggestion)
  }, [suggestion, displayTouched])

  const reset = () => {
    setBookName('')
    setYear('')
    setGrade(defaultGrade)
    setSubject('')
    setEdition('')
    setDisplayName('')
    setDisplayTouched(false)
    setFile(null)
    if (fileRef.current) fileRef.current.value = ''
  }

  const canSubmit = !!file && !!bookName.trim() && !!year.trim() && !!grade.trim() && !uploading

  const handleUpload = async () => {
    if (!file || !canSubmit) return
    setUploading(true)
    try {
      const book = await questionPaperApi.uploadBook({
        file,
        book_name: bookName.trim(),
        year: year.trim(),
        grade: grade.trim(),
        subject: subject.trim(),
        edition: edition.trim(),
        display_name: displayName.trim() || suggestion,
      })
      await queryClient.invalidateQueries({ queryKey: QUESTION_PAPER_KEYS.books })
      toast.success(t.questionPaper.bookSaved)
      onUploaded(book)
      reset()
      onOpenChange(false)
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(detail || t.questionPaper.bookUploadFailed)
    } finally {
      setUploading(false)
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) reset()
        onOpenChange(next)
      }}
    >
      <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{t.questionPaper.uploadNewBookTitle}</DialogTitle>
          <DialogDescription>{t.questionPaper.uploadNewBookDesc}</DialogDescription>
        </DialogHeader>
        <div className="space-y-3 text-sm">
          <div className="space-y-1.5">
            <Label htmlFor="lib-book-name">{t.questionPaper.bookName}</Label>
            <Input
              id="lib-book-name"
              value={bookName}
              onChange={(e) => setBookName(e.target.value)}
              placeholder={t.questionPaper.bookNamePlaceholder}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="lib-year">{t.questionPaper.year}</Label>
              <Input
                id="lib-year"
                value={year}
                onChange={(e) => setYear(e.target.value)}
                placeholder={t.questionPaper.yearPlaceholder}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="lib-grade">{t.questionPaper.grade}</Label>
              <Input
                id="lib-grade"
                value={grade}
                onChange={(e) => setGrade(e.target.value)}
                placeholder={t.questionPaper.gradePlaceholder}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="lib-subject">{t.questionPaper.subject}</Label>
              <Input
                id="lib-subject"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder={t.questionPaper.subjectPlaceholder}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="lib-edition">{t.questionPaper.editionOptional}</Label>
              <Input
                id="lib-edition"
                value={edition}
                onChange={(e) => setEdition(e.target.value)}
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="lib-display">{t.questionPaper.displayName}</Label>
            <Input
              id="lib-display"
              value={displayName}
              onChange={(e) => {
                setDisplayTouched(true)
                setDisplayName(e.target.value)
              }}
              placeholder={t.questionPaper.displayNameHint}
            />
            <p className="text-xs text-muted-foreground">{t.questionPaper.displayNameHint}</p>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="lib-file">{t.questionPaper.bookFile}</Label>
            <Input
              id="lib-file"
              ref={fileRef}
              type="file"
              accept=".pdf,.txt,.epub,.docx,.doc,.md"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={uploading}>
              {t.common.cancel}
            </Button>
            <Button type="button" onClick={handleUpload} disabled={!canSubmit}>
              {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : t.questionPaper.saveBook}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
