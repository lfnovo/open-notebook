import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { teamsApi, TeamCreateRequest, TeamMemberUpsertRequest, TeamUpdateRequest } from '@/lib/api/teams'
import { usersApi } from '@/lib/api/users'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { useToast } from '@/lib/hooks/use-toast'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getApiErrorKey } from '@/lib/utils/error-handler'

export function useTeams(q?: string) {
  return useQuery({
    queryKey: [...QUERY_KEYS.teams, q || ''],
    queryFn: () => teamsApi.list({ q: q || undefined }),
  })
}

export function useCanManageTeams() {
  const { data } = useTeams()
  return Boolean(data?.items.some((team) => team.can_manage))
}

export function useHasTeams() {
  const { data } = useTeams()
  return Boolean(
    data?.items.some(
      (team) => team.type === 'workspace' && Boolean(team.current_user_role)
    )
  )
}

export function useTeamMembers(teamId?: string) {
  return useQuery({
    queryKey: teamId ? QUERY_KEYS.teamMembers(teamId) : ['teams', 'members', 'none'],
    queryFn: () => teamsApi.listMembers(teamId as string),
    enabled: !!teamId,
  })
}

export function useTeamModels(teamId?: string) {
  return useQuery({
    queryKey: teamId ? QUERY_KEYS.teamModels(teamId) : ['teams', 'models', 'none'],
    queryFn: () => teamsApi.listModels(teamId as string),
    enabled: !!teamId,
  })
}

export function useUpdateTeamModels(teamId: string) {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (modelIds: string[]) => teamsApi.updateModels(teamId, modelIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.teamModels(teamId) })
      toast({ title: t.common.success, description: t.teams.allowlistSaved })
    },
    onError: (error: unknown) => {
      toast({
        title: t.common.error,
        description: getApiErrorKey(error, t.common.error),
        variant: 'destructive',
      })
    },
  })
}

export function useTeamTransformations(teamId?: string) {
  return useQuery({
    queryKey: teamId ? QUERY_KEYS.teamTransformations(teamId) : ['teams', 'transformations', 'none'],
    queryFn: () => teamsApi.listTransformations(teamId as string),
    enabled: !!teamId,
  })
}

export function useUpdateTeamTransformations(teamId: string) {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (transformationIds: string[]) => teamsApi.updateTransformations(teamId, transformationIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.teamTransformations(teamId) })
      toast({ title: t.common.success, description: t.teams.allowlistSaved })
    },
    onError: (error: unknown) => {
      toast({
        title: t.common.error,
        description: getApiErrorKey(error, t.common.error),
        variant: 'destructive',
      })
    },
  })
}

export function useActiveUsers(q?: string, teamId?: string, enabled = true) {
  return useQuery({
    queryKey: teamId
      ? [...QUERY_KEYS.teams, teamId, 'assignable-users', q || '']
      : [...QUERY_KEYS.users, 'active', q || ''],
    queryFn: () =>
      teamId
        ? teamsApi.listAssignableUsers(teamId, { q: q || undefined, limit: 20 })
        : usersApi.list({ q: q || undefined, status: 'active', limit: 20 }),
    enabled,
  })
}

export function useCreateTeam() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (data: TeamCreateRequest) => teamsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.teams })
      toast({ title: t.common.success, description: t.teams.teamSaved })
    },
    onError: (error: unknown) => {
      toast({
        title: t.common.error,
        description: getApiErrorKey(error, t.common.error),
        variant: 'destructive',
      })
    },
  })
}

export function useUpdateTeam() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: ({ teamId, data }: { teamId: string; data: TeamUpdateRequest }) =>
      teamsApi.update(teamId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.teams })
      toast({ title: t.common.success, description: t.teams.teamSaved })
    },
    onError: (error: unknown) => {
      toast({
        title: t.common.error,
        description: getApiErrorKey(error, t.common.error),
        variant: 'destructive',
      })
    },
  })
}

export function useDeleteTeam() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (teamId: string) => teamsApi.delete(teamId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.teams })
      toast({ title: t.common.success, description: t.teams.teamDeleted })
    },
    onError: (error: unknown) => {
      toast({
        title: t.common.error,
        description: getApiErrorKey(error, t.common.error),
        variant: 'destructive',
      })
    },
  })
}

export function useUpsertTeamMember(teamId: string) {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (data: TeamMemberUpsertRequest) => teamsApi.upsertMember(teamId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.teamMembers(teamId) })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.teams })
      toast({ title: t.common.success, description: t.teams.memberSaved })
    },
    onError: (error: unknown) => {
      toast({
        title: t.common.error,
        description: getApiErrorKey(error, t.common.error),
        variant: 'destructive',
      })
    },
  })
}

export function useRemoveTeamMember(teamId: string) {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (userId: string) => teamsApi.removeMember(teamId, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.teamMembers(teamId) })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.teams })
      toast({ title: t.common.success, description: t.teams.memberRemoved })
    },
    onError: (error: unknown) => {
      toast({
        title: t.common.error,
        description: getApiErrorKey(error, t.common.error),
        variant: 'destructive',
      })
    },
  })
}
