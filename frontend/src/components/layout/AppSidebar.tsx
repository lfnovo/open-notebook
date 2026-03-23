'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import { usePathname } from 'next/navigation'

import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/lib/hooks/use-auth'
import { useSidebarStore } from '@/lib/stores/sidebar-store'
import { useCreateDialogs } from '@/lib/hooks/use-create-dialogs'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { ThemeToggle } from '@/components/common/ThemeToggle'
import { LanguageToggle } from '@/components/common/LanguageToggle'
import { TranslationKeys } from '@/lib/locales'
import { useTranslation } from '@/lib/hooks/use-translation'
import { Separator } from '@/components/ui/separator'
import {
  Book,
  Search,
  Mic,
  Bot,
  Shuffle,
  Settings,
  LogOut,
  ChevronLeft,
  Menu,
  FileText,
  Plus,
  Wrench,
  Command,
  GitBranch,
  Newspaper,
} from 'lucide-react'
import { SourcePickerDialog } from '@/components/studio/SourcePickerDialog'

const getNavigation = (t: TranslationKeys) => [
  {
    title: t.navigation.collect,
    items: [
      { name: t.navigation.sources, href: '/sources', icon: FileText, studio: null },
    ],
  },
  {
    title: t.navigation.process,
    items: [
      { name: t.navigation.notebooks, href: '/notebooks', icon: Book, studio: null },
      { name: t.navigation.askAndSearch, href: '/search', icon: Search, studio: null },
    ],
  },
  {
    title: 'Studio',
    items: [
      { name: 'Mind Map', href: null, icon: GitBranch, studio: 'mindmap' as const },
      { name: 'Infographic', href: null, icon: Newspaper, studio: 'infographic' as const },
      { name: 'Summary', href: null, icon: FileText, studio: 'summary' as const },
    ],
  },
  {
    title: t.navigation.manage,
    items: [
      { name: t.navigation.models, href: '/settings/api-keys', icon: Bot, studio: null },
      { name: t.navigation.transformations, href: '/transformations', icon: Shuffle, studio: null },
      { name: t.navigation.settings, href: '/settings', icon: Settings, studio: null },
      { name: t.navigation.advanced, href: '/advanced', icon: Wrench, studio: null },
    ],
  },
]

type CreateTarget = 'source' | 'notebook' | 'podcast'

export function AppSidebar() {
  const { t } = useTranslation()
  const navigation = getNavigation(t)
  const pathname = usePathname()
  const { logout } = useAuth()
  const { isCollapsed, toggleCollapse } = useSidebarStore()
  const { openSourceDialog, openNotebookDialog, openPodcastDialog } = useCreateDialogs()

  const [createMenuOpen, setCreateMenuOpen] = useState(false)
  const [isMac, setIsMac] = useState(true)
  const [mindMapPickerOpen, setMindMapPickerOpen] = useState(false)
  const [infographicPickerOpen, setInfographicPickerOpen] = useState(false)
  const [summaryPickerOpen, setSummaryPickerOpen] = useState(false)

  // Detect platform for keyboard shortcut display
  useEffect(() => {
    setIsMac(navigator.platform.toLowerCase().includes('mac'))
  }, [])

  const handleCreateSelection = (target: CreateTarget) => {
    setCreateMenuOpen(false)

    if (target === 'source') {
      openSourceDialog()
    } else if (target === 'notebook') {
      openNotebookDialog()
    } else if (target === 'podcast') {
      openPodcastDialog()
    }
  }

  return (
    <TooltipProvider delayDuration={0}>
      <div
        className={cn(
          'app-sidebar flex h-full flex-col bg-sidebar border-sidebar-border border-r transition-all duration-300',
          isCollapsed ? 'w-16' : 'w-64'
        )}
      >
        <div
          className={cn(
            'flex h-16 items-center group',
            isCollapsed ? 'justify-center px-2' : 'justify-between px-4'
          )}
        >
          {isCollapsed ? (
            <div className="relative flex items-center justify-center w-full">
              <Image
                src="/KavachLogo.png"
                alt="Kavach"
                width={32}
                height={32}
                className="transition-opacity group-hover:opacity-0 object-contain"
              />
              <Button
                variant="ghost"
                size="sm"
                onClick={toggleCollapse}
                className="absolute text-sidebar-foreground hover:bg-sidebar-accent opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <Menu className="h-4 w-4" />
              </Button>
            </div>
          ) : (
            <>
              <div className="flex items-center gap-2">
                <Image src="/logo(1).svg" alt="Notebook" width={50} height={36} className="object-contain" />
                <p>NOTEBOOK</p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={toggleCollapse}
                className="text-sidebar-foreground hover:bg-sidebar-accent"
                data-testid="sidebar-toggle"
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
            </>
          )}
        </div>

        <nav
          className={cn(
            'flex-1 space-y-1 py-4',
            isCollapsed ? 'px-2' : 'px-3'
          )}
        >
          <div
            className={cn(
              'mb-4',
              isCollapsed ? 'px-0' : 'px-3'
            )}
          >
            <DropdownMenu open={createMenuOpen} onOpenChange={setCreateMenuOpen}>
              {isCollapsed ? (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <DropdownMenuTrigger asChild>
                      <Button
                        onClick={() => setCreateMenuOpen(true)}
                        variant="default"
                        size="sm"
                        className="w-full justify-center px-2 bg-primary hover:bg-primary/90 text-primary-foreground border-0"
                        aria-label={t.common.create}
                      >
                        <Plus className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                  </TooltipTrigger>
                   <TooltipContent side="right">{t.common.create}</TooltipContent>
                </Tooltip>
              ) : (
                <DropdownMenuTrigger asChild>
                  <Button
                    onClick={() => setCreateMenuOpen(true)}
                    variant="default"
                    size="sm"
                    className="w-full justify-start bg-primary hover:bg-primary/90 text-primary-foreground border-0"
                   >
                    <Plus className="h-4 w-4 mr-2" />
                    {t.common.create}
                  </Button>
                </DropdownMenuTrigger>
              )}

              <DropdownMenuContent
                align={isCollapsed ? 'end' : 'start'}
                side={isCollapsed ? 'right' : 'bottom'}
                className="w-48"
              >
                <DropdownMenuItem
                  onSelect={(event) => {
                    event.preventDefault()
                    handleCreateSelection('source')
                  }}
                  className="gap-2"
                >
                   <FileText className="h-4 w-4" />
                  {t.common.source}
                </DropdownMenuItem>
                <DropdownMenuItem
                  onSelect={(event) => {
                    event.preventDefault()
                    handleCreateSelection('notebook')
                  }}
                  className="gap-2"
                >
                   <Book className="h-4 w-4" />
                  {t.common.notebook}
                </DropdownMenuItem>
                <DropdownMenuItem
                  onSelect={(event) => {
                    event.preventDefault()
                    handleCreateSelection('podcast')
                  }}
                  className="gap-2"
                >
                   <Mic className="h-4 w-4" />
                  {t.common.podcast}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>

          {navigation.map((section, index) => (
            <div key={section.title}>
              {index > 0 && (
                <Separator className="my-3" />
              )}
              <div className="space-y-1">
                {!isCollapsed && (
                  <h3 className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-sidebar-foreground/60">
                    {section.title}
                  </h3>
                )}

                {section.items.map((item) => {
                  const isActive = item.href ? (pathname?.startsWith(item.href) || false) : false
                  const button = (
                    <Button
                      variant={isActive ? 'secondary' : 'ghost'}
                      className={cn(
                        'w-full gap-3 text-sidebar-foreground sidebar-menu-item',
                        isActive && 'bg-sidebar-accent text-sidebar-accent-foreground',
                        isCollapsed ? 'justify-center px-2' : 'justify-start'
                      )}
                    >
                      <item.icon className="h-4 w-4" />
                      {!isCollapsed && <span>{item.name}</span>}
                    </Button>
                  )

                  // Studio items open a source picker dialog
                  if (item.studio) {
                    const studioKey = item.studio
                    const openPicker = () => {
                      if (studioKey === 'mindmap') setMindMapPickerOpen(true)
                      else if (studioKey === 'infographic') setInfographicPickerOpen(true)
                      else setSummaryPickerOpen(true)
                    }
                    if (isCollapsed) {
                      return (
                        <Tooltip key={item.name}>
                          <TooltipTrigger asChild>
                            <div onClick={openPicker}>{button}</div>
                          </TooltipTrigger>
                          <TooltipContent side="right">{item.name}</TooltipContent>
                        </Tooltip>
                      )
                    }
                    return (
                      <div key={item.name} onClick={openPicker}>
                        {button}
                      </div>
                    )
                  }

                  if (isCollapsed) {
                    return (
                      <Tooltip key={item.name}>
                        <TooltipTrigger asChild>
                          <Link href={item.href!}>
                            {button}
                          </Link>
                        </TooltipTrigger>
                        <TooltipContent side="right">{item.name}</TooltipContent>
                      </Tooltip>
                    )
                  }

                  return (
                    <Link key={item.name} href={item.href!}>
                      {button}
                    </Link>
                  )
                })}
              </div>
            </div>
          ))}
        </nav>

        <div
          className={cn(
            'border-t border-sidebar-border p-3 space-y-2',
            isCollapsed && 'px-2'
          )}
        >
          {/* Command Palette hint */}
          {!isCollapsed && (
            <div className="px-3 py-1.5 text-xs text-sidebar-foreground/60">
              <div className="flex items-center justify-between">
                 <span className="flex items-center gap-1.5">
                  <Command className="h-3 w-3" />
                  {t.common.quickActions}
                </span>
                <kbd className="pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
                  {isMac ? <span className="text-xs">⌘</span> : <span>Ctrl+</span>}K
                </kbd>
              </div>
               <p className="mt-1 text-[10px] text-sidebar-foreground/40">
                {t.common.quickActionsDesc}
              </p>
            </div>
          )}

           <div
            className={cn(
              'flex flex-col gap-2',
              isCollapsed ? 'items-center' : 'items-stretch'
            )}
          >
            {isCollapsed ? (
              <>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div>
                      <ThemeToggle iconOnly />
                    </div>
                  </TooltipTrigger>
                  <TooltipContent side="right">{t.common.theme}</TooltipContent>
                </Tooltip>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div>
                      <LanguageToggle iconOnly />
                    </div>
                  </TooltipTrigger>
                  <TooltipContent side="right">{t.common.language}</TooltipContent>
                </Tooltip>
              </>
            ) : (
              <>
                <ThemeToggle />
                <LanguageToggle />
              </>
            )}
          </div>

          {isCollapsed ? (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  className="w-full justify-center sidebar-menu-item"
                  onClick={logout}
                  aria-label={t.common.signOut}
                >
                  <LogOut className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
               <TooltipContent side="right">{t.common.signOut}</TooltipContent>
            </Tooltip>
          ) : (
            <Button
              variant="outline"
              className="w-full justify-start gap-3 sidebar-menu-item"
              onClick={logout}
              aria-label={t.common.signOut}
             >
              <LogOut className="h-4 w-4" />
              {t.common.signOut}
            </Button>
          )}
        </div>
      </div>
      {/* Studio source pickers — always mounted so result dialogs survive picker close */}
      <SourcePickerDialog
        open={mindMapPickerOpen}
        onOpenChange={setMindMapPickerOpen}
        mode="mindmap"
      />
      <SourcePickerDialog
        open={infographicPickerOpen}
        onOpenChange={setInfographicPickerOpen}
        mode="infographic"
      />
      <SourcePickerDialog
        open={summaryPickerOpen}
        onOpenChange={setSummaryPickerOpen}
        mode="summary"
      />
    </TooltipProvider>
  )
}
