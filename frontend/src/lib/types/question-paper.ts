export type QuestionDifficulty = 'easy' | 'medium' | 'hard' | 'difficult'
export type CognitiveDifficulty = 'easy' | 'medium' | 'difficult'
export type QuestionType = 'mcq' | 'multi_correct' | 'short' | 'scenario' | 'calculation' | 'definition'
export type AnswerType = 'single_correct' | 'multiple_correct'
export type PaperStatus = 'pending' | 'running' | 'completed' | 'failed' | 'needs_manual_review'
export type ValidationStatus = 'passed' | 'rejected' | 'needs_manual_review'

export interface SectionConfig {
  [sectionType: string]: number
}

export interface DifficultyCounts {
  easy: number
  medium: number
  difficult: number
}

export type ChapterDifficultyCounts = DifficultyCounts

export interface AnswerTypeCounts {
  single_correct: number
  multiple_correct: number
}

export interface PaperBlueprint {
  id?: string
  total_questions: number
  pass_percentage: number
  options_per_question: number
  format: string
  language?: string
  chapter_difficulty: Record<string, DifficultyCounts>
  difficulty_answer_types: Record<CognitiveDifficulty, AnswerTypeCounts>
}

export const DEFAULT_PAPER_BLUEPRINT: PaperBlueprint = {
  id: 'grade_default_50_mcq',
  total_questions: 50,
  pass_percentage: 70,
  options_per_question: 5,
  format: 'mcq',
  language: 'en',
  chapter_difficulty: {
    '1': { easy: 3, medium: 4, difficult: 2 },
    '2': { easy: 3, medium: 4, difficult: 4 },
    '3': { easy: 4, medium: 5, difficult: 5 },
    '4': { easy: 4, medium: 5, difficult: 7 },
  },
  difficulty_answer_types: {
    easy: { single_correct: 0, multiple_correct: 0 },
    medium: { single_correct: 0, multiple_correct: 0 },
    difficult: { single_correct: 0, multiple_correct: 0 },
  },
}

export interface GeneratePaperRequest {
  topic: string
  difficulty?: QuestionDifficulty
  target_marks: number
  section_config?: SectionConfig
  curriculum_objectives?: string[]
  generator_model?: string | null
  reviewer_model?: string | null
  book_id?: string | null
  selected_chapters?: number[] | null
  grade?: string | null
  subject?: string | null
  language?: string
  pass_percentage?: number
  options_per_question?: number
  question_format?: string
  blueprint?: PaperBlueprint
  max_slot_attempts?: number
  slot_concurrency?: number
}

export interface GeneratePaperResponse {
  job_id: string
  paper_id: string
  status: string
  message: string
  topic: string
}

export type BankBatchDifficulty = CognitiveDifficulty
export type BankBatchStatus =
  | 'pending'
  | 'submitted'
  | 'running'
  | 'completed'
  | 'completed_partial'
  | 'failed'
  | string

export interface GenerateBankBatchRequest {
  book_id: string
  grade: string
  subject: string
  chapter: number
  difficulty: BankBatchDifficulty
  total_questions: number
  single_correct: number
  multiple_correct: number
  language?: string
}

export interface GenerateBankBatchResponse {
  job_id: string
  batch_id: string
  status: string
  message: string
  requested: number
}

export interface BankBatchSummary {
  batch_id: string
  grade?: string | null
  book_id?: string | null
  chapter?: number | string | null
  difficulty?: string | null
  requested: number
  accepted: number
  failed?: number | null
  status: BankBatchStatus
  created: string
  error_message?: string | null
  stop_reason?: string | null
  saved_question_ids?: string[]
  subject?: string | null
}

export interface BankBatchStatusResponse {
  batch_id: string
  status: BankBatchStatus
  job_status?: string | null
  book_id?: string | null
  grade?: string | null
  subject?: string | null
  chapter?: number | null
  difficulty?: string | null
  requested?: number | null
  accepted?: number | null
  failed?: number | null
  minimum_accepted_questions?: number | null
  error_message?: string | null
  stop_reason?: string | null
  created?: string | null
}

export interface BankBatchResultResponse {
  batch_id: string
  status: BankBatchStatus
  book_id?: string | null
  grade?: string | null
  subject?: string | null
  chapter?: number | null
  difficulty?: string | null
  requested?: number | null
  accepted?: number | null
  failed?: number | null
  saved_question_ids?: string[]
  questions?: BankQuestion[]
  error_message?: string | null
  stop_reason?: string | null
  audit?: { stop_reason?: string | null } | null
}

export interface PaperSummary {
  paper_id: string
  topic: string
  difficulty: QuestionDifficulty
  target_marks: number
  section_config: SectionConfig
  status: PaperStatus
  error_message?: string | null
  grade?: string | null
  book_id?: string | null
  question_count?: number | null
  requested_questions?: number | null
  generated_questions?: number | null
  remaining_questions?: number | null
  requested_source?: string | null
  display_status?: string | null
  requested_difficulty?: DifficultyCounts | null
  generated_difficulty?: DifficultyCounts | null
  remaining_difficulty?: DifficultyCounts | null
  difficulty_mix?: string | null
  difficulty_mix_label?: string | null
  created: string
}

export interface PaperStatusResponse {
  paper_id: string
  status: PaperStatus
  job_status?: string | null
  topic: string
  difficulty: QuestionDifficulty
  target_marks: number
  error_message?: string | null
  grade?: string | null
  created: string
}

export interface DifficultyScores {
  knowledge?: number
  reasoning?: number
  context?: number
  application?: number
  interpretation?: number
  decision_making?: number
  concept_integration?: number
  distractor_quality?: number
}

export interface PaperQuestion {
  question_number: number
  question: string
  type: QuestionType
  options?: string[] | null
  correct_indices?: number[] | null
  marks: number
  topic: string
  sub_topic?: string
  difficulty: QuestionDifficulty | CognitiveDifficulty
  answer_type?: AnswerType
  grade?: string
  chapter?: number
  chapter_title?: string
  target_difficulty?: CognitiveDifficulty
  validated_cognitive_difficulty?: CognitiveDifficulty
  difficulty_score?: number
  difficulty_scores?: DifficultyScores
  validation_status?: ValidationStatus
  validation_reasons?: string[]
  generation_attempts?: number
  explanation?: string
  answer?: string
}

export interface PaperSection {
  section_name: string
  questions: PaperQuestion[]
}

export interface FinalPaper {
  sections: PaperSection[]
  total_marks: number
  question_count: number
  pass_percentage?: number
  grade?: string
  subject?: string
  failed_slots?: PaperQuestion[]
}

export interface AnswerKeyItem {
  question_number: number
  question: string
  answer: string
  explanation: string
  marks: number
}

export interface PaperAudit {
  ok: boolean
  errors: string[]
}

export interface PaperResult {
  paper_id: string
  topic: string
  difficulty: QuestionDifficulty
  target_marks: number
  section_config: SectionConfig
  final_paper: FinalPaper
  answer_key: AnswerKeyItem[]
  coverage_gaps: string[]
  covered_topics: string[]
  status: PaperStatus
  grade?: string | null
  subject?: string | null
  language?: string | null
  pass_percentage?: number | null
  blueprint?: PaperBlueprint | null
  audit?: PaperAudit | null
  failed_slots?: PaperQuestion[]
  error_message?: string | null
  requested_questions?: number | null
  generated_questions?: number | null
  remaining_questions?: number | null
  requested_source?: string | null
  display_status?: string | null
  requested_difficulty?: DifficultyCounts | null
  generated_difficulty?: DifficultyCounts | null
  remaining_difficulty?: DifficultyCounts | null
  difficulty_mix?: string | null
  difficulty_mix_label?: string | null
  created: string
}

export interface RegenerateMissingResponse {
  paper_id: string
  status: PaperStatus
  accepted_count: number
  still_failed: number
  audit?: PaperAudit | null
}

export interface BookChapter {
  index: number
  title: string
  preview?: string
  char_count?: number
}

export interface BookUploadResponse {
  book_id: string
  title: string
  total_chars: number
  chapters: BookChapter[]
  detected_grade?: string | null
  book_name?: string | null
  year?: string | null
  grade?: string | null
  subject?: string | null
  edition?: string | null
  display_name?: string | null
  chapter_count?: number
  missing_fields?: string[]
  metadata_complete?: boolean
}

export interface LibraryBook {
  book_id?: string
  book_name?: string | null
  year?: string | null
  grade?: string | null
  subject?: string | null
  edition?: string | null
  display_name: string
  title?: string | null
  detected_grade?: string | null
  chapter_count: number
  missing_fields?: string[]
  metadata_complete: boolean
  chapters?: BookChapter[]
  total_chars?: number
}

export interface BankQuestion {
  id: string
  question: string
  topic: string
  sub_topic?: string | null
  type: QuestionType | string
  difficulty: QuestionDifficulty | string
  answer: string
  explanation?: string | null
  options?: string[] | null
  correct_indices?: number[] | null
  grade?: string | null
  subject?: string | null
  chapter?: number | string | null
  chapter_title?: string | null
  answer_type?: AnswerType | string | null
  target_difficulty?: string | null
  validated_cognitive_difficulty?: string | null
  difficulty_score?: number | null
  validation_status?: ValidationStatus | string | null
  batch_id?: string | null
  book_id?: string | null
}
