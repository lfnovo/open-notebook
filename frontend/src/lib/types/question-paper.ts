export type QuestionDifficulty = 'easy' | 'medium' | 'hard'
export type QuestionType = 'mcq' | 'short' | 'scenario' | 'calculation' | 'definition'
export type PaperStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface SectionConfig {
  [sectionType: string]: number
}

export interface GeneratePaperRequest {
  topic: string
  difficulty: QuestionDifficulty
  target_marks: number
  section_config: SectionConfig
  curriculum_objectives?: string[]
  generator_model?: string | null
  reviewer_model?: string | null
  book_id?: string | null
  selected_chapters?: number[] | null
}

export interface GeneratePaperResponse {
  job_id: string
  paper_id: string
  status: string
  message: string
  topic: string
}

export interface PaperSummary {
  paper_id: string
  topic: string
  difficulty: QuestionDifficulty
  target_marks: number
  section_config: SectionConfig
  status: PaperStatus
  error_message?: string | null
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
  created: string
}

export interface PaperQuestion {
  question_number: number
  question: string
  type: QuestionType
  options?: string[] | null
  marks: number
  topic: string
  difficulty: QuestionDifficulty
}

export interface PaperSection {
  section_name: string
  questions: PaperQuestion[]
}

export interface FinalPaper {
  sections: PaperSection[]
  total_marks: number
  question_count: number
}

export interface AnswerKeyItem {
  question_number: number
  question: string
  answer: string
  explanation: string
  marks: number
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
  created: string
}

export interface BookChapter {
  index: number
  title: string
  preview: string
  char_count: number
}

export interface BookUploadResponse {
  book_id: string
  title: string
  total_chars: number
  chapters: BookChapter[]
}

export interface BankQuestion {
  id: string
  question: string
  topic: string
  type: QuestionType
  difficulty: QuestionDifficulty
  answer: string
}
