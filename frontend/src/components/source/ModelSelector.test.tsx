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
  useTeams: vi.fn(() => ({
    data: {
      items: [
        {
          id: 'team:research',
          type: 'workspace',
          current_user_role: 'member',
          can_manage: false,
        },
      ],
    },
  })),
  useTeamModelDefaults: vi.fn(() => ({
    data: { default_chat_model: 'model:team-chat' },
  })),
}))

afterEach(() => {
  vi.clearAllMocks()
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

  it('shows the system default chat model for admins', () => {
    act(() => {
      useAuthStore.setState({ role: 'admin', username: 'admin' })
    })

    render(<ModelSelector onModelChange={vi.fn()} />)

    expect(screen.getByRole('button', { name: /System Chat/i })).toBeEnabled()
  })
})
