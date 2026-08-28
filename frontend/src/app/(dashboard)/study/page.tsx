'use client'

import { useMemo, useState } from 'react'
import { useQueries } from '@tanstack/react-query'
import { AlertCircle, Loader2, RefreshCcw } from 'lucide-react'

import { AppShell } from '@/components/layout/AppShell'
import { useNotebooks } from '@/lib/hooks/use-notebooks'
import { useDeleteStudySet } from '@/lib/hooks/use-study'
import { studyApi } from '@/lib/api/study'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { StudyKind, StudySetListItem } from '@/lib/types/study'
import { useTranslation } from '@/lib/hooks/use-translation'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { StudySetCard } from '@/components/study/StudySetCard'
import { GenerateStudySetDialog } from '@/components/study/GenerateStudySetDialog'

interface FlatStudySet {
  studySet: StudySetListItem
  notebookName: string
}

export default function StudyPage() {
  const { t } = useTranslation()
  const [showGenerateDialog, setShowGenerateDialog] = useState(false)
  const [filter, setFilter] = useState<'all' | StudyKind>('all')

  const notebooksQuery = useNotebooks()
  const notebooks = useMemo(() => notebooksQuery.data ?? [], [notebooksQuery.data])

  const studySetQueries = useQueries({
    queries: notebooks.map((notebook) => ({
      queryKey: QUERY_KEYS.studySetsForNotebook(notebook.id),
      queryFn: () => studyApi.listForNotebook(notebook.id),
    })),
  })

  const deleteStudySet = useDeleteStudySet()

  const isLoading = notebooksQuery.isLoading || studySetQueries.some((q) => q.isLoading)
  const isFetching = notebooksQuery.isFetching || studySetQueries.some((q) => q.isFetching)
  const isError = notebooksQuery.isError || studySetQueries.some((q) => q.isError)

  const allStudySets = useMemo<FlatStudySet[]>(() => {
    const flat: FlatStudySet[] = []
    notebooks.forEach((notebook, index) => {
      const sets = studySetQueries[index]?.data ?? []
      sets.forEach((studySet) => {
        flat.push({ studySet, notebookName: notebook.name })
      })
    })
    return flat.sort((a, b) => {
      const aTime = a.studySet.created ? new Date(a.studySet.created).getTime() : 0
      const bTime = b.studySet.created ? new Date(b.studySet.created).getTime() : 0
      return bTime - aTime
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [notebooks, studySetQueries.map((q) => q.dataUpdatedAt).join(',')])

  const filteredStudySets = useMemo(
    () => (filter === 'all' ? allStudySets : allStudySets.filter((s) => s.studySet.kind === filter)),
    [allStudySets, filter]
  )

  const handleRefresh = () => {
    notebooksQuery.refetch()
    studySetQueries.forEach((q) => q.refetch())
  }

  const emptyState = !isLoading && allStudySets.length === 0

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto">
        <div className="px-6 py-6 space-y-6">
          <header className="flex flex-wrap items-center justify-between gap-3">
            <div className="space-y-1">
              <h1 className="font-display text-2xl font-bold tracking-tight">{t('study.listTitle')}</h1>
              <p className="text-muted-foreground">{t('study.listDesc')}</p>
            </div>
            <div className="flex items-center gap-2">
              <Button onClick={() => setShowGenerateDialog(true)}>{t('study.generateBtn')}</Button>
              <Button variant="outline" size="sm" onClick={handleRefresh} disabled={isFetching}>
                {isFetching ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCcw className="h-4 w-4" />
                )}
                {t('common.refresh')}
              </Button>
            </div>
          </header>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <Tabs value={filter} onValueChange={(value) => setFilter(value as 'all' | StudyKind)}>
              <TabsList>
                <TabsTrigger value="all">{t('study.filterAll')}</TabsTrigger>
                <TabsTrigger value="flashcards">{t('study.kindFlashcards')}</TabsTrigger>
                <TabsTrigger value="quiz">{t('study.kindQuiz')}</TabsTrigger>
              </TabsList>
            </Tabs>
            <Badge variant="outline" className="font-medium">
              <span className="text-muted-foreground mr-1.5">{t('study.total')}</span>
              <span className="font-mono text-foreground">{allStudySets.length}</span>
            </Badge>
          </div>

          {isError ? (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>{t('study.loadErrorTitle')}</AlertTitle>
              <AlertDescription>{t('study.loadErrorDesc')}</AlertDescription>
            </Alert>
          ) : null}

          {isLoading ? (
            <div className="flex items-center gap-3 rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              {t('study.loadingSets')}
            </div>
          ) : null}

          {emptyState ? (
            <div className="rounded-md border border-dashed p-10 text-center">
              <p className="text-sm text-muted-foreground">{t('study.noSetsYetDesc')}</p>
            </div>
          ) : null}

          <div className="space-y-4">
            {filteredStudySets.map(({ studySet, notebookName }) => (
              <StudySetCard
                key={studySet.id}
                studySet={studySet}
                notebookName={notebookName}
                onDelete={(id) => deleteStudySet.mutate(id)}
                deleting={deleteStudySet.isPending}
              />
            ))}
          </div>

          <GenerateStudySetDialog open={showGenerateDialog} onOpenChange={setShowGenerateDialog} />
        </div>
      </div>
    </AppShell>
  )
}
