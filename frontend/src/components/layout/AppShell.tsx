'use client'

import { AppSidebar } from './AppSidebar'
import { QuickSearch } from '@/components/search/QuickSearch'

interface AppShellProps {
  children: React.ReactNode
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex h-screen overflow-hidden">
      <AppSidebar />
      <div className="flex-1 flex flex-col min-h-0">
        <header className="h-16 flex items-center justify-end px-4 border-b bg-background shrink-0 z-10">
          <div className='flex-1'/>
          <QuickSearch />
        </header>
        <main className="flex-1 flex flex-col min-h-0 overflow-hidden">
          {children}
        </main>
      </div>
    </div>
  )
}
