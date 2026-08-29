'use client'

import { useState } from 'react'
import { CheckCircle2, XCircle } from 'lucide-react'

import { QuizItem } from '@/lib/types/study'
import { useTranslation } from '@/lib/hooks/use-translation'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'

interface GuidedQuizSessionProps {
  items: QuizItem[]
  /** Called when the student dismisses the session-complete summary
   * ("Continuar") - the parent decides where that takes them (e.g. back to
   * exam mode / the study set overview). */
  onSessionComplete?: () => void
}

/** Same 3-attempt cap as the flashcard guided session (see
 * GuidedFlashcardSession.tsx's MAX_ATTEMPTS), kept as an independent
 * constant here since quiz grading is a pure client-side index comparison -
 * there's no backend constant to mirror. */
const MAX_ATTEMPTS = 3

type QuestionOutcome = 'mastered' | 'corrected' | 'struggled'

interface QuestionResult {
  question: string
  outcome: QuestionOutcome
}

export function GuidedQuizSession({ items, onSessionComplete }: GuidedQuizSessionProps) {
  const { t } = useTranslation()

  const [position, setPosition] = useState(0)
  const [attempt, setAttempt] = useState(1)
  const [selected, setSelected] = useState<number | undefined>(undefined)
  const [graded, setGraded] = useState(false)
  // Options already tried and found wrong ON THE CURRENT question - disabled
  // on retry so the student picks from what's left, rather than re-trying a
  // known-wrong option.
  const [triedWrong, setTriedWrong] = useState<number[]>([])
  const [results, setResults] = useState<QuestionResult[]>([])

  const sessionDone = position >= items.length
  const item = !sessionDone ? items[position] : undefined

  const isCorrect = graded && !!item && selected === item.correct_index
  const revealed = graded && !isCorrect && attempt >= MAX_ATTEMPTS

  const handleAnswer = () => {
    if (selected === undefined || !item) return
    setGraded(true)
  }

  const recordAndAdvance = (outcome: QuestionOutcome) => {
    if (item) {
      setResults((prev) => [...prev, { question: item.question, outcome }])
    }
    setPosition((prev) => prev + 1)
    setAttempt(1)
    setSelected(undefined)
    setGraded(false)
    setTriedWrong([])
  }

  const handleNext = () => {
    if (!graded) return
    if (isCorrect) {
      recordAndAdvance(attempt === 1 ? 'mastered' : 'corrected')
    } else {
      // Only reachable once `revealed` is true (3rd wrong attempt).
      recordAndAdvance('struggled')
    }
  }

  const handleRetry = () => {
    if (selected !== undefined) {
      setTriedWrong((prev) => [...prev, selected])
    }
    setAttempt((prev) => prev + 1)
    setSelected(undefined)
    setGraded(false)
  }

  const handleContinue = () => {
    setPosition(0)
    setAttempt(1)
    setSelected(undefined)
    setGraded(false)
    setTriedWrong([])
    setResults([])
    onSessionComplete?.()
  }

  if (items.length === 0) {
    return null
  }

  if (sessionDone) {
    const mastered = results.filter((r) => r.outcome === 'mastered')
    const corrected = results.filter((r) => r.outcome === 'corrected')
    const struggled = results.filter((r) => r.outcome === 'struggled')
    const allGood = struggled.length === 0

    return (
      <div className="flex flex-col items-center gap-4 text-center">
        <CheckCircle2 className="h-10 w-10 text-fern" />
        <h2 className="font-display text-xl font-bold text-foreground">
          {t('study.guidedSession.sessionComplete')}
        </h2>
        <p className="text-sm text-muted-foreground">
          {t('study.guidedQuizSession.sessionSummary', {
            mastered: mastered.length + corrected.length,
            total: results.length,
          })}
        </p>
        <div className="flex flex-wrap items-center justify-center gap-2">
          <Badge variant="outline" className="border-fern/40 text-fern">
            {t('study.guidedQuizSession.masteredLabel')}: {mastered.length}
          </Badge>
          <Badge variant="outline" className="border-teal/40 text-teal">
            {t('study.guidedQuizSession.correctedLabel')}: {corrected.length}
          </Badge>
          <Badge variant="outline" className="border-gold/40 text-gold">
            {t('study.guidedQuizSession.struggledLabel')}: {struggled.length}
          </Badge>
        </div>
        {allGood ? (
          <p className="text-sm font-medium text-fern">
            {t('study.guidedSession.allMasteredMessage')}
          </p>
        ) : (
          <div className="w-full max-w-md space-y-2 text-left">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {t('study.guidedQuizSession.needsWorkTitle')}
            </p>
            <ul className="space-y-1">
              {struggled.map((r, index) => (
                <li
                  key={index}
                  className="rounded-md border border-gold/40 bg-gold-tint px-3 py-1.5 text-sm text-foreground"
                >
                  {r.question}
                </li>
              ))}
            </ul>
          </div>
        )}
        <Button onClick={handleContinue}>{t('study.guidedSession.continueBtn')}</Button>
      </div>
    )
  }

  if (!item) return null

  const canRetry = graded && !isCorrect && !revealed
  const canAdvance = graded && (isCorrect || revealed)

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="flex flex-wrap items-center justify-center gap-2">
        <p className="text-sm text-muted-foreground">
          {t('study.question', { current: position + 1, total: items.length })}
        </p>
        <Badge variant="outline" className="border-teal/40 text-teal">
          {t('study.guidedSession.attemptLabel', { current: attempt, max: MAX_ATTEMPTS })}
        </Badge>
      </div>

      <Card className="w-full max-w-xl">
        <CardContent className="space-y-4 p-6">
          <p className="text-center text-lg font-medium text-foreground">{item.question}</p>

          <RadioGroup
            value={selected !== undefined ? String(selected) : undefined}
            onValueChange={(value) => !graded && setSelected(Number(value))}
          >
            {item.options.map((option, optionIndex) => {
              const isThisCorrect =
                graded && optionIndex === item.correct_index && (isCorrect || revealed)
              const isThisWrongSelection =
                graded && optionIndex === selected && optionIndex !== item.correct_index
              const isTriedWrong = triedWrong.includes(optionIndex)

              return (
                <div
                  key={optionIndex}
                  className={cn(
                    'flex items-center gap-2 rounded-md border p-2 text-sm',
                    isThisCorrect && 'border-fern/40 bg-fern-tint',
                    isThisWrongSelection && 'border-destructive/40 bg-destructive-tint',
                    isTriedWrong && 'opacity-60 line-through'
                  )}
                >
                  <RadioGroupItem
                    value={String(optionIndex)}
                    id={`guided-quiz-q${position}-o${optionIndex}`}
                    disabled={graded || isTriedWrong}
                  />
                  <Label
                    htmlFor={`guided-quiz-q${position}-o${optionIndex}`}
                    className="flex-1 cursor-pointer font-normal"
                  >
                    {option}
                  </Label>
                </div>
              )
            })}
          </RadioGroup>

          {!graded ? (
            <div className="flex justify-end">
              <Button onClick={handleAnswer} disabled={selected === undefined}>
                {t('study.guidedSession.submitAnswer')}
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              <div
                className={cn(
                  'flex items-center gap-2 rounded-md border px-3 py-2 text-sm font-medium',
                  isCorrect
                    ? 'border-fern/40 bg-fern-tint text-fern'
                    : 'border-destructive/40 bg-destructive-tint text-destructive'
                )}
              >
                {isCorrect ? (
                  <CheckCircle2 className="h-4 w-4 shrink-0" />
                ) : (
                  <XCircle className="h-4 w-4 shrink-0" />
                )}
                {isCorrect
                  ? t('study.guidedSession.correctLabel')
                  : t('study.guidedSession.incorrectLabel')}
              </div>
              {item.explanation ? (
                <p className="text-sm text-foreground">
                  <span className="font-semibold">{t('study.explanation')}:</span>{' '}
                  {item.explanation}
                </p>
              ) : null}
              {revealed ? (
                <p className="rounded-md border bg-muted/50 px-3 py-2 text-sm text-foreground">
                  <span className="font-semibold">
                    {t('study.guidedQuizSession.correctAnswerLabel')}:
                  </span>{' '}
                  {item.options[item.correct_index]}
                </p>
              ) : null}
              <div className="flex justify-end gap-2">
                {canRetry ? (
                  <Button variant="outline" onClick={handleRetry}>
                    {t('study.guidedSession.tryAgainBtn')}
                  </Button>
                ) : null}
                {canAdvance ? (
                  <Button onClick={handleNext}>
                    {t('study.guidedQuizSession.nextQuestion')}
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
