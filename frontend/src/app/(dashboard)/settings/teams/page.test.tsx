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
  useTeamModelDefaults,
  useTeamTransformations,
  useTeams,
  useUpdateTeam,
  useUpdateTeamModels,
  useUpdateTeamModelDefaults,
  useUpdateTeamTransformations,
  useUpsertTeamMember,
} from '@/lib/hooks/use-teams'
import { useModels } from '@/lib/hooks/use-models'
import { useTransformations } from '@/lib/hooks/use-transformations'
import {
  useUpdateWorkspacePolicy,
  useWorkspacePolicy,
  useWorkspaces,
} from '@/lib/hooks/use-workspaces'
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
  useTeamModelDefaults: vi.fn(),
  useUpdateTeamModelDefaults: vi.fn(),
  useTeamTransformations: vi.fn(),
  useUpdateTeamTransformations: vi.fn(),
}))

vi.mock('@/lib/hooks/use-models', () => ({
  useModels: vi.fn(),
}))

vi.mock('@/lib/hooks/use-transformations', () => ({
  useTransformations: vi.fn(),
}))

vi.mock('@/lib/hooks/use-workspaces', () => ({
  useWorkspaces: vi.fn(),
  useWorkspacePolicy: vi.fn(),
  useUpdateWorkspacePolicy: vi.fn(),
}))

describe('TeamsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
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
      data: {
        team_id: 'team:research',
        model_ids: ['model:chat', 'model:embed'],
        models: [
          {
            id: 'model:chat',
            name: 'Chat',
            provider: 'openai',
            type: 'language',
            created: '2026-05-05T00:00:00Z',
            updated: '2026-05-05T00:00:00Z',
          },
          {
            id: 'model:embed',
            name: 'Embed',
            provider: 'openai',
            type: 'embedding',
            created: '2026-05-05T00:00:00Z',
            updated: '2026-05-05T00:00:00Z',
          },
        ],
      },
      isLoading: false,
    } as any)
    vi.mocked(useUpdateTeamModels).mockReturnValue({ mutate: vi.fn(), isPending: false } as any)
    vi.mocked(useTeamModelDefaults).mockReturnValue({
      data: {
        team_id: 'team:research',
        default_chat_model: 'model:chat',
        default_embedding_model: null,
        default_transformation_model: null,
        default_tools_model: null,
        large_context_model: null,
      },
      isLoading: false,
    } as any)
    vi.mocked(useUpdateTeamModelDefaults).mockReturnValue({ mutate: vi.fn(), isPending: false } as any)
    vi.mocked(useTeamTransformations).mockReturnValue({
      data: {
        team_id: 'team:research',
        transformation_ids: ['transformation:summary'],
        transformations: [],
      },
      isLoading: false,
    } as any)
    vi.mocked(useUpdateTeamTransformations).mockReturnValue({ mutate: vi.fn(), isPending: false } as any)
    vi.mocked(useWorkspaces).mockReturnValue({
      data: {
        items: [
          {
            id: 'workspace:research',
            name: 'Research',
            type: 'team',
            team_id: 'team:research',
            owner_id: null,
            created_by: 'app_user:admin',
            created: '2026-05-05T00:00:00Z',
            updated: '2026-05-05T00:00:00Z',
            current_user_role: 'admin',
            can_manage: true,
          },
        ],
      },
      isLoading: false,
    } as any)
    vi.mocked(useWorkspacePolicy).mockReturnValue({
      data: {
        workspace_id: 'workspace:research',
        policy: {
          member_can_read: true,
          member_can_create_source: true,
          member_can_update_own_source: true,
          member_can_process_own_source: true,
          member_can_delete_own_source: false,
          member_can_remove_source: false,
          member_can_create_note: true,
          member_can_update_own_note: true,
          member_can_delete_own_note: true,
          member_can_delete_chat: false,
          member_can_update_notebook: false,
        },
        effective_policy: {
          member_can_read: true,
          member_can_create_source: true,
          member_can_update_own_source: true,
          member_can_process_own_source: true,
          member_can_delete_own_source: false,
          member_can_remove_source: false,
          member_can_create_note: true,
          member_can_update_own_note: true,
          member_can_delete_own_note: true,
          member_can_delete_chat: false,
          member_can_update_notebook: false,
        },
      },
      isLoading: false,
    } as any)
    vi.mocked(useUpdateWorkspacePolicy).mockReturnValue({ mutate: vi.fn(), isPending: false } as any)
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
        {
          id: 'model:embed',
          name: 'Embed',
          provider: 'openai',
          type: 'embedding',
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

  it('lets team owners choose team default models without changing available model scopes', async () => {
    useAuthStore.setState({ role: 'user' })
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
            current_user_role: 'owner',
            can_manage: true,
          },
        ],
      },
      isLoading: false,
      error: null,
    } as any)

    render(<TeamsPage />)

    expect(await screen.findByText('Team default models')).toBeInTheDocument()
    expect(screen.getByText('Chat Model')).toBeInTheDocument()
    expect(screen.queryByText('Allowed models')).not.toBeInTheDocument()
    expect(screen.queryByText('Allowed transformations')).not.toBeInTheDocument()
    expect(useTeamModelDefaults).toHaveBeenCalledWith('team:research')
  })

  it('shows workspace permission policy for team managers', async () => {
    render(<TeamsPage />)

    expect(await screen.findByText('Workspace permissions')).toBeInTheDocument()
    expect(screen.getByLabelText('Members can add sources')).toBeChecked()
    expect(screen.getByLabelText('Members can remove sources')).not.toBeChecked()
    expect(useWorkspacePolicy).toHaveBeenCalledWith('workspace:research')
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

  it('uses the team-scoped active user lookup when adding members', async () => {
    render(<TeamsPage />)

    fireEvent.click(screen.getByRole('button', { name: 'Add Member' }))

    expect(await screen.findByText('Select a user')).toBeInTheDocument()
    expect(useActiveUsers).toHaveBeenCalledWith('', 'team:research', true)
  })

  it('defaults to the first manageable workspace team and keeps the page scrollable', async () => {
    vi.mocked(useTeams).mockReturnValue({
      data: {
        items: [
          {
            id: 'team:public',
            slug: 'public',
            name: 'Public',
            type: 'system',
            created: '2026-05-05T00:00:00Z',
            updated: '2026-05-05T00:00:00Z',
            member_count: 0,
            share_count: 4,
            current_user_role: null,
            can_manage: false,
          },
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

    const { container } = render(<TeamsPage />)

    expect(await screen.findByRole('heading', { name: 'Research' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add Member' })).toBeEnabled()
    expect(container.firstElementChild).toHaveClass('overflow-y-auto')
  })

  it('shows team members their team without member or allowlist management controls', async () => {
    useAuthStore.setState({ role: 'user' })
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
            member_count: 3,
            share_count: 2,
            current_user_role: 'member',
            can_manage: false,
          },
        ],
      },
      isLoading: false,
      error: null,
    } as any)

    render(<TeamsPage />)

    expect(await screen.findByRole('heading', { name: 'Research' })).toBeInTheDocument()
    expect(screen.getByText('Member')).toBeInTheDocument()
    expect(screen.getAllByText('Members: 3').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Shares: 2').length).toBeGreaterThan(0)
    expect(screen.queryByRole('button', { name: 'Add Member' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Edit Team' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Delete Team' })).not.toBeInTheDocument()
    expect(screen.queryByText('Allowed models')).not.toBeInTheDocument()
    expect(screen.queryByText('Allowed transformations')).not.toBeInTheDocument()
    expect(useTeamMembers).not.toHaveBeenCalled()
    expect(useTeamModels).not.toHaveBeenCalled()
    expect(useTeamTransformations).not.toHaveBeenCalled()
  })
})
