import type { ModuleInfo, ModuleSettings, SettingValue } from './types'

/** Immutable edit session. A polling refresh never overwrites unsaved choices. */
export class ModuleSettingsDraft {
  readonly revision: number
  readonly values: ModuleSettings
  constructor(readonly module: ModuleInfo, values?: ModuleSettings) {
    this.revision = module.revision ?? 0
    this.values = { ...(values ?? module.settings ?? {}) }
  }
  withValue(key: string, value: SettingValue) {
    return new ModuleSettingsDraft(this.module, { ...this.values, [key]: value })
  }
  defaults() {
    return new ModuleSettingsDraft(this.module, Object.fromEntries((this.module.settings_schema ?? []).map(field => [field.key, field.default])))
  }
  get dirty() { return JSON.stringify(this.values) !== JSON.stringify(this.module.settings ?? {}) }
  get valid() {
    return (this.module.settings_schema ?? []).every(field => {
      const value = this.values[field.key]
      if (field.kind === 'boolean') return typeof value === 'boolean'
      if (field.kind === 'integer') return typeof value === 'number' && Number.isInteger(value) && (field.minimum == null || value >= field.minimum) && (field.maximum == null || value <= field.maximum)
      if (field.kind === 'choice') return typeof value === 'string' && field.options.includes(value)
      return typeof value === 'string' && value.trim().length > 0 && value.length <= 120
    })
  }
}
