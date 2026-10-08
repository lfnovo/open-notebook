import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ChatResponseContent } from './ChatResponseContent'

vi.mock('./InlineChatQuiz', () => ({ InlineChatQuiz: ({ id }: { id: string }) => <div data-testid="inline-quiz">{id}</div> }))
const image = { name: 'Chart', data_url: 'data:image/png;base64,iVBORw0KGgo=' }

describe('Positioned response content', () => {
  it('puts an image and quiz between the corresponding explanation paragraphs', () => {
    const { container } = render(<ChatResponseContent content={'First paragraph\n\n[[image:1]]\n\nSecond paragraph\n\n[[quiz:chat_quiz:one]]\n\nLast paragraph'} images={[image]} quizzes={['chat_quiz:one']} onReferenceClick={vi.fn()} />)
    const first = screen.getByText('First paragraph')
    const img = screen.getByRole('img')
    const second = screen.getByText('Second paragraph')
    const quiz = screen.getByTestId('inline-quiz')
    const last = screen.getByText('Last paragraph')
    expect(first.compareDocumentPosition(img) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(img.compareDocumentPosition(second) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(second.compareDocumentPosition(quiz) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(quiz.compareDocumentPosition(last) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(container.textContent).not.toContain('[[image:')
  })

  it('ignores invented IDs, prevents duplication and preserves old attachments', () => {
    render(<ChatResponseContent content={'[[image:1]]\n\n[[image:1]]\n\n[[image:8]]\n\n[[quiz:chat_quiz:fake]]'} images={[image, { ...image, name: 'Legacy figure' }]} onReferenceClick={vi.fn()} />)
    expect(screen.getAllByRole('img')).toHaveLength(2)
    expect(screen.queryByTestId('inline-quiz')).not.toBeInTheDocument()
  })
})

it('preserves the explanation and shows one localized notice if a test cannot be recovered', () => {
  const { container } = render(<ChatResponseContent content={'Explanation\n\n[[quiz-unavailable]]\n\nConclusion\n\n[[quiz-unavailable]]'} onReferenceClick={vi.fn()} />)
  expect(screen.getByText('Explanation')).toBeInTheDocument()
  expect(screen.getByText('Conclusion')).toBeInTheDocument()
  expect(screen.getAllByRole('status')).toHaveLength(1)
  expect(screen.getByRole('status')).toHaveTextContent('chat.quizPreparationFailed')
  expect(container.textContent).not.toContain('[[quiz-unavailable]]')
})
