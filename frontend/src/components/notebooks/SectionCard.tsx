'use client'

import { useState } from 'react'
import { Layers, MoreHorizontal, Pencil, Trash2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { useDeleteSection } from '@/lib/hooks/use-sections'
import { useTranslation } from '@/lib/hooks/use-translation'
import type { SectionResponse } from '@/lib/types/api'
import { SectionDialog } from './SectionDialog'

interface SectionCardProps {
  section: SectionResponse
  onOpen: (section: SectionResponse) => void
  onDeleted?: (section: SectionResponse) => void
}

export function SectionCard({ section, onOpen, onDeleted }: SectionCardProps) {
  const { t } = useTranslation()
  const [renameOpen, setRenameOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const deleteSection = useDeleteSection()

  const handleDelete = async () => {
    try {
      await deleteSection.mutateAsync(section.id)
      setDeleteOpen(false)
      onDeleted?.(section)
    } catch {
      // Error toast is handled by the hook.
    }
  }

  return (
    <>
      <Card className="group card-hover cursor-pointer" onClick={() => onOpen(section)}>
        <CardContent className="flex items-center gap-3 p-4">
          <Layers className="h-6 w-6 shrink-0 text-sage" aria-hidden />
          <div className="min-w-0 flex-1">
            <button
              type="button"
              className="block max-w-full truncate text-left text-base font-medium focus-visible:outline-none focus-visible:underline"
              aria-label={t('sections.openSection', { name: section.name })}
              onClick={(event) => {
                event.stopPropagation()
                onOpen(section)
              }}
            >
              {section.name}
            </button>
            <p className="text-xs text-muted-foreground">
              {t('sections.folderCount', { count: section.folder_count })}
            </p>
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="opacity-0 transition-opacity focus-visible:opacity-100 group-hover:opacity-100 data-[state=open]:opacity-100"
                aria-label={t('sections.actions')}
                onClick={(event) => event.stopPropagation()}
              >
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" onClick={(event) => event.stopPropagation()}>
              <DropdownMenuItem onClick={() => setRenameOpen(true)}>
                <Pencil className="mr-2 h-4 w-4" />
                {t('sections.rename')}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setDeleteOpen(true)} className="text-destructive">
                <Trash2 className="mr-2 h-4 w-4" />
                {t('common.delete')}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </CardContent>
      </Card>

      <SectionDialog open={renameOpen} onOpenChange={setRenameOpen} section={section} />
      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title={t('sections.deleteTitle')}
        description={t('sections.deleteDesc', { name: section.name })}
        confirmText={t('common.delete')}
        confirmVariant="destructive"
        onConfirm={handleDelete}
        isLoading={deleteSection.isPending}
      />
    </>
  )
}
