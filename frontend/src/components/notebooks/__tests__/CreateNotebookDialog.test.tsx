import { renderWithProviders, screen } from '@/test-utils'
import { CreateNotebookDialog } from '../CreateNotebookDialog'
import { vi } from 'vitest'

vi.mock('@/lib/hooks/use-notebooks', () => ({
  useCreateNotebook: () => ({
    mutateAsync: vi.fn().mockResolvedValue(undefined),
    isPending: false,
  }),
}))

describe('CreateNotebookDialog', () => {
  it('validates required name field', async () => {
    const onOpenChange = vi.fn()

    const { user } = renderWithProviders(
      <CreateNotebookDialog open={true} onOpenChange={onOpenChange} />
    )

    // Trigger onChange validation by typing and clearing
    const nameInput = screen.getByLabelText(/name/i)
    await user.type(nameInput, 'a')
    await user.clear(nameInput)

    // Error should appear and submit should be disabled
    expect(await screen.findByText('Name is required')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /create notebook/i })).toBeDisabled()
  })

  it('submits form and closes dialog on success', async () => {
    const onOpenChange = vi.fn()

    const { user } = renderWithProviders(
      <CreateNotebookDialog open={true} onOpenChange={onOpenChange} />
    )

    await user.type(screen.getByLabelText(/name/i), 'New Notebook')
    await user.type(screen.getByLabelText(/description/i), 'A description')

    await user.click(screen.getByRole('button', { name: /create notebook/i }))

    // Expect dialog to close
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })
})
