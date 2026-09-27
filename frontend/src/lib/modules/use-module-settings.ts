'use client'
import { useState } from 'react'
import { useModuleUpdate } from './hooks'
import { ModuleSettingsDraft } from './settings-model'
import type { ModuleInfo, SettingValue } from './types'

/** MVVM: edit state, validation and commands; no markup or network details. */
export function useModuleSettings(module: ModuleInfo) {
  const mutation = useModuleUpdate()
  const [edited, setEdited] = useState<ModuleSettingsDraft | null>(null)
  const draft = edited ?? new ModuleSettingsDraft(module)
  const conflict = draft.dirty && draft.revision !== (module.revision ?? 0)
  const discard = () => { setEdited(null); mutation.reset() }
  return {
    draft, conflict, pending: mutation.isPending, error: mutation.error,
    saved: mutation.isSuccess && !draft.dirty,
    change: (key: string, value: SettingValue) => { mutation.reset(); setEdited(draft.withValue(key, value)) },
    defaults: () => { mutation.reset(); setEdited(draft.defaults()) }, discard,
    toggle: () => mutation.mutate({ id: module.id, enabled: !module.enabled, expected_revision: module.revision }),
    save: () => mutation.mutate({ id: module.id, settings: draft.values, expected_revision: draft.revision }, { onSuccess: () => setEdited(null) }),
  }
}
