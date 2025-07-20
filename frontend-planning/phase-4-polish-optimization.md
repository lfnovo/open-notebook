# Phase 4: Polish and Optimization Implementation Guide

## Overview

Phase 4 focuses on polishing the user experience, implementing performance optimizations, enhancing accessibility, and adding advanced UI interactions. This phase transforms the functional application from Phase 3 into a production-ready, professional-grade research tool.

## Technology Additions

- **Framer Motion**: For smooth animations and transitions
- **React Virtual**: For performance optimization of large lists
- **React Testing Library**: For comprehensive testing
- **Storybook**: For component documentation
- **MSW (Mock Service Worker)**: For testing and development
- **React Hook Form DevTools**: For development debugging
- **Bundle Analyzer**: For performance monitoring

## Project Structure Additions

```
src/
├── app/
│   ├── (dashboard)/
│   │   └── notebooks/
│   │       └── components/
│   │           ├── advanced/
│   │           │   ├── AdvancedSearch.tsx
│   │           │   ├── BulkActions.tsx
│   │           │   ├── KeyboardShortcuts.tsx
│   │           │   └── DataExport.tsx
│   │           ├── optimized/
│   │           │   ├── VirtualizedSourceList.tsx
│   │           │   ├── VirtualizedNoteList.tsx
│   │           │   └── OptimizedChat.tsx
│   │           └── enhanced/
│   │               ├── RichTextEditor.tsx
│   │               ├── CollaborativeFeatures.tsx
│   │               └── AdvancedFilters.tsx
├── components/
│   ├── ui/
│   │   ├── animations/
│   │   │   ├── fade-in.tsx
│   │   │   ├── slide-in.tsx
│   │   │   └── stagger-children.tsx
│   │   ├── optimized/
│   │   │   ├── virtual-list.tsx
│   │   │   ├── lazy-image.tsx
│   │   │   └── intersection-observer.tsx
│   │   └── accessibility/
│   │       ├── focus-trap.tsx
│   │       ├── screen-reader.tsx
│   │       └── keyboard-navigation.tsx
│   ├── features/
│   │   ├── onboarding/
│   │   │   ├── OnboardingTour.tsx
│   │   │   ├── FeatureHighlight.tsx
│   │   │   └── WelcomeWizard.tsx
│   │   ├── help/
│   │   │   ├── HelpCenter.tsx
│   │   │   ├── ContextualHelp.tsx
│   │   │   └── Tutorials.tsx
│   │   └── analytics/
│   │       ├── UsageTracking.tsx
│   │       └── PerformanceMonitor.tsx
├── lib/
│   ├── hooks/
│   │   ├── advanced/
│   │   │   ├── use-keyboard-shortcuts.ts
│   │   │   ├── use-offline-sync.ts
│   │   │   ├── use-infinite-scroll.ts
│   │   │   └── use-debounced-search.ts
│   │   ├── optimization/
│   │   │   ├── use-virtualization.ts
│   │   │   ├── use-lazy-loading.ts
│   │   │   └── use-performance-monitor.ts
│   │   └── accessibility/
│   │       ├── use-focus-management.ts
│   │       ├── use-screen-reader.ts
│   │       └── use-reduced-motion.ts
│   ├── utils/
│   │   ├── performance/
│   │   │   ├── memoization.ts
│   │   │   ├── lazy-loading.ts
│   │   │   └── bundle-splitting.ts
│   │   ├── accessibility/
│   │   │   ├── aria-helpers.ts
│   │   │   ├── focus-management.ts
│   │   │   └── screen-reader.ts
│   │   └── analytics/
│   │       ├── tracking.ts
│   │       └── performance.ts
│   └── constants/
│       ├── keyboard-shortcuts.ts
│       ├── animations.ts
│       └── accessibility.ts
├── __tests__/
├── .storybook/
└── docs/
```

---

## 1. Performance Optimization

### 1.1 Virtualized Lists (`components/ui/optimized/virtual-list.tsx`)

```typescript
'use client'

import { FixedSizeList as List } from 'react-window'
import { useMemo, useState, useCallback } from 'react'
import { Input } from '@/components/ui/input'
import { Search } from 'lucide-react'

interface VirtualListProps<T> {
  items: T[]
  itemHeight: number
  height: number
  renderItem: (item: T, index: number) => React.ReactNode
  searchable?: boolean
  searchKey?: keyof T
  onSearch?: (query: string) => void
  className?: string
}

export function VirtualList<T>({
  items,
  itemHeight,
  height,
  renderItem,
  searchable = false,
  searchKey,
  onSearch,
  className
}: VirtualListProps<T>) {
  const [searchQuery, setSearchQuery] = useState('')

  const filteredItems = useMemo(() => {
    if (!searchable || !searchQuery || !searchKey) return items
    
    return items.filter(item => {
      const value = item[searchKey]
      return String(value).toLowerCase().includes(searchQuery.toLowerCase())
    })
  }, [items, searchQuery, searchable, searchKey])

  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query)
    onSearch?.(query)
  }, [onSearch])

  const Row = useCallback(({ index, style }: { index: number; style: React.CSSProperties }) => (
    <div style={style}>
      {renderItem(filteredItems[index], index)}
    </div>
  ), [filteredItems, renderItem])

  return (
    <div className={className}>
      {searchable && (
        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            placeholder="Search..."
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
            className="pl-10"
          />
        </div>
      )}
      
      <List
        height={height}
        itemCount={filteredItems.length}
        itemSize={itemHeight}
        itemData={filteredItems}
      >
        {Row}
      </List>
    </div>
  )
}
```

### 1.2 Optimized Source List (`app/(dashboard)/notebooks/components/optimized/VirtualizedSourceList.tsx`)

```typescript
'use client'

import { useMemo } from 'react'
import { SourceListResponse } from '@/lib/types/api'
import { VirtualList } from '@/components/ui/optimized/virtual-list'
import { SourceCard } from '../SourceCard'
import { useInfiniteScroll } from '@/lib/hooks/optimization/use-infinite-scroll'

interface VirtualizedSourceListProps {
  sources: SourceListResponse[]
  notebookId: string
  onLoadMore?: () => void
  hasMore?: boolean
}

export function VirtualizedSourceList({ 
  sources, 
  notebookId, 
  onLoadMore, 
  hasMore 
}: VirtualizedSourceListProps) {
  const { containerRef } = useInfiniteScroll({
    onLoadMore,
    hasMore,
    threshold: 0.8
  })

  const renderSourceItem = useMemo(() => 
    (source: SourceListResponse, index: number) => (
      <div key={source.id} className="p-2">
        <SourceCard source={source} />
      </div>
    ), []
  )

  return (
    <div ref={containerRef} className="h-full">
      <VirtualList
        items={sources}
        itemHeight={120}
        height={600}
        renderItem={renderSourceItem}
        searchable
        searchKey="title"
        className="h-full"
      />
    </div>
  )
}
```

### 1.3 Performance Monitoring Hook (`lib/hooks/optimization/use-performance-monitor.ts`)

```typescript
import { useEffect, useCallback } from 'react'

interface PerformanceMetrics {
  componentRenderTime: number
  apiResponseTime: number
  memoryUsage: number
}

export function usePerformanceMonitor(componentName: string) {
  const measureRenderTime = useCallback(() => {
    const startTime = performance.now()
    
    return () => {
      const endTime = performance.now()
      const renderTime = endTime - startTime
      
      if (renderTime > 16) { // Frame budget exceeded
        console.warn(`${componentName} render time: ${renderTime.toFixed(2)}ms`)
      }
    }
  }, [componentName])

  const measureApiCall = useCallback((apiName: string) => {
    const startTime = performance.now()
    
    return () => {
      const endTime = performance.now()
      const responseTime = endTime - startTime
      
      console.log(`${apiName} response time: ${responseTime.toFixed(2)}ms`)
    }
  }, [])

  const getMemoryUsage = useCallback(() => {
    if ('memory' in performance) {
      return (performance as any).memory.usedJSHeapSize
    }
    return 0
  }, [])

  useEffect(() => {
    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (entry.entryType === 'measure') {
          console.log(`${entry.name}: ${entry.duration.toFixed(2)}ms`)
        }
      }
    })

    observer.observe({ entryTypes: ['measure'] })

    return () => observer.disconnect()
  }, [])

  return {
    measureRenderTime,
    measureApiCall,
    getMemoryUsage
  }
}
```

---

## 2. Advanced UI Interactions

### 2.1 Keyboard Shortcuts (`lib/hooks/advanced/use-keyboard-shortcuts.ts`)

```typescript
import { useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'

interface KeyboardShortcut {
  key: string
  ctrlKey?: boolean
  metaKey?: boolean
  shiftKey?: boolean
  altKey?: boolean
  action: () => void
  description: string
}

export function useKeyboardShortcuts(shortcuts: KeyboardShortcut[]) {
  const router = useRouter()

  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    const matchingShortcut = shortcuts.find(shortcut => {
      return (
        shortcut.key.toLowerCase() === event.key.toLowerCase() &&
        !!shortcut.ctrlKey === event.ctrlKey &&
        !!shortcut.metaKey === event.metaKey &&
        !!shortcut.shiftKey === event.shiftKey &&
        !!shortcut.altKey === event.altKey
      )
    })

    if (matchingShortcut) {
      event.preventDefault()
      matchingShortcut.action()
    }
  }, [shortcuts])

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  // Global shortcuts
  const globalShortcuts: KeyboardShortcut[] = [
    {
      key: 'n',
      ctrlKey: true,
      action: () => router.push('/notebooks'),
      description: 'Go to Notebooks'
    },
    {
      key: 's',
      ctrlKey: true,
      action: () => router.push('/search'),
      description: 'Go to Search'
    },
    {
      key: 'p',
      ctrlKey: true,
      action: () => router.push('/podcasts'),
      description: 'Go to Podcasts'
    },
    {
      key: '/',
      action: () => {
        const searchInput = document.querySelector('input[placeholder*="Search"]') as HTMLInputElement
        searchInput?.focus()
      },
      description: 'Focus search'
    }
  ]

  useKeyboardShortcuts(globalShortcuts)

  return { shortcuts: [...shortcuts, ...globalShortcuts] }
}
```

### 2.2 Advanced Search Component (`app/(dashboard)/notebooks/components/advanced/AdvancedSearch.tsx`)

```typescript
'use client'

import { useState, useMemo } from 'react'
import { useForm } from 'react-hook-form'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { X, Search, Filter } from 'lucide-react'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'

interface SearchFilters {
  query: string
  contentTypes: string[]
  dateRange: {
    from?: string
    to?: string
  }
  tags: string[]
  sortBy: 'relevance' | 'date' | 'title'
  sortOrder: 'asc' | 'desc'
}

interface AdvancedSearchProps {
  onSearch: (filters: SearchFilters) => void
  isLoading?: boolean
  resultCount?: number
}

export function AdvancedSearch({ onSearch, isLoading, resultCount }: AdvancedSearchProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [activeFilters, setActiveFilters] = useState<string[]>([])
  
  const { register, handleSubmit, watch, setValue, reset } = useForm<SearchFilters>({
    defaultValues: {
      query: '',
      contentTypes: [],
      dateRange: {},
      tags: [],
      sortBy: 'relevance',
      sortOrder: 'desc'
    }
  })

  const watchedValues = watch()

  const contentTypeOptions = [
    { value: 'sources', label: 'Sources' },
    { value: 'notes', label: 'Notes' },
    { value: 'insights', label: 'Insights' }
  ]

  const activeFilterCount = useMemo(() => {
    let count = 0
    if (watchedValues.contentTypes?.length > 0) count++
    if (watchedValues.dateRange?.from || watchedValues.dateRange?.to) count++
    if (watchedValues.tags?.length > 0) count++
    if (watchedValues.sortBy !== 'relevance') count++
    return count
  }, [watchedValues])

  const clearFilters = () => {
    reset()
    setActiveFilters([])
  }

  const removeFilter = (filterType: string) => {
    switch (filterType) {
      case 'contentTypes':
        setValue('contentTypes', [])
        break
      case 'dateRange':
        setValue('dateRange', {})
        break
      case 'tags':
        setValue('tags', [])
        break
      case 'sort':
        setValue('sortBy', 'relevance')
        setValue('sortOrder', 'desc')
        break
    }
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" />
            Advanced Search
          </CardTitle>
          {resultCount !== undefined && (
            <Badge variant="secondary">
              {resultCount} result{resultCount !== 1 ? 's' : ''}
            </Badge>
          )}
        </div>
      </CardHeader>
      
      <CardContent>
        <form onSubmit={handleSubmit(onSearch)} className="space-y-4">
          <div className="flex gap-2">
            <div className="flex-1">
              <Input
                {...register('query')}
                placeholder="Search your knowledge base..."
                className="text-base"
              />
            </div>
            <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
              <CollapsibleTrigger asChild>
                <Button variant="outline" type="button">
                  <Filter className="h-4 w-4 mr-2" />
                  Filters
                  {activeFilterCount > 0 && (
                    <Badge variant="secondary" className="ml-2">
                      {activeFilterCount}
                    </Badge>
                  )}
                </Button>
              </CollapsibleTrigger>
            </Collapsible>
            <Button type="submit" disabled={isLoading}>
              {isLoading ? 'Searching...' : 'Search'}
            </Button>
          </div>

          {activeFilterCount > 0 && (
            <div className="flex flex-wrap gap-2 items-center">
              <span className="text-sm text-gray-500">Active filters:</span>
              {watchedValues.contentTypes?.length > 0 && (
                <Badge variant="outline" className="flex items-center gap-1">
                  Content: {watchedValues.contentTypes.join(', ')}
                  <X 
                    className="h-3 w-3 cursor-pointer" 
                    onClick={() => removeFilter('contentTypes')}
                  />
                </Badge>
              )}
              {(watchedValues.dateRange?.from || watchedValues.dateRange?.to) && (
                <Badge variant="outline" className="flex items-center gap-1">
                  Date Range
                  <X 
                    className="h-3 w-3 cursor-pointer" 
                    onClick={() => removeFilter('dateRange')}
                  />
                </Badge>
              )}
              {watchedValues.sortBy !== 'relevance' && (
                <Badge variant="outline" className="flex items-center gap-1">
                  Sort: {watchedValues.sortBy}
                  <X 
                    className="h-3 w-3 cursor-pointer" 
                    onClick={() => removeFilter('sort')}
                  />
                </Badge>
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={clearFilters}
                className="h-6 px-2 text-xs"
              >
                Clear all
              </Button>
            </div>
          )}

          <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
            <CollapsibleContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div>
                  <Label>Content Types</Label>
                  <div className="space-y-2 mt-2">
                    {contentTypeOptions.map((option) => (
                      <div key={option.value} className="flex items-center space-x-2">
                        <Checkbox
                          id={option.value}
                          checked={watchedValues.contentTypes?.includes(option.value)}
                          onCheckedChange={(checked) => {
                            const current = watchedValues.contentTypes || []
                            if (checked) {
                              setValue('contentTypes', [...current, option.value])
                            } else {
                              setValue('contentTypes', current.filter(t => t !== option.value))
                            }
                          }}
                        />
                        <Label htmlFor={option.value} className="text-sm">
                          {option.label}
                        </Label>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <Label>Date Range</Label>
                  <div className="space-y-2 mt-2">
                    <Input
                      type="date"
                      {...register('dateRange.from')}
                      placeholder="From"
                    />
                    <Input
                      type="date"
                      {...register('dateRange.to')}
                      placeholder="To"
                    />
                  </div>
                </div>

                <div>
                  <Label>Sort</Label>
                  <div className="space-y-2 mt-2">
                    <Select 
                      value={watchedValues.sortBy}
                      onValueChange={(value) => setValue('sortBy', value as any)}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="relevance">Relevance</SelectItem>
                        <SelectItem value="date">Date</SelectItem>
                        <SelectItem value="title">Title</SelectItem>
                      </SelectContent>
                    </Select>
                    
                    <Select 
                      value={watchedValues.sortOrder}
                      onValueChange={(value) => setValue('sortOrder', value as any)}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="desc">Descending</SelectItem>
                        <SelectItem value="asc">Ascending</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>
            </CollapsibleContent>
          </Collapsible>
        </form>
      </CardContent>
    </Card>
  )
}
```

### 2.3 Bulk Actions Component (`app/(dashboard)/notebooks/components/advanced/BulkActions.tsx`)

```typescript
'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Badge } from '@/components/ui/badge'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { MoreHorizontal, Archive, Trash2, Download, Tag } from 'lucide-react'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'

interface BulkActionsProps<T> {
  items: T[]
  selectedItems: string[]
  onSelectionChange: (selectedIds: string[]) => void
  onBulkAction: (action: string, itemIds: string[]) => void
  getItemId: (item: T) => string
  actions?: {
    archive?: boolean
    delete?: boolean
    export?: boolean
    tag?: boolean
  }
}

export function BulkActions<T>({
  items,
  selectedItems,
  onSelectionChange,
  onBulkAction,
  getItemId,
  actions = { archive: true, delete: true, export: true, tag: true }
}: BulkActionsProps<T>) {
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)

  const isAllSelected = items.length > 0 && selectedItems.length === items.length
  const isPartiallySelected = selectedItems.length > 0 && selectedItems.length < items.length

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      onSelectionChange(items.map(getItemId))
    } else {
      onSelectionChange([])
    }
  }

  const handleItemSelect = (itemId: string, checked: boolean) => {
    if (checked) {
      onSelectionChange([...selectedItems, itemId])
    } else {
      onSelectionChange(selectedItems.filter(id => id !== itemId))
    }
  }

  const handleBulkDelete = () => {
    onBulkAction('delete', selectedItems)
    setShowDeleteDialog(false)
    onSelectionChange([])
  }

  if (items.length === 0) return null

  return (
    <>
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center gap-3">
          <Checkbox
            checked={isAllSelected}
            ref={(ref) => {
              if (ref) {
                ref.indeterminate = isPartiallySelected
              }
            }}
            onCheckedChange={handleSelectAll}
          />
          
          <span className="text-sm text-gray-600">
            {selectedItems.length > 0 ? (
              <>
                <Badge variant="secondary" className="mr-2">
                  {selectedItems.length}
                </Badge>
                selected
              </>
            ) : (
              `${items.length} items`
            )}
          </span>
        </div>

        {selectedItems.length > 0 && (
          <div className="flex items-center gap-2">
            {actions.archive && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onBulkAction('archive', selectedItems)}
              >
                <Archive className="h-4 w-4 mr-2" />
                Archive
              </Button>
            )}

            {actions.export && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onBulkAction('export', selectedItems)}
              >
                <Download className="h-4 w-4 mr-2" />
                Export
              </Button>
            )}

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm">
                  <MoreHorizontal className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                {actions.tag && (
                  <DropdownMenuItem onClick={() => onBulkAction('tag', selectedItems)}>
                    <Tag className="h-4 w-4 mr-2" />
                    Add Tags
                  </DropdownMenuItem>
                )}
                {actions.delete && (
                  <DropdownMenuItem
                    onClick={() => setShowDeleteDialog(true)}
                    className="text-red-600"
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    Delete
                  </DropdownMenuItem>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        )}
      </div>

      <ConfirmDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        title="Delete Selected Items"
        description={`Are you sure you want to delete ${selectedItems.length} selected items? This action cannot be undone.`}
        confirmText="Delete"
        confirmVariant="destructive"
        onConfirm={handleBulkDelete}
      />
    </>
  )
}
```

---

## 3. Accessibility Enhancements

### 3.1 Focus Management (`lib/hooks/accessibility/use-focus-management.ts`)

```typescript
import { useEffect, useRef, useCallback } from 'react'

export function useFocusManagement() {
  const focusableElementsSelector = `
    a[href]:not([disabled]),
    button:not([disabled]),
    input:not([disabled]),
    select:not([disabled]),
    textarea:not([disabled]),
    [tabindex]:not([tabindex="-1"]):not([disabled])
  `

  const trapFocus = useCallback((containerElement: HTMLElement) => {
    const focusableElements = containerElement.querySelectorAll(focusableElementsSelector)
    const firstElement = focusableElements[0] as HTMLElement
    const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement

    const handleTabKey = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return

      if (e.shiftKey) {
        if (document.activeElement === firstElement) {
          lastElement.focus()
          e.preventDefault()
        }
      } else {
        if (document.activeElement === lastElement) {
          firstElement.focus()
          e.preventDefault()
        }
      }
    }

    containerElement.addEventListener('keydown', handleTabKey)
    
    // Focus first element
    firstElement?.focus()

    return () => {
      containerElement.removeEventListener('keydown', handleTabKey)
    }
  }, [focusableElementsSelector])

  const restoreFocus = useCallback(() => {
    const lastFocused = useRef<HTMLElement | null>(null)
    
    return {
      save: () => {
        lastFocused.current = document.activeElement as HTMLElement
      },
      restore: () => {
        lastFocused.current?.focus()
      }
    }
  }, [])

  const announceLiveMessage = useCallback((message: string, priority: 'polite' | 'assertive' = 'polite') => {
    const announcement = document.createElement('div')
    announcement.setAttribute('aria-live', priority)
    announcement.setAttribute('aria-atomic', 'true')
    announcement.className = 'sr-only'
    announcement.textContent = message

    document.body.appendChild(announcement)

    setTimeout(() => {
      document.body.removeChild(announcement)
    }, 1000)
  }, [])

  return {
    trapFocus,
    restoreFocus,
    announceLiveMessage
  }
}
```

### 3.2 Accessible Modal (`components/ui/accessibility/accessible-modal.tsx`)

```typescript
'use client'

import { useEffect, useRef } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { useFocusManagement } from '@/lib/hooks/accessibility/use-focus-management'

interface AccessibleModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description?: string
  children: React.ReactNode
}

export function AccessibleModal({
  open,
  onOpenChange,
  title,
  description,
  children
}: AccessibleModalProps) {
  const modalRef = useRef<HTMLDivElement>(null)
  const { trapFocus, restoreFocus, announceLiveMessage } = useFocusManagement()
  const focusRestore = restoreFocus()

  useEffect(() => {
    if (open) {
      focusRestore.save()
      announceLiveMessage(`${title} dialog opened`)
      
      if (modalRef.current) {
        const cleanup = trapFocus(modalRef.current)
        return cleanup
      }
    } else {
      focusRestore.restore()
      announceLiveMessage(`${title} dialog closed`)
    }
  }, [open, title, trapFocus, focusRestore, announceLiveMessage])

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open) {
        onOpenChange(false)
      }
    }

    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [open, onOpenChange])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent 
        ref={modalRef}
        role="dialog"
        aria-labelledby="modal-title"
        aria-describedby={description ? "modal-description" : undefined}
        className="max-w-2xl"
      >
        <DialogHeader>
          <DialogTitle id="modal-title">{title}</DialogTitle>
          {description && (
            <p id="modal-description" className="text-sm text-gray-600">
              {description}
            </p>
          )}
        </DialogHeader>
        
        <div className="mt-4">
          {children}
        </div>
      </DialogContent>
    </Dialog>
  )
}
```

### 3.3 Screen Reader Utilities (`lib/utils/accessibility/screen-reader.ts`)

```typescript
export class ScreenReaderUtils {
  private static announcements = new Set<string>()

  static announce(message: string, priority: 'polite' | 'assertive' = 'polite') {
    // Avoid duplicate announcements
    if (this.announcements.has(message)) return
    
    this.announcements.add(message)
    
    const announcement = document.createElement('div')
    announcement.setAttribute('aria-live', priority)
    announcement.setAttribute('aria-atomic', 'true')
    announcement.className = 'sr-only absolute left-[-10000px] w-[1px] h-[1px] overflow-hidden'
    announcement.textContent = message

    document.body.appendChild(announcement)

    setTimeout(() => {
      document.body.removeChild(announcement)
      this.announcements.delete(message)
    }, 1000)
  }

  static announceProgress(current: number, total: number, operation: string) {
    const percentage = Math.round((current / total) * 100)
    this.announce(`${operation}: ${percentage}% complete, ${current} of ${total}`, 'polite')
  }

  static announceStatus(status: 'loading' | 'success' | 'error', message: string) {
    const priority = status === 'error' ? 'assertive' : 'polite'
    this.announce(`${status}: ${message}`, priority)
  }

  static announceNavigation(page: string) {
    this.announce(`Navigated to ${page}`, 'polite')
  }

  static announceAction(action: string, result?: string) {
    const message = result ? `${action}: ${result}` : action
    this.announce(message, 'polite')
  }
}
```

---

## 4. Animations and Polish

### 4.1 Animation Components (`components/ui/animations/fade-in.tsx`)

```typescript
'use client'

import { motion, AnimatePresence } from 'framer-motion'

interface FadeInProps {
  children: React.ReactNode
  duration?: number
  delay?: number
  show?: boolean
  className?: string
}

export function FadeIn({ 
  children, 
  duration = 0.3, 
  delay = 0, 
  show = true,
  className 
}: FadeInProps) {
  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration, delay }}
          className={className}
        >
          {children}
        </motion.div>
      )}
    </AnimatePresence>
  )
}

export function SlideIn({ 
  children, 
  direction = 'up',
  duration = 0.3, 
  delay = 0,
  show = true,
  className 
}: FadeInProps & { direction?: 'up' | 'down' | 'left' | 'right' }) {
  const variants = {
    up: { y: 20 },
    down: { y: -20 },
    left: { x: 20 },
    right: { x: -20 }
  }

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ opacity: 0, ...variants[direction] }}
          animate={{ opacity: 1, x: 0, y: 0 }}
          exit={{ opacity: 0, ...variants[direction] }}
          transition={{ duration, delay }}
          className={className}
        >
          {children}
        </motion.div>
      )}
    </AnimatePresence>
  )
}

export function StaggerChildren({ 
  children, 
  staggerDelay = 0.1,
  className 
}: { 
  children: React.ReactNode[]
  staggerDelay?: number
  className?: string 
}) {
  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={{
        hidden: { opacity: 0 },
        visible: {
          opacity: 1,
          transition: {
            staggerChildren: staggerDelay
          }
        }
      }}
      className={className}
    >
      {children.map((child, index) => (
        <motion.div
          key={index}
          variants={{
            hidden: { opacity: 0, y: 20 },
            visible: { opacity: 1, y: 0 }
          }}
        >
          {child}
        </motion.div>
      ))}
    </motion.div>
  )
}
```

### 4.2 Enhanced Loading States (`components/common/enhanced-loading.tsx`)

```typescript
'use client'

import { motion } from 'framer-motion'
import { Loader2 } from 'lucide-react'

interface LoadingSkeletonProps {
  lines?: number
  className?: string
}

export function LoadingSkeleton({ lines = 3, className }: LoadingSkeletonProps) {
  return (
    <div className={`space-y-3 ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <motion.div
          key={i}
          className="h-4 bg-gray-200 rounded"
          style={{ width: `${Math.random() * 40 + 60}%` }}
          animate={{
            opacity: [0.5, 1, 0.5],
          }}
          transition={{
            duration: 1.5,
            repeat: Infinity,
            delay: i * 0.1,
          }}
        />
      ))}
    </div>
  )
}

export function LoadingCard() {
  return (
    <div className="border rounded-lg p-4 space-y-3">
      <div className="flex items-center space-x-3">
        <LoadingSkeleton lines={1} className="flex-1" />
        <motion.div
          className="w-8 h-8 bg-gray-200 rounded"
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 1.5, repeat: Infinity }}
        />
      </div>
      <LoadingSkeleton lines={2} />
    </div>
  )
}

export function LoadingSpinner({ 
  size = 'md', 
  text,
  className 
}: { 
  size?: 'sm' | 'md' | 'lg'
  text?: string
  className?: string 
}) {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-6 w-6',
    lg: 'h-8 w-8'
  }

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <Loader2 className={`animate-spin ${sizeClasses[size]}`} />
      {text && (
        <motion.span
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-sm text-gray-600"
        >
          {text}
        </motion.span>
      )}
    </div>
  )
}
```

---

## 5. Onboarding and Help System

### 5.1 Onboarding Tour (`components/features/onboarding/OnboardingTour.tsx`)

```typescript
'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { X, ArrowRight, ArrowLeft } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

interface TourStep {
  id: string
  title: string
  description: string
  target: string
  position?: 'top' | 'bottom' | 'left' | 'right'
  action?: () => void
}

interface OnboardingTourProps {
  steps: TourStep[]
  onComplete: () => void
  onSkip: () => void
}

export function OnboardingTour({ steps, onComplete, onSkip }: OnboardingTourProps) {
  const [currentStep, setCurrentStep] = useState(0)
  const [isVisible, setIsVisible] = useState(true)

  const currentStepData = steps[currentStep]
  const isLastStep = currentStep === steps.length - 1
  const isFirstStep = currentStep === 0

  const handleNext = () => {
    if (currentStepData.action) {
      currentStepData.action()
    }

    if (isLastStep) {
      onComplete()
    } else {
      setCurrentStep(currentStep + 1)
    }
  }

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleSkip = () => {
    setIsVisible(false)
    onSkip()
  }

  useEffect(() => {
    const targetElement = document.querySelector(currentStepData.target)
    if (targetElement) {
      targetElement.scrollIntoView({ 
        behavior: 'smooth', 
        block: 'center' 
      })
      
      // Add highlight effect
      targetElement.classList.add('tour-highlight')
      return () => {
        targetElement.classList.remove('tour-highlight')
      }
    }
  }, [currentStep, currentStepData.target])

  if (!isVisible) return null

  return (
    <>
      {/* Overlay */}
      <div className="fixed inset-0 bg-black/50 z-40" />
      
      {/* Tour Card */}
      <AnimatePresence mode="wait">
        <motion.div
          key={currentStep}
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.9 }}
          transition={{ duration: 0.2 }}
          className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-md"
        >
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CardTitle className="text-lg">{currentStepData.title}</CardTitle>
                  <Badge variant="secondary">
                    {currentStep + 1} of {steps.length}
                  </Badge>
                </div>
                <Button variant="ghost" size="sm" onClick={handleSkip}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </CardHeader>
            
            <CardContent>
              <CardDescription className="mb-4">
                {currentStepData.description}
              </CardDescription>
              
              <div className="flex justify-between">
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    onClick={handlePrevious}
                    disabled={isFirstStep}
                  >
                    <ArrowLeft className="h-4 w-4 mr-2" />
                    Previous
                  </Button>
                  
                  <Button onClick={handleNext}>
                    {isLastStep ? 'Finish' : 'Next'}
                    {!isLastStep && <ArrowRight className="h-4 w-4 ml-2" />}
                  </Button>
                </div>
                
                <Button variant="ghost" onClick={handleSkip}>
                  Skip Tour
                </Button>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </AnimatePresence>
    </>
  )
}
```

### 5.2 Contextual Help (`components/features/help/ContextualHelp.tsx`)

```typescript
'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { HelpCircle, X } from 'lucide-react'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { motion, AnimatePresence } from 'framer-motion'

interface HelpContent {
  title: string
  description: string
  steps?: string[]
  links?: Array<{
    text: string
    url: string
  }>
}

interface ContextualHelpProps {
  content: HelpContent
  trigger?: React.ReactNode
  position?: 'top' | 'bottom' | 'left' | 'right'
}

export function ContextualHelp({ 
  content, 
  trigger,
  position = 'bottom' 
}: ContextualHelpProps) {
  const [isOpen, setIsOpen] = useState(false)

  const defaultTrigger = (
    <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
      <HelpCircle className="h-4 w-4 text-gray-400" />
    </Button>
  )

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        {trigger || defaultTrigger}
      </PopoverTrigger>
      
      <PopoverContent side={position} className="w-80">
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
        >
          <div className="flex items-start justify-between mb-3">
            <h4 className="font-semibold text-sm">{content.title}</h4>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0"
              onClick={() => setIsOpen(false)}
            >
              <X className="h-3 w-3" />
            </Button>
          </div>
          
          <p className="text-sm text-gray-600 mb-3">
            {content.description}
          </p>
          
          {content.steps && (
            <div className="mb-3">
              <h5 className="font-medium text-xs mb-2">Steps:</h5>
              <ol className="text-xs space-y-1">
                {content.steps.map((step, index) => (
                  <li key={index} className="flex gap-2">
                    <span className="text-gray-400">{index + 1}.</span>
                    <span>{step}</span>
                  </li>
                ))}
              </ol>
            </div>
          )}
          
          {content.links && (
            <div className="space-y-1">
              {content.links.map((link, index) => (
                <a
                  key={index}
                  href={link.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block text-xs text-blue-600 hover:text-blue-800"
                >
                  {link.text} →
                </a>
              ))}
            </div>
          )}
        </motion.div>
      </PopoverContent>
    </Popover>
  )
}
```

---

## 6. Testing and Quality Assurance

### 6.1 Component Tests (Example)

```typescript
// __tests__/components/NotebookCard.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { NotebookCard } from '@/app/(dashboard)/notebooks/components/NotebookCard'
import { NotebookResponse } from '@/lib/types/api'

const mockNotebook: NotebookResponse = {
  id: '1',
  name: 'Test Notebook',
  description: 'Test description',
  archived: false,
  created: '2024-01-01T00:00:00Z',
  updated: '2024-01-01T00:00:00Z'
}

const renderWithProviders = (component: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false }
    }
  })

  return render(
    <QueryClientProvider client={queryClient}>
      {component}
    </QueryClientProvider>
  )
}

describe('NotebookCard', () => {
  it('renders notebook information correctly', () => {
    renderWithProviders(<NotebookCard notebook={mockNotebook} />)
    
    expect(screen.getByText('Test Notebook')).toBeInTheDocument()
    expect(screen.getByText('Test description')).toBeInTheDocument()
  })

  it('shows archived badge for archived notebooks', () => {
    const archivedNotebook = { ...mockNotebook, archived: true }
    renderWithProviders(<NotebookCard notebook={archivedNotebook} />)
    
    expect(screen.getByText('Archived')).toBeInTheDocument()
  })

  it('opens actions menu when clicked', () => {
    renderWithProviders(<NotebookCard notebook={mockNotebook} />)
    
    const menuButton = screen.getByRole('button', { name: /more options/i })
    fireEvent.click(menuButton)
    
    expect(screen.getByText('Archive')).toBeInTheDocument()
    expect(screen.getByText('Delete')).toBeInTheDocument()
  })
})
```

### 6.2 Performance Monitoring

```typescript
// lib/utils/performance/monitoring.ts
export class PerformanceMonitor {
  private static metrics: Map<string, number[]> = new Map()

  static measureComponent(name: string) {
    const start = performance.now()
    
    return () => {
      const end = performance.now()
      const duration = end - start
      
      if (!this.metrics.has(name)) {
        this.metrics.set(name, [])
      }
      
      this.metrics.get(name)!.push(duration)
      
      // Alert for slow renders
      if (duration > 16) {
        console.warn(`Slow render detected: ${name} took ${duration.toFixed(2)}ms`)
      }
    }
  }

  static getAverageRenderTime(componentName: string): number {
    const times = this.metrics.get(componentName) || []
    return times.reduce((a, b) => a + b, 0) / times.length
  }

  static getReport(): Record<string, { average: number; max: number; count: number }> {
    const report: Record<string, { average: number; max: number; count: number }> = {}
    
    this.metrics.forEach((times, name) => {
      report[name] = {
        average: times.reduce((a, b) => a + b, 0) / times.length,
        max: Math.max(...times),
        count: times.length
      }
    })
    
    return report
  }
}
```

---

## 7. Additional Dependencies

Add to package.json:

```json
{
  "dependencies": {
    "framer-motion": "^10.16.0",
    "react-window": "^1.8.0",
    "react-intersection-observer": "^9.5.0"
  },
  "devDependencies": {
    "@testing-library/react": "^13.4.0",
    "@testing-library/jest-dom": "^6.1.0",
    "@testing-library/user-event": "^14.5.0",
    "jest": "^29.7.0",
    "jest-environment-jsdom": "^29.7.0",
    "@storybook/react": "^7.5.0",
    "@storybook/addon-essentials": "^7.5.0",
    "msw": "^2.0.0",
    "webpack-bundle-analyzer": "^4.9.0"
  }
}
```

---

## Success Criteria

Phase 4 is complete when:

1. ✅ **Performance Optimization**: Virtualized lists, lazy loading, optimized renders
2. ✅ **Advanced UI**: Keyboard shortcuts, bulk actions, advanced search
3. ✅ **Accessibility**: WCAG 2.1 AA compliance, screen reader support
4. ✅ **Animations**: Smooth transitions and loading states
5. ✅ **Onboarding**: User guidance and contextual help
6. ✅ **Testing**: Comprehensive test coverage (>80%)
7. ✅ **Documentation**: Component library and user guides
8. ✅ **Mobile Experience**: Fully responsive with touch optimization
9. ✅ **Error Handling**: Graceful error boundaries and recovery
10. ✅ **Production Ready**: Monitoring, analytics, and deployment optimization

This phase delivers a polished, professional-grade application ready for production deployment with excellent user experience, performance, and accessibility standards.