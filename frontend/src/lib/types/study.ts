export type StudyKind = 'flashcards' | 'quiz'

export type StudyJobStatus =
  | 'running'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'error'
  | 'pending'
  | 'submitted'
  | 'unknown'

export const ACTIVE_STUDY_JOB_STATUSES: StudyJobStatus[] = [
  'running',
  'processing',
  'pending',
  'submitted',
]

export const FAILED_STUDY_JOB_STATUSES: StudyJobStatus[] = ['failed', 'error']

export interface FlashcardItem {
  front: string
  back: string
}

export interface QuizItem {
  question: string
  options: string[]
  correct_index: number
  explanation?: string | null
}

/** Matches api/models.py StudySetResponse (GET /api/study/{id}). */
export interface StudySet {
  id: string
  notebook: string
  kind: StudyKind
  name: string
  items: FlashcardItem[] | QuizItem[]
  model_id?: string | null
  created?: string | null
  updated?: string | null
  job_status?: StudyJobStatus | null
  error_message?: string | null
}

/** Matches api/models.py StudySetListResponse (GET /api/notebooks/{id}/study). */
export interface StudySetListItem {
  id: string
  notebook: string
  kind: StudyKind
  name: string
  item_count: number
  model_id?: string | null
  created?: string | null
  updated?: string | null
  job_status?: StudyJobStatus | null
  error_message?: string | null
}

export interface GenerateStudySetRequest {
  notebook_id: string
  name: string
  item_count: number
  model_id?: string
}

/** Matches api/models.py StudySetGenerationResponse. */
export interface StudySetGenerationResponse {
  job_id: string
  status: string
  message: string
  notebook_id: string
  name: string
}

/** Mirrors PodcastJobStatus's shape - see StudyService.get_job_status. */
export interface StudyJobStatusResponse {
  job_id: string
  status: string
  result?: { study_set_id?: string; item_count?: number; error_message?: string } | null
  error_message?: string | null
  created?: string | null
  updated?: string | null
  progress?: unknown
}

export function isStudyJobActive(status?: string | null): boolean {
  return !!status && (ACTIVE_STUDY_JOB_STATUSES as string[]).includes(status)
}

export function isFlashcardItem(item: FlashcardItem | QuizItem): item is FlashcardItem {
  return 'front' in item
}

export function isQuizItem(item: FlashcardItem | QuizItem): item is QuizItem {
  return 'question' in item
}
