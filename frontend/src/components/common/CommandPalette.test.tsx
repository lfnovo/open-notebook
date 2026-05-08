import { describe, expect, it } from 'vitest'
import { enUS } from '@/lib/locales'
import { getCommandCreateItems, getCommandNavigationItems } from './CommandPalette'

describe('CommandPalette permission model', () => {
  it('does not expose resource creation, advanced, or knowledge exploration for system admins', () => {
    const navigation = getCommandNavigationItems(enUS, {
      isAdmin: true,
      canManageTeams: false,
      hasTeams: false,
    }).map((item) => item.name)
    const createItems = getCommandCreateItems(enUS, { isAdmin: true })

    expect(navigation).toContain('Models')
    expect(navigation).toContain('Transformations')
    expect(navigation).toContain('Settings')
    expect(navigation).not.toContain('Knowledge Explorer')
    expect(navigation).not.toContain('Advanced')
    expect(createItems).toEqual([])
  })

  it('exposes advanced tools for team managers but not system settings', () => {
    const navigation = getCommandNavigationItems(enUS, {
      isAdmin: false,
      canManageTeams: true,
      hasTeams: true,
    }).map((item) => item.name)

    expect(navigation).toContain('Advanced')
    expect(navigation).toContain('Teams')
    expect(navigation).not.toContain('Models')
    expect(navigation).not.toContain('Settings')
  })
})
