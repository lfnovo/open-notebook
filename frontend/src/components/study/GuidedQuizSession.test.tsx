import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

import { GuidedQuizSession } from './GuidedQuizSession'
import type { QuizItem } from '@/lib/types/study'

// useTranslation is mocked globally in setup.ts (t returns the key string)

function makeItems(): QuizItem[] {
  return [
    {
      question: 'What is the capital of France?',
      options: ['London', 'Paris', 'Berlin'],
      correct_index: 1,
      explanation: 'Paris has been the capital since the 10th century.',
    },
    {
      question: 'What is 2 + 2?',
      options: ['3', '4'],
      correct_index: 1,
    },
  ]
}

function answer(optionLabel: string) {
  fireEvent.click(screen.getByLabelText(optionLabel))
  fireEvent.click(screen.getByText('study.guidedSession.submitAnswer'))
}

describe('GuidedQuizSession', () => {
  it('renders nothing for an empty item list', () => {
    const { container } = render(<GuidedQuizSession items={[]} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('shows the question and options up front, ungraded', () => {
    render(<GuidedQuizSession items={makeItems()} />)

    expect(screen.getByText('What is the capital of France?')).toBeInTheDocument()
    expect(screen.getByLabelText('Paris')).toBeInTheDocument()
    expect(screen.queryByText('study.guidedSession.correctLabel')).not.toBeInTheDocument()
  })

  it('marks the question mastered on a first-try correct answer and advances', () => {
    render(<GuidedQuizSession items={makeItems()} />)

    answer('Paris')

    expect(screen.getByText('study.guidedSession.correctLabel')).toBeInTheDocument()
    expect(screen.getByText(/Paris has been the capital/)).toBeInTheDocument()

    fireEvent.click(screen.getByText('study.guidedQuizSession.nextQuestion'))

    expect(screen.getByText('What is 2 + 2?')).toBeInTheDocument()
  })

  it('lets the student retry a wrong answer, disabling the tried option', () => {
    render(<GuidedQuizSession items={makeItems()} />)

    answer('London')

    expect(screen.getByText('study.guidedSession.incorrectLabel')).toBeInTheDocument()
    expect(screen.getByText('study.guidedSession.tryAgainBtn')).toBeInTheDocument()
    // Not yet revealed - no next button offered.
    expect(screen.queryByText('study.guidedQuizSession.nextQuestion')).not.toBeInTheDocument()

    fireEvent.click(screen.getByText('study.guidedSession.tryAgainBtn'))

    expect(screen.getByLabelText('London')).toBeDisabled()
    expect(screen.getByText('study.guidedSession.attemptLabel')).toBeInTheDocument()

    answer('Paris')
    expect(screen.getByText('study.guidedSession.correctLabel')).toBeInTheDocument()
    expect(screen.getByText('study.guidedQuizSession.nextQuestion')).toBeInTheDocument()
  })

  it('reveals the correct option and forces closure after the 3rd wrong attempt', () => {
    const items: QuizItem[] = [
      {
        question: 'Pick the right one',
        options: ['A', 'B', 'C', 'D'],
        correct_index: 3,
      },
    ]
    render(<GuidedQuizSession items={items} />)

    answer('A')
    fireEvent.click(screen.getByText('study.guidedSession.tryAgainBtn'))
    answer('B')
    fireEvent.click(screen.getByText('study.guidedSession.tryAgainBtn'))
    answer('C')

    expect(screen.getByText(/study\.guidedQuizSession\.correctAnswerLabel/)).toBeInTheDocument()
    expect(screen.getByText('study.guidedQuizSession.nextQuestion')).toBeInTheDocument()
    expect(screen.queryByText('study.guidedSession.tryAgainBtn')).not.toBeInTheDocument()
  })

  it('shows a session summary with mastered/corrected/struggled counts', () => {
    const items: QuizItem[] = [
      { question: 'Q1', options: ['Wrong', 'Right'], correct_index: 1 },
      { question: 'Q2', options: ['Wrong', 'Right'], correct_index: 1 },
    ]
    render(<GuidedQuizSession items={items} />)

    // Q1: mastered (first try).
    answer('Right')
    fireEvent.click(screen.getByText('study.guidedQuizSession.nextQuestion'))

    // Q2: wrong then corrected.
    answer('Wrong')
    fireEvent.click(screen.getByText('study.guidedSession.tryAgainBtn'))
    answer('Right')
    fireEvent.click(screen.getByText('study.guidedQuizSession.nextQuestion'))

    expect(screen.getByText('study.guidedSession.sessionComplete')).toBeInTheDocument()
    expect(screen.getByText(/study\.guidedQuizSession\.masteredLabel/)).toBeInTheDocument()
    expect(screen.getByText(/study\.guidedQuizSession\.correctedLabel/)).toBeInTheDocument()
    expect(screen.getByText('study.guidedSession.allMasteredMessage')).toBeInTheDocument()
  })
})
