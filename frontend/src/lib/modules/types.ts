import type { ComponentType } from 'react'

export type SettingValue = string | number | boolean
export type ModuleSettings = Record<string, SettingValue>
export type SettingSpec = {
  key: string; kind: 'boolean' | 'integer' | 'choice' | 'text'; default: SettingValue
  label_key: string; help_key: string; minimum: number | null; maximum: number | null; options: string[]
}
export type ModuleInfo = {
  id: string; name: string; description: string; version: string
  activation: 'runtime' | 'external' | 'build'; dependencies: string[]
  installed: boolean; enabled: boolean; active?: boolean; pending_build?: boolean
  revision?: number; settings?: ModuleSettings; settings_schema?: SettingSpec[]
  frontend: { route: string; label_key: string; section: string; icon: string } | null
}
export type ModuleUpdate = { id: string; enabled?: boolean; settings?: ModuleSettings; expected_revision?: number }
export type ModuleEntry = { SearchWidget?: ComponentType<{query:string}>
  Page: ComponentType; locales?: Record<string, Record<string, unknown>> }
