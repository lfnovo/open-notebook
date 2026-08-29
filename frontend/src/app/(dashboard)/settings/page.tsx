'use client'

import { AppShell } from '@/components/layout/AppShell'
import { SettingsForm } from './components/SettingsForm'
import { useSettings } from '@/lib/hooks/use-settings'
import { Button } from '@/components/ui/button'
import { RefreshCw } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { CostMeterWidget } from '@/components/usage/CostMeterWidget'
import { DriveConnectionCard } from '@/components/settings'

export default function SettingsPage() {
  const { t } = useTranslation()
  const { refetch } = useSettings()

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto">
        <div className="p-6">
          <div className="max-w-4xl">
            <div className="flex items-center gap-4 mb-6">
              <h1 className="font-display text-2xl font-bold tracking-tight">{t('navigation.settings')}</h1>
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>

            <div className="mb-6">
              <CostMeterWidget />
            </div>

            <div className="mb-6">
              <DriveConnectionCard />
            </div>

            <SettingsForm />
          </div>
        </div>
      </div>
    </AppShell>
  )
}
