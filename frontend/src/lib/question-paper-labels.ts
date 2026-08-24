import type { BankQuestion, PaperStatus } from '@/lib/types/question-paper'

const OPTION_LETTERS = ['A', 'B', 'C', 'D', 'E'] as const

export function formatDifficulty(value?: string | null): string {
  const raw = (value || '').toLowerCase()
  if (raw === 'hard' || raw === 'difficult') return 'Difficult'
  if (raw === 'easy') return 'Easy'
  if (raw === 'medium') return 'Medium'
  return value ? value : '—'
}

export function difficultyKey(value?: string | null): 'easy' | 'medium' | 'difficult' | '' {
  const raw = (value || '').toLowerCase()
  if (raw === 'easy') return 'easy'
  if (raw === 'medium') return 'medium'
  if (raw === 'hard' || raw === 'difficult') return 'difficult'
  return ''
}

export const SINGLE_CORRECT = 'Single Correct'
export const MULTIPLE_CORRECT = 'Multiple Correct'
export const OTHER_LEGACY = 'Other / Legacy'

export function formatAnswerType(type?: string | null, answerType?: string | null): string {
  const raw = `${answerType || ''} ${type || ''}`.toLowerCase()
  if (
    raw.includes('multi_correct') ||
    raw.includes('multiple_correct') ||
    raw.includes('multi-correct')
  ) {
    return MULTIPLE_CORRECT
  }
  if (raw.includes('mcq') || raw.includes('single_correct') || raw.includes('single-correct')) {
    return SINGLE_CORRECT
  }
  if (type || answerType) return OTHER_LEGACY
  return '—'
}

export function formatValidationStatus(status?: string | null): string {
  const raw = (status || '').toLowerCase()
  if (raw === 'passed') return 'Passed'
  if (raw === 'rejected') return 'Rejected'
  if (raw === 'needs_manual_review') return 'Needs Review'
  if (!status) return '—'
  return status
}

export function formatPaperStatus(status: PaperStatus | string): string {
  switch (status) {
    case 'completed':
      return 'Completed'
    case 'partial':
    case 'completed_partial':
      return 'Partial'
    case 'needs_manual_review':
      return 'Needs Review'
    case 'failed':
      return 'Failed'
    case 'running':
    case 'pending':
      return 'Running'
    default:
      return status
  }
}

export function paperDisplayStatus(paper: {
  status?: string | null
  display_status?: string | null
  generated_questions?: number | null
  requested_questions?: number | null
}): string {
  if (paper.display_status) return paper.display_status
  const stored = (paper.status || '').toLowerCase()
  if (stored === 'running' || stored === 'pending') return 'running'
  const generated = paper.generated_questions ?? 0
  const requested = paper.requested_questions ?? 0
  if (requested > 0 && generated === requested) return 'completed'
  if (generated > 0 && generated < requested) return 'partial'
  if (generated === 0 && (stored === 'failed' || stored === 'error')) return 'failed'
  return stored
}

export function formatQuestionProgress(
  generated?: number | null,
  requested?: number | null,
): string {
  const gen = generated ?? 0
  if (requested == null) return `${gen} / —`
  return `${gen} / ${requested}`
}

export function formatQuestionCount(value?: number | null): string {
  return value == null ? '—' : String(value)
}

export function formatDifficultyMixLabel(mix?: {
  easy?: number
  medium?: number
  difficult?: number
} | null): string {
  if (!mix) return '—'
  const parts = [
    { label: 'Easy', count: mix.easy || 0 },
    { label: 'Medium', count: mix.medium || 0 },
    { label: 'Difficult', count: mix.difficult || 0 },
  ].filter((part) => part.count > 0)
  if (parts.length === 0) return '—'
  if (parts.length === 1) return `${parts[0].label} Only · ${parts[0].count}`
  return parts.map((part) => `${part.label} ${part.count}`).join(' · ')
}

export function questionDifficulty(q: BankQuestion): string {
  return q.validated_cognitive_difficulty || q.target_difficulty || q.difficulty || ''
}

export function formatCorrectAnswer(q: BankQuestion): string {
  const lettersFromIndices = (q.correct_indices || [])
    .map((index) => OPTION_LETTERS[index])
    .filter(Boolean)
  if (lettersFromIndices.length > 0) {
    return `Correct Answer: ${lettersFromIndices.join(', ')}`
  }

  const raw = (q.answer || '').trim()
  if (!raw) return 'Correct Answer: —'

  const cleaned = raw
    .replace(/^correct answer:\s*/i, '')
    .replace(/^answer:\s*/i, '')
    .replace(/^:\s*/, '')
    .replace(/\s+and\s+/gi, ', ')
    .replace(/[|/;]+/g, ', ')
    .replace(/\s*,\s*/g, ', ')
    .replace(/\s+/g, ' ')
    .trim()

  return `Correct Answer: ${cleaned || '—'}`
}

export function formatChapterLabel(chapter?: string | number | null): string {
  if (chapter == null || String(chapter).trim() === '') return ''
  const text = String(chapter).trim()
  if (/^chapter\b/i.test(text)) return text
  return `Chapter ${text}`
}

export function chapterLabel(q: BankQuestion): string {
  const formatted = formatChapterLabel(q.chapter)
  if (formatted && q.chapter_title) return `${formatted} — ${q.chapter_title}`
  if (formatted) return formatted
  if (q.chapter_title) return q.chapter_title
  return '—'
}

export function formatCreatedDate(value?: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export { OPTION_LETTERS }
