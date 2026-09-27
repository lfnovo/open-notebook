'use client'

import { Menu } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { useTranslation } from '@/lib/hooks/use-translation'
import { AppSidebar } from './AppSidebar'
import { SetupBanner } from './SetupBanner'

interface AppShellProps {
  children: React.ReactNode
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex h-screen overflow-hidden">
      <AppSidebar />
      <main className="flex-1 flex flex-col min-h-0 overflow-hidden">
        <SetupBanner />
        {children}
      </main>
    </div>
  )
}

/** Shared responsive host for optional modules and the settings workspace. */
export function ResponsiveAppShell({ children }: AppShellProps) {
  const { t } = useTranslation()
  return <div className="flex h-dvh overflow-hidden">
    <div className="hidden shrink-0 md:flex"><AppSidebar /></div>
    <main className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
      <div className="flex items-center gap-2 border-b bg-card px-3 py-2 md:hidden">
        <Dialog><DialogTrigger asChild><Button variant="ghost" size="icon" className="size-11" aria-label={t('modules.navigation')}><Menu aria-hidden className="size-5" /></Button></DialogTrigger>
          <DialogContent className="start-0 top-0 h-dvh w-72 max-w-72 translate-x-0 translate-y-0 rounded-none border-y-0 border-s-0 p-0 sm:max-w-72">
            <DialogTitle className="sr-only">{t('modules.navigation')}</DialogTitle>
            <div className="overflow-y-auto"><AppSidebar /></div>
          </DialogContent>
        </Dialog>
        <span className="text-sm font-semibold">{t('common.appName')}</span>
      </div>
      <SetupBanner />
      {children}
    </main>
  </div>
}
