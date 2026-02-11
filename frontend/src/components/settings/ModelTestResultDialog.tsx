'use client'

import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Check, X } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { ModelTestResult } from '@/lib/types/models'

export function ModelTestResultDialog({
  open,
  onOpenChange,
  result,
  modelName,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  result: ModelTestResult | null
  modelName: string
}) {
  const { t } = useTranslation()

  if (!result) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {result.success ? (
              <Check className="h-5 w-5 text-emerald-500" />
            ) : (
              <X className="h-5 w-5 text-destructive" />
            )}
            {result.success ? t.models.testModelSuccess : t.models.testModelFailed}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">{modelName}</p>
          <p className="text-sm">{result.message}</p>

          {result.details && (
            <pre className="text-xs bg-muted p-3 rounded-md overflow-auto max-h-60 whitespace-pre-wrap break-words">
              {result.details}
            </pre>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t.common.done}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
