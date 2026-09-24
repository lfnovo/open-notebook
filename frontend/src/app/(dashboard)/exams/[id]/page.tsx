'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import { ArrowLeft, Loader2, RotateCcw, Send, Trash2 } from 'lucide-react'
import { AppShell } from '@/components/layout/AppShell'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import {
  useDeleteExamAttempt,
  useExam,
  useExamAttempts,
  useSubmitExamAttempt,
} from '@/lib/hooks/use-exams'
import { useTranslation } from '@/lib/hooks/use-translation'
import { cn } from '@/lib/utils'
import { ExamAnswer, ExamAnswers, ExamAttempt, ExamQuestion } from '@/lib/types/exams'
import { QuestionInput } from '../components/QuestionInput'
import { ExamResults } from '../components/ExamResults'

function isAnswered(question: ExamQuestion, answer: ExamAnswer | undefined) {
  if (question.type === 'multiple_choice') return typeof answer === 'number'
  if (question.type === 'multiple_select') return Array.isArray(answer) && answer.length > 0
  if (question.type === 'fill_blank') return Array.isArray(answer) && answer.some((a) => String(a).trim())
  return typeof answer === 'string' && answer.trim().length > 0
}

export default function ExamPage() {
  const { t } = useTranslation()
  const params = useParams()
  const examId = params?.id ? decodeURIComponent(params.id as string) : ''

  const [answers, setAnswers] = useState<ExamAnswers>({})
  const [viewedAttempt, setViewedAttempt] = useState<ExamAttempt | null>(null)
  const [confirmSubmit, setConfirmSubmit] = useState(false)

  const { data: exam, isLoading } = useExam(examId)
  // The answer key is only fetched once results are shown.
  const { data: examWithAnswers } = useExam(viewedAttempt ? examId : '', true)
  const { data: attempts = [] } = useExamAttempts(examId)
  const submitAttempt = useSubmitExamAttempt(examId)
  const deleteAttempt = useDeleteExamAttempt(examId)

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (!exam) {
    return (
      <AppShell>
        <div className="p-6">
          <h1 className="text-2xl font-bold mb-4">{t('exams.notFound')}</h1>
          <Button asChild variant="outline">
            <Link href="/exams">{t('exams.backToExams')}</Link>
          </Button>
        </div>
      </AppShell>
    )
  }

  const questions = exam.questions ?? []
  const answeredCount = questions.filter((q) => isAnswered(q, answers[q.id])).length

  const submit = async () => {
    setConfirmSubmit(false)
    try {
      setViewedAttempt(await submitAttempt.mutateAsync(answers))
    } catch {
      // Error toast is shown by the mutation hook
    }
  }

  const retake = () => {
    setAnswers({})
    setViewedAttempt(null)
  }

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto">
        <div className="p-6 grid gap-6 lg:grid-cols-[1fr_280px] max-w-6xl">
          <div className="space-y-6 min-w-0">
            <div className="space-y-2">
              <Button asChild variant="ghost" size="sm" className="-ml-2">
                <Link href="/exams">
                  <ArrowLeft className="h-4 w-4 mr-1" />
                  {t('exams.backToExams')}
                </Link>
              </Button>
              <h1 className="font-display text-2xl font-bold tracking-tight">{exam.title}</h1>
              <div className="flex flex-wrap gap-2">
                <Badge variant="secondary">{t('exams.questionCount', { n: exam.question_count })}</Badge>
                <Badge variant="outline">{t(`exams.difficulties.${exam.difficulty}`)}</Badge>
                <Badge variant="outline">{t('exams.maxScore', { points: exam.max_score })}</Badge>
              </div>
            </div>

            {viewedAttempt ? (
              <>
                <ExamResults attempt={viewedAttempt} questions={examWithAnswers?.questions ?? questions} />
                <Button onClick={retake}>
                  <RotateCcw className="h-4 w-4 mr-2" />
                  {t('exams.retake')}
                </Button>
              </>
            ) : (
              <>
                {questions.map((question, index) => (
                  <Card key={question.id}>
                    <CardHeader className="pb-3">
                      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                        <span className="font-medium">{t('exams.questionN', { n: index + 1 })}</span>
                        <Badge variant="outline">{t(`exams.types.${question.type}`)}</Badge>
                        <span className="ml-auto">{t('exams.points', { n: question.points })}</span>
                      </div>
                      {question.type !== 'fill_blank' && (
                        <CardTitle className="text-base font-medium leading-snug whitespace-pre-wrap">
                          {question.prompt}
                        </CardTitle>
                      )}
                    </CardHeader>
                    <CardContent>
                      <QuestionInput
                        question={question}
                        value={answers[question.id]}
                        disabled={submitAttempt.isPending}
                        onChange={(value) => setAnswers((prev) => ({ ...prev, [question.id]: value }))}
                      />
                    </CardContent>
                  </Card>
                ))}

                <div className="sticky bottom-0 -mx-6 border-t bg-background/95 px-6 py-4 backdrop-blur flex flex-wrap items-center gap-4">
                  <p className="text-sm text-muted-foreground">
                    {t('exams.answeredProgress', { answered: answeredCount, total: questions.length })}
                  </p>
                  {submitAttempt.isPending && (
                    <p className="text-sm text-muted-foreground">{t('exams.gradingHint')}</p>
                  )}
                  <Button
                    className="ml-auto"
                    disabled={submitAttempt.isPending}
                    onClick={() => (answeredCount < questions.length ? setConfirmSubmit(true) : submit())}
                  >
                    {submitAttempt.isPending ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Send className="h-4 w-4 mr-2" />
                    )}
                    {submitAttempt.isPending ? t('exams.grading') : t('exams.submit')}
                  </Button>
                </div>
              </>
            )}
          </div>

          <aside className="space-y-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              {t('exams.attempts')}
            </h2>
            {attempts.length === 0 && <p className="text-sm text-muted-foreground">{t('exams.noAttempts')}</p>}
            {attempts.map((attempt) => {
              const percent = attempt.max_score > 0 ? Math.round((attempt.score / attempt.max_score) * 100) : 0
              return (
                <div
                  key={attempt.id}
                  className={cn(
                    'flex items-center gap-2 rounded-md border p-2 text-sm',
                    viewedAttempt?.id === attempt.id && 'border-primary'
                  )}
                >
                  <button
                    type="button"
                    className="flex-1 text-left"
                    onClick={() => setViewedAttempt(attempt)}
                  >
                    <span className="font-semibold">{percent}%</span>
                    <span className="block text-xs text-muted-foreground">
                      {new Date(attempt.created).toLocaleString()}
                    </span>
                  </button>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-7 w-7"
                    aria-label={t('common.delete')}
                    onClick={() =>
                      deleteAttempt.mutate(attempt.id, {
                        onSuccess: () => {
                          if (viewedAttempt?.id === attempt.id) setViewedAttempt(null)
                        },
                      })
                    }
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              )
            })}
          </aside>
        </div>
      </div>

      <ConfirmDialog
        open={confirmSubmit}
        onOpenChange={setConfirmSubmit}
        title={t('exams.submitIncompleteTitle')}
        description={t('exams.submitIncompleteDesc', { n: questions.length - answeredCount })}
        confirmText={t('exams.submit')}
        onConfirm={submit}
      />
    </AppShell>
  )
}
