import { act, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '@/lib/stores/auth-store'
import { ModelSelector } from './ModelSelector'

vi.mock('@/lib/hooks/use-models', () => ({
  useModels: vi.fn(() => ({
    data: [
      { id: 'model:system-chat', name: 'System Chat', provider: 'openai', type: 'language' },
      { id: 'model:team-chat', name: 'Team Chat', provider: 'openai', type: 'language' },
    ],
    isLoading: false,
  })),
  useModelDefaults: vi.fn(() => ({
    data: { default_chat_model: 'model:system-chat' },
  })),
}))

vi.mock('@/lib/hooks/use-teams', () => ({
  useTeamModelDefaults: vi.fn(() => ({
    data: { default_chat_model: 'model:team-chat' },
  })),
}))

let currentWorkspace: {
  id: string
  type: 'personal' | 'team'
  team_id?: string | null
} | null = {
  id: 'workspace:team',
  type: 'team',
  team_id: 'team:research',
}

vi.mock('@/lib/hooks/use-workspaces', () => ({
  useCurrentWorkspace: () => ({
    currentWorkspace,
  }),
}))

afterEach(() => {
  vi.clearAllMocks()
  currentWorkspace = {
    id: 'workspace:team',
    type: 'team',
    team_id: 'team:research',
  }
  act(() => {
    useAuthStore.setState({ role: null, username: null })
  })
})

describe('source ModelSelector', () => {
  it('shows the single team default chat model for regular team members', () => {
    act(() => {
      useAuthStore.setState({ role: 'user', username: 'member' })
    })

    render(<ModelSelector onModelChange={vi.fn()} />)

    expect(screen.getByRole('button', { name: /Team Chat/i })).toBeDisabled()
  })

  it('shows the system default chat model in a personal workspace', () => {
    currentWorkspace = {
      id: 'workspace:personal',
      type: 'personal',
      team_id: null,
    }
    act(() => {
      useAuthStore.setState({ role: 'user', username: 'member' })
    })

    render(<ModelSelector onModelChange={vi.fn()} />)

    expect(screen.getByRole('button', { name: /System Chat/i })).toBeDisabled()
  })

  it('shows the system default chat model for admins', () => {
    act(() => {
      useAuthStore.setState({ role: 'admin', username: 'admin' })
    })

    render(<ModelSelector onModelChange={vi.fn()} />)

    expect(screen.getByRole('button', { name: /System Chat/i })).toBeEnabled()
  })
})
