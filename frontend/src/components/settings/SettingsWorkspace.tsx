'use client'

import { useState } from 'react'
import { Puzzle, RefreshCw, SlidersHorizontal } from 'lucide-react'
import { ResponsiveAppShell as AppShell } from '@/components/layout/AppShell'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useSettings } from '@/lib/hooks/use-settings'
import { SettingsForm } from '@/app/(dashboard)/settings/components/SettingsForm'
import { ModuleSettingsWorkspace } from '@/components/modules/ModuleSettingsWorkspace'

export function SettingsWorkspace({ initialTab = 'general' }: { initialTab?: 'general' | 'modules' }) {
  const { t } = useTranslation()
  const { refetch, isFetching } = useSettings()
  const [tab, setTab] = useState(initialTab)
  return <AppShell><div className="flex-1 overflow-y-auto"><div className="mx-auto max-w-6xl space-y-7 p-4 sm:p-8">
    <header className="flex items-start justify-between gap-4">
      <div><h1 className="text-2xl font-semibold tracking-tight">{t('navigation.settings')}</h1><p className="mt-2 text-sm text-muted-foreground">{t('modules.settingsIntro')}</p></div>
      {tab === 'general' && <Button variant="outline" className="min-h-11" disabled={isFetching} onClick={() => refetch()}><RefreshCw aria-hidden className={isFetching ? 'size-4 animate-spin' : 'size-4'} /><span className="hidden sm:inline">{t('modules.refresh')}</span><span className="sr-only sm:hidden">{t('modules.refresh')}</span></Button>}
    </header>
    <Tabs value={tab} onValueChange={value => setTab(value as typeof tab)}>
      <TabsList aria-label={t('navigation.settings')} className="mb-6 h-auto max-w-full gap-2 bg-muted/40 p-1">
        <TabsTrigger className="min-h-11 flex-none whitespace-nowrap px-4" value="general"><SlidersHorizontal aria-hidden className="size-4" />{t('modules.general')}</TabsTrigger>
        <TabsTrigger className="min-h-11 flex-none whitespace-nowrap px-4" value="modules"><Puzzle aria-hidden className="size-4" />{t('modules.settingsTab')}</TabsTrigger>
      </TabsList>
      <TabsContent value="general" forceMount hidden={tab !== 'general'} className="max-w-4xl"><SettingsForm /></TabsContent>
      <TabsContent value="modules" forceMount hidden={tab !== 'modules'}><ModuleSettingsWorkspace /></TabsContent>
    </Tabs>
  </div></div></AppShell>
}
