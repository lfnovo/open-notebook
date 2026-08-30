import { beforeEach, describe, expect, it, vi } from 'vitest'

const post = vi.fn()
const get = vi.fn()

vi.mock('./client', () => ({
  default: {
    post: (...args: unknown[]) => post(...args),
    get: (...args: unknown[]) => get(...args),
  },
}))

import { questionPaperApi } from './question-paper'

const payload = {
  book_id: 'question_book:4b46dax7tgo86c3sgaz0',
  grade: '10',
  subject: 'PFH 2026 Grade 10',
  chapter: 2,
  difficulty: 'medium' as const,
  total_questions: 15,
  single_correct: 11,
  multiple_correct: 4,
  language: 'en',
}

describe('questionPaperApi bank batch', () => {
  beforeEach(() => {
    post.mockReset()
    get.mockReset()
  })

  it('generateBankBatch posts to /papers/bank/batch/generate', async () => {
    post.mockResolvedValue({
      data: {
        job_id: 'cmd:1',
        batch_id: 'question_bank_batch:abc',
        status: 'submitted',
        message: 'started',
        requested: 15,
      },
    })

    const result = await questionPaperApi.generateBankBatch(payload)

    expect(post).toHaveBeenCalledWith('/papers/bank/batch/generate', payload)
    expect(result.batch_id).toBe('question_bank_batch:abc')
    expect(result.requested).toBe(15)
  })

  it('getBankBatchStatus polls the encoded batch id', async () => {
    get.mockResolvedValue({
      data: {
        batch_id: 'question_bank_batch:abc',
        status: 'running',
        requested: 15,
        accepted: 3,
        failed: 1,
      },
    })

    const result = await questionPaperApi.getBankBatchStatus('question_bank_batch:abc')

    expect(get).toHaveBeenCalledWith(
      `/papers/bank/batch/${encodeURIComponent('question_bank_batch:abc')}/status`,
    )
    expect(result.status).toBe('running')
    expect(result.accepted).toBe(3)
  })

  it('getBankBatchResult fetches a finished batch', async () => {
    get.mockResolvedValue({
      data: {
        batch_id: 'question_bank_batch:abc',
        status: 'completed',
        requested: 15,
        accepted: 15,
        questions: [],
      },
    })

    await questionPaperApi.getBankBatchResult('question_bank_batch:abc')

    expect(get).toHaveBeenCalledWith(
      `/papers/bank/batch/${encodeURIComponent('question_bank_batch:abc')}/result`,
    )
  })

  it('listBankBatches gets /papers/bank/batches', async () => {
    get.mockResolvedValue({
      data: [
        {
          batch_id: 'question_bank_batch:abc',
          grade: '10',
          book_id: 'question_book:4b46dax7tgo86c3sgaz0',
          chapter: 2,
          difficulty: 'medium',
          requested: 15,
          accepted: 12,
          status: 'completed_partial',
          created: '2026-08-30T01:00:00Z',
        },
      ],
    })

    const rows = await questionPaperApi.listBankBatches()

    expect(get).toHaveBeenCalledWith('/papers/bank/batches')
    expect(rows).toHaveLength(1)
    expect(rows[0].chapter).toBe(2)
    expect(rows[0].accepted).toBe(12)
  })
})
