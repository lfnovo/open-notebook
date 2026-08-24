'use client'

import { useTranslation } from '@/lib/hooks/use-translation'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { AlertCircle, CheckCircle2, Download, BookOpen, FileSpreadsheet, FileText, File, RefreshCw } from 'lucide-react'
import { useState } from 'react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { questionPaperApi } from '@/lib/api/question-paper'
import type { PaperQuestion, PaperResult, PaperSection, AnswerKeyItem } from '@/lib/types/question-paper'
import { formatPaperStatus, formatQuestionCount } from '@/lib/question-paper-labels'
import { DifficultyBreakdown } from '@/components/question-paper/DifficultyBreakdown'

interface PaperResultProps {
  result: PaperResult
  onRegenerated?: () => void
}

function displayDifficulty(value?: string | null) {
  if (value === 'hard') return 'difficult'
  return value || ''
}

function DifficultyBadge({ difficulty }: { difficulty: string }) {
  const label = displayDifficulty(difficulty)
  const variant =
    label === 'easy' ? 'secondary' : label === 'difficult' ? 'destructive' : 'default'
  return (
    <Badge variant={variant} className="capitalize text-xs">
      {label}
    </Badge>
  )
}

function QuestionPaperView({ sections }: { sections: PaperSection[] }) {
  const { t } = useTranslation()
  return (
    <div className="space-y-6">
      {sections.map((section, si) => (
        <div key={si} className="space-y-3">
          <h3 className="font-semibold text-base capitalize border-b pb-1">
            {t.questionPaper.section}: {section.section_name.toUpperCase()}
          </h3>
          <div className="space-y-4">
            {section.questions.map((q, qi) => (
              <QuestionCard key={qi} question={q} />
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

function QuestionCard({ question: q }: { question: PaperQuestion }) {
  const { t } = useTranslation()
  const target = displayDifficulty(q.target_difficulty || q.difficulty)
  const validated = displayDifficulty(q.validated_cognitive_difficulty)
  return (
    <div className="space-y-1 rounded-md border p-3">
      <div className="flex items-start gap-2">
        <span className="font-medium text-sm shrink-0 mt-0.5">{q.question_number}.</span>
        <div className="flex-1">
          <p className="text-sm">{q.question}</p>
          {q.options && q.options.length > 0 && (
            <ol className="mt-1.5 ml-2 space-y-0.5 list-[upper-alpha]">
              {q.options.map((opt, oi) => (
                <li key={oi} className="text-sm text-muted-foreground">
                  {opt}
                </li>
              ))}
            </ol>
          )}
          <div className="mt-2 flex flex-wrap gap-1.5 text-xs text-muted-foreground">
            {q.chapter_title && <span>{q.chapter_title}</span>}
            {q.topic && <span>· {q.topic}</span>}
            {q.sub_topic && <span>· {q.sub_topic}</span>}
            {q.answer_type && (
              <span>· {q.answer_type === 'multiple_correct' ? t.questionPaper.multipleCorrect : t.questionPaper.singleCorrect}</span>
            )}
          </div>
        </div>
        <div className="flex flex-col items-end gap-1 shrink-0">
          <DifficultyBadge difficulty={validated || target} />
          <Badge variant="outline" className="text-xs">{q.marks}m</Badge>
        </div>
      </div>
      {(q.target_difficulty || q.difficulty_score != null) && (
        <div className="text-xs text-muted-foreground pl-6 space-y-0.5">
          <p>
            {t.questionPaper.targetDifficulty}: <span className="capitalize">{target}</span>
            {validated && (
              <> · {t.questionPaper.validatedDifficulty}: <span className="capitalize">{validated}</span></>
            )}
            {q.difficulty_score != null && (
              <> · {t.questionPaper.cognitiveScore}: {q.difficulty_score}</>
            )}
          </p>
          {q.validation_status && (
            <p>
              {t.questionPaper.validationStatus}: {q.validation_status}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

function AnswerKeyView({ answerKey }: { answerKey: AnswerKeyItem[] }) {
  return (
    <Accordion type="multiple" className="space-y-1">
      {answerKey.map((item, i) => (
        <AccordionItem key={i} value={`answer-${i}`} className="border rounded-md px-3">
          <AccordionTrigger className="text-sm hover:no-underline py-2">
            <div className="flex items-start gap-2 text-left">
              <span className="font-medium shrink-0">{item.question_number}.</span>
              <span className="line-clamp-1">{item.question}</span>
            </div>
          </AccordionTrigger>
          <AccordionContent className="space-y-1 pb-3">
            <div className="flex items-start gap-1">
              <CheckCircle2 className="h-3.5 w-3.5 text-green-500 mt-0.5 shrink-0" />
              <p className="text-sm font-medium">{item.answer}</p>
            </div>
            {item.explanation && (
              <p className="text-xs text-muted-foreground ml-4.5">{item.explanation}</p>
            )}
          </AccordionContent>
        </AccordionItem>
      ))}
    </Accordion>
  )
}

export function PaperResultView({ result, onRegenerated }: PaperResultProps) {
  const { t } = useTranslation()
  const [regenerating, setRegenerating] = useState(false)
  const hasGaps = result.coverage_gaps && result.coverage_gaps.length > 0
  const hasCoverage = (result.covered_topics?.length ?? 0) > 0 || hasGaps
  const sections = result.final_paper?.sections ?? []
  const failedSlots = result.failed_slots ?? result.final_paper?.failed_slots ?? []
  const auditFailed = result.audit && result.audit.ok === false
  const missingCount = failedSlots.length
  const showRegenerate = result.status === 'needs_manual_review' && missingCount > 0

  const handleRegenerate = async () => {
    setRegenerating(true)
    try {
      await questionPaperApi.regenerateMissing(result.paper_id)
      onRegenerated?.()
    } catch {
      // error handled by caller via refresh
    } finally {
      setRegenerating(false)
    }
  }

  const downloadBlob = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  const baseName = `question-paper-${result.topic.toLowerCase().replace(/\s+/g, '-')}`

  const handleDownloadXlsx = async () => {
    const blob = await questionPaperApi.exportXlsx(result.paper_id)
    downloadBlob(blob, `${baseName}.xlsx`)
  }

  const handleDownloadDocx = async () => {
    const blob = await questionPaperApi.exportDocx(result.paper_id)
    downloadBlob(blob, `${baseName}.docx`)
  }

  const handleDownloadTxt = async () => {
    const blob = await questionPaperApi.exportTxt(result.paper_id)
    downloadBlob(blob, `${baseName}.txt`)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-lg font-semibold">{result.topic}</h2>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            {result.grade && <Badge variant="outline" className="text-xs">Grade {result.grade}</Badge>}
            {(result.display_status === 'partial' || result.status === 'needs_manual_review') &&
              result.display_status !== 'completed' && (
              <Badge variant="destructive" className="text-xs">DRAFT — NEEDS MANUAL REVIEW</Badge>
            )}
            <span className="text-sm text-muted-foreground">
              {formatPaperStatus(result.display_status || result.status)}
            </span>
          </div>
          <div className="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-2 text-sm">
            <div>
              <p className="text-muted-foreground">{t.questionPaper.requestedQuestions}</p>
              <p className="font-medium">{formatQuestionCount(result.requested_questions)}</p>
            </div>
            <div>
              <p className="text-muted-foreground">{t.questionPaper.generatedQuestions}</p>
              <p className="font-medium">{formatQuestionCount(result.generated_questions ?? result.final_paper?.question_count)}</p>
            </div>
            <div>
              <p className="text-muted-foreground">{t.questionPaper.remainingQuestions}</p>
              <p className="font-medium">{formatQuestionCount(result.remaining_questions)}</p>
            </div>
          </div>
          {result.target_marks != null && (
            <p className="text-xs text-muted-foreground mt-2">
              {t.questionPaper.targetMarks}: {result.target_marks}
            </p>
          )}
          <div className="mt-4">
            <DifficultyBreakdown
              requested={result.requested_difficulty}
              generated={result.generated_difficulty}
              remaining={result.remaining_difficulty}
            />
          </div>
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm">
              <Download className="h-4 w-4 mr-1" />
              {t.questionPaper.download}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={handleDownloadXlsx}>
              <FileSpreadsheet className="h-4 w-4 mr-2" />
              Excel (.xlsx) — QA Review
            </DropdownMenuItem>
            <DropdownMenuItem onClick={handleDownloadDocx}>
              <File className="h-4 w-4 mr-2" />
              Word (.docx) — Student Paper
            </DropdownMenuItem>
            <DropdownMenuItem onClick={handleDownloadTxt}>
              <FileText className="h-4 w-4 mr-2" />
              Text (.txt)
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {result.status === 'failed' && result.error_message && (
        <div className="rounded-md border p-3">
          <p className="text-sm font-medium mb-1">Error details</p>
          <pre className="text-xs whitespace-pre-wrap break-words text-muted-foreground">{result.error_message}</pre>
        </div>
      )}

      {auditFailed && (
        <div className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-3">
          <AlertCircle className="h-4 w-4 text-destructive mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-medium">{t.questionPaper.auditFailedTitle}</p>
            <ul className="mt-1 text-xs space-y-0.5">
              {(result.audit?.errors ?? []).map((err, i) => (
                <li key={i}>• {err}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {failedSlots.length > 0 && (
        <div className="rounded-md border p-3 space-y-2">
          <p className="text-sm font-medium">
            {t.questionPaper.questionsCouldNotFinalize.replace('{count}', String(missingCount))}
          </p>
          {failedSlots.map((slot, i) => (
            <p key={i} className="text-xs text-muted-foreground">
              Q{slot.question_number} · {slot.chapter_title || `Chapter ${slot.chapter}`} · {displayDifficulty(slot.target_difficulty)} · {(slot.validation_reasons || []).join('; ')}
            </p>
          ))}
          {showRegenerate && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleRegenerate}
              disabled={regenerating}
              className="mt-1"
            >
              <RefreshCw className={`h-4 w-4 mr-1 ${regenerating ? 'animate-spin' : ''}`} />
              {regenerating
                ? t.questionPaper.regenerating.replace('{count}', String(missingCount))
                : t.questionPaper.regenerateMissing.replace('{count}', String(missingCount))
              }
            </Button>
          )}
        </div>
      )}

      {hasCoverage && (
        <div className="space-y-2">
          {result.covered_topics?.length > 0 && (
            <div className="flex items-start gap-2 rounded-md border border-green-200 bg-green-50 dark:border-green-900 dark:bg-green-950/20 p-3">
              <BookOpen className="h-4 w-4 text-green-600 dark:text-green-400 mt-0.5 shrink-0" />
              <div>
                <p className="text-sm font-medium text-green-800 dark:text-green-300">
                  {t.questionPaper.coveredTopicsTitle}
                </p>
                <ul className="mt-1 text-xs text-green-700 dark:text-green-400 space-y-0.5">
                  {result.covered_topics.map((topic, i) => (
                    <li key={i} className="flex items-start gap-1">
                      <CheckCircle2 className="h-3 w-3 mt-0.5 shrink-0" />
                      <span>{topic}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
          {hasGaps && (
            <div className="flex items-start gap-2 rounded-md border border-yellow-200 bg-yellow-50 dark:border-yellow-900 dark:bg-yellow-950/20 p-3">
              <AlertCircle className="h-4 w-4 text-yellow-600 dark:text-yellow-400 mt-0.5 shrink-0" />
              <div>
                <p className="text-sm font-medium text-yellow-800 dark:text-yellow-300">
                  {t.questionPaper.coverageGapsTitle}
                </p>
                <ul className="mt-1 text-xs text-yellow-700 dark:text-yellow-400 space-y-0.5">
                  {result.coverage_gaps.map((gap, i) => (
                    <li key={i}>• {gap}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>
      )}

      <Tabs defaultValue="paper">
        <TabsList className="w-full">
          <TabsTrigger value="paper" className="flex-1">
            {t.questionPaper.questionPaperTab}
          </TabsTrigger>
          <TabsTrigger value="answers" className="flex-1">
            {t.questionPaper.answerKeyTab}
          </TabsTrigger>
        </TabsList>
        <TabsContent value="paper" className="mt-4">
          {sections.length > 0 ? (
            <QuestionPaperView sections={sections} />
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">
              {t.questionPaper.noQuestions}
            </p>
          )}
        </TabsContent>
        <TabsContent value="answers" className="mt-4">
          {result.answer_key.length > 0 ? (
            <AnswerKeyView answerKey={result.answer_key} />
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">
              {t.questionPaper.noAnswerKey}
            </p>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
