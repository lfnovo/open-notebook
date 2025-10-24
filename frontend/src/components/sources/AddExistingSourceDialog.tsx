'use client'

import { useState, useEffect, useMemo, useCallback } from 'react'
import { useDebounce } from 'use-debounce'
import { Search, Link2, LoaderIcon, FileText, Link as LinkIcon, Upload } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { searchApi } from '@/lib/api/search'
import { sourcesApi } from '@/lib/api/sources'
import { useSources, useAddSourcesToNotebook } from '@/lib/hooks/use-sources'
import { SourceListResponse } from '@/lib/types/api'

interface AddExistingSourceDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  notebookId: string
  onSuccess?: () => void
}

export function AddExistingSourceDialog({
  open,
  onOpenChange,
  notebookId,
  onSuccess,
}: AddExistingSourceDialogProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [debouncedSearchQuery] = useDebounce(searchQuery, 300)
  const [selectedSourceIds, setSelectedSourceIds] = useState<string[]>([])
  const [allSources, setAllSources] = useState<SourceListResponse[]>([])
  const [filteredSources, setFilteredSources] = useState<SourceListResponse[]>([])
  const [isSearching, setIsSearching] = useState(false)

  // Get sources already in this notebook
  const { data: currentNotebookSources } = useSources(notebookId)
  const currentSourceIds = useMemo(
    () => new Set(currentNotebookSources?.map(s => s.id) || []),
    [currentNotebookSources]
  )

  const addSources = useAddSourcesToNotebook()

  const loadAllSources = useCallback(async () => {
    try {
      setIsSearching(true)
      // Use sources API directly to get all sources (max 100 per API limit)
      const sources = await sourcesApi.list({
        limit: 100,
        offset: 0,
        sort_by: 'created',
        sort_order: 'desc',
      })

      setAllSources(sources)
      setFilteredSources(sources)
    } catch (error) {
      console.error('Error loading sources:', error)
    } finally {
      setIsSearching(false)
    }
  }, [])

  const performSearch = useCallback(async () => {
    if (!debouncedSearchQuery.trim()) {
      // Empty query - show all sources
      setFilteredSources(allSources)
      setIsSearching(false)
      return
    }

    try {
      setIsSearching(true)
      const response = await searchApi.search({
        query: debouncedSearchQuery,
        type: 'text',
        search_sources: true,
        search_notes: false,
        limit: 100,
        minimum_score: 0.01,
      })

      // Since we set search_sources=true and search_notes=false,
      // the API only returns sources, no need to filter
      const sources = response.results.map(r => ({
        id: r.parent_id,
        title: r.title || 'Untitled',
        topics: [],
        asset: null,
        embedded: false,
        embedded_chunks: 0,
        insights_count: 0,
        created: r.created,
        updated: r.updated,
      })) as SourceListResponse[]

      setFilteredSources(sources)
    } catch (error) {
      console.error('Error searching sources:', error)
      // On error, fall back to showing all sources
      setFilteredSources(allSources)
    } finally {
      setIsSearching(false)
    }
  }, [debouncedSearchQuery, allSources])

  // Load all sources initially
  useEffect(() => {
    if (open) {
      loadAllSources()
    }
  }, [open, loadAllSources])

  // Filter sources when search query changes
  useEffect(() => {
    if (!debouncedSearchQuery) {
      setFilteredSources(allSources)
      setIsSearching(false)
      return
    }

    performSearch()
  }, [debouncedSearchQuery, allSources, performSearch])

  const handleToggleSource = (sourceId: string) => {
    setSelectedSourceIds(prev =>
      prev.includes(sourceId)
        ? prev.filter(id => id !== sourceId)
        : [...prev, sourceId]
    )
  }

  const handleAddSelected = async () => {
    if (selectedSourceIds.length === 0) return

    try {
      await addSources.mutateAsync({
        notebookId,
        sourceIds: selectedSourceIds,
      })

      // Reset state
      setSelectedSourceIds([])
      setSearchQuery('')
      onOpenChange(false)
      onSuccess?.()
    } catch (error) {
      // Error handled by the hook's onError
      console.error('Error adding sources:', error)
    }
  }

  const getSourceIcon = (source: SourceListResponse) => {
    // Derive type from asset
    if (source.asset?.url) {
      return <LinkIcon className="h-4 w-4" />
    }
    if (source.asset?.file_path) {
      return <Upload className="h-4 w-4" />
    }
    return <FileText className="h-4 w-4" />
  }

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString()
    } catch {
      return ''
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl sm:max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Link2 className="h-5 w-5" />
            Add Existing Sources
          </DialogTitle>
          <DialogDescription>
            Search and select existing sources to add to this notebook
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 flex-1 overflow-hidden flex flex-col">
          {/* Search Input */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search sources..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
            {isSearching && (
              <LoaderIcon className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin text-muted-foreground" />
            )}
          </div>

          {/* Source List */}
          <ScrollArea className="h-[400px] border rounded-md">
            {isSearching && filteredSources.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-[200px] text-muted-foreground">
                <LoaderIcon className="h-12 w-12 mb-2 animate-spin" />
                <p>Loading sources...</p>
              </div>
            ) : filteredSources.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-[200px] text-muted-foreground">
                <FileText className="h-12 w-12 mb-2 opacity-50" />
                <p>No sources found</p>
              </div>
            ) : (
              <div className="space-y-2 p-4">
                {filteredSources.map((source) => {
                  const isAlreadyLinked = currentSourceIds.has(source.id)
                  const isSelected = selectedSourceIds.includes(source.id)

                  return (
                    <div
                      key={source.id}
                      className={`flex items-start gap-3 p-3 rounded-lg border transition-colors min-w-0 ${
                        isSelected ? 'bg-accent border-accent-foreground/20' : 'hover:bg-accent/50'
                      }`}
                    >
                      <Checkbox
                        checked={isSelected}
                        onCheckedChange={() => handleToggleSource(source.id)}
                        disabled={isAlreadyLinked}
                        className="mt-1"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start gap-2 mb-1">
                          <div className="shrink-0 mt-0.5">
                            {getSourceIcon(source)}
                          </div>
                          <h4 className="font-medium text-sm break-words line-clamp-2 flex-1 min-w-0">
                            {source.title}
                          </h4>
                          {isAlreadyLinked && (
                            <Badge variant="secondary" className="text-xs shrink-0">
                              Linked
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground truncate">
                          Added {formatDate(source.created)}
                        </p>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </ScrollArea>

          {/* Truncation Warning */}
          {allSources.length >= 100 && !debouncedSearchQuery && (
            <div className="text-xs text-muted-foreground bg-muted/50 p-2 rounded-md">
              Showing first 100 sources. Use the Search feature to find specific sources.
            </div>
          )}

          {/* Selection Summary */}
          {selectedSourceIds.length > 0 && (
            <div className="text-sm text-muted-foreground">
              {selectedSourceIds.length} source{selectedSourceIds.length > 1 ? 's' : ''} selected
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={addSources.isPending}
          >
            Cancel
          </Button>
          <Button
            onClick={handleAddSelected}
            disabled={selectedSourceIds.length === 0 || addSources.isPending}
          >
            {addSources.isPending ? (
              <>
                <LoaderIcon className="mr-2 h-4 w-4 animate-spin" />
                Adding...
              </>
            ) : (
              <>Add Selected</>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
