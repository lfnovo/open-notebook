'use client'

import { useState } from 'react'
import { Folder, MoreHorizontal, Pencil, Trash2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { useDeleteFolder, useMoveNotebookToFolder } from '@/lib/hooks/use-folders'
import { useTranslation } from '@/lib/hooks/use-translation'
import type { FolderResponse } from '@/lib/types/api'
import { NOTEBOOK_DRAG_MIME } from '@/lib/utils/folders'
import { FolderDialog } from './FolderDialog'

interface FolderCardProps {
  folder: FolderResponse
  notebookCount: number
  onOpen: (folder: FolderResponse) => void
  onDeleted?: (folder: FolderResponse) => void
}

export function FolderCard({ folder, notebookCount, onOpen, onDeleted }: FolderCardProps) {
  const { t } = useTranslation()
  const [renameOpen, setRenameOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const deleteFolder = useDeleteFolder()
  const moveNotebook = useMoveNotebookToFolder()

  const handleDelete = async () => {
    try {
      await deleteFolder.mutateAsync(folder.id)
      setDeleteOpen(false)
      onDeleted?.(folder)
    } catch {
      // Error toast is handled by the hook.
    }
  }

  const acceptsDrag = (event: React.DragEvent) =>
    Array.from(event.dataTransfer.types).includes(NOTEBOOK_DRAG_MIME)

  return (
    <>
      <Card
        className={`group card-hover cursor-pointer ${dragOver ? 'ring-2 ring-ring' : ''}`}
        onClick={() => onOpen(folder)}
        onDragOver={(event) => {
          if (!acceptsDrag(event)) return
          event.preventDefault()
          event.dataTransfer.dropEffect = 'move'
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(event) => {
          setDragOver(false)
          const notebookId = event.dataTransfer.getData(NOTEBOOK_DRAG_MIME)
          if (!notebookId) return
          event.preventDefault()
          moveNotebook.mutate({ notebookId, folderId: folder.id })
        }}
      >
        <CardContent className="flex items-center gap-3 p-4">
          <Folder className="h-6 w-6 shrink-0 text-teal" aria-hidden />
          <div className="min-w-0 flex-1">
            <button
              type="button"
              className="block max-w-full truncate text-left text-base font-medium focus-visible:outline-none focus-visible:underline"
              aria-label={t('folders.openFolder', { name: folder.name })}
              onClick={(event) => {
                event.stopPropagation()
                onOpen(folder)
              }}
            >
              {folder.name}
            </button>
            <p className="text-xs text-muted-foreground">
              {t('folders.notebookCount', { count: notebookCount })}
            </p>
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="opacity-0 transition-opacity focus-visible:opacity-100 group-hover:opacity-100 data-[state=open]:opacity-100"
                aria-label={t('folders.actions')}
                onClick={(event) => event.stopPropagation()}
              >
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" onClick={(event) => event.stopPropagation()}>
              <DropdownMenuItem onClick={() => setRenameOpen(true)}>
                <Pencil className="mr-2 h-4 w-4" />
                {t('folders.rename')}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setDeleteOpen(true)} className="text-destructive">
                <Trash2 className="mr-2 h-4 w-4" />
                {t('common.delete')}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </CardContent>
      </Card>

      <FolderDialog open={renameOpen} onOpenChange={setRenameOpen} folder={folder} />
      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title={t('folders.deleteTitle')}
        description={t('folders.deleteDesc', { name: folder.name })}
        confirmText={t('common.delete')}
        confirmVariant="destructive"
        onConfirm={handleDelete}
        isLoading={deleteFolder.isPending}
      />
    </>
  )
}
