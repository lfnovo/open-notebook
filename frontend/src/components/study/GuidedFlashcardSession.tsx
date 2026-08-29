'use client'

import { useMemo, useState } from 'react'
import { CheckCircle2, Loader2, XCircle } from 'lucide-react'

import { FlashcardItem, GradeFlashcardResponse, SrsRating } from '@/lib/types/study'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useGradeFlashcardAnswer } from '@/lib/hooks/use-study'
import { buildDueQueue } from '@/lib/utils/flashcard-queue'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'

interface GuidedFlashcardSessionProps {
  items: FlashcardItem[]
  studySetId: string
  notebookId?: string
  /** Called when the student dismisses the session-complete summary
   * ("Continuar") - the parent decides where that takes them (e.g. back to
   * quick mode / the study set overview). */
  onSessionComplete?: () => void
}

/** Matches api/study_service.py::StudyService.MAX_GRADING_ATTEMPTS. */
const MAX_ATTEMPTS = 3

const MASTERED_RATINGS: SrsRating[] = ['easy', 'good']

interface CardResult {
  front: string
  rating: SrsRating
}

export function GuidedFlashcardSession({
  items,
  studySetId,
  notebookId,
  onSessionComplete,
}: GuidedFlashcardSessionProps) {
  const { t } = useTranslation()
  const gradeAnswer = useGradeFlashcardAnswer(studySetId, notebookId)

  // Built once per study set - a session works through what's due right now,
  // not a moving target as reviews change due dates mid-session.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const dueQueue = useMemo(() => buildDueQueue(items), [studySetId])

  const [position, setPosition] = useState(0)
  const [attempt, setAttempt] = useState(1)
  const [answer, setAnswer] = useState('')
  const [lastResult, setLastResult] = useState<GradeFlashcardResponse | null>(null)
  // Feedback from the previous (failed) attempt on the SAME card, shown as a
  // hint above the input on retry. Separate from `lastResult` because
  // `lastResult` is cleared to flip back to the answering view.
  const [hint, setHint] = useState<string | null>(null)
  const [results, setResults] = useState<CardResult[]>([])

  const sessionDone = position >= dueQueue.length
  const originalIndex = !sessionDone ? dueQueue[position] : undefined
  const card = originalIndex !== undefined ? items[originalIndex] : undefined

  const handleSubmit = () => {
    if (originalIndex === undefined || !answer.trim()) return
    gradeAnswer.mutate(
      { itemIndex: originalIndex, answer, attempt },
      { onSuccess: (response) => setLastResult(response) }
    )
  }

  const advance = (rating: SrsRating) => {
    if (card) {
      setResults((prev) => [...prev, { front: card.front, rating }])
    }
    setPosition((prev) => prev + 1)
    setAttempt(1)
    setAnswer('')
    setLastResult(null)
    setHint(null)
  }

  const handleNextCard = () => {
    if (!lastResult) return
    advance(lastResult.rating)
  }

  const handleRetry = () => {
    setHint(lastResult?.feedback ?? null)
    setAttempt((prev) => prev + 1)
    setAnswer('')
    setLastResult(null)
  }

  const handleContinue = () => {
    setPosition(0)
    setAttempt(1)
    setAnswer('')
    setLastResult(null)
    setHint(null)
    setResults([])
    onSessionComplete?.()
  }

  if (dueQueue.length === 0) {
    return (
      <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
        {t('study.guidedSession.noCardsDue')}
      </div>
    )
  }

  if (sessionDone) {
    const mastered = results.filter((r) => MASTERED_RATINGS.includes(r.rating))
    const struggled = results.filter((r) => !MASTERED_RATINGS.includes(r.rating))
    const allMastered = struggled.length === 0

    return (
      <div className="flex flex-col items-center gap-4 text-center">
        <CheckCircle2 className="h-10 w-10 text-fern" />
        <h2 className="font-display text-xl font-bold text-foreground">
          {t('study.guidedSession.sessionComplete')}
        </h2>
        <p className="text-sm text-muted-foreground">
          {t('study.guidedSession.sessionSummary', {
            mastered: mastered.length,
            total: results.length,
          })}
        </p>
        {allMastered ? (
          <p className="text-sm font-medium text-fern">
            {t('study.guidedSession.allMasteredMessage')}
          </p>
        ) : (
          <div className="w-full max-w-md space-y-2 text-left">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {t('study.guidedSession.needsWorkTitle')}
            </p>
            <ul className="space-y-1">
              {struggled.map((r, index) => (
                <li
                  key={index}
                  className="rounded-md border border-gold/40 bg-gold-tint px-3 py-1.5 text-sm text-foreground"
                >
                  {r.front}
                </li>
              ))}
            </ul>
          </div>
        )}
        <Button onClick={handleContinue}>{t('study.guidedSession.continueBtn')}</Button>
      </div>
    )
  }

  if (!card) return null

  const showResult = !!lastResult
  const canRetry = showResult && !lastResult.correct && !lastResult.revealed_answer
  const canAdvance = showResult && (lastResult.correct || !!lastResult.revealed_answer)

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="flex flex-wrap items-center justify-center gap-2">
        <p className="text-sm text-muted-foreground">
          {t('study.cardProgress', { current: position + 1, total: dueQueue.length })}
        </p>
        <Badge variant="outline" className="border-teal/40 text-teal">
          {t('study.guidedSession.attemptLabel', { current: attempt, max: MAX_ATTEMPTS })}
        </Badge>
      </div>

      <Card className="w-full max-w-xl">
        <CardContent className="space-y-4 p-6">
          <p className="text-center text-lg font-medium text-foreground">{card.front}</p>

          {!showResult ? (
            <div className="space-y-3">
              {hint ? (
                <p className="rounded-md border border-gold/40 bg-gold-tint px-3 py-2 text-xs text-foreground">
                  <span className="font-semibold">{t('study.guidedSession.hintLabel')}:</span>{' '}
                  {hint}
                </p>
              ) : null}
              <Textarea
                value={answer}
                onChange={(event) => setAnswer(event.target.value)}
                placeholder={t('study.guidedSession.answerPlaceholder')}
                rows={4}
                disabled={gradeAnswer.isPending}
              />
              <div className="flex justify-end">
                <Button
                  onClick={handleSubmit}
                  disabled={gradeAnswer.isPending || !answer.trim()}
                >
                  {gradeAnswer.isPending ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      {t('study.guidedSession.grading')}
                    </>
                  ) : (
                    t('study.guidedSession.submitAnswer')
                  )}
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <div
                className={cn(
                  'flex items-center gap-2 rounded-md border px-3 py-2 text-sm font-medium',
                  lastResult.correct
                    ? 'border-fern/40 bg-fern-tint text-fern'
                    : 'border-destructive/40 bg-destructive-tint text-destructive'
                )}
              >
                {lastResult.correct ? (
                  <CheckCircle2 className="h-4 w-4 shrink-0" />
                ) : (
                  <XCircle className="h-4 w-4 shrink-0" />
                )}
                {lastResult.correct
                  ? t('study.guidedSession.correctLabel')
                  : t('study.guidedSession.incorrectLabel')}
              </div>
              <p className="text-sm text-foreground">{lastResult.feedback}</p>
              {lastResult.revealed_answer ? (
                <p className="rounded-md border bg-muted/50 px-3 py-2 text-sm text-foreground">
                  <span className="font-semibold">
                    {t('study.guidedSession.revealedAnswerLabel')}:
                  </span>{' '}
                  {lastResult.revealed_answer}
                </p>
              ) : null}
              <div className="flex justify-end gap-2">
                {canRetry ? (
                  <Button variant="outline" onClick={handleRetry}>
                    {t('study.guidedSession.tryAgainBtn')}
                  </Button>
                ) : null}
                {canAdvance ? (
                  <Button onClick={handleNextCard}>
                    {t('study.guidedSession.nextCard')}
                  </Button>
                ) : null}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
