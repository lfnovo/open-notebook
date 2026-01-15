'use client'

import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { CheckboxList } from '@/components/ui/checkbox-list'
import { useNotebooks } from '@/lib/hooks/use-notebooks'
import { useCreateNote } from '@/lib/hooks/use-notes'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { toast } from 'sonner'
import { useTranslation } from '@/lib/hooks/use-translation'

interface SaveToNotebooksDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  question: string
  answer: string
}

export function SaveToNotebooksDialog({
  open,
  onOpenChange,
  question,
  answer
}: SaveToNotebooksDialogProps) {
  const { t } = useTranslation()
  const [selectedNotebooks, setSelectedNotebooks] = useState<string[]>([])
  const { data: notebooks, isLoading } = useNotebooks(false) // false = not archived
  const createNote = useCreateNote()

  const handleToggle = (notebookId: string) => {
    setSelectedNotebooks(prev =>
      prev.includes(notebookId)
        ? prev.filter(id => id !== notebookId)
        : [...prev, notebookId]
    )
  }

  const handleSave = async () => {
    if (selectedNotebooks.length === 0) {
      toast.error(t.searchPage.selectNotebook)
      return
    }

    try {
      // Create note in each selected notebook
      for (const notebookId of selectedNotebooks) {
        await createNote.mutateAsync({
          title: question,
          content: answer,
          note_type: 'ai',
          notebook_id: notebookId
        })
      }

      toast.success(t.searchPage.saveSuccess)
      setSelectedNotebooks([])
      onOpenChange(false)
    } catch {
      toast.error(t.searchPage.saveError)
    }
  }

  const notebookItems = notebooks?.map(nb => ({
    id: nb.id,
    title: nb.name,
    description: nb.description || undefined
  })) || []

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>{t.searchPage.saveToNotebooks}</DialogTitle>
          <DialogDescription>
            {t.searchPage.selectNotebook}
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <LoadingSpinner />
            </div>
          ) : (
            <CheckboxList
              items={notebookItems}
              selectedIds={selectedNotebooks}
              onToggle={handleToggle}
              emptyMessage={t.sources.noNotebooksFound}
            />
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t.common.cancel}
          </Button>
          <Button
            onClick={handleSave}
            disabled={selectedNotebooks.length === 0 || createNote.isPending}
          >
            {createNote.isPending ? (
              <>
                <LoadingSpinner size="sm" className="mr-2" />
                {t.searchPage.saving}
              </>
            ) : (
              t.searchPage.saveToNotebook
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
