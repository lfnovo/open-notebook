import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { authApi, ProfileUpdateRequest } from '@/lib/api/auth'
import { useAuthStore } from '@/lib/stores/auth-store'
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
