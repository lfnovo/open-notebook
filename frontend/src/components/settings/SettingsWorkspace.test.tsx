import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { SettingsWorkspace } from './SettingsWorkspace'
vi.mock('@/components/layout/AppShell', () => ({ ResponsiveAppShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div> }))
vi.mock('@/lib/hooks/use-settings', () => ({ useSettings: () => ({ refetch: vi.fn(), isFetching: false }) }))
vi.mock('@/app/(dashboard)/settings/components/SettingsForm', () => ({ SettingsForm: () => <label>General setting<input defaultValue="saved" /></label> }))
vi.mock('@/components/modules/ModuleSettingsWorkspace', () => ({ ModuleSettingsWorkspace: () => <label>Module draft<input defaultValue="initial" /></label> }))
describe('Settings tabs', () => {
  it('opens General by default and preserves both forms when switching tabs', () => {
    render(<SettingsWorkspace />)
    expect(screen.getByRole('tab', { name: 'modules.general' })).toHaveAttribute('aria-selected', 'true')
    fireEvent.change(screen.getByLabelText('General setting'), { target: { value: 'unsaved' } })
    fireEvent.mouseDown(screen.getByRole('tab', { name: 'modules.settingsTab' }), { button: 0, ctrlKey: false })
    expect(screen.getByRole('tab', { name: 'modules.settingsTab' })).toHaveAttribute('aria-selected', 'true')
    fireEvent.change(screen.getByLabelText('Module draft'), { target: { value: 'keep me' } })
    fireEvent.mouseDown(screen.getByRole('tab', { name: 'modules.general' }), { button: 0, ctrlKey: false })
    expect(screen.getByLabelText('General setting')).toHaveValue('unsaved')
    expect(screen.getByLabelText('Module draft')).toHaveValue('keep me')
  })
  it('keeps legacy module settings links on the module tab', () => {
    render(<SettingsWorkspace initialTab="modules" />)
    expect(screen.getByRole('tab', { name: 'modules.settingsTab' })).toHaveAttribute('aria-selected', 'true')
  })
})
