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
  isDuplicateSectionError,
  useCreateSection,
  useRenameSection,
} from '@/lib/hooks/use-sections'
import { useTranslation } from '@/lib/hooks/use-translation'
import type { SectionResponse } from '@/lib/types/api'
import { FOLDER_NAME_MAX_LENGTH, validateFolderName } from '@/lib/utils/folders'

interface SectionDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** When set, the dialog renames this section instead of creating one. */
  section?: SectionResponse
  onSaved?: (section: SectionResponse) => void
}

export function SectionDialog({ open, onOpenChange, section, onSaved }: SectionDialogProps) {
  const { t } = useTranslation()
  const createSection = useCreateSection()
  const renameSection = useRenameSection()
  const [name, setName] = useState('')
  const [touched, setTouched] = useState(false)
  const [duplicate, setDuplicate] = useState(false)

  const isEditing = !!section
  const isPending = createSection.isPending || renameSection.isPending

  useEffect(() => {
    if (open) {
      setName(section?.name ?? '')
      setTouched(false)
      setDuplicate(false)
    }
  }, [open, section])

  // Section names share the folder name rules (1-80 characters).
  const validation = validateFolderName(name)
  const errorMessage = duplicate
    ? t('sections.duplicateName')
    : touched && validation === 'required'
      ? t('sections.nameRequired')
      : validation === 'tooLong'
        ? t('sections.nameTooLong')
        : null

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setTouched(true)
    if (validation !== null || isPending) return

    const trimmed = name.trim()
    try {
      const saved = section
        ? await renameSection.mutateAsync({ id: section.id, name: trimmed })
        : await createSection.mutateAsync(trimmed)
      onOpenChange(false)
      onSaved?.(saved)
    } catch (error) {
      if (isDuplicateSectionError(error)) {
        setDuplicate(true)
      }
      // Other errors are toasted by the mutation hook.
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[420px]">
        <DialogHeader>
          <DialogTitle>{isEditing ? t('sections.renameTitle') : t('sections.createTitle')}</DialogTitle>
          <DialogDescription>
            {isEditing ? t('sections.renameDesc') : t('sections.createDesc')}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <div className="space-y-2">
            <Label htmlFor="section-name">{t('sections.nameLabel')} *</Label>
            <Input
              id="section-name"
              value={name}
              onChange={(event) => {
                setName(event.target.value)
                setDuplicate(false)
              }}
              onBlur={() => setTouched(true)}
              placeholder={t('sections.namePlaceholder')}
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
              {isEditing ? t('sections.rename') : t('sections.create')}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
