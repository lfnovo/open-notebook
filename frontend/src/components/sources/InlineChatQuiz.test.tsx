import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { InlineChatQuiz } from './InlineChatQuiz'
import { chatQuizzesApi, type ChatQuizDetail } from '@/lib/api/chat-quizzes'

vi.mock('@/lib/api/chat-quizzes', () => ({ chatQuizzesApi: { get: vi.fn(), submit: vi.fn() } }))
const question = { id: 'q1', type: 'multiple_choice' as const, prompt: 'Pick even', points: 1, options: ['3', '4'], blank_count: 0 }
const initial: ChatQuizDetail = { id: 'chat_quiz:one', title: 'Check your understanding', questions: [question], images: {}, latest_attempt: null, review_questions: null }
const graded: ChatQuizDetail = { ...initial, review_questions: [{ ...question, correct_option: 1 }], latest_attempt: { id: 'chat_quiz_attempt:one', exam_id: initial.id, answers: { q1: 1 }, results: [{ question_id: 'q1', score: 1, max_score: 1, is_correct: true, graded_by: 'auto' }], score: 1, max_score: 1, created: '2026-10-07' } }
function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(<QueryClientProvider client={client}><InlineChatQuiz id={initial.id} /></QueryClientProvider>)
}

describe('Inline interactive tests', () => {
  beforeEach(() => { vi.clearAllMocks(); vi.mocked(chatQuizzesApi.get).mockResolvedValue(initial); vi.mocked(chatQuizzesApi.submit).mockResolvedValue(graded) })
  it('submits answers here, shows feedback and allows another attempt', async () => {
    mount()
    await screen.findByText('Pick even')
    expect(screen.getByRole('button', { name: 'exams.submit' })).toBeDisabled()
    fireEvent.click(screen.getByRole('radio', { name: '4' }))
    fireEvent.click(screen.getByRole('button', { name: 'exams.submit' }))
    await screen.findByText('100%')
    expect(chatQuizzesApi.submit).toHaveBeenCalledExactlyOnceWith(initial.id, { q1: 1 })
    fireEvent.click(screen.getByRole('button', { name: 'exams.retake' }))
    expect(screen.getByRole('button', { name: 'exams.submit' })).toBeDisabled()
    expect(screen.getByRole('radio', { name: '4' })).not.toBeChecked()
  })
  it('restores the saved result when reopening a conversation', async () => {
    vi.mocked(chatQuizzesApi.get).mockResolvedValue(graded)
    mount()
    await screen.findByText('100%')
    expect(screen.queryByRole('button', { name: 'exams.submit' })).not.toBeInTheDocument()
  })
  it('keeps answers after a grading failure and does not auto-retry the request', async () => {
    vi.mocked(chatQuizzesApi.submit).mockRejectedValue(new Error('Offline'))
    mount()
    await screen.findByText('Pick even')
    fireEvent.click(screen.getByRole('radio', { name: '4' }))
    fireEvent.click(screen.getByRole('button', { name: 'exams.submit' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'exams.submit' })).toBeEnabled())
    expect(screen.getByRole('radio', { name: '4' })).toBeChecked()
    expect(chatQuizzesApi.submit).toHaveBeenCalledTimes(1)
  })
})
