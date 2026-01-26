'use client'

import { useState } from 'react'
import { ModuleResponse } from '@/lib/types/api'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Archive, ArchiveRestore, Trash2 } from 'lucide-react'
import { useUpdateModule, useDeleteModule } from '@/lib/hooks/use-modules'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { formatDistanceToNow } from 'date-fns'
import { getDateLocale } from '@/lib/utils/date-locale'
import { InlineEdit } from '@/components/common/InlineEdit'
import { useTranslation } from '@/lib/hooks/use-translation'

interface ModuleHeaderProps {
  module: ModuleResponse
}

export function ModuleHeader({ module }: ModuleHeaderProps) {
  const { t, language } = useTranslation()
  const dfLocale = getDateLocale(language)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  
  const updateModule = useUpdateModule()
  const deleteModule = useDeleteModule()

  const handleUpdateName = async (name: string) => {
    if (!name || name === module.name) return
    
    await updateModule.mutateAsync({
      id: module.id,
      data: { name }
    })
  }

  const handleUpdateDescription = async (description: string) => {
    if (description === module.description) return
    
    await updateModule.mutateAsync({
      id: module.id,
      data: { description: description || undefined }
    })
  }

  const handleArchiveToggle = () => {
    updateModule.mutate({
      id: module.id,
      data: { archived: !module.archived }
    })
  }

  const handleDelete = () => {
    deleteModule.mutate(module.id)
    setShowDeleteDialog(false)
  }

  return (
    <>
      <div className="border-b pb-6">
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3 flex-1">
              <InlineEdit
                id="module-name"
                name="module-name"
                value={module.name}
                onSave={handleUpdateName}
                className="text-2xl font-bold"
                inputClassName="text-2xl font-bold"
                placeholder={t.modules.namePlaceholder}
              />
              {module.archived && (
                <Badge variant="secondary">{t.modules.archived}</Badge>
              )}
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleArchiveToggle}
              >
                {module.archived ? (
                  <>
                    <ArchiveRestore className="h-4 w-4 mr-2" />
                    {t.modules.unarchive}
                  </>
                ) : (
                  <>
                    <Archive className="h-4 w-4 mr-2" />
                    {t.modules.archive}
                  </>
                )}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowDeleteDialog(true)}
                className="text-red-600 hover:text-red-700"
              >
                <Trash2 className="h-4 w-4 mr-2" />
                {t.common.delete}
              </Button>
            </div>
          </div>
          
          <InlineEdit
            id="module-description"
            name="module-description"
            value={module.description || ''}
            onSave={handleUpdateDescription}
            className="text-muted-foreground"
            inputClassName="text-muted-foreground"
            placeholder={t.modules.addDescription}
            multiline
            emptyText={t.modules.addDescription}
          />
          
          <div className="text-sm text-muted-foreground">
            {t.common.created.replace('{time}', formatDistanceToNow(new Date(module.created), { addSuffix: true, locale: dfLocale }))} • 
            {t.common.updated.replace('{time}', formatDistanceToNow(new Date(module.updated), { addSuffix: true, locale: dfLocale }))}
          </div>
        </div>
      </div>

      <ConfirmDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        title={t.modules.deleteModule}
        description={t.modules.deleteModuleDesc.replace('{name}', module.name)}
        confirmText={t.common.deleteForever}
        confirmVariant="destructive"
        onConfirm={handleDelete}
      />
    </>
  )
}