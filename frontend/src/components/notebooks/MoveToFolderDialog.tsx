'use client'

import { useState } from 'react'
import { Check, Folder, FolderPlus, FolderX } from 'lucide-react'

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { useFolders, useMoveNotebookToFolder } from '@/lib/hooks/use-folders'
import { useTranslation } from '@/lib/hooks/use-translation'
import type { NotebookResponse } from '@/lib/types/api'
import { FolderDialog } from './FolderDialog'

interface MoveToFolderDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  notebook: NotebookResponse
}

export function MoveToFolderDialog({ open, onOpenChange, notebook }: MoveToFolderDialogProps) {
  const { t } = useTranslation()
  const { data: folders = [] } = useFolders()
  const moveNotebook = useMoveNotebookToFolder()
  const [newFolderOpen, setNewFolderOpen] = useState(false)
  const currentFolderId = notebook.folder_id ?? null

  const move = async (folderId: string | null) => {
    if (folderId === currentFolderId) {
      onOpenChange(false)
      return
    }
    try {
      await moveNotebook.mutateAsync({ notebookId: notebook.id, folderId })
      onOpenChange(false)
    } catch {
      // Error toast is handled by the hook.
    }
  }

  const optionClass =
    'w-full justify-start gap-2 font-normal'

  return (
    <>
      <Dialog open={open && !newFolderOpen} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-[420px]" onClick={(event) => event.stopPropagation()}>
          <DialogHeader>
            <DialogTitle>{t('folders.moveToFolder')}</DialogTitle>
            <DialogDescription>{t('folders.moveDesc', { name: notebook.name })}</DialogDescription>
          </DialogHeader>

          <div className="max-h-72 space-y-1 overflow-y-auto" role="group" aria-label={t('folders.title')}>
            <Button
              type="button"
              variant="ghost"
              className={optionClass}
              disabled={moveNotebook.isPending}
              onClick={() => move(null)}
            >
              <FolderX className="h-4 w-4" />
              <span className="flex-1 text-left">{t('folders.noFolder')}</span>
              {currentFolderId === null && <Check className="h-4 w-4" aria-label={t('folders.currentFolder')} />}
            </Button>
            {folders.map((folder) => (
              <Button
                key={folder.id}
                type="button"
                variant="ghost"
                className={optionClass}
                disabled={moveNotebook.isPending}
                onClick={() => move(folder.id)}
              >
                <Folder className="h-4 w-4" />
                <span className="flex-1 truncate text-left">{folder.name}</span>
                {currentFolderId === folder.id && (
                  <Check className="h-4 w-4" aria-label={t('folders.currentFolder')} />
                )}
              </Button>
            ))}
            <Button
              type="button"
              variant="ghost"
              className={optionClass}
              disabled={moveNotebook.isPending}
              onClick={() => setNewFolderOpen(true)}
            >
              <FolderPlus className="h-4 w-4" />
              {t('folders.newFolderEllipsis')}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <FolderDialog
        open={newFolderOpen}
        onOpenChange={setNewFolderOpen}
        onSaved={(folder) => move(folder.id)}
      />
    </>
  )
}
