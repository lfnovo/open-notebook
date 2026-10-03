'use client'

import Link from 'next/link'
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { formatDistanceToNow } from 'date-fns'
import type { Locale } from 'date-fns/locale'
import { BookOpen, ChevronDown, ChevronRight, FileText } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { notebooksApi } from '@/lib/api/notebooks'
import type { RecentlyViewedResponse } from '@/lib/types/api'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getDateLocale } from '@/lib/utils/date-locale'

interface RecentlyViewedProps {
  limit?: number
}

function getItemHref(item: RecentlyViewedResponse) {
  if (item.type === 'notebook') {
    return `/notebooks/${encodeURIComponent(item.id)}`
  }

  return `/sources/${item.id}`
}

function formatViewedAt(value: string, locale: Locale) {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return value
  }

  return formatDistanceToNow(date, {
    addSuffix: true,
    locale,
  })
}

export function RecentlyViewed({ limit = 12 }: RecentlyViewedProps) {
  const { t, language } = useTranslation()
  const [isOpen, setIsOpen] = useState(true)
  const locale = getDateLocale(language)
  const { data: items, isLoading, isError } = useQuery({
    queryKey: ['recently-viewed', limit],
    queryFn: () => notebooksApi.recentlyViewed(limit),
  })

  if (isLoading || isError || !items || items.length === 0) {
    return null
  }

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen} className="space-y-4">
      <div className="flex items-center gap-2">
        <CollapsibleTrigger asChild>
          <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
            {isOpen ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
            <span className="sr-only">
              {t('notebooks.toggleRecentlyViewed', {
                defaultValue: 'Toggle recently viewed',
              })}
            </span>
          </Button>
        </CollapsibleTrigger>
        <h2 className="font-display text-lg font-semibold tracking-tight">
          {t('notebooks.recentlyViewed', { defaultValue: 'Recently Viewed' })}
        </h2>
        <span className="text-sm text-muted-foreground">({items.length})</span>
      </div>

      <CollapsibleContent>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {items.map((item) => {
            const Icon = item.type === 'notebook' ? BookOpen : FileText
            const typeLabel =
              item.type === 'notebook'
                ? t('notebooks.recentlyViewedNotebook', {
                    defaultValue: 'Notebook',
                  })
                : t('notebooks.recentlyViewedSource', {
                    defaultValue: 'Source',
                  })

            return (
              <Link
                key={`${item.type}-${item.id}`}
                href={getItemHref(item)}
                className="group flex items-center gap-3 rounded-md border bg-card px-3 py-2 card-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <div
                  className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-muted ${
                    item.type === 'notebook' ? 'text-teal' : 'text-sage'
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex min-w-0 items-center gap-2">
                    <p className="truncate text-sm font-medium">{item.title}</p>
                    <span className="shrink-0 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                      {typeLabel}
                    </span>
                  </div>
                  <p className="mt-0.5 truncate text-xs text-muted-foreground">
                    {t('notebooks.lastViewed', {
                      time: formatViewedAt(item.last_viewed_at, locale),
                      defaultValue: 'Viewed {{time}}',
                    })}
                  </p>
                </div>
              </Link>
            )
          })}
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}
