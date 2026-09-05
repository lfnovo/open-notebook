import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { NotebookScopeSelector } from './NotebookScopeSelector'
import { useNotebooks } from '@/lib/hooks/use-notebooks'

// useTranslation is mocked globally in setup.ts (t returns the key string)

vi.mock('@/lib/hooks/use-notebooks', () => ({
  useNotebooks: vi.fn(),
}))

const mockUseNotebooks = vi.mocked(useNotebooks)

const notebooks = [
  { id: 'notebook:a', name: 'Alpha', description: '' },
  { id: 'notebook:b', name: 'Beta', description: 'second' },
]

describe('NotebookScopeSelector', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseNotebooks.mockReturnValue({ data: notebooks, isLoading: false } as ReturnType<typeof useNotebooks>)
  })

  it('reads as "all notebooks" when nothing is selected and hides the clear action', () => {
    render(<NotebookScopeSelector selectedIds={[]} onChange={vi.fn()} />)
    expect(screen.getByText('searchPage.scopeAllNotebooks')).toBeInTheDocument()
    expect(screen.queryByText('searchPage.scopeClear')).not.toBeInTheDocument()
  })

  it('adds a notebook to the scope when its checkbox is toggled', () => {
    const onChange = vi.fn()
    render(<NotebookScopeSelector selectedIds={['notebook:a']} onChange={onChange} />)

    fireEvent.click(screen.getByRole('button', { name: /searchPage.scopeNotebooks/ }))
    fireEvent.click(screen.getByRole('checkbox', { name: /Beta/ }))

    expect(onChange).toHaveBeenCalledWith(['notebook:a', 'notebook:b'])
  })

  it('removes an already selected notebook when toggled again', () => {
    const onChange = vi.fn()
    render(<NotebookScopeSelector selectedIds={['notebook:a', 'notebook:b']} onChange={onChange} />)

    fireEvent.click(screen.getByRole('button', { name: /searchPage.scopeNotebooks/ }))
    fireEvent.click(screen.getByRole('checkbox', { name: /Alpha/ }))

    expect(onChange).toHaveBeenCalledWith(['notebook:b'])
  })

  it('clears the whole scope from the clear action', () => {
    const onChange = vi.fn()
    render(<NotebookScopeSelector selectedIds={['notebook:a']} onChange={onChange} />)

    fireEvent.click(screen.getByText('searchPage.scopeClear'))

    expect(onChange).toHaveBeenCalledWith([])
  })
})
