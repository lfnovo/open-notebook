import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { authApi, CompleteProfileRequest, ProfileUpdateRequest } from '@/lib/api/auth'
import { useAuthStore } from '@/lib/stores/auth-store'
import { useWorkspaceStore } from '@/lib/stores/workspace-store'
import { useToast } from '@/lib/hooks/use-toast'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getApiErrorKey } from '@/lib/utils/error-handler'

export const PROFILE_QUERY_KEY = ['auth', 'me'] as const

export function profileQueryKey(identity?: string | null) {
  return [...PROFILE_QUERY_KEY, identity || 'anonymous'] as const
}

export function useProfile() {
  const username = useAuthStore((state) => state.username)

  return useQuery({
    queryKey: profileQueryKey(username),
    queryFn: authApi.me,
  })
}

export function useUpdateProfile() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()
  const username = useAuthStore((state) => state.username)

  return useMutation({
    mutationFn: (data: ProfileUpdateRequest) => authApi.updateMe(data),
    onSuccess: (user) => {
      queryClient.setQueryData(profileQueryKey(user.username || username), user)
      useAuthStore.setState({
        username: user.username,
        role: user.role || null,
        displayName: user.display_name || user.username,
        status: user.status || null,
        requiresProfileCompletion: user.login_provider === 'wechat' && !user.email,
      })
      toast({ title: t.common.success, description: t.profile.saved })
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

export function useCompleteProfile() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (data: CompleteProfileRequest) => authApi.completeProfile(data),
    onSuccess: (response) => {
      queryClient.clear()
      useWorkspaceStore.getState().resetWorkspace()
      useAuthStore.setState({
        token: response.token,
        isAuthenticated: true,
        username: response.user.username,
        role: response.user.role || null,
        displayName: response.user.display_name || response.user.username,
        status: response.user.status || null,
        requiresProfileCompletion: false,
        lastAuthCheck: Date.now(),
      })
      queryClient.setQueryData(profileQueryKey(response.user.username), response.user)
      toast({
        title: t.common.success,
        description: response.bound_existing_user
          ? t.profile.emailBound
          : t.profile.emailVerified,
      })
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
