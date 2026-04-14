'use client'

import { useState } from 'react'
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
import { AlertCircle, CheckCircle2, Download, BookOpen } from 'lucide-react'
import type { PaperResult, PaperSection, AnswerKeyItem } from '@/lib/types/question-paper'

interface PaperResultProps {
  result: PaperResult
}

function DifficultyBadge({ difficulty }: { difficulty: string }) {
  const variant =
    difficulty === 'easy'
      ? 'secondary'
      : difficulty === 'hard'
        ? 'destructive'
        : 'default'
  return (
    <Badge variant={variant} className="capitalize text-xs">
      {difficulty}
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
              <div key={qi} className="space-y-1">
                <div className="flex items-start gap-2">
                  <span className="font-medium text-sm shrink-0 mt-0.5">
                    {q.question_number}.
                  </span>
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
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <DifficultyBadge difficulty={q.difficulty} />
                    <Badge variant="outline" className="text-xs">
                      {q.marks}m
                    </Badge>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

function AnswerKeyView({ answerKey }: { answerKey: AnswerKeyItem[] }) {
  const { t } = useTranslation()
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

export function PaperResultView({ result }: PaperResultProps) {
  const { t } = useTranslation()
  const hasGaps = result.coverage_gaps && result.coverage_gaps.length > 0
  const hasCoverage = (result.covered_topics?.length ?? 0) > 0 || hasGaps
  const sections = result.final_paper?.sections ?? []

  const handleDownload = () => {
    const lines: string[] = []
    lines.push(`QUESTION PAPER — ${result.topic.toUpperCase()}`)
    lines.push(`Difficulty: ${result.difficulty} | Total Marks: ${result.target_marks}`)
    lines.push('='.repeat(60))
    lines.push('')

    for (const section of sections) {
      lines.push(`SECTION: ${section.section_name.toUpperCase()}`)
      lines.push('-'.repeat(40))
      for (const q of section.questions) {
        lines.push(`${q.question_number}. ${q.question} [${q.marks} mark(s)]`)
        if (q.options) {
          q.options.forEach((opt, i) =>
            lines.push(`   ${String.fromCharCode(65 + i)}. ${opt}`)
          )
        }
        lines.push('')
      }
    }

    lines.push('='.repeat(60))
    lines.push('ANSWER KEY')
    lines.push('='.repeat(60))
    for (const item of result.answer_key) {
      lines.push(`${item.question_number}. ${item.answer}`)
      if (item.explanation) lines.push(`   Explanation: ${item.explanation}`)
      lines.push('')
    }

    const blob = new Blob([lines.join('\n')], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `question-paper-${result.topic.toLowerCase().replace(/\s+/g, '-')}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-lg font-semibold">{result.topic}</h2>
          <div className="flex items-center gap-2 mt-1">
            <DifficultyBadge difficulty={result.difficulty} />
            <span className="text-sm text-muted-foreground">
              {result.final_paper?.total_marks ?? result.target_marks} {t.questionPaper.marks} ·{' '}
              {result.final_paper?.question_count ?? 0} {t.questionPaper.questions}
            </span>
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={handleDownload}>
          <Download className="h-4 w-4 mr-1" />
          {t.questionPaper.download}
        </Button>
      </div>

      {/* Coverage Report */}
      {(result.covered_topics?.length > 0 || hasGaps) && (
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

      {/* Tabs: Paper / Answer Key */}
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
