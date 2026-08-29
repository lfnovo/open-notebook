import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

import { GuidedFlashcardSession } from './GuidedFlashcardSession'
import { useGradeFlashcardAnswer } from '@/lib/hooks/use-study'
import type { FlashcardItem, GradeFlashcardResponse } from '@/lib/types/study'

// useTranslation is mocked globally in setup.ts (t returns the key string)

vi.mock('@/lib/hooks/use-study', () => ({
  useGradeFlashcardAnswer: vi.fn(),
}))

const mockUseGradeFlashcardAnswer = vi.mocked(useGradeFlashcardAnswer)

type MutateOptions = { onSuccess: (response: GradeFlashcardResponse) => void }

function makeItems(): FlashcardItem[] {
  return [{ front: 'What is the capital of France?', back: 'Paris' }]
}

function asMutationResult(mutate: ReturnType<typeof vi.fn>) {
  return { mutate, isPending: false } as unknown as ReturnType<typeof useGradeFlashcardAnswer>
}

function submitAnswer(text: string) {
  fireEvent.change(screen.getByPlaceholderText('study.guidedSession.answerPlaceholder'), {
    target: { value: text },
  })
  fireEvent.click(screen.getByText('study.guidedSession.submitAnswer'))
}

describe('GuidedFlashcardSession', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows the front but not the back up front', () => {
    mockUseGradeFlashcardAnswer.mockReturnValue(asMutationResult(vi.fn()))

    render(<GuidedFlashcardSession items={makeItems()} studySetId="study_set:1" />)

    expect(screen.getByText('What is the capital of France?')).toBeInTheDocument()
    expect(screen.queryByText('Paris')).not.toBeInTheDocument()
  })

  it('shows a friendly empty state when no cards are due', () => {
    mockUseGradeFlashcardAnswer.mockReturnValue(asMutationResult(vi.fn()))
    const futureItem: FlashcardItem = { front: 'Q', back: 'A', due: '2999-01-01' }

    render(<GuidedFlashcardSession items={[futureItem]} studySetId="study_set:1" />)

    expect(screen.getByText('study.guidedSession.noCardsDue')).toBeInTheDocument()
  })

  it('increments the attempt number on retry and surfaces the previous feedback as a hint', () => {
    const mutate = vi.fn((_vars: unknown, options: MutateOptions) => {
      options.onSuccess({
        correct: false,
        feedback: 'You missed the key detail.',
        rating: 'again',
        attempt: 1,
        revealed_answer: null,
        item: { front: 'What is the capital of France?', back: 'Paris' },
        due_count: 1,
      })
    })
    mockUseGradeFlashcardAnswer.mockReturnValue(asMutationResult(mutate))

    render(<GuidedFlashcardSession items={makeItems()} studySetId="study_set:1" />)

    submitAnswer('London')

    expect(mutate).toHaveBeenCalledWith(
      { itemIndex: 0, answer: 'London', attempt: 1 },
      expect.anything()
    )
    expect(screen.getByText('study.guidedSession.incorrectLabel')).toBeInTheDocument()
    // No reveal yet - retry is offered instead of advancing.
    expect(screen.getByText('study.guidedSession.tryAgainBtn')).toBeInTheDocument()
    expect(screen.queryByText('study.guidedSession.nextCard')).not.toBeInTheDocument()

    fireEvent.click(screen.getByText('study.guidedSession.tryAgainBtn'))

    // Back to the answer input, attempt now 2, with the previous feedback shown as a hint.
    expect(screen.getByText('study.guidedSession.attemptLabel')).toBeInTheDocument()
    expect(screen.getByText(/You missed the key detail\./)).toBeInTheDocument()
    expect(screen.getByPlaceholderText('study.guidedSession.answerPlaceholder')).toHaveValue('')

    submitAnswer('Paris, obviously')
    expect(mutate).toHaveBeenLastCalledWith(
      { itemIndex: 0, answer: 'Paris, obviously', attempt: 2 },
      expect.anything()
    )
  })

  it('forces "again" and reveals the answer after the 3rd failed attempt, offering only Next', () => {
    const mutate = vi.fn((_vars: unknown, options: MutateOptions) => {
      options.onSuccess({
        correct: false,
        feedback: 'Still not quite right.',
        rating: 'again',
        attempt: 3,
        revealed_answer: 'Paris',
        item: { front: 'What is the capital of France?', back: 'Paris' },
        due_count: 0,
      })
    })
    mockUseGradeFlashcardAnswer.mockReturnValue(asMutationResult(mutate))

    render(<GuidedFlashcardSession items={makeItems()} studySetId="study_set:1" />)

    // Simulate having already retried twice by submitting once (attempt=1
    // starts the exchange - this final mutate resolves with attempt: 3,
    // which is what the backend would report on the 3rd try).
    submitAnswer('still wrong')

    expect(screen.getByText(/study\.guidedSession\.revealedAnswerLabel/)).toBeInTheDocument()
    expect(screen.getByText(/Paris/)).toBeInTheDocument()
    expect(screen.getByText('study.guidedSession.nextCard')).toBeInTheDocument()
    // Forced closure: no more retries offered once revealed.
    expect(screen.queryByText('study.guidedSession.tryAgainBtn')).not.toBeInTheDocument()
  })

  it('shows the session summary once the due queue is exhausted', () => {
    const mutate = vi.fn((_vars: unknown, options: MutateOptions) => {
      options.onSuccess({
        correct: true,
        feedback: 'Nicely done.',
        rating: 'good',
        attempt: 1,
        revealed_answer: null,
        item: { front: 'What is the capital of France?', back: 'Paris' },
        due_count: 0,
      })
    })
    mockUseGradeFlashcardAnswer.mockReturnValue(asMutationResult(mutate))

    render(<GuidedFlashcardSession items={makeItems()} studySetId="study_set:1" />)

    submitAnswer('Paris')
    fireEvent.click(screen.getByText('study.guidedSession.nextCard'))

    expect(screen.getByText('study.guidedSession.sessionComplete')).toBeInTheDocument()
    expect(screen.getByText('study.guidedSession.allMasteredMessage')).toBeInTheDocument()
  })
})
