'use client'

import { useState, useEffect, useMemo } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { ScrollArea } from '@/components/ui/scroll-area'
import { SourceListResponse } from '@/lib/types/api'
import { useBulkSourceOperation, useSources } from '@/lib/hooks/use-sources'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { sourcesApi } from '@/lib/api/sources'

interface BulkSourceActionDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  notebookId: string
  operation: 'add' | 'remove'
  onSuccess?: () => void
}

export function BulkSourceActionDialog({
  open,
  onOpenChange,
  notebookId,
  operation,
  onSuccess
}: BulkSourceActionDialogProps) {
  const [selectedSources, setSelectedSources] = useState<Record<string, boolean>>({})
  const [availableSources, setAvailableSources] = useState<SourceListResponse[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const bulkOperation = useBulkSourceOperation()
  
  // Get sources already in the notebook
  const { data: currentNotebookSources } = useSources(notebookId)
  const currentSourceIds = useMemo(
    () => new Set(currentNotebookSources?.map(s => s.id) || []),
    [currentNotebookSources]
  )

  // Load appropriate sources based on operation type
  useEffect(() => {
    if (!open) return

    const loadSources = async () => {
      setIsLoading(true)
      try {
        if (operation === 'add') {
          // For add: fetch all sources and filter out ones already in notebook
          const allSources = await sourcesApi.list({
            limit: 100,
            offset: 0,
            sort_by: 'created',
            sort_order: 'desc',
          })
          const sourcesToAdd = allSources.filter(s => !currentSourceIds.has(s.id))
          setAvailableSources(sourcesToAdd)
        } else {
          // For remove: use sources already in the notebook
          setAvailableSources(currentNotebookSources || [])
        }
      } catch (error) {
        console.error('Error loading sources:', error)
        setAvailableSources([])
      } finally {
        setIsLoading(false)
      }
    }

    loadSources()
  }, [open, operation, currentSourceIds, currentNotebookSources])

  // Initialize selected sources when dialog opens
  useEffect(() => {
    if (open && availableSources.length > 0) {
      const initialSelection: Record<string, boolean> = {}
      availableSources.forEach(source => {
        initialSelection[source.id] = true
      })
      setSelectedSources(initialSelection)
    }
  }, [open, availableSources])

  const handleSelectAll = (checked: boolean) => {
    const newSelection: Record<string, boolean> = {}
    availableSources.forEach(source => {
      newSelection[source.id] = checked
    })
    setSelectedSources(newSelection)
  }

  const handleSourceToggle = (sourceId: string, checked: boolean) => {
    setSelectedSources(prev => ({
      ...prev,
      [sourceId]: checked
    }))
  }

  const handleConfirm = async () => {
    const selectedSourceIds = Object.entries(selectedSources)
      .filter(([_, isSelected]) => isSelected)
      .map(([sourceId, _]) => sourceId)

    if (selectedSourceIds.length === 0) {
      return
    }

    try {
      await bulkOperation.mutateAsync({
        notebookId,
        data: {
          source_ids: selectedSourceIds,
          operation
        }
      })
      
      onSuccess?.()
      onOpenChange(false)
    } catch (error) {
      console.error('Bulk operation failed:', error)
    }
  }

  const selectedCount = Object.values(selectedSources).filter(Boolean).length
  const allSelected = selectedCount === availableSources.length && availableSources.length > 0
  const noneSelected = selectedCount === 0

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>
            {operation === 'add' ? 'Add Sources to Notebook' : 'Remove Sources from Notebook'}
          </DialogTitle>
          <DialogDescription>
            Select the sources you want to {operation} from this notebook. 
            {operation === 'add' ? ' Selected sources will be included in chat sessions.' : ' Selected sources will be excluded from chat sessions.'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <LoadingSpinner />
            </div>
          ) : availableSources.length > 0 ? (
            <>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="select-all"
                  checked={allSelected}
                  onCheckedChange={handleSelectAll}
                />
                <Label htmlFor="select-all" className="font-medium">
                  Select All ({selectedCount}/{availableSources.length} selected)
                </Label>
              </div>

              <ScrollArea className="h-[300px] border rounded-md p-2">
                <div className="space-y-2">
                  {availableSources.map((source) => (
                    <div key={`${operation}-${source.id}`} className="flex items-center space-x-2 p-2 hover:bg-muted rounded">
                      <Checkbox
                        id={`${operation}-source-${source.id}`}
                        checked={selectedSources[source.id] || false}
                        onCheckedChange={(checked) => handleSourceToggle(source.id, !!checked)}
                      />
                      <Label htmlFor={`${operation}-source-${source.id}`} className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                        {source.title || 'Untitled Source'}
                      </Label>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              {operation === 'add' 
                ? 'No sources available to add. All sources are already in this notebook.'
                : 'No sources in this notebook to remove.'
              }
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={bulkOperation.isPending}
          >
            Cancel
          </Button>
          <Button
            type="button"
            onClick={handleConfirm}
            disabled={bulkOperation.isPending || noneSelected}
          >
            {bulkOperation.isPending ? (
              <>
                <LoadingSpinner size="sm" className="mr-2" />
                Processing...
              </>
            ) : (
              `${operation === 'add' ? 'Add' : 'Remove'} ${selectedCount} Source${selectedCount !== 1 ? 's' : ''}`
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}