'use client'

import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { 
  Book, 
  Search, 
  Mic, 
  Bot, 
  Shuffle, 
  Settings,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Menu
} from 'lucide-react'
import { useAuth } from '@/lib/hooks/use-auth'
import { useSidebarStore } from '@/lib/stores/sidebar-store'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

const navigation = [
  { name: 'Notebooks', href: '/notebooks', icon: Book },
  { name: 'Ask and Search', href: '/search', icon: Search },
  { name: 'Podcasts', href: '/podcasts', icon: Mic },
  { name: 'Models', href: '/models', icon: Bot },
  { name: 'Transformations', href: '/transformations', icon: Shuffle },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export function AppSidebar() {
  const pathname = usePathname()
  const { logout } = useAuth()
  const { isCollapsed, toggleCollapse } = useSidebarStore()

  return (
    <TooltipProvider delayDuration={0}>
      <div className={cn(
        "app-sidebar flex h-full flex-col bg-sidebar border-sidebar-border border-r transition-all duration-300",
        isCollapsed ? "w-16" : "w-64"
      )}>
        <div className={cn(
          "flex h-16 items-center",
          isCollapsed ? "justify-center px-2" : "justify-between px-6"
        )}>
          {!isCollapsed && (
            <h1 className="text-lg font-semibold text-sidebar-foreground">Open Notebook</h1>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleCollapse}
            className="text-sidebar-foreground hover:bg-sidebar-accent"
          >
            {isCollapsed ? <Menu className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </Button>
        </div>
        
        <nav className={cn(
          "flex-1 space-y-1 py-4",
          isCollapsed ? "px-2" : "px-3"
        )}>
          {navigation.map((item) => {
            const isActive = pathname.startsWith(item.href)
            const button = (
              <Button
                variant={isActive ? "secondary" : "ghost"}
                className={cn(
                  "w-full gap-3 text-sidebar-foreground",
                  isActive && "bg-sidebar-accent text-sidebar-accent-foreground",
                  isCollapsed ? "justify-center px-2" : "justify-start"
                )}
              >
                <item.icon className="h-4 w-4" />
                {!isCollapsed && <span>{item.name}</span>}
              </Button>
            )

            if (isCollapsed) {
              return (
                <Tooltip key={item.name}>
                  <TooltipTrigger asChild>
                    <Link href={item.href}>
                      {button}
                    </Link>
                  </TooltipTrigger>
                  <TooltipContent side="right">
                    {item.name}
                  </TooltipContent>
                </Tooltip>
              )
            }

            return (
              <Link key={item.name} href={item.href}>
                {button}
              </Link>
            )
          })}
        </nav>
        
        <div className={cn(
          "p-3",
          isCollapsed && "px-2"
        )}>
          {isCollapsed ? (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button 
                  variant="outline" 
                  className="w-full justify-center"
                  onClick={logout}
                >
                  <LogOut className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right">
                Sign Out
              </TooltipContent>
            </Tooltip>
          ) : (
            <Button 
              variant="outline" 
              className="w-full justify-start gap-3"
              onClick={logout}
            >
              <LogOut className="h-4 w-4" />
              Sign Out
            </Button>
          )}
        </div>
      </div>
    </TooltipProvider>
  )
}