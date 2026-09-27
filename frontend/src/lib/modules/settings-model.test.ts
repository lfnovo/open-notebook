import { describe, it, expect } from 'vitest'
import { ModuleSettingsDraft } from './settings-model'
import type { ModuleInfo } from './types'

const sampleModule: ModuleInfo = { id: 'sample', name: 'Sample', description: '', version: '1', activation: 'runtime', dependencies: [], installed: true, enabled: true, frontend: null, revision: 4,
  settings: { timeout: 600, language: 'Türkçe' }, settings_schema: [
    { key: 'timeout', kind: 'integer', default: 300, minimum: 30, maximum: 7200, options: [], label_key: '', help_key: '' },
    { key: 'language', kind: 'text', default: 'English', minimum: null, maximum: null, options: [], label_key: '', help_key: '' },
  ] }

describe('Module edit session', () => {
  it('isolates draft and revision from catalog polling', () => {
    const draft = new ModuleSettingsDraft(sampleModule).withValue('language', 'Deutsch')
    expect(sampleModule.settings?.language).toBe('Türkçe')
    expect(draft.values.language).toBe('Deutsch')
    expect(draft.revision).toBe(4)
    expect(draft.dirty).toBe(true)
  })
  it.each([NaN, 0, 8000, 1.5, '600'])('rejects invalid timeout %s', timeout => {
    expect(new ModuleSettingsDraft(sampleModule).withValue('timeout', timeout).valid).toBe(false)
  })
  it('restores defaults into an unsaved edit, not directly into the server', () => {
    const draft = new ModuleSettingsDraft(sampleModule).defaults()
    expect(draft.values).toEqual({ timeout: 300, language: 'English' })
    expect(draft.dirty && draft.valid).toBe(true)
    expect(sampleModule.settings?.timeout).toBe(600)
  })
})
