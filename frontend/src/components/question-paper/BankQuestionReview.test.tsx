import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BankQuestionReview } from './BankQuestionReview'
import type { BankQuestion } from '@/lib/types/question-paper'

const options = [
  'SIP is a one-time investment',
  'SIP invests a fixed amount regularly',
  'SIP is only for stocks',
  'SIP has no lock-in',
  'SIP is a government scheme',
]

function question(overrides: Partial<BankQuestion> = {}): BankQuestion {
  return {
    id: 'question_bank:single',
    question: 'What is a Systematic Investment Plan (SIP)?',
    topic: 'Mutual Funds',
    type: 'mcq',
    difficulty: 'medium',
    answer: 'B',
    explanation: 'SIP invests a fixed amount at regular intervals.',
    options,
    correct_indices: [1],
    answer_type: 'single_correct',
    target_difficulty: 'medium',
    validated_cognitive_difficulty: 'medium',
    difficulty_score: 15,
    validation_status: 'passed',
    ...overrides,
  }
}

describe('BankQuestionReview', () => {
  it('shows single-correct question fields without editing controls', () => {
    render(<BankQuestionReview question={question()} />)

    expect(screen.getByText('What is a Systematic Investment Plan (SIP)?')).toBeInTheDocument()
    expect(screen.getByText('SIP invests a fixed amount regularly')).toBeInTheDocument()
    expect(screen.getByText('Correct')).toBeInTheDocument()
    expect(screen.getByText('B')).toBeInTheDocument()
    expect(screen.getByText('Single Correct')).toBeInTheDocument()
    expect(screen.getByText('Medium')).toBeInTheDocument()
    expect(screen.getByText('Passed')).toBeInTheDocument()
    expect(screen.getByText('15')).toBeInTheDocument()
    expect(screen.getByText('SIP invests a fixed amount at regular intervals.')).toBeInTheDocument()
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /save|edit/i })).not.toBeInTheDocument()
  })

  it('marks multiple correct options and hides cognitive score when missing', () => {
    render(
      <BankQuestionReview
        question={question({
          id: 'question_bank:multi',
          question: 'Which statements about SIPs are true?',
          type: 'multi_correct',
          answer_type: 'multiple_correct',
          correct_indices: [1, 3],
          answer: 'B, D',
          difficulty_score: null,
          explanation: 'Regular investing and no mandatory lock-in apply.',
        })}
      />,
    )

    expect(screen.getByText('Which statements about SIPs are true?')).toBeInTheDocument()
    expect(screen.getByText('Multiple Correct')).toBeInTheDocument()
    expect(screen.getByText('B, D')).toBeInTheDocument()
    expect(screen.getAllByText('Correct')).toHaveLength(2)
    expect(screen.queryByText('Cognitive score')).not.toBeInTheDocument()
    expect(screen.getByText('Regular investing and no mandatory lock-in apply.')).toBeInTheDocument()
  })
})
