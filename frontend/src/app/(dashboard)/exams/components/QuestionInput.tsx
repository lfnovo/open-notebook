'use client'

import { Fragment, useId } from 'react'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { useTranslation } from '@/lib/hooks/use-translation'
import { ExamAnswer, ExamQuestion } from '@/lib/types/exams'

export const BLANK_MARKER = '___'

/** Pad/trim a fill-in-the-blank answer to one string per blank. */
export function blankAnswers(answer: ExamAnswer | undefined, count: number): string[] {
  const values = Array.isArray(answer) ? answer.map(String) : []
  return Array.from({ length: count }, (_, i) => values[i] ?? '')
}

interface QuestionInputProps {
  question: ExamQuestion
  value: ExamAnswer | undefined
  onChange: (value: ExamAnswer) => void
  disabled?: boolean
}

export function QuestionInput({ question, value, onChange, disabled }: QuestionInputProps) {
  const { t } = useTranslation()
  const inputId = useId()

  if (question.type === 'multiple_choice') {
    return (
      <RadioGroup
        value={typeof value === 'number' ? String(value) : ''}
        onValueChange={(v) => onChange(Number(v))}
        disabled={disabled}
        className="gap-2"
      >
        {question.options.map((option, index) => {
          const id = `${inputId}-${question.id}-opt-${index}`
          return (
            <div key={id} className="flex items-start gap-3 rounded-md border p-3 has-[:checked]:border-primary">
              <RadioGroupItem value={String(index)} id={id} className="mt-0.5" />
              <Label htmlFor={id} className="font-normal leading-snug cursor-pointer">
                {option}
              </Label>
            </div>
          )
        })}
      </RadioGroup>
    )
  }

  if (question.type === 'multiple_select') {
    const selected = new Set(Array.isArray(value) ? (value as number[]) : [])
    return (
      <div className="space-y-2">
        <p className="text-sm text-muted-foreground">{t('exams.selectAllThatApply')}</p>
        {question.options.map((option, index) => {
          const id = `${inputId}-${question.id}-opt-${index}`
          return (
            <div key={id} className="flex items-start gap-3 rounded-md border p-3 has-[[data-state=checked]]:border-primary">
              <Checkbox
                id={id}
                className="mt-0.5"
                checked={selected.has(index)}
                disabled={disabled}
                onCheckedChange={(checked) => {
                  const next = new Set(selected)
                  if (checked === true) next.add(index)
                  else next.delete(index)
                  onChange(Array.from(next).sort((a, b) => a - b))
                }}
              />
              <Label htmlFor={id} className="font-normal leading-snug cursor-pointer">
                {option}
              </Label>
            </div>
          )
        })}
      </div>
    )
  }

  if (question.type === 'fill_blank') {
    const parts = question.prompt.split(BLANK_MARKER)
    const answers = blankAnswers(value, question.blank_count)
    return (
      <p className="leading-10">
        {parts.map((part, index) => (
          <Fragment key={index}>
            <span className="whitespace-pre-wrap">{part}</span>
            {index < parts.length - 1 && (
              <Input
                aria-label={t('exams.blankN', { n: index + 1 })}
                className="inline-flex h-8 w-44 mx-1 align-middle"
                value={answers[index] ?? ''}
                disabled={disabled}
                onChange={(e) => {
                  const next = [...answers]
                  next[index] = e.target.value
                  onChange(next)
                }}
              />
            )}
          </Fragment>
        ))}
      </p>
    )
  }

  return (
    <Textarea
      rows={6}
      value={typeof value === 'string' ? value : ''}
      placeholder={t('exams.openPlaceholder')}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value)}
    />
  )
}
