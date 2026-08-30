import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BankBatchProgressPanel } from './BankBatchProgressPanel'

describe('BankBatchProgressPanel', () => {
  it('shows running metrics including percent, remaining, and elapsed', () => {
    render(
      <BankBatchProgressPanel
        status="running"
        requested={15}
        accepted={3}
        failed={4}
        created={new Date(Date.now() - 65_000).toISOString()}
      />,
    )
    expect(screen.getByTestId('bank-batch-progress')).toBeInTheDocument()
    expect(screen.getByText('Status: Running')).toBeInTheDocument()
    expect(screen.getByText('20%')).toBeInTheDocument()
    expect(screen.getByText('Requested')).toBeInTheDocument()
    expect(screen.getByText('15')).toBeInTheDocument()
    expect(screen.getByText('Accepted')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('Failed attempts')).toBeInTheDocument()
    expect(screen.getByText('4')).toBeInTheDocument()
    expect(screen.getByText('Remaining')).toBeInTheDocument()
    expect(screen.getByText('12')).toBeInTheDocument()
    expect(screen.getByText('Elapsed')).toBeInTheDocument()
    expect(screen.getByText(/1m \d+s/)).toBeInTheDocument()
  })

  it('shows completed, partial, and failed states', () => {
    const { rerender } = render(
      <BankBatchProgressPanel status="completed" requested={15} accepted={15} failed={0} />,
    )
    expect(screen.getByText('Status: Completed')).toBeInTheDocument()
    expect(screen.getByText('100%')).toBeInTheDocument()
    expect(screen.getByText('All requested questions were accepted.')).toBeInTheDocument()

    rerender(
      <BankBatchProgressPanel
        status="completed_partial"
        requested={15}
        accepted={12}
        failed={8}
        stopReason="catalog_exhausted"
        errorMessage="Stopped after 12/15 accepted; catalog exhausted."
      />,
    )
    expect(screen.getByText('Status: Completed (partial)')).toBeInTheDocument()
    expect(screen.queryByText('Status: Failed')).not.toBeInTheDocument()
    expect(screen.getByText('12 of 15 questions were accepted.')).toBeInTheDocument()
    expect(screen.getByText('Stop reason: Question catalog was exhausted')).toBeInTheDocument()
    expect(screen.queryByText('Stopped after 12/15 accepted; catalog exhausted.')).not.toBeInTheDocument()
    expect(screen.getByText('12')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()

    rerender(
      <BankBatchProgressPanel
        status="failed"
        requested={15}
        accepted={0}
        failed={6}
        errorMessage="Worker stopped"
      />,
    )
    expect(screen.getByText('Status: Failed')).toBeInTheDocument()
    expect(screen.getByText('Worker stopped')).toBeInTheDocument()
  })
})
