'use client'

import { AppSidebar } from './AppSidebar'
import { AppHeader } from './AppHeader'

interface AppShellProps {
  title: string
  onRefresh?: () => void
  headerActions?: React.ReactNode
  children: React.ReactNode
}

export function AppShell({ title, onRefresh, headerActions, children }: AppShellProps) {
  return (
    <div className="flex h-screen">
      <AppSidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <AppHeader title={title} onRefresh={onRefresh}>
          {headerActions}
        </AppHeader>
        <main className="flex-1 overflow-auto p-6">
          {children}
        </main>
      </div>
    </div>
  )
}