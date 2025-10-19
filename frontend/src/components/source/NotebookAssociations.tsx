'use client'

import { useState, useEffect, useMemo } from 'react'
import { LoaderIcon, BookOpen, Check } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useNotebooks } from '@/lib/hooks/use-notebooks'
import { useAddSourcesToNotebook, useRemoveSourceFromNotebook } from '@/lib/hooks/use-sources'

interface NotebookAssociationsProps {
  sourceId: string
  currentNotebookIds: string[]
  onSave?: () => void
}

export function NotebookAssociations({
  sourceId,
  currentNotebookIds,
  onSave,
}: NotebookAssociationsProps) {
  const [selectedNotebookIds, setSelectedNotebookIds] = useState<string[]>(currentNotebookIds)
  const [isSaving, setIsSaving] = useState(false)

  const { data: notebooks, isLoading } = useNotebooks()
  const addSources = useAddSourcesToNotebook()
  const removeFromNotebook = useRemoveSourceFromNotebook()

  // Update selected notebooks when current changes (after save)
  useEffect(() => {
    setSelectedNotebookIds(currentNotebookIds)
  }, [currentNotebookIds])

  const hasChanges = useMemo(() => {
    const current = new Set(currentNotebookIds)
    const selected = new Set(selectedNotebookIds)

    if (current.size !== selected.size) return true

    for (const id of current) {
      if (!selected.has(id)) return true
    }

    return false
  }, [currentNotebookIds, selectedNotebookIds])

  const handleToggleNotebook = (notebookId: string) => {
    setSelectedNotebookIds(prev =>
      prev.includes(notebookId)
        ? prev.filter(id => id !== notebookId)
        : [...prev, notebookId]
    )
  }

  const handleSave = async () => {
    if (!hasChanges) return

    try {
      setIsSaving(true)

      const current = new Set(currentNotebookIds)
      const selected = new Set(selectedNotebookIds)

      // Determine which notebooks to add and remove
      const toAdd = selectedNotebookIds.filter(id => !current.has(id))
      const toRemove = currentNotebookIds.filter(id => !selected.has(id))

      // Execute additions
      if (toAdd.length > 0) {
        await Promise.allSettled(
          toAdd.map(notebookId =>
            addSources.mutateAsync({
              notebookId,
              sourceIds: [sourceId],
            })
          )
        )
      }

      // Execute removals
      if (toRemove.length > 0) {
        await Promise.allSettled(
          toRemove.map(notebookId =>
            removeFromNotebook.mutateAsync({
              notebookId,
              sourceId,
            })
          )
        )
      }

      onSave?.()
    } catch (error) {
      console.error('Error saving notebook associations:', error)
    } finally {
      setIsSaving(false)
    }
  }

  const handleCancel = () => {
    setSelectedNotebookIds(currentNotebookIds)
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BookOpen className="h-5 w-5" />
            Notebooks
          </CardTitle>
          <CardDescription>
            Manage which notebooks contain this source
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

  if (!notebooks || notebooks.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BookOpen className="h-5 w-5" />
            Notebooks
          </CardTitle>
          <CardDescription>
            Manage which notebooks contain this source
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No notebooks available</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BookOpen className="h-5 w-5" />
          Notebooks
        </CardTitle>
        <CardDescription>
          Manage which notebooks contain this source
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <ScrollArea className="h-[300px] border rounded-md p-4">
          <div className="space-y-3">
            {notebooks
              .filter(nb => !nb.archived)
              .map((notebook) => {
                const isSelected = selectedNotebookIds.includes(notebook.id)
                const isCurrentlyLinked = currentNotebookIds.includes(notebook.id)

                return (
                  <div
                    key={notebook.id}
                    className={`flex items-start gap-3 p-3 rounded-lg border transition-colors ${
                      isSelected ? 'bg-accent border-accent-foreground/20' : 'hover:bg-accent/50'
                    }`}
                  >
                    <Checkbox
                      checked={isSelected}
                      onCheckedChange={() => handleToggleNotebook(notebook.id)}
                      className="mt-0.5"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h4 className="font-medium text-sm truncate">
                          {notebook.name}
                        </h4>
                        {isCurrentlyLinked && !hasChanges && (
                          <Check className="h-4 w-4 text-green-600" />
                        )}
                      </div>
                      {notebook.description && (
                        <p className="text-xs text-muted-foreground line-clamp-1">
                          {notebook.description}
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
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={handleSave}
              disabled={isSaving}
            >
              {isSaving ? (
                <>
                  <LoaderIcon className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                'Save Changes'
              )}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
