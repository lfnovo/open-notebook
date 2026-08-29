import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

import { FlashcardStudyModes } from './FlashcardStudyModes'

// useTranslation is mocked globally in setup.ts (t returns the key string)

vi.mock('@/components/study/FlashcardViewer', () => ({
  FlashcardViewer: () => <div data-testid="quick-mode" />,
}))

vi.mock('@/components/study/GuidedFlashcardSession', () => ({
  GuidedFlashcardSession: () => <div data-testid="guided-mode" />,
}))

describe('FlashcardStudyModes', () => {
  it('defaults to quick mode', () => {
    render(<FlashcardStudyModes items={[]} studySetId="study_set:1" />)
    expect(screen.getByTestId('quick-mode')).toBeInTheDocument()
    expect(screen.queryByTestId('guided-mode')).not.toBeInTheDocument()
  })

  it('switches to guided mode when the AI-guided tab is clicked', () => {
    render(<FlashcardStudyModes items={[]} studySetId="study_set:1" />)

    // Radix Tabs switches on mousedown (and focus), not click - fireEvent.click
    // alone never dispatches a mousedown, so it would never flip tabs here.
    fireEvent.mouseDown(screen.getByText('study.guidedSession.guidedModeTab'))

    expect(screen.getByTestId('guided-mode')).toBeInTheDocument()
    expect(screen.queryByTestId('quick-mode')).not.toBeInTheDocument()
  })

  it('switches back to quick mode', () => {
    render(<FlashcardStudyModes items={[]} studySetId="study_set:1" />)

    // Radix Tabs switches on mousedown (and focus), not click - fireEvent.click
    // alone never dispatches a mousedown, so it would never flip tabs here.
    fireEvent.mouseDown(screen.getByText('study.guidedSession.guidedModeTab'))
    expect(screen.getByTestId('guided-mode')).toBeInTheDocument()

    fireEvent.mouseDown(screen.getByText('study.guidedSession.quickModeTab'))
    expect(screen.getByTestId('quick-mode')).toBeInTheDocument()
  })
})
