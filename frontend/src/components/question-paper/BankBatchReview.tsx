'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { ArrowLeft, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { BankQuestionReview } from '@/components/question-paper/BankQuestionReview'
import {
  useBankBatchResult,
  useQuestionBooks,
} from '@/lib/hooks/use-question-paper'
import { useTranslation } from '@/lib/hooks/use-translation'
import {
  BANK_BATCH_HISTORY_PATH,
  normalizeBankQuestion,
} from '@/lib/question-paper-bank-batch'
import {
  formatAnswerType,
  formatChapterLabel,
  formatDifficulty,
  questionDifficulty,
} from '@/lib/question-paper-labels'

export function BankBatchReview({ batchId }: { batchId: string }) {
  const { t } = useTranslation()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const { data: result, isLoading, isError } = useBankBatchResult(batchId || null, !!batchId)
  const bookTitles = useQuestionBooks(
    result?.book_id ? [String(result.book_id)] : [],
  )
  const questions = useMemo(
    () => (result?.questions || []).map(normalizeBankQuestion).filter((q) => q.id || q.question),
    [result?.questions],
  )

  useEffect(() => {
    if (questions.length === 0) {
      setSelectedId(null)
      return
    }
    if (!selectedId || !questions.some((question) => question.id === selectedId)) {
      setSelectedId(questions[0].id || null)
    }
  }, [questions, selectedId])

  const selected = questions.find((question) => question.id === selectedId) || questions[0] || null
  const bookTitle = result?.book_id
    ? (bookTitles[String(result.book_id)] || String(result.book_id))
    : ''

  return (
    <div className="h-full flex flex-col">
      <div className="p-6 pb-4 border-b space-y-3">
        <Button variant="ghost" size="sm" className="-ml-2 w-fit" asChild>
          <Link href={BANK_BATCH_HISTORY_PATH}>
            <ArrowLeft className="h-4 w-4" />
            {t.questionPaper.bankReviewBack}
          </Link>
        </Button>
        <div>
          <h1 className="text-2xl font-bold">{t.questionPaper.bankReviewTitle}</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {[
              result?.grade ? `Grade ${result.grade}` : null,
              bookTitle,
              formatChapterLabel(result?.chapter),
              formatDifficulty(result?.difficulty),
              batchId,
            ].filter(Boolean).join(' · ')}
          </p>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-hidden">
        {!batchId || isError ? (
          <p className="text-sm text-destructive p-6">{t.questionPaper.bankHistoryLoadFailed}</p>
        ) : isLoading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : questions.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-16">
            {t.questionPaper.bankHistoryNoQuestions}
          </p>
        ) : (
          <div className="h-full grid grid-cols-1 lg:grid-cols-[minmax(16rem,22rem)_1fr]">
            <aside className="border-b lg:border-b-0 lg:border-r overflow-y-auto p-4 space-y-2">
              <p className="text-xs font-medium text-muted-foreground px-1">
                {t.questionPaper.bankHistoryQuestionsTitle}
              </p>
              {questions.map((question, index) => {
                const active = selected?.id === question.id
                return (
                  <button
                    key={question.id || String(index)}
                    type="button"
                    onClick={() => setSelectedId(question.id)}
                    className={`w-full text-left rounded-md border px-3 py-2 text-sm transition-colors ${
                      active ? 'border-primary bg-primary/5' : 'hover:bg-muted/50'
                    }`}
                  >
                    <p className="font-medium">
                      {t.questionPaper.bankReviewQuestionN.replace('{n}', String(index + 1))}
                    </p>
                    <p className="line-clamp-2 text-muted-foreground mt-0.5">{question.question}</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {formatAnswerType(question.type, question.answer_type)}
                      {' · '}
                      {formatDifficulty(questionDifficulty(question))}
                    </p>
                  </button>
                )
              })}
            </aside>
            <section className="overflow-y-auto p-6">
              {selected ? <BankQuestionReview question={selected} /> : null}
            </section>
          </div>
        )}
      </div>
    </div>
  )
}
