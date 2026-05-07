import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { StreamingResponse } from './StreamingResponse'

vi.mock('@/lib/hooks/use-modal-manager', () => ({
  useModalManager: () => ({
    openModal: vi.fn(),
  }),
}))

describe('StreamingResponse', () => {
  it('prioritizes the final answer before process details', () => {
    render(
      <StreamingResponse
        isStreaming={false}
        finalAnswer="This is the answer."
        strategy={{
          reasoning: 'Search for supporting context.',
          searches: [{ term: 'cement additive', instructions: 'Find relevant sources.' }],
        }}
        answers={['Intermediate answer']}
      />
    )

    const text = document.body.textContent ?? ''
    expect(text.indexOf('Final Answer')).toBeLessThan(text.indexOf('Strategy'))
    expect(text.indexOf('Final Answer')).toBeLessThan(text.indexOf('Individual Answers'))
    expect(screen.getByText('This is the answer.')).toBeInTheDocument()
  })
})
