'use client'

import { useState } from 'react'

import { QuizItem } from '@/lib/types/study'
import { useTranslation } from '@/lib/hooks/use-translation'
import { QuizTaker } from '@/components/study/QuizTaker'
import { GuidedQuizSession } from '@/components/study/GuidedQuizSession'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

interface QuizStudyModesProps {
  items: QuizItem[]
  studySetName: string
}

type StudyMode = 'exam' | 'guided'

/** Top-level mode toggle for the quiz study view: "Modo examen" is the
 * existing all-questions-at-once behavior (QuizTaker, unchanged), "Modo
 * guiado" is the new question-by-question retry-until-correct mode
 * (GuidedQuizSession). Mirrors FlashcardStudyModes. */
export function QuizStudyModes({ items, studySetName }: QuizStudyModesProps) {
  const { t } = useTranslation()
  const [mode, setMode] = useState<StudyMode>('exam')

  return (
    <Tabs value={mode} onValueChange={(value) => setMode(value as StudyMode)}>
      <TabsList>
        <TabsTrigger value="exam">{t('study.guidedQuizSession.examModeTab')}</TabsTrigger>
        <TabsTrigger value="guided">{t('study.guidedQuizSession.guidedModeTab')}</TabsTrigger>
      </TabsList>
      <TabsContent value="exam" className="pt-4">
        <QuizTaker items={items} studySetName={studySetName} />
      </TabsContent>
      <TabsContent value="guided" className="pt-4">
        <GuidedQuizSession items={items} onSessionComplete={() => setMode('exam')} />
      </TabsContent>
    </Tabs>
  )
}
