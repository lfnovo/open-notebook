import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ApiKeysPage from './page'
import { ProviderInfo } from '@/lib/api/providers'
import { Credential } from '@/lib/api/credentials'

// useTranslation is mocked globally in setup.ts (t returns the key string)

vi.mock('@/components/layout/AppShell', () => ({
  AppShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

vi.mock('@/components/settings', () => ({
  MigrationBanner: () => null,
  DefaultModelSelectors: () => null,
  ProviderSection: ({ provider }: { provider: ProviderInfo }) => (
    <div data-testid="provider-section">{provider.display_name}</div>
  ),
}))

vi.mock('@/lib/hooks/use-models', () => ({
  useModels: vi.fn(() => ({ data: [], isLoading: false })),
  useModelDefaults: vi.fn(() => ({ data: null, isLoading: false })),
}))

const mockUseCredentials = vi.fn()
vi.mock('@/lib/hooks/use-credentials', () => ({
  useCredentials: () => mockUseCredentials(),
  useCredentialStatus: vi.fn(() => ({
    data: { configured: {}, source: {}, encryption_configured: true },
  })),
  useEnvStatus: vi.fn(() => ({ data: {} })),
}))

const mockUseProviders = vi.fn()
vi.mock('@/lib/hooks/use-providers', () => ({
  useProviders: () => mockUseProviders(),
}))

const providers: ProviderInfo[] = [
  {
    name: 'openai',
    display_name: 'OpenAI',
    modalities: ['language'],
    docs_url: null,
    env_configured: false,
  },
  {
    name: 'anthropic',
    display_name: 'Anthropic',
    modalities: ['language'],
    docs_url: null,
    env_configured: false,
  },
]

const anthropicCredential = {
  id: 'credential:1',
  name: 'Anthropic Prod',
  provider: 'anthropic',
  modalities: ['language'],
  has_api_key: true,
  created: '2026-01-01T00:00:00Z',
  updated: '2026-01-01T00:00:00Z',
  model_count: 0,
} as Credential

describe('ApiKeysPage', () => {
  beforeEach(() => {
    mockUseCredentials.mockReturnValue({ data: [], isLoading: false })
    mockUseProviders.mockReturnValue({
      data: providers,
      isLoading: false,
      isError: false,
    })
  })

  it('renders one section per provider from GET /api/providers', () => {
    render(<ApiKeysPage />)
    const sections = screen.getAllByTestId('provider-section')
    expect(sections.map(s => s.textContent)).toEqual(['OpenAI', 'Anthropic'])
  })

  it('sorts configured providers first, keeping backend order otherwise', () => {
    mockUseCredentials.mockReturnValue({
      data: [anthropicCredential],
      isLoading: false,
    })
    render(<ApiKeysPage />)
    const sections = screen.getAllByTestId('provider-section')
    expect(sections.map(s => s.textContent)).toEqual(['Anthropic', 'OpenAI'])
  })

  it('shows a loading state while the provider list loads', () => {
    mockUseProviders.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    })
    render(<ApiKeysPage />)
    expect(screen.queryAllByTestId('provider-section')).toHaveLength(0)
  })

  it('shows an error state when the provider list fails to load', () => {
    mockUseProviders.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    })
    render(<ApiKeysPage />)
    expect(screen.getByText('apiKeys.providersLoadFailed')).toBeInTheDocument()
    expect(
      screen.getByText('apiKeys.providersLoadFailedDescription')
    ).toBeInTheDocument()
    expect(screen.queryAllByTestId('provider-section')).toHaveLength(0)
  })
})
