'use client'

import { useEffect, useMemo, useState } from 'react'
import { BookOpen, Check, CheckSquare, Loader2, Pencil, Plus, Square, X } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { questionPaperApi } from '@/lib/api/question-paper'
import { useBooks } from '@/lib/hooks/use-question-paper'
import { useTranslation } from '@/lib/hooks/use-translation'
import type { BookChapter, LibraryBook } from '@/lib/types/question-paper'
import { UploadNewBookDialog } from './UploadNewBookDialog'
import { EditBookDetailsDialog } from './EditBookDetailsDialog'

const MISSING_YEAR = '__missing_year__'

export function bookRecordId(book: LibraryBook) {
  return book.book_id || (book as { book_id?: string }).book_id || ''
}

export function bookMissingFields(book: LibraryBook) {
  return book.missing_fields || (book as { missing_fields?: string[] }).missing_fields || []
}

export function gradesMatch(a?: string | null, b?: string | null) {
  if (a == null || b == null || !String(a).trim() || !String(b).trim()) return false
  const na = String(a).match(/\d+/)
  const nb = String(b).match(/\d+/)
  if (na && nb) return na[0] === nb[0]
  return String(a).trim().toLowerCase() === String(b).trim().toLowerCase()
}

function chapterIndex(chapter: BookChapter) {
  const raw = chapter as BookChapter & { index?: number; preview?: string; char_count?: number }
  return typeof raw.index === 'number' ? raw.index : Number(raw.index ?? 0)
}

function formatSize(chars: number) {
  if (chars < 1000) return `${chars} chars`
  if (chars < 1_000_000) return `~${Math.round(chars / 1000)}k chars`
  return `~${(chars / 1_000_000).toFixed(1)}M chars`
}

interface BookUploaderProps {
  grade: string
  onBookReady: (
    bookId: string,
    selectedChapters: number[] | null,
    bookTitle: string,
    chapterTitles: string[],
    detectedGrade?: string | null,
  ) => void
  onClear: () => void
}

export function BookUploader({ grade, onBookReady, onClear }: BookUploaderProps) {
  const { t } = useTranslation()
  const { data: books = [], isLoading } = useBooks()
  const [year, setYear] = useState('')
  const [bookId, setBookId] = useState('')
  const [detail, setDetail] = useState<LibraryBook | null>(null)
  const [loadingChapters, setLoadingChapters] = useState(false)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [allSelected, setAllSelected] = useState(true)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [editOpen, setEditOpen] = useState(false)

  const booksForGrade = useMemo(
    () => (grade.trim() ? books.filter((book) => gradesMatch(book.grade, grade)) : []),
    [books, grade],
  )

  const yearOptions = useMemo(() => {
    const years = Array.from(
      new Set(booksForGrade.map((book) => (book.year || '').trim()).filter(Boolean)),
    ).sort((a, b) => a.localeCompare(b, undefined, { numeric: true }))
    const hasMissing = booksForGrade.some((book) => !String(book.year || '').trim())
    return { years, hasMissing }
  }, [booksForGrade])

  const booksForYear = useMemo(() => {
    if (!year) return []
    if (year === MISSING_YEAR) {
      return booksForGrade.filter((book) => !String(book.year || '').trim())
    }
    return booksForGrade.filter((book) => String(book.year || '').trim() === year)
  }, [booksForGrade, year])

  useEffect(() => {
    setYear('')
    setBookId('')
    setDetail(null)
    setSelected(new Set())
    setAllSelected(true)
    onClear()
    // Reset when the generate-form grade changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [grade])

  useEffect(() => {
    if (!grade.trim()) return
    if (yearOptions.years.length === 1 && !yearOptions.hasMissing) {
      setYear(yearOptions.years[0])
      return
    }
    if (yearOptions.years.length === 0 && yearOptions.hasMissing) {
      setYear(MISSING_YEAR)
    }
  }, [grade, yearOptions.years, yearOptions.hasMissing])

  useEffect(() => {
    if (!year) {
      setBookId('')
      return
    }
    if (booksForYear.length === 1) {
      setBookId(bookRecordId(booksForYear[0]))
      return
    }
    if (bookId && !booksForYear.some((book) => bookRecordId(book) === bookId)) {
      setBookId('')
      setDetail(null)
    }
  }, [year, booksForYear, bookId])

  useEffect(() => {
    if (!bookId) {
      setDetail(null)
      return
    }
    let cancelled = false
    setLoadingChapters(true)
    questionPaperApi
      .getBook(bookId)
      .then((book) => {
        if (cancelled) return
        setDetail(book)
        const chapters = book.chapters || []
        const all = new Set(chapters.map(chapterIndex))
        setSelected(all)
        setAllSelected(true)
        onBookReady(
          bookRecordId(book),
          null,
          book.display_name || book.title || bookRecordId(book),
          chapters.map((chapter) => chapter.title),
          book.detected_grade ?? book.grade,
        )
      })
      .finally(() => {
        if (!cancelled) setLoadingChapters(false)
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bookId])

  const notifySelection = (
    book: LibraryBook,
    next: Set<number>,
    isAll: boolean,
  ) => {
    const chapters = book.chapters || []
    onBookReady(
      bookRecordId(book),
      isAll ? null : Array.from(next).sort((a, b) => a - b),
      book.display_name || book.title || bookRecordId(book),
      chapters.filter((chapter) => next.has(chapterIndex(chapter))).map((chapter) => chapter.title),
      book.detected_grade ?? book.grade,
    )
  }

  const toggleChapter = (index: number) => {
    if (!detail?.chapters) return
    const next = new Set(selected)
    if (next.has(index)) next.delete(index)
    else next.add(index)
    const isAll = next.size === detail.chapters.length
    setSelected(next)
    setAllSelected(isAll)
    notifySelection(detail, next, isAll)
  }

  const toggleAll = () => {
    if (!detail?.chapters) return
    if (allSelected) {
      setSelected(new Set())
      setAllSelected(false)
      notifySelection(detail, new Set(), false)
    } else {
      const all = new Set(detail.chapters.map(chapterIndex))
      setSelected(all)
      setAllSelected(true)
      notifySelection(detail, all, true)
    }
  }

  const handleClear = () => {
    setYear('')
    setBookId('')
    setDetail(null)
    setSelected(new Set())
    setAllSelected(true)
    onClear()
  }

  const yearDisabled = !grade.trim()
  const bookDisabled = !year || booksForYear.length === 0
  const selectedSummary = booksForYear.find((book) => bookRecordId(book) === bookId)

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-muted-foreground">{t.questionPaper.libraryHint}</p>
        <div className="flex items-center gap-2">
          {selectedSummary && (
            <Button type="button" variant="outline" size="sm" onClick={() => setEditOpen(true)}>
              <Pencil className="h-4 w-4 mr-1" />
              {t.questionPaper.editBookDetails}
            </Button>
          )}
          <Button type="button" variant="outline" size="sm" onClick={() => setUploadOpen(true)}>
            <Plus className="h-4 w-4 mr-1" />
            {t.questionPaper.uploadNewBook}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label>{t.questionPaper.year}</Label>
          <Select
            value={year || undefined}
            disabled={yearDisabled}
            onValueChange={(value) => {
              setYear(value)
              setBookId('')
              setDetail(null)
            }}
          >
            <SelectTrigger>
              <SelectValue placeholder={yearDisabled ? t.questionPaper.selectGradeFirst : t.questionPaper.selectYear} />
            </SelectTrigger>
            <SelectContent>
              {yearOptions.years.map((value) => (
                <SelectItem key={value} value={value}>{value}</SelectItem>
              ))}
              {yearOptions.hasMissing && (
                <SelectItem value={MISSING_YEAR}>{t.questionPaper.yearNotSet}</SelectItem>
              )}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label>{t.questionPaper.storedBook}</Label>
          <Select
            value={bookId || undefined}
            disabled={bookDisabled}
            onValueChange={setBookId}
          >
            <SelectTrigger>
              <SelectValue
                placeholder={
                  booksForYear.length > 1
                    ? t.questionPaper.selectBookRequired
                    : t.questionPaper.selectBook
                }
              />
            </SelectTrigger>
            <SelectContent>
              {booksForYear.map((book) => {
                const incomplete = bookMissingFields(book).length > 0
                return (
                  <SelectItem key={bookRecordId(book)} value={bookRecordId(book)}>
                    {book.display_name}
                    {incomplete ? ` — ${t.questionPaper.missingBookDetails}` : ''}
                  </SelectItem>
                )
              })}
            </SelectContent>
          </Select>
        </div>
      </div>

      {isLoading && (
        <p className="text-xs text-muted-foreground flex items-center gap-2">
          <Loader2 className="h-3 w-3 animate-spin" />
          {t.questionPaper.loadingBooks}
        </p>
      )}

      {grade.trim() && !isLoading && booksForGrade.length === 0 && (
        <p className="text-xs text-muted-foreground">{t.questionPaper.noBooksForGrade}</p>
      )}

      {selectedSummary && bookMissingFields(selectedSummary).length ? (
        <p className="text-xs rounded-md border border-amber-300 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/20 px-2 py-1.5 text-amber-800 dark:text-amber-200">
          {t.questionPaper.missingBookDetails}
        </p>
      ) : null}

      {loadingChapters && (
        <p className="text-xs text-muted-foreground flex items-center gap-2">
          <Loader2 className="h-3 w-3 animate-spin" />
          {t.questionPaper.loadingChapters}
        </p>
      )}

      {detail?.chapters && detail.chapters.length > 0 && (
        <div className="space-y-3 rounded-lg border p-3">
          <div className="flex items-start gap-2">
            <BookOpen className="h-4 w-4 text-primary mt-0.5 shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{detail.display_name}</p>
              <p className="text-xs text-muted-foreground">
                {detail.chapters.length} {t.questionPaper.chapters}
                {detail.total_chars || detail.total_chars
                  ? ` · ${formatSize(detail.total_chars || detail.total_chars || 0)}`
                  : ''}
              </p>
            </div>
            <Button type="button" variant="ghost" size="icon" className="h-7 w-7 shrink-0" onClick={handleClear}>
              <X className="h-3 w-3" />
            </Button>
          </div>

          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium text-muted-foreground">{t.questionPaper.selectChapters}</p>
              <Button type="button" variant="ghost" size="sm" className="h-6 text-xs px-2" onClick={toggleAll}>
                {allSelected ? (
                  <><CheckSquare className="h-3 w-3 mr-1" />{t.questionPaper.deselectAll}</>
                ) : (
                  <><Square className="h-3 w-3 mr-1" />{t.questionPaper.selectAll}</>
                )}
              </Button>
            </div>
            <div className="max-h-48 overflow-y-auto space-y-1 pr-1">
              {detail.chapters.map((chapter) => {
                const index = chapterIndex(chapter)
                const preview = chapter.preview || chapter.preview
                const chars = chapter.char_count || chapter.char_count || 0
                return (
                  <div
                    key={index}
                    className="flex items-start gap-2 rounded p-1.5 hover:bg-muted/50 cursor-pointer"
                    onClick={() => toggleChapter(index)}
                  >
                    <div className="mt-0.5 shrink-0 h-4 w-4 rounded border border-primary flex items-center justify-center bg-background">
                      {selected.has(index) && <Check className="h-3 w-3 text-primary" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium truncate">{chapter.title}</p>
                      {preview ? (
                        <p className="text-xs text-muted-foreground line-clamp-1 mt-0.5">{preview}</p>
                      ) : null}
                    </div>
                    <Badge variant="outline" className="text-xs shrink-0">
                      {formatSize(chars)}
                    </Badge>
                  </div>
                )
              })}
            </div>
          </div>
          <p className="text-xs text-muted-foreground">
            {selected.size === 0
              ? t.questionPaper.noChaptersSelected
              : allSelected
                ? t.questionPaper.allChaptersSelected
                : t.questionPaper.chaptersSelected
                    .replace('{count}', String(selected.size))
                    .replace('{total}', String(detail.chapters.length))}
          </p>
        </div>
      )}

      <UploadNewBookDialog
        open={uploadOpen}
        onOpenChange={setUploadOpen}
        defaultGrade={grade}
        onUploaded={(book) => {
          setYear(book.year || MISSING_YEAR)
          setBookId(bookRecordId(book))
        }}
      />
      <EditBookDetailsDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        book={selectedSummary || detail}
        onSaved={(updated) => {
          if (updated.year) setYear(updated.year)
          setBookId(bookRecordId(updated))
        }}
      />
    </div>
  )
}
