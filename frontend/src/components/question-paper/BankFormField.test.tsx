import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  BANK_FIELD_CONTROL_CLASS,
  BankFormField,
  bankFieldLabelId,
} from './BankFormField'

function GradeField({ value }: { value?: string }) {
  return (
    <BankFormField id="bank-gen-grade" label="Grade">
      <Select value={value}>
        <SelectTrigger
          id="bank-gen-grade"
          aria-labelledby={bankFieldLabelId('bank-gen-grade')}
          className={BANK_FIELD_CONTROL_CLASS}
        >
          <SelectValue placeholder="Select Grade" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="10">10</SelectItem>
        </SelectContent>
      </Select>
    </BankFormField>
  )
}

describe('BankFormField', () => {
  it('keeps the field label visible before a value is selected', () => {
    render(<GradeField />)
    expect(screen.getByText('Grade')).toBeInTheDocument()
    expect(screen.getByText('Select Grade')).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Grade' })).toHaveClass('w-full', 'h-9')
  })

  it('keeps the field label visible after a value is selected', () => {
    render(<GradeField value="10" />)
    expect(screen.getByText('Grade')).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Grade' })).toHaveTextContent('10')
    expect(screen.queryByText('Select Grade')).not.toBeInTheDocument()
  })
})
