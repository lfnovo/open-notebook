import type { ChatImage } from './api'

export type ExamQuestionType = 'multiple_choice' | 'multiple_select' | 'fill_blank' | 'open'
export type ExamDifficulty = 'easy' | 'medium' | 'hard'

export interface ExamQuestion {
  id: string
  type: ExamQuestionType
  prompt: string
  points: number
  options: string[]
  image_ids?: string[]
  blank_count: number
  // Answer key: only present when requested with include_answers
  correct_option?: number | null
  correct_options?: number[] | null
  blanks?: string[][] | null
  reference_answer?: string | null
  rubric?: string | null
  explanation?: string | null
}

export interface Exam {
  id: string
  notebook_id: string
  title: string
  difficulty: ExamDifficulty
  language?: string | null
  instructions?: string | null
  source_ids: string[]
  images?: Record<string, ChatImage>
  question_count: number
  max_score: number
  attempt_count: number
  best_score?: number | null
  questions?: ExamQuestion[] | null
  created: string
  updated: string
}

export interface CreateExamRequest {
  notebook_id: string
  title?: string
  source_ids?: string[]
  include_notes: boolean
  include_images?: boolean
  num_multiple_choice: number
  num_multiple_select: number
  num_fill_blank: number
  num_open: number
  difficulty: ExamDifficulty
  language?: string
  instructions?: string
  model_id?: string
}

/**
 * multiple_choice: option index · multiple_select: option indexes ·
 * fill_blank: one string per blank · open: text
 */
export type ExamAnswer = number | number[] | string[] | string | null
export type ExamAnswers = Record<string, ExamAnswer>

export interface ExamQuestionResult {
  question_id: string
  score: number
  max_score: number
  is_correct: boolean
  graded_by: 'auto' | 'ai'
  feedback?: string | null
}

export interface ExamAttempt {
  id: string
  exam_id: string
  answers: ExamAnswers
  results: ExamQuestionResult[]
  score: number
  max_score: number
  created: string
}
