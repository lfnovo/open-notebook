'use client'

import { Globe } from 'lucide-react'
import { PublicContentExplorer } from '@/components/public-client'
import { useTranslation } from '@/lib/hooks/use-translation'

export default function DiscoverPage() {
  const { t } = useTranslation()

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-8 p-6">
        <div className="space-y-3">
          <div className="inline-flex items-center gap-2 rounded-full border border-stone-200 bg-white/70 px-3 py-1 text-sm text-muted-foreground">
            <Globe className="h-4 w-4 text-primary" />
            {t.public?.discover || t.navigation.discover}
          </div>
          <div>
            <h1 className="text-2xl font-semibold tracking-normal">
              {t.public?.title || 'Public Content'}
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
              {t.public?.description || 'Browse publicly shared notebooks and sources'}
            </p>
          </div>
        </div>

        <PublicContentExplorer />
      </div>
    </div>
  )
}
