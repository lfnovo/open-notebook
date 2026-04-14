'use client'

import { useRef, useState } from 'react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Loader2, BookOpen, Upload, X, CheckSquare, Square, Check } from 'lucide-react'
import { toast } from 'sonner'
import { questionPaperApi } from '@/lib/api/question-paper'
import type { BookChapter, BookUploadResponse } from '@/lib/types/question-paper'

interface BookUploaderProps {
  onBookReady: (bookId: string, selectedChapters: number[] | null, bookTitle: string, chapterTitles: string[]) => void
  onClear: () => void
}

function formatSize(chars: number) {
  if (chars < 1000) return `${chars} chars`
  if (chars < 1_000_000) return `~${Math.round(chars / 1000)}k chars`
  return `~${(chars / 1_000_000).toFixed(1)}M chars`
}

export function BookUploader({ onBookReady, onClear }: BookUploaderProps) {
  const { t } = useTranslation()
  const inputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [book, setBook] = useState<BookUploadResponse | null>(null)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [allSelected, setAllSelected] = useState(true)

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const result = await questionPaperApi.uploadBook(file)
      setBook(result)
      // Default: all chapters selected
      setAllSelected(true)
      setSelected(new Set(result.chapters.map((c) => c.index)))
      onBookReady(result.book_id, null, result.title, result.chapters.map((c) => c.title))
      toast.success(t.questionPaper.bookUploaded.replace('{count}', String(result.chapters.length)))
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || t.questionPaper.bookUploadFailed)
    } finally {
      setUploading(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  const toggleChapter = (index: number) => {
    if (!book) return
    const next = new Set(selected)
    if (next.has(index)) {
      next.delete(index)
    } else {
      next.add(index)
    }
    const isAll = next.size === book.chapters.length
    setSelected(next)
    setAllSelected(isAll)
    onBookReady(book.book_id, isAll ? null : Array.from(next).sort((a, b) => a - b), book.title, book.chapters.filter(c => next.has(c.index)).map(c => c.title))
  }

  const toggleAll = () => {
    if (!book) return
    if (allSelected) {
      // Deselect all
      setSelected(new Set())
      setAllSelected(false)
      onBookReady(book.book_id, [], book.title, [])
    } else {
      // Select all
      const all = new Set(book.chapters.map((c) => c.index))
      setSelected(all)
      setAllSelected(true)
      onBookReady(book.book_id, null, book.title, book.chapters.map(c => c.title))
    }
  }

  const handleClear = async () => {
    if (book) {
      try {
        await questionPaperApi.deleteBook(book.book_id)
      } catch {}
    }
    setBook(null)
    setSelected(new Set())
    setAllSelected(true)
    onClear()
  }

  if (!book) {
    return (
      <div>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.txt,.epub,.docx,.doc,.md"
          className="hidden"
          onChange={handleFileChange}
        />
        <Button
          type="button"
          variant="outline"
          className="w-full h-20 border-dashed flex-col gap-1"
          onClick={() => inputRef.current?.click()}
          disabled={uploading}
        >
          {uploading ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              <span className="text-sm">{t.questionPaper.bookExtracting}</span>
            </>
          ) : (
            <>
              <Upload className="h-5 w-5 text-muted-foreground" />
              <span className="text-sm">{t.questionPaper.bookUploadPrompt}</span>
              <span className="text-xs text-muted-foreground">PDF, EPUB, DOCX, TXT</span>
            </>
          )}
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-3 rounded-lg border p-3">
      {/* Book header */}
      <div className="flex items-start gap-2">
        <BookOpen className="h-4 w-4 text-primary mt-0.5 shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">{book.title}</p>
          <p className="text-xs text-muted-foreground">
            {book.chapters.length} {t.questionPaper.chapters} · {formatSize(book.total_chars)}
          </p>
        </div>
        <Button type="button" variant="ghost" size="icon" className="h-7 w-7 shrink-0" onClick={handleClear}>
          <X className="h-3 w-3" />
        </Button>
      </div>

      {/* Chapter selector */}
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
          {book.chapters.map((chapter) => (
            <div
              key={chapter.index}
              className="flex items-start gap-2 rounded p-1.5 hover:bg-muted/50 cursor-pointer"
              onClick={() => toggleChapter(chapter.index)}
            >
              <div className="mt-0.5 shrink-0 h-4 w-4 rounded border border-primary flex items-center justify-center bg-background">
                {selected.has(chapter.index) && <Check className="h-3 w-3 text-primary" />}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium truncate">{chapter.title}</p>
                {chapter.preview && (
                  <p className="text-xs text-muted-foreground line-clamp-1 mt-0.5">
                    {chapter.preview}
                  </p>
                )}
              </div>
              <Badge variant="outline" className="text-xs shrink-0">
                {formatSize(chapter.char_count)}
              </Badge>
            </div>
          ))}
        </div>
      </div>

      {/* Selection summary */}
      <p className="text-xs text-muted-foreground">
        {selected.size === 0
          ? t.questionPaper.noChaptersSelected
          : allSelected
            ? t.questionPaper.allChaptersSelected
            : t.questionPaper.chaptersSelected.replace('{count}', String(selected.size)).replace('{total}', String(book.chapters.length))}
      </p>
    </div>
  )
}
