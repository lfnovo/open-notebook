'use client'

import { AppShell } from '@/components/layout/AppShell'
import { SettingsForm } from './components/SettingsForm'
import { useSettings } from '@/lib/hooks/use-settings'

export default function SettingsPage() {
  const { refetch } = useSettings()

  return (
    <AppShell title="Settings" onRefresh={() => refetch()}>
      <div className="max-w-4xl">
        <SettingsForm />
      </div>
    </AppShell>
  )
}