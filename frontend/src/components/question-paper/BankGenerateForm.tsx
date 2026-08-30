'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { BankBatchProgressPanel } from '@/components/question-paper/BankBatchProgressPanel'
import {
  BANK_FIELD_CONTROL_CLASS,
  BANK_FIELD_GRID_CLASS,
  BankFormField,
  bankFieldLabelId,
} from '@/components/question-paper/BankFormField'
import { bookRecordId, gradesMatch } from '@/components/question-paper/BookUploader'
import { questionPaperApi } from '@/lib/api/question-paper'
import {
  useBankBatchStatus,
  useBooks,
  useGenerateBankBatch,
} from '@/lib/hooks/use-question-paper'
import { useTranslation } from '@/lib/hooks/use-translation'
import {
  BANK_BATCH_DIFFICULTIES,
  apiErrorDetail,
  bankBatchCanSubmit,
  bankBatchCountError,
  buildBankBatchPayload,
  chapterNumberForApi,
  isBankBatchActive,
  isBankBatchTerminal,
  parseNonNegInt,
  resolveBookSubject,
} from '@/lib/question-paper-bank-batch'
import type { BankBatchDifficulty, LibraryBook } from '@/lib/types/question-paper'

const MISSING_YEAR = '__missing_year__'

function uniqueSorted(values: Array<string | number | null | undefined>): string[] {
  return Array.from(
    new Set(
      values
        .map((value) => (value == null ? '' : String(value).trim()))
        .filter(Boolean),
    ),
  ).sort((a, b) => a.localeCompare(b, undefined, { numeric: true }))
}

export function BankGenerateForm() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const { data: books = [], isLoading: booksLoading } = useBooks()
  const { mutate: generateBatch, isPending: isSubmitting } = useGenerateBankBatch()
  const toastedKey = useRef<string | null>(null)

  const [grade, setGrade] = useState('')
  const [year, setYear] = useState('')
  const [bookId, setBookId] = useState('')
  const [detail, setDetail] = useState<LibraryBook | null>(null)
  const [loadingChapters, setLoadingChapters] = useState(false)
  const [chapter, setChapter] = useState('')
  const [difficulty, setDifficulty] = useState('')
  const [totalQuestions, setTotalQuestions] = useState(0)
  const [singleCorrect, setSingleCorrect] = useState(0)
  const [multipleCorrect, setMultipleCorrect] = useState(0)
  const [pendingBatchId, setPendingBatchId] = useState<string | null>(null)
  const [startedAtMs, setStartedAtMs] = useState<number | null>(null)

  const { data: batchStatus } = useBankBatchStatus(pendingBatchId)
  const isRunning = isBankBatchActive(batchStatus?.status) || (isSubmitting && !batchStatus)
  const isBusy = isSubmitting || isRunning

  const grades = useMemo(
    () => uniqueSorted(books.map((book) => book.grade)),
    [books],
  )

  const booksForGrade = useMemo(
    () => (grade.trim() ? books.filter((book) => gradesMatch(book.grade, grade)) : []),
    [books, grade],
  )

  const yearOptions = useMemo(() => {
    const years = uniqueSorted(booksForGrade.map((book) => book.year))
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
    setChapter('')
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
      setChapter('')
    }
  }, [year, booksForYear, bookId])

  useEffect(() => {
    if (!bookId) {
      setDetail(null)
      setChapter('')
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
        if (chapters.length === 1) {
          setChapter(String(chapterNumberForApi(0)))
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setDetail(null)
        toast.error(apiErrorDetail(err, t.questionPaper.bankGenerateFailed))
      })
      .finally(() => {
        if (!cancelled) setLoadingChapters(false)
      })
    return () => {
      cancelled = true
    }
  }, [bookId, t.questionPaper.bankGenerateFailed])

  useEffect(() => {
    if (!pendingBatchId || !batchStatus || !isBankBatchTerminal(batchStatus.status)) return
    const key = `${pendingBatchId}:${batchStatus.status}`
    if (toastedKey.current === key) return
    toastedKey.current = key
    queryClient.invalidateQueries({ queryKey: ['question-bank'] })
    if (batchStatus.status === 'failed') {
      toast.error(batchStatus.error_message || t.questionPaper.bankGenerateFailed)
      return
    }
    const template = batchStatus.status === 'completed_partial'
      ? t.questionPaper.bankGeneratePartial
      : t.questionPaper.bankGenerateSuccess
    toast.success(
      template
        .replace('{accepted}', String(batchStatus.accepted ?? 0))
        .replace('{requested}', String(batchStatus.requested ?? 0)),
    )
  }, [
    batchStatus,
    pendingBatchId,
    queryClient,
    t.questionPaper.bankGenerateFailed,
    t.questionPaper.bankGeneratePartial,
    t.questionPaper.bankGenerateSuccess,
  ])

  const chapters = detail?.chapters || []
  const selectedBook = booksForYear.find((book) => bookRecordId(book) === bookId) || detail
  const subject = selectedBook ? resolveBookSubject(selectedBook, grade) : ''
  const countError = bankBatchCountError(totalQuestions, singleCorrect, multipleCorrect)
  const chapterNumber = parseInt(chapter, 10)
  const canSubmit = bankBatchCanSubmit({
    bookId,
    grade,
    subject,
    chapter: Number.isInteger(chapterNumber) ? chapterNumber : 0,
    difficulty: difficulty as BankBatchDifficulty,
    totalQuestions,
    singleCorrect,
    multipleCorrect,
    isLoading: isBusy,
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return
    try {
      const payload = buildBankBatchPayload({
        bookId,
        grade,
        subject,
        chapter: chapterNumber,
        difficulty: difficulty as BankBatchDifficulty,
        totalQuestions,
        singleCorrect,
        multipleCorrect,
      })
      generateBatch(payload, {
        onSuccess: (response) => {
          toastedKey.current = null
          setStartedAtMs(Date.now())
          toast.success(t.questionPaper.bankGenerateStarted)
          setPendingBatchId(response.batch_id)
        },
        onError: (err: unknown) => {
          toast.error(apiErrorDetail(err, t.questionPaper.bankGenerateFailed))
        },
      })
    } catch (err: unknown) {
      toast.error(apiErrorDetail(err, t.questionPaper.bankGenerateFailed))
    }
  }

  const yearDisabled = !grade.trim() || isBusy
  const bookDisabled = !year || booksForYear.length === 0 || isBusy
  const chapterDisabled = !bookId || loadingChapters || isBusy

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t.questionPaper.bankGenerateTitle}</CardTitle>
        <CardDescription>{t.questionPaper.bankGenerateDesc}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <p className="text-xs text-muted-foreground">{t.questionPaper.bankGenerateHint}</p>

          <div className={BANK_FIELD_GRID_CLASS} data-testid="bank-generate-row-1">
            <BankFormField id="bank-gen-grade" label={t.questionPaper.grade}>
              <Select
                value={grade || undefined}
                disabled={isBusy}
                onValueChange={(value) => {
                  setGrade(value)
                  setDifficulty('')
                }}
              >
                <SelectTrigger
                  id="bank-gen-grade"
                  aria-labelledby={bankFieldLabelId('bank-gen-grade')}
                  className={BANK_FIELD_CONTROL_CLASS}
                >
                  <SelectValue placeholder={t.questionPaper.bankSelectGrade} />
                </SelectTrigger>
                <SelectContent>
                  {grades.map((value) => (
                    <SelectItem key={value} value={value}>{value}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </BankFormField>

            <BankFormField id="bank-gen-year" label={t.questionPaper.year}>
              <Select
                value={year || undefined}
                disabled={yearDisabled}
                onValueChange={(value) => {
                  setYear(value)
                  setBookId('')
                  setDetail(null)
                  setChapter('')
                }}
              >
                <SelectTrigger
                  id="bank-gen-year"
                  aria-labelledby={bankFieldLabelId('bank-gen-year')}
                  className={BANK_FIELD_CONTROL_CLASS}
                >
                  <SelectValue placeholder={t.questionPaper.bankSelectYear} />
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
            </BankFormField>

            <BankFormField id="bank-gen-book" label={t.questionPaper.storedBook}>
              <Select
                value={bookId || undefined}
                disabled={bookDisabled}
                onValueChange={(value) => {
                  setBookId(value)
                  setChapter('')
                }}
              >
                <SelectTrigger
                  id="bank-gen-book"
                  aria-labelledby={bankFieldLabelId('bank-gen-book')}
                  className={BANK_FIELD_CONTROL_CLASS}
                >
                  <SelectValue placeholder={t.questionPaper.bankSelectBook} />
                </SelectTrigger>
                <SelectContent>
                  {booksForYear.map((book) => (
                    <SelectItem key={bookRecordId(book)} value={bookRecordId(book)}>
                      {book.display_name || book.title || bookRecordId(book)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </BankFormField>

            <BankFormField id="bank-gen-chapter" label={t.questionPaper.chapter}>
              <Select
                value={chapter || undefined}
                disabled={chapterDisabled}
                onValueChange={setChapter}
              >
                <SelectTrigger
                  id="bank-gen-chapter"
                  aria-labelledby={bankFieldLabelId('bank-gen-chapter')}
                  className={BANK_FIELD_CONTROL_CLASS}
                >
                  <SelectValue placeholder={t.questionPaper.bankSelectChapter} />
                </SelectTrigger>
                <SelectContent>
                  {chapters.map((item, index) => {
                    const number = chapterNumberForApi(index)
                    return (
                      <SelectItem key={`${number}-${item.title}`} value={String(number)}>
                        {item.title || `Chapter ${number}`}
                      </SelectItem>
                    )
                  })}
                </SelectContent>
              </Select>
            </BankFormField>
          </div>

          {booksLoading && (
            <p className="text-xs text-muted-foreground flex items-center gap-2">
              <Loader2 className="h-3 w-3 animate-spin" />
              {t.questionPaper.loadingBooks}
            </p>
          )}
          {grade.trim() && !booksLoading && booksForGrade.length === 0 && (
            <p className="text-xs text-muted-foreground">{t.questionPaper.noBooksForGrade}</p>
          )}
          {loadingChapters && (
            <p className="text-xs text-muted-foreground flex items-center gap-2">
              <Loader2 className="h-3 w-3 animate-spin" />
              {t.questionPaper.loadingChapters}
            </p>
          )}
          {bookId && !loadingChapters && chapters.length === 0 && (
            <p className="text-xs text-destructive">{t.questionPaper.bankNoChapters}</p>
          )}

          <div className={BANK_FIELD_GRID_CLASS} data-testid="bank-generate-row-2">
            <BankFormField id="bank-gen-difficulty" label={t.questionPaper.difficulty}>
              <Select
                value={difficulty || undefined}
                disabled={isBusy}
                onValueChange={setDifficulty}
              >
                <SelectTrigger
                  id="bank-gen-difficulty"
                  aria-labelledby={bankFieldLabelId('bank-gen-difficulty')}
                  className={BANK_FIELD_CONTROL_CLASS}
                >
                  <SelectValue placeholder={t.questionPaper.bankSelectDifficulty} />
                </SelectTrigger>
                <SelectContent>
                  {BANK_BATCH_DIFFICULTIES.map((value) => (
                    <SelectItem key={value} value={value}>
                      {value === 'easy'
                        ? t.questionPaper.easy
                        : value === 'medium'
                          ? t.questionPaper.medium
                          : t.questionPaper.difficult}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </BankFormField>
            <BankFormField id="bank-total-q" label={t.questionPaper.totalQuestions}>
              <Input
                id="bank-total-q"
                type="number"
                min={1}
                max={200}
                disabled={isBusy}
                className={BANK_FIELD_CONTROL_CLASS}
                value={totalQuestions || ''}
                onChange={(e) => setTotalQuestions(parseNonNegInt(e.target.value))}
              />
            </BankFormField>
            <BankFormField id="bank-single" label={t.questionPaper.singleCorrect}>
              <Input
                id="bank-single"
                type="number"
                min={0}
                disabled={isBusy}
                className={BANK_FIELD_CONTROL_CLASS}
                value={singleCorrect || ''}
                onChange={(e) => setSingleCorrect(parseNonNegInt(e.target.value))}
              />
            </BankFormField>
            <BankFormField id="bank-multiple" label={t.questionPaper.multipleCorrect}>
              <Input
                id="bank-multiple"
                type="number"
                min={0}
                disabled={isBusy}
                className={BANK_FIELD_CONTROL_CLASS}
                value={multipleCorrect || ''}
                onChange={(e) => setMultipleCorrect(parseNonNegInt(e.target.value))}
              />
            </BankFormField>
          </div>

          {totalQuestions >= 1 && countError && (
            <p className="text-xs text-destructive">
              {t.questionPaper.bankCountMismatch
                .replace('{total}', String(totalQuestions))
                .replace('{sum}', String(singleCorrect + multipleCorrect))}
            </p>
          )}

          <Button type="submit" className="w-full" disabled={!canSubmit}>
            {isBusy ? t.questionPaper.bankGenerating : t.questionPaper.bankGenerate}
          </Button>
        </form>

        {(isSubmitting || pendingBatchId) && (
          <BankBatchProgressPanel
            status={batchStatus?.status || (isSubmitting ? 'pending' : 'running')}
            requested={batchStatus?.requested ?? (totalQuestions || null)}
            accepted={batchStatus?.accepted ?? 0}
            failed={batchStatus?.failed ?? 0}
            created={batchStatus?.created}
            errorMessage={batchStatus?.error_message}
            stopReason={batchStatus?.stop_reason}
            startedAtMs={startedAtMs}
          />
        )}
      </CardContent>
    </Card>
  )
}
