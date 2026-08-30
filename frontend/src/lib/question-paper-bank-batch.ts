import type {
  BankBatchDifficulty,
  BankQuestion,
  GenerateBankBatchRequest,
} from '@/lib/types/question-paper'

export const BANK_BATCH_HISTORY_PATH = '/question-paper?tab=bank'

export function bankBatchReviewPath(batchId: string): string {
  return `/question-paper/bank/${encodeURIComponent(String(batchId || '').trim())}`
}

export function normalizeBankQuestion(raw: BankQuestion): BankQuestion {
  return {
    ...raw,
    id: String(raw.id || ''),
    batch_id: raw.batch_id ? String(raw.batch_id) : raw.batch_id,
    book_id: raw.book_id ? String(raw.book_id) : raw.book_id,
  }
}

export const BANK_BATCH_DIFFICULTIES: BankBatchDifficulty[] = ['easy', 'medium', 'difficult']

export function parseNonNegInt(raw: string): number {
  const n = parseInt(raw, 10)
  if (Number.isNaN(n) || n < 0) return 0
  return n
}

export function chapterNumberForApi(arrayIndex: number): number {
  return arrayIndex + 1
}

export function resolveBookSubject(book: {
  subject?: string | null
  display_name?: string | null
  title?: string | null
  book_name?: string | null
}, grade?: string): string {
  const subject = (
    book.subject ||
    book.display_name ||
    book.title ||
    book.book_name ||
    ''
  ).trim()
  if (subject) return subject
  const g = (grade || '').trim()
  return g ? `Grade ${g}` : ''
}

export function bankBatchCountError(
  totalQuestions: number,
  singleCorrect: number,
  multipleCorrect: number,
): string | null {
  if (!Number.isInteger(totalQuestions) || totalQuestions < 1) {
    return 'Total questions must be at least 1'
  }
  if (!Number.isInteger(singleCorrect) || singleCorrect < 0) {
    return 'Single correct must be 0 or more'
  }
  if (!Number.isInteger(multipleCorrect) || multipleCorrect < 0) {
    return 'Multiple correct must be 0 or more'
  }
  const sum = singleCorrect + multipleCorrect
  if (sum !== totalQuestions) {
    return `single_correct (${singleCorrect}) + multiple_correct (${multipleCorrect}) must equal total_questions (${totalQuestions})`
  }
  return null
}

export function isBankBatchDifficulty(value: string): value is BankBatchDifficulty {
  return (BANK_BATCH_DIFFICULTIES as string[]).includes(value)
}

export function isBankBatchTerminal(status?: string | null): boolean {
  return status === 'completed' || status === 'completed_partial' || status === 'failed'
}

export function bankBatchHasQuestions(batch: {
  accepted?: number | null
  saved_question_ids?: string[] | null
}): boolean {
  if ((batch.accepted ?? 0) > 0) return true
  return (batch.saved_question_ids || []).length > 0
}

export function bankBatchQuestionIds(
  batch?: { saved_question_ids?: string[] | null } | null,
  result?: { saved_question_ids?: string[] | null; questions?: Array<{ id?: string | null }> | null } | null,
): string[] {
  const fromResult = (result?.saved_question_ids || []).map((id) => String(id)).filter(Boolean)
  if (fromResult.length > 0) return fromResult
  const fromQuestions = (result?.questions || [])
    .map((question) => String(question.id || '').trim())
    .filter(Boolean)
  if (fromQuestions.length > 0) return fromQuestions
  return (batch?.saved_question_ids || []).map((id) => String(id)).filter(Boolean)
}

export function bankBatchCanView(status?: string | null): boolean {
  return isBankBatchTerminal(status)
}

export function bankBatchCanExport(
  status?: string | null,
  batch?: { accepted?: number | null; saved_question_ids?: string[] | null } | null,
): boolean {
  return isBankBatchTerminal(status) && bankBatchHasQuestions(batch || {})
}

export function isBankBatchActive(status?: string | null): boolean {
  if (!status) return false
  return !isBankBatchTerminal(status)
}

export function bankBatchProgressPercent(
  accepted?: number | null,
  requested?: number | null,
): number {
  const req = requested ?? 0
  if (req <= 0) return 0
  const acc = Math.max(0, accepted ?? 0)
  return Math.min(100, Math.round((acc / req) * 100))
}

export type BankBatchProgressTone = 'pending' | 'running' | 'completed' | 'partial' | 'failed'

export function bankBatchProgressTone(status?: string | null): BankBatchProgressTone {
  if (status === 'completed') return 'completed'
  if (status === 'completed_partial') return 'partial'
  if (status === 'failed') return 'failed'
  if (status === 'pending' || status === 'submitted' || !status) return 'pending'
  return 'running'
}

export function formatBankBatchStopReason(reason?: string | null): string {
  const raw = String(reason || '').trim()
  if (!raw) return ''
  switch (raw) {
    case 'full_target_reached':
      return 'All requested questions were accepted'
    case 'catalog_exhausted':
      return 'Question catalog was exhausted'
    case 'normal_partial_completion':
      return 'Generation stopped before the full request was filled'
    case 'minimum_target_reached_attempt_budget':
      return 'Stopped after reaching the minimum target (attempt budget)'
    case 'minimum_target_reached_time_budget':
      return 'Stopped after reaching the minimum target (time budget)'
    default:
      return raw.replace(/_/g, ' ')
  }
}

export function bankBatchStopReason(
  batch?: {
    stop_reason?: string | null
    audit?: { stop_reason?: string | null } | null
  } | null,
): string {
  return String(batch?.stop_reason || batch?.audit?.stop_reason || '').trim()
}

export function bankBatchRemaining(
  requested?: number | null,
  accepted?: number | null,
): number {
  return Math.max(0, (requested ?? 0) - (accepted ?? 0))
}

export function formatElapsed(ms: number): string {
  if (!Number.isFinite(ms) || ms < 0) return '0s'
  const totalSec = Math.floor(ms / 1000)
  const hours = Math.floor(totalSec / 3600)
  const minutes = Math.floor((totalSec % 3600) / 60)
  const seconds = totalSec % 60
  if (hours > 0) return `${hours}h ${minutes}m ${seconds}s`
  if (minutes > 0) return `${minutes}m ${seconds}s`
  return `${seconds}s`
}

export function bankBatchElapsedMs(opts: {
  created?: string | null
  startedAtMs?: number | null
  nowMs?: number
  endedAtMs?: number | null
}): number {
  const end = opts.endedAtMs ?? opts.nowMs ?? Date.now()
  let start = opts.startedAtMs ?? 0
  if (opts.created) {
    const parsed = Date.parse(opts.created)
    if (!Number.isNaN(parsed)) start = parsed
  }
  if (!start) return 0
  return Math.max(0, end - start)
}

export function apiErrorDetail(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail)) {
    const joined = detail
      .map((item) => (typeof item === 'string' ? item : JSON.stringify(item)))
      .filter(Boolean)
      .join('; ')
    if (joined) return joined
  }
  if (err instanceof Error && err.message.trim()) return err.message
  return fallback
}

export interface BankBatchFormValues {
  bookId: string
  grade: string
  subject: string
  chapter: number
  difficulty: BankBatchDifficulty
  totalQuestions: number
  singleCorrect: number
  multipleCorrect: number
  language?: string
}

export function bankBatchCanSubmit(
  values: Partial<BankBatchFormValues> & { isLoading?: boolean },
): boolean {
  if (values.isLoading) return false
  if (!String(values.bookId || '').trim()) return false
  if (!String(values.grade || '').trim()) return false
  if (!String(values.subject || '').trim()) return false
  if (!Number.isInteger(values.chapter) || (values.chapter ?? 0) < 1) return false
  if (!values.difficulty || !isBankBatchDifficulty(values.difficulty)) return false
  return bankBatchCountError(
    values.totalQuestions ?? 0,
    values.singleCorrect ?? 0,
    values.multipleCorrect ?? 0,
  ) === null
}

export function buildBankBatchPayload(values: BankBatchFormValues): GenerateBankBatchRequest {
  if (!bankBatchCanSubmit(values)) {
    throw new Error(
      bankBatchCountError(values.totalQuestions, values.singleCorrect, values.multipleCorrect)
        || 'Bank batch form is incomplete',
    )
  }
  return {
    book_id: values.bookId.trim(),
    grade: values.grade.trim(),
    subject: values.subject.trim(),
    chapter: values.chapter,
    difficulty: values.difficulty,
    total_questions: values.totalQuestions,
    single_correct: values.singleCorrect,
    multiple_correct: values.multipleCorrect,
    language: (values.language || 'en').trim() || 'en',
  }
}
