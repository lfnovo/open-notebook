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
import { useModules } from '@/lib/hooks/use-modules'
import { useCreateNote } from '@/lib/hooks/use-notes'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { toast } from 'sonner'
import { useTranslation } from '@/lib/hooks/use-translation'

interface SaveToModulesDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  question: string
  answer: string
}

export function SaveToModulesDialog({
  open,
  onOpenChange,
  question,
  answer
}: SaveToModulesDialogProps) {
  const { t } = useTranslation()
  const [selectedModules, setSelectedModules] = useState<string[]>([])
  const { data: modules, isLoading } = useModules(false) // false = not archived
  const createNote = useCreateNote()

  const handleToggle = (moduleId: string) => {
    setSelectedModules(prev =>
      prev.includes(moduleId)
        ? prev.filter(id => id !== moduleId)
        : [...prev, moduleId]
    )
  }

  const handleSave = async () => {
    if (selectedModules.length === 0) {
      toast.error(t.searchPage.selectModule)
      return
    }

    try {
      // Create note in each selected module
      for (const moduleId of selectedModules) {
        await createNote.mutateAsync({
          title: question,
          content: answer,
          note_type: 'ai',
          module_id: moduleId
        })
      }

      toast.success(t.searchPage.saveSuccess)
      setSelectedModules([])
      onOpenChange(false)
    } catch {
      toast.error(t.searchPage.saveError)
    }
  }

  const moduleItems = modules?.map(m => ({
    id: m.id,
    title: m.name,
    description: m.description || undefined
  })) || []

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>{t.searchPage.saveToModules}</DialogTitle>
          <DialogDescription>
            {t.searchPage.selectModule}
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <LoadingSpinner />
            </div>
          ) : (
            <CheckboxList
              items={moduleItems}
              selectedIds={selectedModules}
              onToggle={handleToggle}
              emptyMessage={t.sources.noModulesFound}
            />
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t.common.cancel}
          </Button>
          <Button
            onClick={handleSave}
            disabled={selectedModules.length === 0 || createNote.isPending}
          >
            {createNote.isPending ? (
              <>
                <LoadingSpinner size="sm" className="mr-2" />
                {t.searchPage.saving}
              </>
            ) : (
              t.searchPage.saveToModule
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}