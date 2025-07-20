'use client'

import { Button } from '@/components/ui/button'
import { RefreshCw } from 'lucide-react'
import { ThemeToggle } from '@/components/common/ThemeToggle'

interface AppHeaderProps {
  title: string
  onRefresh?: () => void
  children?: React.ReactNode
}

export function AppHeader({ title, onRefresh, children }: AppHeaderProps) {
  return (
    <div className="flex h-16 items-center justify-between border-b px-6">
      <div className="flex items-center gap-4">
        <h1 className="text-xl font-semibold">{title}</h1>
        {onRefresh && (
          <Button variant="outline" size="sm" onClick={onRefresh}>
            <RefreshCw className="h-4 w-4" />
          </Button>
        )}
      </div>
      <div className="flex items-center gap-2">
        {children}
        <ThemeToggle />
      </div>
    </div>
  )
}