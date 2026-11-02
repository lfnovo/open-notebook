'use client'

import { useEffect, useState } from 'react'

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  isDuplicateFolderError,
  useCreateFolder,
  useRenameFolder,
} from '@/lib/hooks/use-folders'
import { useTranslation } from '@/lib/hooks/use-translation'
import type { FolderResponse } from '@/lib/types/api'
import { FOLDER_NAME_MAX_LENGTH, validateFolderName } from '@/lib/utils/folders'

interface FolderDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** When set, the dialog renames this folder instead of creating one. */
  folder?: FolderResponse
  onSaved?: (folder: FolderResponse) => void
}

export function FolderDialog({ open, onOpenChange, folder, onSaved }: FolderDialogProps) {
  const { t } = useTranslation()
  const createFolder = useCreateFolder()
  const renameFolder = useRenameFolder()
  const [name, setName] = useState('')
  const [touched, setTouched] = useState(false)
  const [duplicate, setDuplicate] = useState(false)

  const isEditing = !!folder
  const isPending = createFolder.isPending || renameFolder.isPending

  useEffect(() => {
    if (open) {
      setName(folder?.name ?? '')
      setTouched(false)
      setDuplicate(false)
    }
  }, [open, folder])

  const validation = validateFolderName(name)
  const errorMessage = duplicate
    ? t('folders.duplicateName')
    : touched && validation === 'required'
      ? t('folders.nameRequired')
      : validation === 'tooLong'
        ? t('folders.nameTooLong')
        : null

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setTouched(true)
    if (validation !== null || isPending) return

    const trimmed = name.trim()
    try {
      const saved = folder
        ? await renameFolder.mutateAsync({ id: folder.id, name: trimmed })
        : await createFolder.mutateAsync(trimmed)
      onOpenChange(false)
      onSaved?.(saved)
    } catch (error) {
      if (isDuplicateFolderError(error)) {
        setDuplicate(true)
      }
      // Other errors are toasted by the mutation hook.
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[420px]">
        <DialogHeader>
          <DialogTitle>{isEditing ? t('folders.renameTitle') : t('folders.createTitle')}</DialogTitle>
          <DialogDescription>
            {isEditing ? t('folders.renameDesc') : t('folders.createDesc')}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <div className="space-y-2">
            <Label htmlFor="folder-name">{t('folders.nameLabel')} *</Label>
            <Input
              id="folder-name"
              value={name}
              onChange={(event) => {
                setName(event.target.value)
                setDuplicate(false)
              }}
              onBlur={() => setTouched(true)}
              placeholder={t('folders.namePlaceholder')}
              autoComplete="off"
              aria-invalid={errorMessage ? true : undefined}
              maxLength={FOLDER_NAME_MAX_LENGTH + 20}
            />
            {errorMessage && (
              <p role="alert" className="text-sm text-destructive">
                {errorMessage}
              </p>
            )}
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              {t('common.cancel')}
            </Button>
            <Button type="submit" disabled={validation !== null || duplicate || isPending}>
              {isEditing ? t('folders.rename') : t('folders.create')}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
