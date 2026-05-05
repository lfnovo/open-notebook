import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  UserCreateRequest,
  UserRole,
  UserStatus,
  UserUpdateRequest,
  usersApi,
} from '@/lib/api/users'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { useToast } from '@/lib/hooks/use-toast'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getApiErrorKey } from '@/lib/utils/error-handler'

export function useUsers(params?: {
  q?: string
  role?: UserRole | 'all'
  status?: UserStatus | 'all'
}) {
  return useQuery({
    queryKey: [...QUERY_KEYS.users, params?.q || '', params?.role || 'all', params?.status || 'all'],
    queryFn: () =>
      usersApi.list({
        q: params?.q || undefined,
        role: params?.role === 'all' ? undefined : params?.role,
        status: params?.status === 'all' ? undefined : params?.status,
        limit: 50,
      }),
  })
}

export function useCreateUser() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (data: UserCreateRequest) => usersApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.users })
      toast({ title: t.common.success, description: t.users.userSaved })
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

export function useUpdateUser() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: ({ userId, data }: { userId: string; data: UserUpdateRequest }) =>
      usersApi.update(userId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.users })
      toast({ title: t.common.success, description: t.users.userSaved })
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

export function useResetUserPassword() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (userId: string) => usersApi.resetPassword(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.users })
      toast({ title: t.common.success, description: t.users.passwordReset })
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
