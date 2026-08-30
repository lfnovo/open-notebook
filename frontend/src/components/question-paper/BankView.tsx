'use client'

import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Loader2, Search, Download } from 'lucide-react'
import { toast } from 'sonner'
import { useBooks, useQuestionBank, useQuestionBooks } from '@/lib/hooks/use-question-paper'
import { questionPaperApi } from '@/lib/api/question-paper'
import { bookRecordId, gradesMatch } from '@/components/question-paper/BookUploader'
import {
  BANK_FIELD_CONTROL_CLASS,
  BANK_FIELD_GRID_CLASS,
  BankFormField,
  bankFieldLabelId,
} from '@/components/question-paper/BankFormField'
import type { BankQuestion } from '@/lib/types/question-paper'
import {
  OPTION_LETTERS,
  OTHER_LEGACY,
  chapterLabel,
  difficultyKey,
  formatAnswerType,
  formatChapterLabel,
  formatCorrectAnswer,
  formatDifficulty,
  formatValidationStatus,
  questionDifficulty,
} from '@/lib/question-paper-labels'

const ALL = '__all__'
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

function bookLabel(
  bookId: string,
  titles: Record<string, string>,
  booksById: Record<string, { display_name?: string | null }>,
) {
  return titles[bookId] || booksById[bookId]?.display_name || bookId
}

function questionCountByBook(questions: BankQuestion[]): Record<string, number> {
  const counts: Record<string, number> = {}
  for (const q of questions) {
    const id = String(q.book_id || '').trim()
    if (!id) continue
    counts[id] = (counts[id] || 0) + 1
  }
  return counts
}

function bookIsComplete(
  bookId: string,
  booksById: Record<string, { year?: string | null }>,
  counts: Record<string, number>,
) {
  const hasYear = Boolean(String(booksById[bookId]?.year || '').trim())
  return hasYear && (counts[bookId] || 0) > 0
}

function bookOptionLabel(
  bookId: string,
  titles: Record<string, string>,
  booksById: Record<string, { display_name?: string | null; year?: string | null; grade?: string | null }>,
  counts: Record<string, number>,
) {
  const name = bookLabel(bookId, titles, booksById)
  const count = counts[bookId] || 0
  const meta = booksById[bookId]
  const hasYear = Boolean(String(meta?.year || '').trim())
  if (hasYear && count > 0) return `${name} (${count})`
  if (!hasYear) {
    const grade = String(meta?.grade || '').trim()
    const gradeName = grade ? `Grade ${grade}` : ''
    if (gradeName && (!name || name === grade || name === gradeName || /^grade\s/i.test(name))) {
      return `${gradeName} — Missing details`
    }
    return `${name || 'Legacy Book'} — Missing Year`
  }
  return `${name} (0)`
}

export function BankView() {
  const { t } = useTranslation()
  const [grade, setGrade] = useState('')
  const [year, setYear] = useState('')
  const [bookId, setBookId] = useState('')
  const [chapter, setChapter] = useState('')
  const [difficulty, setDifficulty] = useState('')
  const [answerType, setAnswerType] = useState('')
  const [batchId, setBatchId] = useState('')
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<BankQuestion | null>(null)
  const [downloading, setDownloading] = useState(false)

  const { data: questions = [], isLoading } = useQuestionBank('')
  const { data: libraryBooks = [] } = useBooks()
  const bookTitles = useQuestionBooks(uniqueSorted(questions.map((q) => q.book_id)))

  const booksById = useMemo(() => {
    const map: Record<string, (typeof libraryBooks)[number]> = {}
    for (const book of libraryBooks) map[bookRecordId(book)] = book
    return map
  }, [libraryBooks])

  const grades = useMemo(
    () => uniqueSorted([...questions.map((q) => q.grade), ...libraryBooks.map((b) => b.grade)]),
    [questions, libraryBooks],
  )

  const booksForGrade = useMemo(() => {
    if (!grade) return []
    const fromQuestions = questions
      .filter((q) => String(q.grade || '') === grade || gradesMatch(q.grade, grade))
      .map((q) => q.book_id)
    const fromLibrary = libraryBooks
      .filter((book) => gradesMatch(book.grade, grade))
      .map((book) => bookRecordId(book))
    return uniqueSorted([...fromQuestions, ...fromLibrary])
  }, [questions, libraryBooks, grade])

  const yearsForGrade = useMemo(() => {
    const years = uniqueSorted(
      booksForGrade.map((id) => booksById[id]?.year).filter(Boolean) as string[],
    )
    const hasMissing = booksForGrade.some(
      (id) => booksById[id] && !String(booksById[id].year || '').trim(),
    )
    return { years, hasMissing }
  }, [booksForGrade, booksById])

  const booksForYear = useMemo(() => {
    if (!grade || !year) return []
    return booksForGrade.filter((id) => {
      const meta = booksById[id]
      if (year === MISSING_YEAR) return !meta || !String(meta.year || '').trim()
      if (!meta?.year) return false
      return String(meta.year) === year
    })
  }, [booksForGrade, booksById, grade, year])

  const countsByBook = useMemo(() => questionCountByBook(questions), [questions])

  const sortedBooksForYear = useMemo(() => {
    return [...booksForYear].sort((a, b) => {
      const completeA = bookIsComplete(a, booksById, countsByBook) ? 0 : 1
      const completeB = bookIsComplete(b, booksById, countsByBook) ? 0 : 1
      if (completeA !== completeB) return completeA - completeB
      return bookOptionLabel(a, bookTitles, booksById, countsByBook).localeCompare(
        bookOptionLabel(b, bookTitles, booksById, countsByBook),
      )
    })
  }, [booksForYear, booksById, countsByBook, bookTitles])

  useEffect(() => {
    setYear('')
    setBookId('')
    setChapter('')
    setDifficulty('')
  }, [grade])

  useEffect(() => {
    if (!grade) return
    if (yearsForGrade.years.length === 1 && !yearsForGrade.hasMissing) {
      setYear(yearsForGrade.years[0])
      return
    }
    if (yearsForGrade.years.length === 0 && yearsForGrade.hasMissing) {
      setYear(MISSING_YEAR)
    }
  }, [grade, yearsForGrade.years, yearsForGrade.hasMissing])

  useEffect(() => {
    if (!year) {
      setBookId('')
      return
    }
    if (booksForYear.length === 1) {
      setBookId(booksForYear[0])
      return
    }
    if (bookId && !booksForYear.includes(bookId)) {
      setBookId('')
    }
  }, [year, booksForYear, bookId])

  const chaptersForBook = useMemo(() => {
    return uniqueSorted(
      questions
        .filter((q) => {
          if (grade && String(q.grade || '') !== grade && !gradesMatch(q.grade, grade)) return false
          if (bookId && String(q.book_id || '') !== bookId) return false
          return true
        })
        .map((q) => q.chapter),
    )
  }, [questions, grade, bookId])

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase()
    return questions.filter((q) => {
      if (grade && String(q.grade || '') !== grade && !gradesMatch(q.grade, grade)) return false
      if (year) {
        if (bookId) {
          if (String(q.book_id || '') !== bookId) return false
        } else if (booksForYear.length === 1) {
          if (String(q.book_id || '') !== booksForYear[0]) return false
        } else {
          return false
        }
      }
      if (chapter && String(q.chapter || '') !== chapter) return false
      if (difficulty && difficultyKey(questionDifficulty(q)) !== difficulty) return false
      if (answerType && formatAnswerType(q.type, q.answer_type) !== answerType) return false
      if (batchId && String(q.batch_id || '') !== batchId) return false
      if (needle) {
        const haystack = [q.question, q.topic, q.sub_topic, q.chapter_title]
          .filter(Boolean)
          .join(' ')
          .toLowerCase()
        if (!haystack.includes(needle)) return false
      }
      return true
    })
  }, [questions, grade, year, bookId, booksForYear, chapter, difficulty, answerType, batchId, search])

  const summary = useMemo(() => {
    const counts = { total: filtered.length, easy: 0, medium: 0, difficult: 0 }
    for (const q of filtered) {
      const key = difficultyKey(questionDifficulty(q))
      if (key) counts[key] += 1
    }
    return counts
  }, [filtered])

  const selectionSummary = useMemo(() => {
    const parts: string[] = []
    if (bookId) parts.push(bookLabel(bookId, bookTitles, booksById))
    if (chapter) {
      parts.push(formatChapterLabel(chapter))
    }
    if (difficulty) parts.push(formatDifficulty(difficulty))
    if (batchId) parts.push(batchId)
    parts.push(`${filtered.length} Questions`)
    return parts.join(' · ')
  }, [bookId, bookTitles, booksById, chapter, difficulty, batchId, filtered.length])

  const resetFilters = () => {
    setGrade('')
    setYear('')
    setBookId('')
    setChapter('')
    setDifficulty('')
    setAnswerType('')
    setBatchId('')
    setSearch('')
  }

  const batches = useMemo(
    () => uniqueSorted(questions.map((q) => q.batch_id)),
    [questions],
  )

  const downloadFiltered = async () => {
    if (filtered.length === 0 || downloading) return
    setDownloading(true)
    try {
      const blob = await questionPaperApi.exportBankXlsx(filtered.map((q) => q.id))
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      const batchPart = batchId ? batchId.replace(/[:/\\]/g, '_') : 'filtered'
      link.download = `question_bank_${batchPart}.xlsx`
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
    } catch {
      toast.error(t.questionPaper.bankDownloadFailed)
    } finally {
      setDownloading(false)
    }
  }

  const yearDisabled = !grade
  const bookDisabled = !year
  const chapterDisabled = !year || (booksForYear.length > 1 && !bookId)
  const difficultyDisabled = !bookId

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="bank-summary-cards">
        <SummaryTile
          testId="bank-summary-total"
          label={t.questionPaper.bankSummaryTotal}
          value={summary.total}
        />
        <SummaryTile testId="bank-summary-easy" label={t.questionPaper.easy} value={summary.easy} />
        <SummaryTile testId="bank-summary-medium" label={t.questionPaper.medium} value={summary.medium} />
        <SummaryTile
          testId="bank-summary-difficult"
          label={t.questionPaper.difficult}
          value={summary.difficult}
        />
      </div>
      <p className="text-sm text-muted-foreground">{t.questionPaper.bankDesc}</p>

      <div className="space-y-3" data-testid="bank-filter-fields">
        <div className={BANK_FIELD_GRID_CLASS} data-testid="bank-filter-row-1">
        <BankFormField id="bank-filter-grade" label={t.questionPaper.grade}>
          <Select
            value={grade || undefined}
            onValueChange={(value) => {
              setGrade(value === ALL ? '' : value)
              setChapter('')
              setDifficulty('')
            }}
          >
            <SelectTrigger
              id="bank-filter-grade"
              aria-labelledby={bankFieldLabelId('bank-filter-grade')}
              className={BANK_FIELD_CONTROL_CLASS}
            >
              <SelectValue placeholder={t.questionPaper.bankSelectGrade} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>{t.questionPaper.filterAll}</SelectItem>
              {grades.map((value) => (
                <SelectItem key={value} value={value}>{value}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </BankFormField>

        <BankFormField id="bank-filter-year" label={t.questionPaper.year}>
          <Select
            value={year || undefined}
            disabled={yearDisabled}
            onValueChange={(value) => {
              setYear(value === ALL ? '' : value)
              setBookId('')
              setChapter('')
              setDifficulty('')
            }}
          >
            <SelectTrigger
              id="bank-filter-year"
              aria-labelledby={bankFieldLabelId('bank-filter-year')}
              className={BANK_FIELD_CONTROL_CLASS}
            >
              <SelectValue placeholder={t.questionPaper.bankSelectYear} />
            </SelectTrigger>
            <SelectContent>
              {yearsForGrade.years.map((value) => (
                <SelectItem key={value} value={value}>{value}</SelectItem>
              ))}
              {yearsForGrade.hasMissing && (
                <SelectItem value={MISSING_YEAR}>{t.questionPaper.yearNotSet}</SelectItem>
              )}
            </SelectContent>
          </Select>
        </BankFormField>

        <BankFormField id="bank-filter-book" label={t.questionPaper.bankFilterBook}>
          <Select
            value={bookId || undefined}
            disabled={bookDisabled}
            onValueChange={(value) => {
              setBookId(value)
              setChapter('')
              setDifficulty('')
            }}
          >
            <SelectTrigger
              id="bank-filter-book"
              aria-labelledby={bankFieldLabelId('bank-filter-book')}
              className={BANK_FIELD_CONTROL_CLASS}
            >
              <SelectValue placeholder={t.questionPaper.bankSelectBook} />
            </SelectTrigger>
            <SelectContent>
              {sortedBooksForYear.map((id) => (
                <SelectItem
                  key={id}
                  value={id}
                  className={bookIsComplete(id, booksById, countsByBook) ? undefined : 'text-muted-foreground'}
                >
                  {bookOptionLabel(id, bookTitles, booksById, countsByBook)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </BankFormField>

        <BankFormField id="bank-filter-chapter" label={t.questionPaper.chapter}>
          <Select
            value={chapter || undefined}
            disabled={chapterDisabled}
            onValueChange={(value) => {
              setChapter(value === ALL ? '' : value)
            }}
          >
            <SelectTrigger
              id="bank-filter-chapter"
              aria-labelledby={bankFieldLabelId('bank-filter-chapter')}
              className={BANK_FIELD_CONTROL_CLASS}
            >
              <SelectValue placeholder={t.questionPaper.bankSelectChapter} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>{t.questionPaper.filterAll}</SelectItem>
              {chaptersForBook.map((value) => (
                <SelectItem key={value} value={value}>{formatChapterLabel(value)}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </BankFormField>
        </div>

        <div className={BANK_FIELD_GRID_CLASS} data-testid="bank-filter-row-2">
        <BankFormField id="bank-filter-difficulty" label={t.questionPaper.difficulty}>
          <Select
            value={difficulty || undefined}
            disabled={difficultyDisabled}
            onValueChange={(value) => setDifficulty(value === ALL ? '' : value)}
          >
            <SelectTrigger
              id="bank-filter-difficulty"
              aria-labelledby={bankFieldLabelId('bank-filter-difficulty')}
              className={BANK_FIELD_CONTROL_CLASS}
            >
              <SelectValue placeholder={t.questionPaper.bankSelectDifficulty} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>{t.questionPaper.filterAll}</SelectItem>
              <SelectItem value="easy">{t.questionPaper.easy}</SelectItem>
              <SelectItem value="medium">{t.questionPaper.medium}</SelectItem>
              <SelectItem value="difficult">{t.questionPaper.difficult}</SelectItem>
            </SelectContent>
          </Select>
        </BankFormField>

        <BankFormField id="bank-filter-answer-type" label={t.questionPaper.bankFilterAnswerType}>
          <Select
            value={answerType || undefined}
            onValueChange={(value) => setAnswerType(value === ALL ? '' : value)}
          >
            <SelectTrigger
              id="bank-filter-answer-type"
              aria-labelledby={bankFieldLabelId('bank-filter-answer-type')}
              className={BANK_FIELD_CONTROL_CLASS}
            >
              <SelectValue placeholder={t.questionPaper.bankSelectAnswerType} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>{t.questionPaper.filterAll}</SelectItem>
              <SelectItem value="Single Correct">{t.questionPaper.singleCorrect}</SelectItem>
              <SelectItem value="Multiple Correct">{t.questionPaper.multipleCorrect}</SelectItem>
              <SelectItem value={OTHER_LEGACY}>{t.questionPaper.otherLegacy}</SelectItem>
            </SelectContent>
          </Select>
        </BankFormField>

        <BankFormField id="bank-filter-batch" label={t.questionPaper.bankFilterBatch}>
          <Select
            value={batchId || undefined}
            onValueChange={(value) => setBatchId(value === ALL ? '' : value)}
          >
            <SelectTrigger
              id="bank-filter-batch"
              aria-labelledby={bankFieldLabelId('bank-filter-batch')}
              className={BANK_FIELD_CONTROL_CLASS}
            >
              <SelectValue placeholder={t.questionPaper.bankSelectBatch} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>{t.questionPaper.filterAll}</SelectItem>
              {batches.map((value) => (
                <SelectItem key={value} value={value}>{value}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </BankFormField>

        <BankFormField id="bank-filter-search" label={t.questionPaper.bankFilterSearch}>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              id="bank-filter-search"
              placeholder={t.questionPaper.bankSearchPlaceholder}
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              className={`${BANK_FIELD_CONTROL_CLASS} pl-9`}
            />
          </div>
        </BankFormField>
        </div>
      </div>

      <div className="flex justify-end gap-2">
        <Button variant="outline" size="sm" onClick={resetFilters}>
          {t.questionPaper.bankFilterReset}
        </Button>
        <Button
          size="sm"
          onClick={downloadFiltered}
          disabled={filtered.length === 0 || downloading}
        >
          {downloading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Download className="h-4 w-4" />
          )}
          {t.questionPaper.bankDownloadExcel}
        </Button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-10">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="space-y-2">
          <p className="text-sm font-medium">{selectionSummary}</p>
          {filtered.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-10">
              {questions.length === 0 ? t.questionPaper.bankEmpty : t.questionPaper.bankNoResults}
            </p>
          ) : (
          <div className="overflow-x-auto rounded-md border">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 text-left">
                <tr className="border-b">
                  <th className="px-3 py-2 font-medium">{t.questionPaper.bankColQuestion}</th>
                  <th className="px-3 py-2 font-medium whitespace-nowrap">{t.questionPaper.chapter}</th>
                  <th className="px-3 py-2 font-medium whitespace-nowrap">{t.questionPaper.difficulty}</th>
                  <th className="px-3 py-2 font-medium whitespace-nowrap">{t.questionPaper.bankFilterAnswerType}</th>
                  <th className="px-3 py-2 font-medium">{t.questionPaper.topic}</th>
                  <th className="px-3 py-2 font-medium whitespace-nowrap">{t.questionPaper.validationStatus}</th>
                  <th className="px-3 py-2 font-medium text-right">{t.questionPaper.bankColView}</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((q) => (
                  <tr key={q.id} className="border-b last:border-0 align-top">
                    <td className="px-3 py-2 max-w-md"><p className="line-clamp-2">{q.question}</p></td>
                    <td className="px-3 py-2 whitespace-nowrap text-muted-foreground">{chapterLabel(q)}</td>
                    <td className="px-3 py-2 whitespace-nowrap">{formatDifficulty(questionDifficulty(q))}</td>
                    <td className="px-3 py-2 whitespace-nowrap">{formatAnswerType(q.type, q.answer_type)}</td>
                    <td className="px-3 py-2 text-muted-foreground">{q.topic || '—'}</td>
                    <td className="px-3 py-2 whitespace-nowrap">{formatValidationStatus(q.validation_status)}</td>
                    <td className="px-3 py-2 text-right">
                      <Button variant="outline" size="sm" onClick={() => setSelected(q)}>
                        {t.questionPaper.bankColView}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          )}
        </div>
      )}

      <QuestionDetailDialog
        question={selected}
        bookTitle={selected?.book_id ? bookLabel(selected.book_id, bookTitles, booksById) : undefined}
        year={selected?.book_id ? booksById[selected.book_id]?.year : undefined}
        onClose={() => setSelected(null)}
      />
    </div>
  )
}

function SummaryTile({
  label,
  value,
  testId,
}: {
  label: string
  value: number
  testId: string
}) {
  return (
    <div className="rounded-md border bg-card px-3 py-3" data-testid={testId}>
      <p className="text-sm font-medium text-foreground">{label}</p>
      <p className="text-2xl font-semibold tabular-nums mt-1">{value}</p>
    </div>
  )
}

function QuestionDetailDialog({
  question,
  bookTitle,
  year,
  onClose,
}: {
  question: BankQuestion | null
  bookTitle?: string
  year?: string | null
  onClose: () => void
}) {
  const { t } = useTranslation()
  if (!question) return null

  return (
    <Dialog open={!!question} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{t.questionPaper.bankDetailTitle}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 text-sm">
          <p>{question.question}</p>
          {question.options && question.options.length > 0 ? (
            <ol className="ml-5 space-y-1 list-[upper-alpha]">
              {question.options.slice(0, 5).map((option, index) => (
                <li key={index}>{option}</li>
              ))}
            </ol>
          ) : (
            <p className="text-muted-foreground">
              {OPTION_LETTERS.map((letter) => letter).join(' · ')}
            </p>
          )}
          <p className="font-medium">{formatCorrectAnswer(question)}</p>
          {question.explanation && (
            <div>
              <p className="text-xs text-muted-foreground mb-1">{t.questionPaper.explanation}</p>
              <p>{question.explanation}</p>
            </div>
          )}
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-2">
            <DetailRow label={t.questionPaper.grade} value={question.grade} />
            <DetailRow label={t.questionPaper.year} value={year} />
            <DetailRow label={t.questionPaper.bankFilterBook} value={bookTitle || question.book_id} />
            <DetailRow label={t.questionPaper.chapter} value={chapterLabel(question)} />
            <DetailRow label={t.questionPaper.difficulty} value={formatDifficulty(questionDifficulty(question))} />
            <DetailRow label={t.questionPaper.topic} value={question.topic} />
            <DetailRow label={t.questionPaper.bankDetailSubTopic} value={question.sub_topic} />
            <DetailRow
              label={t.questionPaper.cognitiveScore}
              value={question.difficulty_score != null ? String(question.difficulty_score) : null}
            />
            <DetailRow
              label={t.questionPaper.bankDetailBatchId}
              value={question.batch_id}
            />
            <DetailRow
              label={t.questionPaper.validationStatus}
              value={formatValidationStatus(question.validation_status)}
            />
          </dl>
        </div>
      </DialogContent>
    </Dialog>
  )
}

function DetailRow({ label, value }: { label: string; value?: string | number | null }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd>{value || '—'}</dd>
    </div>
  )
}
