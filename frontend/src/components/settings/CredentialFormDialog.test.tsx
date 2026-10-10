import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { Credential } from '@/lib/api/credentials'
import { enUS } from '@/lib/locales/en-US'
import { CredentialFormDialog } from './CredentialFormDialog'

// useTranslation is mocked globally in setup.ts (t returns the key string)

const createMutate = vi.hoisted(() => vi.fn())

vi.mock('@/lib/hooks/use-credentials', () => ({
  useCreateCredential: () => ({ isPending: false, mutate: createMutate }),
  useUpdateCredential: () => ({ isPending: false, mutate: vi.fn() }),
}))

// Only Azure comes with registry metadata here, like GET /api/providers
const providers = vi.hoisted(() => [
  {
    name: 'azure',
    display_name: 'Azure OpenAI',
    modalities: ['language'],
    env_configured: false,
    default_api_version: '2024-10-21',
  },
])

vi.mock('@/lib/hooks/use-providers', () => ({
  useProviders: () => ({ data: providers }),
}))

function renderDialog(provider: string) {
  return render(
    <CredentialFormDialog
      open
      onOpenChange={vi.fn()}
      provider={provider}
    />,
  )
}

describe('CredentialFormDialog', () => {
  it('shows the version-path hint for OpenAI-compatible providers', () => {
    renderDialog('openai_compatible')

    expect(
      screen.getByText('apiKeys.openAICompatibleBaseUrlHint'),
    ).toBeInTheDocument()
    expect(
      screen.queryByText('apiKeys.baseUrlOverrideHint'),
    ).not.toBeInTheDocument()
    expect(screen.getByLabelText('apiKeys.baseUrl')).toHaveValue('')
    expect(enUS.apiKeys.openAICompatibleBaseUrlHint).toContain(
      'http://host.docker.internal:1234/v1',
    )
  })

  it('keeps the generic Base URL hint for other URL-based providers', () => {
    renderDialog('ollama')

    expect(screen.getByText('apiKeys.baseUrlOverrideHint')).toBeInTheDocument()
    expect(
      screen.queryByText('apiKeys.openAICompatibleBaseUrlHint'),
    ).not.toBeInTheDocument()
  })

  it('prefills the Azure API version and sends it when creating', () => {
    renderDialog('azure')

    expect(screen.getByLabelText('apiKeys.apiVersion')).toHaveValue('2024-10-21')

    fireEvent.change(screen.getByLabelText('apiKeys.configName'), {
      target: { value: 'Work Azure' },
    })
    fireEvent.change(screen.getByLabelText('models.apiKey'), {
      target: { value: 'azure-key' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'apiKeys.addConfig' }))

    expect(createMutate).toHaveBeenCalledWith(
      expect.objectContaining({ provider: 'azure', api_version: '2024-10-21' }),
      expect.anything(),
    )
  })

  it('shows the saved API version when editing an Azure credential', () => {
    const credential: Credential = {
      id: 'credential:azure',
      name: 'Work Azure',
      provider: 'azure',
      modalities: ['language'],
      api_version: '2025-01-01-preview',
      has_api_key: true,
      created: '2026-01-01',
      updated: '2026-01-01',
      model_count: 0,
    }
    render(
      <CredentialFormDialog
        open
        onOpenChange={vi.fn()}
        provider="azure"
        credential={credential}
      />,
    )

    expect(screen.getByLabelText('apiKeys.apiVersion')).toHaveValue(
      '2025-01-01-preview',
    )
  })

  it('has no API version field for other providers', () => {
    renderDialog('openai')

    expect(screen.queryByLabelText('apiKeys.apiVersion')).not.toBeInTheDocument()
  })
})
