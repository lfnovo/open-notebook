import { describe, expect, it } from 'vitest'
import {
  apiErrorDetail,
  bankBatchCanExport,
  bankBatchCanSubmit,
  bankBatchCanView,
  bankBatchCountError,
  bankBatchHasQuestions,
  bankBatchProgressPercent,
  bankBatchProgressTone,
  bankBatchQuestionIds,
  bankBatchRemaining,
  bankBatchReviewPath,
  bankBatchStopReason,
  bankBatchElapsedMs,
  formatBankBatchStopReason,
  formatElapsed,
  buildBankBatchPayload,
  chapterNumberForApi,
  isBankBatchActive,
  isBankBatchTerminal,
  parseNonNegInt,
  resolveBookSubject,
} from './question-paper-bank-batch'

const validForm = {
  bookId: 'question_book:4b46dax7tgo86c3sgaz0',
  grade: '10',
  subject: 'PFH 2026 Grade 10',
  chapter: 2,
  difficulty: 'medium' as const,
  totalQuestions: 15,
  singleCorrect: 11,
  multipleCorrect: 4,
}

describe('bank batch payload', () => {
  it('builds the Grade 10 Chapter 2 Medium 15Q API body', () => {
    expect(buildBankBatchPayload(validForm)).toEqual({
      book_id: 'question_book:4b46dax7tgo86c3sgaz0',
      grade: '10',
      subject: 'PFH 2026 Grade 10',
      chapter: 2,
      difficulty: 'medium',
      total_questions: 15,
      single_correct: 11,
      multiple_correct: 4,
      language: 'en',
    })
  })

  it('maps book chapter list index 1 to API chapter 2', () => {
    expect(chapterNumberForApi(1)).toBe(2)
  })

  it('requires single_correct + multiple_correct = total_questions', () => {
    expect(bankBatchCountError(15, 11, 4)).toBeNull()
    expect(bankBatchCountError(15, 15, 0)).toBeNull()
    expect(bankBatchCountError(15, 10, 4)).toMatch(/must equal total_questions \(15\)/)
    expect(bankBatchCountError(0, 0, 0)).toMatch(/at least 1/)
  })

  it('rejects incomplete forms and mismatched counts', () => {
    expect(bankBatchCanSubmit(validForm)).toBe(true)
    expect(bankBatchCanSubmit({ ...validForm, chapter: 0 })).toBe(false)
    expect(bankBatchCanSubmit({ ...validForm, bookId: '' })).toBe(false)
    expect(bankBatchCanSubmit({ ...validForm, difficulty: 'hard' as never })).toBe(false)
    expect(bankBatchCanSubmit({ ...validForm, singleCorrect: 10, multipleCorrect: 4 })).toBe(false)
    expect(bankBatchCanSubmit({ ...validForm, isLoading: true })).toBe(false)
  })

  it('does not send paper blueprint fields', () => {
    const payload = buildBankBatchPayload(validForm)
    expect(payload).not.toHaveProperty('blueprint')
    expect(payload).not.toHaveProperty('selected_chapters')
    expect(payload).not.toHaveProperty('target_marks')
    expect(payload).not.toHaveProperty('pass_percentage')
  })
})

describe('bank batch helpers', () => {
  it('resolves subject from book metadata', () => {
    expect(resolveBookSubject({ subject: 'Finance' })).toBe('Finance')
    expect(resolveBookSubject({ display_name: 'PFH 2026 - Grade 10' }, '10')).toBe('PFH 2026 - Grade 10')
    expect(resolveBookSubject({}, '10')).toBe('Grade 10')
  })

  it('classifies batch status for polling', () => {
    expect(isBankBatchActive('running')).toBe(true)
    expect(isBankBatchActive('pending')).toBe(true)
    expect(isBankBatchTerminal('completed')).toBe(true)
    expect(isBankBatchTerminal('completed_partial')).toBe(true)
    expect(isBankBatchTerminal('failed')).toBe(true)
    expect(isBankBatchActive('completed')).toBe(false)
  })

  it('computes progress percent from accepted / requested', () => {
    expect(bankBatchProgressPercent(3, 15)).toBe(20)
    expect(bankBatchProgressPercent(0, 15)).toBe(0)
    expect(bankBatchProgressPercent(15, 15)).toBe(100)
    expect(bankBatchProgressPercent(null, 0)).toBe(0)
  })

  it('formats elapsed time and remaining count', () => {
    expect(formatElapsed(0)).toBe('0s')
    expect(formatElapsed(4500)).toBe('4s')
    expect(formatElapsed(65_000)).toBe('1m 5s')
    expect(formatElapsed(3661000)).toBe('1h 1m 1s')
    expect(bankBatchRemaining(15, 12)).toBe(3)
    expect(bankBatchRemaining(15, 20)).toBe(0)
    expect(bankBatchElapsedMs({
      created: '2026-08-30T10:00:00.000Z',
      nowMs: Date.parse('2026-08-30T10:02:00.000Z'),
    })).toBe(120_000)
    expect(bankBatchElapsedMs({
      startedAtMs: 1_000,
      nowMs: 4_000,
    })).toBe(3_000)
    expect(bankBatchElapsedMs({
      created: '2026-08-30T10:00:00.000Z',
      nowMs: Date.parse('2026-08-30T12:00:00.000Z'),
      endedAtMs: Date.parse('2026-08-30T10:05:00.000Z'),
    })).toBe(300_000)
  })

  it('maps batch status to progress tone', () => {
    expect(bankBatchProgressTone('pending')).toBe('pending')
    expect(bankBatchProgressTone('submitted')).toBe('pending')
    expect(bankBatchProgressTone('running')).toBe('running')
    expect(bankBatchProgressTone('completed')).toBe('completed')
    expect(bankBatchProgressTone('completed_partial')).toBe('partial')
    expect(bankBatchProgressTone('failed')).toBe('failed')
  })

  it('formats stored stop reasons without treating partial as failure', () => {
    expect(formatBankBatchStopReason('catalog_exhausted')).toBe('Question catalog was exhausted')
    expect(formatBankBatchStopReason('normal_partial_completion')).toBe(
      'Generation stopped before the full request was filled',
    )
    expect(formatBankBatchStopReason('minimum_target_reached_attempt_budget')).toContain('minimum target')
    expect(bankBatchStopReason({
      error_message: 'looks like an error',
      audit: { stop_reason: 'catalog_exhausted' },
    })).toBe('catalog_exhausted')
    expect(bankBatchProgressTone('completed_partial')).not.toBe('failed')
  })

  it('parses non-negative integers and API error details', () => {
    expect(parseNonNegInt('15')).toBe(15)
    expect(parseNonNegInt('')).toBe(0)
    expect(parseNonNegInt('-2')).toBe(0)
    expect(apiErrorDetail(
      { response: { data: { detail: 'No chapter content could be loaded for the selected chapter.' } } },
      'fallback',
    )).toBe('No chapter content could be loaded for the selected chapter.')
    expect(apiErrorDetail(new Error('network'), 'fallback')).toBe('network')
  })
})

describe('bank batch history actions', () => {
  const completed = {
    accepted: 12,
    saved_question_ids: ['question_bank:a', 'question_bank:b'],
  }

  it('enables view and export only for finished batches with questions', () => {
    expect(bankBatchCanView('running')).toBe(false)
    expect(bankBatchCanView('completed_partial')).toBe(true)
    expect(bankBatchCanExport('running', completed)).toBe(false)
    expect(bankBatchCanExport('completed_partial', completed)).toBe(true)
    expect(bankBatchCanExport('completed', { accepted: 0, saved_question_ids: [] })).toBe(false)
    expect(bankBatchHasQuestions({ accepted: 0, saved_question_ids: ['q1'] })).toBe(true)
  })

  it('prefers result saved_question_ids for excel export', () => {
    expect(bankBatchQuestionIds(completed)).toEqual(['question_bank:a', 'question_bank:b'])
    expect(bankBatchQuestionIds(completed, {
      saved_question_ids: ['question_bank:z'],
      questions: [{ id: 'ignored' }],
    })).toEqual(['question_bank:z'])
    expect(bankBatchQuestionIds({ saved_question_ids: [] }, {
      questions: [{ id: 'question_bank:from-result' }],
    })).toEqual(['question_bank:from-result'])
  })

  it('builds the review page path from a batch id', () => {
    expect(bankBatchReviewPath('question_bank_batch:qkozkavx2rfkorgleo0h')).toBe(
      '/question-paper/bank/question_bank_batch%3Aqkozkavx2rfkorgleo0h',
    )
  })
})
