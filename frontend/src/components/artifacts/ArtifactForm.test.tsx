import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render } from '@testing-library/react'

// Radix Select measures its trigger via ResizeObserver, which jsdom lacks.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal('ResizeObserver', ResizeObserverStub)

import { ArtifactForm, defaultArtifactLanguage } from './ArtifactForm'
import { useArtifactFormStore } from '@/lib/stores/artifact-form-store'

describe('defaultArtifactLanguage', () => {
  it('maps a regional UI language to its base code', () => {
    expect(defaultArtifactLanguage('it-IT')).toBe('it')
    expect(defaultArtifactLanguage('en-US')).toBe('en')
    expect(defaultArtifactLanguage('zh-CN')).toBe('zh')
    expect(defaultArtifactLanguage('ru-RU')).toBe('ru')
  })

  it('accepts a bare language code', () => {
    expect(defaultArtifactLanguage('fr')).toBe('fr')
  })

  it('falls back to English for unsupported or empty languages', () => {
    expect(defaultArtifactLanguage('')).toBe('en')
    expect(defaultArtifactLanguage('xx-YY')).toBe('en')
  })
})

describe('ArtifactForm remembers the type', () => {
  const notebooks = [{ id: 'notebook:1', name: 'Notebook' }]

  beforeEach(() => {
    localStorage.clear()
    useArtifactFormStore.setState({ kind: 'report', variant: 'document' })
  })

  function submit() {
    const onSubmit = vi.fn()
    const { container } = render(
      <ArtifactForm notebooks={notebooks} submitting={false} onSubmit={onSubmit} />
    )
    fireEvent.submit(container.querySelector('form') as HTMLFormElement)
    return onSubmit
  }

  it('submits a report when nothing was chosen before', () => {
    expect(submit()).toHaveBeenCalledWith(expect.objectContaining({ kind: 'report' }))
  })

  it('submits the type remembered from a previous visit', () => {
    useArtifactFormStore.setState({ kind: 'deck', variant: 'presenter' })
    expect(submit()).toHaveBeenCalledWith(expect.objectContaining({ kind: 'deck' }))
  })

  it('persists the chosen type', () => {
    useArtifactFormStore.getState().setKind('deck')
    expect(localStorage.getItem('artifact-form-storage')).toContain('deck')
  })

  it('refuses an unknown type instead of passing it on', () => {
    useArtifactFormStore.getState().setKind('slides' as never)
    expect(useArtifactFormStore.getState().kind).toBe('report')
  })

  it('ignores an unknown type stored by an older version', async () => {
    localStorage.setItem(
      'artifact-form-storage',
      JSON.stringify({ state: { kind: 'poster' }, version: 0 })
    )
    // rehydrate() is what the persist middleware does on load; the merge guard
    // must keep the form usable rather than hand a bad value to the Select.
    await useArtifactFormStore.persist.rehydrate()
    expect(useArtifactFormStore.getState().kind).toBe('report')
  })
})

describe('ArtifactForm remembers the style', () => {
  const notebooks = [{ id: 'notebook:1', name: 'Notebook' }]

  beforeEach(() => {
    localStorage.clear()
    useArtifactFormStore.setState({ kind: 'report', variant: 'document' })
  })

  function submit() {
    const onSubmit = vi.fn()
    const { container } = render(
      <ArtifactForm notebooks={notebooks} submitting={false} onSubmit={onSubmit} />
    )
    fireEvent.submit(container.querySelector('form') as HTMLFormElement)
    return onSubmit
  }

  it('submits a plain document when nothing was chosen before', () => {
    expect(submit()).toHaveBeenCalledWith(
      expect.objectContaining({ kind: 'report', variant: 'document' })
    )
  })

  it('submits the style remembered from a previous visit', () => {
    useArtifactFormStore.setState({ kind: 'report', variant: 'illustrated' })

    expect(submit()).toHaveBeenCalledWith(
      expect.objectContaining({ variant: 'illustrated' })
    )
  })

  it('refuses a style belonging to the other type', () => {
    useArtifactFormStore.getState().setVariant('presenter' as never)
    expect(useArtifactFormStore.getState().variant).toBe('document')
  })

  it('resets the style when the type changes', () => {
    useArtifactFormStore.getState().setVariant('illustrated')
    useArtifactFormStore.getState().setKind('deck')
    expect(useArtifactFormStore.getState().variant).toBe('presenter')
  })

  it('drops a style stored for the other type by an older version', async () => {
    localStorage.setItem(
      'artifact-form-storage',
      JSON.stringify({
        state: { kind: 'deck', variant: 'illustrated' },
        version: 0,
      })
    )
    await useArtifactFormStore.persist.rehydrate()
    expect(useArtifactFormStore.getState().kind).toBe('deck')
    expect(useArtifactFormStore.getState().variant).toBe('presenter')
  })
})
