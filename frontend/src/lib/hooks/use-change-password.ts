import { useMutation } from '@tanstack/react-query'
import { authApi, ChangePasswordRequest } from '@/lib/api/auth'
import { useToast } from '@/lib/hooks/use-toast'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getApiErrorMessage } from '@/lib/utils/error-handler'

export function useChangePassword() {
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (data: ChangePasswordRequest) => authApi.changePassword(data),
    onSuccess: (data) => {
      toast({
        title: t.common.success,
        description: data.message || t.auth.changePasswordSuccess,
      })
    },
    onError: (error: unknown) => {
      toast({
        title: t.common.error,
        description: getApiErrorMessage(error, t, 'auth.changePasswordError'),
        variant: 'destructive',
      })
    },
  })
}
