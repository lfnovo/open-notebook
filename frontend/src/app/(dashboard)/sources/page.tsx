'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { sourcesApi } from '@/lib/api/sources'
import { SourceListResponse } from '@/lib/types/api'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { EmptyState } from '@/components/common/EmptyState'
import { AppShell } from '@/components/layout/AppShell'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { FileText, Link as LinkIcon, Upload, AlignLeft, Trash2, ArrowUpDown } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'

export default function SourcesPage() {
  const [sources, setSources] = useState<SourceListResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [sortBy, setSortBy] = useState<'created' | 'updated'>('updated')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [deleteDialog, setDeleteDialog] = useState<{ open: boolean; source: SourceListResponse | null }>({
    open: false,
    source: null
  })
  const router = useRouter()
  const tableRef = useRef<HTMLTableElement>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const offsetRef = useRef(0)
  const loadingMoreRef = useRef(false)
  const hasMoreRef = useRef(true)
  const PAGE_SIZE = 30

  const fetchSources = useCallback(async (reset = false) => {
    try {
      // Check flags before proceeding
      if (!reset && (loadingMoreRef.current || !hasMoreRef.current)) {
        return
      }

      if (reset) {
        setLoading(true)
        offsetRef.current = 0
        setSources([])
        hasMoreRef.current = true
      } else {
        loadingMoreRef.current = true
        setLoadingMore(true)
      }

      const data = await sourcesApi.list({
        limit: PAGE_SIZE,
        offset: offsetRef.current,
        sort_by: sortBy,
        sort_order: sortOrder,
      })

      if (reset) {
        setSources(data)
      } else {
        setSources(prev => [...prev, ...data])
      }

      // Check if we have more data
      const hasMoreData = data.length === PAGE_SIZE
      hasMoreRef.current = hasMoreData
      offsetRef.current += data.length
    } catch (err) {
      console.error('Failed to fetch sources:', err)
      setError('Failed to load sources')
      toast.error('Failed to load sources')
    } finally {
      setLoading(false)
      setLoadingMore(false)
      loadingMoreRef.current = false
    }
  }, [sortBy, sortOrder])

  // Initial load and when sort changes
  useEffect(() => {
    fetchSources(true)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sortBy, sortOrder])

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
            // Scroll to keep selected row visible
            setTimeout(() => scrollToSelectedRow(newIndex), 0)
            return newIndex
          })
          break
        case 'ArrowUp':
          e.preventDefault()
          setSelectedIndex((prev) => {
            const newIndex = Math.max(prev - 1, 0)
            // Scroll to keep selected row visible
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

    // Find the selected row element
    const rows = scrollContainer.querySelectorAll('tbody tr')
    const selectedRow = rows[index] as HTMLElement
    if (!selectedRow) return

    const containerRect = scrollContainer.getBoundingClientRect()
    const rowRect = selectedRow.getBoundingClientRect()

    // Check if row is above visible area
    if (rowRect.top < containerRect.top) {
      selectedRow.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
    // Check if row is below visible area
    else if (rowRect.bottom > containerRect.bottom) {
      selectedRow.scrollIntoView({ behavior: 'smooth', block: 'end' })
    }
  }

  // Set up scroll listener after sources are loaded
  useEffect(() => {
    const scrollContainer = scrollContainerRef.current
    if (!scrollContainer) return

    let scrollTimeout: NodeJS.Timeout | null = null

    const handleScroll = () => {
      if (scrollTimeout) {
        clearTimeout(scrollTimeout)
      }

      scrollTimeout = setTimeout(() => {
        if (!scrollContainerRef.current) return

        const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current
        const distanceFromBottom = scrollHeight - scrollTop - clientHeight

        // Load more when within 200px of the bottom
        if (distanceFromBottom < 200 && !loadingMoreRef.current && hasMoreRef.current) {
          fetchSources(false)
        }
      }, 100)
    }

    scrollContainer.addEventListener('scroll', handleScroll)
    handleScroll() // Check on mount

    return () => {
      scrollContainer.removeEventListener('scroll', handleScroll)
      if (scrollTimeout) {
        clearTimeout(scrollTimeout)
      }
    }
  }, [fetchSources, sources.length])

  const toggleSort = (field: 'created' | 'updated') => {
    if (sortBy === field) {
      // Toggle order if clicking the same field
      setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      // Switch to new field with default desc order
      setSortBy(field)
      setSortOrder('desc')
    }
  }

  const getSourceIcon = (source: SourceListResponse) => {
    if (source.asset?.url) return <LinkIcon className="h-4 w-4" />
    if (source.asset?.file_path) return <Upload className="h-4 w-4" />
    return <AlignLeft className="h-4 w-4" />
  }

  const getSourceType = (source: SourceListResponse) => {
    if (source.asset?.url) return 'Link'
    if (source.asset?.file_path) return 'File'
    return 'Text'
  }

  const handleRowClick = useCallback((index: number, sourceId: string) => {
    setSelectedIndex(index)
    router.push(`/sources/${sourceId}`)
  }, [router])

  const handleDeleteClick = useCallback((e: React.MouseEvent, source: SourceListResponse) => {
    e.stopPropagation() // Prevent row click
    setDeleteDialog({ open: true, source })
  }, [])

  const handleDeleteConfirm = async () => {
    if (!deleteDialog.source) return

    try {
      await sourcesApi.delete(deleteDialog.source.id)
      toast.success('Source deleted successfully')
      // Remove the deleted source from the list
      setSources(prev => prev.filter(s => s.id !== deleteDialog.source?.id))
      setDeleteDialog({ open: false, source: null })
    } catch (err) {
      console.error('Failed to delete source:', err)
      toast.error('Failed to delete source')
    }
  }

  if (loading) {
    return (
      <AppShell>
        <div className="flex h-full items-center justify-center">
          <LoadingSpinner />
        </div>
      </AppShell>
    )
  }

  if (error) {
    return (
      <AppShell>
        <div className="flex h-full items-center justify-center">
          <p className="text-red-500">{error}</p>
        </div>
      </AppShell>
    )
  }

  if (sources.length === 0) {
    return (
      <AppShell>
        <EmptyState
          icon={FileText}
          title="No sources yet"
          description="Sources from all notebooks will appear here"
        />
      </AppShell>
    )
  }

  return (
    <AppShell>
      <div className="flex flex-col h-full w-full max-w-none px-6 py-6">
        <div className="mb-6 flex-shrink-0">
          <h1 className="text-3xl font-bold">All Sources</h1>
          <p className="mt-2 text-muted-foreground">
            Browse all sources across your notebooks. Use arrow keys to navigate and Enter to open.
          </p>
        </div>

        <div ref={scrollContainerRef} className="flex-1 rounded-md border overflow-auto">
          <table
            ref={tableRef}
            tabIndex={0}
            className="w-full min-w-[800px] outline-none table-fixed"
          >
            <colgroup>
              <col className="w-[120px]" />
              <col className="w-auto" />
              <col className="w-[140px]" />
              <col className="w-[100px]" />
              <col className="w-[100px]" />
              <col className="w-[100px]" />
            </colgroup>
            <thead className="sticky top-0 bg-background z-10">
              <tr className="border-b bg-muted/50">
                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">
                  Type
                </th>
                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">
                  Title
                </th>
                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground hidden sm:table-cell">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => toggleSort('created')}
                    className="h-8 px-2 hover:bg-muted"
                  >
                    Created
                    <ArrowUpDown className={cn(
                      "ml-2 h-3 w-3",
                      sortBy === 'created' ? 'opacity-100' : 'opacity-30'
                    )} />
                    {sortBy === 'created' && (
                      <span className="ml-1 text-xs">
                        {sortOrder === 'asc' ? '↑' : '↓'}
                      </span>
                    )}
                  </Button>
                </th>
                <th className="h-12 px-4 text-center align-middle font-medium text-muted-foreground hidden md:table-cell">
                  Insights
                </th>
                <th className="h-12 px-4 text-center align-middle font-medium text-muted-foreground hidden lg:table-cell">
                  Embedded
                </th>
                <th className="h-12 px-4 text-right align-middle font-medium text-muted-foreground">
                  Actions
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
                  <td className="h-12 px-4">
                    <div className="flex items-center gap-2">
                      {getSourceIcon(source)}
                      <Badge variant="secondary" className="text-xs">
                        {getSourceType(source)}
                      </Badge>
                    </div>
                  </td>
                  <td className="h-12 px-4">
                    <div className="flex flex-col overflow-hidden">
                      <span className="font-medium truncate">
                        {source.title || 'Untitled Source'}
                      </span>
                      {source.asset?.url && (
                        <span className="text-xs text-muted-foreground truncate">
                          {source.asset.url}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="h-12 px-4 text-muted-foreground text-sm hidden sm:table-cell">
                    {formatDistanceToNow(new Date(source.created), { addSuffix: true })}
                  </td>
                  <td className="h-12 px-4 text-center hidden md:table-cell">
                    <span className="text-sm font-medium">{source.insights_count || 0}</span>
                  </td>
                  <td className="h-12 px-4 text-center hidden lg:table-cell">
                    <Badge variant={source.embedded ? "default" : "secondary"} className="text-xs">
                      {source.embedded ? "Yes" : "No"}
                    </Badge>
                  </td>
                  <td className="h-12 px-4 text-right">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={(e) => handleDeleteClick(e, source)}
                      className="text-destructive hover:text-destructive"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </td>
                </tr>
              ))}
              {loadingMore && (
                <tr>
                  <td colSpan={6} className="h-16 text-center">
                    <div className="flex items-center justify-center">
                      <LoadingSpinner />
                      <span className="ml-2 text-muted-foreground">Loading more sources...</span>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <ConfirmDialog
        open={deleteDialog.open}
        onOpenChange={(open) => setDeleteDialog({ open, source: deleteDialog.source })}
        title="Delete Source"
        description={`Are you sure you want to delete "${deleteDialog.source?.title || 'this source'}"? This action cannot be undone.`}
        confirmText="Delete"
        confirmVariant="destructive"
        onConfirm={handleDeleteConfirm}
      />
    </AppShell>
  )
}