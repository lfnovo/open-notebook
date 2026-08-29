'use client'

import Link from 'next/link'
import { formatDistanceToNow } from 'date-fns'
import { AlertTriangle, GraduationCap, ListChecks, Trash2 } from 'lucide-react'

import { getDateLocale } from '@/lib/utils/date-locale'
import { FAILED_STUDY_JOB_STATUSES, StudySetListItem } from '@/lib/types/study'
import { useTranslation } from '@/lib/hooks/use-translation'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
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

interface StudySetCardProps {
  studySet: StudySetListItem
  notebookName: string
  onDelete: (studySetId: string) => void
  deleting?: boolean
}

export function StudySetCard({ studySet, notebookName, onDelete, deleting }: StudySetCardProps) {
  const { t, language } = useTranslation()

  const distance = studySet.created
    ? formatDistanceToNow(new Date(studySet.created), {
        addSuffix: true,
        locale: getDateLocale(language),
      })
    : null

  const isFailed = FAILED_STUDY_JOB_STATUSES.includes(
    studySet.job_status as (typeof FAILED_STUDY_JOB_STATUSES)[number]
  )

  return (
    <Card>
      <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            {studySet.kind === 'flashcards' ? (
              <GraduationCap className="h-4 w-4 text-gold" />
            ) : (
              <ListChecks className="h-4 w-4 text-mauve" />
            )}
            <h3 className="truncate text-base font-semibold text-foreground">{studySet.name}</h3>
            <Badge variant="outline" className="uppercase tracking-wide text-xs">
              {studySet.kind === 'flashcards' ? t('study.kindFlashcards') : t('study.kindQuiz')}
            </Badge>
            {isFailed ? (
              <Badge
                variant="outline"
                className="bg-destructive-tint text-destructive border-destructive/30"
              >
                <AlertTriangle className="h-3 w-3" />
                {t('study.failedLabel')}
              </Badge>
            ) : null}
            {!isFailed && (studySet.due_count ?? 0) > 0 ? (
              <Badge variant="outline" className="border-teal/40 text-teal">
                {t('study.dueCount', { count: studySet.due_count })}
              </Badge>
            ) : null}
          </div>
          <p className="text-xs text-muted-foreground">
            {notebookName} • {t('study.itemsCount', { count: studySet.item_count })}
            {distance ? ` • ${distance}` : ''}
          </p>
          {isFailed && studySet.error_message ? (
            <p className="text-xs text-destructive">{studySet.error_message}</p>
          ) : null}
        </div>
        <div className={cn('flex shrink-0 items-center gap-2')}>
          <Button variant="outline" size="sm" asChild>
            <Link href={`/study/${studySet.id}`}>{t('study.view')}</Link>
          </Button>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="ghost" size="sm" className="text-destructive">
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
                <AlertDialogAction onClick={() => onDelete(studySet.id)} disabled={deleting}>
                  {t('study.deleteSet')}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </CardContent>
    </Card>
  )
}
