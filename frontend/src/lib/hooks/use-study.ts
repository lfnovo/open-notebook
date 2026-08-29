import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { studyApi } from '@/lib/api/study'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { useToast } from '@/lib/hooks/use-toast'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getApiErrorKey } from '@/lib/utils/error-handler'
import {
  FlashcardItem,
  GenerateStudySetRequest,
  isStudyJobActive,
  SrsRating,
  StudyKind,
  StudySet,
} from '@/lib/types/study'

export function useStudySetsForNotebook(notebookId: string | undefined) {
  const query = useQuery({
    queryKey: QUERY_KEYS.studySetsForNotebook(notebookId ?? ''),
    queryFn: () => studyApi.listForNotebook(notebookId as string),
    enabled: !!notebookId,
  })

  return { ...query, studySets: query.data ?? [] }
}

export function useStudySet(studySetId: string | undefined) {
  return useQuery({
    queryKey: QUERY_KEYS.studySet(studySetId ?? ''),
    queryFn: () => studyApi.get(studySetId as string),
    enabled: !!studySetId,
  })
}

/**
 * Polls GET /study/jobs/{job_id} while a flashcards/quiz generation is in
 * flight. Unlike podcast episodes, the StudySet row is only created once
 * generation succeeds (see StudyService docstring), so this is the only way
 * to observe progress/failure before that row exists. Mirrors the podcast
 * job endpoint's polling shape: active only while status is
 * pending/submitted/running/processing, stops once it resolves.
 */
export function useStudyJobStatus(jobId: string | undefined) {
  return useQuery({
    queryKey: QUERY_KEYS.studyJob(jobId ?? ''),
    queryFn: () => studyApi.getJobStatus(jobId as string),
    enabled: !!jobId,
    refetchInterval: (query) => (isStudyJobActive(query.state.data?.status) ? 3000 : false),
    // TanStack Query pauses interval refetching once the tab isn't visible/
    // focused by default. Generation can take long enough that a student
    // switches tabs while waiting - without this, polling silently stops and
    // GenerateStudySetDialog gets stuck even after the job finishes. Same fix
    // as AskAcrossSourcesDialog's identical useQuery.
    refetchIntervalInBackground: true,
  })
}

function useGenerateStudySet(kind: StudyKind) {
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (payload: GenerateStudySetRequest) =>
      kind === 'flashcards'
        ? studyApi.generateFlashcards(payload)
        : studyApi.generateQuiz(payload),
    onSuccess: (response) => {
      toast({
        title: t('study.generationStarted'),
        description: t('study.generationSubmittedDesc', { name: response.name }),
      })
    },
    onError: (error: unknown) => {
      toast({
        title: t('study.generationFailed'),
        description: getApiErrorKey(error, t('common.error')),
        variant: 'destructive',
      })
    },
  })
}

export function useGenerateFlashcards() {
  return useGenerateStudySet('flashcards')
}

export function useGenerateQuiz() {
  return useGenerateStudySet('quiz')
}

/**
 * Records a self-graded recall outcome for one flashcard (retrieval
 * practice) and updates its spaced-repetition due date. Optimistically
 * patches the cached study set so the viewer's due-count updates instantly;
 * also invalidates the notebook's list query (scoped like
 * useDeleteStudySet) so the /study list page's due badges stay in sync.
 */
export function useReviewFlashcard(studySetId: string, notebookId?: string) {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: ({ itemIndex, rating }: { itemIndex: number; rating: SrsRating }) =>
      studyApi.reviewFlashcard(studySetId, itemIndex, rating),
    onSuccess: (response) => {
      queryClient.setQueryData<StudySet>(QUERY_KEYS.studySet(studySetId), (prev) => {
        if (!prev) return prev
        const items = [...(prev.items as FlashcardItem[])]
        items[response.item_index] = response.item
        return { ...prev, items, due_count: response.due_count }
      })
      if (notebookId) {
        queryClient.invalidateQueries({ queryKey: QUERY_KEYS.studySetsForNotebook(notebookId) })
      }
    },
    onError: (error: unknown) => {
      toast({
        title: t('study.reviewFailed'),
        description: getApiErrorKey(error, t('common.error')),
        variant: 'destructive',
      })
    },
  })
}

/**
 * AI-grades a student's free-text answer to one flashcard (guided study mode
 * - "Modo guiado con IA") and records the resulting spaced-repetition
 * rating. Same cache-patching shape as useReviewFlashcard (this endpoint
 * also returns the updated item + due_count) - no success toast, since the
 * component shows the AI's feedback inline instead.
 */
export function useGradeFlashcardAnswer(studySetId: string, notebookId?: string) {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: ({ itemIndex, answer, attempt }: { itemIndex: number; answer: string; attempt: number }) =>
      studyApi.gradeFlashcardAnswer(studySetId, itemIndex, answer, attempt),
    onSuccess: (response, variables) => {
      queryClient.setQueryData<StudySet>(QUERY_KEYS.studySet(studySetId), (prev) => {
        if (!prev) return prev
        const items = [...(prev.items as FlashcardItem[])]
        items[variables.itemIndex] = response.item
        return { ...prev, items, due_count: response.due_count }
      })
      if (notebookId) {
        queryClient.invalidateQueries({ queryKey: QUERY_KEYS.studySetsForNotebook(notebookId) })
      }
    },
    onError: (error: unknown) => {
      toast({
        title: t('study.guidedSession.gradeFailed'),
        description: getApiErrorKey(error, t('common.error')),
        variant: 'destructive',
      })
    },
  })
}

/**
 * `notebookId` scopes cache invalidation to a single notebook's study set
 * list (e.g. the detail page, which knows its own notebook). Omit it (e.g.
 * the cross-notebook list page) to invalidate every notebook's study set
 * list query instead.
 */
export function useDeleteStudySet(notebookId?: string) {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (studySetId: string) => studyApi.delete(studySetId),
    onSuccess: () => {
      if (notebookId) {
        queryClient.invalidateQueries({ queryKey: QUERY_KEYS.studySetsForNotebook(notebookId) })
      } else {
        queryClient.invalidateQueries({
          predicate: (query) =>
            query.queryKey[0] === 'study' && query.queryKey[1] === 'notebook',
        })
      }
      toast({
        title: t('study.deleteSuccess'),
      })
    },
    onError: (error: unknown) => {
      toast({
        title: t('study.deleteFailed'),
        description: getApiErrorKey(error, t('common.error')),
        variant: 'destructive',
      })
    },
  })
}
