import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'

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

import { useSettings, useUpdateSettings } from '@/lib/hooks/use-settings'
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

describe('SettingsForm vision endpoint fields', () => {
  const visionUrl = 'http://192.168.1.20:1234/v1/chat/completions'

  function mockSettings(overrides: Record<string, unknown>) {
    ;(useSettings as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      data: { ...settingsData, ...overrides },
      isLoading: false,
      error: null,
    })
    ;(useCapabilities as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      data: { docling_available: true, crawl4ai_available: true, crawl4ai_remote_configured: false },
      isError: false,
    })
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('hides the endpoint fields while image description is off', () => {
    mockSettings({ docling_vision: false, docling_vision_url: visionUrl })
    render(<SettingsForm />)

    expect(screen.queryByLabelText('settings.visionUrl')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('settings.visionModel')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('settings.visionPrompt')).not.toBeInTheDocument()
  })

  it('shows the stored endpoint fields while image description is on', () => {
    mockSettings({
      docling_vision: true,
      docling_vision_url: visionUrl,
      docling_vision_model: 'qwen2.5-vl-7b',
      docling_vision_prompt: null,
    })
    render(<SettingsForm />)

    expect(screen.getByLabelText('settings.visionUrl')).toHaveValue(visionUrl)
    expect(screen.getByLabelText('settings.visionModel')).toHaveValue('qwen2.5-vl-7b')
    // A null prompt (unset, env var applies) renders as an empty field.
    expect(screen.getByLabelText('settings.visionPrompt')).toHaveValue('')
  })

  it('reveals the endpoint fields when image description is turned on', () => {
    mockSettings({ docling_vision: false })
    render(<SettingsForm />)

    fireEvent.click(screen.getByRole('checkbox', { name: 'settings.visionEnabled' }))

    expect(screen.getByLabelText('settings.visionUrl')).toBeInTheDocument()
  })

  it('submits the edited endpoint fields', async () => {
    const mutateAsync = vi.fn()
    ;(useUpdateSettings as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      mutateAsync,
      isPending: false,
    })
    mockSettings({ docling_vision: true })
    render(<SettingsForm />)

    fireEvent.change(screen.getByLabelText('settings.visionUrl'), {
      target: { value: visionUrl },
    })
    fireEvent.change(screen.getByLabelText('settings.visionModel'), {
      target: { value: 'qwen2.5-vl-7b' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'common.save' }))

    await waitFor(() => expect(mutateAsync).toHaveBeenCalledTimes(1))
    expect(mutateAsync.mock.calls[0][0]).toEqual(
      expect.objectContaining({
        docling_vision: true,
        docling_vision_url: visionUrl,
        docling_vision_model: 'qwen2.5-vl-7b',
        docling_vision_prompt: '',
      })
    )
  })
})
