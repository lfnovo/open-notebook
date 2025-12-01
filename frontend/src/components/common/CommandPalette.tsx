'use client'

import { useEffect, useState, useCallback, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { useCreateDialogs } from '@/lib/hooks/use-create-dialogs'
import { useNotebooks } from '@/lib/hooks/use-notebooks'
import { useTheme } from '@/lib/stores/theme-store'
import {
  CommandDialog,
  CommandInput,
  CommandList,
  CommandGroup,
  CommandItem,
  CommandSeparator,
} from '@/components/ui/command'
import {
  Book,
  Search,
  Mic,
  Bot,
  Shuffle,
  Settings,
  FileText,
  Wrench,
  MessageCircleQuestion,
  Plus,
  Sun,
  Moon,
  Monitor,
  Loader2,
} from 'lucide-react'

const navigationItems = [
  { name: 'Sources', href: '/sources', icon: FileText, keywords: ['files', 'documents', 'upload'] },
  { name: 'Notebooks', href: '/notebooks', icon: Book, keywords: ['notes', 'research', 'projects'] },
  { name: 'Ask and Search', href: '/search', icon: Search, keywords: ['find', 'query'] },
  { name: 'Podcasts', href: '/podcasts', icon: Mic, keywords: ['audio', 'episodes', 'generate'] },
  { name: 'Models', href: '/models', icon: Bot, keywords: ['ai', 'llm', 'providers', 'openai', 'anthropic'] },
  { name: 'Transformations', href: '/transformations', icon: Shuffle, keywords: ['prompts', 'templates', 'actions'] },
  { name: 'Settings', href: '/settings', icon: Settings, keywords: ['preferences', 'config', 'options'] },
  { name: 'Advanced', href: '/advanced', icon: Wrench, keywords: ['debug', 'system', 'tools'] },
]

const createItems = [
  { name: 'Create Source', action: 'source', icon: FileText },
  { name: 'Create Notebook', action: 'notebook', icon: Book },
  { name: 'Create Podcast', action: 'podcast', icon: Mic },
]

const themeItems = [
  { name: 'Light Theme', value: 'light' as const, icon: Sun, keywords: ['bright', 'day'] },
  { name: 'Dark Theme', value: 'dark' as const, icon: Moon, keywords: ['night'] },
  { name: 'System Theme', value: 'system' as const, icon: Monitor, keywords: ['auto', 'default'] },
]

export function CommandPalette() {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const router = useRouter()
  const { openSourceDialog, openNotebookDialog, openPodcastDialog } = useCreateDialogs()
  const { setTheme } = useTheme()
  const { data: notebooks, isLoading: notebooksLoading } = useNotebooks(false)

  // Global keyboard listener for ⌘K / Ctrl+K
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      // Skip if focus is inside editable elements
      const target = e.target as HTMLElement | null
      if (
        target &&
        (target.isContentEditable ||
          ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName))
      ) {
        return
      }

      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        e.stopPropagation()
        setOpen((open) => !open)
      }
    }

    // Use capture phase to intercept before other handlers
    document.addEventListener('keydown', down, true)
    return () => document.removeEventListener('keydown', down, true)
  }, [])

  // Reset query when dialog closes
  useEffect(() => {
    if (!open) {
      setQuery('')
    }
  }, [open])

  const handleSelect = useCallback((callback: () => void) => {
    setOpen(false)
    setQuery('')
    // Use setTimeout to ensure dialog closes before action
    setTimeout(callback, 0)
  }, [])

  const handleNavigate = useCallback((href: string) => {
    handleSelect(() => router.push(href))
  }, [handleSelect, router])

  const handleSearch = useCallback(() => {
    if (!query.trim()) return
    handleSelect(() => router.push(`/search?q=${encodeURIComponent(query)}&mode=search`))
  }, [handleSelect, router, query])

  const handleAsk = useCallback(() => {
    if (!query.trim()) return
    handleSelect(() => router.push(`/search?q=${encodeURIComponent(query)}&mode=ask`))
  }, [handleSelect, router, query])

  const handleCreate = useCallback((action: string) => {
    handleSelect(() => {
      if (action === 'source') openSourceDialog()
      else if (action === 'notebook') openNotebookDialog()
      else if (action === 'podcast') openPodcastDialog()
    })
  }, [handleSelect, openSourceDialog, openNotebookDialog, openPodcastDialog])

  const handleTheme = useCallback((theme: 'light' | 'dark' | 'system') => {
    handleSelect(() => setTheme(theme))
  }, [handleSelect, setTheme])

  // Check if query matches any command (navigation, create, theme, or notebook)
  const queryLower = query.toLowerCase().trim()
  const hasCommandMatch = useMemo(() => {
    if (!queryLower) return false
    return (
      navigationItems.some(item =>
        item.name.toLowerCase().includes(queryLower) ||
        item.keywords.some(k => k.includes(queryLower))
      ) ||
      createItems.some(item =>
        item.name.toLowerCase().includes(queryLower)
      ) ||
      themeItems.some(item =>
        item.name.toLowerCase().includes(queryLower) ||
        item.keywords.some(k => k.includes(queryLower))
      ) ||
      (notebooks?.some(nb =>
        nb.name.toLowerCase().includes(queryLower) ||
        (nb.description && nb.description.toLowerCase().includes(queryLower))
      ) ?? false)
    )
  }, [queryLower, notebooks])

  // Determine if we should show the Search/Ask section at the top
  const showSearchFirst = query.trim() && !hasCommandMatch

  return (
    <CommandDialog
      open={open}
      onOpenChange={setOpen}
      title="Command Palette"
      description="Navigate, search, or ask your knowledge base"
      className="sm:max-w-lg"
    >
      <CommandInput
        placeholder="Type a command or search..."
        value={query}
        onValueChange={setQuery}
      />
      <CommandList>
        {/* Search/Ask - show FIRST when there's a query with no command match */}
        {showSearchFirst && (
          <CommandGroup heading="Search & Ask" forceMount>
            <CommandItem
              value={`__search__ ${query}`}
              onSelect={handleSearch}
              forceMount
            >
              <Search className="h-4 w-4" />
              <span>Search for &ldquo;{query}&rdquo;</span>
            </CommandItem>
            <CommandItem
              value={`__ask__ ${query}`}
              onSelect={handleAsk}
              forceMount
            >
              <MessageCircleQuestion className="h-4 w-4" />
              <span>Ask about &ldquo;{query}&rdquo;</span>
            </CommandItem>
          </CommandGroup>
        )}

        {/* Navigation */}
        <CommandGroup heading="Navigation">
          {navigationItems.map((item) => (
            <CommandItem
              key={item.href}
              value={`${item.name} ${item.keywords.join(' ')}`}
              onSelect={() => handleNavigate(item.href)}
            >
              <item.icon className="h-4 w-4" />
              <span>{item.name}</span>
            </CommandItem>
          ))}
        </CommandGroup>

        {/* Notebooks */}
        <CommandGroup heading="Notebooks">
          {notebooksLoading ? (
            <CommandItem disabled>
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Loading notebooks...</span>
            </CommandItem>
          ) : notebooks && notebooks.length > 0 ? (
            notebooks.map((notebook) => (
              <CommandItem
                key={notebook.id}
                value={`notebook ${notebook.name} ${notebook.description || ''}`}
                onSelect={() => handleNavigate(`/notebooks/${notebook.id}`)}
              >
                <Book className="h-4 w-4" />
                <span>{notebook.name}</span>
              </CommandItem>
            ))
          ) : null}
        </CommandGroup>

        {/* Create */}
        <CommandGroup heading="Create">
          {createItems.map((item) => (
            <CommandItem
              key={item.action}
              value={`create ${item.name}`}
              onSelect={() => handleCreate(item.action)}
            >
              <Plus className="h-4 w-4" />
              <span>{item.name}</span>
            </CommandItem>
          ))}
        </CommandGroup>

        {/* Theme */}
        <CommandGroup heading="Theme">
          {themeItems.map((item) => (
            <CommandItem
              key={item.value}
              value={`theme ${item.name} ${item.keywords.join(' ')}`}
              onSelect={() => handleTheme(item.value)}
            >
              <item.icon className="h-4 w-4" />
              <span>{item.name}</span>
            </CommandItem>
          ))}
        </CommandGroup>

        {/* Search/Ask - show at bottom when there IS a command match */}
        {query.trim() && hasCommandMatch && (
          <>
            <CommandSeparator />
            <CommandGroup heading="Or search your knowledge base" forceMount>
              <CommandItem
                value={`__search__ ${query}`}
                onSelect={handleSearch}
                forceMount
              >
                <Search className="h-4 w-4" />
                <span>Search for &ldquo;{query}&rdquo;</span>
              </CommandItem>
              <CommandItem
                value={`__ask__ ${query}`}
                onSelect={handleAsk}
                forceMount
              >
                <MessageCircleQuestion className="h-4 w-4" />
                <span>Ask about &ldquo;{query}&rdquo;</span>
              </CommandItem>
            </CommandGroup>
          </>
        )}
      </CommandList>
    </CommandDialog>
  )
}
