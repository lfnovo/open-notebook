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
  LogOut
} from 'lucide-react'
import { useAuth } from '@/lib/hooks/use-auth'

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

  return (
    <div className="app-sidebar flex h-full w-64 flex-col bg-sidebar border-sidebar-border border-r">
      <div className="flex h-16 items-center px-6">
        <h1 className="text-lg font-semibold text-sidebar-foreground">Open Notebook</h1>
      </div>
      
      <nav className="flex-1 space-y-1 px-3 py-4">
        {navigation.map((item) => {
          const isActive = pathname.startsWith(item.href)
          return (
            <Link key={item.name} href={item.href}>
              <Button
                variant={isActive ? "secondary" : "ghost"}
                className={cn(
                  "w-full justify-start gap-3 text-sidebar-foreground",
                  isActive && "bg-sidebar-accent text-sidebar-accent-foreground"
                )}
              >
                <item.icon className="h-4 w-4" />
                {item.name}
              </Button>
            </Link>
          )
        })}
      </nav>
      
      <div className="p-3">
        <Button 
          variant="outline" 
          className="w-full justify-start gap-3"
          onClick={logout}
        >
          <LogOut className="h-4 w-4" />
          Sign Out
        </Button>
      </div>
    </div>
  )
}