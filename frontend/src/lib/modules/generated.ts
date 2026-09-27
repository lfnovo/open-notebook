// Core build: no optional UI modules. scripts/prepare_modules.py generates this in a staging directory.
import type { ModuleEntry } from './types'
export const moduleEntries: Record<string, ModuleEntry> = {}
