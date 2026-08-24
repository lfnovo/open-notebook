'use client'

import { useEffect, useMemo, useState } from 'react'
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
import { suggestedDisplayName } from './UploadNewBookDialog'

interface EditBookDetailsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  book: LibraryBook | null
  onSaved: (book: LibraryBook) => void
}

export function EditBookDetailsDialog({
  open,
  onOpenChange,
  book,
  onSaved,
}: EditBookDetailsDialogProps) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [bookName, setBookName] = useState('')
  const [year, setYear] = useState('')
  const [grade, setGrade] = useState('')
  const [subject, setSubject] = useState('')
  const [edition, setEdition] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [displayTouched, setDisplayTouched] = useState(false)
  const [saving, setSaving] = useState(false)

  const suggestion = useMemo(
    () => suggestedDisplayName(bookName, year, grade),
    [bookName, year, grade],
  )

  useEffect(() => {
    if (!open || !book) return
    const name = (book.book_name || '').trim()
    const yr = (book.year || '').trim()
    const gr = (book.grade || '').trim()
    setBookName(name)
    setYear(yr)
    setGrade(gr)
    setSubject((book.subject || '').trim())
    setEdition((book.edition || '').trim())
    const storedDisplay = (book.display_name || '').trim()
    const complete = Boolean(name && yr && gr)
    const matchesSuggestion = complete && storedDisplay === suggestedDisplayName(name, yr, gr)
    // Do not treat a leftover filename/title as a real display name when details are missing.
    if (complete && storedDisplay && !matchesSuggestion) {
      setDisplayName(storedDisplay)
      setDisplayTouched(true)
    } else {
      setDisplayName(complete ? storedDisplay || suggestedDisplayName(name, yr, gr) : '')
      setDisplayTouched(false)
    }
  }, [open, book])

  useEffect(() => {
    if (!displayTouched) setDisplayName(suggestion)
  }, [suggestion, displayTouched])

  const canSave = !!bookName.trim() && !!year.trim() && !!grade.trim() && !saving

  const handleSave = async () => {
    if (!book || !canSave) return
    setSaving(true)
    try {
      const bookId = book.book_id || (book as { book_id?: string }).book_id || ''
      const updated = await questionPaperApi.updateBook(bookId, {
        book_name: bookName.trim(),
        year: year.trim(),
        grade: grade.trim(),
        subject: subject.trim(),
        edition: edition.trim(),
        display_name: displayName.trim() || suggestion,
      })
      await queryClient.invalidateQueries({ queryKey: QUESTION_PAPER_KEYS.books })
      toast.success(t.questionPaper.bookDetailsSaved)
      onSaved(updated)
      onOpenChange(false)
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(detail || t.questionPaper.bookDetailsSaveFailed)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{t.questionPaper.editBookDetailsTitle}</DialogTitle>
          <DialogDescription>{t.questionPaper.editBookDetailsDesc}</DialogDescription>
        </DialogHeader>
        <div className="space-y-3 text-sm">
          <div className="space-y-1.5">
            <Label htmlFor="edit-book-name">{t.questionPaper.bookName}</Label>
            <Input
              id="edit-book-name"
              value={bookName}
              onChange={(e) => setBookName(e.target.value)}
              placeholder={t.questionPaper.bookNamePlaceholder}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="edit-year">{t.questionPaper.year}</Label>
              <Input
                id="edit-year"
                value={year}
                onChange={(e) => setYear(e.target.value)}
                placeholder={t.questionPaper.yearPlaceholder}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="edit-grade">{t.questionPaper.grade}</Label>
              <Input
                id="edit-grade"
                value={grade}
                onChange={(e) => setGrade(e.target.value)}
                placeholder={t.questionPaper.gradePlaceholder}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="edit-subject">{t.questionPaper.subject}</Label>
              <Input
                id="edit-subject"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder={t.questionPaper.subjectPlaceholder}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="edit-edition">{t.questionPaper.editionOptional}</Label>
              <Input
                id="edit-edition"
                value={edition}
                onChange={(e) => setEdition(e.target.value)}
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="edit-display">{t.questionPaper.displayName}</Label>
            <Input
              id="edit-display"
              value={displayName}
              onChange={(e) => {
                setDisplayTouched(true)
                setDisplayName(e.target.value)
              }}
              placeholder={t.questionPaper.displayNameHint}
            />
            <p className="text-xs text-muted-foreground">{t.questionPaper.displayNameHint}</p>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
              {t.common.cancel}
            </Button>
            <Button type="button" onClick={handleSave} disabled={!canSave}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : t.questionPaper.saveDetails}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
