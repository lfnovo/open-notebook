'use client'

import { useRef, useState } from 'react'
import { useChatQuiz, useSubmitChatQuiz } from '@/lib/hooks/use-chat-quiz'
import { useTranslation } from '@/lib/hooks/use-translation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { QuestionInput } from '@/app/(dashboard)/exams/components/QuestionInput'
import { ExamQuestionImages } from '@/app/(dashboard)/exams/components/ExamQuestionImages'
import { ExamResults } from '@/app/(dashboard)/exams/components/ExamResults'
import type { ExamAnswers, ExamQuestion } from '@/lib/types/exams'

function answered(question: ExamQuestion, answers: ExamAnswers) {
  const value = answers[question.id]
  if (question.type === 'multiple_choice') return typeof value === 'number'
  if (question.type === 'multiple_select') return Array.isArray(value) && value.length > 0
  if (question.type === 'fill_blank') return Array.isArray(value) && value.length === question.blank_count && value.every(item => String(item).trim())
  return typeof value === 'string' && !!value.trim()
}

export function InlineChatQuiz({ id }: { id: string }) {
  const { t } = useTranslation()
  const query = useChatQuiz(id)
  const submit = useSubmitChatQuiz(id)
  const [answers, setAnswers] = useState<ExamAnswers>({})
  const [retaking, setRetaking] = useState(false)
  const sending = useRef(false)
  const quiz = query.data
  if (query.isLoading) return <p role="status" className="text-sm text-muted-foreground">{t('common.loading')}</p>
  if (!quiz) return <div className="space-y-2"><p className="text-sm text-destructive">{t('chat.quizUnavailable')}</p><Button variant="outline" size="sm" onClick={() => query.refetch()}>{t('common.retry')}</Button></div>
  const result = !retaking ? quiz.latest_attempt : null
  const completed = quiz.questions.every(question => answered(question, answers))
  const handleSubmit = async () => {
    if (!completed || sending.current || submit.isPending) return
    sending.current = true
    try { await submit.mutateAsync(answers); setRetaking(false) } catch { /* Hook shows the error; retain answers. */ }
    finally { sending.current = false }
  }
  return <Card className="my-3 min-w-0" data-chat-quiz={id}>
    <CardHeader className="pb-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-teal">{t('chat.inlineQuiz')}</p>
      <CardTitle className="text-base">{quiz.title}</CardTitle>
    </CardHeader>
    <CardContent className="space-y-4">
      {result ? <>
        <ExamResults attempt={result} questions={quiz.review_questions ?? quiz.questions} images={quiz.images} />
        <Button variant="outline" onClick={() => { setAnswers({}); setRetaking(true) }}>{t('exams.retake')}</Button>
      </> : <>
        {quiz.questions.map((question, index) => <section key={question.id} className="space-y-3 border-t pt-3">
          <p className="text-xs text-muted-foreground">{t('exams.questionN', { n: index + 1 })}</p>
          {question.type !== 'fill_blank' && <p className="text-sm font-medium whitespace-pre-wrap">{question.prompt}</p>}
          <ExamQuestionImages question={question} images={quiz.images} />
          <QuestionInput question={question} value={answers[question.id]} disabled={submit.isPending} onChange={value => setAnswers(previous => ({ ...previous, [question.id]: value }))} />
        </section>)}
        <Button disabled={!completed || submit.isPending} onClick={handleSubmit}>{submit.isPending ? t('exams.grading') : t('exams.submit')}</Button>
      </>}
    </CardContent>
  </Card>
}
