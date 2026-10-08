import { render, screen, fireEvent, within } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { ExamQuestionImages } from './ExamQuestionImages'
import type { ExamQuestion } from '@/lib/types/exams'

const question: ExamQuestion = {
  id: 'q1', type: 'open', prompt: 'Describe Figure 1', points: 1, options: [], blank_count: 0, image_ids: ['figure1'],
}
const images = { figure1: { name: 'The answer is blue', data_url: 'data:image/png;base64,iVBORw0KGgo=', kind: 'source' as const, source_id: 'source:one', source_title: 'Solutions.pdf', page: 2 } }

describe('Exam figures', () => {
  it('shows the saved figure with a neutral caption and allows enlargement', () => {
    render(<ExamQuestionImages question={question} images={images} />)
    expect(screen.getByRole('img').getAttribute('src')).toBe(images.figure1.data_url)
    expect(screen.queryByText('The answer is blue')).not.toBeInTheDocument()
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button'))
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(within(screen.getByRole('dialog')).getByRole('img').getAttribute('src')).toBe(images.figure1.data_url)
  })

  it('provides source provenance during review', () => {
    render(<ExamQuestionImages question={question} images={images} review />)
    expect(screen.getByRole('link').getAttribute('href')).toBe('/sources/source%3Aone')
  })

  it('keeps legacy questions without figures usable', () => {
    render(<ExamQuestionImages question={{ ...question, image_ids: undefined }} />)
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
  })
})
