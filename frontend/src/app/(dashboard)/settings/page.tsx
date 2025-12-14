'use client'

import { AppShell } from '@/components/layout/AppShell'
import { SettingsForm } from './components/SettingsForm'
import { ServiceStatus } from './components/ServiceStatus'
import { EmbeddingTaskTracker } from './components/EmbeddingTaskTracker'
import { useSettings } from '@/lib/hooks/use-settings'
import { Button } from '@/components/ui/button'
import { RefreshCw } from 'lucide-react'

export default function SettingsPage() {
  const { refetch } = useSettings()

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto">
        <div className="p-6">
          <div className="max-w-4xl space-y-6">
            <div className="flex items-center gap-4">
              <h1 className="text-2xl font-bold">Settings</h1>
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
            
            <ServiceStatus />

            <EmbeddingTaskTracker />

            <SettingsForm />
          </div>
        </div>
      </div>
    </AppShell>
  )
}
