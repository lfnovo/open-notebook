import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { enUS } from '@/lib/locales/en-US'
import { CredentialFormDialog } from './CredentialFormDialog'

// useTranslation is mocked globally in setup.ts (t returns the key string)

vi.mock('@/lib/hooks/use-credentials', () => ({
  useCreateCredential: () => ({ isPending: false, mutate: vi.fn() }),
  useUpdateCredential: () => ({ isPending: false, mutate: vi.fn() }),
}))

vi.mock('@/lib/hooks/use-providers', () => ({
  useProviders: () => ({ data: [] }),
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
})
