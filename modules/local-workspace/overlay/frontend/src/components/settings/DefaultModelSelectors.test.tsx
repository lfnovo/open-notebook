import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import { DefaultModelSelectors } from './DefaultModelSelectors'
import { enUS } from '@/lib/locales/en-US'
import type { Model, ModelDefaults } from '@/lib/types/models'

const state = vi.hoisted(() => ({
  update: { mutate: vi.fn(), reset: vi.fn(), isPending: false, isError: false, isSuccess: false },
  auto: { mutate: vi.fn(), reset: vi.fn(), isPending: false, isError: false, isSuccess: false },
}))
vi.mock('@/lib/hooks/use-models', () => ({
  useUpdateModelDefaults: () => state.update,
  useAutoAssignDefaults: () => state.auto,
}))
vi.mock('@/lib/hooks/use-translation', () => ({ useTranslation: () => ({
  t: (key: string, args: Record<string, string> = {}) => {
    const value = key.split('.').reduce<unknown>((result, part) => (result as Record<string, unknown>)[part], enUS)
    return String(value ?? key).replace(/\{\{(\w+)\}\}/g, (_, name) => args[name] ?? '')
  },
}) }))
vi.mock('./EmbeddingModelChangeDialog', () => ({
  EmbeddingModelChangeDialog: ({ open, onConfirm, onOpenChange }: { open: boolean; onConfirm: () => void; onOpenChange: (open: boolean) => void }) => open
    ? <div role="alertdialog"><button onClick={onConfirm}>Confirm embedding change</button><button onClick={() => onOpenChange(false)}>Cancel embedding change</button></div> : null,
}))

const model = (id: string, type: Model['type'] = 'language'): Model => ({ id, name: id, type, provider: 'test-provider', created: '', updated: '' })
const models = [model('chat'), model('other-chat'), model('embedding', 'embedding'), model('other-embedding', 'embedding'), model('voice', 'text_to_speech')]
const defaults: ModelDefaults = { default_chat_model: 'chat', default_embedding_model: 'embedding', default_text_to_speech_model: 'voice', default_tools_model: 'other-chat' }
const advanced = () => screen.getByRole('button', { name: /^Advanced/ })

beforeEach(() => {
  vi.clearAllMocks()
  for (const mutation of [state.update, state.auto]) Object.assign(mutation, { isPending: false, isError: false, isSuccess: false })
  HTMLElement.prototype.scrollIntoView = vi.fn()
  HTMLElement.prototype.hasPointerCapture = vi.fn(() => false)
  HTMLElement.prototype.releasePointerCapture = vi.fn()
})
afterEach(cleanup)

describe('model assignment interactions', () => {
  it('reveals advanced slots without writing settings', () => {
    render(<DefaultModelSelectors models={models} defaults={defaults} />)
    expect(advanced()).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByRole('combobox', { name: 'Tools Model' })).not.toBeInTheDocument()
    fireEvent.click(advanced())
    expect(screen.getByRole('combobox', { name: 'Tools Model' })).toBeVisible()
    expect(state.update.mutate).not.toHaveBeenCalled()
  })

  it('clears only the chosen optional assignment and explains fallback', () => {
    const { rerender } = render(<DefaultModelSelectors models={models} defaults={defaults} />)
    fireEvent.click(advanced())
    fireEvent.click(screen.getByRole('button', { name: 'Clear Tools Model selection' }))
    expect(state.update.mutate).toHaveBeenCalledExactlyOnceWith({ default_tools_model: null })
    rerender(<DefaultModelSelectors models={models} defaults={{ ...defaults, default_tools_model: null }} />)
    expect(screen.getAllByText(/Using chat model \(chat\)/).length).toBeGreaterThan(0)
  })

  it('blocks repeated changes while saving', () => {
    state.update.isPending = true
    render(<DefaultModelSelectors models={models} defaults={defaults} />)
    expect(screen.getByRole('status')).toHaveTextContent('Saving...')
    expect(screen.getByRole('combobox', { name: /Chat Model/ })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Clear Text-to-Speech Model selection' }))
    expect(state.update.mutate).not.toHaveBeenCalled()
  })

  it('keeps the confirmed server selection after a save error', () => {
    state.update.isError = true
    render(<DefaultModelSelectors models={models} defaults={defaults} />)
    expect(screen.getByRole('status')).toHaveTextContent('Could not save')
    expect(screen.getByRole('combobox', { name: /Chat Model/ })).toHaveTextContent('chat')
  })

  it('requires confirmation before changing the embedding model', () => {
    render(<DefaultModelSelectors models={models} defaults={defaults} />)
    fireEvent.keyDown(screen.getByRole('combobox', { name: /Embedding Model/ }), { key: 'ArrowDown' })
    fireEvent.click(screen.getByRole('option', { name: /other-embedding/ }))
    expect(screen.getByRole('alertdialog')).toBeVisible()
    expect(state.update.mutate).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Cancel embedding change' }))
    expect(state.update.mutate).not.toHaveBeenCalled()
    fireEvent.keyDown(screen.getByRole('combobox', { name: /Embedding Model/ }), { key: 'ArrowDown' })
    fireEvent.click(screen.getByRole('option', { name: /other-embedding/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Confirm embedding change' }))
    expect(state.update.mutate).toHaveBeenCalledExactlyOnceWith({ default_embedding_model: 'other-embedding' })
  })

  it('identifies unavailable assignments and supports missing-model recovery', () => {
    render(<DefaultModelSelectors models={[]} defaults={defaults} />)
    expect(screen.getByRole('combobox', { name: /Chat Model/ })).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getAllByText('This model is no longer available. Choose another model.').length).toBeGreaterThan(0)
    fireEvent.click(screen.getByRole('button', { name: 'Auto-assign Defaults' }))
    expect(state.auto.mutate).toHaveBeenCalledOnce()
    expect(models.map(item => item.id)).toEqual(['chat', 'other-chat', 'embedding', 'other-embedding', 'voice'])
  })
})
