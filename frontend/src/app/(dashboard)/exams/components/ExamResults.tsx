'use client'

import { CheckCircle2, XCircle, MinusCircle, Sparkles } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { useTranslation } from '@/lib/hooks/use-translation'
import { cn } from '@/lib/utils'
import { ExamAttempt, ExamQuestion, ExamQuestionResult } from '@/lib/types/exams'
import type { ChatImage } from '@/lib/types/api'
import { ExamQuestionImages } from './ExamQuestionImages'
import { BLANK_MARKER, blankAnswers } from './QuestionInput'

function formatScore(value: number) {
  return Number.isInteger(value) ? String(value) : value.toFixed(1)
}

function ResultIcon({ result }: { result: ExamQuestionResult }) {
  if (result.is_correct) return <CheckCircle2 className="h-5 w-5 text-green-600 shrink-0" />
  if (result.score > 0) return <MinusCircle className="h-5 w-5 text-amber-500 shrink-0" />
  return <XCircle className="h-5 w-5 text-destructive shrink-0" />
}

function QuestionReview({
  question,
  result,
  answer,
  index,
  images,
}: {
  question: ExamQuestion
  result?: ExamQuestionResult
  answer: ExamAttempt['answers'][string] | undefined
  index: number
  images?: Record<string, ChatImage>
}) {
  const { t } = useTranslation()

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start gap-3">
          {result && <ResultIcon result={result} />}
          <div className="flex-1 space-y-2">
            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <span className="font-medium">{t('exams.questionN', { n: index + 1 })}</span>
              <Badge variant="outline">{t(`exams.types.${question.type}`)}</Badge>
              {result?.graded_by === 'ai' && (
                <Badge variant="secondary" className="gap-1">
                  <Sparkles className="h-3 w-3" />
                  {t('exams.gradedByAi')}
                </Badge>
              )}
              {result && (
                <span className="ml-auto font-semibold text-foreground">
                  {formatScore(result.score)} / {formatScore(result.max_score)}
                </span>
              )}
            </div>
            <p className="font-medium whitespace-pre-wrap">
              {question.type === 'fill_blank' ? question.prompt.split(BLANK_MARKER).join('_____') : question.prompt}
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <ExamQuestionImages question={question} images={images} review />
        {(question.type === 'multiple_choice' || question.type === 'multiple_select') && (
          <ul className="space-y-1.5">
            {question.options.map((option, i) => {
              const isCorrect =
                question.type === 'multiple_select'
                  ? (question.correct_options ?? []).includes(i)
                  : i === question.correct_option
              const isChosen = Array.isArray(answer) ? (answer as number[]).includes(i) : i === answer
              return (
                <li
                  key={i}
                  className={cn(
                    'rounded-md border px-3 py-2',
                    isCorrect && 'border-green-600 bg-green-600/10',
                    isChosen && !isCorrect && 'border-destructive bg-destructive/10'
                  )}
                >
                  {option}
                  {isChosen && (
                    <span className="ml-2 text-xs text-muted-foreground">({t('exams.yourAnswer')})</span>
                  )}
                </li>
              )
            })}
          </ul>
        )}

        {question.type === 'fill_blank' && (
          <div className="space-y-1.5">
            {blankAnswers(answer, question.blank_count).map((given, i) => (
              <div key={i} className="grid grid-cols-[auto_1fr] gap-x-3">
                <span className="text-muted-foreground">{t('exams.blankN', { n: i + 1 })}:</span>
                <span>
                  <span className={cn(!given && 'italic text-muted-foreground')}>
                    {given || t('exams.noAnswer')}
                  </span>
                  {question.blanks?.[i] && (
                    <span className="text-muted-foreground">
                      {' '}
                      → {question.blanks[i].join(' / ')}
                    </span>
                  )}
                </span>
              </div>
            ))}
          </div>
        )}

        {question.type === 'open' && (
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {t('exams.yourAnswer')}
            </p>
            <p className={cn('whitespace-pre-wrap rounded-md bg-muted p-3', !answer && 'italic text-muted-foreground')}>
              {typeof answer === 'string' && answer.trim() ? answer : t('exams.noAnswer')}
            </p>
          </div>
        )}

        {result?.feedback && (
          <div className="rounded-md border-l-4 border-primary bg-primary/5 p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">
              {t('exams.feedback')}
            </p>
            <p className="whitespace-pre-wrap">{result.feedback}</p>
          </div>
        )}

        {question.type === 'open' && question.reference_answer && (
          <details className="rounded-md border p-3">
            <summary className="cursor-pointer font-medium">{t('exams.referenceAnswer')}</summary>
            <p className="mt-2 whitespace-pre-wrap">{question.reference_answer}</p>
          </details>
        )}

        {question.explanation && (
          <p className="text-muted-foreground">
            <span className="font-medium text-foreground">{t('exams.explanation')}: </span>
            {question.explanation}
          </p>
        )}
      </CardContent>
    </Card>
  )
}

interface ExamResultsProps {
  attempt: ExamAttempt
  questions: ExamQuestion[]
  images?: Record<string, ChatImage>
}

export function ExamResults({ attempt, questions, images }: ExamResultsProps) {
  const { t } = useTranslation()
  const percent = attempt.max_score > 0 ? Math.round((attempt.score / attempt.max_score) * 100) : 0
  const resultsById = Object.fromEntries(attempt.results.map((r) => [r.question_id, r]))
  const correct = attempt.results.filter((r) => r.is_correct).length

  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="pt-6 space-y-3">
          <div className="flex flex-wrap items-end justify-between gap-2">
            <div>
              <p className="text-sm text-muted-foreground">{t('exams.yourScore')}</p>
              <p className="text-4xl font-bold">
                {formatScore(attempt.score)}
                <span className="text-xl text-muted-foreground"> / {formatScore(attempt.max_score)}</span>
              </p>
            </div>
            <p className="text-3xl font-semibold">{percent}%</p>
          </div>
          <Progress value={percent} />
          <p className="text-sm text-muted-foreground">
            {t('exams.correctSummary', { correct, total: attempt.results.length })} ·{' '}
            {new Date(attempt.created).toLocaleString()}
          </p>
        </CardContent>
      </Card>

      {questions.map((question, index) => (
        <QuestionReview
          key={question.id}
          question={question}
          images={images}
          index={index}
          result={resultsById[question.id]}
          answer={attempt.answers[question.id]}
        />
      ))}
    </div>
  )
}
