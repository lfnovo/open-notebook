import { toast as sonnerToast } from 'sonner'
import { useTranslation } from '@/lib/hooks/use-translation'

type ToastProps = {
  title?: string
  description?: string
  variant?: 'default' | 'destructive'
}

export function useToast() {
  const { t } = useTranslation()

  return {
    toast: ({ title, description, variant = 'default' }: ToastProps) => {
      if (variant === 'destructive') {
        sonnerToast.error(title || t.common.error, {
          description,
        })
      } else {
        sonnerToast.success(title || t.common.success, {
          description,
        })
      }
    }
  }
}