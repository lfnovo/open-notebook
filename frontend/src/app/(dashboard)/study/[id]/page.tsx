'use client'

import { useMemo } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { formatDistanceToNow } from 'date-fns'
import { AlertCircle, ArrowLeft, GraduationCap, ListChecks, Loader2, Trash2 } from 'lucide-react'

import { AppShell } from '@/components/layout/AppShell'
import { useStudySet, useDeleteStudySet } from '@/lib/hooks/use-study'
import { useModel } from '@/lib/hooks/use-models'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getDateLocale } from '@/lib/utils/date-locale'
import { FlashcardItem, QuizItem } from '@/lib/types/study'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { FlashcardViewer } from '@/components/study/FlashcardViewer'
import { QuizTaker } from '@/components/study/QuizTaker'

export default function StudySetDetailPage() {
  const { t, language } = useTranslation()
  const router = useRouter()
  const params = useParams()
  const studySetId = params?.id ? decodeURIComponent(params.id as string) : ''

  const { data: studySet, isLoading, isError } = useStudySet(studySetId)
  const { data: model } = useModel(studySet?.model_id ?? '')
  const deleteStudySet = useDeleteStudySet(studySet?.notebook)

  const distance = studySet?.created
    ? formatDistanceToNow(new Date(studySet.created), { addSuffix: true, locale: getDateLocale(language) })
    : null

  const flashcards = useMemo(
    () => (studySet?.kind === 'flashcards' ? (studySet.items as FlashcardItem[]) : []),
    [studySet]
  )
  const quizItems = useMemo(
    () => (studySet?.kind === 'quiz' ? (studySet.items as QuizItem[]) : []),
    [studySet]
  )

  const handleDelete = () => {
    if (!studySet) return
    deleteStudySet.mutate(studySet.id, {
      onSuccess: () => router.push('/study'),
    })
  }

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto">
        <div className="px-6 py-6 space-y-6 max-w-4xl mx-auto">
          <Button variant="ghost" size="sm" onClick={() => router.push('/study')} className="-ml-2">
            <ArrowLeft className="h-4 w-4" />
            {t('study.backToList')}
          </Button>

          {isLoading ? (
            <div className="flex items-center gap-3 rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              {t('study.loadingSets')}
            </div>
          ) : isError || !studySet ? (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>{t('study.notFound')}</AlertTitle>
              <AlertDescription>{t('study.notFoundDesc')}</AlertDescription>
            </Alert>
          ) : (
            <>
              <header className="flex flex-wrap items-start justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    {studySet.kind === 'flashcards' ? (
                      <GraduationCap className="h-5 w-5 text-gold" />
                    ) : (
                      <ListChecks className="h-5 w-5 text-mauve" />
                    )}
                    <h1 className="font-display text-2xl font-bold tracking-tight">{studySet.name}</h1>
                    <Badge variant="outline" className="uppercase tracking-wide text-xs">
                      {studySet.kind === 'flashcards' ? t('study.kindFlashcards') : t('study.kindQuiz')}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {distance ? t('study.createdOn', { time: distance }) : null}
                    {model ? ` • ${t('study.modelUsed')}: ${model.name}` : null}
                  </p>
                </div>

                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button variant="outline" size="sm" className="text-destructive">
                      <Trash2 className="h-4 w-4" />
                      {t('study.deleteSet')}
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>{t('study.deleteSetTitle')}</AlertDialogTitle>
                      <AlertDialogDescription>
                        {t('study.deleteSetDesc', { name: studySet.name })}
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
                      <AlertDialogAction onClick={handleDelete} disabled={deleteStudySet.isPending}>
                        {t('study.deleteSet')}
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </header>

              {studySet.kind === 'flashcards' ? (
                <FlashcardViewer
                  items={flashcards}
                  studySetId={studySet.id}
                  notebookId={studySet.notebook}
                />
              ) : (
                <QuizTaker items={quizItems} studySetName={studySet.name} />
              )}
            </>
          )}
        </div>
      </div>
    </AppShell>
  )
}
