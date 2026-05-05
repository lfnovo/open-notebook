import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { OperationGuide } from './OperationGuide'

describe('OperationGuide', () => {
  it('renders a labelled standard operation sequence', () => {
    render(
      <OperationGuide
        title="Standard flow"
        description="Use this sequence before changing access."
        steps={[
          'Review current access',
          'Make one scoped change',
          'Check audit evidence',
        ]}
      />
    )

    expect(screen.getByRole('region', { name: 'Standard flow' })).toBeInTheDocument()
    expect(screen.getByText('Use this sequence before changing access.')).toBeInTheDocument()
    expect(screen.getAllByRole('listitem')).toHaveLength(3)
    expect(screen.getByText('Review current access')).toBeInTheDocument()
    expect(screen.getByText('Make one scoped change')).toBeInTheDocument()
    expect(screen.getByText('Check audit evidence')).toBeInTheDocument()
  })
})
