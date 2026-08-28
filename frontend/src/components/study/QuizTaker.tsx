'use client'

import { useMemo, useState } from 'react'
import { CheckCircle2, Download, RotateCcw, XCircle } from 'lucide-react'

import { QuizItem } from '@/lib/types/study'
import { useTranslation } from '@/lib/hooks/use-translation'
import { downloadTextFile, rowsToCsv } from '@/lib/utils/csv'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'

interface QuizTakerProps {
  items: QuizItem[]
  studySetName: string
}

function buildAnkiCsv(items: QuizItem[]): string {
  const rows = items.map((item) => {
    const optionLines = item.options.map((option, index) =>
      index === item.correct_index ? `<b>${option} &#10003;</b>` : option
    )
    const back = [
      optionLines.join('<br>'),
      item.explanation ? `<br><br>${item.explanation}` : '',
    ].join('')
    return [item.question, back]
  })
  return rowsToCsv(rows)
}

export function QuizTaker({ items, studySetName }: QuizTakerProps) {
  const { t } = useTranslation()
  const [answers, setAnswers] = useState<Record<number, number>>({})
  const [graded, setGraded] = useState(false)

  const score = useMemo(() => {
    if (!graded) return 0
    return items.reduce(
      (total, item, index) => (answers[index] === item.correct_index ? total + 1 : total),
      0
    )
  }, [answers, graded, items])

  const handleSelect = (questionIndex: number, optionIndex: number) => {
    if (graded) return
    setAnswers((prev) => ({ ...prev, [questionIndex]: optionIndex }))
  }

  const handleReset = () => {
    setAnswers({})
    setGraded(false)
  }

  const handleExport = () => {
    const csv = buildAnkiCsv(items)
    const safeName = studySetName.replace(/[^a-z0-9-_]+/gi, '_').toLowerCase() || 'quiz'
    downloadTextFile(csv, `${safeName}-anki.csv`)
  }

  if (items.length === 0) {
    return null
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {graded ? (
            <p className="text-sm font-medium text-foreground">
              {t('study.yourScore', { score, total: items.length })}
            </p>
          ) : null}
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleExport}>
            <Download className="h-4 w-4" />
            {t('study.exportAnki')}
          </Button>
          {graded ? (
            <Button variant="outline" size="sm" onClick={handleReset}>
              <RotateCcw className="h-4 w-4" />
              {t('study.reset')}
            </Button>
          ) : (
            <Button size="sm" onClick={() => setGraded(true)}>
              {t('study.grade')}
            </Button>
          )}
        </div>
      </div>

      <div className="space-y-4">
        {items.map((item, questionIndex) => {
          const selected = answers[questionIndex]
          const isCorrect = graded && selected === item.correct_index
          const isIncorrect = graded && selected !== undefined && selected !== item.correct_index

          return (
            <Card
              key={questionIndex}
              className={cn(
                graded && isCorrect && 'border-fern/40',
                graded && (isIncorrect || selected === undefined) && 'border-destructive/40'
              )}
            >
              <CardContent className="space-y-3 p-4">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-medium text-foreground">
                    {t('study.question', { current: questionIndex + 1, total: items.length })}
                    {': '}
                    {item.question}
                  </p>
                  {graded ? (
                    isCorrect ? (
                      <span className="flex shrink-0 items-center gap-1 text-xs font-medium text-fern">
                        <CheckCircle2 className="h-4 w-4" /> {t('study.correct')}
                      </span>
                    ) : (
                      <span className="flex shrink-0 items-center gap-1 text-xs font-medium text-destructive">
                        <XCircle className="h-4 w-4" /> {t('study.incorrect')}
                      </span>
                    )
                  ) : null}
                </div>

                <RadioGroup
                  value={selected !== undefined ? String(selected) : undefined}
                  onValueChange={(value) => handleSelect(questionIndex, Number(value))}
                >
                  {item.options.map((option, optionIndex) => {
                    const isThisCorrect = graded && optionIndex === item.correct_index
                    const isThisWrongSelection =
                      graded && optionIndex === selected && optionIndex !== item.correct_index

                    return (
                      <div
                        key={optionIndex}
                        className={cn(
                          'flex items-center gap-2 rounded-md border p-2 text-sm',
                          isThisCorrect && 'border-fern/40 bg-fern-tint',
                          isThisWrongSelection && 'border-destructive/40 bg-destructive-tint'
                        )}
                      >
                        <RadioGroupItem
                          value={String(optionIndex)}
                          id={`q${questionIndex}-o${optionIndex}`}
                          disabled={graded}
                        />
                        <Label
                          htmlFor={`q${questionIndex}-o${optionIndex}`}
                          className="flex-1 cursor-pointer font-normal"
                        >
                          {option}
                        </Label>
                      </div>
                    )
                  })}
                </RadioGroup>

                {graded && item.explanation ? (
                  <p className="text-xs text-muted-foreground">
                    <span className="font-semibold">{t('study.explanation')}:</span>{' '}
                    {item.explanation}
                  </p>
                ) : null}
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
