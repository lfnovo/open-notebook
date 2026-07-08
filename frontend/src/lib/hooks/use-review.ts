import { useMutation, useQuery } from '@tanstack/react-query'
import { reviewsApi, CreateReviewRequest } from '@/lib/api/reviews'
import { notesApi } from '@/lib/api/notes'

const TERMINAL = new Set(['completed', 'failed'])

/** Start a repo review. Returns the created (queued) Review record. */
export function useCreateReview() {
  return useMutation({
    mutationFn: (data: CreateReviewRequest) => reviewsApi.create(data),
  })
}

/**
 * Poll a review until it reaches a terminal state. A repo review runs many LLM
 * calls over minutes, so we poll every few seconds while it's queued/running and
 * stop once it's completed/failed.
 */
export function useReviewStatus(reviewId: string | null) {
  return useQuery({
    queryKey: ['review', reviewId],
    queryFn: () => reviewsApi.get(reviewId as string),
    enabled: !!reviewId,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (status && TERMINAL.has(status)) return false
      return 3000
    },
  })
}

/** Fetch the AI Note holding the finished report, once available. */
export function useReviewReport(noteId: string | null | undefined) {
  return useQuery({
    queryKey: ['note', noteId],
    queryFn: () => notesApi.get(noteId as string),
    enabled: !!noteId,
  })
}

/** Roots the backend is allowed to scan — powers the repo-path folder picker. */
export function useReviewConfig() {
  return useQuery({
    queryKey: ['review-config'],
    queryFn: () => reviewsApi.getConfig(),
  })
}

/** Distinct repo paths used in past reviews, newest first — powers the "recent paths" combobox. */
export function useRecentReviewPaths() {
  return useQuery({
    queryKey: ['review-recent-paths'],
    queryFn: () => reviewsApi.getRecentPaths(),
  })
}
