'use client'

import { useMemo, useState } from 'react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Separator } from '@/components/ui/separator'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { Info } from 'lucide-react'
import { BookUploader } from './BookUploader'
import {
  DEFAULT_PAPER_BLUEPRINT,
  type ChapterDifficultyCounts,
  type CognitiveDifficulty,
  type GeneratePaperRequest,
} from '@/lib/types/question-paper'

interface GenerateFormProps {
  onSubmit: (request: GeneratePaperRequest) => void
  isLoading: boolean
}

const DIFFICULTIES: CognitiveDifficulty[] = ['easy', 'medium', 'difficult']

/** Parse raw input to a non-negative integer; blank/invalid → 0. */
function parseNonNegInt(raw: string): number {
  const n = parseInt(raw, 10)
  if (Number.isNaN(n) || n < 0) return 0
  return n
}

function FieldInfo({ children }: { children: React.ReactNode }) {
  return (
    <TooltipProvider delayDuration={100}>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            className="inline-flex items-center justify-center rounded-full text-muted-foreground hover:text-foreground transition-colors focus:outline-none"
            aria-label="More information"
          >
            <Info className="h-3.5 w-3.5" />
          </button>
        </TooltipTrigger>
        <TooltipContent side="right" className="max-w-xs text-sm leading-relaxed">
          {children}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

function FieldLabel({ htmlFor, label, children }: { htmlFor?: string; label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-1.5">
      <Label htmlFor={htmlFor}>{label}</Label>
      <FieldInfo>{children}</FieldInfo>
    </div>
  )
}

function emptyCounts(): ChapterDifficultyCounts {
  return { easy: 0, medium: 0, difficult: 0 }
}

function sumCounts(counts: ChapterDifficultyCounts): number {
  return counts.easy + counts.medium + counts.difficult
}

export function GenerateForm({ onSubmit, isLoading }: GenerateFormProps) {
  const { t } = useTranslation()
  const [grade, setGrade] = useState('')
  const [subject, setSubject] = useState('')
  const [language, setLanguage] = useState('en')
  const [passPercentage, setPassPercentage] = useState(DEFAULT_PAPER_BLUEPRINT.pass_percentage)
  const [totalQuestions, setTotalQuestions] = useState(DEFAULT_PAPER_BLUEPRINT.total_questions)
  const [chapterMatrix, setChapterMatrix] = useState<Record<string, ChapterDifficultyCounts>>(
    () => structuredClone(DEFAULT_PAPER_BLUEPRINT.chapter_difficulty),
  )
  const [answerTypes, setAnswerTypes] = useState(
    () => structuredClone(DEFAULT_PAPER_BLUEPRINT.difficulty_answer_types),
  )
  const [objectivesText, setObjectivesText] = useState('')
  const [bookId, setBookId] = useState<string | null>(null)
  const [selectedChapters, setSelectedChapters] = useState<number[] | null>(null)
  const [selectedChapterCount, setSelectedChapterCount] = useState(0)
  const [autoTopic, setAutoTopic] = useState('')
  const [detectedGrade, setDetectedGrade] = useState<string | null>(null)

  const difficultyTotals = useMemo(() => {
    const totals = emptyCounts()
    for (const row of Object.values(chapterMatrix)) {
      totals.easy += row.easy
      totals.medium += row.medium
      totals.difficult += row.difficult
    }
    return totals
  }, [chapterMatrix])

  const matrixTotal = sumCounts(difficultyTotals)
  const matrixMismatch = matrixTotal !== totalQuestions
  const requiredChapters = Object.keys(chapterMatrix).length
  const chapterCountMismatch = !!bookId && selectedChapterCount !== requiredChapters

  const answerTypeTotals = useMemo(() => {
    return DIFFICULTIES.reduce(
      (acc, d) => {
        acc.single += answerTypes[d]?.single_correct ?? 0
        acc.multiple += answerTypes[d]?.multiple_correct ?? 0
        return acc
      },
      { single: 0, multiple: 0 },
    )
  }, [answerTypes])

  const answerTypeErrors = useMemo(() => {
    const errs: string[] = []
    for (const d of DIFFICULTIES) {
      const s = answerTypes[d]?.single_correct ?? 0
      const m = answerTypes[d]?.multiple_correct ?? 0
      const expected = difficultyTotals[d]
      if (s + m !== expected) {
        errs.push(`${d}: Single (${s}) + Multiple (${m}) = ${s + m}, expected ${expected}`)
      }
    }
    return errs
  }, [answerTypes, difficultyTotals])

  const updateChapterCell = (chapter: string, difficulty: CognitiveDifficulty, raw: string) => {
    const n = parseNonNegInt(raw)
    setChapterMatrix((prev) => ({
      ...prev,
      [chapter]: { ...prev[chapter], [difficulty]: n },
    }))
  }

  const updateAnswerType = (difficulty: CognitiveDifficulty, field: 'single_correct' | 'multiple_correct', raw: string) => {
    const n = parseNonNegInt(raw)
    setAnswerTypes((prev) => ({
      ...prev,
      [difficulty]: { ...prev[difficulty], [field]: n },
    }))
  }

  const canSubmit =
    !isLoading &&
    !!grade.trim() &&
    !!(subject.trim() || autoTopic) &&
    totalQuestions >= 1 &&
    !matrixMismatch &&
    !chapterCountMismatch &&
    answerTypeErrors.length === 0

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return
    const effectiveSubject = subject.trim() || autoTopic

    const objectives = objectivesText.split('\n').map((s) => s.trim()).filter(Boolean)

    onSubmit({
      topic: effectiveSubject,
      subject: effectiveSubject,
      grade: grade.trim(),
      language,
      difficulty: 'medium',
      target_marks: totalQuestions,
      pass_percentage: passPercentage,
      options_per_question: 5,
      question_format: 'mcq',
      curriculum_objectives: objectives,
      generator_model: null,
      reviewer_model: null,
      book_id: bookId,
      selected_chapters: selectedChapters,
      max_slot_attempts: 3,
      slot_concurrency: 3,
      blueprint: {
        ...DEFAULT_PAPER_BLUEPRINT,
        total_questions: totalQuestions,
        pass_percentage: passPercentage,
        language,
        chapter_difficulty: chapterMatrix,
        difficulty_answer_types: answerTypes,
      },
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <FieldLabel htmlFor="grade" label={t.questionPaper.grade}>
            <p>Grade is an active generation constraint. Questions use grade-appropriate vocabulary, examples, and reasoning.</p>
          </FieldLabel>
          <Input
            id="grade"
            placeholder="e.g. 5 or Grade 10"
            value={grade}
            onChange={(e) => setGrade(e.target.value)}
            required
          />
        </div>
        <div className="space-y-2">
          <FieldLabel htmlFor="language" label={t.questionPaper.language}>
            <p>Language used for generated questions and explanations.</p>
          </FieldLabel>
          <Select value={language} onValueChange={setLanguage}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="en">English</SelectItem>
              <SelectItem value="hi">Hindi</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {!bookId && (
        <div className="space-y-2">
          <FieldLabel htmlFor="subject" label={t.questionPaper.subject}>
            <p>Academic subject area for the examination.</p>
          </FieldLabel>
          <Input
            id="subject"
            placeholder="e.g. Financial Literacy"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            required={!bookId}
          />
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <FieldLabel htmlFor="totalQ" label={t.questionPaper.totalQuestions}>
            <p>Total number of questions for this paper. Must match the sum of the Chapter × Difficulty table below.</p>
          </FieldLabel>
          <Input
            id="totalQ"
            type="number"
            min={1}
            max={500}
            value={totalQuestions || ''}
            onChange={(e) => setTotalQuestions(parseNonNegInt(e.target.value))}
          />
        </div>
        <div className="space-y-2">
          <FieldLabel htmlFor="pass" label={t.questionPaper.passPercentage}>
            <p>Pass mark as a percentage of total marks.</p>
          </FieldLabel>
          <Input
            id="pass"
            type="number"
            min={1}
            max={100}
            value={passPercentage || ''}
            onChange={(e) => setPassPercentage(parseNonNegInt(e.target.value) || 70)}
          />
        </div>
      </div>

      <div className="space-y-2">
        <FieldLabel label={t.questionPaper.chapterBlueprint}>
          <p>Each cell is the number of questions for that chapter and cognitive difficulty. Row and column totals are computed automatically.</p>
        </FieldLabel>
        <div className="overflow-x-auto rounded-md border">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr>
                <th className="p-2 text-left font-medium">{t.questionPaper.chapter}</th>
                <th className="p-2 text-center font-medium">{t.questionPaper.easy}</th>
                <th className="p-2 text-center font-medium">{t.questionPaper.medium}</th>
                <th className="p-2 text-center font-medium">{t.questionPaper.difficult}</th>
                <th className="p-2 text-center font-medium">{t.questionPaper.total}</th>
              </tr>
            </thead>
            <tbody>
              {Object.keys(chapterMatrix).map((chapter) => (
                <tr key={chapter} className="border-t">
                  <td className="p-2">{t.questionPaper.chapter} {chapter}</td>
                  {DIFFICULTIES.map((d) => (
                    <td key={d} className="p-1">
                      <Input
                        type="number"
                        min={0}
                        className="h-8 text-center"
                        value={chapterMatrix[chapter][d] || ''}
                        onChange={(e) => updateChapterCell(chapter, d, e.target.value)}
                      />
                    </td>
                  ))}
                  <td className="p-2 text-center font-medium">{sumCounts(chapterMatrix[chapter])}</td>
                </tr>
              ))}
              <tr className={`border-t bg-muted/30 font-medium ${matrixMismatch ? 'text-destructive' : ''}`}>
                <td className="p-2">{t.questionPaper.total}</td>
                <td className="p-2 text-center">{difficultyTotals.easy}</td>
                <td className="p-2 text-center">{difficultyTotals.medium}</td>
                <td className="p-2 text-center">{difficultyTotals.difficult}</td>
                <td className="p-2 text-center">{matrixTotal}{matrixMismatch ? ` / ${totalQuestions}` : ''}</td>
              </tr>
            </tbody>
          </table>
        </div>
        {matrixMismatch && (
          <p className="text-xs text-destructive">
            Chapter blueprint totals {matrixTotal} questions, but Total Questions is {totalQuestions}. Please adjust the chapter distribution or Total Questions.
          </p>
        )}
      </div>

      <div className="space-y-2">
        <FieldLabel label={t.questionPaper.answerTypeBlueprint}>
          <p>Single Correct vs Multiple Correct per difficulty. Totals must match the chapter matrix difficulty totals.</p>
        </FieldLabel>
        <div className="overflow-x-auto rounded-md border">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr>
                <th className="p-2 text-left font-medium">{t.questionPaper.difficulty}</th>
                <th className="p-2 text-center font-medium">{t.questionPaper.singleCorrect}</th>
                <th className="p-2 text-center font-medium">{t.questionPaper.multipleCorrect}</th>
                <th className="p-2 text-center font-medium">{t.questionPaper.total}</th>
              </tr>
            </thead>
            <tbody>
              {DIFFICULTIES.map((d) => {
                const rowTotal = (answerTypes[d]?.single_correct ?? 0) + (answerTypes[d]?.multiple_correct ?? 0)
                const rowMismatch = rowTotal !== difficultyTotals[d]
                return (
                  <tr key={d} className={`border-t ${rowMismatch ? 'bg-destructive/5' : ''}`}>
                    <td className="p-2 capitalize">{d}</td>
                    <td className="p-1">
                      <Input
                        type="number"
                        min={0}
                        className="h-8 text-center"
                        value={answerTypes[d]?.single_correct || ''}
                        onChange={(e) => updateAnswerType(d, 'single_correct', e.target.value)}
                      />
                    </td>
                    <td className="p-1">
                      <Input
                        type="number"
                        min={0}
                        className="h-8 text-center"
                        value={answerTypes[d]?.multiple_correct || ''}
                        onChange={(e) => updateAnswerType(d, 'multiple_correct', e.target.value)}
                      />
                    </td>
                    <td className={`p-2 text-center ${rowMismatch ? 'text-destructive font-medium' : ''}`}>
                      {rowTotal} / {difficultyTotals[d]}
                    </td>
                  </tr>
                )
              })}
              <tr className="border-t bg-muted/30 font-medium">
                <td className="p-2">{t.questionPaper.total}</td>
                <td className="p-2 text-center">{answerTypeTotals.single}</td>
                <td className="p-2 text-center">{answerTypeTotals.multiple}</td>
                <td className={`p-2 text-center ${answerTypeTotals.single + answerTypeTotals.multiple !== totalQuestions ? 'text-destructive' : ''}`}>
                  {answerTypeTotals.single + answerTypeTotals.multiple} / {totalQuestions}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        {answerTypeErrors.length > 0 && (
          <div className="text-xs text-destructive space-y-0.5">
            {answerTypeErrors.map((err, i) => (
              <p key={i}>• {err}</p>
            ))}
          </div>
        )}
        <p className="text-xs text-muted-foreground">
          {t.questionPaper.optionsFormatLocked}
        </p>
      </div>

      <div className="space-y-2">
        <FieldLabel htmlFor="objectives" label={t.questionPaper.objectives}>
          <p>Optional learning goals — one per line — used for the coverage report after generation.</p>
        </FieldLabel>
        <Textarea
          id="objectives"
          placeholder={t.questionPaper.objectivesPlaceholder}
          value={objectivesText}
          onChange={(e) => setObjectivesText(e.target.value)}
          rows={3}
        />
      </div>

      <div className="space-y-2">
        <Separator />
        <FieldLabel label={t.questionPaper.bookSource}>
          <p>Choose a saved book by Grade, Year, and Book. Upload a new book only when it is not already in the library.</p>
        </FieldLabel>
        <BookUploader
          grade={grade}
          onBookReady={(id, chapters, bookTitle, chapterTitles, bookDetectedGrade) => {
            setBookId(id)
            setSelectedChapters(chapters)
            setSelectedChapterCount(chapterTitles.length)
            setDetectedGrade(bookDetectedGrade ?? null)
            const derived = chapterTitles.length === 0
              ? bookTitle
              : chapterTitles.length <= 2
                ? chapterTitles.join(' & ')
                : bookTitle
            setAutoTopic(derived)
            if (!subject) setSubject(derived)
          }}
          onClear={() => {
            setBookId(null)
            setSelectedChapters(null)
            setSelectedChapterCount(0)
            setAutoTopic('')
            setDetectedGrade(null)
          }}
        />
        {!bookId && (
          <p className="text-xs text-muted-foreground">{t.questionPaper.topicOnlyHint}</p>
        )}
        {bookId && chapterCountMismatch && (
          <p className="text-xs text-destructive">
            {t.questionPaper.chapterCountMismatch
              .replace('{required}', String(requiredChapters))
              .replace('{selected}', String(selectedChapterCount))}
          </p>
        )}
        {bookId && !chapterCountMismatch && (
          <p className="text-xs text-primary font-medium">{t.questionPaper.bookGrounded}</p>
        )}
        {bookId && detectedGrade && grade.trim() && grade.trim() !== detectedGrade && (
          <div className="flex items-start gap-2 rounded-md border border-yellow-300 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-950/20 p-2.5">
            <Info className="h-4 w-4 text-yellow-600 dark:text-yellow-400 mt-0.5 shrink-0" />
            <p className="text-xs text-yellow-800 dark:text-yellow-300">
              {t.questionPaper.gradeMismatchWarning
                .replace('{selected}', grade.trim())
                .replace('{detected}', detectedGrade)}
            </p>
          </div>
        )}
      </div>

      <Button
        type="submit"
        className="w-full"
        disabled={!canSubmit}
      >
        {isLoading ? t.questionPaper.generating : t.questionPaper.generate}
      </Button>
    </form>
  )
}
