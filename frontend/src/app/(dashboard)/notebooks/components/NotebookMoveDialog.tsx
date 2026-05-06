'use client'

import { useEffect, useMemo, useState } from 'react'
import { MoveRight } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { useMoveWorkspaceResource, useWorkspaces } from '@/lib/hooks/use-workspaces'
import { useTranslation } from '@/lib/hooks/use-translation'
import { NotebookResponse } from '@/lib/types/api'

interface NotebookMoveDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  notebook: NotebookResponse
}

export function NotebookMoveDialog({
  open,
  onOpenChange,
  notebook,
}: NotebookMoveDialogProps) {
  const { t } = useTranslation()
  const { data, isLoading } = useWorkspaces()
  const moveResource = useMoveWorkspaceResource()
  const manageableWorkspaces = useMemo(
    () =>
      (data?.items ?? []).filter(
        (workspace) => workspace.can_manage && workspace.id !== notebook.workspace_id
      ),
    [data?.items, notebook.workspace_id]
  )
  const [targetWorkspaceId, setTargetWorkspaceId] = useState('')

  useEffect(() => {
    if (!open) return
    setTargetWorkspaceId(manageableWorkspaces[0]?.id ?? '')
  }, [open, manageableWorkspaces])

  const handleMove = async () => {
    if (!targetWorkspaceId) return
    await moveResource.mutateAsync({
      workspaceId: targetWorkspaceId,
      data: {
        resource_type: 'notebook',
        resource_id: notebook.id,
        mode: 'move',
      },
    })
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <MoveRight className="h-5 w-5" />
            {t.notebooks.moveNotebookTitle}
          </DialogTitle>
          <DialogDescription>
            {t.notebooks.moveNotebookDesc.replace('{name}', notebook.name)}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            {t.notebooks.moveNotebookWarning}
          </p>

          {isLoading ? (
            <div className="flex items-center justify-center py-6">
              <LoadingSpinner />
            </div>
          ) : manageableWorkspaces.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              {t.notebooks.noManageableWorkspaces}
            </p>
          ) : (
            <div className="space-y-2">
              <label className="text-sm font-medium">{t.notebooks.targetWorkspace}</label>
              <Select value={targetWorkspaceId} onValueChange={setTargetWorkspaceId}>
                <SelectTrigger>
                  <SelectValue placeholder={t.notebooks.selectWorkspace} />
                </SelectTrigger>
                <SelectContent>
                  {manageableWorkspaces.map((workspace) => (
                    <SelectItem key={workspace.id} value={workspace.id}>
                      {workspace.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={moveResource.isPending}
          >
            {t.common.cancel}
          </Button>
          <Button
            type="button"
            onClick={handleMove}
            disabled={!targetWorkspaceId || moveResource.isPending}
          >
            {moveResource.isPending ? t.common.loading : t.notebooks.moveNotebook}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
