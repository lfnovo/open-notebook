import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

import { QuizStudyModes } from './QuizStudyModes'

// useTranslation is mocked globally in setup.ts (t returns the key string)

vi.mock('@/components/study/QuizTaker', () => ({
  QuizTaker: () => <div data-testid="exam-mode" />,
}))

vi.mock('@/components/study/GuidedQuizSession', () => ({
  GuidedQuizSession: () => <div data-testid="guided-mode" />,
}))

describe('QuizStudyModes', () => {
  it('defaults to exam mode', () => {
    render(<QuizStudyModes items={[]} studySetName="My Quiz" />)
    expect(screen.getByTestId('exam-mode')).toBeInTheDocument()
    expect(screen.queryByTestId('guided-mode')).not.toBeInTheDocument()
  })

  it('switches to guided mode when the guided tab is clicked', () => {
    render(<QuizStudyModes items={[]} studySetName="My Quiz" />)

    // Radix Tabs switches on mousedown (and focus), not click - fireEvent.click
    // alone never dispatches a mousedown, so it would never flip tabs here.
    fireEvent.mouseDown(screen.getByText('study.guidedQuizSession.guidedModeTab'))

    expect(screen.getByTestId('guided-mode')).toBeInTheDocument()
    expect(screen.queryByTestId('exam-mode')).not.toBeInTheDocument()
  })

  it('switches back to exam mode', () => {
    render(<QuizStudyModes items={[]} studySetName="My Quiz" />)

    fireEvent.mouseDown(screen.getByText('study.guidedQuizSession.guidedModeTab'))
    expect(screen.getByTestId('guided-mode')).toBeInTheDocument()

    fireEvent.mouseDown(screen.getByText('study.guidedQuizSession.examModeTab'))
    expect(screen.getByTestId('exam-mode')).toBeInTheDocument()
  })
})
