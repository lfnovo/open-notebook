'use client'

import { useState } from 'react'

import { FlashcardItem } from '@/lib/types/study'
import { useTranslation } from '@/lib/hooks/use-translation'
import { FlashcardViewer } from '@/components/study/FlashcardViewer'
import { GuidedFlashcardSession } from '@/components/study/GuidedFlashcardSession'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

interface FlashcardStudyModesProps {
  items: FlashcardItem[]
  studySetId: string
  notebookId?: string
}

type StudyMode = 'quick' | 'guided'

/** Top-level mode toggle for the flashcard study view: "Modo rápido" is the
 * existing self-graded flip-card behavior (FlashcardViewer, unchanged),
 * "Modo guiado con IA" is the new AI-graded free-answer mode
 * (GuidedFlashcardSession). */
export function FlashcardStudyModes({ items, studySetId, notebookId }: FlashcardStudyModesProps) {
  const { t } = useTranslation()
  const [mode, setMode] = useState<StudyMode>('quick')

  return (
    <Tabs value={mode} onValueChange={(value) => setMode(value as StudyMode)}>
      <TabsList>
        <TabsTrigger value="quick">{t('study.guidedSession.quickModeTab')}</TabsTrigger>
        <TabsTrigger value="guided">{t('study.guidedSession.guidedModeTab')}</TabsTrigger>
      </TabsList>
      <TabsContent value="quick" className="pt-4">
        <FlashcardViewer items={items} studySetId={studySetId} notebookId={notebookId} />
      </TabsContent>
      <TabsContent value="guided" className="pt-4">
        <GuidedFlashcardSession
          items={items}
          studySetId={studySetId}
          notebookId={notebookId}
          onSessionComplete={() => setMode('quick')}
        />
      </TabsContent>
    </Tabs>
  )
}
