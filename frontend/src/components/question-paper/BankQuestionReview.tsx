'use client'

import { Badge } from '@/components/ui/badge'
import { useTranslation } from '@/lib/hooks/use-translation'
import {
  OPTION_LETTERS,
  correctOptionIndices,
  formatAnswerType,
  formatCorrectAnswerLetters,
  formatDifficulty,
  formatValidationStatus,
  questionDifficulty,
} from '@/lib/question-paper-labels'
import type { BankQuestion } from '@/lib/types/question-paper'

function DetailRow({ label, value }: { label: string; value?: string | number | null }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="text-sm mt-0.5">{value == null || value === '' ? '—' : value}</dd>
    </div>
  )
}

export function BankQuestionReview({ question }: { question: BankQuestion }) {
  const { t } = useTranslation()
  const correct = new Set(correctOptionIndices(question))
  const options = question.options && question.options.length > 0
    ? question.options.slice(0, OPTION_LETTERS.length)
    : []
  const questionType = formatAnswerType(question.type, question.answer_type)
  const showCognitive = question.difficulty_score != null

  return (
    <div className="space-y-5 text-sm">
      <div>
        <p className="text-xs text-muted-foreground mb-1">{t.questionPaper.bankColQuestion}</p>
        <p className="whitespace-pre-wrap">{question.question || '—'}</p>
      </div>

      <div>
        <p className="text-xs text-muted-foreground mb-2">{t.questionPaper.bankReviewOptions}</p>
        {options.length > 0 ? (
          <ol className="space-y-2">
            {options.map((option, index) => {
              const letter = OPTION_LETTERS[index]
              const isCorrect = correct.has(index)
              return (
                <li
                  key={`${letter}-${index}`}
                  className={`flex items-start gap-2 rounded-md border px-3 py-2 ${
                    isCorrect
                      ? 'border-green-200 bg-green-50/70 dark:border-green-900 dark:bg-green-950/20'
                      : 'bg-background'
                  }`}
                >
                  <span className="font-medium w-5 shrink-0">{letter}.</span>
                  <span className="flex-1">{option}</span>
                  {isCorrect ? (
                    <Badge variant="secondary">{t.questionPaper.bankReviewCorrectOption}</Badge>
                  ) : null}
                </li>
              )
            })}
          </ol>
        ) : (
          <p className="text-muted-foreground">—</p>
        )}
      </div>

      <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-3">
        <DetailRow
          label={t.questionPaper.bankCorrectAnswer}
          value={formatCorrectAnswerLetters(question)}
        />
        <DetailRow label={t.questionPaper.bankQuestionType} value={questionType} />
        <DetailRow
          label={t.questionPaper.difficulty}
          value={formatDifficulty(questionDifficulty(question))}
        />
        <DetailRow
          label={t.questionPaper.validationStatus}
          value={formatValidationStatus(question.validation_status)}
        />
        {showCognitive ? (
          <DetailRow
            label={t.questionPaper.cognitiveScore}
            value={String(question.difficulty_score)}
          />
        ) : null}
      </dl>

      <div>
        <p className="text-xs text-muted-foreground mb-1">{t.questionPaper.explanation}</p>
        <p className="whitespace-pre-wrap">{question.explanation?.trim() || '—'}</p>
      </div>
    </div>
  )
}
