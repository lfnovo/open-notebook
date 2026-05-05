'use client'

import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { sourcesApi } from '@/lib/api/sources'
import { SourceListResponse, BulkDeleteResponse } from '@/lib/types/api'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { EmptyState } from '@/components/common/EmptyState'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { FileText, Link as LinkIcon, Upload, AlignLeft, Trash2, ArrowUpDown } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getDateLocale } from '@/lib/utils/date-locale'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'
import { getApiErrorKey } from '@/lib/utils/error-handler'
import { ShareDialog } from '@/components/share/ShareDialog'
import { ResourceVisibilityBadge } from '@/components/share/ResourceVisibilityBadge'
import { useProfile } from '@/lib/hooks/use-profile'
import { canDeleteSource, deletableSourceIds } from '@/lib/utils/source-delete-eligibility'

export default function SourcesPage() {
  const { t, language } = useTranslation()
  const [sources, setSources] = useState<SourceListResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [sortBy, setSortBy] = useState<'created' | 'updated'>('updated')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [deleteDialog, setDeleteDialog] = useState<{ open: boolean; source: SourceListResponse | null }>({
    open: false,
    source: null
  })
  // Selection state for bulk delete
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [bulkDeleteDialog, setBulkDeleteDialog] = useState(false)
  const [bulkDeleting, setBulkDeleting] = useState(false)
  const [shareDialog, setShareDialog] = useState<{ open: boolean; source: SourceListResponse | null }>({
    open: false,
    source: null,
  })
  const router = useRouter()
  const tableRef = useRef<HTMLTableElement>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const { data: profile } = useProfile()
  const currentUserId = profile?.id
  
  // Pagination state
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const PAGE_SIZE = 30

  const fetchSources = useCallback(async () => {
    try {
      setLoading(true)
      const data = await sourcesApi.list({
        limit: PAGE_SIZE,
        offset: (page - 1) * PAGE_SIZE,
        sort_by: sortBy,
        sort_order: sortOrder,
      })

      setSources(data)
      setHasMore(data.length === PAGE_SIZE)
    } catch (err) {
      console.error('Failed to fetch sources:', err)
      setError(t.sources.failedToLoad)
      toast.error(t.sources.failedToLoad)
    } finally {
      setLoading(false)
    }
  }, [page, sortBy, sortOrder, t.sources.failedToLoad])

  // Initial load and when sort changes
  useEffect(() => {
    fetchSources()
  }, [fetchSources])

  // Listen for sourcesUpdated event to refresh instantly
  useEffect(() => {
    const handleSourcesUpdated = () => {
      fetchSources()
    }
    window.addEventListener('sourcesUpdated', handleSourcesUpdated)
    return () => window.removeEventListener('sourcesUpdated', handleSourcesUpdated)
  }, [fetchSources])

  // Polling for status updates
  useEffect(() => {
    const pollSources = async () => {
      // Avoid polling if already loading
      if (loading) return

      try {
        const data = await sourcesApi.list({
          limit: PAGE_SIZE,
          offset: (page - 1) * PAGE_SIZE,
          sort_by: sortBy,
          sort_order: sortOrder,
        })
        
        setSources(data)
        setHasMore(data.length === PAGE_SIZE)
      } catch (err) {
        console.error('Failed to poll sources:', err)
      }
    }

    const interval = setInterval(pollSources, 5000)
    return () => clearInterval(interval)
  }, [page, sortBy, sortOrder, loading])

  useEffect(() => {
    // Focus the table when component mounts or sources change
    if (sources.length > 0 && tableRef.current) {
      tableRef.current.focus()
    }
  }, [sources])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (sources.length === 0) return

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault()
          setSelectedIndex((prev) => {
            const newIndex = Math.min(prev + 1, sources.length - 1)
            setTimeout(() => scrollToSelectedRow(newIndex), 0)
            return newIndex
          })
          break
        case 'ArrowUp':
          e.preventDefault()
          setSelectedIndex((prev) => {
            const newIndex = Math.max(prev - 1, 0)
            setTimeout(() => scrollToSelectedRow(newIndex), 0)
            return newIndex
          })
          break
        case 'Enter':
          e.preventDefault()
          if (sources[selectedIndex]) {
            router.push(`/sources/${sources[selectedIndex].id}`)
          }
          break
        case 'Home':
          e.preventDefault()
          setSelectedIndex(0)
          setTimeout(() => scrollToSelectedRow(0), 0)
          break
        case 'End':
          e.preventDefault()
          const lastIndex = sources.length - 1
          setSelectedIndex(lastIndex)
          setTimeout(() => scrollToSelectedRow(lastIndex), 0)
          break
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [sources, selectedIndex, router])

  const scrollToSelectedRow = (index: number) => {
    const scrollContainer = scrollContainerRef.current
    if (!scrollContainer) return

    const rows = scrollContainer.querySelectorAll('tbody tr')
    const selectedRow = rows[index] as HTMLElement
    if (!selectedRow) return

    const containerRect = scrollContainer.getBoundingClientRect()
    const rowRect = selectedRow.getBoundingClientRect()

    if (rowRect.top < containerRect.top) {
      selectedRow.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
    else if (rowRect.bottom > containerRect.bottom) {
      selectedRow.scrollIntoView({ behavior: 'smooth', block: 'end' })
    }
  }

  const toggleSort = (field: 'created' | 'updated') => {
    if (sortBy === field) {
      setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(field)
      setSortOrder('desc')
    }
  }

  // Selection handlers
  const toggleSelect = (sourceId: string) => {
    const source = sources.find(s => s.id === sourceId)
    if (!source || !canDeleteSource(source, currentUserId)) return

    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(sourceId)) {
        next.delete(sourceId)
      } else {
        next.add(sourceId)
      }
      return next
    })
  }

  const toggleSelectAll = () => {
    const ids = deletableSourceIds(sources, currentUserId)
    if (ids.length === 0) return

    if (ids.every(id => selectedIds.has(id))) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(ids))
    }
  }

  const deletableIds = useMemo(
    () => deletableSourceIds(sources, currentUserId),
    [sources, currentUserId]
  )
  const selectedDeletableIds = useMemo(
    () => Array.from(selectedIds).filter(id => deletableIds.includes(id)),
    [selectedIds, deletableIds]
  )
  const isAllSelected = deletableIds.length > 0 && deletableIds.every(id => selectedIds.has(id))

  useEffect(() => {
    setSelectedIds(prev => {
      const next = new Set(Array.from(prev).filter(id => deletableIds.includes(id)))
      return next.size === prev.size ? prev : next
    })
  }, [sources, currentUserId, deletableIds])

  // Bulk delete handler
  const handleBulkDelete = async () => {
    if (selectedDeletableIds.length === 0) return
    setBulkDeleting(true)
    try {
      const result: BulkDeleteResponse = await sourcesApi.bulkDelete(selectedDeletableIds)
      if (result.failed_count === 0) {
        toast.success(t.sources.bulkDeleteSuccess.replace('{count}', String(result.deleted_count)))
      } else {
        const partialMessage = t.sources.bulkDeletePartial
          .replace('{deleted}', String(result.deleted_count))
          .replace('{failed}', String(result.failed_count))
        const hasReferencedFailure = result.results.some(
          (item) =>
            !item.deleted &&
            getApiErrorKey(item.error) === 'apiErrors.sourceReferencedCannotDelete'
        )

        toast.warning(
          hasReferencedFailure
            ? `${partialMessage} ${t.apiErrors.sourceReferencedCannotDelete}`
            : partialMessage
        )
      }
      setSelectedIds(new Set())
      setBulkDeleteDialog(false)
      fetchSources()
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } }, message?: string }
      console.error('Failed to bulk delete sources:', error)
      toast.error(t(getApiErrorKey(error.response?.data?.detail || error.message)))
    } finally {
      setBulkDeleting(false)
    }
  }

  // Cache translations outside the loop to prevent proxy infinite loop detection
  const tSourcesTypeLink = t.sources?.type?.link ?? 'Link'
  const tSourcesTypeFile = t.sources?.type?.file ?? 'File'
  const tSourcesTypeText = t.sources?.type?.text ?? 'Text'
  const tUntitledSource = t.sources?.untitledSource ?? 'Untitled Source'
  const tYes = t.sources?.yes ?? 'Yes'
  const tNo = t.sources?.no ?? 'No'
  const tVisibilityPrivate = t.visibility?.private ?? 'Private'
  const tVisibilityTeam = t.visibility?.team ?? 'Team'
  const tVisibilityPublic = t.visibility?.public ?? 'Public'
  const visibilityLabels = {
    private: tVisibilityPrivate,
    team: tVisibilityTeam,
    public: tVisibilityPublic,
  }
  const tSourcesKgExtracted = t.sources?.kgExtracted ?? 'KG Extracted'
  const tSourcesKgExtractQueued = t.sources?.kgExtractQueued ?? 'KG extraction queued'

  const getSourceIcon = (source: SourceListResponse) => {
    if (source.asset?.url) return <LinkIcon className="h-4 w-4" />
    if (source.asset?.file_path) return <Upload className="h-4 w-4" />
    return <AlignLeft className="h-4 w-4" />
  }

  const getSourceType = (source: SourceListResponse) => {
    if (source.asset?.url) return tSourcesTypeLink
    if (source.asset?.file_path) return tSourcesTypeFile
    return tSourcesTypeText
  }

  const handleRowClick = useCallback((index: number, sourceId: string) => {
    setSelectedIndex(index)
    router.push(`/sources/${sourceId}`)
  }, [router])

  const handleExtractKg = useCallback(async (e: React.MouseEvent, sourceId: string) => {
    e.stopPropagation() // Prevent row click
    try {
      const result = await sourcesApi.extractKg(sourceId)
      if (result.success) {
        toast.success(tSourcesKgExtractQueued)
        // Optimistic update: flip kg_extracted to true
        setSources(prev => prev.map(s => s.id === sourceId ? { ...s, kg_extracted: true } : s))
      }
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } }, message?: string }
      toast.error(t(getApiErrorKey(error.response?.data?.detail || error.message)))
    }
  }, [t, tSourcesKgExtractQueued])

  const handleDeleteConfirm = async () => {
    if (!deleteDialog.source) return

    try {
      await sourcesApi.delete(deleteDialog.source.id)
      toast.success(t.sources.deleteSuccess)
      setSources(prev => prev.filter(s => s.id !== deleteDialog.source?.id))
      setSelectedIds(prev => {
        const next = new Set(prev)
        next.delete(deleteDialog.source!.id)
        return next
      })
      setDeleteDialog({ open: false, source: null })
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } }, message?: string };
      console.error('Failed to delete source:', error)
      toast.error(t(getApiErrorKey(error.response?.data?.detail || error.message)))
    }
  }

  if (loading) {
    return (
              <div className="flex h-full items-center justify-center">
          <LoadingSpinner />
        </div>
    )
  }

  if (error) {
    return (
              <div className="flex h-full items-center justify-center">
          <p className="text-red-500">{error}</p>
        </div>
    )
  }

  if (sources.length === 0) {
    return (
              <EmptyState
          icon={FileText}
          title={t.sources.noSourcesYet}
          description={t.sources.allSourcesDescShort}
        />
    )
  }

  return (
    <>
      <div className="flex flex-col h-full w-full max-w-none px-6 py-6">
        <div className="mb-6 flex-shrink-0">
          <h1 className="text-3xl font-bold">{t.sources.allSources}</h1>
          <p className="mt-2 text-muted-foreground">
            {t.sources.allSourcesDesc}
          </p>
        </div>

        {/* Toolbar with bulk actions */}
        <div className="flex items-center gap-2 mb-4 flex-shrink-0">
          <Button
            variant="outline"
            size="sm"
            onClick={toggleSelectAll}
            disabled={deletableIds.length === 0}
          >
            {isAllSelected ? t.sources.deselectAll : t.sources.selectAll}
          </Button>
          {selectedDeletableIds.length > 0 && (
            <>
              <span className="text-sm text-muted-foreground ml-2">
                {t.sources.selected.replace('{count}', String(selectedDeletableIds.length))}
              </span>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => setBulkDeleteDialog(true)}
                className="ml-auto"
              >
                <Trash2 className="h-4 w-4 mr-1" />
                {t.sources.bulkDelete}
              </Button>
            </>
          )}
        </div>

        <div ref={scrollContainerRef} className="flex-1 rounded-md border overflow-auto">
          <table
            ref={tableRef}
            tabIndex={0}
            className="w-full min-w-[1120px] outline-none table-fixed"
          >
            <colgroup>
              <col className="w-[40px]" />
              <col className="w-[120px]" />
              <col className="w-auto" />
              <col className="w-[90px]" />
              <col className="w-[140px]" />
              <col className="w-[90px]" />
              <col className="w-[90px]" />
              <col className="w-[80px]" />
              <col className="w-[90px]" />
            </colgroup>
            <thead className="sticky top-0 bg-background z-10">
              <tr className="border-b bg-muted/50">
                <th className="h-12 px-2 text-center align-middle">
                  <Checkbox
                    checked={isAllSelected}
                    onCheckedChange={toggleSelectAll}
                    aria-label={isAllSelected ? t.sources.deselectAll : t.sources.selectAll}
                  />
                </th>
                <th className="h-12 px-2 text-left align-middle font-medium text-muted-foreground">
                  {t.common.type}
                </th>
                <th className="h-12 px-2 text-left align-middle font-medium text-muted-foreground">
                  {t.common.title}
                </th>
                <th className="h-12 px-2 text-left align-middle font-medium text-muted-foreground">
                  {t.visibility?.label || "可见性"}
                </th>
                <th className="h-12 px-2 text-left align-middle font-medium text-muted-foreground hidden sm:table-cell">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => toggleSort('created')}
                    className="h-8 px-2 hover:bg-muted"
                  >
                    {t.common.created_label}
                    <ArrowUpDown className={cn(
                      "ml-1 h-3 w-3",
                      sortBy === 'created' ? 'opacity-100' : 'opacity-30'
                    )} />
                    {sortBy === 'created' && (
                      <span className="ml-1 text-xs">
                        {sortOrder === 'asc' ? '↑' : '↓'}
                      </span>
                    )}
                  </Button>
                </th>
                <th className="h-12 px-2 text-center align-middle font-medium text-muted-foreground hidden md:table-cell">
                  {t.sources.insights}
                </th>
                <th className="h-12 px-2 text-center align-middle font-medium text-muted-foreground hidden md:table-cell">
                  {t.sources.referenceCount}
                </th>
                <th className="h-12 px-2 text-center align-middle font-medium text-muted-foreground hidden lg:table-cell">
                  {t.sources.embedded}
                </th>
                <th className="h-12 px-2 text-center align-middle font-medium text-muted-foreground hidden xl:table-cell">
                  {tSourcesKgExtracted}
                </th>
              </tr>
            </thead>
            <tbody>
              {sources.map((source, index) => (
                <tr
                  key={source.id}
                  onClick={() => handleRowClick(index, source.id)}
                  onMouseEnter={() => setSelectedIndex(index)}
                  className={cn(
                    "border-b transition-colors cursor-pointer",
                    selectedIndex === index
                      ? "bg-accent"
                      : "hover:bg-muted/50"
                  )}
                >
                  <td className="h-12 px-2 text-center" onClick={(e) => e.stopPropagation()}>
                    <Checkbox
                      checked={selectedIds.has(source.id)}
                      onCheckedChange={() => toggleSelect(source.id)}
                      disabled={!canDeleteSource(source, currentUserId)}
                      aria-label={`Select ${source.title || tUntitledSource}`}
                    />
                  </td>
                  <td className="h-12 px-2">
                    <div className="flex items-center gap-1">
                      {getSourceIcon(source)}
                      <Badge variant="secondary" className="text-xs">
                        {getSourceType(source)}
                      </Badge>
                    </div>
                  </td>
                  <td className="h-12 px-2">
                    <div className="flex flex-col overflow-hidden">
                      <span className="font-medium truncate">
                        {source.title || tUntitledSource}
                      </span>
                      {source.asset?.url && (
                        <span className="text-xs text-muted-foreground truncate">
                          {source.asset.url}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="h-12 px-2" onClick={(e) => e.stopPropagation()}>
                    <ResourceVisibilityBadge
                      visibility={source.visibility}
                      labels={visibilityLabels}
                      title={t.sharing?.title || 'Share'}
                      onClick={() => setShareDialog({ open: true, source })}
                    />
                  </td>
                  <td className="h-12 px-2 text-muted-foreground text-sm hidden sm:table-cell">
                    {formatDistanceToNow(new Date(source.created), { 
                      addSuffix: true,
                      locale: getDateLocale(language)
                    })}
                  </td>
                  <td className="h-12 px-2 text-center hidden md:table-cell">
                    <span className="text-sm font-medium">{source.insights_count || 0}</span>
                  </td>
                  <td className="h-12 px-2 text-center hidden md:table-cell">
                    <Badge
                      variant={source.reference_count > 0 ? "secondary" : "outline"}
                      className="text-xs"
                    >
                      {source.reference_count || 0}
                    </Badge>
                  </td>
                  <td className="h-12 px-2 text-center hidden lg:table-cell">
                    <Badge variant={source.embedded ? "default" : "secondary"} className="text-xs">
                      {source.embedded ? tYes : tNo}
                    </Badge>
                  </td>
                  <td className="h-12 px-2 text-center hidden xl:table-cell" onClick={(e) => e.stopPropagation()}>
                    {source.kg_extracted ? (
                      <Badge variant="default" className="text-xs">
                        {tYes}
                      </Badge>
                    ) : (
                      <button
                        onClick={(e) => handleExtractKg(e, source.id)}
                        className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors bg-amber-100 text-amber-800 hover:bg-amber-200 dark:bg-amber-900/30 dark:text-amber-400 dark:hover:bg-amber-900/50 cursor-pointer border-0"
                        title={t.sources?.kgExtractHint || "点击抽取知识图谱"}
                      >
                        {tNo}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination Controls */}
        <div className="flex items-center justify-between mt-4 pt-4 border-t">
          <Button 
            variant="outline" 
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
          >
            {language.startsWith('zh') ? '上一页' : 'Previous'}
          </Button>
          <span className="text-sm text-muted-foreground">
            {language.startsWith('zh') ? `第 ${page} 页` : `Page ${page}`}
          </span>
          <Button 
            variant="outline" 
            onClick={() => setPage(p => p + 1)}
            disabled={!hasMore}
          >
            {language.startsWith('zh') ? '下一页' : 'Next'}
          </Button>
        </div>
      </div>

      <ConfirmDialog
        open={deleteDialog.open}
        onOpenChange={(open) => setDeleteDialog({ open, source: deleteDialog.source })}
        title={t.sources?.delete ?? 'Delete'}
        description={(t.sources?.deleteConfirmWithTitle ?? 'Are you sure you want to delete {title}?').replace('{title}', deleteDialog.source?.title || tUntitledSource)}
        confirmText={t.common?.delete ?? 'Delete'}
        confirmVariant="destructive"
        onConfirm={handleDeleteConfirm}
      />

      <ConfirmDialog
        open={bulkDeleteDialog}
        onOpenChange={setBulkDeleteDialog}
        title={t.sources?.bulkDelete ?? 'Delete Selected'}
        description={(t.sources?.bulkDeleteConfirm ?? 'Are you sure you want to delete {count} source(s)?').replace('{count}', String(selectedDeletableIds.length))}
        confirmText={t.common?.delete ?? 'Delete'}
        confirmVariant="destructive"
        onConfirm={handleBulkDelete}
        isLoading={bulkDeleting}
      />

      {shareDialog.source && (
        <ShareDialog
          open={shareDialog.open}
          onOpenChange={(open) => setShareDialog({ open, source: shareDialog.source })}
          resourceType="source"
          resourceId={shareDialog.source.id}
          resourceTitle={shareDialog.source.title || tUntitledSource}
          resourceVisibility={shareDialog.source.visibility}
          onChanged={(visibility) => {
            const sourceId = shareDialog.source?.id
            if (!sourceId) return
            setSources(prev => prev.map(s => s.id === sourceId ? { ...s, visibility } : s))
            setShareDialog(prev =>
              prev.source?.id === sourceId
                ? { ...prev, source: { ...prev.source, visibility } }
                : prev
            )
          }}
        />
      )}
    </>
  )
}
