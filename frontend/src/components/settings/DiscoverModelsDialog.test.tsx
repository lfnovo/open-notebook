import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { DiscoverModelsDialog } from './DiscoverModelsDialog'
import type { Credential } from '@/lib/api/credentials'

// useTranslation is mocked globally in setup.ts (t returns the key string)

const discovered = [
  { name: 'openai/gpt-4o', provider: 'openrouter', model_type: 'language' },
  { name: 'openai/text-embedding-3-small', provider: 'openrouter', model_type: 'embedding' },
  { name: 'untyped/model', provider: 'openrouter' },
]

vi.mock('@/lib/hooks/use-credentials', () => ({
  useDiscoverModels: () => ({
    mutate: (_id: string, opts: { onSuccess: (r: { discovered: typeof discovered }) => void }) =>
      opts.onSuccess({ discovered }),
  }),
  useRegisterModels: () => ({ mutate: vi.fn(), isPending: false }),
}))

vi.mock('@/lib/hooks/use-providers', () => ({
  useProviders: () => ({
    data: [{ name: 'openrouter', modalities: ['language', 'embedding'] }],
  }),
}))

// Radix Select does not open in jsdom, so use a native select instead
vi.mock('@/components/ui/select', () => ({
  Select: ({ value, onValueChange, children }: {
    value: string
    onValueChange: (v: string) => void
    children: React.ReactNode
  }) => (
    <select data-testid="type-select" value={value} onChange={e => onValueChange(e.target.value)}>
      {children}
    </select>
  ),
  SelectTrigger: () => null,
  SelectValue: () => null,
  SelectContent: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  SelectItem: ({ value }: { value: string }) => <option value={value}>{value}</option>,
}))

const credential = {
  id: 'credential:1',
  provider: 'openrouter',
  modalities: ['language', 'embedding'],
} as unknown as Credential

describe('DiscoverModelsDialog', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows typed models only under their type and untyped under every type', () => {
    render(<DiscoverModelsDialog open onOpenChange={() => {}} credential={credential} />)

    expect(screen.getByText('openai/gpt-4o')).toBeInTheDocument()
    expect(screen.queryByText('openai/text-embedding-3-small')).not.toBeInTheDocument()
    expect(screen.getByText('untyped/model')).toBeInTheDocument()

    fireEvent.change(screen.getByTestId('type-select'), { target: { value: 'embedding' } })

    expect(screen.queryByText('openai/gpt-4o')).not.toBeInTheDocument()
    expect(screen.getByText('openai/text-embedding-3-small')).toBeInTheDocument()
    expect(screen.getByText('untyped/model')).toBeInTheDocument()
  })
})
