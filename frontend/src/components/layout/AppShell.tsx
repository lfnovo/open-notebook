'use client'

import { AppSidebar } from './AppSidebar'
import { SetupBanner } from './SetupBanner'

interface AppShellProps {
  children: React.ReactNode
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex h-screen max-h-screen min-h-0 overflow-hidden">
      <AppSidebar />
      <main className="flex-1 flex flex-col min-h-0 min-w-0 overflow-hidden">
        <SetupBanner />
        {children}
      </main>
    </div>
  )
}
