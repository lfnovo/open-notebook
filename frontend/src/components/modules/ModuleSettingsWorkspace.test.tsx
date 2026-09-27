import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ModuleSettingsWorkspace } from './ModuleSettingsWorkspace'
import { useModules, useModuleUpdate } from '@/lib/modules/hooks'
import type { ModuleInfo } from '@/lib/modules/types'
vi.mock('@/lib/modules/hooks', () => ({ useModules: vi.fn(), useModuleUpdate: vi.fn() }))
const mutation = { mutate: vi.fn(), reset: vi.fn(), isPending: false, isSuccess: false, error: null }
const audio: ModuleInfo = { id: 'local-audio', name: 'Audio', description: '', version: '1', activation: 'external', dependencies: [], installed: true, enabled: true, active: true, revision: 2, frontend: null, settings: { timeout_seconds: 600 }, settings_schema: [{ key: 'timeout_seconds', kind: 'integer', default: 300, minimum: 30, maximum: 7200, options: [], label_key: 'timeout-label', help_key: 'timeout-help' }] }
const load = (data: ModuleInfo[]) => vi.mocked(useModules).mockReturnValue({ data, isLoading: false } as ReturnType<typeof useModules>)
beforeEach(() => { vi.clearAllMocks(); load([audio]); vi.mocked(useModuleUpdate).mockReturnValue(mutation as unknown as ReturnType<typeof useModuleUpdate>) })
describe('Module settings UI', () => {
  it('allows external integration toggles and submits explicit state with a revision', () => {
    render(<ModuleSettingsWorkspace />)
    fireEvent.click(screen.getByRole('switch', { name: 'modules.useModule' }))
    expect(mutation.mutate).toHaveBeenCalledWith({ id: 'local-audio', enabled: false, expected_revision: 2 })
  })
  it('retains a draft during polling and shows conflicts instead of overwriting it', () => {
    const { rerender } = render(<ModuleSettingsWorkspace />)
    fireEvent.change(screen.getByLabelText('timeout-label'), { target: { value: '900' } })
    load([{ ...audio, revision: 3, settings: { timeout_seconds: 1200 } }])
    rerender(<ModuleSettingsWorkspace />)
    expect(screen.getByLabelText('timeout-label')).toHaveValue(900)
    expect(screen.getByText('modules.conflict')).toBeVisible()
    expect(screen.getByRole('button', { name: 'modules.save' })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'modules.discard' }))
    expect(screen.getByLabelText('timeout-label')).toHaveValue(1200)
  })
  it('explains dependency restrictions', () => {
    load([audio, { ...audio, id: 'another', dependencies: ['local-audio'] }])
    render(<ModuleSettingsWorkspace />)
    expect(screen.getByRole('switch', { name: 'modules.useModule' })).toBeDisabled()
    expect(screen.getByText('modules.disableDependencies')).toBeVisible()
  })
  it('shows desired-off but still-applied build changes honestly', () => {
    load([{ ...audio, activation: 'build', enabled: false, active: true, pending_build: true }])
    render(<ModuleSettingsWorkspace />)
    expect(screen.getByRole('switch', { name: 'modules.useModule' })).not.toBeChecked()
    expect(screen.getByText('modules.pendingBuildHelp')).toBeVisible()
  })
})
