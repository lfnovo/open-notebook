/* eslint-disable @typescript-eslint/no-explicit-any */
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import TeamsPage from './page'
import {
  useActiveUsers,
  useCreateTeam,
  useDeleteTeam,
  useRemoveTeamMember,
  useTeamMembers,
  useTeamModels,
  useTeamTransformations,
  useTeams,
  useUpdateTeam,
  useUpdateTeamModels,
  useUpdateTeamTransformations,
  useUpsertTeamMember,
} from '@/lib/hooks/use-teams'
import { useModels } from '@/lib/hooks/use-models'
import { useTransformations } from '@/lib/hooks/use-transformations'
import { enUS } from '@/lib/locales/en-US'
import { zhCN } from '@/lib/locales/zh-CN'
import { useAuthStore } from '@/lib/stores/auth-store'

vi.mock('@/lib/hooks/use-teams', () => ({
  useTeams: vi.fn(),
  useTeamMembers: vi.fn(),
  useActiveUsers: vi.fn(),
  useCreateTeam: vi.fn(),
  useUpdateTeam: vi.fn(),
  useDeleteTeam: vi.fn(),
  useUpsertTeamMember: vi.fn(),
  useRemoveTeamMember: vi.fn(),
  useTeamModels: vi.fn(),
  useUpdateTeamModels: vi.fn(),
  useTeamTransformations: vi.fn(),
  useUpdateTeamTransformations: vi.fn(),
}))

vi.mock('@/lib/hooks/use-models', () => ({
  useModels: vi.fn(),
}))

vi.mock('@/lib/hooks/use-transformations', () => ({
  useTransformations: vi.fn(),
}))

describe('TeamsPage', () => {
  beforeEach(() => {
    useAuthStore.setState({ role: 'admin' })
    vi.mocked(useTeams).mockReturnValue({
      data: {
        items: [
          {
            id: 'team:research',
            slug: 'research',
            name: 'Research',
            type: 'workspace',
            created: '2026-05-05T00:00:00Z',
            updated: '2026-05-05T00:00:00Z',
            member_count: 1,
            share_count: 0,
            current_user_role: 'admin',
            can_manage: true,
          },
        ],
      },
      isLoading: false,
      error: null,
    } as any)
    vi.mocked(useTeamMembers).mockReturnValue({ data: [], isLoading: false, error: null } as any)
    vi.mocked(useActiveUsers).mockReturnValue({
      data: {
        items: [
          {
            id: 'app_user:owner',
            username: 'owner',
            display_name: 'Owner User',
            email: 'owner@example.com',
            role: 'user',
            status: 'active',
          },
        ],
      },
      isLoading: false,
    } as any)
    vi.mocked(useCreateTeam).mockReturnValue({ mutate: vi.fn(), isPending: false } as any)
    vi.mocked(useUpdateTeam).mockReturnValue({ mutate: vi.fn(), isPending: false } as any)
    vi.mocked(useDeleteTeam).mockReturnValue({ mutate: vi.fn(), isPending: false } as any)
    vi.mocked(useUpsertTeamMember).mockReturnValue({ mutate: vi.fn(), isPending: false } as any)
    vi.mocked(useRemoveTeamMember).mockReturnValue({ mutate: vi.fn(), isPending: false } as any)
    vi.mocked(useTeamModels).mockReturnValue({
      data: { team_id: 'team:research', model_ids: ['model:chat'], models: [] },
      isLoading: false,
    } as any)
    vi.mocked(useUpdateTeamModels).mockReturnValue({ mutate: vi.fn(), isPending: false } as any)
    vi.mocked(useTeamTransformations).mockReturnValue({
      data: {
        team_id: 'team:research',
        transformation_ids: ['transformation:summary'],
        transformations: [],
      },
      isLoading: false,
    } as any)
    vi.mocked(useUpdateTeamTransformations).mockReturnValue({ mutate: vi.fn(), isPending: false } as any)
    vi.mocked(useModels).mockReturnValue({
      data: [
        {
          id: 'model:chat',
          name: 'Chat',
          provider: 'openai',
          type: 'language',
          created: '2026-05-05T00:00:00Z',
          updated: '2026-05-05T00:00:00Z',
        },
      ],
      isLoading: false,
    } as any)
    vi.mocked(useTransformations).mockReturnValue({
      data: [
        {
          id: 'transformation:summary',
          name: 'summary',
          title: 'Summary',
          description: 'Summarize text',
          prompt: 'Summarize',
          apply_default: false,
          created: '2026-05-05T00:00:00Z',
          updated: '2026-05-05T00:00:00Z',
        },
      ],
      isLoading: false,
    } as any)
  })

  it('renders team-scoped model and transformation selection without system configuration actions', async () => {
    render(<TeamsPage />)

    expect(await screen.findByText('Allowed models')).toBeInTheDocument()
    expect(screen.getByText('Allowed transformations')).toBeInTheDocument()
    expect(screen.getByLabelText('Chat')).toBeChecked()
    expect(screen.getByLabelText('Summary')).toBeChecked()
    expect(screen.queryByText('Add Config')).not.toBeInTheDocument()
    expect(screen.queryByText('Create Transformation')).not.toBeInTheDocument()
  })

  it('has localized copy for the team slug label', () => {
    expect(enUS.teams.slugLabel).toBe('Slug')
    expect(zhCN.teams.slugLabel).toBe('标识')
  })

  it('requires selecting an owner when creating a team', async () => {
    render(<TeamsPage />)

    fireEvent.click(screen.getByRole('button', { name: 'Create Team' }))

    expect(await screen.findByText('Owner')).toBeInTheDocument()
    expect(screen.getByText('Select an owner')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Save' })).toBeDisabled()
  })
})
