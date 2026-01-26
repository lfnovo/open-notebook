'use client'

import { useState, useEffect, useMemo } from 'react'
import { LoaderIcon, BookOpen, Check } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useModules } from '@/lib/hooks/use-modules'
import { useAddSourcesToModule, useRemoveSourceFromModule } from '@/lib/hooks/use-sources'
import { useTranslation } from '@/lib/hooks/use-translation'

interface ModuleAssociationsProps {
  sourceId: string
  currentModuleIds: string[]
  onSave?: () => void
}

export function ModuleAssociations({
  sourceId,
  currentModuleIds,
  onSave,
}: ModuleAssociationsProps) {
  const { t } = useTranslation()
  const [selectedModuleIds, setSelectedModuleIds] = useState<string[]>(currentModuleIds)
  const [isSaving, setIsSaving] = useState(false)

  const { data: modules, isLoading } = useModules()
  const addSources = useAddSourcesToModule()
  const removeFromModule = useRemoveSourceFromModule()

  // Update selected modules when current changes (after save)
  useEffect(() => {
    setSelectedModuleIds(currentModuleIds)
  }, [currentModuleIds])

  const hasChanges = useMemo(() => {
    const current = new Set(currentModuleIds)
    const selected = new Set(selectedModuleIds)

    if (current.size !== selected.size) return true

    for (const id of current) {
      if (!selected.has(id)) return true
    }

    return false
  }, [currentModuleIds, selectedModuleIds])

  const handleToggleModule = (moduleId: string) => {
    setSelectedModuleIds(prev =>
      prev.includes(moduleId)
        ? prev.filter(id => id !== moduleId)
        : [...prev, moduleId]
    )
  }

  const handleSave = async () => {
    if (!hasChanges) return

    try {
      setIsSaving(true)

      const current = new Set(currentModuleIds)
      const selected = new Set(selectedModuleIds)

      // Determine which modules to add and remove
      const toAdd = selectedModuleIds.filter(id => !current.has(id))
      const toRemove = currentModuleIds.filter(id => !selected.has(id))

      // Execute additions
      if (toAdd.length > 0) {
        await Promise.allSettled(
          toAdd.map(moduleId =>
            addSources.mutateAsync({
              moduleId,
              sourceIds: [sourceId],
            })
          )
        )
      }

      // Execute removals
      if (toRemove.length > 0) {
        await Promise.allSettled(
          toRemove.map(moduleId =>
            removeFromModule.mutateAsync({
              moduleId,
              sourceId,
            })
          )
        )
      }

      onSave?.()
    } catch (error) {
      console.error('Error saving module associations:', error)
    } finally {
      setIsSaving(false)
    }
  }

  const handleCancel = () => {
    setSelectedModuleIds(currentModuleIds)
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BookOpen className="h-5 w-5" />
            {t.sources.manageModules}
          </CardTitle>
          <CardDescription>
            {t.sources.manageModulesDesc}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <LoaderIcon className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!modules || modules.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BookOpen className="h-5 w-5" />
            {t.sources.manageModules}
          </CardTitle>
          <CardDescription>
            {t.sources.manageModulesDesc}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{t.sources.noModulesAvailable}</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BookOpen className="h-5 w-5" />
          {t.sources.manageModules}
        </CardTitle>
        <CardDescription>
          {t.sources.manageModulesDesc}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <ScrollArea className="h-[300px] border rounded-md p-4">
          <div className="space-y-3">
            {modules
              .filter(m => !m.archived)
              .map((module) => {
                const isSelected = selectedModuleIds.includes(module.id)
                const isCurrentlyLinked = currentModuleIds.includes(module.id)

                return (
                  <div
                    key={module.id}
                    className={`flex items-start gap-3 p-3 rounded-lg border transition-colors ${
                      isSelected ? 'bg-accent border-accent-foreground/20' : 'hover:bg-accent/50'
                    }`}
                  >
                    <Checkbox
                      checked={isSelected}
                      onCheckedChange={() => handleToggleModule(module.id)}
                      className="mt-0.5"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h4 className="font-medium text-sm truncate">
                          {module.name}
                        </h4>
                        {isCurrentlyLinked && !hasChanges && (
                          <Check className="h-4 w-4 text-green-600" />
                        )}
                      </div>
                      {module.description && (
                        <p className="text-xs text-muted-foreground line-clamp-1">
                          {module.description}
                        </p>
                      )}
                    </div>
                  </div>
                )
              })}
          </div>
        </ScrollArea>

        {hasChanges && (
          <div className="flex items-center justify-end gap-2 pt-2 border-t">
            <Button
              variant="outline"
              size="sm"
              onClick={handleCancel}
              disabled={isSaving}
            >
              {t.common.cancel}
            </Button>
            <Button
              size="sm"
              onClick={handleSave}
              disabled={isSaving}
            >
              {isSaving ? (
                <>
                  <LoaderIcon className="mr-2 h-4 w-4 animate-spin" />
                  {t.common.saving}...
                </>
              ) : (
                t.common.saveChanges
              )}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}