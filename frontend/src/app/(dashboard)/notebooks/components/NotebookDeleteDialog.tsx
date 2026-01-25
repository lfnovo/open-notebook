'use client'

import { useState, useEffect } from 'react'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Label } from '@/components/ui/label'
import { useTranslation } from '@/lib/hooks/use-translation'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { useNotebookDeletePreview, useDeleteNotebook } from '@/lib/hooks/use-notebooks'
import { useRouter } from 'next/navigation'

interface NotebookDeleteDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  notebookId: string
  notebookName: string
  redirectAfterDelete?: boolean
}

export function NotebookDeleteDialog({
  open,
  onOpenChange,
  notebookId,
  notebookName,
  redirectAfterDelete = false,
}: NotebookDeleteDialogProps) {
  const { t } = useTranslation()
  const router = useRouter()
  const [sourceAction, setSourceAction] = useState<'keep' | 'delete'>('keep')

  // Reset state when dialog opens
  useEffect(() => {
    if (open) {
      setSourceAction('keep')
    }
  }, [open, notebookId])

  // Fetch delete preview when dialog is open
  const { data: preview, isLoading: isLoadingPreview, error: previewError } = useNotebookDeletePreview(
    notebookId,
    open
  )

  const deleteNotebook = useDeleteNotebook()

  const handleConfirm = async () => {
    await deleteNotebook.mutateAsync({
      id: notebookId,
      deleteExclusiveSources: sourceAction === 'delete',
    })
    onOpenChange(false)
    if (redirectAfterDelete) {
      router.push('/notebooks')
    }
  }

  const isDeleting = deleteNotebook.isPending

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{t.notebooks.deleteNotebook}</AlertDialogTitle>
          <AlertDialogDescription>
            {t.notebooks.deleteNotebookDesc.replace('{name}', notebookName)}
          </AlertDialogDescription>
        </AlertDialogHeader>

        <div className="py-4 space-y-3">
          {isLoadingPreview ? (
            <div className="flex items-center gap-2 text-muted-foreground">
              <LoadingSpinner size="sm" />
              <span>{t.notebooks.deleteNotebookLoading}</span>
            </div>
          ) : previewError ? (
            <div className="text-sm text-destructive">
              {t.common.error}: {previewError.message || 'Failed to load preview'}
            </div>
          ) : preview ? (
            <>
              {/* Notes section */}
              <div className="text-sm">
                {preview.note_count > 0 ? (
                  <p className="text-destructive font-medium">
                    {t.notebooks.deleteNotebookNotes.replace(
                      '{count}',
                      String(preview.note_count)
                    )}
                  </p>
                ) : (
                  <p className="text-muted-foreground">{t.notebooks.deleteNotebookNoNotes}</p>
                )}
              </div>

              {/* Shared sources - always above the line */}
              {preview.shared_source_count > 0 && (
                <div className="text-sm">
                  <p className="text-muted-foreground">
                    {t.notebooks.deleteNotebookSharedSources.replace(
                      '{count}',
                      String(preview.shared_source_count)
                    )}
                  </p>
                </div>
              )}

              {/* No sources message */}
              {preview.exclusive_source_count === 0 && preview.shared_source_count === 0 && (
                <div className="text-sm">
                  <p className="text-muted-foreground">{t.notebooks.deleteNotebookNoSources}</p>
                </div>
              )}

              {/* Exclusive sources section - below the line with radio buttons */}
              {preview.exclusive_source_count > 0 && (
                <div className="pt-3 border-t space-y-3">
                  <p className="text-sm text-destructive font-medium">
                    {t.notebooks.deleteNotebookExclusiveSources.replace(
                      '{count}',
                      String(preview.exclusive_source_count)
                    )}
                  </p>
                  <RadioGroup
                    value={sourceAction}
                    onValueChange={(value) => setSourceAction(value as 'keep' | 'delete')}
                    disabled={isDeleting}
                  >
                    <div className="flex items-center space-x-3">
                      <RadioGroupItem value="delete" id="delete-sources" />
                      <Label htmlFor="delete-sources" className="text-sm cursor-pointer">
                        {t.notebooks.deleteExclusiveSourcesLabel}
                      </Label>
                    </div>
                    <div className="flex items-center space-x-3">
                      <RadioGroupItem value="keep" id="keep-sources" />
                      <Label htmlFor="keep-sources" className="text-sm cursor-pointer">
                        {t.notebooks.keepExclusiveSourcesLabel}
                      </Label>
                    </div>
                  </RadioGroup>
                </div>
              )}
            </>
          ) : null}
        </div>

        <AlertDialogFooter>
          <AlertDialogCancel disabled={isDeleting}>{t.common.cancel}</AlertDialogCancel>
          <AlertDialogAction
            onClick={handleConfirm}
            disabled={isDeleting || isLoadingPreview}
            className="bg-red-600 hover:bg-red-700"
          >
            {isDeleting ? (
              <>
                <LoadingSpinner size="sm" className="mr-2" />
                {t.common.deleting}
              </>
            ) : (
              t.common.delete
            )}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
