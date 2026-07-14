import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'

// Radix Select measures its trigger via ResizeObserver, which jsdom lacks.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal('ResizeObserver', ResizeObserverStub)

import { SettingsForm } from './SettingsForm'

// useTranslation is mocked globally in setup.ts (t returns the key string),
// so hint keys render as their literal key names below.

vi.mock('@/lib/hooks/use-settings', () => ({
  useSettings: vi.fn(),
  useUpdateSettings: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
}))

vi.mock('@/lib/hooks/use-capabilities', () => ({
  useCapabilities: vi.fn(),
}))

import { useSettings } from '@/lib/hooks/use-settings'
import { useCapabilities } from '@/lib/hooks/use-capabilities'

const settingsData = {
  default_content_processing_engine_doc: 'auto',
  default_content_processing_engine_url: 'auto',
  default_embedding_option: 'ask',
  auto_delete_files: 'no',
  docling_ocr: true,
}

function mockCapabilities(caps: unknown, { isError = false } = {}) {
  ;(useSettings as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
    data: settingsData,
    isLoading: false,
    error: null,
  })
  ;(useCapabilities as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
    data: caps,
    isError,
  })
}

describe('SettingsForm engine gating', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('disables OCR and shows env hints when the runtimes are unavailable', () => {
    mockCapabilities({
      docling_available: false,
      crawl4ai_available: false,
      crawl4ai_remote_configured: false,
    })
    render(<SettingsForm />)

    expect(screen.getByText('settings.enableDoclingHint')).toBeInTheDocument()
    expect(screen.getByText('settings.enableCrawl4aiHint')).toBeInTheDocument()
    // Target the OCR toggle by its accessible name (from the associated Label).
    expect(
      screen.getByRole('checkbox', { name: 'settings.ocrEnabled' })
    ).toBeDisabled()
  })

  it('enables OCR and hides the hints when the runtimes are available', () => {
    mockCapabilities({
      docling_available: true,
      crawl4ai_available: true,
      crawl4ai_remote_configured: false,
    })
    render(<SettingsForm />)

    expect(screen.queryByText('settings.enableDoclingHint')).not.toBeInTheDocument()
    expect(screen.queryByText('settings.enableCrawl4aiHint')).not.toBeInTheDocument()
    expect(
      screen.getByRole('checkbox', { name: 'settings.ocrEnabled' })
    ).not.toBeDisabled()
  })

  it('treats runtimes as available while the capability probe is still loading', () => {
    mockCapabilities(undefined)
    render(<SettingsForm />)

    // Optimistic default avoids a flash of disabled controls on a working setup.
    expect(screen.queryByText('settings.enableDoclingHint')).not.toBeInTheDocument()
    expect(
      screen.getByRole('checkbox', { name: 'settings.ocrEnabled' })
    ).not.toBeDisabled()
  })

  it('fails closed when the capability probe errors', () => {
    mockCapabilities(undefined, { isError: true })
    render(<SettingsForm />)

    // A failed probe must not advertise engines the backend couldn't verify.
    expect(screen.getByText('settings.enableDoclingHint')).toBeInTheDocument()
    expect(screen.getByText('settings.enableCrawl4aiHint')).toBeInTheDocument()
    expect(
      screen.getByRole('checkbox', { name: 'settings.ocrEnabled' })
    ).toBeDisabled()
  })
})
