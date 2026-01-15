import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ConfirmDialog } from './ConfirmDialog'

// useTranslation is mocked globally in setup.ts

describe('ConfirmDialog', () => {
  const onConfirmMock = vi.fn()
  const onOpenChangeMock = vi.fn()

  const defaultProps = {
    open: true,
    onOpenChange: onOpenChangeMock,
    title: 'Test Title',
    description: 'Test Description',
    onConfirm: onConfirmMock,
  }

  it('should render correct titles and descriptions', () => {
    render(<ConfirmDialog {...defaultProps} />)
    
    expect(screen.getByText('Test Title')).toBeInTheDocument()
    expect(screen.getByText('Test Description')).toBeInTheDocument()
    // Localized text from our setup.ts mock should be visible
    expect(screen.getByText('Confirm')).toBeInTheDocument()
    expect(screen.getByText('Cancel')).toBeInTheDocument()
  })

  it('should call onConfirm when confirm button is clicked', () => {
    render(<ConfirmDialog {...defaultProps} />)
    
    const confirmBtn = screen.getByText('Confirm')
    fireEvent.click(confirmBtn)
    
    expect(onConfirmMock).toHaveBeenCalledTimes(1)
  })

  it('should show custom confirm text if provided', () => {
    render(<ConfirmDialog {...defaultProps} confirmText="Delete Now" />)
    expect(screen.getByText('Delete Now')).toBeInTheDocument()
  })

  it('should show loading state and disable buttons', () => {
    render(<ConfirmDialog {...defaultProps} isLoading={true} />)
    
    const confirmBtn = screen.getByText('Confirm').closest('button')
    const cancelBtn = screen.getByText('Cancel').closest('button')
    
    expect(confirmBtn).toBeDisabled()
    expect(cancelBtn).toBeDisabled()
  })
})
