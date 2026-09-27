'use client'
import Link from 'next/link'
import { AppShell } from '@/components/layout/AppShell'
import { Button } from '@/components/ui/button'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useModules } from '@/lib/modules/hooks'
import { moduleEntries } from '@/lib/modules/generated'

export function ModulePage({ id }: { id: string }) {
  const { t } = useTranslation(), catalog = useModules()
  const feature = catalog.data?.find(item => item.id === id)
  const entry = moduleEntries[id]
  if (feature?.enabled && entry) return <entry.Page />
  return <AppShell><section className="space-y-4 p-8" role="status">
    <h1 className="text-2xl font-semibold">{feature?.name || t('modules.title')}</h1>
    <p>{catalog.isLoading ? t('common.loading') : catalog.isError ? t('modules.error') : t('modules.unavailable')}</p>
    {catalog.isError && <Button onClick={() => catalog.refetch()}>{t('modules.retry')}</Button>}
    <Button asChild variant="outline"><Link href="/settings/modules">{t('modules.title')}</Link></Button>
  </section></AppShell>
}
