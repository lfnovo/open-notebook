import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ProviderSection } from './ProviderSection'
import { ProviderInfo } from '@/lib/api/providers'

// useTranslation is mocked globally in setup.ts (t returns the key string)

vi.mock('./CredentialFormDialog', () => ({
  CredentialFormDialog: () => <div data-testid="credential-form-dialog" />,
}))

vi.mock('./CredentialItem', () => ({
  CredentialItem: () => <div data-testid="credential-item" />,
}))

function makeProvider(overrides: Partial<ProviderInfo> = {}): ProviderInfo {
  return {
    name: 'openai',
    display_name: 'OpenAI',
    modalities: ['language', 'embedding'],
    docs_url: 'https://platform.openai.com/api-keys',
    env_configured: false,
    ...overrides,
  }
}

function renderSection(provider: ProviderInfo) {
  return render(
    <ProviderSection
      provider={provider}
      credentials={[]}
      models={[]}
      defaults={null}
      allCredentials={[]}
      encryptionReady={true}
    />
  )
}

describe('ProviderSection', () => {
  it('renders the display name from the backend registry', () => {
    renderSection(makeProvider())
    expect(screen.getByText('OpenAI')).toBeInTheDocument()
  })

  it('renders one modality badge per registry modality', () => {
    renderSection(makeProvider())
    expect(screen.getByText('Language')).toBeInTheDocument()
    expect(screen.getByText('Embedding')).toBeInTheDocument()
  })

  it('renders providers the frontend has never seen, with a fallback icon', () => {
    // "Zero frontend edits to add a provider": a brand-new provider with a
    // brand-new modality must render (raw label + generic icon), not break.
    const { container } = renderSection(
      makeProvider({
        name: 'newprovider',
        display_name: 'Brand New Provider',
        modalities: ['language', 'holograms'],
      })
    )
    expect(screen.getByText('Brand New Provider')).toBeInTheDocument()
    expect(screen.getByText('holograms')).toBeInTheDocument()
    // The unknown modality badge still carries an icon (the fallback one)
    const badges = container.querySelectorAll('svg')
    expect(badges.length).toBeGreaterThanOrEqual(2)
  })
})
